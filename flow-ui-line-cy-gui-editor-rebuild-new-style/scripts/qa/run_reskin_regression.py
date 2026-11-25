# -*- coding: utf-8 -*-
"""run_reskin_regression.py — 换风回装一键回归（单测入口）

对给定回装产物依次跑全部换风回归，输出 PASS/FAIL 汇总（exit 0=全过 / 1=有 FAIL / 2=环境不可用）：
  1. acc_reskin.mjs   — 七项核心 + 页数不对称专项（树整套换/隔离/两域真点/重映射/往返/不对称）
  2. acc_covers.mjs   — 封面供给链（面板真图×卡数/零色板条/切卡回归）

用法：
  python run_reskin_regression.py <产物.html> [--out-dir <截图目录>] [--skip-covers] [--script <额外.mjs>]…
  产物 = 回装后的 index.html（双风格卡）；卡名/页 id 从产物解析，不写死项目。
输出：逐行转发子脚本 stdout（[PASS]/[FAIL]/[INFO]），末尾汇总表。

依赖：node（子脚本内部自带 playwright 三级探测：本地 → PLAYWRIGHT_MODULE_PATH 环境变量 → npm 全局，
与 conversion.md「客户环境降级」同口径；本 runner 不直接依赖 playwright）。
运行方式：常规 `python 路径/run_reskin_regression.py` 即可（禁 python -I 不影响本文件——本文件零兄弟模块 import）。
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PASS_RE = re.compile(r'^\[PASS\]')
FAIL_RE = re.compile(r'^\[FAIL\]')
INFO_RE = re.compile(r'^\[INFO\]')
SUMMARY_RE = re.compile(r'^SUMMARY ')


def run_one(script: Path, product: str, out_dir: str, extra_args):
    """跑单个 .mjs 回归脚本，返回 (exit_code, pass_lines, fail_lines, info_lines)。"""
    pass_lines, fail_lines, info_lines = [], [], []
    cmd = ['node', str(script), product, '--out-dir', out_dir] + extra_args
    t0 = time.time()
    print('\n===== %s =====' % script.name)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
        out = (proc.stdout or '') + (proc.stderr or '')
    except FileNotFoundError:
        print('[FAIL] node 不可用——回归需要 node ≥18 在 PATH')
        return 2, [], ['node 不可用'], []
    except subprocess.TimeoutExpired:
        print('[FAIL] %s 超时（600s）' % script.name)
        return 1, [], ['超时 600s'], []
    for line in out.splitlines():
        print(line)
        if PASS_RE.match(line):
            pass_lines.append(line)
        elif FAIL_RE.match(line):
            fail_lines.append(line)
        elif INFO_RE.match(line) or SUMMARY_RE.match(line):
            info_lines.append(line)
    dur = time.time() - t0
    print('----- %s 退出码=%d 用时=%.1fs -----' % (script.name, proc.returncode, dur))
    return proc.returncode, pass_lines, fail_lines, info_lines


def main():
    ap = argparse.ArgumentParser(description='换风回装一键回归（单测入口）')
    ap.add_argument('product', help='回装产物 index.html 路径')
    ap.add_argument('--out-dir', default=None, help='截图/证据输出目录（缺省=产物同目录 qa-shots/）')
    ap.add_argument('--skip-covers', action='store_true', help='跳过封面回归（只跑核心七项）')
    ap.add_argument('--script', action='append', default=[], dest='extra_scripts',
                    help='追加回归脚本（.mjs，吃同样参数；可多次）')
    a = ap.parse_args()

    product = str(Path(a.product).resolve())
    if not Path(product).is_file():
        print('[FAIL] 产物不存在: %s' % product)
        return 2
    out_dir = a.out_dir or str(Path(product).parent / 'qa-shots')

    scripts = [HERE / 'acc_reskin.mjs', HERE / 'acc_covers.mjs']
    if a.skip_covers:
        scripts = scripts[:1]
    for s in a.extra_scripts:
        scripts.append(Path(s).resolve())
    missing = [s.name for s in scripts if not s.is_file()]
    if missing:
        print('[FAIL] 回归脚本缺失: %s（应与本 runner 同在 scripts/qa/）' % ','.join(missing))
        return 2

    total_pass, total_fail, env_fail = [], [], False
    for s in scripts:
        code, p, f, _i = run_one(s, product, out_dir, [])
        if code == 2:
            env_fail = True
        total_pass += p
        total_fail += f

    print('\n================ 换风回归汇总 ================')
    for line in total_pass:
        print('  ' + line)
    for line in total_fail:
        print('  ' + line)
    verdict = 'ENV-UNAVAILABLE' if env_fail else ('FAIL' if total_fail else 'PASS')
    print('结果: %s  （PASS %d / FAIL %d；产物=%s）' % (verdict, len(total_pass), len(total_fail), product))
    print('证据目录: %s' % out_dir)
    if env_fail:
        print('环境不可用（node/playwright 落空）——按 conversion.md「客户环境降级」在交付说明注明，禁静默跳过')
    return 2 if env_fail else (1 if total_fail else 0)


if __name__ == '__main__':
    sys.exit(main())
