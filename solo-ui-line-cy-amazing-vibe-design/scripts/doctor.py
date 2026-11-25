"""escape-the-mean 环境体检（精简版）

检查项：Node / 种子脚本可执行 / Playwright（可选）/ BAILIAN_TOKEN（实现者写代码时需要）。
失败 → 报告 + 修复命令；成功 → 退出 0。
"""
import os, sys, shutil, subprocess
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
SEED = SKILL_DIR / "scripts" / "seed.mjs"


def check(name, ok, fix=None):
    mark = "OK  " if ok else "FAIL"
    line = f"  [{mark}] {name}"
    if fix and not ok:
        line += f"\n         修: {fix}"
    print(line)
    return ok


def check_bailian_token() -> tuple[bool, str]:
    """检查 BAILIAN_TOKEN 是否配（在 env 或 ~/.claude/secrets.md）。"""
    tok = os.environ.get("BAILIAN_TOKEN", "").strip()
    if tok:
        return True, "ENV"
    secrets_file = Path.home() / ".claude" / "secrets.md"
    if secrets_file.exists():
        for line in secrets_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line and not line.lower().startswith("bearer "):
                k, v = line.split("=", 1)
                if k.strip() in ("BAILIAN_TOKEN", "TOKEN") and v.strip().strip('"').strip("'"):
                    return True, "SECRETS.md"
            elif line.startswith("sk-"):
                return True, "SECRETS.md (裸 token)"
    return False, "MISSING"


def main():
    print(f"escape-the-mean doctor @ {SKILL_DIR}")
    print("-" * 50)
    all_ok = True

    all_ok &= check("Node.js", shutil.which("node") is not None,
                    "安装 Node 18+ from https://nodejs.org/")

    if not SEED.exists():
        all_ok &= check(f"seed.mjs 存在 ({SEED.name})", False, "技能文件不完整")
    else:
        try:
            r = subprocess.run(
                ["node", str(SEED), "--json"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=15,
            )
            stdout = r.stdout or ""
            ok = r.returncode == 0 and '"seed"' in stdout
            all_ok &= check("seed.mjs 可执行 + JSON 输出", ok,
                            f"cd {SEED.parent} && node seed.mjs --json")
        except subprocess.TimeoutExpired:
            all_ok &= check("seed.mjs 可执行", False, "超时（15s）")
        except FileNotFoundError as e:
            all_ok &= check("seed.mjs 可执行", False, f"node 不可用: {e}")
        except Exception as e:
            all_ok &= check("seed.mjs 可执行", False, str(e))

    pw_ok = False
    try:
        from playwright.sync_api import sync_playwright  # noqa
        pw_ok = True
    except ImportError:
        pass
    check("Playwright（评审回路截图用，可选）", pw_ok,
          "pip install playwright && playwright install chromium")

    tok_ok, tok_src = check_bailian_token()
    all_ok &= check(f"BAILIAN_TOKEN（实现者写代码时需） [{tok_src}]", tok_ok,
                    "跑 image-gen 时按 ~/.claude/skills/image-gen/SKILL.md 的 4 步引导配置 token")

    print("-" * 50)
    print("READY" if all_ok else "NOT READY")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
