# -*- coding: utf-8 -*-
"""editor_convert — 静态高保真单文件 → 编辑器片段 转化器（附加A 通用版）

参考实现（首个试点+坑记录）：师傅工单项目 editor-pilot/tools/convert_pilot.py；
规范：references/editor-conversion.md——转前建三份账，本脚本只执行账面映射，不自作主张。

用法：
  python editor_convert.py --src <静态稿.html> --out <片段输出目录> \
    --screens page-home=首页=说明文本,page-order=工单详情=说明文本 \
    [--colors <色映射.json>] [--ext-keys <扩展键.json>] [--app-patch <额外压回.css>]

色映射 JSON：{"#1769E0": "var(--accent)", "rgba(23,105,224,.1)": "color-mix(...)"} 字面量→表达式。
扩展键 JSON：{"amount-accent": "#E5760A", ...} → 片段 :root 兜底 --sp-<键> + style-blocks 提示。
rgba 派生：--colors 里可给 "rgba(23,105,224,{a})": "color-mix(in srgb, var(--accent) {p}%, transparent)"
模板形态（{a}=alpha 原值, {p}=百分比），脚本按 alpha 枚举生成——未命中的 rgba 保留原值并打印清单（进账3）。

产出：<out>/<屏id>.html（fonts+page-css+片段）+ 占位屏 zz-placeholders.html + 转化摘要 stdout。
自检：CSS 括号配平不通过即拒绝落盘（K2 教训）；旧 data-go/data-seg/data-filter 残留=0 才算成功。
"""
import argparse
import base64
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

STRIP_SELECTORS = (
    ':root', '*', 'body', 'nav', 'main', '.pg-', '.w-btn', '.wswitch',
    '.screen', '.device', '.viewport', '.anno-', '.host-toast',
)

# 运行时/种子漏进属性压回（K1 实证五处；项目特有追加走 --app-patch）
BASE_PATCH = (
    '\n/* convert: 压运行时 .app 默认 */\n'
    '.screen .app{padding-top:0;padding-left:0;padding-right:0;padding-bottom:0;gap:0}\n'
    '/* convert: 压运行时 .chips 默认 wrap */\n'
    '.screen .chips{flex-wrap:nowrap}\n'
    '/* convert: 压种子 .hero 主视觉默认 */\n'
    '.screen .hero{background-image:none;color:inherit;display:block}\n'
    '/* convert: 压运行时 .viewport 顶部垫层（源稿状态栏为流内元素）；选择器须对齐 .device.mobile .viewport 三类特异性 */\n'
    '.screen .device.mobile .viewport{padding-top:0}\n'
    '/* convert: 压运行时 .flow 默认（壳给 gap:9px/padding:4px，会撑开源稿卡间距与状态栏，源稿 .flow 无此声明） */\n'
    '.screen .flow{padding:0;gap:0}\n'
)


def strip_rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules, depth, cur = [], 0, ''
    for ch in css:
        cur += ch
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                rules.append(cur); cur = ''
    if cur.strip():
        rules.append(cur)
    kept = []
    for r in rules:
        s = r.strip()
        if not s:
            continue
        sel = s.split('{')[0].strip()
        if s.startswith('@keyframes') or s.startswith('@media'):
            kept.append(s); continue
        if sel.startswith('@'):
            continue
        if any(sel.startswith(p) for p in STRIP_SELECTORS):
            continue
        kept.append(s)
    return kept


def scope_prefix(rule, extra=''):
    """业务 CSS 逐条挂 .screen 前缀；--db 模式 extra='[data-style-id="db-<id>"]'
    时升级为 .screen[data-style-id="…"] X——**连写**（data-style-id 挂 section 本身；带空格=后代选择器永不命中，
    uni-ui 实测变量全灭根因，multi-style-spec v2 §三：页面业务 CSS 逐条挂风格域）。"""
    s = rule.strip()
    # v2 多风格：style-id 挂 section 本身，.screen 与域选择器连写（后代关系永不命中——实测翻车）
    mid = extra if extra else ''
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
                    parts.append(cur); cur = ''
        return head + '{\n' + '\n'.join(scope_prefix(r, extra) for r in parts if r.strip()) + '\n}'
    head, body = s.split('{', 1)
    segs = ['.screen' + mid + ' ' + seg.strip() for seg in head.split(',') if seg.strip()]
    return ',\n'.join(segs) + ' {' + body


def dom_scope_css(css_text, dom_sel):
    """--db 模式配套：对 BASE_PATCH/app_patch 这类已拼好的 .screen 前缀文本统一升级域前缀。
    已含 [data-dom-base= 的 seg 幂等跳过；@keyframes 原样；@media 递归；
    压回规则的 /* convert: */ 注释行在段头，占位保护不参与 seg 判断。"""
    stash = []

    def _stash(m):
        stash.append(m.group(0))
        return '\x00%d\x00' % (len(stash) - 1)

    def _unstash(t):
        return re.sub(r'\x00(\d+)\x00', lambda m: stash[int(m.group(1))], t)

    def upgrade(rule):
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
                        parts.append(cur); cur = ''
            return head + '{\n' + '\n'.join(upgrade(r) for r in parts if r.strip()) + '\n}'
        head, body = s.split('{', 1)
        segs = []
        for seg in head.split(','):
            seg = seg.strip()
            if not seg:
                continue
            # 剥前导注释占位（压回规则段头的 /* convert: */ 行），净 seg 判断后再拼回
            lead_m = re.match(r'((?:\x00\d+\x00[\s]*)+)', seg)
            lead = lead_m.group(1) if lead_m else ''
            core = seg[lead_m.end():].strip() if lead_m else seg
            if '[data-dom-base=' in core or '[data-style-id=' in core:  # v2 多风格：双前缀幂等（scope_prefix 已连写挂域，dom_scope_css 不再二次升级）
                # K16 输入口径：历史带空格坏形态（.screen [data-style-id=）永不命中，幂等放行前归一为连写
                core = re.sub(r'(\.screen)\s+(\[data-(?:style-id|dom-base)=)', r'\1\2', core)
                segs.append(lead + core)
            elif core.startswith('.screen'):
                segs.append(lead + '.screen' + dom_sel + ' ' + core[len('.screen'):].strip())
            else:
                segs.append(lead + '.screen' + dom_sel + ' ' + core)
        return ',\n'.join(segs) + ' {' + body

    text = re.sub(r'/\*.*?\*/', _stash, css_text, flags=re.S)
    rules, depth, cur = [], 0, ''
    for ch in text:
        cur += ch
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                rules.append(cur); cur = ''
    if cur.strip():
        rules.append(cur)
    return _unstash('\n'.join(upgrade(r) for r in rules))


def brace_balance(css):
    return css.count('{') - css.count('}')


def build_color_repl(color_map):
    """字面量映射 + rgba 模板枚举 → (替换函数, 未命中收集器)"""
    exact = dict(color_map)
    templates = []  # (r,g,b, template_str)
    for k, v in color_map.items():
        m = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*\{a\}\)', k)
        if m:
            templates.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), v))


    def repl(css, misses):
        def sub(m):
            r, g, b, a = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
            for tr, tg, tb, tpl in templates:
                if (tr, tg, tb) == (r, g, b):
                    p = round(a * 100, 2)
                    pi = int(p) if p == int(p) else p
                    return tpl.replace('{p}', str(pi)).replace('{a}', m.group(4))
            key = m.group(0)
            if key in exact:
                return exact[key]
            misses.add(key)
            return key

        def subh(m):
            k = m.group(0)
            if k in exact:
                return exact[k]
            misses.add(k)
            return k

        css = re.sub(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', sub, css)
        css = re.sub(r'#[0-9a-fA-F]{6}\b', subh, css)
        return css

    return repl


def tokenize(css, color_repl):
    """颜色 var 化 + box-shadow 整串保护（K3）+ 1.5px 边框槽 + 圆角主档。"""
    shadows = {}

    def keep(m):
        key = f'__SHADOW{len(shadows)}__'
        shadows[key] = m.group(1).strip()
        return f'box-shadow:{key}'
    css = re.sub(r'box-shadow:\s*([^;{}]+)(?=[;}\n])', keep, css)
    misses = set()
    css = color_repl(css, misses)
    for k, v in shadows.items():
        css = css.replace(k, v)
    css = re.sub(r'(border(?:-\w+)?:\s*)1\.5px', r'\g<1>var(--sp-border-width)', css)
    css = re.sub(r'border-radius:\s*8px(?=[;}\s])', 'border-radius:var(--sp-radius-sm)', css)
    css = re.sub(r'border-radius:\s*12px(?=[;}\s])', 'border-radius:var(--sp-radius-md)', css)
    css = re.sub(r'border-radius:\s*16px(?=[;}\s])', 'border-radius:var(--sp-radius-lg)', css)
    return css, misses


def img_to_dataurl(html, img_dir):
    def repl(m):
        p = img_dir / Path(m.group(1)).name
        b64 = base64.b64encode(p.read_bytes()).decode()
        ext = p.suffix.lstrip('.').lower()
        mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
        return f'src="data:image/{mime};base64,{b64}"'
    return re.sub(r'src="(assets/images/[^"]+)"', repl, html)


def convert_screen(section_html, screen_id, screen_name, scr_note, img_dir, color_repl=None, misses=None):
    s = img_to_dataurl(section_html, img_dir)
    # A1（审查 P1）：内联 style 颜色 var 化——多屏源稿常见行内色值，漏了会静默保留硬值；
    # 未命中色值并入全局 misses 上报（复核 P2：不能只在主 CSS 侧打印）
    if color_repl is not None and misses is not None:
        s = color_repl(s, misses)
    n = [0]

    def go_repl(m):
        n[0] += 1
        return (f'data-eid="{screen_id}-act-{n[0]:02d}" '
                f'data-on="{{&quot;click&quot;:{{&quot;goto&quot;:&quot;{m.group(1)}&quot;}}}}"')
    s = re.sub(r'data-go="([^"]+)"', go_repl, s)
    s = re.sub(r'\s+data-seg="[^"]*"', '', s)
    s = re.sub(r'\s+data-tab="[^"]*"', '', s)
    cn = [0]

    def chip_repl(m):
        cn[0] += 1
        return f'class="fchip chip{m.group(1)}" data-eid="{screen_id}-chip-{cn[0]:02d}"'
    s = re.sub(r'class="fchip(\s[^"]*)?"', chip_repl, s)  # v2 修：fchip 后必须空白或闭引号，防误吞 .fchips 容器
    s = re.sub(r'\s+data-filter="[^"]*"', '', s)
    from html import escape as _e
    head = (f'<div class="scr-head"><span class="scr-name">{_e(screen_name)}</span>'
            f'<span class="scr-note">{_e(scr_note)}</span></div>')
    s = re.sub(r'(<section\b[^>]*>)', lambda m: m.group(1) + head, s, count=1)
    # 旁批转编辑器格式（复核后用户定案）：aside.anno 合并为单条 data-note 挂 .app 页面锚，
    # aside 从编辑器产物移除——面板全统一原生标注，与用户手动批注同构可编辑。
    # aside 原文仍归档：预览壳版（gui 交付物）继续用 aside 面板，两形态各自成立。
    anno = re.search(r'<aside class="anno"[^>]*>([\s\S]*?)</aside>', s)
    if anno:
        parts, cur = [], None
        for pn in re.findall(r'<p([^>]*)>([\s\S]*?)</p>', anno.group(1)):
            attrs, txt = pn[0], re.sub(r'<[^>]+>', '', pn[1]).strip()
            if not txt:
                continue
            if 'anno-no' in attrs:
                parts.append('【%s】%s' % (txt, ''))
                cur = len(parts) - 1
            elif cur is not None:
                parts[cur] += txt
            else:
                parts.append(txt)
        note = '\n'.join(x for x in parts if x.strip())
        if note and '<div class="app"' not in s:
            print(f'WARN {screen_id}：片段无 .app 挂点，旁批 {len(note)} 字未挂载（请检查源稿结构）')
        if note:
            e_note = _e(note).replace('\n', '&#10;')
            s = re.sub(r'(<div class="app")',
                       lambda m: m.group(1) + ' data-note="' + e_note + '"', s, count=1)
        s = re.sub(r'\s*<aside class="anno"[^>]*>[\s\S]*?</aside>', '', s)
    return s


def main():
    ap = argparse.ArgumentParser(description='static hifi → editor fragments (附加A)')
    ap.add_argument('--src', required=True, help='静态稿 html（只读）')
    ap.add_argument('--out', required=True, help='片段输出目录')
    ap.add_argument('--screens', required=True,
                    help='逗号分隔 屏id=页名=说明（说明可空）：page-home=首页=营生概况,page-submit=提交完工=')
    ap.add_argument('--colors', help='色映射 JSON（字面量→表达式；rgba 模板用 {a}/{p}）')
    ap.add_argument('--ext-keys', help='扩展键 JSON（键→值，生成 :root --sp-<键> 兜底）')
    ap.add_argument('--app-patch', help='项目特有压回 CSS 文件（追加在 BASE_PATCH 后）')
    ap.add_argument('--groups', help='导航分组（2026-11-20 用户定案：分组=底栏/一级导航归属，非业务域）：'
                    '格式 "组名:屏id,屏id;组名:屏id…"，按声明顺序输出 pages/<组名>/<屏id>.html；'
                    '未列入组的屏落根级殿后。构建按目录树自动生成左侧分组')
    ap.add_argument('--db', help='多风格屏集合 id（值域=domBaseId，格式 db-<风格id>）：业务 CSS 前缀升级为 '
                    '.screen[data-style-id="db-<id>"]（连写挂域——带空格=后代选择器永不命中；v2 屏集合组，multi-style-spec §三），'
                    'BASE_PATCH/app_patch/:root 兜底同步域化'
                    '（单文件多风格回装/构建时编排用；不传=既有行为零变化）')
    args = ap.parse_args()
    dom_sel = None
    if args.db:
        if not re.match(r'^db-[A-Za-z0-9_-]+$', args.db):
            print(f'FAIL --db 格式非法（须 db-<风格id>，^[A-Za-z0-9_-]+$）：{args.db}')
            raise SystemExit(2)
        dom_sel = '[data-style-id="%s"]' % args.db  # v2 多风格：域前缀平移为 [data-style-id]（值域=domBaseId，规格 §三）

    src_path = Path(args.src)
    src = src_path.read_text(encoding='utf-8')
    out = Path(args.out)
    (out / 'pages').mkdir(parents=True, exist_ok=True)

    css_blocks = re.findall(r'<style[^>]*>(.*?)</style>', src, re.S)
    font_css = css_blocks[0] if len(css_blocks) > 1 else ''
    biz_css = css_blocks[1] if len(css_blocks) > 1 else css_blocks[0]

    def _load_json(p, what):
        try:
            return json.loads(Path(p).read_text(encoding='utf-8-sig'))
        except Exception as e:
            print('FAIL %s 文件不可解析: %s | %s' % (what, p, e))
            raise SystemExit(2)
    color_map = _load_json(args.colors, '色映射 --colors') if args.colors else {}
    ext_keys = _load_json(args.ext_keys, '扩展键 --ext-keys') if args.ext_keys else {}
    color_repl = build_color_repl(color_map)

    rules = strip_rules(biz_css)
    tokenized, misses = [], set()
    for r in rules:
        t, m = tokenize(r, color_repl)
        tokenized.append(t)
        misses |= m
    scoped = '\n'.join(scope_prefix(r, dom_sel or '') for r in tokenized)
    scoped += BASE_PATCH
    if args.app_patch:
        scoped += '\n' + Path(args.app_patch).read_text(encoding='utf-8') + '\n'
    if ext_keys:
        if dom_sel:
            # --db 模式：:root 兜底域化为容器作用域（多风格下 A/B 的 :root 兜底全局共存会跨域泄漏）
            # 连写挂域（.screen[data-style-id=…]）：带空格=后代选择器永不命中，变量全灭（2026-11-24 uni-ui 实测根因）
            scoped = ('.screen' + dom_sel + '{' + ';'.join(f'--sp-{k}:{v}' for k, v in ext_keys.items()) + '}\n'
                      + scoped)
        else:
            scoped = ':root{' + ';'.join(f'--sp-{k}:{v}' for k, v in ext_keys.items()) + '}\n' + scoped
    if dom_sel:
        scoped = dom_scope_css(scoped, dom_sel)

    bal = brace_balance(scoped)
    if bal != 0:
        print(f'FAIL 业务 CSS 括号配平差值 {bal}——K2 防线，拒绝落盘')
        raise SystemExit(1)
    if font_css:
        bf = brace_balance(font_css)
        if bf != 0:
            print(f'FAIL 字体 CSS 块配平差值 {bf}——源稿首个 style 块自身不配平，拒绝带病落盘')
            raise SystemExit(1)

    group_of = {}
    if args.groups:
        for block in [x.strip() for x in args.groups.split(';') if x.strip()]:
            if ':' not in block:
                print(f'FAIL --groups 块缺冒号（格式 组名:屏id,屏id）：{block}')
                raise SystemExit(2)
            gname, sids = block.split(':', 1)
            gname = gname.strip()
            if not gname or re.search(r'[\/:*?"<>|]', gname):
                print(f'FAIL --groups 组名含非法字符（Windows 保留符/路径符）：{gname!r}')
                raise SystemExit(2)
            for sid in [x.strip() for x in sids.split(',') if x.strip()]:
                group_of[sid] = gname
    screens = []
    for item in args.screens.split(','):
        parts = item.split('=', 2)
        sid = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else sid
        note = parts[2].strip() if len(parts) > 2 else ''
        screens.append((sid, name, note, group_of.get(sid, '')))

    img_dir = src_path.parent / 'assets' / 'images'
    bodies = []
    for sid, name, note, grp in screens:
        marker = f'data-screen="{sid}"'
        if marker not in src:
            print(f'FAIL 源稿找不到 {marker}')
            raise SystemExit(1)
        before = src.split(marker, 1)[0]
        orig_tag = re.findall(r'<section[^>]*$', before)[-1]
        seg = src.split(marker, 1)[1]
        sec = orig_tag + ' ' + marker + seg.split('</section>', 1)[0] + '</section>'
        frag = convert_screen(sec, sid, name, note, img_dir, color_repl, misses)
        out_dir = out / 'pages' / grp if grp else out / 'pages'
        out_dir.mkdir(parents=True, exist_ok=True)
        content = (f'<style id="pilot-fonts">\n{font_css}\n</style>\n'
                   f'<style id="pilot-page-css">\n{scoped}\n</style>\n{frag}\n')
        (out_dir / f'{sid}.html').write_text(content, encoding='utf-8')
        bodies.append(frag)
        print(f'片段 {sid}.html —— {len(content)} 字符')

    # 占位屏：被引用未转化的目标屏
    joined = '\n'.join(bodies)
    targets = set(re.findall(r'goto&quot;:&quot;([\w-]+)&quot;', joined))
    missing = sorted(targets - {s[0] for s in screens})
    if missing:
        ph = [f'<style id="pilot-page-css">\n{scoped}\n</style>']
        for sid in missing:
            ph.append(
                f'<section class="screen" data-screen="{sid}" data-name="{sid}（待迁移）">'
                f'<div class="scr-head"><span class="scr-name">{sid}（待迁移）</span>'
                f'<span class="scr-note">全量铺量时由转化管线补全</span></div>'
                f'<div class="device mobile"><div class="viewport"><div class="app">'
                f'<div class="flow"><div class="body" style="padding-top:40px">'
                f'<div class="mcard r12" style="padding:24px;text-align:center">'
                f'<b style="font-size:14px">此页未在试点范围内</b>'
                f'<div style="font-size:12px;color:color-mix(in srgb, var(--text) 45%, transparent);margin-top:8px">'
                f'全量铺量时由转化管线补全（占位屏）</div></div></div></div>'
                f'</div></div></div></section>')
        (out / 'pages' / 'zz-placeholders.html').write_text('\n'.join(ph) + '\n', encoding='utf-8')
        print(f'占位屏 {len(missing)} 个：{", ".join(missing)}')

    resid = 0
    for p in sorted((out / 'pages').rglob('*.html')):
        t = p.read_text(encoding='utf-8')
        resid += len(re.findall(r'data-go=|data-seg=|data-filter=|data-tab=', t))
    print(f'旧标注残留 {resid}（须为 0）')
    if misses:
        print('未命中色值（进账3 值域登记）：', ', '.join(sorted(misses)))
    fonts = out / 'assets' / 'fonts'
    fonts.mkdir(parents=True, exist_ok=True)
    print(f'字体需拷贝至 {fonts}（源稿 assets/fonts/）')
    print('下一步：值域扫描生成 design-system/style-blocks JSON（见 editor-conversion.md）→ 正式链验收')


if __name__ == '__main__':
    main()
