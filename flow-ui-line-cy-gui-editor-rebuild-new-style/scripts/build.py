"""Build a portable editable prototype: validate fragments, compose into the editor runtime.

Modes:
  python build.py --check pages/                    # dev-mode pre-check ALL fragments (merged: cross-page targets resolve)
  python build.py --check pages/x.html              # dev-mode pre-check one fragment, auto-merging siblings for cross-page targets
  python build.py --check pages/ --start-doc intake/开工文档.md --phase incremental|final
                    [--scope pageId[,pageId...]] [--report u2.json]   # T02.1 项目模式阶段化检查（U2 回执）
  python build.py --project-dir DIR --phase incremental|final [--scope ...] [--report ...]
                    # T02.1 同上；pages=DIR/pages，intake=DIR/intake-开工文档.md（缺则唯一 *.md 兜底）
  python build.py --pages pages/ --title T --output build/x.html [--start-doc intake/开工文档.md]
                   [--device mobile|tablet|desktop] [--profile none|<name>]
                    [--u1-receipt R1 --u2-receipt R2 [--u3-report R3]]
                    # T02.1: --start-doc 构建=正式构建，构建前必须过 qa_receipt 门禁（U1+U2 final）

T01：装配只走 apply_current（冻结单「需保留」patch 集，无 version 反向改写/旧商城文案）；
受控运行时块唯一校验（重复/缺失具名失败）；AGENTS.md 文案与实际装配配置同源并防误覆他项目；
项目 profile 显式选择（默认 none 不注入任何专项，登记见 assets/project-profiles/）。
退出语义（冻结单 §2 现状保留）：0=成功；1=--check 检查失败（正式构建=门禁拒绝，含
verify_blocks 门禁失败）；2=参数/文件/装配内部错误。
页面命名检查（--check / 正式构建 / U2 项目检查共用）：E-NAMING-GROUP（页面树分组名不含中文）/
E-NAMING-PAGE（页面树显示名不含中文）/ E-NAMING-ID-LEAK（页头标题或页面描述含内部编号，
词边界匹配：编号前后紧挨字母/数字/下划线/连字符不算）。

T02.1 阶段化检查（项目模式）：契约错误（prototype_contract.loadContract，含片段对账）→ FAIL 逐条
ruleId:file:line:message → exit 1；片段级检查=动作/目标/身份/样式（runtime-contract.json 消费，
增量未产目标记 deferred E-ACT-TARGET-PENDING 不失败，final 收口 deferred==0）；覆盖=每非装饰
feature ≥1 条 claim 且 claim.eid 在对应页实存（final 强制）；--report 写 U2 回执（station U2）。
"""
import argparse
import html
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from upgrade_html import apply_current

ROOT = Path(__file__).resolve().parents[1]

# ---- T01 装配元信息（唯一出处；AGENTS.md/头注与实际装配配置同源，禁止散落硬编码文案）----
# 默认编辑口令明文仅此处出现；compose 以 PBKDF2-SHA-256 哈希注入产物，指南/头注引用同一常量。
EDIT_PASSWORD = '12345678'
# 与 seed 内 .device.* CSS 同源（editor-seed.html:137-146）：device -> (width, height)
DEVICE_SIZES = {'mobile': (375, 812), 'tablet': (834, 900), 'desktop': (1200, 800)}
DEVICE_LABELS = {'mobile': 'App 手机端', 'tablet': '平板端', 'desktop': '桌面浏览器'}
PROJECT_PROFILE_NONE = 'none'


class PageValidator(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.screens = []
        self.elements = set()
        self.bindings = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {'script', 'iframe', 'object', 'embed', 'link', 'base'}:
            self.errors.append('fragment introduces executable/external tag: ' + tag)
        if any(k.startswith('on') for k in a):
            self.errors.append('inline event handler found; use data-on JSON')
        if tag == 'section' and 'screen' in a.get('class', '').split():
            sid = a.get('data-screen')
            if not sid or not re.fullmatch(r'[a-zA-Z0-9_-]+', sid) or sid in self.screens:
                self.errors.append('screen needs a unique safe data-screen id: ' + repr(sid))
            else:
                self.screens.append(sid)
        if a.get('data-eid'):
            if a['data-eid'] in self.elements:
                self.errors.append('duplicate data-eid: ' + a['data-eid'])
            self.elements.add(a['data-eid'])
        if 'data-on' in a:
            try:
                spec = json.loads(a['data-on'])
                if not isinstance(spec, dict):
                    raise ValueError('not an object')
                self.bindings.append(spec)
            except Exception as e:
                self.errors.append('data-on must be a JSON object: ' + str(e))
        if tag == 'img' and not a.get('src', '').startswith('data:'):
            self.errors.append('img src must be an embedded data URL')
        if tag in {'video', 'audio', 'source'} and a.get('src') and not a['src'].startswith('data:'):
            self.errors.append('media src must be an embedded data URL')
        if tag == 'video' and a.get('poster') and not a['poster'].startswith('data:'):
            self.errors.append('video poster must be an embedded data URL')

    def check_targets(self):
        def walk(value):
            if isinstance(value, dict):
                for key, v in value.items():
                    if key in {'goto', 'sheet'} and isinstance(v, str) and v not in self.screens:
                        self.errors.append('missing target screen: ' + v)
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        for spec in self.bindings:
            walk(spec)


def validate_merged(pages_text: str):
    v = PageValidator()
    v.feed(pages_text)
    v.close()
    v.check_targets()
    return v


def validate_fragment(path: Path, merge_siblings=True):
    """Pre-check a fragment. Cross-page jumps resolve against sibling fragments
    in the same directory (merged validation) — single-file mode flags that a
    'missing target screen' may simply live in another fragment."""
    pages = path.read_text(encoding='utf-8-sig')
    merged = pages
    others = []
    if merge_siblings and path.parent.exists():
        others = [f for f in sorted(path.parent.glob('*.html')) if f != path]
        if others:
            merged = pages + '\n' + '\n'.join(f.read_text(encoding='utf-8-sig') for f in others)
    v = validate_merged(merged)
    return v, len(others) if merge_siblings else 0


def design_style(design):
    def safe(value):
        s = str(value)
        if any(c in s for c in ';{}<>\\'):
            raise ValueError('Unsafe design token value: ' + s)
        return s

    declarations = []
    for key, value in design.get('tokens', {}).items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', key):
            raise ValueError('Invalid token name: ' + key)
        declarations.append('--' + key + ':' + safe(value))
    typography = design.get('typography', {})
    size = float(typography.get('baseSize', 14))
    line = float(typography.get('lineHeight', 1.55))
    if not 10 <= size <= 24 or not 1 <= line <= 2.5:
        raise ValueError('Invalid typography scale')
    component = design.get('components', {})

    def dimension(key, default, low, high):
        value = float(component.get(key, default))
        if not low <= value <= high:
            raise ValueError('Invalid dimension: ' + key)
        return str(value) + 'px'

    return (':root{' + ';'.join(declarations) + '}'
            'body{font-family:' + safe(typography.get('fontFamily', 'system-ui, sans-serif'))
            + ';font-size:' + str(size) + 'px;line-height:' + str(line) + '}'
            '.b{border-radius:' + dimension('buttonRadius', 9, 0, 48)
            + ';min-height:var(--sp-size-ctl-lg,' + dimension('buttonMinHeight', 40, 24, 80) + ')}'
            '.ipt{border-radius:' + dimension('fieldRadius', 9, 0, 48) + '}'
            '.card-b{padding:var(--sp-space-3,' + dimension('cardPadding', 16, 0, 60) + ')}')


def overlay_active_pack(design, pack):
    """--active-pack：交付物基础设计=选中风格（单一来源，防「设计令牌说蓝、打开却是橙」两套真相）。
    只覆盖语义一一对应的字段；包里没有的键保持 design 原值。
    tokens 键名一律按正本表 assets/token-keys.json（全小写连字符，逐字读取）：
    primary/bg/surface/text-primary/text-secondary/border/radius-md/font-body/size-body/
    size-ctl-lg/space-3；驼峰等错误键名读不到=保持 design 原值（报错归检查脚本）。"""
    import copy
    d = copy.deepcopy(design)
    t = pack.get('tokens') or {}

    def num(v):
        try:
            return float(str(v).strip().replace('px', ''))
        except (TypeError, ValueError):
            return None
    tok = d.setdefault('tokens', {})
    for dk, pk in (('accent', 'primary'), ('bg', 'bg'), ('surface', 'surface'), ('text', 'text-primary'),
                   ('muted', 'text-secondary'), ('line', 'border')):
        if t.get(pk):
            tok[dk] = str(t[pk])
    if t.get('radius-md') is not None and num(t['radius-md']) is not None:
        tok['radius'] = '%gpx' % num(t['radius-md'])
    typ = d.setdefault('typography', {})
    if t.get('font-body'):
        typ['fontFamily'] = str(t['font-body'])
    if num(t.get('size-body')) is not None and 10 <= num(t['size-body']) <= 24:
        typ['baseSize'] = num(t['size-body'])
    comp = d.setdefault('components', {})
    if num(t.get('size-ctl-lg')) is not None and 24 <= num(t['size-ctl-lg']) <= 80:
        comp['buttonMinHeight'] = num(t['size-ctl-lg'])
    if num(t.get('space-3')) is not None and 0 <= num(t['space-3']) <= 60:
        comp['cardPadding'] = num(t['space-3'])
    ident = pack.get('identity') or {}
    if ident.get('styleName'):
        d['name'] = str(ident['styleName'])
    return d


def check_controlled_blocks(text: str, expected):
    """T01 装配防御性复核：每个受控运行时块必须恰出现一次；重复/缺失＝具名失败。

    受控块＝装配注入的运行时身份（prototype-* JSON 块、设计令牌、FREE_EDITOR/FREE_STYLE
    受控注入块、project-profile 标记块）。重复块/缺失块一律 ValueError（退出码 2＝装配内部错误）。
    """
    for marker in expected:
        n = text.count(marker)
        if n != 1:
            raise ValueError('Controlled block %s appears %d time(s); expected exactly 1' % (marker, n))


def load_profile(name: str):
    """加载显式项目 profile（assets/project-profiles/<name>.json）。

    默认不注入任何专项（--profile none）；未知/命名非法/id 不匹配＝具名失败。
    真实专项规则迁移属 T03/T04/T07——本轮只注入规则标记占位。
    """
    if not re.fullmatch(r'[a-z][a-z0-9_-]*', name):
        raise ValueError('Invalid project profile name: ' + name)
    profiles_dir = ROOT / 'assets/project-profiles'
    path = profiles_dir / (name + '.json')
    if not path.exists():
        available = ', '.join(sorted(p.stem for p in profiles_dir.glob('*.json'))) if profiles_dir.exists() else ''
        raise ValueError('Unknown project profile: %s (available: %s)' % (name, available or '(none registered)'))
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('id') != name:
        raise ValueError('Profile id mismatch: file %s declares id %r' % (path.name, data.get('id')))
    return data


def describe_device(pages_text: str, override=None):
    """AGENTS.md 端型文案：来自实际装配配置（片段内 device 类 / --device 覆盖 / seed 同源尺寸表）。"""
    if override:
        names = [override]
    else:
        found = re.findall(r'class="device\s+([a-zA-Z0-9_-]+)', pages_text)
        names = []
        for n in found:
            if n in DEVICE_SIZES and n not in names:
                names.append(n)
        if not names:
            names = ['mobile']
    parts = []
    for n in names:
        width = DEVICE_SIZES[n][0]
        parts.append(DEVICE_LABELS[n] + '（%dpx）' % width)
    return '＋'.join(parts)


def compose(pages: str, title: str, project_id: str, design=None, start_doc=None, tree=None, profile=None,
            style_blocks=None, active_pack=None, icon_families=None, conversion=False):
    v = PageValidator()
    v.feed(pages)
    v.close()
    v.check_targets()
    if v.errors:
        raise ValueError('Fragment validation failed:\n- ' + '\n- '.join(v.errors))
    if not v.screens:
        raise ValueError('At least one .screen section is required')
    # T01：装配只走 apply_current（冻结单「需保留」patch 集；无 P15 version 反向改写、无仅旧件 patch）。
    seed = apply_current((ROOT / 'assets/editor-seed.html').read_text(encoding='utf-8'))
    if conversion:
        seed = seed.replace('<html', '<html data-conversion="1"', 1)
    check_controlled_blocks(seed, ['/*FREE_EDITOR_START*/', '/*FREE_EDITOR_END*/',
                                   '/*FREE_STYLE_START*/', '/*FREE_STYLE_END*/'])
    seed = (seed
            .replace('__PROJECT_TITLE__', html.escape(title, quote=True))
            .replace('__PROJECT_ID__', html.escape(project_id, quote=True)))
    if design is None:
        design = json.loads((ROOT / 'assets/design-system.json').read_text(encoding='utf-8'))
    design_json = json.dumps(design, ensure_ascii=False).replace('<', '\\u003c')
    # T18：产物内置默认编辑口令（PBKDF2-SHA-256，与运行时 crypto.subtle 校验一致）。
    # 口令明文唯一出处=EDIT_PASSWORD 装配常量；AGENTS.md/头注引用同一常量（文案与装配配置同源）。
    # 批1e：不再注入 defaultPasswordHint 明文字段——口令只以哈希存在（该字段此前无任何运行时消费方）
    import hashlib as _hl
    _salt = 'd3f40000000000000000000000000000'
    _hash = _hl.pbkdf2_hmac('sha256', EDIT_PASSWORD.encode('utf-8'), bytes.fromhex(_salt), 210000).hex()
    inject = ('<style id="project-design-tokens">' + design_style(design) + '</style>'
              '<script type="application/json" id="prototype-design-system">'
              + design_json + '</script>'
              + '<script type="application/json" id="prototype-config">'
              + json.dumps({'schemaVersion': 2, 'editPassword': {'salt': _salt, 'hash': _hash, 'iterations': 210000, 'algorithm': 'PBKDF2-SHA-256'}}, ensure_ascii=False).replace('<', '\\u003c')
              + '</script>')
    if start_doc:
        doc_json = json.dumps({'markdown': start_doc}, ensure_ascii=False).replace('<', '\\u003c')
        inject += ('<script type="application/json" id="prototype-start-doc">'
                   + doc_json + '</script>')
    if tree:
        tree_json = json.dumps(tree, ensure_ascii=False).replace('<', '\\u003c')
        inject += ('<script type="application/json" id="prototype-page-tree">'
                   + tree_json + '</script>')
    # 图标库打包（原始全量不精简不压缩——考核要求：产物单文件发给别人也能编辑）。
    # 库存双形态（2026-11-23 D 案）：优先聚合件 assets/icons-json/<族>.json（Iconify 格式，
    # 与 solo-img-line-cy-icon-provisioner assets/icons-json 同源同格式，按需拷族文件扩族）；
    # 无聚合件目录时回落散 SVG 库 assets/icons/<族>/（旧形态兼容）。
    icons_json_dir = ROOT / 'assets/icons-json'
    icons_root = ROOT / 'assets/icons'
    icons_injected = False
    lib_pack = []
    only_fams = (icon_families or '').strip()
    only_set = {x.strip().lower() for x in only_fams.split(',') if x.strip()} if only_fams else None
    if icons_json_dir.exists():
        for jf in sorted(icons_json_dir.glob('*.json')):
            fam = jf.stem.lower()
            if only_set is not None and fam not in only_set:
                continue
            try:
                data = json.loads(jf.read_text(encoding='utf-8'))
            except Exception:
                continue
            w, h = data.get('width') or 24, data.get('height') or 24
            svgs = {}
            for name, ic in (data.get('icons') or {}).items():
                body = (ic or {}).get('body') if isinstance(ic, dict) else None
                if body:
                    svgs[name] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s">%s</svg>'
                                  % (w, h, body))
            for name, al in (data.get('aliases') or {}).items():
                parent = (al or {}).get('parent') if isinstance(al, dict) else None
                if parent and parent in svgs and name not in svgs:
                    svgs[name] = svgs[parent]
            if svgs:
                lib_pack.append({'name': jf.stem, 'forms': [{'key': 'default', 'label': '默认', 'svgs': svgs}]})
        if lib_pack:
            icons_injected = True
    elif icons_root.exists():
        icons_injected = True
        for lib_dir in sorted(icons_root.iterdir()):
            if not lib_dir.is_dir() or lib_dir.name.startswith('_'):
                continue
            if only_set is not None and lib_dir.name.lower() not in only_set:
                continue
            entry = {'name': lib_dir.name, 'forms': []}
            subdirs = [d for d in lib_dir.iterdir() if d.is_dir()]
            svg_dirs = [(d.name, d) for d in subdirs] or [('', lib_dir)]
            for label, d in svg_dirs:
                svgs = {}
                for f in sorted(d.glob('*.svg')):
                    try:
                        svgs[f.stem] = f.read_text(encoding='utf-8')
                    except Exception:
                        pass
                if svgs:
                    entry['forms'].append({'key': label or 'default', 'label': label or '默认', 'svgs': svgs})
            if entry['forms']:
                lib_pack.append(entry)
    if icons_injected:
        icons_json = json.dumps(lib_pack, ensure_ascii=False).replace('<', '\\u003c')
        inject += ('<script type="application/json" id="prototype-icon-library">'
                   + icons_json + '</script>')
    # T01：显式项目 profile 注入（默认 none 不注入任何专项；启用与否属于项目配置，不按内容/名称自动判定）。
    # 本轮只注入规则标记占位（CSS 变量/类开关）；真实专项规则迁移属 T03/T04/T07，登记见 assets/project-profiles/。
    if profile:
        pdata = load_profile(profile)
        inject_cfg = pdata.get('inject', {})
        var = inject_cfg.get('cssVar', '--project-profile')
        hook = inject_cfg.get('hookClass', 'prototype-profile-' + profile)
        profile_css = ('/*PROJECT_PROFILE:%s*/ :root{%s:%s;}.%s{/* placeholder: 专项规则迁移属 T03/T04/T07，'
                       '清单见 assets/project-profiles/%s.md */}'
                       % (profile, var, profile, hook, profile))
        inject += ('<style id="project-profile-css" data-project-profile="' + profile + '">'
                   + profile_css.replace('<', '\\u003c') + '</style>')
        # V06：profile 可声明 bodyClass（如 draft 档的 ed-draft——壳 CSS/JS 按它切预览形态）
        # 与 brandSubtitle（顶栏副标题文案）。注入是字面替换，seed 模板漂移＝具名失败（宁停勿错）。
        body_cls = inject_cfg.get('bodyClass')
        if body_cls:
            _body_tag = '<body class="shownotes ed-preview ed-ui-browse">'
            if _body_tag not in seed:
                raise ValueError('profile %s bodyClass inject failed: seed body tag template drifted '
                                 '(expected %r)' % (profile, _body_tag))
            seed = seed.replace(_body_tag, '<body class="shownotes ed-preview ed-ui-browse %s">' % body_cls, 1)
        brand_sub = inject_cfg.get('brandSubtitle')
        if brand_sub:
            _brand_tag = '<small>单文件可编辑原型 · 口令解锁后可调整全部设计</small>'
            if _brand_tag not in seed:
                raise ValueError('profile %s brandSubtitle inject failed: seed brand template drifted' % profile)
            seed = seed.replace(_brand_tag, '<small>' + html.escape(brand_sub) + '</small>', 1)
    # V05戊：换肤受控块注入（面板正式态数据源）。四块键名冻结（controlled-blocks.md 通则），
    # 注入形态=script data-block（verify_blocks/chooser 同口径）；传文件则四块必须齐。
    style_blocks_injected = []
    if style_blocks:
        for name in ('STYLE-REGISTRY', 'STYLE-PACK', 'COMPONENT-PACK', 'STYLE-CONTRACT'):
            if name not in style_blocks:
                raise ValueError('--style-blocks 缺块: %s（四块全量为契约，宁停勿错）' % name)
            bjson = json.dumps(style_blocks[name], ensure_ascii=False).replace('<', '\\u003c')
            inject += ('<script type="application/json" data-block="' + name + '">' + bjson + '</script>')
            style_blocks_injected.append(name)
    active_pack_state = None
    if active_pack:
        if not style_blocks:
            raise ValueError('--active-pack 需要 --style-blocks（选中包必须来自 STYLE-PACK.packs）')
        pack_ids = [p.get('packId') for p in (style_blocks.get('STYLE-PACK', {}).get('packs') or [])]
        if active_pack not in pack_ids:
            raise ValueError('--active-pack %r 不在 STYLE-PACK.packs 内（现有：%s）' % (active_pack, pack_ids))
        active_pack_state = json.dumps({'schemaVersion': 2, 'id': active_pack, 'packId': active_pack,
                                        'initialPackId': active_pack},
                                       ensure_ascii=False).replace('<', '\\u003c')
        # 挂 #canvas 内（与 chooser write()/seed 草稿快照同址：state 随 canvasHTML 进草稿/导出，刷新还原链不断）
    seed = seed.replace('</head>', inject + '</head>', 1)
    state_tag = ('<script type="application/json" id="prototype-style-state">' + active_pack_state + '</script>'
                 if active_pack_state else '')
    final = seed.replace('<!--PROTOTYPE_PAGES-->', pages + state_tag)
    # T01 装配防御性复核：受控运行时块唯一校验（重复块/缺失块＝具名失败）。
    expected = ['id="project-design-tokens"', 'id="prototype-design-system"', 'id="prototype-config"',
                '/*FREE_EDITOR_START*/', '/*FREE_EDITOR_END*/', '/*FREE_STYLE_START*/', '/*FREE_STYLE_END*/']
    if start_doc:
        expected.append('id="prototype-start-doc"')
    if tree:
        expected.append('id="prototype-page-tree"')
    if icons_injected:
        expected.append('id="prototype-icon-library"')
    if profile:
        expected.append('id="project-profile-css"')
    for name in style_blocks_injected:
        expected.append('data-block="' + name + '"')
    if active_pack_state:
        expected.append('id="prototype-style-state"')
    check_controlled_blocks(final, expected)
    if '<!--PROTOTYPE_PAGES-->' in final:
        raise ValueError('Controlled slot <!--PROTOTYPE_PAGES--> not replaced exactly once')
    return final, len(v.screens)


def collect_tree(root: Path):
    """Walk pages/ as a navigation tree. Returns (ordered_fragments, tree_config).
    Order = depth-first over the directory tree (folder = nav group, files inside
    sorted by name). tree_config maps screen -> group path for the editor's tab bar."""
    ordered = []
    tree = {}

    def walk(d: Path, group: str):
        for f in sorted(d.iterdir(), key=lambda p: (p.is_dir() is False, p.name.lower())):
            if f.is_dir():
                if not f.name.startswith('.'):
                    walk(f, (group + '/' + f.name) if group else f.name)
            elif f.suffix.lower() == '.html':
                text = f.read_text(encoding='utf-8-sig')
                ordered.append((f, text, group))

    walk(root, '')
    tree = {}
    for f, text, group in ordered:
        m = re.search(r'<section\b[^>]*\bdata-screen="([a-zA-Z0-9_-]+)"', text)
        tree[m.group(1) if m else f.stem] = group
    return ordered, tree


def read_pages_text(arg: Path):
    """Returns (pages_text, tree_config, ordered_fragments).

    ordered_fragments = [(path, text, group|None)]：目录模式来自 collect_tree
    （group=页面树分组路径，'/' 连接文件夹名）；单文件模式 group=None（无页面树）。"""
    if arg.is_dir():
        ordered, tree = collect_tree(arg)
        if not ordered:
            raise ValueError(f'no .html fragments found in directory: {arg}')
        pages = '\n'.join(text for _, text, _ in ordered)
        return pages, tree, ordered
    if not arg.exists():
        raise ValueError(f'fragment file not found: {arg}')
    text = arg.read_text(encoding='utf-8-sig')
    return text, None, [(arg, text, None)]


# ====================================================================== 页面命名检查
# 界面上给人看的名字必须是中文（2026-11 键名统一批新增）：
#   E-NAMING-GROUP   页面树分组名（= pages 根目录下的文件夹名，含嵌套层）不含中文
#   E-NAMING-PAGE    页面树里显示的页面名（section.screen 的 data-name，缺省回退 data-screen）不含中文
#   E-NAMING-ID-LEAK 带风格块时，页头标题/页面描述出现内部编号（domBaseId/familyId/packId 值）
_CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def _has_cjk(s):
    return bool(s and _CJK_RE.search(s))


class _ScreenTextCollector(HTMLParser):
    """逐屏收集页面名（data-name）与页头可见文字（.scr-name=页头标题 / .scr-note=页面描述）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.screens = []      # [{'screen': id, 'name': 显示名}]
        self.head_texts = []   # [{'screen': id, 'kind': 'title'|'desc', 'text': str}]
        self._screen = None
        self._cap = None       # [kind, buf, tag]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get('class') or '').split()
        if tag == 'section' and 'screen' in cls:
            self._screen = a.get('data-screen') or ''
            self.screens.append({'screen': self._screen,
                                 'name': a.get('data-name') or self._screen})
        if self._screen is not None and not self._cap:
            if 'scr-name' in cls:
                self._cap = ['title', [], tag]
            elif 'scr-note' in cls:
                self._cap = ['desc', [], tag]

    def handle_data(self, data):
        if self._cap is not None:
            self._cap[1].append(data)

    def handle_endtag(self, tag):
        if self._cap is not None and tag == self._cap[2]:
            text = ''.join(self._cap[1]).strip()
            if text:
                self.head_texts.append({'screen': self._screen,
                                        'kind': self._cap[0], 'text': text})
            self._cap = None
        if tag == 'section':
            self._screen = None


def _style_block_pack_ids(style_blocks):
    """受控块数据 → 内部编号集合（domBaseId/familyId/packId 值）。"""
    ids = set()
    if not isinstance(style_blocks, dict):
        return ids
    reg = style_blocks.get('STYLE-REGISTRY') or {}
    for d in (reg.get('domBases') or []):
        if isinstance(d, dict) and isinstance(d.get('domBaseId'), str):
            ids.add(d['domBaseId'])
    for f in (reg.get('families') or []):
        if isinstance(f, dict) and isinstance(f.get('familyId'), str):
            ids.add(f['familyId'])
    sp = style_blocks.get('STYLE-PACK') or {}
    for p in (sp.get('packs') or []):
        if isinstance(p, dict) and isinstance(p.get('packId'), str):
            ids.add(p['packId'])
    return ids


def _id_leak_hits(text, ids):
    """词边界匹配内部编号：编号前后不能紧挨字母/数字/下划线/连字符，
    防 pk-a 这类短编号在 pk-a1、x-fam-a 等普通词里误报。"""
    hits = []
    for i in sorted(x for x in ids if x):
        pat = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(i) + r'(?![A-Za-z0-9_-])')
        if pat.search(text):
            hits.append(i)
    return hits


def _collect_naming_issues(fragments, style_blocks=None):
    """结构化命名问题（检测唯一出处，dev 输出与 U2 findings 共用）。

    fragments=[(label, text, group|None)]；返回 [{rule,label,...}]，
    rule ∈ E-NAMING-GROUP / E-NAMING-PAGE / E-NAMING-ID-LEAK。"""
    pack_ids = _style_block_pack_ids(style_blocks)
    issues = []
    seen_groups = {}
    for label, text, group in fragments:
        for name in (group.split('/') if group else []):
            seen_groups.setdefault(name, label)
        c = _ScreenTextCollector()
        try:
            c.feed(text)
            c.close()
        except Exception:
            continue  # 结构坏件由 PageValidator/契约检查负责，此处不重复报
        for s in c.screens:
            if not _has_cjk(s['name']):
                issues.append({'rule': 'E-NAMING-PAGE', 'label': label,
                               'screen': s['screen'] or '(无 data-screen)', 'name': s['name']})
        for h in c.head_texts:
            hit = _id_leak_hits(h['text'], pack_ids)
            if hit:
                issues.append({'rule': 'E-NAMING-ID-LEAK', 'label': label,
                               'screen': h['screen'] or '(无 data-screen)',
                               'kind': h['kind'], 'text': h['text'], 'hit': hit})
    for name, label in sorted(seen_groups.items()):
        if not _has_cjk(name):
            issues.append({'rule': 'E-NAMING-GROUP', 'label': label, 'name': name})
    return issues


def _naming_issue_message(issue):
    """命名问题 → 中文提示串（--check 输出口径，含具名错误码与改法）。"""
    r = issue['rule']
    if r == 'E-NAMING-PAGE':
        return ('[E-NAMING-PAGE] %s: 页面「%s」显示名「%s」不含中文——'
                '页面树里给人看的页面名必须是中文，请给 <section class="screen"> '
                '加含中文的 data-name 属性（如 data-name="消息中心"）'
                % (issue['label'], issue['screen'], issue['name']))
    if r == 'E-NAMING-ID-LEAK':
        return ('[E-NAMING-ID-LEAK] %s: 页面「%s」的%s「%s」含风格内部编号 %s——'
                'domBaseId/familyId/packId 等内部编号不得出现在页头标题或页面描述里，'
                '请改写成给人看的中文名'
                % (issue['label'], issue['screen'],
                   '页头标题' if issue['kind'] == 'title' else '页面描述',
                   issue['text'], '、'.join(issue['hit'])))
    return ('[E-NAMING-GROUP] %s: 页面树分组名「%s」不含中文——'
            '界面上给人看的分组名必须是中文，请把 pages 下的文件夹 %s '
            '改为中文名（如「消息中心」）' % (issue['label'], issue['name'], issue['name']))


def check_page_naming(fragments, style_blocks=None):
    """页面命名检查（dev --check 输出）。fragments=[(label, text, group|None)]。

    返回错误消息列表（空=通过）。界面给人看的名字必须含中文字符；内部编号不得上界面。"""
    return [_naming_issue_message(i) for i in _collect_naming_issues(fragments, style_blocks)]


def _naming_findings_project(pages_root, ordered, scope, produced, style_blocks):
    """U2 项目模式命名 findings：分组名全局查；页面名/编号泄漏按 scope 内已产片段查。

    与正式构建共用 _collect_naming_issues 检测逻辑（U2 即拦，不等 U3 构建）。"""
    out = []
    for issue in _collect_naming_issues(_frag_labels(pages_root, ordered), style_blocks):
        if issue['rule'] != 'E-NAMING-GROUP':
            continue
        out.append(_make_finding('E-NAMING-GROUP', issue['label'], 0, None,
                                 '页面树分组名（pages 下文件夹名）含中文',
                                 '分组名「%s」不含中文——请把 pages 下的文件夹 %s '
                                 '改为中文名（如「消息中心」）' % (issue['name'], issue['name'])))
    for pid in scope:
        f = produced.get(pid)
        if f is None:
            continue
        try:
            rel = Path(os.path.relpath(f, pages_root)).as_posix()
        except ValueError:
            rel = f.name
        try:
            text = f.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeDecodeError):
            continue  # 片段可读性已由片段阶段 E-STRUCT 报，此处不重复
        for issue in _collect_naming_issues([(rel, text, None)], style_blocks):
            if issue['rule'] == 'E-NAMING-PAGE':
                out.append(_make_finding('E-NAMING-PAGE', rel, 0, pid,
                                         '页面树显示名（data-name，缺省回退 data-screen）含中文',
                                         '页面「%s」显示名「%s」不含中文——请给 section.screen '
                                         '加含中文的 data-name 属性（如 data-name="消息中心"）'
                                         % (issue['screen'], issue['name'])))
            elif issue['rule'] == 'E-NAMING-ID-LEAK':
                out.append(_make_finding('E-NAMING-ID-LEAK', rel, 0, pid,
                                         '页头标题/页面描述不得出现内部编号（domBaseId/familyId/packId）',
                                         '页面「%s」的%s「%s」含内部编号 %s——请改写成给人看的中文名'
                                         % (issue['screen'],
                                            '页头标题' if issue['kind'] == 'title' else '页面描述',
                                            issue['text'], '、'.join(issue['hit']))))
    return out


def _load_style_blocks_arg(args):
    """--check 模式可选 --style-blocks：为 E-NAMING-ID-LEAK 提供包/族/结构编号。
    文件缺失/JSON 坏 = ValueError（退出码 2，与构建模式同语义）。"""
    if not getattr(args, 'style_blocks', None):
        return None
    if not args.style_blocks.exists():
        raise ValueError(f'style-blocks not found: {args.style_blocks}')
    data = json.loads(args.style_blocks.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('style-blocks must be a JSON object (four controlled blocks)')
    return data


def _frag_labels(root, ordered):
    """片段标签（相对 pages 根，posix）——命名检查错误信息里的文件定位。"""
    frags = []
    for f, text, group in ordered:
        try:
            rel = Path(os.path.relpath(f, root)).as_posix()
        except ValueError:
            rel = Path(f).name
        frags.append((rel, text, group))
    return frags


# ====================================================================== T02.1
# 阶段化契约检查（项目模式）+ 正式构建 qa_receipt 门禁。只读消费 prototype_contract.py
# 与 assets/runtime-contract.json（冻结件，不修改）；回执读写走 qa_receipt.py 冻结接口。

U2_CHECKER_VERSION = 'build/2.1-t02.1'
THEN_DEPTH_LIMIT = 6
_COLOR_OK_VALUES = {'inherit', 'currentcolor', 'transparent', 'none'}


def _make_finding(rule_id, file, line, page, expected, actual, severity='error',
                  eid=None, feature_id=None):
    """U2 finding 统一形状：{ruleId,file,line,page,eid,featureId,expected,actual,severity}。"""
    try:
        line_no = int(line or 0)
    except (TypeError, ValueError):
        line_no = 0
    return {'ruleId': rule_id, 'file': str(file), 'line': line_no, 'page': page,
            'eid': eid, 'featureId': feature_id, 'expected': expected,
            'actual': actual, 'severity': severity}


def _record_path(f, base):
    """回执 inputs 记录路径：优先相对 receipt 目录；跨盘符（relpath ValueError）退回绝对 posix。"""
    try:
        return Path(os.path.relpath(f, base)).as_posix()
    except ValueError:
        return Path(f).resolve().as_posix()


def _is_color_prop(prop):
    p = str(prop).strip().lower()
    return p == 'color' or p.startswith('background') or p.endswith('-color') or p == 'box-shadow'


def _color_value_ok(value):
    v = str(value).strip().lower()
    return (not v) or v in _COLOR_OK_VALUES or 'var(--' in v


class _EidCollector(HTMLParser):
    """轻量 eid 收集器：非 scope 已产片段只取 data-eid 集做覆盖统计，不做检查不产生失败。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.eids = set()

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == 'data-eid' and v:
                self.eids.add(v)


def _collect_eids(path):
    c = _EidCollector()
    try:
        c.feed(Path(path).read_text(encoding='utf-8-sig'))
        c.close()
    except Exception:
        pass
    return c.eids


def _strip_css_comments(text):
    def keep_newlines(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    return re.sub(r'/\*.*?\*/', keep_newlines, text, flags=re.S)


def _scan_declarations(block, base_line, emit):
    """declaration 级扫描：!important/calc( → E-STYLE-SYNTAX；颜色类属性裸值 → E-STYLE-TOKEN。"""
    pos = 0
    for part in block.split(';'):
        start = pos
        pos += len(part) + 1
        text = part.strip()
        if not text:
            continue
        dline = base_line + block.count('\n', 0, start)
        low = text.lower()
        if '!important' in low:
            emit('E-STYLE-SYNTAX', dline, 'flat token-only CSS (no !important)',
                 text[:80])
            continue
        if 'calc(' in low:
            emit('E-STYLE-SYNTAX', dline, 'token-declared values (no calc())', text[:80])
            continue
        if ':' not in text:
            continue
        prop, value = text.split(':', 1)
        if _is_color_prop(prop) and not _color_value_ok(value):
            emit('E-STYLE-TOKEN', dline,
                 'color property = var(--token)/inherit/currentColor/transparent/none',
                 ('%s: %s' % (prop.strip(), value.strip()))[:80])


def scan_style_block(css_text, start_line, emit):
    """片段 <style> 块扫描：@规则白名单外/嵌套块/花括号失衡 → E-STYLE-SYNTAX；声明交 _scan_declarations。

    GPT#5 放行口径：@font-face / @keyframes 允许（纯声明，产物零依赖要求其资源必须内嵌——
    @font-face 的 src 只许 data: URI，外链/相对路径字体 = E-STYLE-FONT-SRC）；
    其余 @ 规则（@import 外链等）照拒。"""
    css = _strip_css_comments(css_text)

    def line_at(pos):
        return start_line + css.count('\n', 0, pos)

    ALLOWED_AT = ('@font-face', '@keyframes')
    depth = 0
    sel_start = 0
    decl_start = 0
    rule_line = start_line
    rule_sel = ''
    nesting_reported = False
    top_allowed = False
    for i, ch in enumerate(css):
        if ch == '{':
            if depth == 0:
                selector = css[sel_start:i].strip()
                rule_line = line_at(sel_start)
                rule_sel = selector
                top_allowed = selector.startswith('@') and selector.split('(')[0].split()[0] in ALLOWED_AT
                if selector.startswith('@') and not top_allowed:
                    emit('E-STYLE-SYNTAX', rule_line,
                         'flat token-only CSS (at-rules: only @font-face/@keyframes allowed)',
                         selector[:60] or '@rule')
                if selector.lower().startswith('@font-face'):
                    block = css[i:css.find('}', i)]
                    for um in re.finditer(r'url\(\s*["\']?([^"\')]+)', block):
                        src = um.group(1).strip()
                        if not src.startswith('data:'):
                            emit('E-STYLE-FONT-SRC', rule_line,
                                 '@font-face src must be embedded data: URI (zero external deps)',
                                 src[:60])
                decl_start = i + 1
            elif not nesting_reported and not top_allowed:
                nesting_reported = True
                emit('E-STYLE-SYNTAX', line_at(i), 'flat CSS (no nested blocks)',
                     'nested block inside %r' % css[sel_start:i].strip()[:40])
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0:
                    if not rule_sel.lower().startswith('@font-face'):
                        _scan_declarations(css[decl_start:i], rule_line, emit)
                    sel_start = i + 1
                    nesting_reported = False
    if depth != 0:
        emit('E-STYLE-SYNTAX', line_at(max(len(css) - 1, 0)),
             'balanced CSS braces', 'unbalanced braces (depth=%d at EOF)' % depth)


def scan_inline_style(raw, line, emit):
    """内联 style 属性扫描（declaration 级，同块级规则）。"""
    for part in str(raw).split(';'):
        text = part.strip()
        if not text:
            continue
        low = text.lower()
        if '!important' in low:
            emit('E-STYLE-SYNTAX', line, 'flat token-only CSS (no !important)', text[:80])
            continue
        if 'calc(' in low:
            emit('E-STYLE-SYNTAX', line, 'token-declared values (no calc())', text[:80])
            continue
        if ':' not in text:
            continue
        prop, value = text.split(':', 1)
        if _is_color_prop(prop) and not _color_value_ok(value):
            emit('E-STYLE-TOKEN', line,
                 'color property = var(--token)/inherit/currentColor/transparent/none',
                 ('%s: %s' % (prop.strip(), value.strip()))[:80])


class StagedPageValidator(PageValidator):
    """T02.1 阶段化片段解析（扩展 PageValidator 的结构规则，补行号与 ruleId）。

    结构违规不走父类 errors 字符串通道，全部转为带 ruleId 的 finding（file/page 由
    构造参数给足）；另捕获 eid 出现点、tabgroup、data-note/data-block 载体、内联
    style 与 <style> 块，供动作/目标/样式阶段检查。"""

    def __init__(self, file_label, page_id):
        super().__init__()
        self.file_label = file_label
        self.page_id = page_id
        self.findings = []
        self.eid_spots = {}          # eid -> [line, ...]
        self.first_screen = None     # (value, line)
        self.tabgroups = set()
        self.staged_bindings = []    # (spec, eid, line)
        self.inline_styles = []      # (line, eid, raw)
        self.style_blocks = []       # (start_line, text)
        self._in_style = False
        self._style_line = 0
        self._style_buf = []

    def _emit(self, rule_id, line, expected, actual, severity='error', eid=None):
        self.findings.append(_make_finding(rule_id, self.file_label, line, self.page_id,
                                           expected, actual, severity, eid))

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = dict(attrs)
        # 结构规则（与 PageValidator 同语义，补行号/ruleId）
        if tag in {'script', 'iframe', 'object', 'embed', 'link', 'base'}:
            self._emit('E-STRUCT', line, 'no executable/external tags in fragment',
                       'tag <%s>' % tag)
        on_keys = [k for k in a if k.startswith('on')]
        if on_keys:
            self._emit('E-ACT-UNKNOWN', line, 'bind events via data-on JSON only',
                       'inline handler %r' % on_keys[0])
        if tag == 'section' and 'screen' in a.get('class', '').split():
            sid = a.get('data-screen')
            if not sid or not re.fullmatch(r'[a-zA-Z0-9_-]+', sid):
                self._emit('E-STRUCT', line, 'unique safe data-screen id', repr(sid))
            else:
                if sid in self.screens:
                    self._emit('E-STRUCT', line, 'one unique screen per fragment',
                               'duplicate screen %r' % sid)
                else:
                    self.screens.append(sid)
                if self.first_screen is None:
                    self.first_screen = (sid, line)
        eid = a.get('data-eid')
        has_on = 'data-on' in a
        if eid:
            self.eid_spots.setdefault(eid, []).append(line)
        if has_on:
            if not eid:
                self._emit('E-ID-EID-MISSING', line,
                           'data-eid on data-on carrier', 'missing data-eid')
            try:
                spec = json.loads(a.get('data-on') or '')
                if not isinstance(spec, dict):
                    raise ValueError('not an object')
                self.staged_bindings.append((spec, eid, line))
            except Exception as e:
                self._emit('E-ACT-TYPE', line, 'data-on must be a JSON object', str(e)[:80])
        if not eid and ('data-note' in a or 'data-block' in a):
            kind = 'data-note' if 'data-note' in a else 'data-block'
            self._emit('E-ID-EID-MISSING', line, 'data-eid on %s carrier' % kind,
                       'missing data-eid')
        tg = a.get('data-tabgroup')
        if isinstance(tg, str) and tg.strip():
            self.tabgroups.add(tg.strip())
        if isinstance(a.get('style'), str) and a['style'].strip():
            self.inline_styles.append((line, eid, a['style']))
        if tag == 'img' and not str(a.get('src', '') or '').startswith('data:'):
            self._emit('E-STRUCT', line, 'img src must be an embedded data URL',
                       repr(a.get('src'))[:60])
        if tag in {'video', 'audio', 'source'} and a.get('src') \
                and not str(a['src']).startswith('data:'):
            self._emit('E-STRUCT', line, 'media src must be an embedded data URL',
                       repr(a.get('src'))[:60])
        if tag == 'video' and a.get('poster') and not str(a['poster']).startswith('data:'):
            self._emit('E-STRUCT', line, 'video poster must be an embedded data URL',
                       repr(a.get('poster'))[:60])
        if tag == 'style':
            self._in_style = True
            self._style_line = line
            self._style_buf = []

    def handle_data(self, data):
        if self._in_style:
            self._style_buf.append(data)

    def handle_endtag(self, tag):
        if tag == 'style' and self._in_style:
            self.style_blocks.append((self._style_line, ''.join(self._style_buf)))
            self._in_style = False


def check_action_object(obj, ctx, line, eid, label, emit, depth=0):
    """校验一个动作对象（click 值 / submit.then / loading.then；thenRecursive 递归）。

    ctx 键：actions(runtime-contract.actions) / page_ids / produced{pid:file|None} /
    phase / eids(本页) / tabgroups(本页) / cur_file / cur_page / defer(挂 deferred)。"""
    if depth > THEN_DEPTH_LIMIT:
        emit('E-ACT-TYPE', line, 'then nesting <= %d' % THEN_DEPTH_LIMIT,
             'too deep at %s' % label, eid=eid)
        return
    keys = [k for k in obj.keys() if k != 'title']
    if not keys:
        emit('E-ACT-TYPE', line, 'exactly one action key', 'no action key in %s' % label, eid=eid)
        return
    if len(keys) > 1:
        emit('E-ACT-TYPE', line, 'exactly one action key (runtime executes the first only)',
             'multiple keys: %s' % ','.join(sorted(keys)), eid=eid)
        return
    k = keys[0]
    v = obj[k]
    meta = ctx['actions'].get(k)
    if not isinstance(meta, dict):
        emit('E-ACT-UNKNOWN', line, 'action key registered in runtime-contract.actions',
             'unknown action %r' % k, eid=eid)
        return

    def need_type(expected, actual):
        emit('E-ACT-TYPE', line, expected, actual, eid=eid)

    def pos_int(raw):
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int) and raw > 0:
            return raw
        if isinstance(raw, str) and raw.isdigit() and int(raw) > 0:
            return int(raw)
        return None

    def screen_target(target, where):
        if not isinstance(target, str) or not target.strip():
            need_type('non-empty screenId string', '%s=%r' % (where, target))
            return
        if target not in ctx['page_ids']:
            emit('E-ACT-TARGET-MISSING', line, 'screenId declared in contract pages[]',
                 '%s=%r not declared in contract' % (where, target), eid=eid)
        elif ctx['produced'].get(target) is None:
            if ctx['phase'] == 'incremental':
                ctx['defer'](_make_finding(
                    'E-ACT-TARGET-PENDING', ctx['cur_file'], line, ctx['cur_page'],
                    'target fragment produced',
                    'declared target %r not produced yet' % target, 'deferred', eid=eid))
            else:
                emit('E-ACT-TARGET-MISSING', line, 'target fragment produced (final)',
                     '%s=%r declared but fragment missing' % (where, target), eid=eid)

    def eid_target(target, where):
        if not isinstance(target, str) or not target.strip():
            need_type('non-empty eid string', '%s=%r' % (where, target))
            return
        if target.startswith('#') or target.startswith('.'):
            emit('E-ACT-TARGET-UNVERIFIED', line, 'static-verifiable eid target',
                 'selector target %r (runtime-only, recorded unverified)' % target,
                 severity='info', eid=eid)
            return
        if target not in ctx['eids']:
            emit('E-ACT-TARGET-MISSING', line, 'target [data-eid] present on this page',
                 '%s=%r not found on page' % (where, target), eid=eid)

    if k == 'goto':
        screen_target(v, 'goto')
    elif k == 'sheet':
        screen_target(v, 'sheet')
        if 'title' in obj and not isinstance(obj['title'], str):
            need_type('sheet.title: string', 'title=%r' % (obj['title'],))
    elif k in ('back', 'close', 'shuffle'):
        if v is not True:
            need_type('%s: true' % k, '%s=%r' % (k, v))
    elif k == 'modal':
        ok = isinstance(v, str) and bool(v.strip())
        if not ok and isinstance(v, dict):
            ok = bool(v) and all(isinstance(x, str) and x.strip() for x in v.values())
        if not ok:
            need_type('modal: non-empty string or {title?,text?}', 'modal=%r' % (v,))
    elif k == 'toast':
        if not isinstance(v, str) or not v.strip():
            need_type('toast: non-empty string', 'toast=%r' % (v,))
    elif k == 'result':
        if not isinstance(v, dict):
            need_type('result: object {ok?,title?,text?,btn?,goto?}', 'result=%r' % (v,))
        else:
            unknown = [x for x in v if x not in ('ok', 'title', 'text', 'btn', 'goto')]
            if unknown:
                need_type('result keys subset of {ok,title,text,btn,goto}',
                          'unknown key(s): %s' % ','.join(sorted(unknown)))
            if 'ok' in v and not isinstance(v['ok'], bool):
                need_type('result.ok: bool', 'ok=%r' % (v['ok'],))
            for fld in ('title', 'text', 'btn'):
                if fld in v and not isinstance(v[fld], str):
                    need_type('result.%s: string' % fld, '%s=%r' % (fld, v[fld]))
            if 'goto' in v:
                screen_target(v['goto'], 'result.goto')
    elif k == 'loading':
        if pos_int(v) is None:
            need_type('loading: positive integer (ms)', 'loading=%r' % (v,))
        th = obj.get('then')
        if th is not None:
            if isinstance(th, dict):
                check_action_object(th, ctx, line, eid, label + '.then', emit, depth + 1)
            else:
                need_type('loading.then: action object', 'then=%r' % (th,))
    elif k == 'submit':
        if not isinstance(v, dict):
            need_type('submit: object {toast?,loading?,then?}', 'submit=%r' % (v,))
        else:
            unknown = [x for x in v if x not in ('toast', 'loading', 'then')]
            if unknown:
                need_type('submit keys subset of {toast,loading,then}',
                          'unknown key(s): %s' % ','.join(sorted(unknown)))
            if 'toast' in v and not isinstance(v['toast'], str):
                need_type('submit.toast: string', 'toast=%r' % (v['toast'],))
            if 'loading' in v and pos_int(v['loading']) is None:
                need_type('submit.loading: positive integer (ms)', 'loading=%r' % (v['loading'],))
            if 'then' in v:
                th = v['then']
                if isinstance(th, dict):
                    check_action_object(th, ctx, line, eid, label + '.then', emit, depth + 1)
                else:
                    need_type('submit.then: action object (doSubmit:2990 recurses runAction)',
                              'then=%r' % (th,))
    elif k == 'tab':
        m = re.fullmatch(r'([A-Za-z0-9_-]+)(?::\d+)?', v) if isinstance(v, str) else None
        if not m:
            need_type('tab: "group:index" string', 'tab=%r' % (v,))
        elif m.group(1) not in ctx['tabgroups']:
            emit('E-ACT-TARGET-MISSING', line,
                 'tab group present on this page ([data-tabgroup])',
                 'group %r not found on page' % m.group(1), eid=eid)
    elif k in ('toggle', 'switch', 'clear', 'scroll'):
        eid_target(v, k)
    elif k == 'check':
        if v is not None and (not isinstance(v, str) or not v.strip()):
            need_type('check: selector string (runtime-bounded)', 'check=%r' % (v,))
    elif k == 'link':
        if not isinstance(v, str) or not re.match(r'^https?://\S+$', v.strip() or ''):
            need_type('link: http(s) URL string', 'link=%r' % (v,))
    elif k == 'lang':
        if v not in ('en', 'zh', 'toggle'):
            need_type("lang: 'en'|'zh'|'toggle'", 'lang=%r' % (v,))


def run_project_check(args, parser):
    """T02.1 项目模式阶段化检查：契约 → 命名 → 片段 → 覆盖；--report 写 U2 回执。

    页面命名检查（2026-11 键名统一批接入）：分组名/页面名须含中文；带 --style-blocks 时
    页头文字不得出现内部编号（domBaseId/familyId/packId）——U2 即拦，不等 U3 构建。
    退出：0=incremental ready / final passed；1=fail；2=用法/IO。"""
    try:
        import prototype_contract
    except ImportError as e:
        print('ERROR prototype_contract not available: %s' % e)
        raise SystemExit(2)

    # -- 解析 pages_root / start_doc（两种触发式）--
    if args.check is not None and args.start_doc is not None:
        pages_root = args.check
        start_doc = args.start_doc
    else:
        pdir = args.project_dir
        if not pdir.is_dir():
            parser.error('--project-dir not found: %s' % pdir)
        pages_root = pdir / 'pages'
        start_doc = pdir / 'intake-开工文档.md'
        if not start_doc.is_file():
            cands = sorted(p for p in pdir.glob('*.md') if p.is_file())
            if len(cands) == 1:
                start_doc = cands[0]
        if not pages_root.is_dir():
            parser.error('--project-dir/pages not found: %s' % pages_root)
        if not start_doc.is_file():
            parser.error('--project-dir intake not found (intake-开工文档.md 或唯一 *.md): %s' % pdir)
    if not pages_root.is_dir():
        parser.error('--check project mode requires a pages directory: %s' % pages_root)
    phase = args.phase
    if phase == 'final' and args.scope:
        parser.error('--scope is only valid with --phase incremental')

    # -- runtime-contract.json（只读消费）--
    rt_path = ROOT / 'assets/runtime-contract.json'
    try:
        rt = json.loads(rt_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        print('ERROR runtime-contract unreadable: %s' % e)
        raise SystemExit(2)
    rt_actions = rt.get('actions') if isinstance(rt.get('actions'), dict) else {}

    # -- 契约 --
    try:
        loaded = prototype_contract.loadContract(start_doc, pages_root=pages_root)
    except OSError as e:
        print('ERROR intake unreadable: %s' % e)
        raise SystemExit(2)
    contract = loaded.get('contract') or {}
    claims = loaded.get('claims') or []
    contract_errors = list(loaded.get('errors') or [])
    page_by_id = {}
    path_to_pid = {}
    for p in (contract.get('pages') or []):
        if not isinstance(p, dict) or not isinstance(p.get('id'), str):
            continue
        pid = p['id']
        page_by_id[pid] = p
        path = p.get('path')
        if isinstance(path, str) and path:
            path_to_pid[Path(path).as_posix()] = pid
            path_to_pid[Path(path).name] = pid
        path_to_pid[pid] = pid
    page_ids = set(page_by_id)
    produced = {}
    for pid, p in page_by_id.items():
        path = p.get('path')
        f = None
        if isinstance(path, str) and path:
            for cand in (pages_root / path, pages_root / Path(path).name):
                if cand.is_file():
                    f = cand
                    break
        produced[pid] = f

    # -- 契约错误分区：增量下「声明页未产」→ deferred；其余=硬错误 --
    findings = []
    deferred = []
    hard = []
    for e in contract_errors:
        if (phase == 'incremental' and e.get('ruleId') == 'E-ID-PAGE-UNDECLARED'
                and 'declared but fragment file missing' in str(e.get('message', ''))):
            key = str(e.get('file', ''))
            pid = path_to_pid.get(key) or path_to_pid.get(Path(key).name)
            deferred.append(_make_finding('E-ACT-TARGET-PENDING', key, 0, pid,
                                          'contract page fragment produced',
                                          'declared but not produced yet', 'deferred'))
        else:
            hard.append(e)
    for e in hard:
        findings.append(_make_finding(e.get('ruleId'), str(e.get('file')), e.get('line'),
                                      None, 'contract rule satisfied', str(e.get('message'))))

    # -- scope（仅增量）--
    if phase == 'incremental':
        if args.scope:
            scope = [s.strip() for s in args.scope.split(',') if s.strip()]
            unknown = [s for s in scope if s not in page_ids]
            if unknown:
                parser.error('--scope pageId(s) not declared in contract: %s' % ', '.join(unknown))
            if len(set(scope)) != len(scope):
                parser.error('--scope contains duplicate pageId(s)')
        else:
            scope = sorted(page_ids)
    else:
        scope = sorted(page_ids)

    result = 'fail'
    uncovered = []
    features_expected = 0
    features_covered = 0
    generated_pages = sum(1 for f in produced.values() if f is not None)
    produced_eids = {}

    if not hard:
        # -- 页面命名检查（U2 阶段即拦，不等 U3 构建；带 --style-blocks 时含内部编号泄漏）--
        try:
            sb_data = _load_style_blocks_arg(args)
        except ValueError as e:
            print('ERROR %s' % e)
            raise SystemExit(2)
        try:
            ordered_naming, _tree_naming = collect_tree(pages_root)
        except ValueError:
            ordered_naming = []
        findings.extend(_naming_findings_project(pages_root, ordered_naming, scope, produced, sb_data))
        # -- 片段阶段化检查（增量=scope 内；final=全部契约页）--
        for pid in scope:
            f = produced.get(pid)
            if f is None:
                continue
            try:
                rel = Path(os.path.relpath(f, pages_root)).as_posix()
            except ValueError:
                rel = f.name
            v = StagedPageValidator(rel, pid)
            try:
                v.feed(f.read_text(encoding='utf-8-sig'))
                v.close()
            except (OSError, UnicodeDecodeError) as e:
                findings.append(_make_finding('E-STRUCT', rel, 0, pid, 'fragment readable', str(e)))
                produced_eids[pid] = set()
                continue
            findings.extend(v.findings)
            for dup_eid, lines in v.eid_spots.items():
                if len(lines) > 1:
                    for ln in lines:
                        findings.append(_make_finding('E-ID-EID-DUP', rel, ln, pid,
                                                      'unique data-eid within fragment',
                                                      'data-eid %r appears %d times'
                                                      % (dup_eid, len(lines)), eid=dup_eid))
            if v.first_screen and v.first_screen[0] != pid:
                findings.append(_make_finding('E-CONTRACT-SCHEMA', rel, v.first_screen[1], pid,
                                              'first section data-screen == contract page id',
                                              'data-screen=%r' % v.first_screen[0]))
            # 样式（declaration 级）；契约 exceptions[] 匹配 page+target+property 豁免 E-STYLE-TOKEN
            excs = [x for x in (contract.get('exceptions') or []) if isinstance(x, dict)]

            def F(rule_id, line_, expected, actual, severity='error', eid=None,
                  _pid=pid, _rel=rel, _excs=excs):
                if rule_id == 'E-STYLE-TOKEN' and severity == 'error':
                    prop = str(actual).split(':', 1)[0].strip()
                    for exc in _excs:
                        if (exc.get('page') == _pid
                                and exc.get('target') in (None, '*', eid)
                                and exc.get('property') in (None, '*', prop)):
                            return  # 豁免
                findings.append(_make_finding(rule_id, _rel, line_, _pid,
                                              expected, actual, severity, eid))

            for start_line, css in v.style_blocks:
                scan_style_block(css, start_line, F)
            for st_line, _eid, raw in v.inline_styles:
                scan_inline_style(raw, st_line, F)
            # 动作与目标
            ctx = {'actions': rt_actions, 'page_ids': page_ids, 'produced': produced,
                   'phase': phase, 'eids': set(v.eid_spots), 'tabgroups': v.tabgroups,
                   'cur_file': rel, 'cur_page': pid, 'defer': deferred.append}
            for spec, b_eid, b_line in v.staged_bindings:
                for key in spec:
                    if key != 'click':
                        F('E-ACT-UNKNOWN', b_line, "top-level event key must be 'click'",
                          'unknown event key %r' % key, eid_=b_eid)
                if 'click' not in spec:
                    F('E-ACT-TYPE', b_line, "data-on carries a 'click' action",
                      'missing click', eid_=b_eid)
                    continue
                click = spec['click']
                if not isinstance(click, dict):
                    F('E-ACT-TYPE', b_line, 'click: action object', 'click=%r' % (click,),
                      eid_=b_eid)
                    continue
                check_action_object(click, ctx, b_line, b_eid, 'click', F)
            produced_eids[pid] = set(v.eid_spots)
            # 装饰声明安全网（增量 scope 内；final 由 loadContract 片段对账覆盖）
            if phase == 'incremental':
                for c in claims:
                    if c.get('decorative') is True and c.get('page') == pid:
                        d_eid = c.get('eid')
                        if not v.eid_spots.get(d_eid):
                            findings.append(_make_finding(
                                'E-ID-EID-MISSING', rel, 0, pid,
                                'decorative claim eid present in fragment',
                                'claim %r eid %r not found' % (c.get('claimId'), d_eid),
                                eid=d_eid))
        # 非 scope 已产片段：轻量收集 eid 供覆盖统计（不检查、不失败）
        for pid, f in produced.items():
            if pid not in produced_eids and f is not None:
                produced_eids[pid] = _collect_eids(f)

        # -- 覆盖：每非装饰 feature ≥1 条 claim 且 claim.eid 在对应页实存 --
        for pid, p in page_by_id.items():
            page_path = p.get('path')
            page_label = Path(str(page_path)).as_posix() if isinstance(page_path, str) and page_path else pid
            for feat in (p.get('features') or []):
                if not isinstance(feat, dict) or feat.get('kind') == 'decorative':  # 死分支：契约 FEATURE_KINDS 无 decorative（装饰语义走 claim.decorative:true）——保留防旧文档漏改，勿扩展
                    continue
                fid = feat.get('id')
                features_expected += 1
                eids = produced_eids.get(pid, set())
                covered = any(c.get('decorative') is not True and c.get('page') == pid
                              and fid in (c.get('featureIds') or [])
                              and isinstance(c.get('eid'), str) and c.get('eid') in eids
                              for c in claims)
                if covered:
                    features_covered += 1
                elif phase == 'final':
                    findings.append(_make_finding('E-COVER-FEATURE', page_label, 0, pid,
                                                  '>=1 non-decorative claim whose eid exists on page',
                                                  'feature %r uncovered' % fid, feature_id=fid))
                    uncovered.append(fid)
        error_findings = [x for x in findings if x['severity'] == 'error']
        if phase == 'incremental':
            result = 'fail' if error_findings else 'ready'
        else:
            result = 'fail' if (error_findings or deferred or uncovered) else 'passed'
    else:
        error_findings = [x for x in findings if x['severity'] == 'error']

    ok = result in ('ready', 'passed')
    unverified_count = sum(1 for x in findings if x['severity'] == 'info')

    # -- 输出 --
    scope_text = ','.join(scope) if phase == 'incremental' else '-'
    print('U2 %s %s | intake=%s | pages=%s | scope=%s' %
          (phase, result, Path(start_doc).name, pages_root, scope_text))
    for x in error_findings:
        print('  %s:%s:%s: %s' % (x['ruleId'], x['file'], x['line'], x['actual']))
    for x in deferred:
        print('  DEFERRED %s %s:%s:%s: %s' % (x['page'], x['ruleId'], x['file'], x['line'], x['actual']))
    print('findings: %d error, %d deferred, %d unverified | coverage: pages %d/%d produced, '
          'features %d/%d covered, deferred %d'
          % (len(error_findings), len(deferred), unverified_count,
             generated_pages, len(page_ids), features_covered, features_expected, len(deferred)))

    # -- U2 回执 --
    if args.report is not None:
        try:
            from qa_receipt import make_receipt, bundle_digest, file_sha256
        except ImportError as e:
            print('ERROR qa_receipt not available for --report: %s' % e)
            raise SystemExit(2)
        input_files = [Path(start_doc)] + sorted(pages_root.rglob('*.html')) + [rt_path]
        if args.design_system:
            input_files.append(args.design_system)  # design若用（显式给定时入回执）
        if args.style_blocks:
            # GPT#1 对称修复（2026-11-21 审查定案）：formal gate 侧（gate_inputs）要求 style-blocks
            # 绑定进回执，生成侧此前漏记——带 --style-blocks 的正式构建必 FAIL（生成/校验不对称）
            input_files.append(args.style_blocks)
        base = Path(args.report).resolve().parent
        items = []
        inputs = []
        for f in input_files:
            f = Path(f).resolve()
            rel = _record_path(f, base)
            items.append(('project/', rel, f))
            inputs.append({'path': rel, 'sha256': file_sha256(f)})
        try:
            receipt = make_receipt(reportVersion=1, checkerVersion=U2_CHECKER_VERSION,
                                   kind='check', station='U2', phase=phase,
                                   scope=(sorted(scope) if phase == 'incremental' else None),
                                   inputDigest=bundle_digest(items), inputs=inputs,
                                   result=result, findings=findings + deferred,
                                   coverage={'expectedPages': len(page_ids),
                                             'generatedPages': generated_pages,
                                             'featuresExpected': features_expected,
                                             'featuresCovered': features_covered,
                                             'deferred': len(deferred),
                                             'unverified': unverified_count},
                                   generatedAt=datetime.now(timezone.utc).isoformat(timespec='seconds'))
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                                   encoding='utf-8')
            print('U2 report: %s' % args.report.resolve())
        except OSError as e:
            print('ERROR report write: %s' % e)
            raise SystemExit(2)
    raise SystemExit(0 if ok else 1)


def formal_gate(args, parser):
    """T02.1 正式构建门禁：--start-doc 构建前校验 U1 回执 + U2(final) 回执。

    qa_receipt 不可用 → 'qa_receipt not ready; formal gate disabled' exit 2（不产件）；
    回执缺失/无效/过期 → 具名原因 exit 1。通过后返回门禁输入清单（供 U3 回执）。"""
    if not args.u1_receipt or not args.u2_receipt:
        parser.error('formal build (--start-doc) requires --u1-receipt and --u2-receipt '
                     '(qa_receipt gate)')
    try:
        from qa_receipt import validate_receipt
    except ImportError:
        print('qa_receipt not ready; formal gate disabled')
        raise SystemExit(2)
    rt_path = ROOT / 'assets/runtime-contract.json'
    if not rt_path.is_file():
        raise ValueError('runtime-contract.json missing: %s' % rt_path)
    if args.pages.is_dir():
        ordered, _tree = collect_tree(args.pages)
        fragments = [f for f, _text, _group in ordered]
    else:
        fragments = [args.pages]
    # design 只在显式 --design-system 时进入门禁期望集（与 U2 回执「design若用」同口径；
    # 默认 skill 资产 design-system.json 不计入——U2 检查阶段的回执不消费它）
    gate_inputs = [args.start_doc] + fragments + [rt_path]
    if args.design_system:
        gate_inputs.append(args.design_system)
    # GPT#1：风格包文件绑定进回执——U2 通过后再改 style-blocks，旧回执即失效（哈希重验不匹配）
    if getattr(args, 'style_blocks', None):
        gate_inputs.append(args.style_blocks)
    # 硬值 lint 门禁（丁线三件之一）：正式构建前对全部片段跑 lint_tokens，FAIL 不产件。
    # lint 靶=片段目录（页面源），非装配产物——装配产物含编辑器壳自有样式，不属生成纪律约束面。
    # 带 --style-blocks 时一并传给 lint_tokens：包内扩展键生成的 --sp-<键名> 进入已知变量集合，
    # 否则页面引用扩展参数变量会被 E-TOKEN-UNKNOWN-VAR 误拦（lint_tokens 新增可选参数）。
    import subprocess
    ds = args.design_system or (ROOT / 'assets/design-system.json')
    lint_pages = args.pages if args.pages.is_dir() else args.pages.parent
    lint_cmd = [sys.executable, str(ROOT / 'scripts' / 'lint_tokens.py'),
                str(lint_pages), '--design-system', str(ds)]
    if getattr(args, 'style_blocks', None):
        lint_cmd += ['--style-blocks', str(args.style_blocks)]
    lint = subprocess.run(lint_cmd,
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=180)
    if lint.returncode != 0:
        print('FAIL formal gate lint_tokens（硬值必须归因令牌；白名单口径见 token-minimum）：')
        print((lint.stdout or '') + (lint.stderr or ''))
        raise SystemExit(1)
    # 组件样式写死值门禁：seed 组件段的裸色/裸圆角必须接令牌或在 chooser 换肤规则表内
    comp = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'verify_component_css.py')],
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=60)
    if comp.returncode != 0:
        print('FAIL formal gate verify_component_css（组件段写死值必须接令牌或换肤规则表）：')
        print((comp.stdout or '') + (comp.stderr or ''))
        raise SystemExit(1)
    print('formal gate: verify_component_css ok')
    # TODO 占位门禁（2026-11-23 端到端实证：gen_tokens 未填槽的 TODO-SEMANTIC 进产物后，
    # 壳层 UI（弹窗等非包作用域元素）读非法颜色渲染透明——verify_blocks 拦数据侧，此处拦输入侧兜底）
    todo_hits = []
    if getattr(args, 'style_blocks', None) and Path(args.style_blocks).is_file():
        if re.search(r'TODO', Path(args.style_blocks).read_text(encoding='utf-8', errors='replace')):
            todo_hits.append('style-blocks: ' + str(args.style_blocks))
    if getattr(args, 'design_system', None) and Path(args.design_system).is_file():
        if re.search(r'TODO', Path(args.design_system).read_text(encoding='utf-8', errors='replace')):
            todo_hits.append('design-system: ' + str(args.design_system))
    if getattr(args, 'pages', None) and Path(args.pages).is_dir():
        for p in sorted(Path(args.pages).rglob('*.html')):
            if re.search(r'TODO-SEMANTIC|:TODO-', p.read_text(encoding='utf-8', errors='replace')):
                todo_hits.append('fragment: ' + str(p))
    if todo_hits:
        print('FAIL formal gate TODO 占位（占位值进产物会让壳层 UI 读非法颜色而透明；'
              '请回 editor_gen_tokens 逐槽填真实语义值，或人工填毕后再构建）：')
        for h in todo_hits[:10]:
            print('  - ' + h)
        raise SystemExit(1)
    print('formal gate: TODO 占位扫描 ok')
    r1 = validate_receipt(args.u1_receipt, 'U1')
    if not r1.get('valid'):
        print('FAIL formal gate U1: %s' % r1.get('reason'))
        raise SystemExit(1)
    r2 = validate_receipt(args.u2_receipt, 'U2', phase='final', expected_inputs=gate_inputs)
    if not r2.get('valid'):
        print('FAIL formal gate U2: %s' % r2.get('reason'))
        raise SystemExit(1)
    print('formal gate ok: U1 receipt + U2(final) receipt valid against current inputs')
    return gate_inputs


def _emit_code_asset(html_text: str, asset_dir: Path) -> str:
    """V06 转化线交付形态：单文件组装结果 → 代码+asset。
    外置顺序固定：先图片（HTML 属性内 dataURL），再 <style>，再可执行 <script>；
    link/script 引用落在原位置，层叠与执行顺序不变。
    CSS 落 assets/ 根（file:// 字体目录隔离，K10 同源教训），相对引用改写 url(assets/fonts/…) → url(fonts/…)。
    prototype-* JSON 契约块、内容含 '</script' 字面量的脚本一律保留内嵌（file:// 直开不依赖 fetch）。"""
    import base64 as _b64

    counter = {'img': 0, 'css': 0, 'js': 0}

    def _safe(base):
        return re.sub(r'[^A-Za-z0-9_-]', '-', base).strip('-') or 'block'

    def img_repl(m):
        counter['img'] += 1
        ext = m.group(1).lower()
        if ext in ('jpeg', 'jpg'):
            ext = 'jpg'
        name = 'img-%04d.%s' % (counter['img'], ext)
        (asset_dir / 'assets' / 'img' / name).write_bytes(_b64.b64decode(m.group(2)))
        return 'src="assets/img/%s"' % name

    html_text = re.sub(r'src="data:image/([\w.+-]+);base64,([^"]+)"', img_repl, html_text)

    def style_repl(m):
        attrs, body = m.group(1), m.group(2)
        if not body.strip():
            return m.group(0)
        counter['css'] += 1
        mid = re.search(r'id="([^"]+)"', attrs)
        slug = _safe(mid.group(1)) if mid else 'css-%03d' % counter['css']
        fname = '%03d-%s.css' % (counter['css'], slug)
        # CSS 落 assets/ 根：file:// 的字体加载按目录隔离（仅同目录及子目录），
        # CSS 若进 css/ 子目录，@font-face 兄弟目录字体引用会被 Chromium 拦截；
        # 相对引用改写 url(assets/…) → url(fonts/)（assets/fonts 是 CSS 的同级子目录，合法）
        body = body.replace('url(assets/fonts/', 'url(fonts/').replace('src(assets/fonts/', 'src(fonts/')
        (asset_dir / 'assets' / fname).write_text(body, encoding='utf-8')
        keep_id = ' id="%s"' % mid.group(1) if mid else ''
        return '<link%s rel="stylesheet" href="assets/%s">' % (keep_id, fname)

    html_text = re.sub(r'<style([^>]*)>(.*?)</style>', style_repl, html_text, flags=re.S)

    def script_repl(m):
        attrs, body = m.group(1), m.group(2)
        if re.search(r'type="[^"]*json', attrs):
            return m.group(0)
        if not body.strip() or '</script' in body.lower():
            return m.group(0)
        counter['js'] += 1
        fname = 'script-%03d.js' % counter['js']
        (asset_dir / 'assets' / 'js' / fname).write_text(body, encoding='utf-8')
        return '<script src="assets/js/%s"></script>' % fname

    html_text = re.sub(r'<script([^>]*)>(.*?)</script>', script_repl, html_text, flags=re.S)
    return html_text


def _capture_pack_shots(output: Path):
    """--style-blocks 构建后回填风格卡截图缩略（STYLE-PACK packs[].screenshot），调 capture_pack_shots.cjs。
    node/playwright 缺位或截帧失败=降级（面板卡片走色板条缩略，style-panel-spec §二），只告警不失败构建。"""
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        print('WARN pack-shots: node 不在 PATH，风格卡降级为色板条缩略')
        return
    try:
        r = subprocess.run([node, str(ROOT / 'scripts' / 'capture_pack_shots.cjs'), str(output)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace',
                           env=dict(os.environ, PROTO_EDIT_PASSWORD=EDIT_PASSWORD), timeout=300)
    except subprocess.TimeoutExpired:
        print('WARN pack-shots: 截帧超时（300s），风格卡降级为色板条缩略')
        return
    lines = [ln for ln in ((r.stdout or '') + (r.stderr or '')).splitlines() if ln.strip()]
    if r.returncode == 0:
        print('pack-shots: ' + (lines[-1] if lines else 'ok'))
    else:
        print('WARN pack-shots 失败，风格卡降级为色板条缩略: ' + (lines[-1] if lines else 'exit %d' % r.returncode))


def _write_u3_receipt(args, gate_inputs, count):
    """T02.1 正式构建 U3 回执：kind=build/station=U3/result=passed；
    coverage.artifactHash=最终产物文件字节 sha256（AGENTS.md/头注写完后计算）。"""
    if not args.u3_report:
        print('formal build: --u3-report not given; U3 receipt skipped')
        return
    from qa_receipt import make_receipt, bundle_digest, file_sha256
    base = args.u3_report.resolve().parent
    items = []
    inputs = []
    for f in gate_inputs:
        f = Path(f).resolve()
        rel = _record_path(f, base)
        items.append(('project/', rel, f))
        inputs.append({'path': rel, 'sha256': file_sha256(f)})
    artifact_hash = file_sha256(args.output)
    receipt = make_receipt(reportVersion=1, checkerVersion=U2_CHECKER_VERSION, kind='build',
                           station='U3', phase=None, scope=None,
                           inputDigest=bundle_digest(items), inputs=inputs, result='passed',
                           findings=[], coverage={'artifactHash': artifact_hash, 'screens': count},
                           generatedAt=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    args.u3_report.parent.mkdir(parents=True, exist_ok=True)
    args.u3_report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                              encoding='utf-8')
    print('U3 report: %s' % args.u3_report.resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pages', type=Path, help='fragment file or directory of fragments')
    parser.add_argument('--check', type=Path, help='pre-check a fragment or directory, no build')
    parser.add_argument('--title')
    parser.add_argument('--project-id', default=None)
    parser.add_argument('--design-system', type=Path)
    parser.add_argument('--style-blocks', type=Path,
                        help='受控块数据 JSON（键=STYLE-REGISTRY/STYLE-PACK/COMPONENT-PACK/STYLE-CONTRACT 四块全量）；'
                             '传入则注入产物（面板走正式态：族分组/真截图/皮肤包组件），缺省=九槽降级态；'
                             '构建后自动跑 verify_blocks 校验，FAIL 即构建 FAIL；'
                             '与 --check 同用时为页面命名检查（E-NAMING-ID-LEAK）提供内部编号名单')
    parser.add_argument('--active-pack', default=None,
                        help='选中的皮肤包 packId（须在 --style-blocks 的 STYLE-PACK.packs 内）：'
                             '构建时注入 prototype-style-state 初始状态，产物打开即应用该风格'
                             '（用户在选型环节选中的风格=交付物的初始外观，而非「原始方案」）')
    parser.add_argument('--start-doc', type=Path, help='embed the start-doc markdown into the deliverable (prototype-start-doc)')
    parser.add_argument('--device', choices=sorted(DEVICE_SIZES), default=None,
                        help='override the device label for AGENTS.md (default: derived from fragment .device classes)')
    parser.add_argument('--profile', default=PROJECT_PROFILE_NONE,
                        help='explicit project profile to inject (default: none; e.g. mall — opt-in only, never auto-enabled)')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--conversion', action='store_true',
                        help='V06 转化线标记：产物 html 标 data-conversion，编辑器换肤跳过组件重写层'
                             '（页面 CSS 自带完整设计，K9）')
    parser.add_argument('--icon-families', default=None,
                        help='comma-separated icon family names to inject (default: all); '
                             'e.g. lucide for inline-SVG 转化线')
    parser.add_argument('--asset-out', type=Path, default=None,
                        help='V06 转化线交付形态：输出 代码+asset 目录（DIR/index.html + DIR/assets/，'
                             '图片/样式/脚本外置、页面 DOM 与 JSON 契约块内嵌）；缺省=单文件模式')
    parser.add_argument('--docs', nargs='+', type=Path, default=None,
                        help='copy project docs into the deliverable folder as docs/<filename> '
                             '(client rebuild-skill supply: 盘问/页面地图/设计规范等；缺失即构建 FAIL)')
    # ---- T02.1 项目模式阶段化检查参数 ----
    parser.add_argument('--phase', choices=('incremental', 'final'), default=None,
                        help='project check phase; REQUIRED with --check+--start-doc or --project-dir '
                             '(incremental: scope pages + deferred pending targets; final: full closeout)')
    parser.add_argument('--project-dir', type=Path, default=None,
                        help='project root for project check mode (expects DIR/pages + DIR/intake-开工文档.md)')
    parser.add_argument('--scope', default=None,
                        help='comma-separated pageIds for --phase incremental (default: all contract pages)')
    parser.add_argument('--report', type=Path, default=None,
                        help='write U2 check receipt (kind=check, station=U2) to this path')
    # ---- T02.1 正式构建门禁参数（--pages+--start-doc 构建模式）----
    parser.add_argument('--u1-receipt', type=Path, default=None,
                        help='formal build gate: U1 contract receipt (required with --start-doc build)')
    parser.add_argument('--u2-receipt', type=Path, default=None,
                        help='formal build gate: U2 final check receipt, phase=final (required with --start-doc build)')
    parser.add_argument('--u3-report', type=Path, default=None,
                        help='formal build: write U3 build receipt (kind=build, station=U3, artifactHash) to this path')
    args = parser.parse_args()

    if args.check and args.pages:
        parser.error('--check and --pages are mutually exclusive')
    if args.check and (args.title or args.output):
        parser.error('--check cannot be combined with --title/--output')
    # T02.1 门卫：--phase/--scope/--report 仅限项目检查模式；--u1/u2/u3 仅限正式构建模式
    if args.asset_out:
        # 代码+asset 模式：产物落 DIR/index.html，AGENTS/截图回填/U3 哈希全部作用在该文件上
        args.output = args.asset_out / 'index.html'
    project_check = (args.check is not None and args.start_doc is not None) or args.project_dir is not None
    if (args.phase or args.scope or args.report) and not project_check:
        parser.error('--phase/--scope/--report only apply to project check mode '
                     '(--check+--start-doc, or --project-dir)')
    if project_check and not args.phase:
        parser.error('--phase (incremental|final) is required for project check mode')
    if args.check is not None and args.start_doc is not None and args.project_dir is not None:
        parser.error('--project-dir cannot be combined with --check+--start-doc')
    if (args.u1_receipt or args.u2_receipt or args.u3_report) \
            and not (args.pages and args.start_doc and not args.check):
        parser.error('--u1-receipt/--u2-receipt/--u3-report only apply to formal build mode '
                     '(--pages+--start-doc)')

    try:
        if project_check:
            run_project_check(args, parser)  # T02.1 项目模式（--check+--start-doc 或 --project-dir）：SystemExit(0/1/2)
        if args.check:
            target = args.check
            if not target.exists():
                raise ValueError(f'--check target not found: {target}')
            if target.is_dir():
                pages_text, _tree, ordered = read_pages_text(target)
                v = validate_merged(pages_text)
                naming = check_page_naming(_frag_labels(target, ordered), _load_style_blocks_arg(args))
                errors = list(v.errors) + naming
                if errors:
                    print('FAIL ' + str(target) + ' [dev-mode 非规格验收]')
                    for e in errors:
                        print('  - ' + e)
                    raise SystemExit(1)
                print(f'PASS {target} (merged: {len(v.screens)} screen(s), {len(v.bindings)} binding(s), '
                      f'naming ok: {len(ordered)} fragment(s)) [dev-mode 非规格验收]')
                raise SystemExit(0)
            v, merged_count = validate_fragment(target)
            naming = check_page_naming(
                [(target.name, target.read_text(encoding='utf-8-sig'), None)],
                _load_style_blocks_arg(args))
            errors = list(v.errors) + naming
            if errors:
                print('FAIL ' + str(target) + ' [dev-mode 非规格验收]')
                for e in errors:
                    print('  - ' + e)
                raise SystemExit(1)
            note = f', merged with {merged_count} sibling fragment(s) for cross-page targets' if merged_count else ''
            print(f'PASS {target} ({len(v.screens)} screen(s), {len(v.bindings)} binding(s){note}, naming ok)'
                  ' [dev-mode 非规格验收]')
            raise SystemExit(0)

        if not args.pages or not args.title or not args.output:
            parser.error('--pages/--title/--output are required for build mode')

        # T02.1 正式构建门禁：--start-doc 构建必须持有效 U1 + U2(final) 回执；不通过不产件
        gate_inputs = None
        if args.start_doc:
            if not args.start_doc.exists():
                raise ValueError(f'start-doc not found: {args.start_doc}')
            gate_inputs = formal_gate(args, parser)

        if args.output.exists():
            parser.error('Output already exists; move the previous build to build/history/ or choose a new destination.')

        design = None
        if args.design_system:
            design = json.loads(args.design_system.read_text(encoding='utf-8'))
        if design is None:
            # T01：design 在 main 读取一次（风格名文案同源），再传给 compose，避免双读漂移
            design = json.loads((ROOT / 'assets/design-system.json').read_text(encoding='utf-8'))
        style_blocks = None
        if args.style_blocks:
            if not args.style_blocks.exists():
                raise ValueError(f'style-blocks not found: {args.style_blocks}')
            style_blocks = json.loads(args.style_blocks.read_text(encoding='utf-8'))
        if args.active_pack and style_blocks:
            _ap = next((p for p in (style_blocks.get('STYLE-PACK', {}).get('packs') or [])
                        if p.get('packId') == args.active_pack), None)
            if _ap is not None:
                design = overlay_active_pack(design, _ap)
        start_doc = None
        if args.start_doc:
            if not args.start_doc.exists():
                raise ValueError(f'start-doc not found: {args.start_doc}')
            start_doc = args.start_doc.read_text(encoding='utf-8')
        pages, tree, ordered = read_pages_text(args.pages)
        # 页面命名检查（正式构建门禁）：界面上给人看的名字必须是中文；
        # 带 --style-blocks 时同时查内部编号（domBaseId/familyId/packId）是否泄漏进页头文字
        naming_errors = check_page_naming(_frag_labels(args.pages, ordered), style_blocks)
        if naming_errors:
            print('FAIL 页面命名检查（正式构建门禁：界面上给人看的名字必须是中文）')
            for e in naming_errors:
                print('  - ' + e)
            raise SystemExit(1)
        project_id = args.project_id or 'prototype-' + uuid.uuid4().hex
        profile = None if args.profile == PROJECT_PROFILE_NONE else args.profile
        device_label = describe_device(pages, args.device)
        style_name = str(design.get('name') or '未命名设计系统')
        agents_marker = '<!-- prototype-project: %s -->' % html.escape(project_id, quote=True)
        agents_path = args.output.parent / 'AGENTS.md'
        if args.output.exists():
            parser.error('Output already exists; move the previous build to build/history/ or choose a new destination.')
        # V06：skipAgentsGuide（draft 档）不生成也不校验 AGENTS.md——防误覆检查一并跳过。
        profile_cfg = load_profile(profile) if profile else {}
        if not profile_cfg.get('skipAgentsGuide'):
            # T01 防误覆：目标 AGENTS.md 已存在且不属于本项目（project_id 标记不符）→ 具名拒绝，
            # 不写任何文件（HTML 也不落盘）。同项目重建（标记匹配）允许覆盖。
            if agents_path.exists():
                existing = agents_path.read_text(encoding='utf-8')
                if agents_marker not in existing:
                    raise ValueError('refusing to overwrite AGENTS.md belonging to another project: %s '
                                     '(existing marker mismatch, expected %s)' % (agents_path, agents_marker))
        result, count = compose(pages, args.title, project_id, design, start_doc, tree, profile, style_blocks,
                                args.active_pack, icon_families=args.icon_families, conversion=args.conversion)
        if args.asset_out:
            # V06 转化线交付形态：代码+asset（html + assets/ 目录）。
            # 页面 DOM 与 prototype-* JSON 契约块保持内嵌（file:// 直开不依赖 fetch）；
            # 大体积资源外置为同目录相对引用：图片 dataURL→assets/img/、<style>→assets/css/、
            # 可执行 <script>→assets/js/（内容含 '</script' 字面量或 type=json 的一律保留内嵌）。
            asset_dir = args.asset_out
            for sub in ('js', 'img'):
                (asset_dir / 'assets' / sub).mkdir(parents=True, exist_ok=True)
            result = _emit_code_asset(result, asset_dir)
        if args.docs:
            # 客户版换风格技能的供料：项目侧文档原样复制进产物 docs/（产物走到哪资料跟到哪）；
            # 放 write_text 之前 fail-fast——缺文档即构建 FAIL，防"以为带了其实没带"
            import shutil
            docs_dir = (args.asset_out if args.asset_out else args.output.parent) / 'docs'
            docs_dir.mkdir(parents=True, exist_ok=True)
            for doc in args.docs:
                if not doc.is_file():
                    raise ValueError('--docs file not found: %s' % doc)
                shutil.copyfile(doc, docs_dir / doc.name)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding='utf-8')
        # 换肤受控块注入后必须过 verify_blocks 门禁（产/检同口径，FAIL 即构建 FAIL）；
        # intake/selection-result.json 存在时同时跑 --lock 锁定值校验（skeletonTokens 只扩不改，GPT#1）
        if style_blocks:
            import subprocess
            lock_args = []
            _sel = args.style_blocks.parent / 'selection-result.json'
            if _sel.is_file():
                lock_args = ['--lock', str(_sel)]
            try:
                vb = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'verify_blocks.py'), str(args.output)] + lock_args,
                                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                                    env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=120)
            except subprocess.TimeoutExpired:
                args.output.unlink(missing_ok=True)
                raise ValueError('style-blocks verify_blocks timeout (120s)')
            if vb.returncode != 0:
                args.output.unlink(missing_ok=True)
                print('FAIL style-blocks verify_blocks（正式构建门禁拒绝）:')
                print((vb.stdout or '') + (vb.stderr or ''))
                raise SystemExit(1)
        # T18/T01：产物同目录生成 AGENTS.md（AI 修改指南）+ HTML 头部内嵌摘要注释。
        # 文案与实际装配配置同源：device=片段 .device 类（或 --device），风格名=design.name，
        # 口令=EDIT_PASSWORD 装配常量；不再使用固定商城文案。project_id 标记用于防误覆他项目。
        # V06：profile 声明 skipAgentsGuide=true 时跳过（draft 预览包无编辑器，AI 指南无消费方）。
        if not profile_cfg.get('skipAgentsGuide'):
            try:
                tpl = (ROOT / 'assets/agents-template.md').read_text(encoding='utf-8')
                # 2026-11-23 D 案：AGENTS.md 不写页面数与当前风格名（宿主自动注入给任何会话，换风链禁读产物侧事实——锚定物断源）；
                # 模板概况节已删这两行，此处同步删占位符替换。
                agents = (tpl.replace('{{TITLE}}', args.title)
                             .replace('{{DEVICE}}', device_label)
                             .replace('{{DEFAULT_PWD}}', EDIT_PASSWORD))
                agents = agents_marker + '\n' + agents
                agents_path.write_text(agents, encoding='utf-8')
                head_note = ('<!-- AI 修改指南（摘要）：本文件为单文件可编辑原型。页面=<section class="screen" data-screen=...>；'
                             '跳转=data-on JSON（如 {"click":{"goto":"目标id"}}）；标注=data-note；'
                             '颜色一律用 --accent 等令牌不要硬编码；id=prototype-*/editor-* 的注入块绝不可删；'
                             '完整指南见同目录 AGENTS.md。编辑口令默认 %s。 -->\n' % EDIT_PASSWORD)
                if '<!-- AI 修改指南' not in result:
                    result = head_note + result
                    args.output.write_text(result, encoding='utf-8')
                print('AGENTS.md generated: ' + str(agents_path.resolve()))
            except OSError as e:
                print('WARN agents-md: ' + str(e))
        if style_blocks:
            _capture_pack_shots(args.output)  # 风格卡真截图缩略回填；须在 U3 回执 hash 之前（hash=最终字节）
        if gate_inputs is not None:
            _write_u3_receipt(args, gate_inputs, count)  # T02.1 U3 回执（artifactHash=最终产物字节）
        suffix = ' + start-doc embedded' if start_doc else ''
        print(f'Built {count} screens{suffix}: {args.output.resolve()}')
    except ValueError as e:
        print('ERROR ' + str(e))
        raise SystemExit(2)
    except OSError as e:
        print('ERROR file system: ' + str(e))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
