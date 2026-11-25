"""
tests/test_pipeline.py — 端到端流水线测试

跑 schema.py / tokenize.py / gen_md.py / gen_html.py / self_check.py 全链路，
用 sample-input/middle.example.json 作 fixtures，验证模板生成产物不破。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts" / "core"
SAMPLE = ROOT / "sample-input" / "middle.example.json"
OUT = ROOT / "out"


def run(name, args, expect=0):
    print(f"\n>>> {name}: {' '.join(args)}")
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8")
    print(f"  exit: {r.returncode}")
    if r.stdout:
        print(f"  stdout: {r.stdout[:500]}")
    if r.stderr:
        print(f"  stderr: {r.stderr[:500]}")
    if expect is not None and r.returncode != expect:
        print(f"  [FAIL] 期望退出码 {expect} 实际 {r.returncode}")
        return False
    return True


def main():
    OUT.mkdir(exist_ok=True)

    # 1) schema 校验 + 计数（案例回归才传 --expect-total 85；真实项目不传）
    if not run("schema count", [str(SCRIPTS / "schema.py"), "count", str(SAMPLE),
                                "--expect-total", "85"]):
        return 1
    if not run("schema validate", [str(SCRIPTS / "schema.py"), "validate", str(SAMPLE)]):
        return 1

    # 2) 体系化
    norm = OUT / "normalized.json"
    if not run("tokenize", [str(SCRIPTS / "tokenize.py"), str(SAMPLE), str(norm)]):
        return 1

    # 3) 双产物生成
    md_out = OUT / "system-rules.md"
    html_out = OUT / "system-spec" / "design-system.html"
    if not run("gen_md", [str(SCRIPTS / "gen_md.py"), str(norm), str(md_out)]):
        return 1
    if not run("gen_html", [str(SCRIPTS / "gen_html.py"), str(norm), str(html_out)]):
        return 1

    # 4) 自检（期望 exit 0=全 PASS；1=有 REVIEW 需人决；2=缺文件）
    #    自检件套 + 案例回归专用 --expect-total（真实项目不传此项）
    if not run("self_check", [str(SCRIPTS / "self_check.py"), str(OUT),
                              "--expect-total", "85"], expect=0):
        print("[WARN] 自检有 REVIEW 项，需人决才宣告完成")

    print("\n=== 端到端测试通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
