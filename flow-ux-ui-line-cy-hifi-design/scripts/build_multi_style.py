"""build_multi_style — 构建时多风格·薄编排（multi-style-spec v2 编排式落地）。

编排单 JSON（每项目一份，参数各不同；本脚本只管顺序与失败即停，纯参数透传，禁造新机制）：
  {
    "build":   {"args": {…build.py 正式构建参数（首选风格，kebab-case 键=CLI 名）…}},   // 可省略=已有产物
    "injects": [ {"args": {…editor_inject_style.py 参数（附加风格）…}}, … ],            // 按序逐个回装
    "verify":  [ "verify_blocks",                                                     // 可选；吃最后产物
                 {"tool": "verify-interactions", "args": {…}} ]                       // 对象形态=全参数透传
  }
行为：按序执行（build 可选跳过）→ 每步非 0 即停并打印失败步与参数 → 全过打印产物路径。
--dry-run 只打印将执行的命令，不执行。
用法：python build_multi_style.py <编排单.json> [--dry-run]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = {"build": [sys.executable, str(ROOT / "build.py")],
         "inject": [sys.executable, str(ROOT / "editor_inject_style.py")]}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def cli_args(args: dict):
    """kebab-case 键 → CLI 形态：值 None 跳过；True=裸 flag；其余 --k v。"""
    out = []
    for k, v in (args or {}).items():
        flag = "--" + str(k)
        if v is None:
            continue
        if v is True:
            out.append(flag)
        elif v is False:
            continue
        else:
            out.extend([flag, str(v)])
    return out


def run_step(label, cmd, dry):
    print("[%s] %s" % (label, " ".join(cmd)))
    if dry:
        return True
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip(), file=sys.stderr)
    if p.returncode != 0:
        print("FAIL at %s（exit %d）——编排即停，后续步未执行" % (label, p.returncode))
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", type=Path, help="编排单 JSON 路径")
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的命令")
    args = ap.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print("FAIL 编排单不可解析: %s" % e)
        return 2

    steps = []          # (label, cmd)
    last_output = None
    b = plan.get("build")
    if b:
        cmd = TOOLS["build"] + cli_args(b.get("args"))
        steps.append(("build 首选风格", cmd))
        last_output = (b.get("args") or {}).get("output")
    for i, inj in enumerate(plan.get("injects") or [], 1):
        ia = inj.get("args") or {}
        if not ia.get("target"):
            print("FAIL injects[%d] 缺 target（注入必有靶产物）" % (i - 1))
            return 2
        steps.append(("inject[%d] %s" % (i, ia.get("db") or "?"), TOOLS["inject"] + cli_args(ia)))
        last_output = ia.get("out") or ia.get("target")
    if not last_output:
        print("FAIL 无产物路径：编排单需 build.args.output 或 injects[i].args.target/out")
        return 2
    for j, v in enumerate(plan.get("verify") or [], 1):
        if v == "verify_blocks":
            steps.append(("verify[%d] verify_blocks" % j,
                          [sys.executable, str(ROOT / "verify_blocks.py"), last_output]))
        elif isinstance(v, dict) and v.get("tool"):
            steps.append(("verify[%d] %s" % (j, v["tool"]),
                          [v["tool"]] + cli_args(v.get("args"))))
        else:
            print("FAIL verify[%d] 形态不认（支持 \"verify_blocks\" 或 {\"tool\":…,\"args\":…}）: %r" % (j, v))
            return 2

    print("编排单：%s ｜ 步数=%d ｜ 产物=%s%s" % (args.plan, len(steps), last_output,
                                                 " ｜ dry-run" if args.dry_run else ""))
    for label, cmd in steps:
        if not run_step(label, cmd, args.dry_run):
            return 1
    print("OK 多风格编排全过：%s" % last_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
