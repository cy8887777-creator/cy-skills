#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_e2e — hifi-editable-gui-ux-design 技能端到端实测（一条命令跑完，exit 0 = 全部符合）。

正向链（全部用技能真实脚本，产物落 %TEMP%/e2e-style-*）：
  S1 verify_blocks.py --lock          风格数据自检（参数名/变量/覆盖样式/锁定值）
  S2 lint_tokens.py                   页面硬值 lint（归因令牌）
  S3 build.py --check（目录模式，带 --style-blocks）页面预检 + 命名检查
  S4 qa_receipt.py --make ×2          U1 回执 + U2(final) 回执
  S5 build.py 正式构建（SKILL.md U3 命令 + --u1-receipt/--u2-receipt/--u3-report + --active-pack）
  S6 assert_runtime.cjs               Playwright 运行时断言（切包/配色/跨族/卡片令牌行/组件面板/页面树）
  S7 state_check.py --mark U1 passed  站状态机 + 下一站 U2 要点清单

反向实测（每条独立坏数据，断言被对应检查拦下 / 给出提醒）：
  R1 驼峰参数名 radiusMd            → E-PACK-KEY        exit 1
  R2 覆盖样式坏声明 :ok:#00A2C7     → E-L2-DECL         exit 1
  R3 组件引用未知变量 --sp-surface  → E-COMP-UNKNOWN-VAR exit 1
  R4 覆盖样式选择器 :root           → E-L2-SELECTOR     exit 1
  R5 锁定键在包内缺失               → E-LOCK-KEY-MISSING exit 1
  R6 只有一套配色                   → W-PACK-PALETTES   提醒（exit 0）
  R7 族只有一个成员                 → W-FAMILY-SOLO     提醒（exit 0）
  R8 页面文件夹英文                 → E-NAMING-GROUP    exit 1
  R9 页头描述泄漏内部编号 db-a      → E-NAMING-ID-LEAK  exit 1
  R10 density 写成 airy             → E-PACK-KEY-VALUE  exit 1
  R11 选型结果缺最小集             → E-LOCK-MINIMUM    exit 1
  R12 风格包缺最小集               → E-PACK-MINIMUM    exit 1
  R13 参数值含 }                   → E-PACK-VALUE-CHARS exit 1
  R14 packId 含非法字符            → E-PACK-ID         exit 1
  R15 覆盖样式选择器含 {           → E-L2-SELECTOR-CHARS exit 1
  R16 覆盖样式属性值含 }           → E-L2-DECL         exit 1
  R17 组件正文写「订单 #1024」     → 正向豁免：不报 E-COMP-RAW-COLOR（exit 0）
  R18 页面引用 --style-line        → E-TOKEN-UNKNOWN-VAR 且提示改用 --line

用法：python run_e2e.py   （E2E_SHOW_RUNTIME=1 打印 S6 断言明细）
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent
SCRIPTS = SKILL / 'scripts'
PYTHON = sys.executable
NODE_MODULES = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'node_modules')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(HERE))
import e2e_fixture  # noqa: E402

RESULTS = []
SECTION = ['']


def section(title):
    SECTION[0] = title
    print('\n===== ' + title + ' =====')


def record(name, ok, expect, actual, keep_out=None):
    RESULTS.append({'section': SECTION[0], 'name': name, 'ok': bool(ok),
                    'expect': expect, 'actual': actual})
    tag = '[PASS] ' if ok else '[FAIL] '
    print(tag + SECTION[0] + ' · ' + name)
    print('       预期: ' + expect)
    print('       实际: ' + actual)
    if keep_out and not ok:
        print('       ---- 输出摘录 ----')
        for ln in keep_out.splitlines()[:40]:
            print('       | ' + ln)


def run(cmd, cwd=None, timeout=420):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    if NODE_MODULES and os.path.isdir(NODE_MODULES):
        env['NODE_PATH'] = env.get('NODE_PATH') or NODE_MODULES
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       env=env, timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def first_line_with(out, needle):
    for ln in out.splitlines():
        if needle in ln:
            return ln.strip()
    return ''


# ================================================================ 反向用例工具
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def reverse_case(base, idx, title, mutate, runner, expect_code, expect_needle=None, forbid=None):
    """每条单独造一份坏数据：scratch = base/reverse/<idx>/。mutate(scratch) 落文件，runner(scratch) 跑检查。
    expect_needle：输出必须含的规则码/提示；forbid：输出必须不含的规则码（正向豁免用例）。"""
    scratch = base / ('reverse-%02d' % idx)
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    mutate(scratch)
    code, out = runner(scratch)
    hit = first_line_with(out, expect_needle) if expect_needle else ''
    banned = first_line_with(out, forbid) if forbid else ''
    ok = (code == expect_code) and (hit != '' if expect_needle else True) and (banned == '' if forbid else True)
    if expect_needle:
        actual = 'exit %d；%s' % (code, hit if hit else '未找到 %s' % expect_needle)
        expect = 'exit %d 且输出含 %s' % (expect_code, expect_needle)
    else:
        actual = 'exit %d；%s' % (code, '未出现 %s' % forbid if forbid else '（无附加断言）')
        expect = 'exit %d%s' % (expect_code, (' 且不出现 %s' % forbid) if forbid else '')
    if forbid and banned:
        actual += '；违规出现: %s' % banned
    record('R%d %s' % (idx, title), ok, expect, actual, keep_out=out)


def mutated_style_blocks(scratch, pack_mut, extra=None):
    """把正向 style-blocks 深拷贝后按 pack_mut(pack) 变异，落盘到 scratch。"""
    sb = copy.deepcopy(e2e_fixture.style_blocks())
    for pack in sb['STYLE-PACK']['packs']:
        pack_mut(pack)
    write_json(scratch / 'style-blocks.json', sb)
    if extra:
        extra(sb, scratch)
    return scratch / 'style-blocks.json'


def vb_runner(sb_path, lock_path=None):
    def run_it(_scratch):
        cmd = [PYTHON, SCRIPTS / 'verify_blocks.py', str(sb_path)]
        if lock_path:
            cmd += ['--lock', str(lock_path)]
        return run(cmd)
    return run_it


# ================================================================ 主流程
def main():
    t0 = time.time()
    tmp = Path(tempfile.gettempdir())
    # 清扫本脚本此前运行残留的 e2e-style-* 目录
    for old in tmp.glob('e2e-style-*'):
        shutil.rmtree(old, ignore_errors=True)
    base = tmp / ('e2e-style-%d-%d' % (os.getpid(), int(t0)))
    base.mkdir(parents=True)
    print('技能根: %s' % SKILL)
    print('运行目录: %s' % base)

    proj = e2e_fixture.build_positive_project(base / 'project')
    intake = proj / 'intake'
    sb = intake / 'style-blocks.json'
    sel = intake / 'selection-result.json'
    start_doc = intake / '开工文档.md'
    pages = proj / 'pages'
    qa = proj / 'qa'

    # ---------------- S1 风格数据自检 ----------------
    section('S1 verify_blocks --lock（风格数据自检）')
    code, out = run([PYTHON, SCRIPTS / 'verify_blocks.py', str(sb), '--lock', str(sel)])
    record('四受控块 + 锁定值校验通过', code == 0 and '[FAIL]' not in out,
           'exit 0，无 [FAIL]', 'exit %d；summary 行: %s' % (code, first_line_with(out, 'summary') or out.strip()[:120]),
           keep_out=out)

    # ---------------- S2 硬值 lint ----------------
    section('S2 lint_tokens（页面硬值归因令牌）')
    code, out = run([PYTHON, SCRIPTS / 'lint_tokens.py', str(pages),
                     '--design-system', str(SKILL / 'assets' / 'design-system.json'),
                     '--style-blocks', str(sb)])
    record('页面样式零硬值', code == 0, 'exit 0（PASS）',
           'exit %d；%s' % (code, first_line_with(out, 'summary') or out.strip()[:120]),
           keep_out=out)

    # ---------------- S3 页面预检 + 命名检查 ----------------
    section('S3 build --check（目录模式 + --style-blocks 命名检查）')
    code, out = run([PYTHON, SCRIPTS / 'build.py', '--check', 'pages', '--style-blocks', str(sb)], cwd=proj)
    record('片段预检 + 命名检查通过', code == 0 and 'PASS' in out and 'naming ok' in out,
           'exit 0，PASS 且 naming ok', 'exit %d；%s' % (code, first_line_with(out, 'PASS') or first_line_with(out, 'FAIL')),
           keep_out=out)

    # ---------------- S4 回执（U1 / U2 final） ----------------
    section('S4 qa_receipt --make（U1 + U2 final 回执）')
    rt = SKILL / 'assets' / 'runtime-contract.json'
    u1 = qa / 'u1.json'
    u2 = qa / 'u2.json'
    code1, out1 = run([PYTHON, SCRIPTS / 'qa_receipt.py', '--make', '--station', 'U1',
                       '--kind', 'check', '--result', 'passed',
                       '--inputs', ','.join([str(start_doc), str(sel)]),
                       '--out', str(u1), '--note', 'e2e: 1.0 开工文档 + 选型回传'])
    record('U1 回执落盘', code1 == 0 and u1.is_file(), 'exit 0 且 qa/u1.json 存在',
           'exit %d；%s' % (code1, first_line_with(out1, 'receipt') or out1.strip()[:120]), keep_out=out1)
    u2_inputs = [str(start_doc),
                 str(pages / '工作台' / '接单列表.html'),
                 str(pages / '钱包' / '我的钱包.html'),
                 str(rt), str(sb)]
    code2, out2 = run([PYTHON, SCRIPTS / 'qa_receipt.py', '--make', '--station', 'U2',
                       '--kind', 'check', '--result', 'passed', '--phase', 'final',
                       '--inputs', ','.join(u2_inputs), '--out', str(u2),
                       '--note', 'e2e: U2 final（开工文档+片段+runtime-contract+风格块）'])
    record('U2 final 回执落盘', code2 == 0 and u2.is_file(), 'exit 0 且 qa/u2.json 存在',
           'exit %d；%s' % (code2, first_line_with(out2, 'receipt') or out2.strip()[:120]), keep_out=out2)

    # ---------------- S5 正式构建（SKILL.md U3 + 门禁） ----------------
    section('S5 build 正式构建（--style-blocks + --active-pack + U1/U2 回执门禁）')
    output_html = proj / 'build' / (e2e_fixture.PROJECT_TITLE + '.html')
    code, out = run([PYTHON, SCRIPTS / 'build.py',
                     '--pages', 'pages', '--title', e2e_fixture.PROJECT_TITLE,
                     '--start-doc', str(start_doc), '--style-blocks', str(sb),
                     '--active-pack', e2e_fixture.ACTIVE_PACK,
                     '--output', str(output_html),
                     '--u1-receipt', str(u1), '--u2-receipt', str(u2),
                     '--u3-report', str(qa / 'u3.json')], cwd=proj, timeout=600)
    ok = (code == 0 and output_html.is_file())
    record('正式构建产件', ok, 'exit 0 且 build/接单钱包工作台.html 存在',
           'exit %d；%s' % (code, first_line_with(out, 'Built') or first_line_with(out, 'FAIL') or out.strip()[:160]),
           keep_out=out)
    record('门禁链（lint/组件CSS/U1/U2 回执复核）通过', 'formal gate ok' in out,
           "输出含 'formal gate ok'", first_line_with(out, 'formal gate') or '未找到', keep_out=out)
    record('U3 回执落盘（产物字节 hash）', (qa / 'u3.json').is_file(), 'qa/u3.json 存在',
           str((qa / 'u3.json').is_file()), keep_out=out)
    record('风格卡截图回填（node+playwright）', ('pack-shots:' in out) or ('WARN pack-shots' in out),
           "输出含 'pack-shots:'（成功或降级告警）", first_line_with(out, 'pack-shots') or '未找到', keep_out=out)

    # ---------------- S6 运行时断言 ----------------
    section('S6 Playwright 运行时断言（切包/配色/跨族/卡片令牌行/组件面板/页面树）')
    code, out = run(['node', str(HERE / 'assert_runtime.cjs'), str(output_html)], cwd=proj, timeout=300)
    if os.environ.get('E2E_SHOW_RUNTIME'):
        print(out)
    record('运行时断言全绿', code == 0, 'assert_runtime exit 0',
           'exit %d；%s' % (code, first_line_with(out, 'summary') or out.strip()[:160]),
           keep_out=out)

    # ---------------- S7 站状态机 ----------------
    section('S7 state_check --mark U1 passed（下一站要点清单）')
    code, out = run([PYTHON, SCRIPTS / 'state_check.py', '--project-dir', str(proj),
                     '--mark', 'U1', 'passed', '--receipt', str(u1)], cwd=proj)
    brief = out
    need = ['NEXT U2', 'editor-conversion.md', 'AI 判族', '配色版', '同族变体']
    missing = [k for k in need if k not in brief]
    record('U1 标记 passed', code == 0 and 'recorded: U1 = passed' in out,
           "exit 0 且输出含 'recorded: U1 = passed'",
           'exit %d；%s' % (code, first_line_with(out, 'recorded') or first_line_with(out, 'REJECTED')),
           keep_out=out)
    record('下一站 U2 要点清单（判族/配色版/同族变体/完整代表页先行）', not missing,
           '输出含 ' + '、'.join(need), ('全部命中' if not missing else '缺: ' + '、'.join(missing)),
           keep_out=out)

    # ---------------- 反向实测 ----------------
    section('R1-R18 反向实测（每条独立坏数据）')
    rev = base / 'reverse'
    rev.mkdir(exist_ok=True)

    # R1 驼峰参数名
    def r1(scratch):
        p = mutated_style_blocks(scratch, lambda pk: None)
        sbd = load_json(p)
        tk = sbd['STYLE-PACK']['packs'][0]['tokens']
        tk['radiusMd'] = tk.pop('radius-md')
        write_json(p, sbd)
        return p
    reverse_case(rev, 1, '驼峰参数名 radiusMd', r1,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-PACK-KEY')

    # R2 覆盖样式坏声明
    def r2(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['l2Overrides'] = [{'selector': '.kx-card', 'props': ':ok:#00A2C7'}]
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 2, '覆盖样式坏声明 :ok:#00A2C7', r2,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-L2-DECL')

    # R3 组件引用未知变量
    def r3(scratch):
        def mut(_pk):
            pass
        p = mutated_style_blocks(scratch, mut)
        sbd = load_json(p)
        sbd['COMPONENT-PACK']['components'][0]['html'] += '<span style="color:var(--sp-surface)">异常探针</span>'
        write_json(p, sbd)
        return p
    reverse_case(rev, 3, '组件引用未知变量 --sp-surface', r3,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-COMP-UNKNOWN-VAR')

    # R4 覆盖样式选择器 :root
    def r4(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['l2Overrides'] = [{'selector': ':root', 'props': 'background:var(--bg)'}]
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 4, '覆盖样式选择器 :root', r4,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-L2-SELECTOR')

    # R5 锁定键在包内缺失
    def r5(scratch):
        shutil.copy2(sel, scratch / 'selection-result.json')

        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['tokens'].pop('shadow-md')
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 5, '锁定键 shadow-md 在包 tokens 缺失', r5,
                 lambda s: vb_runner(s / 'style-blocks.json', s / 'selection-result.json')(s),
                 1, 'E-LOCK-KEY-MISSING')

    # R6 只有一套配色（提醒）
    def r6(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-meihong':
                pk['palettes'] = pk['palettes'][:1]
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 6, '只有一套配色', r6,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 0, 'W-PACK-PALETTES')

    # R7 族单成员（提醒）
    def r7(scratch):
        p = mutated_style_blocks(scratch, lambda pk: None)
        sbd = load_json(p)
        sbd['STYLE-REGISTRY']['families'][1]['members'] = ['pack-dianzi']
        write_json(p, sbd)
        return p
    reverse_case(rev, 7, '族只有一个成员', r7,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 0, 'W-FAMILY-SOLO')

    # R8 页面文件夹英文名
    def r8(scratch):
        fdir = scratch / 'pages_en' / 'workbench'
        fdir.mkdir(parents=True)
        (fdir / '接单列表.html').write_text(e2e_fixture.orders_fragment(), encoding='utf-8')
    def r8_run(scratch):
        return run([PYTHON, SCRIPTS / 'build.py', '--check', str(scratch / 'pages_en')])
    reverse_case(rev, 8, '页面文件夹英文（workbench）', r8, r8_run, 1, 'E-NAMING-GROUP')

    # R9 页头描述泄漏内部编号
    def r9(scratch):
        frag = e2e_fixture.wallet_fragment(note_override='商家资产余额与提现入口（骨架 db-a）')
        fdir = scratch / 'pages_leak' / '钱包'
        fdir.mkdir(parents=True)
        (fdir / '我的钱包.html').write_text(frag, encoding='utf-8')
    def r9_run(scratch):
        return run([PYTHON, SCRIPTS / 'build.py', '--check', str(scratch / 'pages_leak'),
                    '--style-blocks', str(sb)])
    reverse_case(rev, 9, '页头描述泄漏内部编号 db-a', r9, r9_run, 1, 'E-NAMING-ID-LEAK')

    # R10 density 写成 airy
    def r10(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-dianzi':
                pk['tokens']['density'] = 'airy'
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 10, 'density 写成 airy', r10,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-PACK-KEY-VALUE')

    # R11 选型结果缺最小集（skeletonTokens 只留 5 个键，缺 E-LOCK-MINIMUM 要求的全量 minimum）
    def r11(scratch):
        shutil.copy2(sb, scratch / 'style-blocks.json')
        sel_bad = e2e_fixture.selection_result()
        keep = ['primary', 'radius-md', 'space-2', 'weight-head', 'shadow-md']
        for grp in sel_bad['audienceGroups']:
            for item in grp['selected']:
                item['skeletonTokens'] = {k: v for k, v in item['skeletonTokens'].items() if k in keep}
        write_json(scratch / 'selection-result.json', sel_bad)
    reverse_case(rev, 11, '选型结果缺最小集', r11,
                 lambda s: vb_runner(s / 'style-blocks.json', s / 'selection-result.json')(s),
                 1, 'E-LOCK-MINIMUM')

    # R12 风格包缺最小集（从包 tokens 删 2 个 minimum 键；不带 --lock，聚焦单规则）
    def r12(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['tokens'].pop('shadow-md')
                pk['tokens'].pop('motion-duration-base')
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 12, '风格包缺最小集', r12,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-PACK-MINIMUM')

    # R13 参数值含注入字符 }
    def r13(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-dianzi':
                pk['tokens']['radius-md'] = '12px}'
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 13, '参数值含 }', r13,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-PACK-VALUE-CHARS')

    # R14 packId 含非法字符（同步改 members 引用，保证只有这一条错）
    def r14(scratch):
        p = mutated_style_blocks(scratch, lambda pk: None)
        sbd = load_json(p)
        for pk in sbd['STYLE-PACK']['packs']:
            if pk['packId'] == 'pack-meihong':
                pk['packId'] = 'pack-meihong×'
        for fam in sbd['STYLE-REGISTRY']['families']:
            fam['members'] = ['pack-meihong×' if m == 'pack-meihong' else m for m in fam['members']]
        write_json(p, sbd)
        return p
    reverse_case(rev, 14, 'packId 含非法字符（×）', r14,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-PACK-ID')

    # R15 覆盖样式选择器含注入字符 {
    def r15(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['l2Overrides'] = [{'selector': '.kx-card{', 'props': 'border-radius:var(--sp-radius-md)'}]
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 15, '覆盖样式选择器含 {', r15,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-L2-SELECTOR-CHARS')

    # R16 覆盖样式属性值含危险字符 }（E-L2-DECL 危险字符分支）
    def r16(scratch):
        def mut(pk):
            if pk['packId'] == 'pack-chenlan':
                pk['l2Overrides'] = [{'selector': '.kx-card',
                                      'props': 'border-radius:var(--sp-radius-md)}'}]
        return mutated_style_blocks(scratch, mut)
    reverse_case(rev, 16, '覆盖样式属性值含 }', r16,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 1, 'E-L2-DECL')

    # R17 组件正文写「订单 #1024」→ 正向豁免（新口径只查样式上下文，正文 #单号 不查）
    def r17(scratch):
        def mut(_pk):
            pass
        p = mutated_style_blocks(scratch, mut)
        sbd = load_json(p)
        for c in sbd['COMPONENT-PACK']['components']:
            if c['compId'] == 'cp-list-row':
                c['html'] = c['html'].replace('订单 1024', '订单 #1024')
        write_json(p, sbd)
        return p
    reverse_case(rev, 17, '组件正文「订单 #1024」不应报错', r17,
                 lambda s: vb_runner(s / 'style-blocks.json')(s), 0, forbid='E-COMP-RAW-COLOR')

    # R18 页面引用 --style-line → lint 报未知变量并提示改用 --line
    def r18(scratch):
        frag = e2e_fixture.wallet_fragment().replace(
            'var(--sp-border-width,1px) solid var(--line)', 'var(--style-line) solid var(--line)', 1)
        fdir = scratch / 'pages_stylevar' / '钱包'
        fdir.mkdir(parents=True)
        (fdir / '我的钱包.html').write_text(frag, encoding='utf-8')

    def r18_run(scratch):
        return run([PYTHON, SCRIPTS / 'lint_tokens.py', str(scratch / 'pages_stylevar'),
                    '--design-system', str(SKILL / 'assets' / 'design-system.json'),
                    '--style-blocks', str(sb)])
    reverse_case(rev, 18, '页面引用 --style-line → 提示改用 --line', r18, r18_run,
                 1, 'E-TOKEN-UNKNOWN-VAR')

    # ---------------- 汇总与清理 ----------------
    total = len(RESULTS)
    bad = [r for r in RESULTS if not r['ok']]
    print('\n===== 汇总 =====')
    for r in RESULTS:
        print('%s  %s · %s' % ('PASS' if r['ok'] else 'FAIL', r['section'], r['name']))
    print('\n%d check(s): %d passed / %d failed — %s（用时 %.1fs）'
          % (total, total - len(bad), len(bad), 'PASS' if not bad else 'FAIL', time.time() - t0))
    if bad:
        print('保留运行目录供排查: %s' % base)
        return 1
    shutil.rmtree(base, ignore_errors=True)
    print('已清理运行目录: %s' % base)
    return 0


if __name__ == '__main__':
    sys.exit(main())
