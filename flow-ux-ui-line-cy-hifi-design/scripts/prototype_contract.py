"""prototype_contract — T02.1 第一批（G）：契约解析 Module。

职责边界（冻结单 T00 §1/§3）：
  - parse_fence:      全文恰一个 ```prototype-contract 围栏 + JSON 解析 + schema 校验
  - parse_claims:     第 6 节围栏内逐行 JSON claim 校验
  - loadContract:     整合 + pages_root 片段对账（E-ID 层）
  - write_derived:    派生件 qa/contract.json（Node 只消费带源摘要的派生件）
  - CLI:              exit 0=有效 / 1=契约错误 / 2=用法或IO

不归本模块（第二批 build.py）：E-ACT-* / E-STYLE-* / E-ID-EID-MISSING / E-FEATURE-UNCOVERED。
纯 stdlib + qa_receipt.file_sha256；禁 import build。
"""
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from qa_receipt import file_sha256

__all__ = ['parse_fence', 'parse_claims', 'loadContract', 'write_derived', 'main']

SCHEMA_VERSION = 1
DEVICES = ('mobile', 'tablet', 'desktop')
FEATURE_KINDS = ('interactive', 'display')
ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')
FENCE_LANG = 'prototype-contract'
SECTION6_RE = re.compile(r'^\s*#{1,6}\s*6(?:\D|$)')
REQUIRED_EXCEPTION_KEYS = ('id', 'page', 'target', 'property', 'reason', 'confirmationRef')
REQUIRED_CLAIM_FIELDS = ('claimId', 'page', 'eid', 'action', 'expect', 'steps', 'assert')

USAGE = """usage: python prototype_contract.py <intake.md> [--pages <dir>] [--out qa/contract.json]
  <intake.md>   开工文档（全文恰一个 ```prototype-contract 围栏 + 第6节交互声明）
  --pages <dir> 片段目录；给定时做片段对账（data-screen / data-eid / decorative / 未声明页）
  --out <path>  派生件输出路径（默认 <intake 所在目录>/qa/contract.json）
exit: 0=有效 / 1=契约错误 / 2=用法或IO
错误输出格式：ruleId:file:line:message"""


def _err(rule_id, file, line, message):
    return {'ruleId': rule_id, 'file': str(file), 'line': line, 'message': message}


# ---------------------------------------------------------------- fence 扫描

def _scan_fence(lines, start):
    """从 start(0-based) 行起收集一个已开启围栏；返回 (content_lines, close_idx|None)。"""
    j = start
    n = len(lines)
    while j < n and not lines[j].strip().startswith('```'):
        j += 1
    return lines[start:j], (j if j < n else None)


def _find_fences(md_text, lang):
    """全文所有 ```lang 围栏：[{openLine, content, contentStart, closeLine}]（行号 1-based）。"""
    lines = md_text.splitlines()
    fences = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith('```') and stripped[3:].strip() == lang:
            content, close_idx = _scan_fence(lines, i + 1)
            fences.append({'openLine': i + 1, 'content': '\n'.join(content),
                           'contentStart': i + 2,
                           'closeLine': (close_idx + 1) if close_idx is not None else None})
            i = (close_idx + 1) if close_idx is not None else len(lines)
        else:
            i += 1
    return fences


def _find_section6_fence(md_text):
    """定位第 6 节交互声明围栏；返回 {openLine, contentLines, contentStart, closeLine} 或 None。

    口径与 verify-interactions.mjs 对齐（N8 修复）：优先匹配 ```interaction-claims 语言标记围栏；
    §6 内无该标记围栏时才回退到首个任意围栏（兼容旧文档），并在返回值标 fallback=True 供调用方提示。"""
    lines = md_text.splitlines()
    for i, ln in enumerate(lines):
        if SECTION6_RE.match(ln):
            j = i + 1
            fallback = None
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith('```'):
                    if s[3:].strip() == 'interaction-claims':
                        content, close_idx = _scan_fence(lines, j + 1)
                        return {'openLine': j + 1, 'contentLines': content, 'contentStart': j + 2,
                                'closeLine': (close_idx + 1) if close_idx is not None else None,
                                'fallback': False}
                    if fallback is None:
                        content, close_idx = _scan_fence(lines, j + 1)
                        fallback = {'openLine': j + 1, 'contentLines': content, 'contentStart': j + 2,
                                    'closeLine': (close_idx + 1) if close_idx is not None else None,
                                    'fallback': True}
                    j = (close_idx + 1) if close_idx is not None else j + 1
                else:
                    j += 1
            return fallback
    return None


# ---------------------------------------------------------------- schema 校验

def _check_path(path):
    """E-PATH-ESCAPE 规则：项目内相对 posix、.html 后缀、禁 ../绝对/空段。违规返回原因，合法返回 None。"""
    if not isinstance(path, str) or not path.strip():
        return 'must be a non-empty string'
    if '\\' in path:
        return 'must use posix "/" separators (backslash forbidden)'
    if path.startswith('/') or re.match(r'^[A-Za-z]:', path):
        return 'must be project-relative (absolute path forbidden)'
    parts = path.split('/')
    if any(p in ('', '.', '..') for p in parts):
        return "must be a normalized relative path ('..', '.' and empty segments forbidden)"
    if not path.endswith('.html'):
        return 'must end with .html'
    return None


def _validate_contract(c, errors, source, line):
    """冻结单 §1 契约 schema。schema 类违规统一 E-CONTRACT-SCHEMA，专码见词表。"""
    def add(rule_id, msg):
        errors.append(_err(rule_id, source, line, msg))

    sv = c.get('schemaVersion')
    if isinstance(sv, bool) or not isinstance(sv, int) or sv != SCHEMA_VERSION:
        add('E-CONTRACT-SCHEMA', 'schemaVersion must be int %d, got %r' % (SCHEMA_VERSION, sv))
    rev = c.get('revision')
    if not isinstance(rev, str) or not rev.strip():
        add('E-CONTRACT-SCHEMA', 'revision must be a non-empty string')

    pages = c.get('pages')
    if not isinstance(pages, list) or not pages:
        add('E-CONTRACT-SCHEMA', 'pages must be a list with at least 1 page')
        pages = []
    seen_page_ids = {}
    seen_paths = {}
    feature_owner = {}
    for idx, page in enumerate(pages):
        if not isinstance(page, dict):
            add('E-CONTRACT-SCHEMA', 'pages[%d] must be an object' % idx)
            continue
        pid = page.get('id')
        if not isinstance(pid, str) or not ID_RE.match(pid):
            add('E-CONTRACT-SCHEMA',
                'pages[%d].id %r must match ^[a-zA-Z0-9_-]+$' % (idx, pid))
        if isinstance(pid, str) and pid:
            if pid in seen_page_ids:
                add('E-ID-PAGE-DUP', 'page id %r duplicated (first at pages[%d])'
                    % (pid, seen_page_ids[pid]))
            else:
                seen_page_ids[pid] = idx
        perr = _check_path(page.get('path'))
        if perr:
            add('E-PATH-ESCAPE', 'pages[%d].path %r: %s' % (idx, page.get('path'), perr))
        elif isinstance(page.get('path'), str):
            norm = Path(page['path']).as_posix()
            if norm in seen_paths:
                add('E-PATH-DUP', 'page path %r duplicated (first on page %r)'
                    % (page['path'], seen_paths[norm]))
            else:
                seen_paths[norm] = page.get('id')
        if page.get('device') not in DEVICES:
            add('E-CONTRACT-SCHEMA', 'pages[%d].device %r must be one of %s'
                % (idx, page.get('device'), list(DEVICES)))
        resp = page.get('responsibility')
        if not isinstance(resp, str) or not resp.strip():
            add('E-CONTRACT-SCHEMA', 'pages[%d].responsibility must be a non-empty string' % idx)
        features = page.get('features')
        if not isinstance(features, list):
            add('E-CONTRACT-SCHEMA', 'pages[%d].features must be a list' % idx)
            features = []
        for fidx, feat in enumerate(features):
            if not isinstance(feat, dict):
                add('E-CONTRACT-SCHEMA', 'pages[%d].features[%d] must be an object' % (idx, fidx))
                continue
            fid = feat.get('id')
            if not isinstance(fid, str) or not ID_RE.match(fid):
                add('E-CONTRACT-SCHEMA',
                    'pages[%d].features[%d].id %r must match ^[a-zA-Z0-9_-]+$' % (idx, fidx, fid))
            if isinstance(fid, str) and fid:
                if fid in feature_owner:
                    add('E-FEATURE-DUP', 'feature id %r duplicated (pages %r / %r)'
                        % (fid, feature_owner[fid], page.get('id')))
                else:
                    feature_owner[fid] = page.get('id')
            if feat.get('kind') not in FEATURE_KINDS:
                add('E-CONTRACT-SCHEMA', 'pages[%d].features[%d].kind %r must be one of %s'
                    % (idx, fidx, feat.get('kind'), list(FEATURE_KINDS)))

    excs = c.get('exceptions')
    if not isinstance(excs, list):
        add('E-CONTRACT-SCHEMA', 'exceptions must be a list (may be empty)')
        excs = []
    for eidx, exc in enumerate(excs):
        if not isinstance(exc, dict):
            add('E-CONTRACT-SCHEMA', 'exceptions[%d] must be an object' % eidx)
            continue
        missing = [k for k in REQUIRED_EXCEPTION_KEYS if k not in exc]
        if missing:
            add('E-CONTRACT-SCHEMA',
                'exceptions[%d] missing field(s): %s' % (eidx, ', '.join(missing)))


# ---------------------------------------------------------------- 公开 API 1

def parse_fence(md_text, source='<intake>'):
    """解析全文唯一 ```prototype-contract 围栏。

    返回 (contract_dict|None, errors[{ruleId,file,line,message}])。
    缺失→E-CONTRACT-FENCE-MISSING；重复→每个多余围栏一条 E-CONTRACT-FENCE-DUP；
    JSON/字段违规→E-CONTRACT-SCHEMA；页面/路径/功能专码见词表。
    """
    errors = []
    fences = _find_fences(md_text, FENCE_LANG)
    if not fences:
        errors.append(_err('E-CONTRACT-FENCE-MISSING', source, 0,
                           'missing ```prototype-contract fence (must appear exactly once)'))
        return None, errors
    for extra in fences[1:]:
        errors.append(_err('E-CONTRACT-FENCE-DUP', source, extra['openLine'],
                           'duplicate ```prototype-contract fence (exactly one allowed)'))
    fence = fences[0]
    if fence['closeLine'] is None:
        errors.append(_err('E-CONTRACT-SCHEMA', source, fence['openLine'],
                           'prototype-contract fence is not closed'))
    try:
        contract = json.loads(fence['content'])
    except json.JSONDecodeError as e:
        line = fence['contentStart'] + fence['content'][:e.pos].count('\n')
        errors.append(_err('E-CONTRACT-SCHEMA', source, line,
                           'contract JSON parse error: %s' % e.msg))
        return None, errors
    if not isinstance(contract, dict):
        errors.append(_err('E-CONTRACT-SCHEMA', source, fence['contentStart'],
                           'contract root must be a JSON object'))
        return None, errors
    _validate_contract(contract, errors, source, fence['contentStart'])
    return contract, errors


# ---------------------------------------------------------------- 公开 API 2

def _feature_index(contract):
    """{featureId: kind}；contract 不可用时返回 {}。"""
    if not isinstance(contract, dict):
        return {}
    index = {}
    for page in contract.get('pages') or []:
        if not isinstance(page, dict):
            continue
        for feat in page.get('features') or []:
            if isinstance(feat, dict) and isinstance(feat.get('id'), str):
                index[feat['id']] = feat.get('kind')
    return index


def _page_ids(contract):
    if not isinstance(contract, dict):
        return set()
    return {p['id'] for p in contract.get('pages') or []
            if isinstance(p, dict) and isinstance(p.get('id'), str)}


def parse_claims(md_text, contract=None, source='<intake>'):
    """解析第 6 节围栏内逐行 JSON claim。

    返回 (claims_list, badLines[{line,ruleId,message}])（行号为 md 全文 1-based）。
    contract 为 None 时内部调 parse_fence；仍为 None（围栏层已报错）则跳过
    contract 依赖检查，避免重复刷屏。
    """
    bad_lines = []
    fence = _find_section6_fence(md_text)
    if fence is None:
        bad_lines.append({'line': 0, 'ruleId': 'E-CONTRACT-SCHEMA',
                          'message': 'section 6 claims fence not found '
                                     '(需「## 6.」标题后紧跟 ```json 围栏)'})
        return [], bad_lines
    if contract is None:
        contract, _ = parse_fence(md_text, source=source)
    strict = isinstance(contract, dict)
    feature_index = _feature_index(contract)
    page_ids = _page_ids(contract)

    claims = []
    seen_ids = {}
    for offset, raw in enumerate(fence['contentLines']):
        line_no = fence['contentStart'] + offset
        text = raw.strip()
        if not text:
            continue

        def bad(rule_id, message):
            bad_lines.append({'line': line_no, 'ruleId': rule_id, 'message': message})

        try:
            claim = json.loads(text)
        except json.JSONDecodeError as e:
            bad('E-CONTRACT-SCHEMA', 'claim JSON parse error: %s' % e.msg)
            continue
        if not isinstance(claim, dict):
            bad('E-CONTRACT-SCHEMA', 'claim line must be a JSON object')
            continue
        missing = [f for f in REQUIRED_CLAIM_FIELDS if f not in claim]
        if missing:
            bad('E-CONTRACT-SCHEMA', 'claim missing field(s): %s' % ', '.join(missing))
            continue
        cid = claim['claimId']
        if not isinstance(cid, str) or not cid.strip():
            bad('E-CONTRACT-SCHEMA', 'claimId must be a non-empty string')
            continue
        if cid in seen_ids:
            bad('E-CONTRACT-SCHEMA',
                'claimId %r duplicated (first at line %d)' % (cid, seen_ids[cid]))
        else:
            seen_ids[cid] = line_no

        decorative = claim.get('decorative') is True
        feature_ids = claim.get('featureIds')
        if not isinstance(feature_ids, list):
            feature_ids = None
        if strict:
            if not decorative and (feature_ids is None or not feature_ids):
                bad('E-CLAIM-REF-UNKNOWN',
                    'non-decorative claim must declare non-empty featureIds')
            for fid in feature_ids or []:
                if fid not in feature_index:
                    bad('E-CLAIM-REF-UNKNOWN',
                        'featureIds item %r not declared in contract.features[].id' % (fid,))
            page = claim.get('page')
            if not (isinstance(page, str) and page in page_ids):
                bad('E-CLAIM-REF-UNKNOWN',
                    'claim page %r not declared in contract.pages[].id' % (page,))

        kinds = {feature_index[f] for f in (feature_ids or []) if f in feature_index}
        steps = claim['steps']
        asserts = claim['assert']
        steps_ok = (isinstance(steps, list) and len(steps) > 0
                    and all(isinstance(s, list) and s
                            and all(isinstance(x, str) and x.strip() for x in s)
                            for s in steps))
        asserts_ok = (isinstance(asserts, list) and len(asserts) > 0
                      and all(isinstance(a, str) and a.strip() for a in asserts))
        if not asserts_ok:
            bad('E-CLAIM-ASSERT-EMPTY', 'claim must carry at least one non-empty assert')
        if strict and 'interactive' in kinds and not steps_ok:
            bad('E-CLAIM-ASSERT-EMPTY',
                'claim covering interactive feature(s) needs >=1 non-empty steps '
                '(display 允许 steps=[])')
        claims.append(claim)
    return claims, bad_lines


# ---------------------------------------------------------------- 片段对账

class _FragmentParser(HTMLParser):
    """片段扫描：首个 section 的 data-screen、全部 data-eid 出现点（含是否携带 data-on）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.first_screen = None          # (value, line) or None
        self.eids = []                    # [(eid, line, has_data_on)]

    def handle_starttag(self, tag, attrs):
        amap = {}
        for k, v in attrs:
            amap.setdefault(k, v)
        line = self.getpos()[0]
        if self.first_screen is None and tag == 'section' and 'data-screen' in amap:
            self.first_screen = (amap.get('data-screen'), line)
        eid = amap.get('data-eid')
        if eid:
            self.eids.append((eid, line, 'data-on' in amap))


def _reconcile_pages(loaded, pages_root, doc_dir):
    """pages_root 片段对账（E-ID 层，仅本批规则）。"""
    errors = loaded['errors']
    contract = loaded['contract']
    pages = contract.get('pages') if isinstance(contract, dict) else None
    pages = pages if isinstance(pages, list) else []
    claims = loaded['claims']

    def resolve(page):
        path = page.get('path')
        if not isinstance(path, str) or not path:
            return None
        for cand in (pages_root / path, pages_root / Path(path).name, doc_dir / path):
            if cand.is_file():
                return cand
        return None

    declared_keys = set()
    resolved = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        pid = page.get('id')
        path = page.get('path')
        if isinstance(path, str) and path:
            declared_keys.add(Path(path).as_posix())
            declared_keys.add(Path(path).name)
        f = resolve(page)
        if f is None:
            errors.append(_err('E-ID-PAGE-UNDECLARED',
                               Path(str(path) if path else pid).as_posix(), 0,
                               "contract page %r declared but fragment file missing "
                               "(path=%r not found; 注明missing)" % (pid, path)))
        else:
            resolved.append((page, f))

    for page, f in resolved:
        pid = page.get('id')
        parser = _FragmentParser()
        try:
            parser.feed(f.read_text(encoding='utf-8-sig'))
        except (OSError, UnicodeDecodeError) as e:
            errors.append(_err('E-CONTRACT-SCHEMA', str(f), 0, 'fragment unreadable: %s' % e))
            continue
        if parser.first_screen is None:
            errors.append(_err('E-CONTRACT-SCHEMA', str(f), 0,
                               "page %r fragment has no <section data-screen>" % (pid,)))
        else:
            value, sline = parser.first_screen
            if value != pid:
                errors.append(_err('E-CONTRACT-SCHEMA', str(f), sline,
                                   "page %r fragment first section data-screen=%r != page id "
                                   "(具名页不符)" % (pid, value)))
        by_eid = {}
        for eid, line, has_on in parser.eids:
            by_eid.setdefault(eid, []).append((line, has_on))
        for eid, occ in by_eid.items():
            if len(occ) > 1:
                for line, _has_on in occ:
                    errors.append(_err('E-ID-EID-DUP', str(f), line,
                                       "data-eid %r appears %d times in this fragment "
                                       "(逐条定位，不得只报第一处)" % (eid, len(occ))))
        for claim in claims:
            if claim.get('decorative') is not True or claim.get('page') != pid:
                continue
            eid = claim.get('eid')
            for line, has_on in by_eid.get(eid, []):
                if has_on:
                    errors.append(_err('E-DECOR-ACTION', str(f), line,
                                       "decorative claim %r targets eid %r which carries "
                                       "data-on (装饰藏动作→失败)" % (claim.get('claimId'), eid)))

    if pages_root.is_dir():
        for html in sorted(pages_root.rglob('*.html')):
            rel = html.relative_to(pages_root).as_posix()
            if rel in declared_keys or html.name in declared_keys:
                continue
            errors.append(_err('E-ID-PAGE-UNDECLARED', rel, 0,
                               'fragment exists under pages_root but is not declared '
                               'in contract.pages[].path'))


def _source_locations(text):
    """契约围栏与每条 claim 的源位置（供派生件溯源）。"""
    loc = {}
    fences = _find_fences(text, FENCE_LANG)
    if fences:
        f0 = fences[0]
        loc['contractFence'] = {'start': f0['openLine'], 'contentStart': f0['contentStart'],
                                'end': f0['closeLine']}
    fence = _find_section6_fence(text)
    if fence is not None:
        claim_map = {}
        for offset, raw in enumerate(fence['contentLines']):
            t = raw.strip()
            if not t:
                continue
            try:
                c = json.loads(t)
            except json.JSONDecodeError:
                continue
            if isinstance(c, dict) and isinstance(c.get('claimId'), str):
                claim_map[c['claimId']] = fence['contentStart'] + offset
        loc['claimsSection'] = {'fenceStart': fence['openLine'],
                                'fenceEnd': fence['closeLine']}
        loc['claims'] = claim_map
    return loc


# ---------------------------------------------------------------- 公开 API 3

def loadContract(doc_path, pages_root=None):
    """整合解析；pages_root 给定时做片段对账。

    返回 {contract, claims, errors, badLines, sourceHash, docPath, sourceLocations}。
    IO 错误向上抛 OSError（CLI 转换为 exit 2）。
    """
    doc_path = Path(doc_path)
    text = doc_path.read_text(encoding='utf-8-sig')
    source = str(doc_path)
    contract, errors = parse_fence(text, source=source)
    claims, bad_lines = parse_claims(text, contract=contract, source=source)
    loaded = {
        'contract': contract,
        'claims': claims,
        'errors': errors,
        'badLines': bad_lines,
        'sourceHash': file_sha256(doc_path),
        'docPath': source,
        'sourceLocations': _source_locations(text),
    }
    if pages_root is not None and contract is not None:
        _reconcile_pages(loaded, Path(pages_root), doc_path.parent)
    return loaded


# ---------------------------------------------------------------- 公开 API 4

def write_derived(out_path, loaded):
    """写派生件 qa/contract.json（Node 消费）。errors 非空时不写并返回 False。"""
    errors = loaded.get('errors') or []
    if errors:
        return False
    contract = loaded.get('contract') or {}
    by_rule = {}
    for e in errors:
        by_rule[e['ruleId']] = by_rule.get(e['ruleId'], 0) + 1
    bad_lines = loaded.get('badLines') or []
    payload = {
        'schemaVersion': SCHEMA_VERSION,
        'sourceHash': loaded.get('sourceHash'),
        'source': loaded.get('docPath'),
        'revision': contract.get('revision'),
        'pages': contract.get('pages', []),
        'claims': loaded.get('claims', []),
        'errors': {'total': len(errors), 'byRule': by_rule},
        'badLines': {'total': len(bad_lines)},
        'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')
    return True


# ---------------------------------------------------------------- CLI

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('-h', '--help'):
        print(USAGE)
        return 0
    if not argv:
        print(USAGE)
        return 2
    doc = Path(argv[0])
    pages_root = None
    out = None
    i = 1
    while i < len(argv):
        if argv[i] == '--pages' and i + 1 < len(argv):
            pages_root = Path(argv[i + 1])
            i += 2
        elif argv[i] == '--out' and i + 1 < len(argv):
            out = Path(argv[i + 1])
            i += 2
        else:
            print('usage error: unexpected argument %r' % (argv[i],))
            print(USAGE)
            return 2
    if not doc.is_file():
        print('IO error: intake not found: %s' % doc)
        return 2
    if out is None:
        out = doc.parent / 'qa' / 'contract.json'
    try:
        loaded = loadContract(doc, pages_root)
    except OSError as e:
        print('IO error: %s' % e)
        return 2
    for e in loaded['errors']:
        print('%s:%s:%s:%s' % (e['ruleId'], e['file'], e['line'], e['message']))
    for b in loaded['badLines']:
        print('%s:%s:%s:%s' % (b['ruleId'], loaded['docPath'], b['line'], b['message']))
    contract = loaded.get('contract') or {}
    pages = contract.get('pages') or []
    n_features = sum(len(p.get('features') or []) for p in pages if isinstance(p, dict))
    if not loaded['errors'] and not loaded['badLines']:
        if write_derived(out, loaded):
            print('OK: pages=%d features=%d claims=%d -> derived %s'
                  % (len(pages), n_features, len(loaded['claims']), out))
        else:
            print('derived not written (errors)')
        return 0
    print('FAIL: errors=%d badLines=%d (derived not written)'
          % (len(loaded['errors']), len(loaded['badLines'])))
    return 1


if __name__ == '__main__':
    sys.exit(main())
