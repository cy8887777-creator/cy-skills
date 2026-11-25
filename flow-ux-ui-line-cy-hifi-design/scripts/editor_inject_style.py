# -*- coding: utf-8 -*-
"""editor_inject_style v2 — 屏集合组架构的第二风格注入（multi-style-spec v2 回装侧）

规格正本：references/multi-style-spec.md §一/§三/§四（v2 屏集合组：每风格一套 section.screen
集合，挂 data-style-id；屏内单容器；页数跨风格可不守恒；页面树按风格独立分组表）。
v1 的"屏内 [data-dom-base] 双容器"机制已废弃——产物含双容器形态=拒绝并提示按 v2 重放。

  python editor_inject_style.py --target <产物.html> --fragments <B片段目录> \
    --style-blocks <style-blocks.json> --db db-polaris --pack-id pk-b \
    [--screens polaris-p01-login,...] [--src-db db-main] [--out <out.html>]

--fragments 形态 = editor_convert 产出（<style id="pilot-page-css"> + <section ...>），
业务 CSS 必须带 [data-style-id="<风格id>"] 域前缀（规格 §三/§四：裸样式全局互压=违规）。
--db 值域 = domBaseId（与 REGISTRY.domBases/family.domBaseId 同值，壳桥 applyDomBase 直通）。
页 id 规则（规格 §一）：B 屏页 id 注入时统一加风格段前缀（<short>-<语义id>），原风格页 id
保持原样；data-on goto 引用同步改写（目标必须都在 B 片段内，跨段引用=拒绝）。

流程：备份 → 对账（页 id 唯一性；页数不守恒合法）→ 产物 v1 双容器检测（拒绝）
→ 既有页面 CSS 补源风格域前缀 + 源屏回填 data-style-id → B 片段页 id 前缀化
→ B 屏 append 到 canvas 末尾（初始 display:none，壳 __spApplyStyleScreens 接管）
→ pageTree 单映射扩分组表并追加新风格段 → B 片段 CSS 注入 head → 受控块合并（查重）
→ 自检（style-id 全覆盖/无 dom-base 残留/四块/配平/eid/sprite/隐藏）→ 落盘。
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_ID_RE = re.compile(r'^db-[A-Za-z0-9_-]+$')
PLAIN_ID_RE = re.compile(r'^[A-Za-z0-9_-]+$')
BLOCK_NAMES = ('STYLE-REGISTRY', 'STYLE-PACK', 'COMPONENT-PACK', 'STYLE-CONTRACT')
BLOCK_RE = {
    name: re.compile('<script\\b[^>]*\\bdata-block=["\']' + name + '["\'][^>]*>([\\s\\S]*?)</script>', re.I)
    for name in BLOCK_NAMES
}
SCREEN_OPEN_RE = re.compile(r'<section\b[^>]*\bdata-screen="([A-Za-z0-9_-]+)"[^>]*>')
PILOT_PAGE_CSS_RE = re.compile('(<style\\b[^>]*\\bid=["\']pilot-page-css["\'][^>]*>)([\\s\\S]*?)(</style>)', re.I)
SYMBOL_ID_RE = re.compile('<symbol\\b[^>]*\\bid=["\']([^"\']+)["\'][^>]*>', re.I)
USE_REF_RE = re.compile('(?:href|xlink:href)=["\']#([A-Za-z0-9_-]+)["\']')
PAGE_TREE_RE = re.compile('(<script\\b[^>]*\\bid=["\']prototype-page-tree["\'][^>]*>)([\\s\\S]*?)(</script>)', re.I)
GOTO_VAL_RE = re.compile('(&quot;goto&quot;:&quot;)([A-Za-z0-9_-]+)(&quot;)')


def die(msg, code=1):
    print('FAIL ' + msg)
    raise SystemExit(code)


def note(msg):
    print('NOTE ' + msg)


def dump_json(v):
    """受控块序列化：与 build.py 同口径（ensure_ascii=False，< 转义 \u003c 字面）。"""
    return json.dumps(v, ensure_ascii=False).replace('<', '\\u003c')


# ---------------------------------------------------------------- 标签配平
def match_balanced(text, open_end, tag):
    """从开标签终点起扫描，返回配平闭标签的 (起点, 终点exclusive)。自闭合不进栈。"""
    pat_open = re.compile('<%s\\b[^>]*?(/?)>' % tag, re.I)
    pat_close = re.compile('</%s\\s*>' % tag, re.I)
    depth = 1
    pos = open_end
    while depth > 0:
        mo = pat_open.search(text, pos)
        mc = pat_close.search(text, pos)
        if mc is None:
            return None
        if mo and mo.start() < mc.start():
            if not mo.group(1):
                depth += 1
            pos = mo.end()
            continue
        depth -= 1
        if depth == 0:
            return mc.start(), mc.end()
        pos = mc.end()
    return None


def span_of_screen(text, start):
    open_end = text.index('>', start) + 1
    end = match_balanced(text, open_end, 'section')
    if end is None:
        return None
    return open_end, end[1]


def brace_balance(css):
    return css.count('{') - css.count('}')


def split_rules(css):
    rules, depth, cur = [], 0, ''
    for ch in css:
        cur += ch
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                rules.append(cur)
                cur = ''
    if cur.strip():
        rules.append(cur)
    return rules


def upgrade_css_scope(css, style_id):
    """业务 CSS 逐条挂风格域：.screen X → .screen [data-style-id="<id>"] X（规格 §三）。
    已带域前缀的 seg 幂等跳过；@keyframes 原样；@media 递归内层。"""
    dom = '[data-style-id="%s"]' % style_id
    warns = []

    def up_rule(rule):
        s = rule.strip()
        if s.startswith('@keyframes'):
            return s
        if s.startswith('@media'):
            head, rest = s.split('{', 1)
            inner = rest.rsplit('}', 1)[0]
            parts, depth, cur = [], 0, ''
            for ch in inner:
                cur += ch
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        parts.append(cur)
                        cur = ''
            return head + '{\n' + '\n'.join(up_rule(r) for r in parts if r.strip()) + '\n}'
        head, body = s.split('{', 1)
        segs = []
        for seg in head.split(','):
            seg = seg.strip()
            if not seg:
                continue
            if '[data-style-id=' in seg or '[data-dom-base=' in seg:
                segs.append(seg)
                continue
            if not seg.startswith('.screen'):
                warns.append(seg)
            segs.append(('.screen' + dom + ' ' + seg[len('.screen'):].strip()) if seg.startswith('.screen') else seg)  # v2 连写
        return ',\n'.join(segs) + ' {' + body

    out = []
    for r in split_rules(css):
        st = r.strip()
        if st.startswith('/* convert:') or not st:
            out.append(r)
            continue
        out.append(up_rule(r))
    return '\n'.join(out), warns


# ---------------------------------------------------------------- fragments
def read_fragments(frag_dir):
    """递归收集片段：{path, screen, section, group}（group=相对子目录=导航组名，v2 pageTree 段用）。"""
    files = sorted(frag_dir.rglob('*.html'), key=lambda p: str(p.relative_to(frag_dir)).lower())
    if not files:
        die('--fragments 目录无 .html 片段: %s' % frag_dir)
    items = []
    css_seen = {}
    for f in files:
        text = f.read_text(encoding='utf-8-sig')
        sm = SCREEN_OPEN_RE.search(text)
        if not sm:
            die('片段缺 data-screen section: %s' % f)
        screen = sm.group(1)
        if any(it['screen'] == screen for it in items):
            die('片段屏 id 重复: %s (%s)' % (screen, f))
        span = span_of_screen(text, sm.start())
        if span is None:
            die('片段 section 标签配平失败: %s' % f)
        rel = f.relative_to(frag_dir)
        group = rel.parent.as_posix() if rel.parent != Path('.') else ''
        for stm in re.finditer(r'<style\b([^>]*)>([\s\S]*?)</style>', text):
            attrs, css = stm.group(1), stm.group(2)
            idm = re.search('id=["\']([^"\']+)["\']', attrs)
            sid = idm.group(1) if idm else ''
            key = (sid, hashlib.sha256(css.encode('utf-8')).hexdigest()[:16])
            if key not in css_seen:
                css_seen[key] = {'id': sid, 'css': css}
        items.append({'path': f, 'screen': screen, 'section': text[sm.start():span[1]], 'group': group})
    return items, list(css_seen.values())


def extract_blocks(text):
    out = {}
    for name, pat in BLOCK_RE.items():
        ms = pat.findall(text)
        if len(ms) > 1:
            die('产物受控块 %s 出现 %d 次（应恰 1）——产物已被注入过或已损坏' % (name, len(ms)))
        if ms:
            try:
                out[name] = json.loads(ms[0])
            except Exception as e:
                die('产物受控块 %s JSON 不可解析: %s' % (name, e))
    return out


def strip_blocks_span(text):
    t = text
    for pat in BLOCK_RE.values():
        t = pat.sub('<script data-x="stripped"></script>', t)
    return t


def canvas_span(text):
    m = re.search(r'<main\b[^>]*\bid=["\']canvas["\'][^>]*>', text)
    if not m:
        die('产物缺 <main id="canvas">')
    pair = match_balanced(text, m.end(), 'main')
    if pair is None:
        die('canvas main 标签配平失败')
    return m.end(), pair[0]


def canvas_body(text):
    a, b = canvas_span(text)
    return text[a:b]


def file_to_data_uri(path):
    """封面文件 → data URI（svg=svg+xml;base64；png/jpg=image/jpeg|png;base64）。"""
    p = Path(path)
    if not p.is_file():
        die('封面文件不存在: %s' % p)
    ext = p.suffix.lower().lstrip('.')
    mime = {'svg': 'image/svg+xml', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}.get(ext)
    if not mime:
        die('封面格式不支持（svg/png/jpg）: %s' % p)
    import base64
    b64 = base64.b64encode(p.read_bytes()).decode('ascii')
    return 'data:%s;base64,%s' % (mime, b64)


def apply_covers(sb, blocks, db_id, pack_id, args):
    """封面供给（用户裁决 2026-11-23：面板卡缩略禁色板条降级）：
    新风格 pack.screenshot=--cover data URI（库卡=wiki cover.svg/自创=手绘 SVG）；
    原 pack.screenshot=--src-shot data URI（playwright 设备框内截帧）。"""
    report = []
    cover_uri = file_to_data_uri(args.cover) if args.cover else None
    if cover_uri and len(cover_uri) > 20000:
        note('新风格封面 data URI %d 字符偏大（建议 SVG <5KB 源文件）' % len(cover_uri))
    shot_uri = file_to_data_uri(args.src_shot) if args.src_shot else None
    # 新风格 pack（merge 前写在 sb 上，随 packs append 进产物）
    if cover_uri:
        sb_pack = [p for p in (sb.get('STYLE-PACK', {}).get('packs') or []) if p.get('packId') == pack_id]
        if not sb_pack:
            die('--cover 注入失败：--style-blocks 里没有 packId=%s' % pack_id)
        sb_pack[0]['screenshot'] = cover_uri
        report.append('新风格封面 += %s (%d 字符)' % (pack_id, len(cover_uri)))
    elif args.cover:
        pass
    # 原 pack（merge 后在产物 blocks 上补）
    if shot_uri:
        packs = blocks['STYLE-PACK'].setdefault('packs', [])
        cand = ([p for p in packs if p.get('packId') == args.src_pack_id] if args.src_pack_id
                else [p for p in packs if not (p.get('builtin') and p.get('builtin', {}).get('id') == 'original')])
        if not cand:
            die('--src-shot 注入失败：产物 packs 里找不到原风格包（--src-pack-id=%s）' % (args.src_pack_id or '缺省'))
        cand[0]['screenshot'] = shot_uri
        report.append('原风格封面 += %s (%d 字符)' % (cand[0].get('packId'), len(shot_uri)))
    return report


def merge_blocks(blocks, sb, db_id, pack_id, pages):
    """受控块合并（规格 §四：schema 零变更）：packId/familyId/domBaseId/compId 全局唯一查重。"""
    report = []
    reg = blocks['STYLE-REGISTRY']
    packs_block = blocks['STYLE-PACK']
    comp = blocks['COMPONENT-PACK']

    dom_bases = reg.setdefault('domBases', [])
    if db_id in [d.get('domBaseId') for d in dom_bases]:
        die('domBaseId 撞车: %s 已在产物 STYLE-REGISTRY.domBases' % db_id)
    new_db = [d for d in (sb.get('STYLE-REGISTRY', {}).get('domBases') or []) if d.get('domBaseId') == db_id]
    if len(new_db) != 1:
        die('--style-blocks 的 STYLE-REGISTRY.domBases 里 domBaseId=%s 的成员恰需 1 个（实得 %d）'
            % (db_id, len(new_db)))
    member = dict(new_db[0])
    member['pages'] = list(pages)
    dom_bases.append(member)
    report.append('domBases += %s (pages=%s)' % (db_id, ','.join(pages)))

    families = reg.setdefault('families', [])
    have_fam = [f.get('familyId') for f in families]
    new_fams = [dict(f) for f in (sb.get('STYLE-REGISTRY', {}).get('families') or []) if f.get('domBaseId') == db_id]
    for f in new_fams:
        fid = f.get('familyId')
        if not fid:
            die('新族缺 familyId: %r' % f)
        if fid in have_fam:
            die('familyId 撞车: %s 已在产物 STYLE-REGISTRY.families' % fid)

    packs = packs_block.setdefault('packs', [])
    have_pack = [p.get('packId') for p in packs]
    if pack_id in have_pack:
        die('packId 撞车: %s 已在产物 STYLE-PACK.packs' % pack_id)
    new_pack = [p for p in (sb.get('STYLE-PACK', {}).get('packs') or []) if p.get('packId') == pack_id]
    if len(new_pack) != 1:
        die('--style-blocks 的 STYLE-PACK.packs 里 packId=%s 的成员恰需 1 个（实得 %d）' % (pack_id, len(new_pack)))
    packs.append(dict(new_pack[0]))
    report.append('packs += %s' % pack_id)

    for f in new_fams:
        members = f.get('members') or []
        dangling = [m for m in members if m not in have_pack and m != pack_id]
        if dangling:
            die('新族 %s 的 members 引用悬空包: %s' % (f['familyId'], ','.join(dangling)))
        if pack_id not in members:
            die('新族 %s 的 members 未包含本次注入包 %s' % (f['familyId'], pack_id))
        families.append(dict(f))
        report.append('families += %s (domBaseId=%s)' % (f['familyId'], db_id))

    sb_comp = sb.get('COMPONENT-PACK')
    if sb_comp:
        comp_list = comp.setdefault('components', [])
        have_comp = [c.get('compId') for c in comp_list]
        added = 0
        for c in (sb_comp.get('components') or []):
            cid = c.get('compId')
            if cid in have_comp:
                die('compId 撞车: %s 已在产物 COMPONENT-PACK.components' % cid)
            comp_list.append(dict(c))
            have_comp.append(cid)
            added += 1
        report.append('COMPONENT-PACK.components += %d' % added)
    else:
        note('--style-blocks 无 COMPONENT-PACK 键，跳过组件包合并（面板沿用既有组件）')
    return report


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(
        description='inject a second style into a built single-file deliverable (multi-style-spec v2 屏集合组)')
    ap.add_argument('--target', required=True, help='已有产物 index.html')
    ap.add_argument('--fragments', required=True, help='新风格片段目录（editor_convert 产出形态）')
    ap.add_argument('--style-blocks', required=True, dest='style_blocks',
                    help='新风格受控块 JSON（build --style-blocks 同构；STYLE-CONTRACT 可缺）')
    ap.add_argument('--db', required=True, help='新风格屏集合 id（值域=domBaseId，^db-[A-Za-z0-9_-]+$）')
    ap.add_argument('--pack-id', required=True, dest='pack_id', help='本次注入的包 id（须在 --style-blocks packs 内）')
    ap.add_argument('--screens', default=None,
                    help='新风格页 id 清单（逗号分隔，前缀化后形态，对账基准；缺省=取 fragments 自身）')
    ap.add_argument('--src-db', default='db-main', dest='src_db',
                    help='原风格屏集合 id（源屏回填 data-style-id 用；缺省 db-main）')
    ap.add_argument('--cover', default=None, dest='cover',
                    help='新风格封面（svg/png/jpg → data URI 填 pack.screenshot；库卡=wiki cover.svg，自创=手绘 SVG，禁位图位面降级）')
    ap.add_argument('--src-shot', default=None, dest='src_shot',
                    help='原风格截帧图（png/jpg → data URI 填原 pack.screenshot——两张卡都不能是色板条降级）')
    ap.add_argument('--src-pack-id', default=None, dest='src_pack_id',
                    help='原风格 packId（缺省=产物 packs 里第一个非 builtin 包）')
    ap.add_argument('--out', default=None, help='输出文件（缺省回写 target）')
    args = ap.parse_args()

    target_path = Path(args.target)
    if not target_path.exists():
        die('--target 不存在: %s' % target_path)
    if not DB_ID_RE.match(args.db):
        die('--db 格式非法（须 ^db-[A-Za-z0-9_-]+$）: %s' % args.db)
    if not PLAIN_ID_RE.match(args.pack_id):
        die('--pack-id 格式非法: %s' % args.pack_id)
    if not DB_ID_RE.match(args.src_db):
        die('--src-db 格式非法: %s' % args.src_db)
    if args.db == args.src_db:
        die('--db 与 --src-db 同名（两风格屏集合 id 冲突）')
    short = args.db[len('db-'):]
    frag_dir = Path(args.fragments)
    if not frag_dir.is_dir():
        die('--fragments 不存在: %s' % frag_dir)
    try:
        _sb_raw = Path(args.style_blocks).read_text(encoding='utf-8-sig')
        if re.search(r'TODO', _sb_raw):
            die('style-blocks 含 TODO 占位（占位值进产物会让壳层 UI 读非法颜色而透明——2026-11-23 端到端实证）；'
                '请回 editor_gen_tokens 填真实语义值（design-system-converted.json 同查）后再注入')
        sb = json.loads(_sb_raw)
    except Exception as e:
        die('--style-blocks JSON 不可解析: %s' % e)

    target = target_path.read_text(encoding='utf-8')

    # ---- 0.预采集：产物既有风格域全集（v2 多次注入支持：自检合法域=既有域+本次新域，N≥3 注入不死）
    pre_style_ids = sorted(set(re.findall(r'data-style-id="([^"]+)"', target)))
    # 分域屏级计数（口径=屏开标签，与自检 per_ids 同源；排查 P0-3 补全：src/new 屏数对齐用）
    pre_domain_counts = {}
    for _sm in SCREEN_OPEN_RE.finditer(target):
        for _sv in re.findall(r'data-style-id="([^"]+)"', _sm.group(0)):
            pre_domain_counts[_sv] = pre_domain_counts.get(_sv, 0) + 1

    # ---- 0. 产物身份：受控块齐 + v1 双容器形态检测（规格 §七：半架构产物拒绝）
    blocks = extract_blocks(target)
    missing = [n for n in BLOCK_NAMES if n not in blocks]
    if missing:
        die('产物缺受控块 %s——目标产物不是现代 build 产出，拒绝注入' % ','.join(missing))
    c_span = canvas_span(target)
    if re.search(r'data-dom-base="', canvas_body(target)):
        die('产物屏内含 [data-dom-base] 容器（v1 半架构形态，multi-style-spec §七已废弃）'
            '——请还原备份后按 v2 重放（本工具 v2 只接受无 dom-base 标记的单容器产物）')
    if re.search(r'data-style-id="' + re.escape(args.db) + '"', target):
        die('产物已含风格屏集合 %s（重复注入）——重注前先还原备份' % args.db)

    # ---- 0.5 运行时身份：目标必须含多风格运行时消费者（2026-11-24 uni-ui 实测：数据侧注入全绿、
    # 真点 90 条 0 过才暴露运行时缺失——墙撞晚了）。无消费者=注入只能得到"数据齐、无切卡"半成品，门口拦下。
    # asset-mode 产物（build --asset-out 把运行时外置 assets/js/）：html 内 0 命中时连外置脚本一并扫再判（standards 审查实证修复）
    _rt_marks = ('applyDomBase', 'style-chooser', '__spApplyStyleScreens', 'prototype-style-state')
    _rt_hits = sum(target.count(_m) for _m in _rt_marks)
    if _rt_hits == 0:
        for _sm in re.finditer(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', target):
            _sp = target_path.parent / _sm.group(1)
            if _sp.exists():
                try:
                    _rt_hits += sum(_sp.read_text(encoding='utf-8', errors='ignore').count(_m)
                                    for _m in _rt_marks[:3])
                except Exception:
                    pass
    if _rt_hits == 0:
        die('目标产物无多风格运行时消费者（applyDomBase/style-chooser/风格面板机制 0 命中，含外置脚本扫描）'
            '——旧版运行时产物，拒绝注入（数据侧注进去也没人消费）\n'
            '处置三选（经用户裁决后重跑）：\n'
            '  A 重建运行时再注入：主管线现行 build.py 重建产物基座（含面板运行时），原风格屏从旧产物 DOM '
            '机械提取保全为 db-main（主客顺序断言见 multi-style-spec.md §九 旧版运行时产物），再走本注入链\n'
            '  C 接受现状交付：注入可成但无点卡切换，交付说明如实声明缺口\n'
            '  D 回退放弃：还原既有 .bak / 不动原产物')

    # ---- 1. 备份
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bak = target_path.with_name(target_path.name + '.bak-' + stamp)
    shutil.copy2(target_path, bak)
    print('备份 %s -> %s' % (target_path, bak))

    # ---- 2. 对账（v2：页数跨风格可不守恒；只查 fragments 页 id 唯一性 + 前缀化后不与 target 撞）
    tgt_screens = SCREEN_OPEN_RE.findall(target)
    frags, frag_css = read_fragments(frag_dir)
    frag_screens = [f['screen'] for f in frags]
    prefixed = ['%s-%s' % (short, x) for x in frag_screens]
    clash = sorted(set(tgt_screens) & set(prefixed))
    if clash:
        die('页 id 前缀化后仍与产物撞车（B 片段页 id 须为不带风格段的语义 id）: %s' % ','.join(clash))
    if len(set(frag_screens)) != len(frag_screens):
        die('B 片段页 id 重复')
    if args.screens:
        want = [x.strip() for x in args.screens.split(',') if x.strip()]
        if want != prefixed:
            die('--screens 对账失败（应为前缀化后页 id）:\n  --screens : %s\n  fragments : %s' % (','.join(want), ','.join(prefixed)))
    print('对账 OK: 原风格 %d 屏 + 新风格 %d 屏（页数不守恒合法，规格 §一）' % (len(tgt_screens), len(prefixed)))

    # ---- 3. 既有页面 CSS 补源风格域前缀 + 源屏回填 data-style-id
    upgraded = 0
    seen_blocks = 0
    scope_warns = []

    def _up(m):
        nonlocal upgraded, seen_blocks
        seen_blocks += 1
        css = m.group(2)
        if '[data-style-id=' in css:
            return m.group(0)
        new_css, w = upgrade_css_scope(css, args.src_db)
        if brace_balance(new_css) != 0:
            die('源域 CSS 前缀升级后括号不配平')
        upgraded += 1
        scope_warns.extend(w)
        return m.group(1) + new_css + m.group(3)

    target = PILOT_PAGE_CSS_RE.sub(_up, target)
    if seen_blocks == 0:
        # asset-mode：页面业务 CSS 外置（<link id="pilot-page-css" href="assets/…">），
        # 对每个外置 pilot-page-css 文件做同一步域前缀升级（机械等价，幂等跳过已带域文件）——
        # 2026-11-24 自换风包回灌（uni-ui 真产物 asset-mode 注入实战验证过的分支）
        link_pat = re.compile('<link\\b[^>]*\\bid=["\']pilot-page-css["\'][^>]*>', re.I)
        links = link_pat.findall(target)
        for lm in links:
            hm = re.search(r'href=["\']([^"\']+)["\']', lm)
            if not hm:
                die('asset-mode pilot-page-css link 缺 href: %s' % lm[:80])
            css_path = target_path.parent / hm.group(1)
            css = css_path.read_text(encoding='utf-8')
            if '[data-style-id=' in css:
                seen_blocks += 1
                continue
            new_css, w = upgrade_css_scope(css, args.src_db)
            if brace_balance(new_css) != 0:
                die('asset-mode 源域 CSS 前缀升级后括号不配平: %s' % css_path.name)
            scope_warns.extend(w)
            bak_css = css_path.with_name(css_path.name + '.bak-' + stamp)  # 外置 CSS 同戳备份：后续任一 die 可回退（standards 审查补）
            shutil.copy2(css_path, bak_css)
            css_path.write_text(new_css, encoding='utf-8')
            upgraded += 1
            seen_blocks += 1
        if seen_blocks:
            note('asset-mode：外置 pilot-page-css 文件 %d 个已处理（升级 %d，改动件 .bak-%s 留存）' % (seen_blocks, upgraded, stamp))
    if seen_blocks == 0:
        die('产物内未找到 id="pilot-page-css" 页面业务 CSS 块——目标产物不是本链（editor_convert→build）产出，拒绝注入')
    if upgraded == 0:
        note('源域 %d 个 pilot-page-css 块均已带前缀（多次注入幂等跳过）' % seen_blocks)
    if scope_warns:
        uniq = sorted(set(scope_warns))
        note('源域 CSS 有 %d 个非 .screen 开头选择器未升级（保持原样，请复核）: %s'
             % (len(scope_warns), '；'.join(uniq[:8]) + ('…' if len(uniq) > 8 else '')))
    print('源域 CSS 前缀升级: %d 个 pilot-page-css 块 -> [data-style-id="%s"]' % (upgraded, args.src_db))

    # 源屏回填 data-style-id（幂等：产物已有任一 data-style-id=多次注入，跳过）
    filled_this_run = 0  # 本次实际回填的 src 域屏数（自检 src 屏数期望=pre 计数+本次回填；编排 A2 实证修复）
    if not re.search(r'<section\b[^>]*\bdata-style-id="', target):
        def _tag(m):
            return m.group(0)[:-1] + ' data-style-id="%s">' % args.src_db
        target, n_filled = re.subn(r'<section\b[^>]*\bdata-screen="(?:%s)"[^>]*>' % '|'.join(re.escape(x) for x in tgt_screens),
                                   _tag, target)
        filled_this_run = n_filled
        print('源屏回填 data-style-id="%s": %d 屏' % (args.src_db, n_filled))
    else:
        note('产物已含 data-style-id 屏（多次注入）：源屏回填跳过')

    # ---- 4. B 片段 CSS 检查（必须带本风格域前缀）
    page_css = [c for c in frag_css if c['id'] == 'pilot-page-css']
    if not page_css:
        die('B 片段缺 <style id="pilot-page-css">（不是 editor_convert 产出形态）')
    for c in page_css:
        if '[data-style-id="%s"]' % args.db not in c['css'] and '[data-dom-base="%s"]' % args.db not in c['css']:
            die('B 片段业务 CSS 未带 [data-style-id="%s"] 域前缀（规格 §三：裸样式全局互压=违规）。'
                '请用 editor_convert --db %s 重新产出片段' % (args.db, args.db))
        if brace_balance(c['css']) != 0:
            die('B 片段 CSS 括号不配平')
        for other in sorted(set(re.findall(r'\[data-(?:style-id|dom-base)="([^"]+)"\]', c['css']))):
            if other != args.db:
                die('B 片段 CSS 出现异域前缀 %s（应只含 %s）' % (other, args.db))

    # ---- 5. B 片段加工：页 id 风格段前缀化（data-screen + goto 引用同步）+ eid 查重 + sprite 前缀
    b2s = dict(zip(frag_screens, prefixed))
    canvas_pre = strip_blocks_span(canvas_body(target))
    have_eids = set(re.findall(r'data-eid="([^"]+)"', canvas_pre))
    have_syms = set(SYMBOL_ID_RE.findall(canvas_pre))
    new_sections = []
    rename_total = 0
    for f in frags:
        sec = f['section']
        if '<script' in sec.lower():
            die('B 片段含 <script>（页面片段纯声明式铁律）: %s' % f['path'])
        gotos = set(g[1] for g in GOTO_VAL_RE.findall(sec))
        bad_goto = sorted(g for g in gotos if g not in b2s)
        if bad_goto:
            die('B 片段 %s 的 goto 引用了片段外的页（跨段引用无法改写）: %s' % (f['screen'], ','.join(bad_goto)))

        def _goto(m):
            return m.group(1) + b2s[m.group(2)] + m.group(3)
        sec = GOTO_VAL_RE.sub(_goto, sec)
        sec = re.sub(r'data-screen="%s"' % re.escape(f['screen']), 'data-screen="%s"' % b2s[f['screen']], sec, count=1)
        short_clash = [p for p in re.findall(r'data-eid="([^"]+)"', sec)
                       if '%s-%s' % (short, p) in have_eids]
        if short_clash:
            die('eid 前缀化后仍撞车: %s' % ','.join(sorted(set(short_clash))))
        sec = prefix_eids(sec, short)
        sec, renames = sprite_prefix(sec, args.pack_id)
        new_syms = [n for _, n in renames]
        dup = [s for s in new_syms if s in have_syms]
        if dup:
            die('sprite symbol id 撞车: %s' % ','.join(sorted(set(dup))))
        have_syms.update(new_syms)
        rename_total += len(renames)
        new_sections.append((b2s[f['screen']], sec, f['group']))
        have_eids.update(re.findall(r'data-eid="([^"]+)"', sec))
    print('B 片段加工: 页 id 前缀化 %s-*（goto 同步），sprite symbol 改名 %d 个' % (short, rename_total))

    # ---- 6. DOM 手术（v2）：B 屏 append 到 canvas 末尾，初始 display:none；源屏不动
    # data-name 读片段原中文页名（排查 P1-8：旧写法回填页 id，左树/页签显示英文内部编号，
    # 违反 editor-runtime「页面名一律用中文」）；片段无名时回退页 id。
    append_parts = []
    for sid, sec, _grp in new_sections:
        nm = re.search(r'data-name="([^"]*)"', sec)
        page_name = nm.group(1) if nm else sid
        append_parts.append('<section class="screen" data-screen="%s" data-name="%s" data-style-id="%s" style="display:none">%s</section>'
                            % (sid, page_name, args.db, _strip_outer_section(sec)))
    append_html = '\n'.join(append_parts)
    c_span = canvas_span(target)  # v2 修复：CSS 前缀升级改变文本长度，canvas 边界须重算（勿用第 0 步旧值）
    main_close = target.rfind('</main>', 0, c_span[1] + 8)
    if main_close < 0:
        die('产物缺 </main>')
    target = target[:main_close] + append_html + '\n' + target[main_close:]
    print('DOM 手术(v2): append %d 屏到 canvas 末尾（data-style-id=%s，初始 display:none）' % (len(new_sections), args.db))

    # ---- 7. pageTree 单映射扩分组表 + 追加新风格段（规格 §一：树按风格独立）
    def _pt_rep(m):
        try:
            pt = json.loads(m.group(2))
        except Exception:
            pt = {}
        if not any(isinstance(v, dict) for v in pt.values()):
            pt = {args.src_db: pt}  # 旧单映射=原风格段（兼容读法）
        pt.setdefault(args.src_db, {})
        pt[args.db] = {sid: grp for sid, _sec, grp in new_sections}
        return m.group(1) + dump_json(pt) + m.group(3)
    if PAGE_TREE_RE.search(target):
        target = PAGE_TREE_RE.sub(_pt_rep, target, count=1)
        print('pageTree: 扩分组表 + 追加风格段 %s（%d 页）' % (args.db, len(new_sections)))
    else:
        note('产物无 prototype-page-tree 节点，跳过 pageTree 合并')

    # ---- 8. B 片段 CSS 注入 </head> 前
    inject_head = ''
    for c in frag_css:
        sid = (c['id'] + '-' + args.db) if c['id'] else ('style-' + args.db)
        inject_head += '<style data-style-css="%s" id="%s">%s</style>' % (args.db, sid, c['css'])
    head_close = target.rfind('</head>')
    if head_close < 0:
        die('产物缺 </head>')
    target = target[:head_close] + inject_head + target[head_close:]

    # ---- 9. 受控块合并（封面：merge 前 sb 半边）
    cover_report = apply_covers(sb, blocks, args.db, args.pack_id, args)
    report = merge_blocks(blocks, sb, args.db, args.pack_id, prefixed)
    report += cover_report
    for name in ('STYLE-REGISTRY', 'STYLE-PACK', 'COMPONENT-PACK'):
        payload = dump_json(blocks[name])
        pat = BLOCK_RE[name]

        def _rep(m, payload=payload):
            return m.group(0)[:m.start(1) - m.start(0)] + payload + m.group(0)[m.end(1) - m.start(0):]

        target, n = pat.subn(_rep, target, count=1)
        if n != 1:
            die('受控块 %s 原位替换失败' % name)
    for line in report:
        print('合并 ' + line)

    # ---- 10. 自检
    errs = []
    # a) 每屏 data-style-id 恰一且 ∈ {产物既有域 ∪ 本次新域}；总屏数=原+新（标记在开标签上，统计用开标签原文）
    #    v2 多次注入：合法域集=注入前采集的 pre_style_ids（既有全部域）+ args.db——N≥3 注入不死（2026-11-23 排查 P0-3 修复）
    per_ids = [re.findall(r'data-style-id="([^"]+)"', mm.group(0)) for mm in SCREEN_OPEN_RE.finditer(target)]
    flat = [v for vs in per_ids for v in vs]
    legal_ids = set(pre_style_ids) | {args.db, args.src_db}
    # src_db 也属合法域：首次注入时产物回填前无任何标记，src 域是本次新挂（编排 A2 实证；pre 采集在回填前）
    bad_ids = sorted(set(v for v in flat if v not in legal_ids))
    if bad_ids:
        errs.append('存在未知风格域 data-style-id: %s' % ','.join(bad_ids[:8]))
    n_multi = sum(1 for vs in per_ids if len(vs) > 1)
    if n_multi:
        errs.append('%d 屏挂多风格标记（v2 屏内单容器）' % n_multi)
    total = len(SCREEN_OPEN_RE.findall(target))
    if total != len(tgt_screens) + len(prefixed):
        errs.append('屏总数 %d ≠ 原 %d + 新 %d' % (total, len(tgt_screens), len(prefixed)))
    n_src = sum(1 for vs in per_ids if args.src_db in vs)
    n_new = sum(1 for vs in per_ids if args.db in vs)
    # src/new 屏数对齐：src 期望=注入前 src 域计数+本次回填增量（首次注入回填全量源屏；
    # 排查 P0-3 补全：原 n_src!=len(tgt_screens) 口径把全部既有屏记在 src_db 头上，N≥3 必假 FAIL）
    src_expect = pre_domain_counts.get(args.src_db, 0) + filled_this_run
    if n_src != src_expect or n_new != len(prefixed):
        errs.append('风格屏数不齐: src=%d/%d new=%d/%d'
                    % (n_src, src_expect, n_new, len(prefixed)))
    # 其他既有域屏数注入前后必须不变（防手术误伤其他风格屏）
    for sid in pre_style_ids:
        if sid in (args.src_db, args.db):
            continue
        after = sum(1 for vs in per_ids if sid in vs)
        if after != pre_domain_counts.get(sid, 0):
            errs.append('既有风格域 %s 屏数变动: %d -> %d（手术误伤）'
                        % (sid, pre_domain_counts.get(sid, 0), after))
    # a2) 产物 TODO 占位扫描（还原重注链的防复发闸：备份若是占位时代产物，还原重注会复带 TODO——2026-11-23 实证）
    if re.search(r'TODO-SEMANTIC', target):
        errs.append('产物含 TODO-SEMANTIC 占位（源备份为占位时代产物）——请以修复后的素材重 build，或手工填毕语义槽再注入')
    # b) v1 残留
    if re.search(r'data-dom-base="', canvas_body(target)):
        errs.append('canvas 内存在 [data-dom-base]（v1 半架构残留）')
    # c) 四块恰 1 且可解析
    for name in BLOCK_NAMES:
        ms = BLOCK_RE[name].findall(target)
        if len(ms) != 1:
            errs.append('受控块 %s 数量=%d（应恰 1）' % (name, len(ms)))
            continue
        try:
            json.loads(ms[0])
        except Exception as e:
            errs.append('受控块 %s JSON 不可解析: %s' % (name, e))
    # d) CSS 配平
    for c in frag_css:
        if brace_balance(c['css']) != 0:
            errs.append('注入 CSS 括号不配平: %s' % c['id'])
    # e) eid 查重
    body_only = strip_blocks_span(canvas_body(target))
    eids = re.findall(r'data-eid="([^"]+)"', body_only)
    dup_e = sorted({e for e in eids if eids.count(e) > 1})
    if dup_e:
        errs.append('裸重名 eid: %s' % ','.join(dup_e[:10]))
    # f) symbol 查重 + use 闭合
    syms = SYMBOL_ID_RE.findall(body_only)
    dup_s = sorted({s for s in syms if syms.count(s) > 1})
    if dup_s:
        errs.append('裸重名 symbol id: %s' % ','.join(dup_s[:10]))
    symset = set(syms)
    for um in USE_REF_RE.finditer(body_only):
        if um.group(1) not in symset:
            errs.append('use 引用悬空: #%s' % um.group(1))
    # g) B 屏初始隐藏
    for sid, _sec, _g in new_sections:
        mm = re.search(r'<section\b[^>]*\bdata-screen="%s"[^>]*>' % re.escape(sid), target)
        if not mm or 'display:none' not in mm.group(0):
            errs.append('新风格屏未初始隐藏: %s' % sid)
    # h) pageTree 分组表形态
    pm = PAGE_TREE_RE.search(target)
    if pm:
        try:
            ptv = json.loads(pm.group(2))
            if not any(isinstance(v, dict) for v in ptv.values()):
                errs.append('pageTree 未扩成分组表')
            if args.db not in ptv:
                errs.append('pageTree 缺新风格段 %s' % args.db)
        except Exception as e:
            errs.append('pageTree JSON 不可解析: %s' % e)

    if errs:
        for e in errs:
            print('SELF-CHECK FAIL ' + e)
        die('自检未过，拒绝落盘（备份保留在 %s）' % bak)

    out_path = Path(args.out) if args.out else target_path
    out_path.write_text(target, encoding='utf-8')
    print('OK 已落盘: %s（%d 字符；备份 %s）' % (out_path, len(target), bak))
    print('下一步: node <SKILL>/scripts/verify-interactions.mjs %s <开工说明.md> 真点验证'
          ' && node <SKILL>/scripts/editor_shoot_compare.mjs 截图对账'
          '（换风包 conversion.md 第 9/10 步；主管线=editor-conversion.md 正式链对账步；'
          '受控块可另跑 python verify_blocks.py 复核）' % out_path)


def _strip_outer_section(sec):
    """B 片段 section 文本 → 内部内容（v2 append 时重建外壳，剥掉原 section 标签）。"""
    open_end = sec.index('>') + 1
    end = match_balanced(sec, open_end, 'section')
    if end is None:
        die('B 片段 section 配平失败')
    return sec[open_end:end[0]]


def prefix_eids(sec, short):
    """data-eid 加风格短段前缀（data-annotation-anchor 引用同步改写）。"""
    def _e(m):
        return 'data-eid="%s-%s"' % (short, m.group(1))
    out = re.sub(r'data-eid="([^"]+)"', _e, sec)
    def _a(m):
        return 'data-annotation-anchor="%s-%s"' % (short, m.group(1))
    out = re.sub(r'data-annotation-anchor="([^"]+)"', _a, out)
    return out


def sprite_prefix(sec, pack_id):
    """sprite symbol id 按包前缀，use 引用同步；返回 (文本, [(旧,新)])。"""
    renames = []

    def _s(m):
        old = m.group(1)
        new = 'icon-%s-%s' % (pack_id, old)
        renames.append((old, new))
        return m.group(0).replace('id="%s"' % old, 'id="%s"' % new, 1)
    out = SYMBOL_ID_RE.sub(_s, sec)
    for old, new in renames:
        out = out.replace('href="#%s"' % old, 'href="#%s"' % new).replace('xlink:href="#%s"' % old, 'xlink:href="#%s"' % new)
    return out, renames


if __name__ == '__main__':
    main()
