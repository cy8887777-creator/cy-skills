"""
scripts/core/run_pipeline.py — 站④一键管线（v4.0）

用法：
  python run_pipeline.py <out目录> [assets源目录]              ← 初稿全链（渲染+形态+派生+字体+自检）
  python run_pipeline.py <out目录> --derive-only               ← 定案后重派生（json+md+字体+自检；不动 HTML）

执行序：
  初稿全链:   gen_html → gen_components → gen_assets → gen_layouts → dual_scale → html_to_json → html_to_md → fetch_fonts → self_check
  --derive-only: html_to_json → html_to_md → fetch_fonts → self_check
  （dual_scale 双标折算必须先于派生——顺序禁反，否则 json/md 口径错、三构造不自洽）

任何一步非零退出 → 立即停止并报告（管线纪律：不跳步、不带病下行）。
agent 的语义活在两条命令之间：补全定案 HTML（占位组填值/语义名/迷你页拼装）。
"""
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent


def run(desc, cmd):
    print("\n=== %s ===" % desc)
    r = subprocess.run([sys.executable] + cmd)
    if r.returncode != 0:
        print("\n[管线停止] %s 失败（exit %d）——按输出排查后重跑" % (desc, r.returncode),
              file=sys.stderr)
        return False
    return True


def main():
    args = [a for a in sys.argv[1:] if a != "--derive-only"]
    derive_only = "--derive-only" in sys.argv
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    out = args[0]
    norm = Path(out) / "work" / "normalized.json"
    if not norm.exists():
        norm = Path(out) / "normalized.json"
    if not norm.exists():
        print("[FAIL] 缺 normalized.json（out/work/ 或 out/）——站③产物缺失", file=sys.stderr)
        return 2

    steps = []
    if not derive_only:
        steps += [
            ("① gen_html 渲染初稿（:root 全量+换肤）",
             [str(CORE / "gen_html.py"), str(norm), str(Path(out) / "design-system.html")]),
            ("② gen_components 组件库形态（33 类字典枚举）",
             [str(CORE / "gen_components.py"), out]),
            ("③ gen_assets 素材网格", [str(CORE / "gen_assets.py"), out]),
            ("④ gen_layouts 九类线框", [str(CORE / "gen_layouts.py"), out]),
            ("④b dual_scale 双标折算（1x 主口径，先折算后派生）",
             [str(CORE / "dual_scale.py"), str(Path(out) / "design-system.html")]),
        ]
    steps += [
        ("⑤ html_to_json 派生机器版", [str(CORE / "html_to_json.py"), out]),
        ("⑥ html_to_md 派生 AI 读版", [str(CORE / "html_to_md.py"), out]),
        ("⑦ fetch_fonts 字体自托管", [str(CORE / "fetch_fonts.py"), out]),
        ("⑧ self_check 十三件套", [str(CORE / "self_check.py"), out]),
    ]
    for desc, cmd in steps:
        if not run(desc, cmd):
            return 1
    print("\n[管线完成] 全部步骤通过——按 self_check 结论交付；"
          "REVIEW 项逐条列明报用户。补全定案后用 --derive-only 重派生。")
    return 0


def html_marker(out):
    p = Path(out) / "design-system.html"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
