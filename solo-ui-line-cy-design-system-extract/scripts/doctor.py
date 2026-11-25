# -*- coding: utf-8 -*-
"""
scripts/doctor.py — 第 ⓪ 步环境体检（激活后、站① 参数锁定前执行）

用法：
    python scripts/doctor.py          # 快检：python 版本 + bs4 + playwright import
    python scripts/doctor.py --full   # --full 真实启动 chromium（验证 playwright 浏览器可用）
    python scripts/doctor.py --fix    # 自动执行安装命令（pip install），装完自动复跑

退出码：0 = READY 可开工；1 = 有失败（读末行 JSON 报告字段处置）。
规则在代码里，报告给结论与修复命令——不许执行模型自己数失败项
（image-to-code-skills doctor 同款纪律）。

报告字段（末行 JSON）：
    ready          true/false——快检口径：blocking_fail 为空即 true
    blocking_fail  阻塞所有提取路径的缺失项（bs4——B-1 是 6 路共同终点）
    url_only_fail  仅阻塞 URL 提取的缺失项（playwright/chromium）——
                   非 URL 任务可带项前进，路由到 B-2 前必须补齐（用户定夺）
    fix_commands   对应的修复命令（禁执行模型自动安装——装依赖是环境变更，
                   须用户点头后由 agent 跑 --fix 或逐条执行）

依赖清单权威来源 = requirements.txt（本脚本是它的运行时执行者）。
"""
import json
import subprocess
import sys

MIN_PY = (3, 9)


def py_ok() -> bool:
    return sys.version_info >= MIN_PY


def import_ok(module: str) -> tuple[bool, str]:
    try:
        __import__(module)
        return True, ""
    except Exception as e:
        return False, str(e)[:80]


def chromium_ok(full: bool) -> tuple[bool, str]:
    if not full:
        return True, "skipped（未 --full，不真实启动）"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True, ""
    except Exception as e:
        return False, str(e)[:120]


def collect(full: bool) -> dict:
    checks, blocking, url_only, fixes = [], [], [], []

    ok = py_ok()
    checks.append(("python>=3.9", ok, f"当前 {sys.version_info.major}.{sys.version_info.minor}"))
    if not ok:
        blocking.append("python>=3.9")
        fixes.append("升级 Python 至 3.9+")

    ok, err = import_ok("bs4")
    checks.append(("beautifulsoup4（B-1 解析必需）", ok, err))
    if not ok:
        blocking.append("beautifulsoup4")
        fixes.append("pip install beautifulsoup4")

    ok, err = import_ok("playwright")
    checks.append(("playwright（仅 B-2 URL 抓取需要）", ok, err))
    if not ok:
        url_only.append("playwright")
        fixes.append("pip install playwright && playwright install chromium")

    cok, cerr = chromium_ok(full)
    label = "chromium 真实启动" if full else "chromium（未检，--full 才启动）"
    checks.append((label, cok, cerr))
    if not cok:
        url_only.append("chromium")
        if "playwright install" not in " ".join(fixes):
            fixes.append("playwright install chromium")

    return {
        "ready": not blocking,
        "blocking_fail": blocking,
        "url_only_fail": url_only,
        "fix_commands": fixes,
        "checks": [{"item": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }


def apply_fixes() -> int:
    cmds = [
        [sys.executable, "-m", "pip", "install", "beautifulsoup4"],
        [sys.executable, "-m", "pip", "install", "playwright"],
        [sys.executable, "-m", "playwright", "install", "chromium"],
    ]
    for c in cmds:
        print(f"[FIX] {' '.join(c)}")
        r = subprocess.run(c)
        if r.returncode != 0:
            print(f"[FAIL] 修复命令失败（exit {r.returncode}）——原样上报，禁自裁", file=sys.stderr)
            return 1
    return 0


def main() -> int:
    full = "--full" in sys.argv
    if "--fix" in sys.argv:
        if apply_fixes() != 0:
            return 1
        print("[INFO] 修复完成，自动复跑体检——\n")

    report = collect(full)
    for c in report["checks"]:
        print(f"[{'OK' if c['ok'] else 'FAIL'}] {c['item']}  {c['detail']}")
    print("\n" + json.dumps({k: report[k] for k in ("ready", "blocking_fail", "url_only_fail", "fix_commands")},
                            ensure_ascii=False))
    if not report["ready"]:
        return 1
    # --full 的目的就是验证 URL 链路：此时 url_only 缺失也应非零（快检模式不判——它不查浏览器）
    return 1 if (full and report["url_only_fail"]) else 0


if __name__ == "__main__":
    sys.exit(main())
