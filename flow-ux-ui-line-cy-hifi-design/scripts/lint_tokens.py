"""lint_tokens — 硬值 lint 门禁（丁·验证三件之一）。

依据（输入权威）：
- editor-runtime「风格令牌应用与换肤生成规范」：颜色/字号/圆角/阴影之外，间距（margin/padding）、
  控件尺寸（高度/最小宽）、网格列数、gap 只能引用令牌，禁自创硬值——白名单外 px 值=FAIL；
- uxui-style-picker/references/token-minimum.md 下游关系：产物 CSS 中的间距/尺寸/列数/颜色/
  圆角/阴影值必须可归因到令牌（或白名单物理值如 1px 边框），白名单口径=token-minimum 语义组。

用法：
  python lint_tokens.py <pages目录 或 单个HTML> [--design-system <json>] [--style-blocks <json>]
  --style-blocks：项目 U2 数据文件 intake/style-blocks.json（也兼容带 STYLE-PACK 围栏的
  HTML）——其中的风格包扩展键用于扩充 var() 已知集合；不给时已知集合只含正本表和种子默认值。

扫描范围：片段/产物中的 style 属性与 <style> 块（<script> 内容不扫；CSS/HTML 注释不扫）。
检查两类硬值：
  - 颜色（#hex / rgb()/rgba()/hsl()/hsla()）：必须可归因令牌
  - px 值：间距（margin*/padding*/gap*）、尺寸（height/width 及 min/max 变体）、圆角
    （border-radius 族）、字号（font-size）、阴影（box-shadow/text-shadow）用途，以及
    grid-template-columns 的 repeat(N) 列数
白名单三档：
  a) 归因令牌：值出现在 --design-system 令牌 JSON 值域（tokens 子树全叶 +
     typography.baseSize + components 数字叶，按 assets/design-system.json 实例结构；
     无 tokens 键时兜底收集全树"CSS 值形"字符串）
  b) 物理白名单：0/0px/0%、1px（仅边框/outline 宽度用途）、任意百分比、@media 断点
     （min/max-width 条件行不产声明）、transparent/currentColor 与布局关键字
  c) var(--*) 引用：var 段必须指向真实存在的变量（见下 E-TOKEN-UNKNOWN-VAR），
     含 var 的声明在变量核验后，非变量部分的裸值继续走用途检查（calc 内含 var 同样过闸）
var() 已知集合与分层（键名正本表/种子/STYLE_OWNED_VARS 的读取单一出处见 scripts/_token_registry.py）：
  页面域集合 = 正本表 assets/token-keys.json emits 里声明的变量（--sp-* 阶梯 + 页面域
  --accent/--bg/--surface/--text/--muted/--line/--ok/--danger/--warn 及 --radius/--shadow）
  + 种子默认值（assets/editor-seed.html 静态自定义属性）
  +（给了 --style-blocks 时）项目风格包每个扩展键对应的 --sp-<键名>。
  分层口径：--style-*（chooser 运行时写 documentElement 的 13 个颜色根变量）不在页面域集合内——
  它们只供覆盖样式（L2，verify_blocks 侧）引用；页面 CSS 应使用页面域变量，引用 --style-* 时
  报错提示会写明应改用的页面变量（如 --style-line → --line，见 _token_registry.PAGE_VAR_SUGGEST）。
  --device 前缀是协议变量（verify_namespace PROTOCOL_VARS 同口径），维持放行。
--design-system 缺失或未提供时只按物理白名单判，报告显式声明。

Exit codes（对齐 verify-interactions 冻结单 §2 统一语义）：0 = PASS；1 = 存在违规（FAIL，
违规数只进报告不进退出码）；2 = 用法错误 / 输入不可读 / 无可扫描文件。
规则码：E-TOKEN-COLOR / E-TOKEN-SPACE / E-TOKEN-SIZE / E-TOKEN-RADIUS / E-TOKEN-FONTSIZE /
E-TOKEN-GRID / E-TOKEN-SHADOW / E-TOKEN-BORDER（边框宽度，物理白名单仅 1px）/
E-TOKEN-UNKNOWN-VAR（引用未定义变量——页面域集合见上，--sp-* 不再一律放行，
--style-* 会提示应改用的页面变量）。
未点名属性（定位 top/left、letter-spacing、z-index、字体栈等）不检——克制口径，避免误伤。
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from _token_registry import load_registry, page_known_vars, PAGE_VAR_SUGGEST

CHECKER_VERSION='lint_tokens/1.2.0-layered'

# --- 受检属性分类（token-minimum 语义组映射）---
SPACE_PROPS={'margin','margin-top','margin-right','margin-bottom','margin-left',
 'padding','padding-top','padding-right','padding-bottom','padding-left',
 'gap','row-gap','column-gap','grid-gap'}
SIZE_PROPS={'height','min-height','max-height','width','min-width','max-width'}
RADIUS_PROPS={'border-radius','border-top-left-radius','border-top-right-radius',
 'border-bottom-left-radius','border-bottom-right-radius'}
FONTSIZE_PROPS={'font-size'}
SHADOW_PROPS={'box-shadow','text-shadow'}
COLOR_PROPS={'color','background','background-color','border','border-top','border-right',
 'border-bottom','border-left','border-color','border-top-color','border-right-color',
 'border-bottom-color','border-left-color','outline','outline-color','fill','stroke','caret-color'}
BORDER_WIDTH_PROPS={'border','border-top','border-right','border-bottom','border-left',
 'border-width','border-top-width','border-right-width','border-bottom-width','border-left-width',
 'outline','outline-width'}
GRID_PROPS={'grid-template-columns'}

KEYWORD_OK={'auto','none','inherit','initial','unset','revert','transparent','currentcolor',
 'min-content','max-content','fit-content','thin','medium','thick'}

DECL_RE=re.compile(r'^([A-Za-z-]+)\s*:\s*(.*)$',re.S)
PX_RE=re.compile(r'(-?\d+(?:\.\d+)?)px',re.I)
VAR_RE=re.compile(r'var\(\s*(--[a-zA-Z0-9-]+)')
VAR_CALL=re.compile(r'var\([^)]*\)')
COLOR_VAL_RE=re.compile(r'#[0-9a-fA-F]{3,8}|\brgba?\(\s*[^)]*\)|\bhsla?\(\s*[^)]*\)')


def norm_color(v):
    """颜色值归一化为 (r,g,b,a) 元组；不可识别返回 None。支持 #hex(3/4/6/8) 与 rgb/rgba/hsl/hsla。"""
    s=v.strip().lower()
    if s in ('transparent','currentcolor'):return (0,0,0,0.0)  # 关键字白名单由调用方处理
    m=re.match(r'^#([0-9a-f]{3,8})$',s)
    if m:
        h=m.group(1)
        if len(h) in (3,4):
            c=[int(x*2,16) for x in h[:3]];a=int(h[3]*2,16)/255 if len(h)==4 else 1.0
            return (c[0],c[1],c[2],round(a,3))
        if len(h) in (6,8):
            c=[int(h[i:i+2],16) for i in range(0,6,2)]
            a=int(h[6:8],16)/255 if len(h)==8 else 1.0
            return (c[0],c[1],c[2],round(a,3))
        return None
    m=re.match(r'^rgba?\(([^)]*)\)$',s)
    if m:
        parts=[p for p in re.split(r'[,\s/]+',m.group(1).strip()) if p]
        if 3<=len(parts)<=4:
            try:
                nums=[]
                for p in parts:
                    nums.append(round(float(p[:-1])*255/100) if p.endswith('%') else float(p))
                a=round(nums[3],3) if len(nums)>3 else 1.0
                return (int(round(nums[0])),int(round(nums[1])),int(round(nums[2])),a)
            except ValueError:return None
        return None
    m=re.match(r'^hsla?\(([^)]*)\)$',s)
    if m:
        parts=[p for p in re.split(r'[,\s/]+',m.group(1).strip()) if p]
        if 3<=len(parts)<=4:
            try:
                hn=float(parts[0].rstrip('deg'));sn=float(parts[1].rstrip('%'))/100;ln=float(parts[2].rstrip('%'))/100
                a=round(float(parts[3]),3) if len(parts)>3 and not parts[3].endswith('%') else 1.0
                def f(n):
                    k=(n+hn/30)%12
                    return ln-sn*min(ln,1-ln)*max(-1,min(k-3,9-k,1))
                return (round(f(0)*255),round(f(8)*255),round(f(4)*255),a)
            except ValueError:return None
        return None
    return None


def extract_colors(value):
    return COLOR_VAL_RE.findall(value)


def suggest_color_group(prop):
    if prop.startswith(('border','outline')):return '色板·border'
    if prop.startswith('background'):return '色板·bg/surface/surfaceAlt'
    if prop in ('fill','stroke'):return '色板·primary'
    return '色板·textPrimary/textSecondary'


def parse_css_declarations(css,base_line):
    """产出 [(line, selector, prop, value)]。@ 规则条件行（@media 断点）天然不产声明=物理白名单。"""
    css=re.sub(r'/\*.*?\*/',lambda m:re.sub(r'[^\n]',' ',m.group(0)),css,flags=re.S)
    out=[];stack=[];buf='';decl_start=0
    def line_at(idx):return base_line+css.count('\n',0,idx)
    def emit():
        nonlocal buf,decl_start
        s=buf.strip()
        if s and not s.startswith('@'):
            m=DECL_RE.match(s)
            if m:
                sel=' '.join(x for x in stack if not x.startswith('@'))
                out.append((line_at(decl_start),sel,m.group(1).lower(),m.group(2).strip()))
        buf=''
    for i,ch in enumerate(css):
        if ch=='{':
            stack.append(buf.strip());buf=''
        elif ch=='}':
            emit()
            if stack:stack.pop()
        elif ch==';':
            emit()
        else:
            if not buf.strip():
                if ch.isspace():continue  # 前导空白不进 buf（保证 decl_start 钉在声明首字符）
                decl_start=i
            buf+=ch
    emit()  # 块尾/文件尾无分号的最后一条
    return out


class StyleCollector(HTMLParser):
    """收集 <style> 块与 style 属性（script 内容、注释天然不触达）。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.style_attrs=[]   # (line, elem_desc, css_text)
        self.style_blocks=[]  # (start_line, css_text)
        self._in_style=False;self._style_lines=[];self._data_line=None
    def handle_starttag(self,tag,attrs):
        if tag=='style':
            self._in_style=True;self._style_lines=[];self._data_line=None;return
        d=dict(attrs)
        if 'style' in d:
            line,_=self.getpos()
            eid=d.get('data-eid') or d.get('id') or ''
            cls='.'+d['class'].strip().split()[0] if d.get('class') else ''
            desc=f'<{tag}{cls}'+(f' data-eid={eid}>' if eid else '>')
            self.style_attrs.append((line,desc,d['style']))
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag=='style' and self._in_style:
            self._in_style=False
            self.style_blocks.append((self._data_line or self.getpos()[0],''.join(self._style_lines)))
    def handle_data(self,data):
        if self._in_style:
            if self._data_line is None:self._data_line=self.getpos()[0]
            self._style_lines.append(data)


def collect_declarations(src):
    """HTML 源 → 全部待检声明 [(line, selector_or_element, prop, value)]。"""
    c=StyleCollector();c.feed(src);c.close()
    decls=[]
    for start_line,css in c.style_blocks:
        decls+=parse_css_declarations(css,start_line)
    for line,elem,style_text in c.style_attrs:
        for part in style_text.split(';'):
            m=DECL_RE.match(part.strip())
            if m:decls.append((line,elem,m.group(1).lower(),m.group(2).strip()))
    return decls


def load_token_values(path):
    """design-system JSON → (colors, lengths, shadows, by_use)。

    值域路径（按 assets/design-system.json 实例结构）：tokens 子树全叶 + typography.baseSize +
    components 数字叶；无 tokens 键时兜底收集全树"CSS 值形"字符串。styleTune 等元数据子树
    （值域定义/说明文字）不进白名单——其数字（min/max/step）不是样式值。

    GPT#3 加固：by_use=按用途分桶的长度集合（键名语义归类）——数字白名单不再跨用途搭车
    （buttonRadius=9 只进圆角桶，不再让 font-size:9px 搭车放行）。桶键：
      radius（键含 radius）/ ctlsize（键含 height|width|size）/ space（键含 padding|margin|gap|space）/
      fontsize（键含 font|size 文本类）。tokens 子树的 radius*/size*/space* 同理归类；
    语义不可判的数字仍进全局 lengths（供非用途组属性与未来扩展），但用途组检查只认自己的桶。
    """
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict):raise ValueError('design-system JSON root must be an object')
    colors=set();lengths=set();shadows=set()
    by_use={'radius':set(),'ctlsize':set(),'space':set(),'fontsize':set()}
    def classify_len(name,f):
        n=(name or '').lower()
        if 'radius' in n:by_use['radius'].add(f)
        elif 'font' in n:by_use['fontsize'].add(f)
        elif any(w in n for w in ('height','width')) or ('size' in n and 'font' not in n):by_use['ctlsize'].add(f)
        elif any(w in n for w in ('padding','margin','gap','space')):by_use['space'].add(f)
    def leaf(v,name=None):
        if isinstance(v,bool):return
        if isinstance(v,(int,float)):lengths.add(float(v));classify_len(name,float(v));return
        if not isinstance(v,str):return
        s=v.strip()
        nc=norm_color(s)
        if nc is not None:colors.add(nc);return
        for m in PX_RE.finditer(s):lengths.add(float(m.group(1)));classify_len(name,float(m.group(1)))
        if re.search(r'\dpx\s+\d|rgba?\(|#',s) and ' ' in s:shadows.add(re.sub(r'\s+',' ',s).lower())
    if isinstance(data.get('tokens'),dict):
        def walk(node,pre=''):
            if isinstance(node,dict):
                for k,x in node.items():walk(x,pre+k+' ')
            elif isinstance(node,list):
                for x in node:walk(x,pre)
            else:leaf(v=node,name=pre)
        walk(data['tokens'],'tokens ')
        tp=data.get('typography')
        if isinstance(tp,dict) and isinstance(tp.get('baseSize'),(int,float)) and not isinstance(tp.get('baseSize'),bool):
            lengths.add(float(tp['baseSize']));by_use['fontsize'].add(float(tp['baseSize']))
        comp=data.get('components')
        if isinstance(comp,dict):
            for k,v in comp.items():
                if isinstance(v,(int,float)) and not isinstance(v,bool):lengths.add(float(v));classify_len(k,float(v))
    else:
        def walk_all(node):
            if isinstance(node,dict):
                for x in node.values():walk_all(x)
            elif isinstance(node,list):
                for x in node:walk_all(x)
            elif isinstance(node,str) and re.search(r'#[0-9a-fA-F]{3}|rgba?\(|\d+px',node):leaf(node)
        walk_all(data)
    return colors,lengths,shadows,by_use


def check_declaration(prop,value,line,ctx,tok,known_vars):
    """单条声明 → 违规列表。tok=None 或 (colors,lengths,shadows,by_use)。

    1) var(--x) 不整条放行——--x 必须在页面域已知集合（正本表 emits + 种子静态声明
       [+ --style-blocks 扩展键 --sp-<键名>]；--sp-* 前缀不再一律放行；--style-* 不在其中，
       引用时报错并提示应改用的页面变量；--device 协议前缀除外）；var 段替换为占位 0 后，
       非变量部分的裸值继续走用途检查（`padding:var(--sp-space-2) 13px` 的 13px 照拦；
       兜底值 `var(--x,137px)` 同样过闸）。
    2) 白名单按用途收集（by_use 桶）——数字不再跨用途搭车。
    3) letter-spacing 过大 → W-TOKEN-TRACKING 提示级（进报告不进退出码，评审关注不拦截）。"""
    colors,lengths,shadows,by_use=tok if tok else (set(),set(),set(),{'radius':set(),'ctlsize':set(),'space':set(),'fontsize':set()})
    vols=[]
    def add(code,seg,grp):vols.append((line,ctx,prop,seg,code,grp))
    p=prop
    if 'var(' in value:
        unknown=[]
        for m in VAR_RE.finditer(value):
            n=m.group(1)
            if n not in known_vars and not n.startswith('--device'):
                unknown.append(n)
        if unknown:
            named=[]
            for n in unknown:
                alt=PAGE_VAR_SUGGEST.get(n)
                named.append(f'{n}（页面应改用 {alt}）' if alt else n)
            add('E-TOKEN-UNKNOWN-VAR',','.join(named),
                '未定义变量（页面域定义处=正本表 emits + 种子静态声明 [+ --style-blocks 扩展键 --sp-<键名>]；'
                '--sp-* 前缀不再一律放行；--style-* 是 chooser 运行时颜色根变量，仅覆盖样式（L2）可引用，'
                '页面请改用页面域变量；引用不存在=渲染失败）')
        # var 段替换为占位 0（物理白名单），非变量部分的裸值继续走下方用途检查
        value=VAR_CALL.sub('0',value)
    if p=='letter-spacing':
        for mnum in PX_RE.finditer(value):
            if float(mnum.group(1))>2:
                add('W-TOKEN-TRACKING',mnum.group(0),'中文字距偏大提示（不拦截；评审关注项）')
    p=prop
    if p in COLOR_PROPS or p in BORDER_WIDTH_PROPS or p in SHADOW_PROPS:
        for c in extract_colors(value):
            if c.lower() in ('transparent','currentcolor'):continue
            nc=norm_color(c)
            if nc is None:continue
            if nc in colors:continue
            grp='阴影 shadow-sm/md（色随令牌）' if p in SHADOW_PROPS else suggest_color_group(p)
            add('E-TOKEN-COLOR',c,grp)
    px_rule=None
    if p in SPACE_PROPS:px_rule=('E-TOKEN-SPACE','间距档 space-1..4')
    elif p in SIZE_PROPS:px_rule=('E-TOKEN-SIZE','尺寸档 size-ctl-sm/md/lg')
    elif p in RADIUS_PROPS:px_rule=('E-TOKEN-RADIUS','圆角 radius-sm/md/lg')
    elif p in FONTSIZE_PROPS:px_rule=('E-TOKEN-FONTSIZE','字阶 size-title/head/body/caption')
    elif p in SHADOW_PROPS:px_rule=('E-TOKEN-SHADOW','阴影 shadow-sm/md')
    elif p in GRID_PROPS:px_rule=('E-TOKEN-GRID','网格列数（U2 展开 --sp-grid-cols）')
    elif p in BORDER_WIDTH_PROPS:px_rule=('E-TOKEN-BORDER','边框宽度（物理白名单仅 1px）')
    if px_rule:
        code,grp=px_rule
        use=by_use.get({('E-TOKEN-SPACE'):'space','E-TOKEN-SIZE':'ctlsize','E-TOKEN-RADIUS':'radius',
                        'E-TOKEN-FONTSIZE':'fontsize','E-TOKEN-GRID':'ctlsize'}.get(code,''),
                       set()) if by_use else set()
        if p in SHADOW_PROPS and re.sub(r'\s+',' ',value).strip().lower() in shadows:
            pass  # 整串归因阴影令牌 → 跳过细项
        else:
            for mnum in PX_RE.finditer(value):
                f=float(mnum.group(1))
                if f==0:continue  # 0 物理白名单
                if f==1 and p in BORDER_WIDTH_PROPS:continue  # 1px 边框物理白名单
                if f in use:continue  # a) 归因令牌（按用途桶——数字不跨用途搭车）
                if f in lengths and not by_use:continue  # 兼容：无 design-system 类型信息时退全局
                add(code,mnum.group(0),grp)
            if p in GRID_PROPS:
                for mm in re.finditer(r'repeat\(\s*(\d+)\s*,',value):
                    k=int(mm.group(1))
                    if float(k) in use:continue
                    add('E-TOKEN-GRID',f'repeat({k},…)','网格列数（U2 展开 --sp-grid-cols）')
    return vols


def lint_file(path,tok,known_vars):
    src=Path(path).read_text(encoding='utf-8-sig',errors='replace')
    vols=[]
    for line,ctx,prop,value in collect_declarations(src):
        vols+=check_declaration(prop,value,line,ctx,tok,known_vars)
    return vols


def main(argv=None):
    ap=argparse.ArgumentParser(prog='lint_tokens.py',description='hard-value lint gate (token attribution)')
    ap.add_argument('target',help='pages directory or a single HTML file')
    ap.add_argument('--design-system',default=None,help='design-system token JSON (missing = physical whitelist only)')
    ap.add_argument('--style-blocks',default=None,
                    help='项目 U2 数据文件 intake/style-blocks.json（或带 STYLE-PACK 围栏的 HTML）：'
                         '风格包扩展键扩充 var() 已知集合；不给时已知集合只含正本表和种子默认值')
    args=ap.parse_args(argv)
    target=Path(args.target)
    files=sorted(target.rglob('*.html') if target.is_dir() else [target]) if target.exists() else None
    if files is None or not files:
        print(f'FAIL no scannable HTML under: {target}',file=sys.stderr);return 2
    tok=None
    if args.design_system:
        ds=Path(args.design_system)
        try:
            if not ds.is_file():raise FileNotFoundError(ds)
            tok=load_token_values(ds)
        except Exception as e:
            print(f'FAIL cannot load design-system JSON: {e}',file=sys.stderr);return 2
    try:
        reg=load_registry()
    except Exception as e:
        print(f'FAIL cannot load token registry (assets/token-keys.json): {e}',file=sys.stderr);return 2
    if args.style_blocks:
        sb=Path(args.style_blocks)
        if not sb.is_file():
            print(f'FAIL --style-blocks file not found: {sb}',file=sys.stderr);return 2
        known_vars=page_known_vars(reg,style_blocks_path=sb)
        src_desc='registry emits + seed static + style-blocks extension keys'
    else:
        known_vars=page_known_vars(reg)
        src_desc='registry emits + seed static (no --style-blocks)'
    print(f'{CHECKER_VERSION} — target: {target} ({len(files)} file(s))')
    if tok is not None:
        print(f'token source: {args.design_system} (colors={len(tok[0])} lengths={len(tok[1])} shadows={len(tok[2])})')
    else:
        print('token JSON not provided — physical whitelist only (no token attribution)')
    print(f'known var set: {len(known_vars)} var(s) ({src_desc})')
    all_vols=[];per_file={}
    for f in files:
        vols=lint_file(f,tok,known_vars)
        per_file[f]=vols;all_vols+=vols
    hard=[v for v in all_vols if not v[4].startswith('W-')]
    warns=[v for v in all_vols if v[4].startswith('W-')]
    for f in files:
        for line,ctx,prop,seg,code,grp in per_file[f]:
            print(f'[{"WARN" if code.startswith("W-") else "FAIL"}] {f}:{line}  {ctx}  {prop}: {seg}  [{code}] -> suggest {grp}' + ('（提示级，不拦截）' if code.startswith('W-') else ' (token-minimum)'))
    n_files_with=sum(1 for v in per_file.values() if v)
    print(f'\nsummary: {len(hard)} violation(s), {len(warns)} warning(s)'
          f' — files with violations: {n_files_with} of {len(files)} scanned'
          f' — {"FAIL" if hard else "PASS"}')
    print(f'exit: {1 if hard else 0}')
    return 1 if hard else 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8',errors='replace')
            sys.stderr.reconfigure(encoding='utf-8',errors='replace')
        except Exception:pass
    sys.exit(main())
