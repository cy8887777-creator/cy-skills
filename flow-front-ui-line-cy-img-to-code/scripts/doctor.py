# -*- coding: utf-8 -*-
"""Environment doctor for the image-to-code-skills skill.

Run BEFORE any generation work. Checks every hard dependency of the
skill's deterministic pipeline and, for anything missing, prints the
exact install/download command — or performs it with --fix.

Checks:
  1. Python >= 3.10
  2. pillow / numpy / onnxruntime importable
  3. playwright importable (+ optional real browser launch with --full)
  4. u2net.onnx present and plausibly sized

Exit code 0 = all green (safe to proceed), 1 = something missing.

Also generates a vision test card (--make-vision-test PATH): the agent
must Read that image and describe it to prove the current model is
multimodal before doing any box_2d labeling work.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# GBK consoles (default on zh-CN Windows) choke on non-ASCII stdout.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

U2NET_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
)
ISNET_URL = (
    "https://github.com/danielgatis/rembg/releases/download/"
    "v0.0.0/isnet-general-use.onnx"
)
MODEL_MIN_BYTES = 100 * 1024 * 1024  # nominal ~170MB; guard against stubs

SKILL_DIR = Path(__file__).resolve().parent.parent

# Model file lookup order: env override -> alongside the skill ->
# the screenshot-to-code project checkout.
def model_candidates(filename: str) -> list[Path]:
    dirs = []
    env_dir = os.environ.get("I2C_MODELS_DIR")
    if env_dir:
        dirs.append(Path(env_dir))
    dirs.append(SKILL_DIR / "models")
    env_backend = os.environ.get("I2C_S2C_BACKEND")
    if env_backend:
        dirs.append(Path(env_backend) / "models")
    dirs.append(Path(r"D:\screenshot-to-code\backend\models"))
    seen: set[Path] = set()
    out = []
    for d in dirs:
        p = d / filename
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def find_model_file(filename: str) -> Path | None:
    for p in model_candidates(filename):
        if p.is_file() and p.stat().st_size >= MODEL_MIN_BYTES:
            return p
    return None


CHECKS: list[dict] = []


def record(name: str, ok: bool, detail: str, fix: str | None = None,
           fixable: bool = False) -> None:
    CHECKS.append(
        {"name": name, "ok": ok, "detail": detail, "fix": fix,
         "fixable": fixable}
    )
    mark = "[OK]  " if ok else "[MISS]"
    print(f"{mark} {name}: {detail}")


def check_python() -> None:
    v = sys.version_info
    ok = v >= (3, 10)
    record("python", ok, f"{v.major}.{v.minor}.{v.micro}",
           fix="Install Python 3.10+ from python.org")


def _import_check(module: str, pip_name: str, why: str) -> None:
    try:
        __import__(module)
        record(f"dep:{module}", True, "importable")
    except Exception as exc:
        record(
            f"dep:{module}", False, f"missing ({exc.__class__.__name__})",
            fix=f"{sys.executable} -m pip install {pip_name}   # {why}",
            fixable=True,
        )


def check_deps() -> None:
    _import_check("PIL", "pillow", "image decode / crop")
    _import_check("numpy", "numpy", "u2net tensor math")
    _import_check("onnxruntime", "onnxruntime", "local background removal")
    _import_check("playwright", "playwright", "page screenshot + checks")
    _import_check("cv2", "opencv-python-headless",
                  "over_photo text erase (inpaint)")


def check_browser(full: bool) -> None:
    if not full:
        # Hard fail, not a pass-with-note: verify_page.py cannot run
        # without a headless browser, and "READY without launching"
        # was a false green the agents trusted (contract: script gates
        # must be conservative — field review 2026-09-30).
        record(
            "browser", False,
            "not launched — rerun with --full (browser is a hard "
            "dependency of verify_page.py)",
            fix=(f"{sys.executable} "
                 f'"{Path(__file__).resolve()}" --full'),
            fixable=True,
        )
        return
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(channel="msedge", headless=True)
                channel = "msedge"
            except Exception:
                browser = pw.chromium.launch(headless=True)
                channel = "chromium"
            browser.close()
        record("browser", True, f"launchable via {channel}")
    except Exception as exc:
        record(
            "browser", False, f"launch failed: {exc}",
            fix=(
                f"{sys.executable} -m playwright install chromium   "
                f"# or rely on system Edge"
            ),
            fixable=True,
        )


def check_bg_models(tier: str = "fidelity") -> None:
    isnet = find_model_file("isnet-general-use.onnx")
    u2net = find_model_file("u2net.onnx")
    if isnet is not None:
        size_mb = isnet.stat().st_size / 1024 / 1024
        note = f"; u2net fallback {'present' if u2net else 'MISSING'}"
        record("bg-model", True,
               f"isnet-general-use active: {isnet} ({size_mb:.0f}MB){note}")
        return
    if u2net is not None:
        size_mb = u2net.stat().st_size / 1024 / 1024
        record(
            "bg-model", True,
            f"u2net active (isnet not installed — sharper edges, "
            f"recommended): {u2net} ({size_mb:.0f}MB)",
        )
        return
    first = model_candidates("isnet-general-use.onnx")[0]
    if tier == "fast":
        # 档位分档（2026-10-07）：快速档不抠图（--no-alpha），模型缺失
        # 不阻塞 READY——否则快速档用户被逼下载 170MB 或卡在铁律
        # "退出码 1 → fix → 两次不 READY 则停"
        record("bg-model", True,
               "no model found — OK for 快速档 (--no-alpha); "
               "fidelity tier requires it")
        return
    record(
        "bg-model", False,
        f"no model found (looked in {first.parent})",
        fix=(
            f'curl -L -o "{first}" {ISNET_URL}   '
            f"# 170MB recommended, or u2net: {U2NET_URL} ; "
            f"or run this script with --fix"
        ),
        fixable=True,
    )


def apply_fixes() -> None:
    to_install = [
        c["fix"].split("#")[0].strip()
        for c in CHECKS
        if not c["ok"] and c["fixable"] and c["name"].startswith("dep:")
    ]
    browser_fix = next(
        (c for c in CHECKS if not c["ok"] and c["fixable"]
         and c["name"] == "browser"), None,
    )
    if to_install:
        print(f"\n== Installing {len(to_install)} python package(s) ==")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *to_install],
            check=False,
        )
    if browser_fix is not None:
        print("\n== Installing playwright chromium ==")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
        )
    bg_check = next(
        (c for c in CHECKS if not c["ok"] and c["name"] == "bg-model"), None,
    )
    if bg_check is not None:
        target = model_candidates("isnet-general-use.onnx")[0]
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n== Downloading isnet-general-use.onnx (170MB) -> {target} ==")
        try:
            import urllib.request

            urllib.request.urlretrieve(ISNET_URL, target)
            print("download done")
        except Exception as exc:
            print(f"download failed: {exc}\n"
                  f"manual: curl -L -o \"{target}\" {ISNET_URL} "
                  f"(or u2net: {U2NET_URL})")


def make_vision_test(out_path: Path) -> None:
    """Draw a card with shapes, colors and digits for multimodality proof."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (640, 320), "#F8FAFC")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 180, 160], fill="#2563EB")
    d.ellipse([240, 40, 380, 160], fill="#DC2626")
    d.polygon(
        [(460, 160), (540, 40), (620, 160)], fill="#CA8A04"
    )
    d.rectangle([40, 200, 600, 280], fill="#0F172A")
    d.text((200, 225), "7 3 4 9", fill="#FFFFFF")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"vision test card written: {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true",
                    help="install missing packages / download model")
    ap.add_argument("--full", action="store_true",
                    help="really launch a browser (slower, definitive)")
    ap.add_argument("--tier", choices=("fidelity", "fast"),
                    default="fidelity",
                    help="fidelity: bg-model required; fast: model "
                         "missing is OK (--no-alpha path)")
    ap.add_argument("--make-vision-test", metavar="PATH",
                    help="write a vision test card image and exit")
    args = ap.parse_args()

    if args.make_vision_test:
        make_vision_test(Path(args.make_vision_test))
        return 0

    print("== image-to-code-skills environment doctor ==\n")
    check_python()
    check_deps()
    check_browser(args.full)
    check_bg_models(args.tier)

    if args.fix:
        apply_fixes()
        CHECKS.clear()
        print("\n== re-check after fix ==\n")
        check_python()
        check_deps()
        check_browser(args.full)
        check_bg_models(args.tier)

    failed = [c for c in CHECKS if not c["ok"]]
    # 模型项例外标记（2026-10-07 第五轮评审）：失败项全部为抠图模型
    # 时 SKILL 第 0 步不停机——档位在第 1 步才确认，缺模型机器必须
    # 能活着走到"选快速档"那一步。规则写在代码里，不让模型数失败项。
    model_only_fail = bool(failed) and all(
        c["name"] == "bg-model" for c in failed)
    report = {
        "ok": not failed,
        "model_only_fail": model_only_fail,
        "checks": [
            {"name": c["name"], "ok": c["ok"], "detail": c["detail"]}
            for c in CHECKS
        ],
        "fix_commands": [c["fix"] for c in failed if c["fix"]],
    }
    print("\n== report ==")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        if model_only_fail:
            print("\nNOT READY (model-only fail) — safe to continue to "
                  "tier confirmation (step 1): 快速档 works without "
                  "models, 保真档 needs the fix commands first.")
        else:
            print("\nNOT READY — apply the fix commands above, then re-run.")
    else:
        print("\nREADY — environment is good to go.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
