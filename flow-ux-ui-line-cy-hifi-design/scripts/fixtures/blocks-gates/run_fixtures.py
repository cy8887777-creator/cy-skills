"""run_fixtures — blocks-gates 补洞规则全量样例回归（预期 vs 实际逐条打印）。

用法：python run_fixtures.py （可从任何目录运行——样例路径锚定本脚本所在目录）
每条规则一对样例（该通过 / 该报错），映射：
  R0 合法基线（数据文件形态 + 围栏 HTML 形态 + 锁定匹配）
  R1a 风格包 tokens 驼峰键名 → E-PACK-KEY（别名命中→正本键；纯驼峰→自动转连字符并按命名族补前缀）
  R1b 合法形态但近正本键（别名命中 / 编辑距离≤2）→ E-PACK-KEY-NEAR（族内延伸豁免）
  R1c 采纳建议后的族内扩展键 size-ctl-xs 放行（family-ext-ok.json）
  R2a 锁定键在风格包里找不到 → E-LOCK-KEY-MISSING（原跳过，现报错）
  R2b skeletonTokens 键名驼峰 → E-LOCK-KEY
  R3  组件引用未定义变量 --sp-surface → E-COMP-UNKNOWN-VAR
  R4  l2Overrides :root 选择器 + 写坏声明 ":ok:…" → E-L2-SELECTOR / E-L2-DECL
  R4b/R4d l2 props var() 引用存在性 → E-L2-UNKNOWN-VAR（STYLE_OWNED_VARS 在已知集合内）
  R4e/R4f l2 props 危险字符 { } < > /* → E-L2-DECL（; 分隔符与引号合法保留）
  R5/R6 配色<2 + 族单成员 → W-PACK-PALETTES / W-FAMILY-SOLO（提醒，退出码仍 0）
  R7  数据文件直读（R0a 即 R7 的通过样例）
  R8a/R8b density 值域 → E-PACK-KEY-VALUE（ok-full 基线含合法 density；bad-density 为 airy）
  S2a tokens 值注入字符 ; { } < > /* → E-PACK-VALUE-CHARS（通过样例=ok-full 基线）
  S2b packId 白名单 ^[A-Za-z0-9_-]+$ → E-PACK-ID
  S2d tokens 值 TODO 未填占位 → E-PACK-TODO（占位进产物=壳层 UI 非包作用域元素读非法颜色透明）
  S2c l2 选择器注入字符 { } < > ; " /* → E-L2-SELECTOR-CHARS
  S3  iconSet=null/空串/缺省=不约束图标族，放行；非字符串 → E-BLOCK-FIELD
  S4  allowed 键的值非字符串（density: 3）→ E-PACK-KEY-VALUE（通过样例=ok-full 基线）
  S5a 包 tokens 缺正本表 minimum 最小集 → E-PACK-MINIMUM（通过样例=ok-full 基线）
  S5b skeletonTokens 缺 minimum → E-LOCK-MINIMUM（通过样例=R0c）
  S6  裸色值只在样式上下文查 → E-COMP-RAW-COLOR（正文"订单 #1024"放行）
  L1-L5 lint_tokens var() 页面域已知集合（正本表+种子默认值，± --style-blocks 扩展键）
  L6  lint 页面引用 --style-* → E-TOKEN-UNKNOWN-VAR 并提示应改用的页面变量
退出码：全部符合预期=0，任一不符=1。
"""
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
SCRIPTS=HERE.parents[1]          # scripts/
SKILL=SCRIPTS.parent             # 技能根

CASES=[
 dict(name='R0a 合法基线·数据文件形态（=R7/R8a/S2/S4/S5a 通过样例：含合法 density、值无注入字符、minimum 齐）',
      script='verify_blocks.py', args=['ok-full.json'],
      expect_exit=0, expect=[],
      expect_absent=['[FAIL]','[warn]','E-PACK-KEY-VALUE','E-PACK-MINIMUM','E-PACK-VALUE-CHARS','E-PACK-ID','E-L2-SELECTOR-CHARS']),
 dict(name='R0b 合法基线·围栏 HTML 形态', script='verify_blocks.py', args=['ok-fenced.html'],
      expect_exit=0, expect=[], expect_absent=['[FAIL]','[warn]']),
 dict(name='R0c 合法基线·锁定回传匹配（=R2/S5b 通过样例：skeletonTokens minimum 齐）', script='verify_blocks.py',
      args=['ok-full.json','--lock','ok-lock-sel.json'],
      expect_exit=0, expect=[], expect_absent=['[FAIL]','E-LOCK','[warn]']),
 dict(name='R1a 风格包 tokens 驼峰键名（该报错，附正确写法；=R1c 报错样例：建议落正本命名族）', script='verify_blocks.py', args=['bad-keys-camel.json'],
      expect_exit=1,
      expect=[('E-PACK-KEY:',2),('请改写为 "size-ctl-xs"（驼峰自动转换，并入正本命名族 size-*）',1),('请改写为 "radius-md"（正本表别名）',1)],
      expect_absent=['E-PACK-KEY-NEAR']),
 dict(name='R1c 族内扩展键 size-ctl-xs 放行（=采纳 R1a 建议后的名字不被近似键拦截）', script='verify_blocks.py', args=['family-ext-ok.json'],
      expect_exit=0, expect=[], expect_absent=['E-PACK-KEY','[FAIL]','[warn]']),
 dict(name='R1b 近正本键名：别名命中 / 编辑距离≤2（该报错，附建议）', script='verify_blocks.py', args=['bad-keys-near.json'],
      expect_exit=1,
      expect=[('E-PACK-KEY-NEAR:',2),('命中正本表别名——正本键是 "space-2"',1),('仅差 1 个字符——若指同一参数请改用正本键 "radius-md"',1)],
      expect_absent=['E-PACK-KEY:']),
 dict(name='R2a 锁定键在风格包里找不到（原跳过→现报错）', script='verify_blocks.py',
      args=['bad-lock-missing.json','--lock','bad-lock-missing-sel.json'],
      expect_exit=1, expect=[('E-LOCK-KEY-MISSING:',1),('锁定键必须在风格包里落地',1)],
      expect_absent=['E-LOCK-KEY:','E-LOCK-MUTATED','E-LOCK-MINIMUM']),
 dict(name='R2b skeletonTokens 键名驼峰（该报错，附正确写法）', script='verify_blocks.py',
      args=['bad-lock-camel.json','--lock','bad-lock-camel-sel.json'],
      expect_exit=1, expect=[('E-LOCK-KEY:',1),('请改写为 "radius-md"',1)],
      expect_absent=['E-LOCK-KEY-MISSING','E-LOCK-MUTATED','E-LOCK-MINIMUM']),
 dict(name='R3 组件引用未定义变量 --sp-surface（该报错）', script='verify_blocks.py', args=['bad-var.json'],
      expect_exit=1, expect=[('E-COMP-UNKNOWN-VAR:',1),('--sp-surface',1)],
      expect_absent=['E-L2-','E-PACK-KEY']),
 dict(name='R4 l2Overrides :root 选择器 + 写坏声明 ":ok:…"（该报错）', script='verify_blocks.py', args=['bad-l2.json'],
      expect_exit=1, expect=[('E-L2-SELECTOR:',1),('E-L2-DECL:',1),(':ok:#00A2C7',1),('请改写成页面容器类',1)],
      expect_absent=['E-COMP-UNKNOWN-VAR']),
 dict(name='R4b l2 props var() 引用 STYLE_OWNED_VARS/emits 变量放行（=R4d 通过样例）', script='verify_blocks.py', args=['l2-var-ok.json'],
      expect_exit=0, expect=[], expect_absent=['E-L2-UNKNOWN-VAR','[FAIL]']),
 dict(name='R4d l2 props var() 引用未定义变量（该报错）', script='verify_blocks.py', args=['l2-var-bad.json'],
      expect_exit=1, expect=[('E-L2-UNKNOWN-VAR:',1),('--style-nope',1)],
      expect_absent=['E-L2-SELECTOR','E-L2-DECL','E-COMP-UNKNOWN-VAR']),
 dict(name='R8b density 值不在正本 allowed 内（该报错，列出可选值；=R8a 报错样例）', script='verify_blocks.py', args=['bad-density.json'],
      expect_exit=1, expect=[('E-PACK-KEY-VALUE:',1),('airy',1),('compact、regular、loose',1)],
      expect_absent=['E-PACK-KEY:','E-PACK-KEY-NEAR']),
 dict(name='S2a tokens 值含注入字符 ;（该报错，运行时同口径）', script='verify_blocks.py', args=['bad-value-chars.json'],
      expect_exit=1, expect=[('E-PACK-VALUE-CHARS:',1),('禁用字符',1)],
      expect_absent=['E-PACK-ID','E-L2-','E-PACK-MINIMUM']),
 dict(name='S2d tokens 值是 TODO 未填占位（该报错 E-PACK-TODO，占位进产物=壳层 UI 读非法颜色透明；排查 P2-18 补样例）',
      script='verify_blocks.py', args=['bad-todo-placeholder.json'],
      expect_exit=1, expect=[('E-PACK-TODO:',1),('未填占位',1)],
      expect_absent=['E-PACK-VALUE-CHARS','E-PACK-MINIMUM']),
 dict(name='S2b packId 含非法字符（该报错，白名单 ^[A-Za-z0-9_-]+$）', script='verify_blocks.py', args=['bad-packid.json'],
      expect_exit=1, expect=[('E-PACK-ID:',1),('只允许字母/数字/下划线/连字符',1)],
      expect_absent=['E-BLOCK-REF','E-PACK-VALUE-CHARS']),
 dict(name='S2c l2 选择器含注入字符 {（该报错）', script='verify_blocks.py', args=['bad-l2-selector-chars.json'],
      expect_exit=1, expect=[('E-L2-SELECTOR-CHARS:',1)],
      expect_absent=['E-L2-SELECTOR:','E-L2-DECL','E-L2-UNKNOWN-VAR']),
 dict(name='R4e l2 props 分号/引号合法保留（=props 危险字符通过样例）', script='verify_blocks.py', args=['l2-props-chars-ok.json'],
      expect_exit=0, expect=[], expect_absent=['E-L2-DECL','[FAIL]']),
 dict(name='R4f l2 props 含 { } < > /*（该报错 E-L2-DECL；; 合法保留）', script='verify_blocks.py', args=['l2-props-chars-bad.json'],
      expect_exit=1, expect=[('E-L2-DECL:',1),('危险字符',1),('合法声明分隔符',1)],
      expect_absent=['E-L2-UNKNOWN-VAR']),
 dict(name='S3a iconSet=null / 缺省（不约束图标族，该通过）', script='verify_blocks.py', args=['iconset-null-ok.json'],
      expect_exit=0, expect=[], expect_absent=['E-BLOCK-FIELD','[FAIL]']),
 dict(name='S3b iconSet 非字符串（该报错）', script='verify_blocks.py', args=['iconset-bad.json'],
      expect_exit=1, expect=[('E-BLOCK-FIELD',1),('iconSet',1),('不约束图标族',1)],
      expect_absent=[]),
 dict(name='S4b allowed 键的值非字符串 density: 3（该报错）', script='verify_blocks.py', args=['bad-density-num.json'],
      expect_exit=1, expect=[('E-PACK-KEY-VALUE:',1),('got int',1),('compact、regular、loose',1)],
      expect_absent=['E-PACK-MINIMUM']),
 dict(name='S5a 包 tokens 缺 minimum 最小集（该报错，列出缺失键）', script='verify_blocks.py', args=['bad-minimum.json'],
      expect_exit=1, expect=[('E-PACK-MINIMUM:',1),('缺少正本表最小集',1),('radius-md',1),('space-4',1)],
      expect_absent=['E-PACK-KEY:','E-PACK-KEY-NEAR']),
 dict(name='S5b skeletonTokens 缺 minimum 最小集（该报错，列出缺失键）', script='verify_blocks.py',
      args=['bad-lock-minimum.json','--lock','bad-lock-minimum-sel.json'],
      expect_exit=1, expect=[('E-LOCK-MINIMUM:',1),('font-head',1),('size-body',1),('space-3',1)],
      expect_absent=['E-LOCK-KEY:','E-LOCK-KEY-MISSING','E-LOCK-MUTATED']),
 dict(name='S6a 正文里的 #1024 不是颜色（该通过；=E-COMP-RAW-COLOR 通过样例）', script='verify_blocks.py', args=['raw-color-ok.json'],
      expect_exit=0, expect=[], expect_absent=['E-COMP-RAW-COLOR','[FAIL]','[warn]']),
 dict(name='S6b 样式上下文裸色值 fill="#FF0000"（该报错）', script='verify_blocks.py', args=['raw-color-bad.json'],
      expect_exit=1, expect=[('E-COMP-RAW-COLOR:',1),('#FF0000',1),('样式上下文',1)],
      expect_absent=['E-COMP-UNKNOWN-VAR']),
 dict(name='R5/R6 配色<2 + 族单成员 → 提醒不拦截（退出码仍 0；ok-full 即两者的通过样例）',
      script='verify_blocks.py', args=['warn-single.json'],
      expect_exit=0,
      expect=[('W-PACK-PALETTES',1),('品牌色盘那一版必须有',1),('W-FAMILY-SOLO',1),('每族顺手送 1-2 个同族变体',1)],
      expect_absent=['[FAIL]']),
 dict(name='L1 lint·全部引用已知变量（该通过）', script='lint_tokens.py', args=['lint-ok.html'],
      expect_exit=0, expect=[], expect_absent=['E-TOKEN-','FAIL']),
 dict(name='L2 lint·--sp-surface 未定义 + 间距硬值照拦（该报错）', script='lint_tokens.py', args=['lint-bad.html'],
      expect_exit=1,
      expect=[('E-TOKEN-UNKNOWN-VAR',1),('--sp-surface',1),('E-TOKEN-SPACE',1),('13px',1)],
      expect_absent=[]),
 dict(name='L3 lint·不给 --style-blocks：扩展键 --sp-surface-2 未知（该报错）', script='lint_tokens.py', args=['lint-ext.html'],
      expect_exit=1, expect=[('E-TOKEN-UNKNOWN-VAR',1),('--sp-surface-2',1)], expect_absent=[]),
 dict(name='L4 lint·给 --style-blocks：包内扩展键 --sp-surface-2 已知（该通过）', script='lint_tokens.py',
      args=['lint-ext.html','--style-blocks','lint-blocks.json'],
      expect_exit=0, expect=[], expect_absent=['E-TOKEN-UNKNOWN-VAR','FAIL']),
 dict(name='L5 lint·合法数据 + 正式 design-system.json（合法数据结果不变）', script='lint_tokens.py',
      args=['lint-ok.html','--design-system',str(SKILL/'assets'/'design-system.json')],
      expect_exit=0, expect=[], expect_absent=['FAIL']),
 dict(name='L6 lint·页面引用 --style-line（该报错，提示改用页面变量 --line）', script='lint_tokens.py', args=['lint-style-var.html'],
      expect_exit=1,
      expect=[('E-TOKEN-UNKNOWN-VAR',1),('--style-line',1),('页面应改用 --line',1)],
      expect_absent=[]),
]


def run_case(case):
    cmd=[sys.executable,str(SCRIPTS/case['script'])]
    for a in case['args']:
        s=str(a)
        if s.startswith('-') or Path(s).is_absolute():
            cmd.append(s)  # 旗标 / 绝对路径原样
        else:
            cmd.append(str(HERE/s))  # 样例路径锚定本脚本所在目录，任意 cwd 可运行
    env=dict(os.environ,PYTHONIOENCODING='utf-8')
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',
                     env=env,timeout=180,cwd=HERE)
    out=(r.stdout or '')+(r.stderr or '')
    ok=True
    print(f"\n== {case['name']}")
    print(f"   命令: {case['script']} {' '.join(str(a) for a in case['args'])}")
    got_exit=r.returncode
    want_exit=case['expect_exit']
    line_ok=got_exit==want_exit
    ok&=line_ok
    print(f"   退出码  预期 {want_exit} / 实际 {got_exit}  {'OK' if line_ok else 'NG'}")
    for sub,want_n in case['expect']:
        got_n=out.count(sub)
        line_ok=(got_n==want_n) if want_n is not None else (got_n>0)
        ok&=line_ok
        print(f"   预期 含 \"{sub}\" ×{want_n if want_n is not None else '≥1'} / 实际 ×{got_n}  {'OK' if line_ok else 'NG'}")
    for sub in case['expect_absent']:
        got_n=out.count(sub)
        line_ok=got_n==0
        ok&=line_ok
        print(f"   预期 不含 \"{sub}\" / 实际 ×{got_n}  {'OK' if line_ok else 'NG'}")
    # 失败用例附输出尾部，便于就地看差异
    if not ok:
        tail=out.strip().splitlines()[-12:]
        print('   ---- 实际输出尾部 ----')
        for ln in tail:
            print('   | '+ln)
    return ok


def main():
    if hasattr(sys.stdout,'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8',errors='replace')
        except Exception:
            pass
    n_ok=0;n_bad=0
    for case in CASES:
        if run_case(case):n_ok+=1
        else:n_bad+=1
    total=len(CASES)
    print(f'\nsummary: {total} case(s): {n_ok} matched / {n_bad} mismatched — {"PASS" if n_bad==0 else "FAIL"}')
    return 0 if n_bad==0 else 1


if __name__=='__main__':
    sys.exit(main())
