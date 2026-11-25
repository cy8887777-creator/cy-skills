"""_token_registry — verify_blocks / lint_tokens 共用的键名正本表与变量集合读取层（单一出处）。

两边不得各自手抄的口径都在这里：
- assets/token-keys.json（冻结正本表）：键名 pattern / 正本键 / 别名 / emits 变量 /
  allowed 值域 / minimum 最小集；
- assets/editor-seed.html：种子静态自定义属性（页面域种子默认值）+ STYLE_OWNED_VARS
  （chooser 换肤运行时写 to documentElement 的 13 个颜色根变量，如 --style-line）；
- 风格数据读取：U2 数据文件（intake/style-blocks.json）/ 单块 JSON / 带 STYLE-PACK
  围栏的 HTML 三形态统一（load_pack_source + extract_style_packs）；
- var() 已知集合分层（口径）：
  * 页面域（lint_tokens）：正本表 emits 变量 + 种子静态声明 + 风格包扩展键 --sp-<键名>。
    --style-* 不在其中——它们由 chooser 运行时写在 documentElement 上，页面 CSS 应使用
    页面域变量（--bg/--text/--line/--accent…），报错提示按 PAGE_VAR_SUGGEST 给出改法；
  * 覆盖样式/组件（verify_blocks 的 l2Overrides 与组件包检查）：页面域集合 ∪ STYLE_OWNED_VARS
    （L2 挂在运行时根上、与 chooser 同层，允许引用 13 个颜色根变量）。
键名规则（check_token_key 及其辅助）也只在此处实现：别名命中、驼峰自动转换并按正本命名族
补前缀（ctlXs→size-ctl-xs）、族内延伸豁免（size-ctl-xs 之于 size-ctl-sm 不算近似键）。
"""
import json
import re
from pathlib import Path

SKILL_ROOT=Path(__file__).resolve().parent.parent

# --style-* → 页面应改用的页面域变量（语义映射，非名单抄写；--style-dark-* 按角色对应）
PAGE_VAR_SUGGEST={
 '--style-bg':'--bg','--style-surface':'--surface','--style-text':'--text',
 '--style-muted':'--muted','--style-line':'--line','--style-soft':'--soft',
 '--style-dark-bg':'--bg（暗色场景）','--style-dark-surface':'--surface（暗色场景）',
 '--style-dark-text':'--text（暗色场景）','--style-dark-muted':'--muted（暗色场景）',
 '--style-dark-line':'--line（暗色场景）',
}


def load_registry():
    """键名正本表 → {keys, alias, emits, allowed, minimum, pattern}。
    minimum=正本表 minimum=true 的键集合（风格包 tokens 与选型 skeletonTokens 的必含最小集）。"""
    data=json.loads((SKILL_ROOT/'assets'/'token-keys.json').read_text(encoding='utf-8-sig'))
    keys=[];alias={};emits=set();allowed={};minimum=set()
    for k in data.get('keys') or []:
        key=k.get('key')
        if isinstance(key,str):keys.append(key)
        for a in k.get('aliases') or []:
            if isinstance(a,str):alias.setdefault(a,key)
        for e in k.get('emits') or []:
            if isinstance(e,str) and e.startswith('--'):emits.add(e)
        if isinstance(k.get('allowed'),list):
            allowed[key]=[v for v in k['allowed'] if isinstance(v,str)]
        if k.get('minimum') is True and isinstance(key,str):minimum.add(key)
    return {'keys':keys,'alias':alias,'emits':emits,'allowed':allowed,'minimum':minimum,
            'pattern':data.get('keyPattern') or r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'}


def load_seed_vars():
    """产物种子 editor-seed.html 的静态自定义属性（种子默认值，页面无风格包时也可引用）→ 集合。"""
    return _seed_text_vars(_seed_text())


def load_style_owned_vars():
    """种子 STYLE_OWNED_VARS（chooser 运行时颜色根变量，--style-* 等 13 个）→ 集合。
    从 editor-seed.html 的 JS 数组字面量解析，不手抄；解析失败返回空集。"""
    text=_seed_text()
    if not text:return set()
    m=re.search(r'STYLE_OWNED_VARS\s*=\s*\[([^\]]*)\]',text)
    if not m:return set()
    return set(re.findall(r'"(--[a-zA-Z0-9-]+)"',m.group(1)))


def _seed_text():
    p=SKILL_ROOT/'assets'/'editor-seed.html'
    try:
        return p.read_text(encoding='utf-8-sig',errors='replace')
    except Exception:
        return ''


def _seed_text_vars(text):
    if not text:return set()
    return {m.group(1) for m in re.finditer(r'(--[a-zA-Z0-9-]+)\s*:',text)}


# ---------------------------------------------------------------- 键名规则（单一出处）
def camel_to_kebab(s):
    """驼峰 → 连字符：radiusMd→radius-md、ctlXs→ctl-xs、radiusPill→radius-pill。"""
    return re.sub(r'(?<=[a-z0-9])([A-Z])',lambda m:'-'+m.group(1).lower(),s).lower()


def _lev(a,b,cap=2):
    """Levenshtein 编辑距离，超过 cap 提前剪枝返回 cap+1。"""
    if abs(len(a)-len(b))>cap:return cap+1
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        if min(cur)>cap:return cap+1
        prev=cur
    return prev[len(b)]


def _family_prefix_suggest(naive,reg):
    """按正本表命名规律给驼峰转换结果补族前缀：naive 首词若命中某正本键的第二词
    （如 ctl ← size-ctl-sm），借该键的族前缀补全（ctl-xs→size-ctl-xs）。
    找不到族 → 原样返回。"""
    parts=naive.split('-')
    if len(parts)<2:return naive,None
    core=parts[0]
    for k in reg['keys']:
        kw=k.split('-')
        if len(kw)>=2 and kw[1]==core:
            return kw[0]+'-'+naive,kw[0]
    return naive,None


def _is_family_extension(key,ck,reg):
    """key 是否为正本键 ck 的同族延伸：前 n-1 词逐词相同、仅末词为全新词，
    且新末词不以正本表任何词开头（防 sm2/mdx 这类笔误借豁免漏网）。"""
    kw=key.split('-');cw=ck.split('-')
    if len(kw)!=len(cw) or len(kw)<2:return False
    if kw[:-1]!=cw[:-1] or kw[-1]==cw[-1]:return False
    allwords={w for k in reg['keys'] for w in k.split('-')}
    return not any(kw[-1].startswith(w) for w in allwords)


def check_token_key(key,reg):
    """单键校验 → (ok, rule, msg)。不合规则时 msg 用中文写明正确写法：
    先查正本表 aliases；查不到再驼峰自动转连字符并按命名族补前缀。
    表外键放行（含族内延伸）；近似正本键的表外键报 E-PACK-KEY-NEAR。"""
    if not re.match(reg['pattern'],key):
        if key in reg['alias']:
            can=reg['alias'][key]
            return False,'E-PACK-KEY',f'键名 "{key}" 不合正本表规则（全小写连字符）——这是正本键 "{can}" 的常见错误写法，请改写为 "{can}"（正本表别名）'
        sug=camel_to_kebab(key)
        if sug!=key and re.match(reg['pattern'],sug):
            sug,fam=_family_prefix_suggest(sug,reg)
            why=f'（驼峰自动转换，并入正本命名族 {fam}-*）' if fam else '（驼峰自动转换）'
            return False,'E-PACK-KEY',f'键名 "{key}" 不合正本表规则（全小写连字符）——请改写为 "{sug}"{why}；若它对应正本表参数，请以 assets/token-keys.json 的键名为准'
        return False,'E-PACK-KEY',f'键名 "{key}" 不合正本表规则（一律全小写连字符；驼峰/下划线/大写均不许）——请改写为全小写连字符并对照 assets/token-keys.json'
    if key in reg['keys']:return True,None,''
    if key in reg['alias']:
        can=reg['alias'][key]
        return False,'E-PACK-KEY-NEAR',f'键名 "{key}" 命中正本表别名——正本键是 "{can}"，请改用正本键名 "{can}"'
    best=None;bd=3
    for ck in reg['keys']:
        if _is_family_extension(key,ck,reg):
            continue  # 族内延伸（size-ctl-xs 之于 size-ctl-sm）不算近似——合法扩展参数
        d=_lev(key,ck,2)
        if d<bd:best,bd=ck,d
    if best is not None:
        return False,'E-PACK-KEY-NEAR',f'扩展键 "{key}" 与正本键 "{best}" 仅差 {bd} 个字符——若指同一参数请改用正本键 "{best}"，否则请换区分度更高的键名（扩展参数同样必须全小写连字符）'
    return True,None,''  # 表外扩展参数：放行（运行时生成 --sp-<键名>）


# ---------------------------------------------------------------- 风格数据读取（三形态统一）
def load_pack_source(text):
    """输入形态识别：整文件 JSON 且含受控块键 → U2 数据文件；否则按围栏 HTML 处理。"""
    try:
        obj=json.loads(text)
    except Exception:
        obj=None
    if isinstance(obj,dict) and any(k in obj for k in ('STYLE-REGISTRY','STYLE-PACK','COMPONENT-PACK','STYLE-CONTRACT')):
        return 'data-file',obj
    return 'fenced-html',text


def extract_style_packs(source):
    """风格数据 → packs 列表。source 可为：U2 数据文件对象/文本、单块 JSON（{packs:[…]} 或
    {"STYLE-PACK":{…}}）、带 STYLE-PACK 围栏的 HTML 文本。取不到返回空列表。"""
    obj=None;text=None
    if isinstance(source,str):
        text=source
        try:
            obj=json.loads(source)
        except Exception:
            obj=None
    elif isinstance(source,dict):
        obj=source
    packs=None
    if isinstance(obj,dict) and isinstance(obj.get('STYLE-PACK'),dict):
        packs=obj['STYLE-PACK'].get('packs')
    elif isinstance(obj,dict) and isinstance(obj.get('packs'),list):
        packs=obj['packs']
    elif text is not None:
        m=(re.search(r'<!--\s*STYLE-PACK:BEGIN\s*-->([\s\S]*?)<!--\s*STYLE-PACK:END\s*-->',text)
           or re.search(r'<script\b(?=[^>]*\bdata-block=["\']STYLE-PACK["\'])[^>]*>([\s\S]*?)</script>',text,re.I)
           or re.search(r'/\*STYLE-PACK_START\*/([\s\S]*?)/\*STYLE-PACK_END\*/',text))
        if m:
            try:
                sp=json.loads(m.group(1).strip())
                packs=sp.get('packs') if isinstance(sp,dict) else None
            except Exception:
                packs=None
    if not isinstance(packs,list):return []
    return [pk for pk in packs if isinstance(pk,dict)]


# ---------------------------------------------------------------- var() 已知集合（分层口径）
def _pack_ext_vars(reg,packs):
    """风格包每个扩展键（含键名暂不合规的，按字面生成）对应的 --sp-<键名>。"""
    ext=set()
    for pk in packs or []:
        toks=pk.get('tokens') if isinstance(pk,dict) else None
        if not isinstance(toks,dict):continue
        for k in toks:
            if isinstance(k,str) and k not in reg['keys']:
                ext.add('--sp-'+k)
    return ext


def page_known_vars(reg,packs=None,style_blocks_path=None):
    """页面域已知集合 = 正本表 emits 变量 + 种子静态声明 + 风格包扩展键 --sp-<键名>。
    不含 STYLE_OWNED_VARS：--style-* 由 chooser 运行时写 documentElement，页面 CSS 应使用
    页面域变量（--bg/--text/--line/--accent…）。
    风格数据入口二选一：packs（已解析）或 style_blocks_path（文件路径，三形态皆可）。"""
    known=set(reg['emits'])|load_seed_vars()
    if style_blocks_path is not None:
        p=Path(style_blocks_path)
        try:
            packs=extract_style_packs(p.read_text(encoding='utf-8-sig',errors='replace'))
        except Exception:
            packs=[]
    known|=_pack_ext_vars(reg,packs)
    return known


def overrides_known_vars(reg,packs=None):
    """覆盖样式/组件（L2）已知集合 = 页面域集合 ∪ STYLE_OWNED_VARS。
    L2 挂运行时根、与 chooser 同层，允许引用 13 个颜色根变量（--style-line 等）。"""
    known=page_known_vars(reg,packs)
    known|=load_style_owned_vars()
    return known
