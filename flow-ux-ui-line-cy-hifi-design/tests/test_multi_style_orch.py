#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_multi_style_orch — 构建时多风格·编排链单测（build_multi_style.py + editor_inject_style.py）。

链路：build 首选风格（token-pipeline fixtures 改造副本）→ inject 第二风格（最小 v2 片段 db-b）
→ verify_blocks。断言（2026-11-23 编排式落地，multi-style-spec v2）：
  T1 编排 exit 0 且产物存在；T2 产物含两套 data-style-id 屏集（db-main+db-b 各≥1）；
  T3 双卡：STYLE-REGISTRY.domBases=2 / families=2 / 新包入 packs；
  T4 pageTree 扩为分组表且两风格段齐；T5 verify_blocks PASS（编排内步+单测独立复跑双证）；
  T6 新风格屏 data-name 为中文（P1-8 回归锚：注入器回填片段原页名）；
  T7 --dry-run 只打印命令不落盘；
  T8 AGENTS.md 无页面数/风格占位符（2026-11-23 D 案回归锚：宿主注入锚定物断源）。
数据全落 %TEMP%/multi-style-orch-*，技能包零污染。用法：python tests/test_multi_style_orch.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
FX = SCRIPTS / "fixtures" / "token-pipeline"
PY = sys.executable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILS = []


def check(name, ok, detail=""):
    print(("[PASS] " if ok else "[FAIL] ") + name + (("  实际: " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def run(cmd, cwd):
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def build_workspace(base: Path) -> None:
    """首选风格料（token-pipeline 副本 + pilot-page-css 形态升级）+ 第二风格半边。"""
    shutil.copytree(FX / "pages-ok", base / "pages")
    shutil.copy2(FX / "style-blocks.json", base / "style-blocks.json")
    # build 直出产物要过注入器身份检查（pilot-page-css 块）——副本页面补该形态块（源侧无域前缀，注入器升级）
    for f in (base / "pages").rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        if "pilot-page-css" not in t:
            f.write_text(t + '<style id="pilot-page-css">\n.screen .app { background: var(--style-bg); }\n'
                             '.screen .hero { border-radius: var(--radius-md); }\n</style>\n', encoding="utf-8")
    # 第二风格：最小 v2 片段（页 id b-home，前缀化后 b-b-home）+ 半边受控块（拷 pk-a tokens 改名换色）
    fb = base / "frag-b"
    fb.mkdir()
    (fb / "b-home.html").write_text(
        '<section class="screen" data-screen="b-home" data-name="北屿首页">\n'
        '<div class="scr-head"><span class="scr-name">北屿首页</span></div>\n'
        '<div class="device mobile"><div class="viewport"><div class="app">\n'
        '<div class="appbar" data-block="appbar" data-eid="eb-header"><span class="t">北屿演示</span></div>\n'
        '<div class="b pri" data-block="btn" data-eid="eb-go" data-on=\'{"click":{"goto":"b-home"}}\'>刷新本页</div>\n'
        '</div></div></div>\n</section>\n'
        '<style id="pilot-page-css">\n'
        '.screen[data-style-id="db-b"] .app { background: var(--style-bg); }\n'
        '.screen[data-style-id="db-b"] .b.pri { background: var(--primary); color: #fff; '
        'border-radius: var(--radius-md); }\n</style>\n', encoding="utf-8")
    import copy
    base_sb = json.loads((FX / "style-blocks.json").read_text(encoding="utf-8-sig"))
    pk = copy.deepcopy(base_sb["STYLE-PACK"]["packs"][0])
    pk["packId"] = "pk-beiyu"
    pk["familyId"] = "fam-b"
    pk["tokens"]["primary"] = "#0E7C86"          # 换主色，与首选风格可区分
    pk["identity"] = {"styleId": "wiki:beiyu", "styleName": "北屿", "origin": "ai-generated", "mood": "极简冷色"}
    sb = {"STYLE-REGISTRY": {"schemaVersion": 1,
                             "domBases": [{"domBaseId": "db-b", "note": "北屿骨架", "pages": []}],
                             "families": [{"familyId": "fam-b", "domBaseId": "db-b",
                                           "label": "北屿族", "members": ["pk-beiyu"]}]},
          "STYLE-PACK": {"schemaVersion": 1, "packs": [pk]}}
    (base / "style-blocks-b.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding="utf-8")
    plan = {"build": {"args": {"pages": "pages", "title": "多风格编排单测",
                               "style-blocks": "style-blocks.json", "active-pack": "pk-a",
                               "output": "build/single.html"}},
            "injects": [{"args": {"target": "build/single.html", "fragments": "frag-b",
                                  "style-blocks": "style-blocks-b.json", "db": "db-b",
                                  "pack-id": "pk-beiyu", "out": "build/multi.html"}}],
            "verify": ["verify_blocks"]}
    (base / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    tmp = Path(tempfile.gettempdir())
    for old in tmp.glob("multi-style-orch-*"):
        shutil.rmtree(old, ignore_errors=True)
    base = tmp / ("multi-style-orch-%d-%d" % (int(time.time()), abs(hash(str(tmp))) % 9973))
    base.mkdir(parents=True)
    print("工作区: %s" % base)
    build_workspace(base)

    # T7 前置：--dry-run 不落盘
    code, out = run([PY, SCRIPTS / "build_multi_style.py", "plan.json", "--dry-run"], base)
    check("T7 dry-run 退出 0 且打印三步命令、不落盘",
          code == 0 and "[inject[1] db-b]" in out and not (base / "build").exists(),
          "exit=%d, build/存在=%s" % (code, (base / "build").exists()))

    # T1 编排全链
    code, out = run([PY, SCRIPTS / "build_multi_style.py", "plan.json"], base)
    multi = base / "build" / "multi.html"
    check("T1 编排 exit 0 且产物存在（失败即停输出含步名）",
          code == 0 and multi.is_file() and "[inject[1] db-b]" in out,
          "exit=%d; %s" % (code, "产物在" if multi.is_file() else out.strip()[-160:]))

    t = multi.read_text(encoding="utf-8") if multi.is_file() else ""
    # T8 AGENTS.md 概况不写页面数/风格名（2026-11-23 D 案回归锚：宿主自动注入给任何会话，锚定物断源）
    agents_md = multi.parent / "AGENTS.md"
    atxt = agents_md.read_text(encoding="utf-8") if agents_md.is_file() else ""
    check("T8 AGENTS.md 存在且无页面数/无风格占位符残留",
          agents_md.is_file() and "页面数：" not in atxt and "{{PAGES}}" not in atxt and "{{STYLE}}" not in atxt,
          "存在=%s; 含页面数=%s; 含占位符=%s" % (agents_md.is_file(),
                                             "页面数：" in atxt,
                                             ("{{PAGES}}" in atxt or "{{STYLE}}" in atxt)))
    screens = re.findall(r'<section\b[^>]*data-screen="([^"]+)"[^>]*data-style-id="([^"]+)"', t)
    doms = {d for _, d in screens}
    check("T2 两套 data-style-id 屏集（db-main+db-b 各≥1）",
          "db-main" in doms and "db-b" in doms, "屏集=%s" % screens)

    if t:
        m = re.search(r'<script[^>]*data-block="STYLE-REGISTRY"[^>]*>([\s\S]*?)</script>', t)
        reg = json.loads(m.group(1)) if m else {}
        packs_m = re.search(r'<script[^>]*data-block="STYLE-PACK"[^>]*>([\s\S]*?)</script>', t)
        packs = json.loads(packs_m.group(1))["packs"] if packs_m else []
        check("T3 双卡：domBases=2 / families=2 / pk-beiyu 入 packs",
              len(reg.get("domBases", [])) == 2 and len(reg.get("families", [])) == 2
              and any(p.get("packId") == "pk-beiyu" for p in packs),
              "domBases=%s families=%s packs=%s" % ([d.get("domBaseId") for d in reg.get("domBases", [])],
                                                    [f.get("familyId") for f in reg.get("families", [])],
                                                    [p.get("packId") for p in packs]))
        pt = re.search(r'<script[^>]*id="prototype-page-tree"[^>]*>([\s\S]*?)</script>', t)
        tree = json.loads(pt.group(1)) if pt else {}
        ok_t4 = all(isinstance(v, dict) for v in tree.values()) and {"db-main", "db-b"} <= set(tree)
        check("T4 pageTree 分组表且两风格段齐", ok_t4,
              "keys=%s" % {k: len(v) for k, v in tree.items()} if tree else "无")
        nm = re.search(r'data-screen="b-b-home"[^>]*data-name="([^"]+)"', t) or \
             re.search(r'data-name="([^"]+)"[^>]*data-screen="b-b-home"', t)
        check("T6 新风格屏 data-name=中文页名（P1-8 回归锚）", bool(nm and "北屿首页" == nm.group(1)),
              nm.group(1) if nm else "未找到 b-b-home 页名")
    else:
        check("T3 双卡", False, "产物缺失"); check("T4 pageTree", False, "产物缺失"); check("T6 页名", False, "产物缺失")

    # T5 verify_blocks 独立复跑（编排内已跑过一次）
    code2, out2 = run([PY, SCRIPTS / "verify_blocks.py", str(multi)], base)
    check("T5 verify_blocks PASS（独立复跑）", code2 == 0 and "PASS" in out2,
          "exit=%d; %s" % (code2, (out2.strip().splitlines() or [""])[-1][:120]))

    shutil.rmtree(base, ignore_errors=True)
    print("\nsummary: %d check(s): %d failed — %s" % (8, len(FAILS), "FAIL" if FAILS else "PASS"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
