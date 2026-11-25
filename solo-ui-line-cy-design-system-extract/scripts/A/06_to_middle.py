"""
scripts/A/06_to_middle.py — A-06 提取（**降级为 B-1**）

复用：scripts/B/parse_html.py（B-1 静态解析）
不做自创逻辑 —— 高保真 HTML 走 B-1 流程，产出 middle.json

输入：out/hifi/{page}/index.html（多张）
产出：out/middle.json
"""
import sys
import subprocess
from pathlib import Path

# B-1 脚本路径
PARSE_HTML = Path(__file__).parent.parent / "B" / "parse_html.py"


def main():
    if len(sys.argv) < 2:
        print("用法: python 06_to_middle.py <hifi_dir> [输出middle.json]", file=sys.stderr)
        sys.exit(1)
    hifi_dir = Path(sys.argv[1])
    out_middle = sys.argv[2] if len(sys.argv) > 2 else "out/middle.json"

    pages = sorted([d for d in hifi_dir.iterdir() if d.is_dir()])
    print(f"[INFO] {len(pages)} 张高保真 HTML 待走 B-1 解析")
    print(f"[INFO] 复用 B/parse_html.py（不在本脚本中自创解析逻辑）")

    for p in pages:
        html_file = p / "index.html"
        if not html_file.exists():
            print(f"[WARN] {html_file} 不存在，跳过")
            continue
        r = subprocess.run(
            [sys.executable, str(PARSE_HTML), str(html_file), str(out_middle)],
            capture_output=True, text=True, encoding="utf-8",
        )
        print(f"  - {p.name}: exit {r.returncode}")
        if r.returncode != 0:
            print(f"    stderr: {r.stderr[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
