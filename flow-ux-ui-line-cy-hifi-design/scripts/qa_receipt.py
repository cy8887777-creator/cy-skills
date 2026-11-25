"""qa_receipt — T05.1 frozen receipt schema: hashing, construction, validation.

Standalone module: imports stdlib only. It must never import build/verify/audit
or any other station business module (frozen spec).

Receipt head fields (frozen spec — exactly these are required):
  reportVersion  int, always 1
  checkerVersion str (non-empty)
  kind           'check' | 'build' | 'verify' | 'audit'
  station        'U1'..'U6' | null
  phase          'incremental' | 'final' | null
  scope          list[pageId] | null
  inputDigest    sha256 hex (64 lowercase hex chars)
  inputs         list of {'path': str, 'sha256': sha256hex}
  result         'ready' | 'passed' | 'fail' | 'error'
  findings       list
  coverage       object (dict)
  generatedAt    ISO8601 string

Digest rules (frozen spec):
  file digest  = SHA-256 over the file's raw bytes (BOM kept, newlines untouched)
  bundleDigest = SHA-256( concat( sorted( f'{ns}:{relpath}:{filesha}\\n' ) ) )
                 with ns in {'skill/', 'project/'}; sort key is
                 (ns + relpath).encode('utf-8'); mtime is never used.
  stale        = any recorded input file whose recomputed hash differs from the
                 receipt record (or which is missing on disk).

An 'incremental'-phase receipt can never substitute for 'final'.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPORT_VERSION = 1
KINDS = ('check', 'build', 'verify', 'audit')
STATIONS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6')
PHASES = ('incremental', 'final')
RESULTS = ('ready', 'passed', 'fail', 'error')
NAMESPACES = ('skill/', 'project/')
HEAD_FIELDS = ('reportVersion', 'checkerVersion', 'kind', 'station', 'phase', 'scope',
               'inputDigest', 'inputs', 'result', 'findings', 'coverage', 'generatedAt')

_HEX = set('0123456789abcdef')


def file_sha256(path) -> str:
    """SHA-256 hex of the file's raw bytes. BOM kept, newlines untouched."""
    digest = hashlib.sha256()
    with open(Path(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_digest(items) -> str:
    """SHA-256 over the sorted per-file digest lines.

    items: iterable of (ns, relpath, path) with ns in ('skill/', 'project/').
    Line format: ns + ':' + relpath + ':' + file_sha256 + '\\n';
    lines are sorted by (ns + relpath).encode('utf-8'); mtime is never used.
    """
    lines = []
    for ns, relpath, path in items:
        if ns not in NAMESPACES:
            raise ValueError('bundle_digest: ns must be one of %s, got %r' % (list(NAMESPACES), ns))
        lines.append(((ns + relpath).encode('utf-8'),
                      '%s:%s:%s\n' % (ns, relpath, file_sha256(path))))
    lines.sort(key=lambda pair: pair[0])
    blob = ''.join(text for _, text in lines).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()


def _is_sha256_hex(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


def _is_iso8601(value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    if text.endswith(('Z', 'z')):
        text = text[:-1] + '+00:00'
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def _validate_head(head: dict):
    """Return a list of problems (empty = valid) for a receipt head dict."""
    problems = []
    missing = [f for f in HEAD_FIELDS if f not in head]
    if missing:
        problems.append('missing field(s): ' + ', '.join(missing))

    def present(field):
        return field in head

    if present('reportVersion'):
        v = head['reportVersion']
        if isinstance(v, bool) or not isinstance(v, int):
            problems.append('reportVersion must be int')
        elif v != REPORT_VERSION:
            problems.append('reportVersion must be %d' % REPORT_VERSION)
    if present('checkerVersion') and (not isinstance(head['checkerVersion'], str)
                                      or not head['checkerVersion']):
        problems.append('checkerVersion must be a non-empty string')
    if present('kind') and head['kind'] not in KINDS:
        problems.append('kind must be one of %s' % (list(KINDS),))
    if present('station') and head['station'] is not None and head['station'] not in STATIONS:
        problems.append('station must be one of %s or null' % (list(STATIONS),))
    if present('phase') and head['phase'] is not None and head['phase'] not in PHASES:
        problems.append('phase must be one of %s or null' % (list(PHASES),))
    if present('scope') and head['scope'] is not None:
        if not isinstance(head['scope'], list) or not all(isinstance(x, str) for x in head['scope']):
            problems.append('scope must be a list of pageId strings or null')
    if present('inputDigest') and not _is_sha256_hex(head['inputDigest']):
        problems.append('inputDigest must be a sha256 hex string (64 lowercase hex chars)')
    if present('inputs'):
        inputs = head['inputs']
        if not isinstance(inputs, list):
            problems.append('inputs must be a list of {path, sha256}')
        else:
            for i, item in enumerate(inputs):
                if not isinstance(item, dict) or not isinstance(item.get('path'), str) \
                        or not item['path']:
                    problems.append('inputs[%d].path must be a non-empty string' % i)
                elif not _is_sha256_hex(item.get('sha256')):
                    problems.append('inputs[%d].sha256 must be a sha256 hex string' % i)
    if present('result') and head['result'] not in RESULTS:
        problems.append('result must be one of %s' % (list(RESULTS),))
    if present('findings') and not isinstance(head['findings'], list):
        problems.append('findings must be a list')
    if present('coverage') and not isinstance(head['coverage'], dict):
        problems.append('coverage must be an object')
    if present('generatedAt') and not _is_iso8601(head['generatedAt']):
        problems.append('generatedAt must be an ISO8601 timestamp string')
    return problems


def make_receipt(**head_fields) -> dict:
    """Build a receipt dict from the head fields; ValueError on missing/invalid fields."""
    missing = [f for f in HEAD_FIELDS if f not in head_fields]
    if missing:
        raise ValueError('make_receipt: missing head field(s): ' + ', '.join(missing))
    problems = _validate_head(head_fields)
    if problems:
        raise ValueError('make_receipt: ' + '; '.join(problems))
    return {f: head_fields[f] for f in HEAD_FIELDS}


def load_receipt(receipt_path) -> dict:
    """Load a receipt JSON file (BOM-tolerant). Raises on missing/unreadable."""
    raw = Path(receipt_path).read_bytes()
    return json.loads(raw.decode('utf-8-sig'))


def receipt_input_paths(receipt: dict):
    """Recorded input paths of a (already loaded) receipt dict."""
    if not isinstance(receipt, dict):
        return []
    return [item['path'] for item in receipt.get('inputs', [])
            if isinstance(item, dict) and isinstance(item.get('path'), str)]


def validate_receipt(receipt_path, station, phase=None, expected_inputs=None) -> dict:
    """Validate a receipt file; returns {'valid': bool, 'reason': str}.

    - header completeness / types / enums (reportVersion==1 enforced)
    - station: receipt.station must equal `station`
    - phase: when `phase` is given, receipt.phase must equal it; an
      'incremental' receipt can never substitute for 'final'
    - expected_inputs: when given (iterable of paths), each file is re-hashed and
      compared with the receipt record; any mismatch or missing file = stale and
      is named in the reason. Relative paths are folded by trying, in order,
      against the process cwd, the receipt's own dir, and the receipt dir's
      parent; the first candidate that exists as a file wins and is returned
      fully resolved (so `..` segments fold and different spellings of the same
      file share one key). Absolute paths are returned unchanged.
    """
    path = Path(receipt_path)
    if not path.exists():
        return {'valid': False, 'reason': 'receipt not found: %s' % path}
    try:
        receipt = load_receipt(path)
    except Exception as e:  # unreadable / invalid JSON
        return {'valid': False, 'reason': 'receipt unreadable: %s' % e}
    if not isinstance(receipt, dict):
        return {'valid': False, 'reason': 'receipt root must be a JSON object'}

    problems = _validate_head(receipt)
    if problems:
        return {'valid': False, 'reason': '; '.join(problems)}

    if receipt.get('station') != station:
        return {'valid': False,
                'reason': 'station mismatch: receipt.station=%r, expected %r'
                          % (receipt.get('station'), station)}

    if phase is not None:
        receipt_phase = receipt.get('phase')
        if receipt_phase != phase:
            if receipt_phase == 'incremental' and phase == 'final':
                return {'valid': False,
                        'reason': 'phase mismatch: incremental receipt cannot substitute final'}
            return {'valid': False,
                    'reason': 'phase mismatch: receipt.phase=%r, expected %r'
                              % (receipt_phase, phase)}

    if expected_inputs is not None:
        base = path.resolve().parent

        def norm(value):
            # Axis-B fix (V01 finding B): the same file can be spelled relative
            # to the process cwd, the receipt's own dir, or the receipt dir's
            # parent. Try these in order and keep the first candidate that
            # exists as a file, fully resolved — `..` segments fold and all
            # spellings of one existing file collapse to a single comparable
            # key. Absolute paths stay untouched (frozen behavior); when no
            # candidate exists the cwd-relative join is the deterministic key
            # so a same-form missing file still reports stale, not unrecorded.
            p = Path(str(value))
            if p.is_absolute():
                return str(p)
            for cand in (Path.cwd() / p, base / p, base.parent / p):
                if cand.is_file():
                    return str(cand.resolve())
            return str(Path.cwd() / p)

        recorded = {}
        for item in receipt['inputs']:
            recorded[norm(item['path'])] = item['sha256']
        unrecorded = []
        stale = []
        for entry in expected_inputs:
            key = norm(entry)
            if key not in recorded:
                unrecorded.append(str(entry))
                continue
            f = Path(key)
            if not f.exists():
                stale.append('%s (missing on disk)' % entry)
            elif file_sha256(f) != recorded[key]:
                stale.append(str(entry))
        if unrecorded:
            return {'valid': False,
                    'reason': 'input not recorded in receipt: ' + ', '.join(unrecorded)}
        if stale:
            return {'valid': False, 'reason': 'stale: ' + ', '.join(stale)}

    return {'valid': True, 'reason': 'ok'}


# ---------------------------------------------------------------- --make CLI（回执构造器）
def _cli_make(argv):
    """python qa_receipt.py --make --station S --kind K --result R --inputs a.html,b.json
                      --out qa/u5.json [--phase ph] [--scope p1,p2] [--note 文本]

    回执构造器：U1/U2/U3 的回执由对应检查器产出；本 CLI 服务两类场景——
    1) 检查器无产出能力的站（如 U5 档⑤"声明交付"：用户明示放弃检查，回执 result=passed、
       coverage.suite='delivery-declared-unchecked'，state_check disposition=skipped 会把质量
       评级降为 unverified——声明≠验证，U6 --require 按 skipped 级裁过程充分性）；
    2) 文档配方需要最小可复制的构造通道（免去手写 inputDigest 拼接规则）。
    inputs 自动逐文件 sha256 + bundle_digest；相对路径 ns='project/'。exit 0=写出 / 2=参数或IO。"""
    import argparse
    ap = argparse.ArgumentParser(prog='qa_receipt.py --make', add_help=True)
    ap.add_argument('--make', action='store_true', dest='make')
    ap.add_argument('--station', required=True)
    ap.add_argument('--kind', required=True, choices=sorted(KINDS))
    ap.add_argument('--result', required=True, choices=sorted(RESULTS))
    ap.add_argument('--inputs', required=True, help='逗号分隔的文件路径（各自 sha256 后入 inputs）')
    ap.add_argument('--out', required=True, help='回执输出路径')
    ap.add_argument('--phase', default=None, choices=sorted(PHASES))
    ap.add_argument('--scope', default=None, help='逗号分隔 pageId')
    ap.add_argument('--note', default=None, help='写入 coverage.note 的说明文本')
    a = ap.parse_args(argv)
    paths = [s.strip() for s in a.inputs.split(',') if s.strip()]
    if not paths:
        print('FAIL --inputs 至少一个文件'); return 2
    items = []
    recs = []
    for raw in paths:
        pp = Path(raw)
        if not pp.is_file():
            print('FAIL input not found: %s' % raw); return 2
        # 修复：inputs[].path 记录原始传入路径（旧写法剥成纯文件名，state_check 折算失败报 stale）
        items.append(('project/', raw, str(pp)))
        recs.append({'path': str(pp), 'sha256': file_sha256(str(pp))})
    head = {
        'reportVersion': 1, 'checkerVersion': 'qa_receipt-make/1.0.0',
        'kind': a.kind, 'station': a.station, 'phase': a.phase,
        'scope': ([s.strip() for s in a.scope.split(',') if s.strip()] or None) if a.scope else None,
        'inputDigest': bundle_digest(items),
        'inputs': recs,
        'result': a.result, 'findings': [],
        'coverage': {'madeBy': 'qa_receipt --make', 'note': a.note},
        'generatedAt': datetime.now(timezone.utc).isoformat(),
    }
    try:
        rec = make_receipt(**head)
    except ValueError as e:
        print('FAIL %s' % e); return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + chr(10), encoding='utf-8')
    print('receipt written: %s' % out.resolve())
    return 0


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--make':
        sys.exit(_cli_make(sys.argv[2:]))
    print('usage: python qa_receipt.py --make --station S --kind K --result R --inputs f1,f2 --out p [--phase ph] [--scope p1,p2] [--note txt]')
    sys.exit(2)
