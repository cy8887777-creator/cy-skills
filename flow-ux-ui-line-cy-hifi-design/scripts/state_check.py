"""Station state machine — the physical carrier of gate verdicts.

Manifest: <project-dir>/project.manifest.json
  {"project": str, "workspace": str, "stations": {U1..U6: {"status": passed|failed|pending,
   "evidence": str, ...}}, "updatedAt": ISO}
  U4/U5 additionally record optional "disposition" ('verified'|'skipped'|'static') and
  "quality" ('verified'|'unverified'); both enums are validated on load. A mark of
  disposition 'skipped' or 'static' auto-fills quality='unverified' when quality is
  absent. Passed U4/U5 stations also record artifactPath/artifactHash (T05.2 HTML
  binding) and any station may carry history[] (T05.2 failure history).

Usage:
  python state_check.py --project-dir <dir>                          # validate manifest
  python state_check.py --project-dir <dir> --require U3             # gate: U1..U2 passed AND their
                                                                     # receipts/artifacts still fresh
  python state_check.py --project-dir <dir> --mark U2 passed --receipt qa/u2.json
  python state_check.py --project-dir <dir> --mark U5 passed --receipt qa/u5.json --disposition skipped
  python state_check.py --project-dir <dir> --mark U4 passed --receipt qa/u4.json --disposition static
  python state_check.py --project-dir <dir> --mark U2 passed --receipt qa/u2.json --resolve-note "fixed"
  python state_check.py --project-dir <dir> --mark U2 failed --evidence qa/notes.txt

Receipt gate rules (T05.1):
  --mark <station> passed REQUIRES --receipt <path>. The receipt is validated
  (schema / station / phase / input freshness via qa_receipt.validate_receipt)
  before 'passed' is written; evidence records
  "receipt=<path> sha256=<receipt-file-sha256>".
  Expected phase defaults per station (U2='final', other stations=any) and can be
  forced with --phase. failed/pending need no receipt; a --receipt given anyway is
  validated advisory-only (warning, non-blocking).
  --require re-validates every already-passed predecessor whose evidence contains
  receipt=<path>; a stale or unreadable receipt closes the gate and names it.

Station rules added in T05.2:
  Source binding (U4/U5): a passed mark for U4 requires receipt kind='verify';
  U5 requires kind='audit' or 'verify'. The receipt must also bind the original
  HTML artifact bytes — either explicit receipt fields artifactPath+artifactHash
  (sha256 over the HTML's raw bytes) or the first *.html entry in receipt.inputs.
  The resolved path + hash are recorded on the station record; --require re-hashes
  the artifact and reports "<station> station stale" when the bytes changed since
  the receipt. A U4/U5 receipt binding neither kind nor artifact is rejected
  (exit 1, station not written).
  Grading: --disposition/--quality are now also accepted for U4. disposition
  'skipped' or 'static' auto-fills quality='unverified' when quality is absent;
  explicit skipped/static + quality=verified is a manifest schema error.
  --require U6 judges process sufficiency from the recorded grading: a skipped
  U5 (quality=unverified) can pass; any static-graded station yields the
  conclusion note "static-only, browser/unverified items not covered".
  Failure history: every --mark appends {ts, result, reason} to station history[]
  (earlier entries are never erased). --require closes the gate with
  "<station> station has unresolved failure history" while any failed history
  entry carries no resolution. --mark passed --resolve-note "<text>" writes the
  resolution onto the last pre-existing history entry ("resolved:" marker), so a
  fixed station re-opens the gate while the history stays visible in the report.

exit 0 = ok / gate open; exit 1 = gate closed / validation failed; exit 2 = usage / manifest missing.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_receipt import file_sha256, load_receipt, receipt_input_paths, validate_receipt

STATIONS = ['U1', 'U2', 'U3', 'U4', 'U5', 'U6']
STATUSES = {'passed', 'failed', 'pending'}
DISPOSITIONS = ('verified', 'skipped', 'static')
QUALITIES = ('verified', 'unverified')
# per-station default expected receipt phase for --mark passed (None = any phase accepted)
STATION_DEFAULT_PHASE = {'U2': 'final'}
# T05.2 source binding: receipt kinds accepted for a passed mark, per station
STATION_KINDS = {'U4': ('verify',), 'U5': ('audit', 'verify')}
# stations whose passed mark must bind the original HTML artifact bytes
ARTIFACT_STATIONS = ('U4', 'U5')
# dispositions that grade the station below browser-verified quality (auto quality rule)
GRADE_AUTO_UNVERIFIED = ('skipped', 'static')
# evidence pointer written on receipt-backed marks; path may contain spaces
_EVIDENCE_RECEIPT_RE = re.compile(r'receipt=(.+?)\s+sha256=([0-9a-fA-F]{64})')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def manifest_path(project_dir: Path) -> Path:
    return project_dir / 'project.manifest.json'


def load(project_dir: Path):
    mp = manifest_path(project_dir)
    if not mp.exists():
        print(f'FAIL manifest not found: {mp} — create it before starting stations')
        raise SystemExit(2)
    try:
        m = json.loads(mp.read_text(encoding='utf-8-sig'))
    except Exception as e:
        print(f'FAIL manifest unreadable: {e}')
        raise SystemExit(1)
    problems = []
    if not isinstance(m.get('project'), str) or not m['project']:
        problems.append('project must be a non-empty string')
    if not isinstance(m.get('workspace'), str) or not m['workspace']:
        problems.append('workspace must be a non-empty string')
    st = m.get('stations')
    if not isinstance(st, dict):
        problems.append('stations must be an object')
    else:
        for name, rec in st.items():
            if name not in STATIONS:
                problems.append(f'unknown station: {name}')
            elif not isinstance(rec, dict) or rec.get('status') not in STATUSES:
                problems.append(f'{name}.status must be one of {sorted(STATUSES)}')
            if name in ARTIFACT_STATIONS and isinstance(rec, dict):
                if rec.get('disposition') is not None and rec.get('disposition') not in DISPOSITIONS:
                    problems.append(f'{name}.disposition must be one of {list(DISPOSITIONS)}')
                if rec.get('quality') is not None and rec.get('quality') not in QUALITIES:
                    problems.append(f'{name}.quality must be one of {list(QUALITIES)}')
                if rec.get('disposition') in GRADE_AUTO_UNVERIFIED \
                        and rec.get('quality') == 'verified':
                    problems.append(f"{name}.disposition={rec['disposition']} grades the "
                                    f"station unverified and contradicts quality=verified")
            if isinstance(rec, dict) and rec.get('history') is not None \
                    and not isinstance(rec.get('history'), list):
                problems.append(f'{name}.history must be a list when present')
        for name in STATIONS:
            if name not in st:
                problems.append(f'missing station: {name}')
    if problems:
        print('FAIL manifest schema invalid:')
        for p in problems:
            print('  - ' + p)
        raise SystemExit(1)
    return m, mp


def save(project_dir: Path, m, mp: Path):
    m['updatedAt'] = _now()
    tmp = mp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, mp)  # atomic — no torn writes under concurrent agents


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _next_station_brief(station: str):
    """站点标记 passed 后，打印下一站在 SKILL.md 中的要点（该节的粗体引导句），提醒先重读该节再动手。
    要点直接取自 SKILL.md，脚本里不另存一份规则。"""
    if station not in STATIONS or station == STATIONS[-1]:
        return
    nxt = STATIONS[STATIONS.index(station) + 1]
    skill_md = Path(__file__).resolve().parent.parent / 'SKILL.md'
    try:
        lines = skill_md.read_text(encoding='utf-8').splitlines()
    except OSError:
        return
    start = next((i for i, ln in enumerate(lines) if ln.startswith('### ' + nxt + ' ')), None)
    if start is None:
        # SKILL.md 已无该节（重构迁移到 references 后的回退）：输出固定指引（2026-11-23 U2 内容迁 editor-conversion.md）
        print(f'NEXT {nxt}: 动手前先重读 references/editor-conversion.md「正式链（全绿标准）」一节；'
              '判族见 references/editor-runtime.md「AI 判族」，配色版/风格卡见 references/style-panel-spec.md，'
              '同族变体见 references/controlled-blocks.md；完整代表页先行已随编辑器直出线退役。')
        return
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith('### ') or lines[i].startswith('## ')), len(lines))
    points = []
    for ln in lines[start + 1:end]:
        m = re.match(r'\s*(?:[-*]\s+)?\*\*(.+?)\*\*[：:]?\s*(.*)', ln)
        if m:
            rest = m.group(2).strip()
            points.append(m.group(1).strip() + ('：' + (rest[:48] + '…' if len(rest) > 48 else rest) if rest else ''))
    print(f'NEXT {nxt}: 动手前先重读 SKILL.md「{lines[start][4:].strip()}」一节（第 {start + 1} 行起）'
          '及其点名的参考文档。本节要点：')
    for p in points:
        print('  - ' + p)


def _sha_hex_ok(value) -> bool:
    return isinstance(value, str) and len(value) == 64 \
        and all(c in '0123456789abcdef' for c in value)


def _artifact_binding(receipt: dict, receipt_path: Path) -> dict:
    """T05.2: locate the original HTML artifact a U4/U5 receipt is bound to.

    Source order: explicit receipt fields artifactPath+artifactHash (sha256 hex,
    relative artifactPath resolves against the receipt's dir), else the first
    *.html entry in receipt['inputs'] (path + recorded sha256). Returns
    {'path': absolute str, 'hash': sha256 hex} or {'error': reason}.
    """
    base = Path(receipt_path).resolve().parent

    def _abs(value: str) -> str:
        p = Path(value)
        return str(p if p.is_absolute() else (base / p))

    apath, ahash = receipt.get('artifactPath'), receipt.get('artifactHash')
    if apath is not None or ahash is not None:
        if not isinstance(apath, str) or not apath:
            return {'error': 'receipt artifactPath must be a non-empty string when '
                             'binding an artifact (T05.2 source binding)'}
        if not _sha_hex_ok(ahash):
            return {'error': 'receipt artifactHash must be a sha256 hex string when '
                             'binding an artifact (T05.2 source binding)'}
        return {'path': _abs(apath), 'hash': ahash}
    for item in receipt.get('inputs') or []:
        if isinstance(item, dict) and isinstance(item.get('path'), str) \
                and item['path'].lower().endswith('.html') and _sha_hex_ok(item.get('sha256')):
            return {'path': _abs(item['path']), 'hash': item['sha256']}
    return {'error': 'receipt binds no HTML artifact: give artifactPath+artifactHash or '
                     'record the deliverable *.html in inputs (T05.2 source binding)'}


def _check_receipt(receipt_path: Path, station: str, phase) -> dict:
    """Validate one receipt for `station` against its OWN recorded inputs (freshness)."""
    try:
        receipt = load_receipt(receipt_path)
    except FileNotFoundError:
        return {'valid': False, 'reason': f'receipt not found: {receipt_path}'}
    except Exception as e:
        return {'valid': False, 'reason': f'receipt unreadable: {e}'}
    return validate_receipt(receipt_path, station, phase=phase,
                            expected_inputs=receipt_input_paths(receipt))


def _u1_style_gate(project_dir: Path):
    """U1 选型门禁 → 问题清单（空=通过）。
    ① intake/selection-result.json 在位、可解析、status=selected、每受众组 selected 非空（failed=宁停勿错）；
    ② 开工文档 §4 风格槽已升 1.0：无 V0.1 占位标记，且引用 selection-result.json（契约见
       solo-ui-line-cy-gui-style-picker/references/selection-contract.md §2）。"""
    problems = []
    intake = project_dir / 'intake'
    sel = intake / 'selection-result.json'
    if not sel.exists():
        problems.append('missing %s（选型回传未落盘）' % sel)
    else:
        try:
            data = json.loads(sel.read_text(encoding='utf-8'))
        except Exception as exc:
            problems.append('selection-result.json unreadable: %s' % exc)
        else:
            if data.get('status') != 'selected':
                problems.append('selection-result.json status=%r（须为 selected；failed=停线报告，不猜默认风格）'
                                % data.get('status'))
            groups = data.get('audienceGroups') or []
            if not groups:
                problems.append('selection-result.json audienceGroups 为空')
            for g in groups:
                if not g.get('selected'):
                    problems.append('受众组 %r 未选中任何风格' % g.get('group'))
            if data.get('pipeline') == 'scaffold':
                problems.append('pipeline=scaffold（脚手架管线不走本技能静态流程，停线报告）')
    docs = [p for p in (intake / '开工文档.md', project_dir / 'intake-开工文档.md') if p.exists()]
    if not docs and intake.exists():
        mds = [p for p in intake.glob('*.md')]
        if len(mds) == 1:
            docs = mds
    if not docs:
        problems.append('开工文档未找到（intake/开工文档.md）')
    else:
        text = docs[0].read_text(encoding='utf-8')
        if 'V0.1 占位' in text or '待选型' in text:
            problems.append('%s §4 风格槽仍是 V0.1 占位（须升 1.0：并入选中风格摘要）' % docs[0].name)
        if 'selection-result' not in text:
            problems.append('%s 未引用 selection-result.json（1.0 风格槽须附回传路径）' % docs[0].name)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project-dir', type=Path, required=True)
    ap.add_argument('--require', choices=STATIONS,
                    help='gate check: every station BEFORE this one must be passed '
                         'with fresh receipts')
    ap.add_argument('--mark', choices=STATIONS, help='set status of this station')
    ap.add_argument('status', nargs='?', choices=sorted(STATUSES),
                    help='status value for --mark')
    ap.add_argument('--evidence', default='', help='evidence pointer stored with --mark')
    ap.add_argument('--receipt', type=Path,
                    help='qa receipt JSON; REQUIRED for --mark <station> passed')
    ap.add_argument('--phase', choices=('incremental', 'final'), default=None,
                    help='force expected receipt phase (default: U2=final, other stations=any)')
    ap.add_argument('--disposition', choices=DISPOSITIONS,
                    help='U4/U5 only: disposition recorded with --mark U4/U5')
    ap.add_argument('--quality', choices=QUALITIES,
                    help='U4/U5 only: quality recorded with --mark U4/U5 '
                         '(skipped/static auto-fills unverified when absent)')
    ap.add_argument('--resolve-note', default=None,
                    help='explanation recorded on the last failed history entry when '
                         're-marking passed (clears "unresolved failure history")')
    args = ap.parse_args()

    if args.mark and not args.status:
        ap.error('--mark requires a status argument (passed|failed|pending)')
    if args.status and not args.mark:
        ap.error('status argument requires --mark')
    if args.evidence and not args.mark:
        ap.error('--evidence requires --mark')
    if args.receipt and not args.mark:
        ap.error('--receipt requires --mark')
    if (args.disposition or args.quality) and args.mark not in ('U4', 'U5'):
        ap.error('--disposition/--quality are only valid together with --mark U4/U5')
    if args.resolve_note and not (args.mark and args.status == 'passed'):
        ap.error('--resolve-note is only valid together with --mark <station> passed')
    if args.mark and args.status == 'passed' and not args.receipt:
        print('USAGE ERROR: --mark passed requires --receipt <qa_receipt.json> '
              '(receipt gate, T05.1)')
        raise SystemExit(2)

    project_dir = args.project_dir
    m, mp = load(project_dir)

    if args.mark:
        prev = m['stations'].get(args.mark, {})
        rec = {**prev, 'status': args.status}
        if args.status == 'passed':
            receipt_path = args.receipt
            if not receipt_path.exists():
                print(f'USAGE ERROR: receipt file not found: {receipt_path}')
                raise SystemExit(2)
            effective_phase = args.phase if args.phase is not None \
                else STATION_DEFAULT_PHASE.get(args.mark)
            verdict = _check_receipt(receipt_path, args.mark, effective_phase)
            if not verdict['valid']:
                print(f'RECEIPT REJECTED — {args.mark} NOT marked passed')
                print(f'  receipt: {receipt_path}')
                print(f'  reason: {verdict["reason"]}')
                raise SystemExit(1)
            if args.mark == 'U1':  # 选型门禁：说明书"风格槽非空"规则的脚本化（宁停勿错）
                style_problems = _u1_style_gate(project_dir)
                if style_problems:
                    print('STYLE GATE REJECTED — U1 NOT marked passed（选型环节未完成：先跑 solo-ui-line-cy-gui-style-picker）')
                    for sp in style_problems:
                        print(f'  reason: {sp}')
                    raise SystemExit(1)
            if args.mark in STATION_KINDS:  # T05.2 source binding
                bind_problems = []
                binding = None
                try:
                    receipt = load_receipt(receipt_path)
                    required = STATION_KINDS[args.mark]
                    if receipt.get('kind') not in required:
                        bind_problems.append(
                            'receipt kind=%r but %s requires kind in %s (T05.2 source binding)'
                            % (receipt.get('kind'), args.mark, list(required)))
                    binding = _artifact_binding(receipt, receipt_path)
                    if 'error' in binding:
                        bind_problems.append(binding['error'])
                    else:
                        try:
                            actual = file_sha256(binding['path'])
                        except OSError:
                            bind_problems.append('artifact file missing: %s' % binding['path'])
                        else:
                            if actual != binding['hash']:
                                bind_problems.append(
                                    'receipt artifactHash does not match current bytes of %s'
                                    % binding['path'])
                except Exception as exc:
                    bind_problems.append('receipt unreadable: %s' % exc)
                if bind_problems:
                    print(f'RECEIPT REJECTED — {args.mark} NOT marked passed '
                          f'(T05.2 source binding)')
                    print(f'  receipt: {receipt_path}')
                    for bp in bind_problems:
                        print(f'  reason: {bp}')
                    raise SystemExit(1)
                rec['artifactPath'] = binding['path']
                rec['artifactHash'] = binding['hash']
            receipt_sha = file_sha256(receipt_path)
            evidence = f'receipt={receipt_path.resolve()} sha256={receipt_sha}'
            if args.evidence:
                evidence += '; ' + args.evidence
            rec['evidence'] = evidence
        else:
            rec['evidence'] = args.evidence or prev.get('evidence', '')
            if args.receipt:
                verdict = _check_receipt(args.receipt, args.mark, args.phase)
                if not verdict['valid']:
                    print(f'WARNING: --receipt failed validation '
                          f'(advisory only, not blocking): {verdict["reason"]}')
        if args.mark in ('U4', 'U5'):
            disposition = args.disposition if args.disposition is not None \
                else prev.get('disposition')
            if args.quality is not None:
                quality = args.quality
            elif disposition in GRADE_AUTO_UNVERIFIED:
                quality = 'unverified'  # auto rule: skipped/static => unverified unless given
            else:
                quality = prev.get('quality')
            if disposition is not None:
                rec['disposition'] = disposition
            if quality is not None:
                rec['quality'] = quality
        # T05.2 failure history: append-only, repeated marks never erase old failures
        history = [dict(h) for h in (prev.get('history') or []) if isinstance(h, dict)]
        if args.status == 'passed' and args.resolve_note:
            for entry in reversed(history):
                if entry.get('result') == 'failed' \
                        and 'resolved:' not in str(entry.get('reason', '')) \
                        and not entry.get('resolved'):
                    entry['resolved'] = args.resolve_note
                    entry['reason'] = ('%s | resolved: %s'
                                       % (entry.get('reason', ''),
                                          args.resolve_note)).strip(' |')
                    break
        history.append({'ts': _now(), 'result': args.status,
                        'reason': rec.get('evidence', '') if args.status == 'passed'
                        else args.evidence})
        rec['history'] = history
        m['stations'][args.mark] = rec
        save(project_dir, m, mp)
        print(f'recorded: {args.mark} = {args.status}' +
              (f' (evidence: {rec["evidence"]})' if rec.get('evidence') else ''))
        if args.status == 'passed':
            _next_station_brief(args.mark)
        if not args.require:
            raise SystemExit(0)
        # --mark + --require combined: fall through to gate check with the updated manifest

    # status report
    print('manifest OK — ' + m.get('project', '?'))
    for name in STATIONS:
        rec = m['stations'].get(name, {'status': 'missing', 'evidence': ''})
        extra = ''
        if name in ('U4', 'U5'):
            bits = [rec.get(k) for k in ('disposition', 'quality') if rec.get(k)]
            if bits:
                extra = '  {' + ', '.join(str(b) for b in bits) + '}'
        hist = rec.get('history') or []
        if hist:
            extra += '  history:%d' % len(hist)
        print(f"  {name}: {rec.get('status')}" +
              (f"  [{rec.get('evidence')}]" if rec.get('evidence') else '') + extra)

    if args.require:
        idx = STATIONS.index(args.require)
        blockers = []
        receipt_problems = []
        history_problems = []
        history_notes = []
        for prev_name in STATIONS[:idx]:
            rec = m['stations'].get(prev_name, {})
            st = rec.get('status')
            if st != 'passed':
                blockers.append(f'{prev_name}={st}')
                continue
            mt = _EVIDENCE_RECEIPT_RE.search(rec.get('evidence') or '')
            if not mt:
                pass  # legacy evidence without receipt pointer: nothing to re-check
            else:
                receipt_path = mt.group(1)
                verdict = _check_receipt(Path(receipt_path), prev_name, None)
                if verdict['valid']:
                    pass
                elif verdict['reason'].startswith('stale:'):
                    for stale_name in verdict['reason'][len('stale:'):].strip().split(', '):
                        receipt_problems.append(f'  {prev_name} receipt stale: {stale_name}')
                else:
                    receipt_problems.append(
                        f'  {prev_name} receipt invalid: {verdict["reason"]} '
                        f'(receipt={receipt_path})')
            # T05.2: a U4/U5 station whose bound HTML artifact changed since its receipt
            apath, ahash = rec.get('artifactPath'), rec.get('artifactHash')
            if apath and ahash:
                try:
                    fresh = file_sha256(apath) == ahash
                except OSError:
                    receipt_problems.append(
                        f'  {prev_name} station stale: artifact missing: {apath}')
                else:
                    if not fresh:
                        receipt_problems.append(
                            f'  {prev_name} station stale: artifact changed since '
                            f'receipt: {apath}')
            # T05.2: failure history — visible in the report; unresolved failures close the gate
            fails = [h for h in (rec.get('history') or []) if isinstance(h, dict)
                     and h.get('result') == 'failed']
            if fails:
                unresolved = [h for h in fails
                              if 'resolved:' not in str(h.get('reason', ''))
                              and not h.get('resolved')]
                history_notes.append('  %s failure history: %d failed, %d resolved'
                                     % (prev_name, len(fails), len(fails) - len(unresolved)))
                if unresolved:
                    first = unresolved[0]
                    history_problems.append(
                        f'  {prev_name} station has unresolved failure history: '
                        f'{first.get("ts", "?")} {str(first.get("reason", ""))[:120]}')
        for line in history_notes:
            print(line)
        if blockers or receipt_problems or history_problems:
            head = f'GATE CLOSED — cannot enter {args.require}'
            if blockers:
                head += ', blockers: ' + ', '.join(blockers)
            print(head)
            for line in receipt_problems + history_problems:
                print(line)
            raise SystemExit(1)
        print(f'GATE OPEN — entering {args.require}')
        if args.require == 'U6':  # T05.2: grading-aware process sufficiency
            notes = []
            for prev_name in ('U4', 'U5'):
                rec = m['stations'].get(prev_name, {})
                if rec.get('status') != 'passed':
                    continue
                if rec.get('disposition') == 'static':
                    notes.append(f'{prev_name} static-only, '
                                 f'browser/unverified items not covered')
                elif prev_name == 'U5' and rec.get('disposition') == 'skipped':
                    notes.append('U5 skipped (quality=%s) — process sufficient'
                                 % (rec.get('quality') or 'unverified'))
            for n in notes:
                print('  U6 conclusion note: ' + n)

    raise SystemExit(0)


if __name__ == '__main__':
    main()
