#!/usr/bin/env python3
"""组件样式写死值门禁（verify_component_css）。

范围：assets/editor-seed.html 组件段（「应用骨架」→「编辑器交互层」之间）。
查什么（按 CSS 规则块判，选择器与声明体一起看）：
  1. 裸色值 —— 声明体出现 #hex 且不含 var(（带回退的 var(--x,#hex) 属已接线，放行）；
  2. 裸圆角 —— border-radius:数字 且不含 var(、50%、999px。
放行（二选一，缺一即 FAIL）：
  a. 语义豁免 —— 状态色/手机机身/开关轨道等白名单（WHITELIST，逐条带理由）；
  b. 换肤接线 —— 选择器的类名出现在 style-chooser.js rules 表
     （应用到包时被 chooser 规则覆盖；两文件自动联动，删 chooser 规则后此处即开始报警）。
用法：python scripts/verify_component_css.py   （exit≠0 = 有未接线写死值；build.py formal_gate 自动调用）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / 'assets' / 'editor-seed.html'
CHOOSER = ROOT / 'assets' / 'style-chooser.js'

SEC_START = '/* ============ 应用骨架 ============ */'
SEC_END = '/* ============ 编辑器交互层 ============ */'

# (正则, 理由) —— 对「选择器+声明体」整体匹配；命中即豁免。只豁免确有语义的例外，别往里塞"懒得改"
WHITELIST = [
    (r'tag\.(ok|warn|danger)|b\.dan|note\.(warn|danger|ok)|badge\.ok|stp\.done', '语义状态色（成功/警告/危险，不随风格）'),
    (r'\.statusbar|\.device|\.chrome', '手机机身/浏览器壳（非页面组件）'),
    (r'\.sw\b|\.sw::|\.ed-ui-swatch', '开关轨道/取色点（硬件感中性灰）'),
    (r'::after|\.badge', '白点白芯白字等微元素（勾选点、开关圆芯、小角标）'),
    (r'\.side\b|\.adtop \.who', '后台深色侧栏（包规则整体覆盖，残余辅助色）'),
    (r'\.hero \.hb', '横幅内白胶囊（浮在 hero 上，白底不随风格）'),
    (r'var\(', '已接线（带令牌回退）'),
]
RADIUS_RE = re.compile(r'border-radius:\s*(?!\d*%)\d')
HEX_RE = re.compile(r'#[0-9a-fA-F]{6}\b')
RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}')
CLASS_RE = re.compile(r'\.([a-z][\w-]*)')


def chooser_tokens():
    """style-chooser.js 规则里出现过的类名集合（L1 规则表 + 材质层等引用的组件类）。"""
    text = CHOOSER.read_text(encoding='utf-8')
    tokens = set()
    for m in re.finditer(r"'([^']+)'\s*:", text):
        for cm in CLASS_RE.finditer(m.group(1)):
            tokens.add(cm.group(1))
    return tokens


def verify():
    if not SEED.exists():
        return [f'seed not found: {SEED}']
    seed = SEED.read_text(encoding='utf-8')
    i0 = seed.find(SEC_START)
    i1 = seed.find(SEC_END)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        return [f'component section markers not found ({SEC_START[:20]}... / {SEC_END[:20]}...)']
    section = seed[i0:i1]
    # 行号定位：在原文上按规则头逐个搜索，报告用真实行号
    tokens = chooser_tokens()
    fails = []
    pos = 0
    for m in RULE_RE.finditer(section):
        head, body = m.group(1).strip(), m.group(2)
        if head.startswith('/*') or '@' in head.split(',')[0][:1]:
            continue
        lineno = seed[:i0 + m.start()].count('\n') + 1
        joined = head + '{' + body + '}'
        whit = next((r for r, _ in WHITELIST if re.search(r, joined)), None)
        wired = any(s in tokens for s in CLASS_RE.findall(head))
        if HEX_RE.search(body) and 'var(' not in body and not whit and not wired:
            fails.append(f'L{lineno} 裸色值 {HEX_RE.search(body).group(0)} → {head.strip()[:60]}')
        if RADIUS_RE.search(body) and 'var(' not in body and '50%' not in body and '999' not in body \
                and not whit and not wired:
            fails.append(f'L{lineno} 裸圆角 → {head.strip()[:60]}')
        pos = m.end()
    return fails


def main():
    fails = verify()
    if fails:
        print('FAIL 组件样式存在未接线写死值（%d 处）——接 var(令牌,原值) 或进 chooser 换肤规则表，确属语义例外才进 WHITELIST：' % len(fails))
        for f in fails:
            print('  ' + f)
        return 1
    print('PASS 组件样式写死值门禁（裸色/裸圆角均已接线或在案豁免）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
