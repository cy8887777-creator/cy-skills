"""
scripts/A/01_inventory.py — A-01 盘点（**真接 intake.py 真实接口**）

复用：design-pack-pipeline/scripts/intake.py
不做自创逻辑 —— intake.py 真实接口：
    intake.py <fig_dir> <project_dir> [--probe] [--project-name]
    产出：<project_dir>/pipeline/pages.manifest.json（键名 = images）
    键名确认（实测 intake.py L130-138）：{"project","source_dir","images":[]}
"""
import subprocess
import sys
from pathlib import Path

REUSED = Path(__file__).parent / "_reused"
INTAKE = REUSED / "intake.py"


def main():
    if len(sys.argv) < 3:
        print("用法: python 01_inventory.py <图包目录> <工程目录> [--probe]", file=sys.stderr)
        sys.exit(1)
    fig_dir = Path(sys.argv[1])
    proj_dir = Path(sys.argv[2])
    probe = "--probe" in sys.argv

    if not fig_dir.is_dir():
        print(f"[FAIL] 图包目录不存在: {fig_dir}", file=sys.stderr)
        sys.exit(2)

    # 调真接口
    cmd = [sys.executable, str(INTAKE), str(fig_dir), str(proj_dir)]
    if probe:
        cmd.append("--probe")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)

    # 真产出位置
    manifest = proj_dir / "pipeline" / "pages.manifest.json"
    if manifest.exists() and not probe:
        print(f"[OK] manifest 落地: {manifest}")
    elif probe:
        print("[OK] probe 完成（无落盘）")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
