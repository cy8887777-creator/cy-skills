"""escape-the-mean 自检 + 回归

跑通 5 种 seed.mjs 用法 + 断言解读字段完整 + 校验关键文件存在。
失败 → 报告 + 修复命令；成功 → 退出 0。
"""
import os, sys, subprocess, json
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
SEED = SKILL_DIR / "scripts" / "seed.mjs"
REQUIRED_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "CLAUDE.md",
    SKILL_DIR / "references" / "start-guide.md",
    SKILL_DIR / "references" / "judge-prompt.md",
    SKILL_DIR / "references" / "principles.md",
    SKILL_DIR / "references" / "discover.md",
    SKILL_DIR / "references" / "define.md",
    SKILL_DIR / "references" / "media.md",
    SKILL_DIR / "references" / "deliver.md",
    SKILL_DIR / "references" / "ai-tells-checklist.md",
    SKILL_DIR / "references" / "direction-catalog.md",
    SKILL_DIR / "references" / "prompt-library.md",
    SKILL_DIR / "templates" / "design-brief.md",
    SKILL_DIR / "templates" / "design-record.md",
    SKILL_DIR / "templates" / "judge-prompt.md",
    SKILL_DIR / "scripts" / "seed.mjs",
    SKILL_DIR / "scripts" / "doctor.py",
    SKILL_DIR / "scripts" / "selftest.py",
]

REQUIRED_JSON_FIELDS = {"seed", "summary", "accentHue", "bodyTypeface", "readings", "judgments"}


def check(name, ok, fix=None):
    mark = "OK  " if ok else "FAIL"
    line = f"  [{mark}] {name}"
    if fix and not ok:
        line += f"\n         修: {fix}"
    print(line)
    return ok


def main():
    print(f"escape-the-mean selftest @ {SKILL_DIR}")
    print("-" * 50)
    all_ok = True

    print("[1] 必需文件检查")
    for f in REQUIRED_FILES:
        all_ok &= check(f.relative_to(SKILL_DIR).as_posix(), f.exists(),
                        f"恢复文件 {f.name}")

    print("\n[2] seed.mjs 用法回归（5 种）")
    cases = [
        ("默认（人类可读）",        ["node", str(SEED)], None, False),
        ("JSON 输出",              ["node", str(SEED), "--json"], '"seed"', True),
        ("4 个并行发散",            ["node", str(SEED), "--count", "4"], None, False),
        ("复现指定种子",            ["node", str(SEED), "--seed", "k7Qa9Z3mN8pR2vT5", "--json"], '"seed"', True),
        ("自定义长度",              ["node", str(SEED), "--length", "48", "--json"], '"seed"', True),
    ]
    for name, cmd, marker, is_json in cases:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=30)
            stdout = r.stdout or ""
            stderr = r.stderr or ""
            output = stdout + stderr
            ok = r.returncode == 0 and (marker is None or marker in output)
            all_ok &= check(f"seed.mjs {name}", ok,
                            f"cd {SEED.parent} && {' '.join(cmd)}")
            if is_json and ok:
                try:
                    obj = json.loads(stdout)
                    missing = REQUIRED_JSON_FIELDS - set(obj.keys())
                    if missing:
                        all_ok &= check(f"  └ 必填字段齐全",
                                        False, f"缺字段 {missing}")
                    else:
                        check(f"  └ 必填字段齐全", True)
                except json.JSONDecodeError as e:
                    all_ok &= check(f"  └ JSON 可解析", False, str(e))
        except subprocess.TimeoutExpired:
            all_ok &= check(f"seed.mjs {name}", False, "超时（30s）")
        except Exception as e:
            all_ok &= check(f"seed.mjs {name}", False, str(e))

    print("\n[3] SKILL.md frontmatter 检查")
    skill_md = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    has_yaml = skill_md.startswith("---") and "\n---\n" in skill_md
    has_name = "name: amazing-vibe-design" in skill_md
    all_ok &= check("SKILL.md 有 YAML frontmatter", has_yaml)
    all_ok &= check("SKILL.md frontmatter 含 name: amazing-vibe-design", has_name)

    print("\n" + "-" * 50)
    print("SELFTEST PASS" if all_ok else "SELFTEST FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
