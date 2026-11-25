"""verify_blocks — 受控块 K2 校验（丁·验证三件之二）。

依据 references/controlled-blocks.md（四方共同依赖的格式契约）逐块断言：
  a) 每块恰 1 个（两围栏形态计数合计）、JSON 可解析、schemaVersion 在（存在且为整数）
  b) 必填字段齐（按各节样例；note 类注释字段、COMPONENT-PACK 组件项 tokenRefs 选填；
     iconSet 允许 null/空串/缺省=不约束图标族，与运行时同语义）
  c) 引用闭合——任务书点名两条：STYLE-PACK 每包的 familyId 必须存在于
     STYLE-REGISTRY.families；COMPONENT-PACK.packFor 必须存在于某 STYLE-PACK 包。另按
     同文件结构引用补三条悬空断言：families[].domBaseId → domBases[]、
     families[].members → packs[].packId、STYLE-CONTRACT.domBaseId → domBases[]
     （悬空指针同为坏数据，错误码独立分组便于裁定）。

围栏两形态（通则：HTML 注释围栏落在交付 HTML 配置区，格式对齐 K2 迁移范式 MARKER:BEGIN/END；
任务书补充 script type=application/json 围栏同权）：
  A) <!-- STYLE-REGISTRY:BEGIN --> JSON <!-- STYLE-REGISTRY:END -->
  B) <script type="application/json" data-block="STYLE-REGISTRY"> JSON </script>
  每类围栏两形态计数合计恰 1；两形态都出现=重复（E-BLOCK-DUP）。

STYLE-PACK 结构（验收裁定：一围栏多包）：块内为 {"schemaVersion":1,"packs":[…]} 包装，
族内变体包是数组元素（数量不设上限；族成员 <2 触发 W-FAMILY-SOLO 提醒）；四类围栏各恰 1
（对齐 K2 六受控块各恰 1 惯例）。旧"裸单包"结构（顶层即 packId/familyId/…）不再是合法形态
（E-BLOCK-FIELD: missing packs）。

输入两形态（1.3 起）：
  A) 交付 HTML（含围栏）——原形态；
  B) U2 数据文件 intake/style-blocks.json——顶层是含四个受控块键的 JSON 对象，
     作者写完即可直接自检，不必先注入 HTML。按顶层键名自动识别形态。

键名正本表/种子变量/STYLE_OWNED_VARS/风格数据读取/已知集合分层，单一出处见
scripts/_token_registry.py（两门禁共用，禁止各自手抄口径）。

必填字段集：
  STYLE-REGISTRY:  domBases[{domBaseId,pages}], families[{familyId,domBaseId,label,members}]
  STYLE-PACK:      packs[{packId,familyId,identity{styleId,styleName,origin,mood},tokens,
                   palettes[{paletteId,label,swatches}],iconSet(可 null/空=不约束),l2Overrides}]
  COMPONENT-PACK:  packFor, components[{compId,name,html}]
  STYLE-CONTRACT:  domBaseId, styleOrigin{styleId,mood}, pages[{pageId,form,regions[{region,shape,count}]}],
                   motion{tier,tokens{duration,easing}}, density

用法：python verify_blocks.py <产物HTML 或 intake/style-blocks.json> [--lock selection-result.json]

Exit codes（对齐 verify-interactions 冻结单 §2 统一语义）：0 = PASS；1 = 校验失败（FAIL，
失败数只进报告不进退出码）；2 = 参数错误 / 输入不可读。
规则码总表：
  E-BLOCK-MISSING / E-BLOCK-DUP / E-BLOCK-JSON / E-BLOCK-SCHEMA / E-BLOCK-FIELD
      受控块层：缺块/重复/JSON 不可解析/schemaVersion/必填字段（iconSet 为 null/空串/缺省不算缺）。
  E-BLOCK-COUNT
      COMPONENT-PACK 组件数低于规格下限 10（六类覆盖 10-15 封顶）。
  E-BLOCK-REF / E-BLOCK-REF-DBASE / E-BLOCK-REF-MEMBER
      引用闭合：familyId→families、packFor→packs（点名）；domBaseId→domBases、
      families[].members→packs、STYLE-CONTRACT.domBaseId（结构补充）。
  E-PACK-KEY
      风格包 tokens 键名不合正本表 keyPattern——报错并给正确写法（先查正本表 aliases；
      查不到则驼峰自动转连字符并按正本命名族补前缀，如 ctlXs→size-ctl-xs、radiusMd→radius-md）。
  E-PACK-KEY-VALUE
      正本键值域：值不在该键 allowed 列表内（如 density ∉ compact/regular/loose），
      或 allowed 键的值不是字符串（如数字 3）——报错并列出可选值。
  E-PACK-KEY-NEAR
      键名合法但命中正本表别名，或与某正本键编辑距离 ≤2——报错并给建议键名。
      豁免：族内延伸（前 n-1 词与某正本键逐词相同、仅末词为全新词且不以正本词开头，
      如 size-ctl-xs 之于 size-ctl-sm）不算近似——这正是驼峰建议要落的位置。
  E-PACK-MINIMUM
      风格包 tokens 缺正本表 minimum 最小集键——报错并列出缺失键名。
  E-PACK-VALUE-CHARS
      tokens 值（正本键与扩展参数，含对象叶）含注入字符 ; { } < > 或 /* ——与运行时过滤口径一致。
  E-PACK-ID
      packId 不匹配 ^[A-Za-z0-9_-]+$（packId 会进数据属性/DOM，禁止注入字符）。
  E-L2-SELECTOR
      l2Overrides 选择器写了 :root/html/body——覆盖样式运行时自动加页面容器前缀，
      这些选择器永远匹配不到；须改写成页面容器类（如 .app）。
  E-L2-SELECTOR-CHARS
      l2Overrides 选择器含 { } < > ; " 或 /* ——与运行时过滤口径一致。
  E-L2-DECL
      l2Overrides.props 存在非法 CSS 声明（如 ":ok:#00A2C7" 缺 "--"，浏览器整句丢弃）；
      或 props 含危险字符 { } < > /*（可跳出规则块注入 CSS；`;` 是合法声明分隔符，保留）。
  E-L2-UNKNOWN-VAR
      l2Overrides.props 的 var() 引用不在已知集合（=页面域集合 ∪ 种子 STYLE_OWNED_VARS
      13 个运行时颜色根变量，如 --style-line；名单从 editor-seed.html 解析，不手抄）。
  E-COMP-RAW-COLOR
      组件 HTML 样式上下文（style 属性、<style> 块、颜色类展示属性 fill/stroke/stop-color/color
      等）含裸色值；正文文本里的 #xxxx 不算（如"订单 #1024"是单号不是颜色）。
  E-COMP-UNKNOWN-VAR
      组件 HTML 引用未知变量——--sp-* 不再一律放行：必须在已知集合内（页面域集合 ∪
      STYLE_OWNED_VARS；--device 协议前缀除外）。
  E-LOCK-MUTATED / E-LOCK-NO-PACK
      --lock：skeletonTokens 选定即锁，只扩不改（改锁=致命；无同名包=警告级）。
  E-LOCK-KEY
      selection-result.skeletonTokens 键名不合正本表规则（与 E-PACK-KEY 同规则）。
  E-LOCK-KEY-MISSING
      锁定的键在对应风格包 tokens 中不存在（原直接跳过 → 现报错，锁定必须落地）。
  E-LOCK-MINIMUM
      skeletonTokens 缺正本表 minimum 最小集键（选型必带）——报错并列出缺失键名。
  W-PACK-PALETTES / W-FAMILY-SOLO
      提醒级（不进退出码）：配色少于 2 套；族成员只有 1 个（族成员数量不设上限）。
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from _token_registry import (check_token_key, load_pack_source, load_registry,
                             overrides_known_vars)

CHECKER_VERSION='verify_blocks/1.4.0-gates'

BLOCK_NAMES=['STYLE-REGISTRY','STYLE-PACK','COMPONENT-PACK','STYLE-CONTRACT']

TOP_FIELDS={  # 顶层必填 {field: kind}
 'STYLE-REGISTRY':{'domBases':'list','families':'list'},
 'STYLE-PACK':{'packs':'list'},
 'COMPONENT-PACK':{'packFor':'str','components':'list'},
 'STYLE-CONTRACT':{'domBaseId':'str','styleOrigin':'dict','pages':'list','motion':'dict','density':'str'},
}
PACK_ITEM_FIELDS={'packId':'str','familyId':'str','identity':'dict','tokens':'dict',
                  'palettes':'list','l2Overrides':'list'}  # iconSet 单独处理：null/空串/缺省=不约束
TYPE_CHECK={'list':lambda v:isinstance(v,list),'dict':lambda v:isinstance(v,dict),
            'str':lambda v:isinstance(v,str) and v.strip()!=''}

PACK_ID_RE=re.compile(r'^[A-Za-z0-9_-]+$')              # packId 会进数据属性/DOM
VALUE_CHARS_FORBIDDEN=re.compile(r'[;{}<>]|/\*')        # tokens 值禁注入字符（运行时同口径）
L2_SELECTOR_FORBIDDEN=re.compile(r'[{}<>;"]|/\*')       # l2 selector 禁注入字符（运行时同口径）
# 组件 HTML 的颜色类展示属性（样式上下文；正文文本不查裸色）
_COLOR_PRESENTATION_ATTRS={'fill','stroke','stop-color','color','background','background-color',
                           'caret-color','outline-color','border-color','text-decoration-color'}


def _iter_string_leaves(v,path=''):
    """遍历任意 JSON 子树的全部字符串叶（tokens 的 dark 等对象值也覆盖）。"""
    if isinstance(v,str):
        yield path or '(value)',v
    elif isinstance(v,dict):
        for kk,vv in v.items():
            yield from _iter_string_leaves(vv,f'{path}.{kk}' if path else str(kk))
    elif isinstance(v,list):
        for i,vv in enumerate(v):
            yield from _iter_string_leaves(vv,f'{path}[{i}]')


class _ComponentStyleScan(HTMLParser):
    """组件 HTML 的样式上下文收集：style 属性、<style> 块、颜色类展示属性（fill/stroke/
    stop-color/color 等）。正文文本不收集——裸色值只在样式上下文里查（"订单 #1024"不是颜色）。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments=[]  # (位置描述, 文本)
        self._in_style=False;self._buf=[]
    def _start(self,tag,attrs):
        if tag=='style':
            self._in_style=True;self._buf=[];return
        d=dict(attrs)
        if d.get('style'):
            self.segments.append((f'<{tag} style>',d['style']))
        for a,v in d.items():
            if a in _COLOR_PRESENTATION_ATTRS and v:
                self.segments.append((f'<{tag} {a}>',v))
    def handle_starttag(self,tag,attrs):self._start(tag,attrs)
    def handle_startendtag(self,tag,attrs):self._start(tag,attrs)
    def handle_endtag(self,tag):
        if tag=='style' and self._in_style:
            self._in_style=False
            self.segments.append(('<style>',''.join(self._buf)))
    def handle_data(self,data):
        if self._in_style:self._buf.append(data)


def find_blocks(html,name):
    """围栏提取（三形态，契约=controlled-blocks.md 通则；与面板侧 chooser/readComponentPack 同口径）：
    ① HTML 注释围栏 NAME:BEGIN/END；② <script data-block="NAME">（type=application/json 可省——
    面板侧不要求，门禁从宽对齐防两判分叉）；③ JS 注释围栏 NAME_START/NAME_END。"""
    esc=re.escape(name)
    comment=re.compile(r'<!--\s*'+esc+r':BEGIN\s*-->([\s\S]*?)<!--\s*'+esc+r':END\s*-->')
    script=re.compile(
        r'<script\b(?=[^>]*\bdata-block=["\']'+esc+r'["\'])[^>]*>([\s\S]*?)</script>',re.I)
    jsfence=re.compile(r'/\*'+esc+r'_START\*/([\s\S]*?)/\*'+esc+r'_END\*/')
    return ([m.group(1) for m in comment.finditer(html)]
            +[m.group(1) for m in script.finditer(html)]
            +[m.group(1) for m in jsfence.finditer(html)])


def check_fields(name,obj):
    """必填字段断言（顶层 + 各块子结构）→ [(rule, message)]。类型错的容器跳过子项防级联。"""
    fails=[]
    for field,kind in TOP_FIELDS[name].items():
        if field not in obj:
            fails.append(('E-BLOCK-FIELD',f'missing top-level field: {field}'))
        elif not TYPE_CHECK[kind](obj[field]):
            fails.append(('E-BLOCK-FIELD',f'field {field} expected {kind}, got {type(obj[field]).__name__}'))

    def list_items(container,fields,path):
        """列表子项的必填字段。"""
        if not isinstance(container,list):return
        for i,item in enumerate(container):
            if not isinstance(item,dict):
                fails.append(('E-BLOCK-FIELD',f'{path}[{i}] expected object'));continue
            for field in fields:
                if field not in item:
                    fails.append(('E-BLOCK-FIELD',f'{path}[{i}] missing field: {field}'))

    def dict_members(node,fields,path):
        """对象子结构的必填字段。"""
        if not isinstance(node,dict):return
        for field in fields:
            if field not in node:
                fails.append(('E-BLOCK-FIELD',f'{path} missing field: {field}'))

    if name=='STYLE-REGISTRY':
        list_items(obj.get('domBases'),['domBaseId','pages'],'domBases')
        list_items(obj.get('families'),['familyId','domBaseId','label','members'],'families')
    elif name=='STYLE-PACK':
        packs=obj.get('packs')
        list_items(packs,['packId','familyId','identity','tokens','palettes','l2Overrides'],'packs')
        if isinstance(packs,list):
            for i,pk in enumerate(packs):
                if not isinstance(pk,dict):continue
                for field,kind in PACK_ITEM_FIELDS.items():
                    if field in pk and not TYPE_CHECK[kind](pk[field]):
                        fails.append(('E-BLOCK-FIELD',f'packs[{i}].{field} expected {kind}, got {type(pk[field]).__name__}'))
                dict_members(pk.get('identity'),['styleId','styleName','origin','mood'],f'packs[{i}].identity')
                list_items(pk.get('palettes'),['paletteId','label','swatches'],f'packs[{i}].palettes')
                icon=pk.get('iconSet')
                if icon is not None and not isinstance(icon,str):
                    fails.append(('E-BLOCK-FIELD',
                        f'packs[{i}].iconSet expected string（或 null/空串=不约束图标族）, got {type(icon).__name__}'))
    elif name=='COMPONENT-PACK':
        list_items(obj.get('components'),['compId','name','html'],'components')
    elif name=='STYLE-CONTRACT':
        dict_members(obj.get('styleOrigin'),['styleId','mood'],'styleOrigin')
        motion=obj.get('motion') if isinstance(obj.get('motion'),dict) else {}
        dict_members(motion,['tier','tokens'],'motion')
        dict_members(motion.get('tokens'),['duration','easing'],'motion.tokens')
        pages=obj.get('pages')
        list_items(pages,['pageId','form','regions'],'pages')
        if isinstance(pages,list):
            for i,p in enumerate(pages):
                if not isinstance(p,dict):continue
                list_items(p.get('regions'),['region','shape','count'],f'pages[{i}].regions')
    return fails


# ---------------------------------------------------------------- 风格包门禁（键名/值域/注入/最小集）
def check_pack_tokens(pk,idx,reg,out):
    """tokens 逐键校验：键名（E-PACK-KEY / E-PACK-KEY-NEAR）、正本键值域（E-PACK-KEY-VALUE）、
    注入字符（E-PACK-VALUE-CHARS）、minimum 最小集（E-PACK-MINIMUM）。逐项独立报，互不掩蔽。"""
    tokens=pk.get('tokens')
    if not isinstance(tokens,dict):return
    label=f'packs[{idx}] "{pk.get("packId")}".tokens'
    for k,v in tokens.items():
        if not isinstance(k,str):continue
        ok,rule,msg=check_token_key(k,reg)
        if not ok:
            out.append((rule,f'{label} 键 "{k}"：{msg}'));continue
        vals=reg['allowed'].get(k)
        if vals:
            if not isinstance(v,str):
                out.append(('E-PACK-KEY-VALUE',
                    f'{label} 键 "{k}" 的值必须是字符串（got {type(v).__name__}: {v!r}）——'
                    f'allowed 键的值请写成字符串，可选值：{"、".join(vals)}；请改用其中之一'))
            elif v.strip() not in vals:
                out.append(('E-PACK-KEY-VALUE',
                    f'{label} 键 "{k}" 的值 "{v}" 不在正本表允许值内——可选值：{"、".join(vals)}；请改用其中之一'))
    for k,v in _iter_string_leaves(tokens):
        m=VALUE_CHARS_FORBIDDEN.search(v)
        if m:
            out.append(('E-PACK-VALUE-CHARS',
                f'{label} 键 "{k}" 的值含禁用字符（命中 {m.group(0)!r}）——tokens 值里不许出现 ; {{ }} < > 或 /*'
                f'（与运行时过滤口径一致）；请改用合法 CSS 值'))
        if re.search(r'TODO', v, re.I):
            out.append(('E-PACK-TODO',
                f'{label} 键 "{k}" 的值是未填占位（"{v}"）——TODO 占位进产物会让壳层 UI（弹窗等非包作用域元素）'
                f'读不到合法颜色而透明（2026-11-23 端到端实证）；请回 editor_gen_tokens 填真实语义值后再构建'))
    missing=sorted(reg['minimum']-set(tokens))
    if missing:
        out.append(('E-PACK-MINIMUM',
            f'{label} 缺少正本表最小集（minimum）键 {len(missing)} 个：{"、".join(missing)}'
            f'——最小集是比稿卡必给、选型必带、选定即锁的核心参数，请在 tokens 里补齐'))


def check_pack_id(pk,idx,out):
    """packId 白名单：^[A-Za-z0-9_-]+$（packId 会进数据属性/DOM，禁止注入字符）。"""
    pid=pk.get('packId')
    if isinstance(pid,str) and not PACK_ID_RE.match(pid):
        out.append(('E-PACK-ID',
            f'packs[{idx}].packId "{pid}" 含非法字符——packId 只允许字母/数字/下划线/连字符'
            f'（^[A-Za-z0-9_-]+$）；请改名（中文与符号请放进 identity.styleName）'))


# ---------------------------------------------------------------- l2Overrides（覆盖样式）
BAD_L2_SELECTORS={':root','html','body'}
L2_DECL_RE=re.compile(r'^(?:--[a-zA-Z0-9-]+|[a-zA-Z][a-zA-Z0-9-]*)\s*:\s*[^;{}\s][^;{}]*$')
L2_PROPS_FORBIDDEN=re.compile(r'[{}<>]|/\*')  # props 危险字符：可跳出规则块注入 CSS（; 是合法分隔符）
VAR_RE=re.compile(r'var\(\s*(--[a-zA-Z0-9-]+)')


def check_l2_overrides(pk,idx,out,known=None):
    """覆盖样式四条：选择器不得是 :root/html/body（自动加容器前缀后永远匹配不到）；
    选择器不得含注入字符；props 必须逐条是格式正确的 CSS 声明（":ok:#00A2C7" 这类缺属性名的
    整句被浏览器丢弃）；props 里 var() 引用必须在已知集合内（known=None 时跳过该条）。"""
    label=f'packs[{idx}] "{pk.get("packId")}"'
    l2=pk.get('l2Overrides')
    if not isinstance(l2,list):return
    for j,item in enumerate(l2):
        if not isinstance(item,dict):
            out.append(('E-BLOCK-FIELD',f'{label}.l2Overrides[{j}] expected object'));continue
        sel=item.get('selector')
        if not isinstance(sel,str) or not sel.strip():
            out.append(('E-BLOCK-FIELD',f'{label}.l2Overrides[{j}] missing/empty field: selector'));continue
        m=L2_SELECTOR_FORBIDDEN.search(sel)
        if m:
            out.append(('E-L2-SELECTOR-CHARS',
                f'{label}.l2Overrides[{j}] 选择器含禁用字符（命中 {m.group(0)!r}）——selector 只能是页面容器类名'
                f'（如 ".app"），不许 {{ }} < > ; " 或 /*（与运行时过滤口径一致）'))
        bad=[seg for seg in (p.strip().lower() for p in sel.split(',')) if seg in BAD_L2_SELECTORS]
        if bad:
            out.append(('E-L2-SELECTOR',f'{label}.l2Overrides[{j}] 选择器 "{sel}" 含 {"、".join(bad)} ——覆盖样式运行时会自动加上页面容器前缀，这些选择器永远匹配不到；请改写成页面容器类（如 ".app"）'))
        props=item.get('props')
        if not isinstance(props,str) or not props.strip():
            out.append(('E-BLOCK-FIELD',f'{label}.l2Overrides[{j}] missing/empty field: props'));continue
        m=L2_PROPS_FORBIDDEN.search(props)
        if m:
            out.append(('E-L2-DECL',
                f'{label}.l2Overrides[{j}].props 含危险字符（命中 {m.group(0)!r}）——{{ }} < > 或 /* 可跳出'
                f'规则块注入 CSS（`;` 是合法声明分隔符，保留）；请删除后再逐条写声明'))
            continue  # 危险字符是根因，先修它——跳过逐条声明检查，避免级联噪音
        if known is not None:
            for m in VAR_RE.finditer(props):
                v=m.group(1)
                if v not in known and not v.startswith('--device'):
                    out.append(('E-L2-UNKNOWN-VAR',
                        f'{label}.l2Overrides[{j}].props 引用未定义变量 {v} ——不在已知集合'
                        f'（正本表 emits 变量 + 种子默认值 + 风格包扩展键 --sp-<键名> + 种子 STYLE_OWNED_VARS'
                        f' 运行时颜色根变量）；请改用已定义变量'))
        for part in props.split(';'):
            s=part.strip()
            if not s:continue  # 结尾分号/空段不算声明
            if not L2_DECL_RE.match(s):
                hint='——疑似漏写属性名前缀 "--"（自定义属性必须以 -- 开头，如 "--ok:#00A2C7"）' if s.startswith(':') \
                     else '——应形如 "--radius:8px" 或 "border-radius:var(--radius)"（属性名: 值）'
                out.append(('E-L2-DECL',f'{label}.l2Overrides[{j}].props 含非法声明 "{s}" {hint}'))


def verify(kind,payload,reg):
    """四块校验 → (results, warns)。
    results: {name: [(rule, message)]}（空列表=该块通过，只进退出码的是这里）；
    warns:   [(block, rule, message)]（提示级，不进退出码）。
    kind='data-file'：payload=U2 数据文件对象（含四受控块键）；kind='fenced-html'：payload=HTML 全文。"""
    results={name:[] for name in BLOCK_NAMES}
    parsed={}
    warns=[]
    for name in BLOCK_NAMES:
        obj=None
        if kind=='data-file':
            raw=payload.get(name) if isinstance(payload,dict) else None
            if raw is None:
                results[name]=[('E-BLOCK-MISSING',f'U2 数据文件缺少受控块键 "{name}"')];continue
            if not isinstance(raw,dict):
                results[name]=[('E-BLOCK-JSON',f'块 "{name}" 内容必须是 JSON 对象，got {type(raw).__name__}')];continue
            obj=raw
        else:
            fences=find_blocks(payload,name)
            if not fences:
                results[name]=[('E-BLOCK-MISSING','fence not found (expected exactly 1, got 0)')];continue
            if len(fences)>1:
                results[name]=[('E-BLOCK-DUP',f'fence appears {len(fences)} times (expected exactly 1)')];continue
            try:
                obj=json.loads(fences[0].strip())
            except json.JSONDecodeError as e:
                results[name]=[('E-BLOCK-JSON',f'cannot parse JSON: {e.msg} at line {e.lineno} col {e.colno}')];continue
            if not isinstance(obj,dict):
                results[name]=[('E-BLOCK-JSON','JSON root must be an object')];continue
        fails=[]
        sv=obj.get('schemaVersion')
        if sv is None:fails.append(('E-BLOCK-SCHEMA','missing schemaVersion'))
        elif isinstance(sv,bool) or not isinstance(sv,int):
            fails.append(('E-BLOCK-SCHEMA',f'schemaVersion must be integer, got {type(sv).__name__}'))
        fails+=check_fields(name,obj)
        results[name]=fails
        parsed[name]=obj  # JSON 解析成功即供引用检查（结构失败与引用失败独立成账，不互相掩蔽）

    # b1) 风格包：packId 白名单 / tokens 键名值域注入最小集 / l2Overrides（含 var 存在性）/ 配色数量
    regobj=parsed.get('STYLE-REGISTRY')
    block=parsed.get('STYLE-PACK')
    packs=[]
    if isinstance(block,dict) and isinstance(block.get('packs'),list):
        packs=[pk for pk in block['packs'] if isinstance(pk,dict)]
        # var() 已知集合（L2 分层：页面域集合 ∪ STYLE_OWNED_VARS，单一出处 _token_registry）。
        # 注册表块缺失时置 None → var 检查跳过（该文件已有兜底 FAIL，不级联出海量噪音）
        known_full=overrides_known_vars(reg,packs) if isinstance(regobj,dict) else None
        for i,pk in enumerate(packs):
            check_pack_id(pk,i,results['STYLE-PACK'])
            check_pack_tokens(pk,i,reg,results['STYLE-PACK'])
            check_l2_overrides(pk,i,results['STYLE-PACK'],known_full)
            pals=pk.get('palettes')
            if isinstance(pals,list) and len(pals)<2:
                warns.append(('STYLE-PACK','W-PACK-PALETTES',
                    f'packs[{i}] "{pk.get("packId")}" 只有 {len(pals)} 套配色（提示，不拦截）——品牌色盘那一版必须有，另按风格气质再配几套合适的配色版'))
    # b1b) 族成员数提醒（不设上限，只提醒下限）
    if isinstance(regobj,dict) and isinstance(regobj.get('families'),list):
        for f in regobj['families']:
            if isinstance(f,dict) and isinstance(f.get('members'),list) and len(f['members'])<2:
                warns.append(('STYLE-REGISTRY','W-FAMILY-SOLO',
                    f'族 "{f.get("familyId")}" 只有 {len(f["members"])} 个成员（提示，不拦截）——每族顺手送 1-2 个同族变体'))

    # b2) COMPONENT-PACK 组件 HTML 检查：计数口径 + 裸色值（仅样式上下文）+ 未知令牌扫描。
    comp=parsed.get('COMPONENT-PACK')
    if isinstance(comp,dict) and isinstance(comp.get('components'),list):
        comps=comp['components']
        if len(comps)<10:
            results['COMPONENT-PACK'].append(('E-BLOCK-COUNT',
                f'components={len(comps)}，低于规格下限 10（六类覆盖 10-15 封顶；见 component-pack-spec §3）'))
        _HEX=re.compile(r'#[0-9a-fA-F]{3,8}\b')
        # var() 已知集合（L2 分层，见 b1 处 known_full）。注册表缺失时跳过 var 检查（防级联）；
        # 裸色值检查不依赖注册表，照查——但只在样式上下文里查。
        known=known_full
        for ci,c in enumerate(comps):
            html_frag=c.get('html') or ''
            if not isinstance(html_frag,str):continue
            scanner=_ComponentStyleScan()
            try:
                scanner.feed(html_frag);scanner.close()
            except Exception:
                scanner.segments=[]
            for where,text in scanner.segments:
                for m in _HEX.finditer(text):
                    results['COMPONENT-PACK'].append(('E-COMP-RAW-COLOR',
                        f'components[{ci}] "{c.get("name")}" 组件 HTML 样式上下文（{where}）含裸色值 {m.group(0)}——接 var(令牌,原值)'
                        f'（正文文本里的 #xxxx 不查：可能是单号等文案）'))
            if known is None:continue
            for m in VAR_RE.finditer(html_frag):
                v=m.group(1)
                if v not in known and not v.startswith('--device'):
                    results['COMPONENT-PACK'].append(('E-COMP-UNKNOWN-VAR',
                        f'components[{ci}] "{c.get("name")}" 引用未定义变量 {v} ——不在已知集合'
                        f'（正本表 emits 变量 + 种子默认值 + 风格包扩展键 --sp-<键名> + STYLE_OWNED_VARS）；'
                        f'请改用已定义变量，或在风格包 tokens 里补该扩展键'))

    # c) 引用闭合。守卫原则：被引用方解析成功且引用容器字段可用才查（否则该块已有兜底 FAIL，不级联）。
    reg_ok=isinstance(regobj,dict) and isinstance(regobj.get('families'),list) and isinstance(regobj.get('domBases'),list)
    pack_ok=isinstance(block,dict) and isinstance(block.get('packs'),list)
    pack_items=packs
    fam_ids=db_ids=set()
    if reg_ok:
        fam_ids={f.get('familyId') for f in regobj.get('families',[])}
        db_ids={d.get('domBaseId') for d in regobj.get('domBases',[])}
    pack_ids={pk.get('packId') for pk in pack_items}
    # 1) 点名：每个 pack 的 familyId ∈ STYLE-REGISTRY.families
    if reg_ok and pack_ok:
        for i,pk in enumerate(pack_items):
            if pk.get('familyId') not in fam_ids:
                results['STYLE-PACK'].append(('E-BLOCK-REF',
                    f'packs[{i}].familyId "{pk.get("familyId")}" not found in STYLE-REGISTRY.families'))
    # 2) 点名：COMPONENT-PACK.packFor ∈ packs[].packId
    if pack_ok and isinstance(comp,dict) and comp.get('packFor') not in pack_ids:
        results['COMPONENT-PACK'].append(('E-BLOCK-REF',
            f'packFor "{comp.get("packFor")}" not found in any STYLE-PACK packs'))
    # 3) 结构：families[].domBaseId ∈ domBases
    if reg_ok:
        for f in regobj.get('families',[]):
            if f.get('domBaseId') not in db_ids:
                results['STYLE-REGISTRY'].append(('E-BLOCK-REF-DBASE',
                    f'families[{f.get("familyId")}].domBaseId "{f.get("domBaseId")}" not in domBases'))
    # 4) 结构：families[].members ∈ packs[].packId
    if reg_ok and pack_ok:
        for f in regobj.get('families',[]):
            for m in f.get('members') or []:
                if m not in pack_ids:
                    results['STYLE-REGISTRY'].append(('E-BLOCK-REF-MEMBER',
                        f'families[{f.get("familyId")}].members references unknown pack "{m}"'))
    # 5) 结构：STYLE-CONTRACT.domBaseId ∈ domBases
    contract=parsed.get('STYLE-CONTRACT')
    if reg_ok and isinstance(contract,dict) and contract.get('domBaseId') not in db_ids:
        results['STYLE-CONTRACT'].append(('E-BLOCK-REF-DBASE',
            f'domBaseId "{contract.get("domBaseId")}" not found in STYLE-REGISTRY.domBases'))
    return results,warns


# ---------------------------------------------------------------- --lock：skeletonTokens 选定即锁（GPT#1）
def _norm_tok(v):
    """令牌值规范化比较：数值 int/float 等值合并，字符串 strip，其余 JSON 序列化。锁=逐字，不做单位换算。"""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        f = float(v)
        return str(int(f)) if f == int(f) else repr(f)
    if isinstance(v, str):
        return v.strip()
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def verify_lock(packs, selection_result, reg):
    """skeletonTokens 选定即锁（GPT#1 + 补洞）：
      - 最小集：每个 selected 的 skeletonTokens 必须含正本表全部 minimum 键（E-LOCK-MINIMUM，致命）；
      - 键名按正本表同规则校验（E-LOCK-KEY，致命）；
      - 键名合法但在对应包 tokens 里找不到 → E-LOCK-KEY-MISSING（致命；原直接跳过）。
        键名本身不合法的键不再重复报 missing——键名错误已给出改法；
      - 已锁键存在且值不同 = E-LOCK-MUTATED（改锁，致命）；
      - selected 找不到同名包 = E-LOCK-NO-PACK 警告级（多选场景允许部分风格不产包）。
    返回 [(rule, message, fatal)]。"""
    fails = []
    if not isinstance(selection_result, dict) or selection_result.get('status') != 'selected':
        return fails
    for grp in selection_result.get('audienceGroups') or []:
        for sel in (grp.get('selected') or []):
            name = sel.get('styleName')
            sk = sel.get('skeletonTokens') or {}
            if not isinstance(sk, dict):
                continue
            # 最小集：选型必带（先独立报，缺键不参与后续落地/改锁比对）
            missing = sorted(reg['minimum'] - set(sk))
            if missing:
                fails.append(('E-LOCK-MINIMUM',
                              f'selected "{name}" skeletonTokens 缺少正本表最小集（minimum）键 {len(missing)} 个：'
                              f'{"、".join(missing)}——最小集选型必带（选定即锁），请补齐后再回传', True))
            matched = [pk for pk in packs if isinstance(pk, dict)
                       and isinstance(pk.get('identity'), dict)
                       and pk['identity'].get('styleName') == name]
            if not matched:
                fails.append(('E-LOCK-NO-PACK',
                              f'selected "{name}" 在 STYLE-PACK 中无同名包（该风格未沉淀为包；多选场景允许）', False))
                continue
            # 键名校验（与风格包 tokens 同规则）；不合法的键不再参与落地/改锁比对
            checked = {}
            for k, v in sk.items():
                if not isinstance(k, str):
                    continue
                ok, rule, msg = check_token_key(k, reg)
                if not ok:
                    fails.append(('E-LOCK-KEY',
                                  f'selected "{name}" skeletonTokens 键 "{k}"：{msg}', True))
                else:
                    checked[k] = v
            toks = {k: _norm_tok(v) for k, v in checked.items()}
            for pk in matched:
                pk_tokens = pk.get('tokens') or {}
                for k, want in toks.items():
                    if k not in pk_tokens:
                        fails.append(('E-LOCK-KEY-MISSING',
                                      f'锁定的键 "{k}" 在包 "{pk.get("packId")}" 的 tokens 中不存在'
                                      f'——锁定键必须在风格包里落地（选定即锁、只扩不改）；'
                                      f'若为扩展参数请先在包 tokens 里补齐该键', True))
                        continue  # 键不在包里无从比值
                    got = _norm_tok(pk_tokens[k])
                    if got != want:
                        fails.append(('E-LOCK-MUTATED',
                                      f'包 {pk.get("packId")} 令牌 "{k}" 已改锁: 选定={want!r} 生成={got!r}', True))
    return fails


def main(argv=None):
    ap=argparse.ArgumentParser(prog='verify_blocks.py',description='controlled-block K2 gate')
    ap.add_argument('html',help='交付 HTML（含受控块围栏）或 U2 数据文件 intake/style-blocks.json（含四受控块键的 JSON 对象）')
    ap.add_argument('--lock',default=None,help='selection-result.json：skeletonTokens 选定即锁校验（同键只扩不改）')
    args=ap.parse_args(argv)
    path=Path(args.html)
    if not path.is_file():
        print(f'FAIL input not found: {path}',file=sys.stderr);return 2
    try:
        text=path.read_text(encoding='utf-8-sig',errors='replace')
    except Exception as e:
        print(f'FAIL cannot read input: {e}',file=sys.stderr);return 2
    try:
        reg=load_registry()
    except Exception as e:
        print(f'FAIL cannot load token registry (assets/token-keys.json): {e}',file=sys.stderr);return 2
    kind,payload=load_pack_source(text)
    print(f'{CHECKER_VERSION} — input: {path} ({kind})')
    results,warns=verify(kind,payload,reg)
    for name in BLOCK_NAMES:
        fails=results.get(name,[])
        if not fails:
            detail='数据文件块齐, JSON ok, fields ok, references closed' if kind=='data-file' \
                   else 'present exactly once, JSON ok, fields ok, references closed'
            print(f'[pass] {name} — {detail}')
        else:
            for rule,msg in fails:
                print(f'[FAIL] {name} — {rule}: {msg}')
    for block,rule,msg in warns:
        print(f'[warn] {block} — {rule}: {msg}')
    # --lock：选定即锁校验（GPT#1）——违规计入 fatal 计数，警告级只报告
    lock_warn=0
    if args.lock:
        lock_path=Path(args.lock)
        if not lock_path.is_file():
            print(f'[FAIL] E-LOCK --lock file not found: {lock_path}',file=sys.stderr)
            return 2
        try:
            sel=json.loads(lock_path.read_text(encoding='utf-8-sig',errors='replace'))
        except Exception as e:
            print(f'[FAIL] E-LOCK cannot read selection-result: {e}',file=sys.stderr)
            return 2
        from _token_registry import extract_style_packs
        packs=extract_style_packs(payload) if kind=='data-file' else extract_style_packs(text)
        for rule,msg,fatal in verify_lock(packs, sel, reg):
            tag='FAIL' if fatal else 'warn'
            print(f'[{tag}] E-LOCK — {rule}: {msg}')
            if fatal:
                results.setdefault('STYLE-PACK',[]).append((rule,msg))
            else:
                lock_warn+=1
    n_bad=sum(1 for n in BLOCK_NAMES if results.get(n))
    total_fail=sum(len(v) for v in results.values())
    print(f'\nsummary: {len(BLOCK_NAMES)} block(s): {len(BLOCK_NAMES)-n_bad} passed / {n_bad} failed'
          + (f' — E-LOCK warnings: {lock_warn}' if lock_warn else '')
          + (f' — warnings: {len(warns)}' if warns else '')
          + f' — {"FAIL" if total_fail else "PASS"}')
    print(f'exit: {1 if total_fail else 0}')
    return 1 if total_fail else 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8',errors='replace')
            sys.stderr.reconfigure(encoding='utf-8',errors='replace')
        except Exception:pass
    sys.exit(main())
