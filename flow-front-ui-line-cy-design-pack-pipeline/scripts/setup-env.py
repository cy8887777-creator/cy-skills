#!/usr/bin/env python3
"""setup-env — 管线环境一键检测 + 最小安装（幂等，已装跳过）。

四步逐项报告（失败分开列，不互相阻塞）：
  [1/4] pip 依赖：pillow / playwright（缺 → 自动 pip install）
  [2/4] 浏览器：msedge 通道真实 launch 验证（失败 → 尝试
        playwright install chromium；都不行列手动命令）
  [3/4] 抠图模型：技能 models/ 或 I2C_BG_MODEL 下 isnet/u2net
        （缺失 → 默认只列下载指引；--download-models 才自动下载
        ~170MB——大件不静默装，用户定向决定）
  [4/4] 工程依赖：<工程>/node_modules（缺失 → 列 npm install 提示；
        --npm 才自动执行）

退出码：0 全就绪；1 有缺失项（逐项列明）。
L1 模式（未装单页技能）可 --skip-models 跳过第 3 步。

用法：python setup-env.py [--project-dir <工程>] [--models-dir <目录>]
                          [--download-models] [--npm] [--skip-models]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# rembg 固定资产名 + latest 泛链（tag 无关，资产名长期稳定）
MODEL_ASSETS = {
    "isnet-general-use.onnx":
        "https://github.com/danielgatis/rembg/releases/latest/download/isnet-general-use.onnx",
    "u2net.onnx":
        "https://github.com/danielgatis/rembg/releases/latest/download/u2net.onnx",
}


def sh(cmd: list[str], cwd: str | None = None) -> bool:
    try:
        # subprocess.run 阻塞返回 CompletedProcess——取 returncode，
        # 没有 wait()（2026-10-07 修复：原 .wait() 直接 AttributeError）
        return subprocess.run(cmd, cwd=cwd).returncode == 0
    except FileNotFoundError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=None,
                    help="工程目录（检测 node_modules）")
    ap.add_argument("--models-dir", default=None,
                    help="模型目录（默认 技能/models/ 或 I2C_BG_MODEL）")
    ap.add_argument("--download-models", action="store_true",
                    help="缺失模型自动下载（~170MB）")
    ap.add_argument("--npm", action="store_true",
                    help="工程依赖缺失时自动 npm install")
    ap.add_argument("--skip-models", action="store_true",
                    help="L1 模式：跳过模型检测")
    args = ap.parse_args()

    problems: list[str] = []

    # [1/4] pip
    pip_map = {"PIL": "pillow", "playwright": "playwright"}
    missing = [m for m in pip_map if importlib.util.find_spec(m) is None]
    if missing:
        print(f"[1/4] pip 缺失 {missing} → 自动安装...")
        pkgs = [pip_map[m] for m in missing]
        if not sh([sys.executable, "-m", "pip", "install", *pkgs]):
            problems.append(f"pip 安装失败（手动：pip install {' '.join(pkgs)}）")
    else:
        print("[1/4] pip 依赖 ✓")

    # [2/4] 浏览器（msedge 优先——用户已装 Edge 就不下 chromium）
    ok_edge = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="msedge", headless=True)
            b.close()
        ok_edge = True
    except Exception:
        pass
    if ok_edge:
        print("[2/4] 浏览器 ✓（msedge 通道，跳过 chromium 下载）")
    else:
        print("[2/4] msedge 不可用 → playwright install chromium ...")
        if not sh([sys.executable, "-m", "playwright", "install", "chromium"]):
            problems.append("浏览器安装失败（手动：python -m playwright install chromium）")

    # [3/4] 抠图模型
    if args.skip_models:
        print("[3/4] 模型：--skip-models 跳过（L1 模式）")
    else:
        models_dir = Path(args.models_dir
                          or Path(__file__).resolve().parent.parent / "models")

        # 候选探测（与单页技能 model_candidates 同源语义）：
        # I2C_BG_MODEL 可指向 onnx 文件或目录，I2C_MODELS_DIR 指目录。
        # 文件形态必须**文件名匹配**——指向 isnet.onnx 时不得把它同时
        # 算作 u2net（四轮评审：原实现同一文件命中两个模型名 → 假 READY）
        def _model_exists(name: str) -> bool:
            cands = []
            env_bg = os.environ.get("I2C_BG_MODEL")
            if env_bg:
                p = Path(env_bg)
                if p.is_file():
                    if p.name == name:
                        cands.append(p)
                else:
                    cands.append(p / name)
            env_dir = os.environ.get("I2C_MODELS_DIR")
            if env_dir:
                cands.append(Path(env_dir) / name)
            cands.append(models_dir / name)
            return any(c.is_file() for c in cands)

        have = {n: _model_exists(n) for n in MODEL_ASSETS}
        if any(have.values()):
            # 与单页 doctor 对齐（八轮评审）：isnet/u2net **任一存在**
            # 即可用（isnet 优先 u2net 兜底）——仅装 isnet 的可工作
            # 环境不得被前置步骤挡住
            present = [n for n, ok in have.items() if ok]
            print(f"[3/4] 模型 ✓（{'+'.join(present)}；"
                  "任一模型即可）")
        elif args.download_models:
            models_dir.mkdir(parents=True, exist_ok=True)
            for n, url in MODEL_ASSETS.items():
                if have[n]:
                    continue
                print(f"  下载 {n} → {models_dir}/ ...")
                try:
                    urllib.request.urlretrieve(url, models_dir / n)
                except Exception as e:
                    problems.append(f"模型 {n} 下载失败: {e}（手动：{url}）")
        else:
            problems.append(
                "模型均缺失 —— isnet/u2net 任一存在即可：手动下载 "
                f"{MODEL_ASSETS['isnet-general-use.onnx']} → "
                f"{models_dir}/isnet-general-use.onnx（推荐 170MB）或 "
                f"u2net.onnx（较小）；或 --download-models 自动下；"
                f"或 --skip-models 走 L1")

    # [4/4] 工程依赖
    if args.project_dir:
        nm = Path(args.project_dir) / "node_modules"
        if nm.is_dir():
            print("[4/4] 工程依赖 ✓（node_modules 存在）")
        elif args.npm:
            print("[4/4] npm install ...")
            if not sh(["cmd", "/c", "npm", "install"], cwd=args.project_dir):
                problems.append(f"npm install 失败（手动：cd {args.project_dir} && npm install）")
        else:
            problems.append(f"工程依赖缺失（手动：cd {args.project_dir} && npm install，或 --npm 自动）")
    else:
        print("[4/4] 工程依赖：未给 --project-dir 跳过（每工程各自 npm install）")

    if problems:
        print("\n缺失项（逐项）:")
        for p in problems:
            print("  -", p)
        return 1
    print("\n环境 READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
