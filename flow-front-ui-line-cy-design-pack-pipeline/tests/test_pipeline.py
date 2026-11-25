#!/usr/bin/env python3
"""管线技能反例回归套件（自包含，干净检出可复跑）。

来源：2026-10 八轮外部评审积累的全部反例——每个 case 对应一次真实
穿透或误判。任何脚本改动后必跑：python tests/test_pipeline.py
Exit 0 = 全过；1 = 有回归。

用法：python tests/test_pipeline.py [--fast]   # --fast 跳过 playwright 用例
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def make_html(dist: Path, body: str = "x") -> Path:
    dist.mkdir(parents=True, exist_ok=True)
    f = dist / "index.html"
    f.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
    return f


class Suite:
    def __init__(self):
        self.ok = True

    def check(self, name, cond, detail=""):
        if not cond:
            self.ok = False
        print(("PASS " if cond else "FAIL ") + name
              + (f" | {detail}" if detail and not cond else ""))


def _run(script: str, *args):
    """统一子进程包装（capture + utf-8 + errors=replace）。"""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace")


def test_plan_io(s: Suite, T: Path):
    T.mkdir(parents=True, exist_ok=True)
    plan = T / "PLAN.md"
    plan.write_text(
        "# PLAN — t\n## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 精绘 | pending | |\n"
        "| p002 | g002 | 2.png | m | 直写 | in_progress | 模糊 |\n",
        encoding="utf-8")

    def run(*a):
        r = _run("plan-io.py", *a)
        return r.returncode, r.stdout
    c, out = run("stats", str(plan))
    s.check("plan-io: 状态列计数（表头驱动）",
            c == 0 and "pending" in out and "精绘" not in out.split("|", 1)[1], out)
    c, out = run("set", str(plan), "p001", "done")
    line = next(l for l in plan.read_text(encoding="utf-8").splitlines()
                if l.startswith("| p001"))
    s.check("plan-io: set 写状态列不动策略列",
            c == 0 and "| 精绘 | done |" in line, line)
    c, out = run("pending", str(plan))
    s.check("plan-io: pending 排除 done", c == 0 and "p001" not in out and "p002" in out, out)


def test_intake(s: Suite, T: Path):
    from PIL import Image
    fig = T / "fig"; fig.mkdir(parents=True)
    Image.new("RGB", (750, 1624)).save(fig / "1-首页.png")
    Image.new("RGB", (750, 1624)).save(fig / "1-主页.png")  # 撞 id
    Image.new("RGB", (750, 1624)).save(fig / "2-详情.png")
    (fig / "乱.txt").write_text("x", encoding="utf-8")
    proj = T / "proj"
    r = _run("intake.py", str(fig), str(proj))
    m = json.loads((proj / "pipeline" / "pages.manifest.json")
                   .read_text(encoding="utf-8"))
    ids = [i["id"] for i in m["images"]]
    s.check("intake: unparsed → exit 2（gate 硬信号）",
            r.returncode == 2, f"rc={r.returncode}")
    s.check("intake: 撞 id 加后缀",
            "p001-default" in ids and "p001-default-2" in ids, str(ids))
    # 空图包（八轮评审）
    empty = T / "empty"; empty.mkdir()
    proj2 = T / "proj2"
    r = _run("intake.py", str(empty), str(proj2))
    s.check("intake: 空图包 → exit 2 不放行",
            r.returncode == 2 and "0 张图片" in r.stdout,
            f"rc={r.returncode} {r.stdout[:120]}")


def test_route_audit(s: Suite, T: Path, fast: bool):
    dist = T / "dist"
    make_html(dist)
    (T / "frozen.json").write_text(json.dumps(
        [{"id": "home", "path": "/home"},
         {"id": "ghost", "path": "/ghost"}]), encoding="utf-8")
    (T / "routes.json").write_text(json.dumps(
        [{"id": "home", "path": "/home"}]), encoding="utf-8")
    src = T / "src"; src.mkdir()
    (src / "r.tsx").write_text(
        '<Route path="/home" /><Route path="/wild" />', encoding="utf-8")

    def run(*a):
        return _run("route-audit.py", *a)
    r = run("--dist", str(dist), "--routes", str(T / "routes.json"),
            "--from-source", str(src), "--frozen", str(T / "frozen.json"),
            "--out", str(T / "a.json"))
    rep = (json.loads((T / "a.json").read_text(encoding="utf-8"))
           if (T / "a.json").is_file() else {})
    rc = rep.get("reconciliation", {})
    s.check("route-audit: 冻结未实现 /ghost 被抓",
            "/ghost" in str(rc.get("frozen_not_implemented", [])), str(rc))
    s.check("route-audit: 实现未冻结 /wild 被抓",
            "/wild" in str(rc.get("implemented_not_frozen", [])), str(rc))
    s.check("route-audit: 差集 → exit 1",
            r.returncode == 1 and "冻结清单未测" in r.stdout, r.stdout[:150])
    r = run("--dist", str(dist), "--routes", str(T / "routes.json"),
            "--out", str(T / "c.json"))
    s.check("route-audit: 缺 --frozen/--from-source → 拒绝",
            r.returncode != 0, f"rc={r.returncode}")
    if fast:
        return
    # 三方一致 + data-route 探针（需 playwright）
    (src / "r.tsx").write_text(
        "<Route path=\"/home\" />\n// path: '/ghost' 注释噪声",
        encoding="utf-8")
    (T / "routes2.json").write_text(json.dumps(
        [{"id": "home", "path": "/home"},
         {"id": "ghost", "path": "/ghost"}]), encoding="utf-8")
    dist2 = T / "dist2"
    make_html(dist2, '<div data-route="/home">home</div>')
    r = run("--dist", str(dist2), "--routes", str(T / "routes2.json"),
            "--from-source", str(src), "--frozen", str(T / "frozen.json"),
            "--out", str(T / "b.json"))
    rep = (json.loads((T / "b.json").read_text(encoding="utf-8"))
           if (T / "b.json").is_file() else {})
    ghost = next((x for x in rep.get("results", []) if x["id"] == "ghost"), {})
    home = next((x for x in rep.get("results", []) if x["id"] == "home"), {})
    s.check("route-audit: 三方一致但未注册 → 探针裁决 FAIL",
            ghost.get("ok") is False and ghost.get("route_tag") == "/home",
            str(ghost))
    s.check("route-audit: 注册页探针匹配 → ok",
            home.get("ok") is True and home.get("route_tag") == "/home",
            str(home))
    s.check("route-audit 01 F4: 报告顶层含 viewport 字段（默认档如实记录）",
            isinstance(rep.get("viewport"), dict)
            and rep["viewport"].get("width") == 375
            and rep["viewport"].get("height") == 812,
            str(rep.get("viewport")))

    # —— redirect 判据（1008-08）：实际落点==契约落点才算过 ——
    # 合规：/ 跳契约落点 /home → PASS
    (T / "frozen_rd.json").write_text(json.dumps(
        [{"id": "root", "path": "/", "redirect_to": "/home"}]),
        encoding="utf-8")
    (T / "routes_rd.json").write_text(json.dumps(
        [{"id": "root", "path": "/"}]), encoding="utf-8")
    (src / "rd.ts").write_text("path: '/'", encoding="utf-8")
    dist_rd = T / "dist_rd"
    make_html(dist_rd,
              "<script>if(location.pathname==='/'||location.pathname==='')"

              "location.replace('/home')</script>"
              '<div data-route="/home">home content</div>')
    r = run("--dist", str(dist_rd), "--routes", str(T / "routes_rd.json"),
            "--from-source", str(src), "--frozen", str(T / "frozen_rd.json"),
            "--out", str(T / "rd.json"))
    rep = (json.loads((T / "rd.json").read_text(encoding="utf-8"))
           if (T / "rd.json").is_file() else {})
    root_rec = next((x for x in rep.get("results", []) if x["id"] == "root"), {})
    s.check("route-audit: redirect 跳契约落点 → PASS",
            root_rec.get("ok") is True
            and root_rec.get("redirect", {}).get("contract") == "/home",
            str(root_rec))
    # 核心反例：错跳另一真实页（有 data-route）→ FAIL
    dist_bad = T / "dist_bad"
    make_html(dist_bad,
              "<script>if(location.pathname==='/'||location.pathname==='')"

              "location.replace('/other')</script>"
              '<div data-route="/other">other real page</div>')
    r = run("--dist", str(dist_bad), "--routes", str(T / "routes_rd.json"),
            "--from-source", str(src), "--frozen", str(T / "frozen_rd.json"),
            "--out", str(T / "rd_bad.json"))
    rep = (json.loads((T / "rd_bad.json").read_text(encoding="utf-8"))
           if (T / "rd_bad.json").is_file() else {})
    root_rec = next((x for x in rep.get("results", []) if x["id"] == "root"), {})
    s.check("route-audit: redirect 错跳另一真实页 → FAIL（核心反例）",
            root_rec.get("ok") is False
            and root_rec.get("redirect", {}).get("to") == "/other",
            str(root_rec))
    # 未登记 redirect_to 却跳转 → FAIL
    (T / "frozen_plain.json").write_text(json.dumps(
        [{"id": "root", "path": "/"}]), encoding="utf-8")
    r = run("--dist", str(dist_rd), "--routes", str(T / "routes_rd.json"),
            "--from-source", str(src), "--frozen", str(T / "frozen_plain.json"),
            "--out", str(T / "rd_plain.json"))
    rep = (json.loads((T / "rd_plain.json").read_text(encoding="utf-8"))
           if (T / "rd_plain.json").is_file() else {})
    root_rec = next((x for x in rep.get("results", []) if x["id"] == "root"), {})
    s.check("route-audit: 未登记 redirect 却跳转 → FAIL",
            root_rec.get("ok") is False, str(root_rec))


def test_exits_audit(s: Suite, T: Path, fast: bool):
    """1009-14 exits-audit 硬断言：配置校验 + 两态 + 预期必填。"""
    T.mkdir(parents=True, exist_ok=True)

    def make(dist: Path, body: str):
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text(
            f"<html><body>{body}</body></html>", encoding="utf-8")

    def run(*a):
        r = _run("exits-audit.py", *a)
        return r.returncode, r.stdout

    def cfg(name, data):
        (T / name).write_text(json.dumps(data), encoding="utf-8")

    # ---- 配置校验四反例（无需浏览器，预校验前置于 playwright）----
    make(T / "d0", "<div>x</div>")
    cfg("c_empty.json", [{"route": "/x", "role": "secondary",
                          "required_exits": []}])
    c, out = run("--dist", str(T / "d0"), "--exits", str(T / "c_empty.json"),
                 "--out", str(T / "r0.json"))
    s.check("exits-audit: secondary 空 required_exits → 配置不合规 FAIL",
            c == 1 and "required_exits 为空" in out, out[:150])
    cfg("c_noexp.json", [{"route": "/x", "role": "secondary",
                          "required_exits": [{"intent": "nav-back"}]}])
    c, out = run("--dist", str(T / "d0"), "--exits", str(T / "c_noexp.json"),
                 "--out", str(T / "rn.json"))
    s.check("exits-audit: 返回出口无 expect_url_contains → 配置 FAIL",
            c == 1 and "expect_url_contains" in out, out[:150])
    cfg("c_tab.json", [{"route": "/x", "role": "tab_landing",
                        "required_exits": [{"intent": "btn-1"}]}])
    c, out = run("--dist", str(T / "d0"), "--exits", str(T / "c_tab.json"),
                 "--out", str(T / "rt.json"))
    s.check("exits-audit: tab_landing 未声明 tab 全件 → 配置 FAIL",
            c == 1 and "tab 全件" in out, out[:150])
    cfg("c_modal.json", [{"route": "/x", "role": "modal_host",
                          "required_exits": [{"intent": "open-x",
                                              "expect_overlay": True}]}])
    c, out = run("--dist", str(T / "d0"), "--exits", str(T / "c_modal.json"),
                 "--out", str(T / "rm.json"))
    s.check("exits-audit: modal_host 缺关闭出口 → 配置 FAIL",
            c == 1 and "开与关" in out, out[:150])
    if fast:
        return
    # ---- 运行时两态 ----
    # 场景 A（PASS）：深链直达 detail，nav-back 点击回 /map-home
    make(T / "d_ok",
         '<div data-route="/detail">detail'
         '<button data-intent="nav-back" '
         "onclick=\"location.href='/map-home'\">back</button></div>")
    cfg("c_ok.json", [{"route": "/detail", "role": "secondary",
                       "required_exits": [{"intent": "nav-back",
                                           "expect_url_contains": "/map-home"}]}])
    c, out = run("--dist", str(T / "d_ok"), "--exits", str(T / "c_ok.json"),
                 "--out", str(T / "ro.json"))
    s.check("exits-audit: 返回出口落点命中 → PASS（深链态）",
            c == 0 and "落点命中" not in out, out[:200])
    # 场景 B（FAIL）：返回出口实际去 /other（语义错位/死出口变体）
    make(T / "d_wrong",
         '<div data-route="/detail">detail'
         '<button data-intent="nav-back" '
         "onclick=\"location.href='/other'\">back</button></div>")
    c, out = run("--dist", str(T / "d_wrong"), "--exits", str(T / "c_ok.json"),
                 "--out", str(T / "rw.json"))
    rep = (json.loads((T / "rw.json").read_text(encoding="utf-8"))
           if (T / "rw.json").is_file() else {})
    item = next((x2 for x in rep.get("results", [])
                 for x2 in x.get("exits", [])
                 if x2.get("intent") == "nav-back"), None)
    s.check("exits-audit: 返回落点不符契约 → FAIL（死出口变体）",
            c == 1 and item is not None and item.get("ok") is False
            and "落点不符" in (item.get("fail") or ""), out[:200])
    # 场景 C（PASS）：站内进入态 enter_via 声明可复现步骤
    make(T / "d_enter",
         '<div data-route="/home">'
         '<button data-intent="open-detail" '
         "onclick=\"location.href='/detail'\">go</button></div>"
         '<div data-route="/detail">detail'
         '<button data-intent="nav-back" '
         "onclick=\"location.href='/map-home'\">back</button></div>")
    cfg("c_enter.json", [{"route": "/detail", "role": "secondary",
                          "required_exits": [{"intent": "nav-back",
                                              "expect_url_contains": "/map-home"}],
                          "enter_via": [{"goto": "/home",
                                         "click": "open-detail"}]}])
    c, out = run("--dist", str(T / "d_enter"), "--exits", str(T / "c_enter.json"),
                 "--out", str(T / "re.json"))
    rep = (json.loads((T / "re.json").read_text(encoding="utf-8"))
           if (T / "re.json").is_file() else {})
    modes = [x2.get("mode") for x in rep.get("results", [])
             for x2 in x.get("exits", [])]
    s.check("exits-audit: 站内进入态（enter_via 声明步骤）→ 两态覆盖 PASS",
            c == 0 and "in-app" in modes and "deep-link" in modes,
            f"modes={modes} {out[:150]}")
    s.check("exits-audit 01 F4: 报告顶层含 viewport 字段（默认档如实记录）",
            isinstance(rep.get("viewport"), dict)
            and rep["viewport"].get("width") == 375
            and rep["viewport"].get("height") == 812,
            str(rep.get("viewport")))


def test_e2e_assert(s: Suite, T: Path, fast: bool):
    """1008-02 空断言恒真封堵。"""
    if fast:
        return
    dist = T / "d_e2e"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        "<script>if(location.pathname==='/'||location.pathname==='')"
        "location.replace('/home')</script>"
        '<div data-route="/home">home</div>', encoding="utf-8")
    (T / "steps_noexp.json").write_text(json.dumps(
        [{"id": "s1", "name": "打开", "goto": "/"}]), encoding="utf-8")
    (T / "steps_exp.json").write_text(json.dumps(
        [{"id": "s1", "name": "打开", "goto": "/",
          "expect_url": "/home"}]), encoding="utf-8")

    def run(*a):
        return _run("e2e-smoke.py", *a)
    r = run("--dist", str(dist), "--steps", str(T / "steps_noexp.json"),
            "--out", str(T / "sm1.json"))
    s.check("e2e-smoke: 无 expect_* 步骤 → FAIL（空断言封堵）",
            r.returncode == 1 and "expect" in r.stdout + str(
                json.loads((T / "sm1.json").read_text(encoding="utf-8"))
                ["results"][0].get("expect_error", "")), r.stdout[:150])
    r = run("--dist", str(dist), "--steps", str(T / "steps_exp.json"),
            "--out", str(T / "sm2.json"))
    s.check("e2e-smoke: 带预期步骤 → PASS",
            r.returncode == 0, r.stdout[:150])
    sm2 = json.loads((T / "sm2.json").read_text(encoding="utf-8"))
    s.check("e2e-smoke 01 F4: 报告顶层含 viewport 字段（默认档如实记录）",
            isinstance(sm2.get("viewport"), dict)
            and sm2["viewport"].get("width") == 375
            and sm2["viewport"].get("height") == 812,
            str(sm2.get("viewport")))

    # —— 1012-07 几何贴底断言（expect_pinned_bottom）——
    def make_pinned(dist_name: str, tabbar_css: str):
        d = T / dist_name
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            "<script>if(location.pathname==='/'||location.pathname==='')"
            "location.replace('/home')</script>"
            '<div data-route="/home">home</div>'
            f'<div class="tabbar" style="{tabbar_css}">tabbar</div>',
            encoding="utf-8")
        return d

    def run_pinned(dist, steps, out, viewport=None):
        a = ["--dist", str(dist), "--steps", str(steps), "--out", str(out)]
        if viewport:
            a += ["--viewport", viewport]
        return run(*a)

    (T / "steps_pin.json").write_text(json.dumps([
        {"id": "s1", "name": "打开", "goto": "/",
         "expect_url": "/home",
         "expect_pinned_bottom": ".tabbar"}]), encoding="utf-8")
    (T / "steps_pin_only.json").write_text(json.dumps([
        {"id": "s1", "name": "打开", "goto": "/",
         "expect_pinned_bottom": ".tabbar"}]), encoding="utf-8")
    # F1 贴底 PASS（fixed bottom:0 → bottom≈812 ∈ [804,820]）
    d_pin = make_pinned("d_pin",
                        "position:fixed;bottom:0;left:0;height:49px;"
                        "width:100%")
    r = run_pinned(d_pin, T / "steps_pin.json", T / "pin1.json")
    p1 = json.loads((T / "pin1.json").read_text(encoding="utf-8"))
    s.check("e2e-pin F1: 贴底元素 bottom≈vh → PASS",
            r.returncode == 0 and p1["results"][0].get("pinned_ok") is True,
            str(p1["results"][0])[:200])
    # F1b 变体视口 820x1180：vh 取实际值禁硬编码 812（同 fixture 仍贴底）
    r = run_pinned(d_pin, T / "steps_pin.json", T / "pin1b.json",
                   viewport="820x1180")
    p1b = json.loads((T / "pin1b.json").read_text(encoding="utf-8"))
    s.check("e2e-pin F1b: --viewport 820x1180 下 vh=1180 仍 PASS（禁硬编码）",
            r.returncode == 0
            and p1b["results"][0].get("pinned_ok") is True,
            str(p1b["results"][0])[:200])
    # F2 margin 悬空 FAIL（bottom:50 → bottom=762 超区间；pinned_ok
    # 拉低整步——expect_url 过但步骤 FAIL）
    d_float = make_pinned("d_float",
                          "position:fixed;bottom:50px;left:0;height:49px;"
                          "width:100%")
    r = run_pinned(d_float, T / "steps_pin.json", T / "pin2.json")
    p2 = json.loads((T / "pin2.json").read_text(encoding="utf-8"))
    rec2 = p2["results"][0]
    s.check("e2e-pin F2: 悬空 50px → FAIL 且 pinned_ok=False 拉低整步",
            r.returncode == 1 and rec2.get("pinned_ok") is False
            and rec2.get("ok") is False
            and "bottom=" in str(rec2.get("pinned_error", "")),
            str(rec2)[:250])
    # F3 selector 不存在 → FAIL（bounding_box=None 禁跳过）
    (T / "steps_pin_ghost.json").write_text(json.dumps([
        {"id": "s1", "name": "打开", "goto": "/",
         "expect_url": "/home",
         "expect_pinned_bottom": ".not-exist"}]), encoding="utf-8")
    r = run_pinned(d_pin, T / "steps_pin_ghost.json", T / "pin3.json")
    p3 = json.loads((T / "pin3.json").read_text(encoding="utf-8"))
    s.check("e2e-pin F3: selector 不存在 → FAIL（bounding_box=None 禁跳过）",
            r.returncode == 1
            and p3["results"][0].get("pinned_ok") is False
            and "未匹配到元素" in str(p3["results"][0].get("pinned_error", "")),
            str(p3["results"][0])[:250])
    # F4 单步仅 pinned 不误杀（has_expect 枚举扩入——漏扩则恒报无断言）
    r = run_pinned(d_pin, T / "steps_pin_only.json", T / "pin4.json")
    p4 = json.loads((T / "pin4.json").read_text(encoding="utf-8"))
    s.check("e2e-pin F4: 仅 expect_pinned_bottom 的步骤不误报无断言 → PASS",
            r.returncode == 0
            and "expect_error" not in p4["results"][0],
            str(p4["results"][0])[:200])


def test_style_lint(s: Suite, T: Path):
    def run_case(tokens: str, files: dict) -> tuple[int, str, Path]:
        T.mkdir(parents=True, exist_ok=True)
        w = T / f"case{T.name}{len(list(T.iterdir()))}"
        (w / "src" / "pages").mkdir(parents=True)
        (w / "src" / "tokens.ts").write_text(tokens, encoding="utf-8")
        for name, body in files.items():
            p = w / "src" / "pages" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        r = _run("style-lint.py", "--src", str(w / "src"))
        return r.returncode, r.stdout, w

    c, out, _ = run_case(
        'export const fontSize = { md: 16 };',
        {"ok.tsx": 'const a = <div style={{fontSize: 16}}>x</div>;'})
    s.check("style-lint: 裸数字 fontSize:16 白名单内（px? 根修）",
            c == 0 and "✓" in out, f"rc={c} {out[:150]}")
    c, out, _ = run_case(
        'export const tokens = { fontSize: { sm: { base: 12 }, md: 16 } };',
        {"ok.tsx": 'const a = <div style={{fontSize: 12}}>x</div>;'})
    s.check("style-lint: 嵌套/双层容器形态识别",
            c == 0 and "✓" in out, f"rc={c} {out[:150]}")
    c, out, _ = run_case(
        'export const radius = { md: 16 };\n'
        'export const fontSize = { md: 16, /* 99 */ lg: 20 },'.replace(",", ";"),
        {"bad.tsx": 'const b = <div style={{fontSize: 99}}>y</div>;'})
    s.check("style-lint: radius 污染/注释 99 均不进白名单（fontSize:99 抓）",
            c == 1 and "99px" in out, f"rc={c} {out[:200]}")
    c, out, _ = run_case(
        'export const lineHeight = { md: 24 };\n'
        'export const fontSize = { md: 16 };',
        {"lh.tsx": 'const b = <div style={{fontSize: 24}}>y</div>;'})
    s.check("style-lint: lineHeight 24 不进字号白名单",
            c == 1 and "24px" in out, f"rc={c} {out[:200]}")
    c, out, _ = run_case(
        'export const t = { vars: { "--font-css": "serif" } };',
        {"ok.tsx": 'const a = <div style={{fontFamily: "var(--font-css)"}}>x</div>;'})
    s.check("style-lint: 引号键定义的变量 var() 豁免",
            c == 0 and "✓" in out, f"rc={c} {out[:150]}")
    c, out, _ = run_case(
        'export const colors = { primary: "#1a73e8" };',
        {"inv.tsx": 'const c = <div style={{fontFamily: "var(--invented, serif)"}}>z</div>;'})
    s.check("style-lint: var(--invented) 未定义变量被拒",
            c == 1 and "--invented" in out, f"rc={c} {out[:200]}")
    c, out, w = run_case(
        'export const colors = { primary: "#1a73e8" };',
        {"url.tsx": 'fetch("https://cdn.test/x"); const s = {fontFamily: "FakeFont"};',
         "cmt.css": '/* font-family: "Comment Sans" */',
         "fam.css": '.a{font-family:var(--nope, serif)}'},
        )
    s.check("style-lint: URL 同行真违规不被 // 误剥",
            c == 1 and "FakeFont" in out, f"rc={c} {out[:250]}")
    s.check("style-lint: 注释族不误报",
            "Comment Sans" not in out, out[:250])
    s.check("style-lint: css font-family 连字符被抓（崩溃回归）",
            "fam.css" in out and "font-family" in out, out[:250])


def test_contracts_lint(s: Suite, T: Path):
    def run(*a):
        r = _run("contracts-lint.py", *a)
        return r.returncode, r.stdout
    # 违规工程：未挂载页 + 缺 mock + 命名违规
    src = T / "cl"; (src / "pages").mkdir(parents=True)
    (src / "pages" / "P001Login.tsx").write_text(
        'const a = <div data-route="/登录">x</div>;', encoding="utf-8")
    (src / "pages" / "NoRoute.tsx").write_text(
        'const a = <div>orphan</div>;', encoding="utf-8")
    (T / "routes.json").write_text(json.dumps(
        [{"id": "p001", "path": "/登录"},
         {"id": "p006", "path": "/地图导览主页"}]), encoding="utf-8")
    c, out = run("--src", str(src), "--routes", str(T / "routes.json"),
                 "--out", str(T / "cl1.json"))
    s.check("contracts-lint: 未挂载页/缺 mock/命名违规全抓",
            c == 1 and "NoRoute" in out and "mock" in out and "命名" in out,
            out[:250])
    # 合规工程（删违规页 + 补 mock）→ PASS
    (src / "pages" / "NoRoute.tsx").unlink()
    (src / "mocks" / "pages").mkdir(parents=True, exist_ok=True)
    (src / "mocks" / "pages" / "P001Login.ts").write_text(
        "export const m = 1;", encoding="utf-8")
    (T / "routes.json").write_text(json.dumps(
        [{"id": "p001", "path": "/登录"}]), encoding="utf-8")
    c, out = run("--src", str(src), "--routes", str(T / "routes.json"),
                 "--out", str(T / "cl2.json"))
    s.check("contracts-lint: 合规工程 PASS（mock 外置在位）",
            c == 0 and "✓" in out, f"rc={c} {out[:200]}")

    # —— Vue 栈适配（1008-07）——
    vsrc = T / "cl_vue"; (vsrc / "pages").mkdir(parents=True)
    (vsrc / "pages" / "order-list.vue").write_text(
        '<template><div data-route="/order-list">x</div></template>',
        encoding="utf-8")
    (vsrc / "pages" / "BadName.vue").write_text(
        '<template><div data-route="/bad">x</div></template>',
        encoding="utf-8")
    (vsrc / "pages" / "no-route.vue").write_text(
        '<template><div>orphan</div></template>', encoding="utf-8")
    (T / "routes_vue.json").write_text(json.dumps(
        [{"id": "p1", "path": "/order-list"}]), encoding="utf-8")
    c, out = run("--src", str(vsrc), "--routes", str(T / "routes_vue.json"),
                 "--stack", "vue", "--out", str(T / "clv1.json"))
    s.check("contracts-lint vue: 应 FAIL 的反例全抓（未挂载/BadName/缺 mock）",
            c == 1 and "no-route" in out and "BadName" in out
            and "mock" in out, out[:300])
    (vsrc / "mocks" / "pages").mkdir(parents=True, exist_ok=True)
    (vsrc / "mocks" / "pages" / "order-list.ts").write_text(
        "export const m = 1;", encoding="utf-8")
    (vsrc / "pages" / "BadName.vue").unlink()
    (vsrc / "pages" / "no-route.vue").unlink()
    c, out = run("--src", str(vsrc), "--routes", str(T / "routes_vue.json"),
                 "--stack", "vue", "--out", str(T / "clv2.json"))
    s.check("contracts-lint vue: 合规 .vue 工程 PASS",
            c == 0 and "✓" in out, f"rc={c} {out[:200]}")

    # —— 占位字样检查（1010-03：页面+mock 禁占位，注释行豁免）——
    (src / "pages" / "P001Login.tsx").write_text(
        'const a = <div data-route="/登录">lorem ipsum 测试文案</div>;',
        encoding="utf-8")
    (src / "mocks" / "pages" / "P001Login.ts").write_text(
        "// 注释含占位内容不报（豁免验证）\n"
        "export const m = { name: '示例数据' };", encoding="utf-8")
    c, out = run("--src", str(src), "--routes", str(T / "routes.json"),
                 "--out", str(T / "cl3.json"))
    s.check("contracts-lint: 占位字样页面+mock 全抓、注释行豁免（1010-03）",
            c == 1 and "lorem" in out and "示例数据" in out
            and "注释含占位" not in out, out[:300])
    # 修复后回归 PASS
    (src / "pages" / "P001Login.tsx").write_text(
        'const a = <div data-route="/登录">中央大厅</div>;', encoding="utf-8")
    (src / "mocks" / "pages" / "P001Login.ts").write_text(
        "export const m = { name: '青铜面具' };", encoding="utf-8")
    c, out = run("--src", str(src), "--routes", str(T / "routes.json"),
                 "--out", str(T / "cl4.json"))
    s.check("contracts-lint: 占位清除后回归 PASS",
            c == 0 and "✓" in out, f"rc={c} {out[:200]}")


def test_style_lint_vue(s: Suite, T: Path):
    """1009-16 style-lint Vue SFC 扫描 + 零覆盖 FAIL。"""
    T.mkdir(parents=True, exist_ok=True)
    (T / "tokens.ts").write_text(
        'export const colors = { primary: "#1a73e8" };\n'
        'export const fontSize = { md: 16 };', encoding="utf-8")

    def run(*a):
        r = _run("style-lint.py", *a)
        return r.returncode, r.stdout

    def make_vue(name, body):
        pg = T / "src" / "pages" / name
        pg.parent.mkdir(parents=True, exist_ok=True)
        pg.write_text(body, encoding="utf-8")

    # 违规：<style> 块与内联 style 各一处 tokens 外字面量
    make_vue("bad.vue",
             '<template><div style="font-size: 13px; color: #123456">x</div></template>\n'
             '<style scoped>.a { color: #abcdef; }</style>')
    c, out = run("--src", str(T / "src"), "--stack", "vue",
                 "--tokens", str(T / "tokens.ts"))
    s.check("style-lint vue: <style> 块与内联 style 违规全抓",
            c == 1 and "bad.vue" in out and "#123456" in out
            and "13px" in out and "#abcdef" in out, out[:250])
    # 合规：颜色/字号在 tokens 或允许集 → PASS
    make_vue("ok.vue",
             '<template><div style="font-size: 16px; color: #1a73e8">x</div></template>')
    (T / "src" / "pages" / "bad.vue").unlink()
    c, out = run("--src", str(T / "src"), "--stack", "vue",
                 "--tokens", str(T / "tokens.ts"))
    s.check("style-lint vue: 合规 .vue PASS 且声明覆盖",
            c == 0 and "stack=vue" in out and "1 页" in out, f"rc={c} {out[:200]}")
    # 零覆盖：--stack vue 但工程无 .vue → FAIL
    (T / "src" / "pages" / "ok.vue").unlink()
    c, out = run("--src", str(T / "src"), "--stack", "vue",
                 "--tokens", str(T / "tokens.ts"))
    s.check("style-lint vue: 所选栈零目标页 → FAIL（零覆盖声明）",
            c == 1 and "零" in out, f"rc={c} {out[:150]}")
    # React 路径不回归：tsx 扫描仍工作
    rx = T / "src" / "pages" / "R.tsx"
    rx.write_text('const a = <div style={{fontSize: 99}}>x</div>;', encoding="utf-8")
    c, out = run("--src", str(T / "src"), "--stack", "react",
                 "--tokens", str(T / "tokens.ts"))
    s.check("style-lint react: tsx 路径不回归（fontSize:99 抓）",
            c == 1 and "99px" in out, f"rc={c} {out[:150]}")


def test_device_probe(s: Suite, T: Path, fast: bool):
    """1010-04 设备形态探针：分带/置信度/视口映射/隔离 + 消费链断言。"""
    from PIL import Image

    def mkfig(name: str, sizes):
        fig = T / name
        fig.mkdir(parents=True, exist_ok=True)
        for i, (w, h) in enumerate(sizes, 1):
            Image.new("RGB", (w, h)).save(fig / f"{i}-图.png")
        return fig

    def probe(fig):
        return _run("intake.py", str(fig), "--probe")

    def jout(r):
        return json.loads(r.stdout.strip().splitlines()[0])

    # F1 纯手机竖屏 + F15 视口映射
    r = probe(mkfig("f1", [(750, 1624)] * 5))
    j = jout(r)
    s.check("probe: 纯竖屏 → phone_portrait/high/375x812（F1/F15）",
            r.returncode == 0 and j["form"] == "phone_portrait"
            and j["confidence"] == "high"
            and j["viewport"] == {"width": 375, "height": 812},
            str(j)[:150])
    # 1012-02：stdout 纯净化——恰一行且整体可解析（人类摘要不得混入机器通道）
    s.check("probe 02: stdout 恰一行且 json 可解析（摘要迁 stderr）",
            len(r.stdout.strip().splitlines()) == 1
            and isinstance(json.loads(r.stdout.strip()), dict),
            repr(r.stdout[:120]))
    s.check("probe 02: 人类摘要在 stderr（表单默认值依据文案）",
            "推断：" in r.stderr and "目标设备" in r.stderr,
            repr(r.stderr[:120]))
    # F14 隔离：--probe 不落盘（与①盘点隔离）
    s.check("probe: 不落盘（F14，与①盘点隔离）",
            not (T / "f1" / "pipeline").exists()
            and not (T / "pages.manifest.json").exists(), "")
    j = jout(probe(mkfig("f2", [(1624, 750)] * 4)))
    s.check("probe: 纯横屏 → landscape/high/1280x800（F2/F15）",
            j["form"] == "landscape" and j["confidence"] == "high"
            and j["viewport"] == {"width": 1280, "height": 800},
            str(j)[:120])
    j = jout(probe(mkfig("f3", [(820, 1180)] * 4)))
    s.check("probe: 纯 Pad → tablet/high/820x1180（F3/F15）",
            j["form"] == "tablet" and j["confidence"] == "high"
            and j["viewport"] == {"width": 820, "height": 1180},
            str(j)[:120])
    j = jout(probe(mkfig("f4", [(750, 1624), (750, 1624), (1624, 750),
                                (1624, 750), (820, 1180)])))
    s.check("probe: 混杂图包 → low（F4）",
            j["confidence"] == "low", str(j)[:150])
    j = jout(probe(mkfig("f5", [(750, 1334)] * 3)))
    s.check("probe: 手机带最宽 0.562 不滑入 Pad 带（F5）",
            j["form"] == "phone_portrait", str(j)[:120])
    j = jout(probe(mkfig("f6", [(744, 1133)] * 3)))
    s.check("probe: Pad 带最窄 0.657 不滑入手机带（F6）",
            j["form"] == "tablet", str(j)[:120])
    j = jout(probe(mkfig("f7", [(1194, 834)] * 3)))
    s.check("probe: 横 Pad 1.43 → landscape 档（F7，三档制定案）",
            j["form"] == "landscape", str(j)[:120])
    j = jout(probe(mkfig("f8", [(750, 3600)] * 3)))
    s.check("probe: 长图归一入竖带（F8，复用 2.2 阈值防双口径）",
            j["form"] == "phone_portrait" and j["confidence"] == "high",
            str(j)[:120])
    r = probe(mkfig("f9", []))
    s.check("probe: 空图包 → exit 2 无 JSON（F9）",
            r.returncode == 2 and "{" not in r.stdout, r.stdout[:100])
    # 1012-02：错误路径 stdout 同样纯净（文案在 stderr）
    s.check("probe 02: 空图包错误文案走 stderr，stdout 无混入（F9 扩展）",
            r.returncode == 2 and r.stdout.strip() == ""
            and "0 张" in r.stderr,
            f"stdout={r.stdout[:60]!r} stderr={r.stderr[:80]!r}")
    r2 = _run("intake.py", str(T / "no_such_dir_xyz"), "--probe")
    s.check("probe 02: 目录不存在错误走 stderr，stdout 空（1012-02）",
            r2.returncode == 1 and r2.stdout.strip() == ""
            and "不存在" in r2.stderr,
            f"rc={r2.returncode} stdout={r2.stdout[:60]!r} stderr={r2.stderr[:80]!r}")
    fig = T / "f10"
    fig.mkdir(parents=True, exist_ok=True)
    (fig / "乱.txt").write_text("x", encoding="utf-8")
    r = probe(fig)
    s.check("probe: 全 unparsed → exit 2（F10）",
            r.returncode == 2, r.stdout[:100])
    j = jout(probe(mkfig("f11", [(750, 1624)] * 2)))
    s.check("probe: n=2 → low（F11，样本下限）",
            j["confidence"] == "low", str(j)[:120])
    j = jout(probe(mkfig("f12", [(1000, 1000)] * 3)))
    s.check("probe: 灰带方形 → tablet/low（F12）",
            j["form"] == "tablet" and j["confidence"] == "low",
            str(j)[:120])
    j = jout(probe(mkfig("f13a", [(750, 1624)] * 17 + [(1624, 750)] * 3)))
    s.check("probe: 17/20=85.0% → high（F13，含等号方向锁定）",
            j["confidence"] == "high", str(j)[:120])
    j = jout(probe(mkfig("f13b", [(750, 1624)] * 16 + [(1624, 750)] * 4)))
    s.check("probe: 16/20=80% → low（F13 反向）",
            j["confidence"] == "low", str(j)[:120])

    # —— A 系静态断言：消费链（fast 可跑，纯文本）——
    a1_ok = True
    for n in ["e2e-smoke", "exits-audit", "route-audit", "explore-walk"]:
        for line in (ROOT / "scripts" / f"{n}.py").read_text(
                encoding="utf-8").splitlines():
            if ('viewport={"width": 375' in line
                    and "DEFAULT_VIEWPORT" not in line):
                a1_ok = False
    s.check("probe 消费 A-1: 4 脚本视口字面量清零（DEFAULT 定义行豁免）",
            a1_ok, "")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    s.check("probe 消费 A-2: SKILL 激活协议 8 项+目标设备+预填+低置信必答",
            "8 项" in skill and "目标设备" in skill
            and "回车确认" in skill and "必答" in skill, "")
    pt = (ROOT / "templates" / "plan-template.md").read_text(
        encoding="utf-8")
    s.check("probe 消费 A-3: execution_policy 含 device_profile",
            "device_profile" in pt, "")
    cm = (ROOT / "references" / "contracts.md").read_text(
        encoding="utf-8")
    s.check("probe 消费 A-4: contracts C-09 在册+反例函数真实存在",
            "| C-09 |" in cm and "设备形态" in cm
            and "test_device_probe" in cm, "")
    pl = (ROOT / "templates" / "page-loop-prompt.md").read_text(
        encoding="utf-8")
    s.check("probe 消费 A-5: page-loop 视口档条文",
            "device_profile" in pl, "")
    sg = (ROOT / "references" / "station-guide.md").read_text(
        encoding="utf-8")
    s.check("probe 消费 A-6: station-guide §6/§10 视口条文",
            "视口档" in sg and "画布居中" in sg and "--viewport" in sg, "")

    # —— B-1 行为级：e2e-smoke 视口参数真穿透（非 fast，防静默兜底假绿）——
    if fast:
        return
    dist = T / "d_vp"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        '<div data-route="/v">v</div>'
        "<script>document.body.insertAdjacentHTML('beforeend',"
        "'<div>' + window.innerHeight + '</div>')</script>",
        encoding="utf-8")
    (T / "steps_vp.json").write_text(json.dumps(
        [{"id": "s1", "name": "打开", "goto": "/",
          "expect_visible": "1180"}]), encoding="utf-8")
    r = _run("e2e-smoke.py", "--dist", str(dist), "--steps",
             str(T / "steps_vp.json"), "--viewport", "820x1180",
             "--out", str(T / "vp1.json"))
    s.check("probe 消费 B-1a: --viewport 820x1180 → 页面真以 1180 高渲染",
            r.returncode == 0, r.stdout[:150])
    r = _run("e2e-smoke.py", "--dist", str(dist), "--steps",
             str(T / "steps_vp.json"), "--out", str(T / "vp2.json"))
    s.check("probe 消费 B-1b: 默认 812 下 1180 不可见（双向锁定防假绿）",
            r.returncode != 0, r.stdout[:150])


def test_setup_env(s: Suite):
    src = (ROOT / "scripts" / "setup-env.py").read_text(encoding="utf-8")
    s.check("setup-env: I2C_BG_MODEL 文件形态须文件名匹配",
            "if p.name == name" in src)
    s.check("setup-env: 模型任一存在即可（any 与 doctor 对齐）",
            "any(have.values())" in src)


def test_explore_walk(s: Suite, T: Path, fast: bool):
    """1008-05 探索式游走：死端发现 + terminal 豁免 + seed 可复现。"""
    if fast:
        return
    T.mkdir(parents=True, exist_ok=True)

    def make(dist: Path, body: str):
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text(
            f"<html><body>{body}</body></html>", encoding="utf-8")

    # 死端工程：首页按钮跳 detail，detail 无出口
    make(T / "d_dead",
         '<div data-route="/home">'
         '<button data-intent="open-detail" '
         'onclick="location.href=\'/detail\'">go</button></div>')
    (T / "exits_dead.json").write_text(json.dumps(
        [{"route": "/detail", "role": "secondary",
          "required_exits": []}]), encoding="utf-8")
    r = _run("explore-walk.py", "--dist", str(T / "d_dead"),
             "--steps", "6", "--seed", "7",
             "--exits", str(T / "exits_dead.json"),
             "--out", str(T / "w1.json"))
    rep = (json.loads((T / "w1.json").read_text(encoding="utf-8"))
           if (T / "w1.json").is_file() else {})
    s.check("explore-walk: detail 无出口 → 死端 FAIL",
            r.returncode == 1 and any("死端" in f for f in rep.get("fails", [])),
            str(rep.get("fails"))[:200])
    s.check("explore-walk: seed+路径落盘可复现",
            rep.get("seed") == 7 and isinstance(rep.get("path"), list),
            str(rep.get("seed")))
    # 良性工程：detail 有返回钮 → PASS
    make(T / "d_ok",
         '<div data-route="/home">'
         '<button data-intent="open-detail" '
         'onclick="location.href=\'/detail\'">go</button></div>'
         '<div data-route="/detail">detail'
         '<button data-intent="nav-back" '
         'onclick="location.href=\'/home\'">back</button></div>')
    r = _run("explore-walk.py", "--dist", str(T / "d_ok"),
             "--steps", "6", "--seed", "7",
             "--exits", str(T / "exits_dead.json"),
             "--out", str(T / "w2.json"))
    s.check("explore-walk: 出口在位 → PASS",
            r.returncode == 0, r.stdout[:200])

    # —— 1012-01 F4/F5：报告 viewport 字段 + --src 落账链（真实链路）——
    srcdir = T / "src_w"
    (srcdir / "pages").mkdir(parents=True)
    (srcdir / "pages" / "P001Home.tsx").write_text("x", encoding="utf-8")
    r = _run("explore-walk.py", "--dist", str(T / "d_ok"),
             "--steps", "6", "--seed", "7",
             "--exits", str(T / "exits_dead.json"),
             "--src", str(srcdir),
             "--out", str(T / "w3.json"))
    rep3 = (json.loads((T / "w3.json").read_text(encoding="utf-8"))
            if (T / "w3.json").is_file() else {})
    s.check("explore-walk 01 F4: 报告顶层含 viewport 字段（默认档 375x812 如实记录）",
            isinstance(rep3.get("viewport"), dict)
            and rep3["viewport"].get("width") == 375
            and rep3["viewport"].get("height") == 812,
            str(rep3.get("viewport")))
    idx = srcdir.parent / "pipeline" / "evidence_index.jsonl"
    s.check("explore-walk 01 F5: --src → 落账 evidence_index.jsonl",
            idx.is_file(), str(idx))
    sys.path.insert(0, str(SCRIPTS))
    from evidence_index import latest_valid, src_hash
    row = latest_valid(idx, src_hash(srcdir), "explore-walk", str(srcdir))
    s.check("explore-walk 01 F5: latest_valid 消费到 PASS 行且 per_id 按页归因",
            row is not None and row.get("verdict") == "PASS"
            and "/home" in (row.get("per_id") or {}),
            str(row and (row.get("per_id"), row.get("verdict")))[:200])
    # 反例：无 --src → fail-closed 跳过落账（stderr 显式，禁静默/禁 cwd 脏行）
    r = _run("explore-walk.py", "--dist", str(T / "d_ok"),
             "--steps", "2", "--seed", "7", "--out", str(T / "w4.json"))
    s.check("explore-walk 01: 无 --src → stderr 显式跳过落账（fail-closed）",
            "跳过证据索引落账" in (r.stderr or ""),
            (r.stderr or "")[:150])


def test_plan_recon(s: Suite, T: Path):
    """1008-09 PLAN 对账：漏回填/假完成/全过。"""
    T.mkdir(parents=True, exist_ok=True)
    plan = T / "PLAN.md"
    plan.write_text(
        "# PLAN — t\n## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | pending | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    (T / "frozen.json").write_text(json.dumps(
        [{"id": "p001", "path": "/p001"},
         {"id": "p002", "path": "/p002"}]), encoding="utf-8")
    src = T / "src"
    (src / "pages").mkdir(parents=True)
    (src / "pages" / "P001Login.tsx").write_text("x", encoding="utf-8")

    def run(*a):
        r = _run("plan-recon.py", *a)
        return r.returncode, r.stdout
    c, out = run("--plan", str(plan), "--routes", str(T / "frozen.json"),
                 "--src", str(src))
    s.check("plan-recon: pending 而文件存在=漏回填 / done 而文件缺=假完成",
            c == 1 and "漏回填" in out and "假完成" in out, out[:250])
    (src / "pages" / "P002Detail.tsx").write_text("x", encoding="utf-8")
    plan.write_text(
        "# PLAN — t\n## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    c, out = run("--plan", str(plan), "--routes", str(T / "frozen.json"),
                 "--src", str(src))
    s.check("plan-recon: 状态与文件齐 → PASS",
            c == 0 and "✓" in out, f"rc={c} {out[:150]}")


def test_plan_recon_final(s: Suite, T: Path):
    """1009-15/01/17 终验模式：索引断言+结清规则+状态终验。"""
    T.mkdir(parents=True, exist_ok=True)
    plan = T / "PLAN.md"
    POLICY = "## execution_policy\ndevice_profile: phone_portrait\n"
    plan.write_text(
        "# PLAN — t\n" + POLICY + "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    (T / "frozen.json").write_text(json.dumps(
        [{"id": "p001", "path": "/p001"},
         {"id": "p002", "path": "/p002"}]), encoding="utf-8")
    src = T / "src"
    (src / "pages").mkdir(parents=True)
    (src / "pages" / "P001A.tsx").write_text("x", encoding="utf-8")
    (src / "pages" / "P002B.tsx").write_text("x", encoding="utf-8")
    (T / "pipeline").mkdir(exist_ok=True)
    idx = T / "pipeline" / "evidence_index.jsonl"

    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence_index import src_hash, record
    h = src_hash(src)

    def run_final():
        r = _run("plan-recon.py", "--plan", str(plan), "--routes",
                 str(T / "frozen.json"), "--src", str(src), "--final",
                 "--index", str(idx),
                 "--required", "style-lint,exits-audit,route-audit")
        return r.returncode, r.stdout

    def rec_idx(tool, per_id, verdict, h_, viewport=None):
        # 1012-01 测试同步升级：账行 report_path 指向真实报告文件
        # （内嵌 viewport+src_hash）——视口核对 fail-closed 读得到
        vp = viewport or {"width": 375, "height": 812}
        rp = T / "pipeline" / f"rep_{tool}.json"
        rp.write_text(json.dumps(
            {"src_hash": h_, "viewport": vp, "verdict": verdict}),
            encoding="utf-8")
        idx.open("a", encoding="utf-8").write(json.dumps(
            {"tool": tool, "target": str(src), "src_hash": h_,
             "ids": list(per_id), "per_id": per_id,
             "exit_code": 0 if verdict == "PASS" else 1,
             "coverage": len(per_id), "report_path": str(rp),
             "verdict": verdict, "time": "t"}) + "\n")

    # 反例 1：缺工具行 → FAIL
    c, out = run_final()
    s.check("plan-recon final: 缺工具行 → FAIL（1009-01）",
            c == 1 and "无任何索引记录" in out, out[:200])
    # 反例 2：最新 FAIL → FAIL
    rec_idx("exits-audit", {"p001": "FAIL", "p002": "FAIL"}, "FAIL", h)
    rec_idx("route-audit", {"p001": "PASS", "p002": "PASS"}, "PASS", h)
    rec_idx("style-lint", {"P001A.tsx": "PASS"}, "PASS", h)
    c, out = run_final()
    s.check("plan-recon final: 索引最新 FAIL → FAIL（不出现账本改判）",
            c == 1 and "FAIL" in out, out[:200])
    # 结清规则：同 hash 重跑 PASS → 结清旧 FAIL
    rec_idx("exits-audit", {"p001": "PASS", "p002": "PASS"}, "PASS", h)
    c, out = run_final()
    s.check("plan-recon final: 重跑 PASS 结清旧 FAIL → PASS",
            c == 0 and "✓" in out, out[:200])
    # 反例 3：工程变更未重跑 → FAIL（PASS 行是旧 hash）
    (src / "pages" / "P003C.tsx").write_text("x", encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final: 工程变更后旧 PASS 无效 → FAIL",
            c == 1 and "无任何索引记录" in out, out[:200])
    rec_idx("exits-audit", {"p001": "PASS", "p002": "PASS"}, "PASS",
            src_hash(src))
    rec_idx("route-audit", {"p001": "PASS", "p002": "PASS"}, "PASS",
            src_hash(src))
    rec_idx("style-lint", {"P001A.tsx": "PASS"}, "PASS", src_hash(src))
    # 反例 4：终验时状态 pending → FAIL（无论有无文件）
    plan.write_text(
        "# PLAN — t\n" + POLICY + "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | pending | |\n",
        encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final: 终验时 pending → FAIL（未完成无降级）",
            c == 1 and "未完成且无显式降级" in out, out[:200])
    # 降级后置 = 显式降级 → 该 route 不因状态 FAIL
    plan.write_text(
        "# PLAN — t\n" + POLICY + "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | 降级后置 | 批准:用户 1008 |\n",
        encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final: 显式降级后置 → 不因状态 FAIL",
            c == 0, out[:200])

    # —— 视口一致性断言（1012-01）——
    # F1a：档一致（phone_portrait + 375x812 报告）→ 不误伤
    c, out = run_final()
    s.check("plan-recon final 01: 档一致 → 视口断言不误伤",
            c == 0, out[:200])
    # F1b：PLAN 改 tablet 档，报告仍 375x812 → FAIL
    plan.write_text(
        "# PLAN — t\n## execution_policy\ndevice_profile: tablet\n"
        "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final 01: 报告视口≠device_profile 档 → FAIL",
            c == 1 and "≠ device_profile" in out, out[:250])
    for tool in ("exits-audit", "route-audit"):
        (T / "pipeline" / f"rep_{tool}.json").write_text(json.dumps(
            {"src_hash": src_hash(src),
             "viewport": {"width": 820, "height": 1180}}), encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final 01: 报告视口改 820x1180 → PASS",
            c == 0, out[:200])
    # F2：报告缺 viewport 字段 → FAIL
    for tool in ("exits-audit", "route-audit"):
        (T / "pipeline" / f"rep_{tool}.json").write_text(json.dumps(
            {"src_hash": src_hash(src)}), encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final 01: 报告缺 viewport 字段 → FAIL（不设过渡豁免）",
            c == 1, out[:200])
    # F3a：PLAN 删 execution_policy 节 → FAIL
    plan.write_text(
        "# PLAN — t\n## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final 01: PLAN 无 device_profile → FAIL（fail-closed）",
            c == 1 and "不在契约档位闭集" in out, out[:250])
    # F3b：未知档名 → FAIL
    plan.write_text(
        "# PLAN — t\n## execution_policy\ndevice_profile: ar_phone\n"
        "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    c, out = run_final()
    s.check("plan-recon final 01: 未知档名 → FAIL（闭集外=契约破坏）",
            c == 1 and "不在契约档位闭集" in out, out[:200])
    # F5 真实落账链（explore-walk）为 playwright 用例，挂 test_explore_walk 扩展

    # —— 报告冻结指纹（1012-05）——
    # 先恢复 PLAN 合规态（01 段 F3b 结束时 PLAN 处于 ar_phone 破坏态），
    # 并恢复报告 viewport（01 段 F2 结束时报告处于缺字段破坏态）
    plan.write_text(
        "# PLAN — t\n" + POLICY + "## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n"
        "| p002 | | 2.png | m | 直写 | done | |\n",
        encoding="utf-8")
    for tool in ("exits-audit", "route-audit"):
        (T / "pipeline" / f"rep_{tool}.json").write_text(json.dumps(
            {"src_hash": src_hash(src),
             "viewport": {"width": 375, "height": 812}}), encoding="utf-8")

    def run_final_rf():
        r = _run("plan-recon.py", "--plan", str(plan), "--routes",
                 str(T / "frozen.json"), "--src", str(src), "--final",
                 "--index", str(idx),
                 "--required", "style-lint,exits-audit,route-audit",
                 "--require-frozen")
        return r.returncode, r.stdout
    # F6a 互斥：同给 = exit 1（防一跑既冻结又核对的机制自洗）
    c, out = (lambda r: (r.returncode, r.stdout))(_run(
        "plan-recon.py", "--plan", str(plan), "--routes",
        str(T / "frozen.json"), "--src", str(src), "--final",
        "--index", str(idx),
        "--freeze-fingerprint", "--require-frozen"))
    s.check("plan-recon 05 F6a: freeze 与 require-frozen 同给 → exit 1",
            c == 1 and "互斥" in out, out[:200])
    # F6b 重复 freeze 覆盖 + stdout 显式声明（合法新时点动作）
    r = _run("plan-recon.py", "--plan", str(plan), "--routes",
             str(T / "frozen.json"), "--src", str(src),
             "--freeze-fingerprint")
    fp = src.parent / "pipeline" / "frozen-src-fingerprint.json"
    h05 = src_hash(src)
    s.check("plan-recon 05 F6b: 首次 freeze 落盘（src_hash 同 evidence_index 口径）",
            r.returncode == 0 and fp.is_file()
            and json.loads(fp.read_text(encoding="utf-8"))["src_hash"] == h05,
            r.stdout[:150])
    r = _run("plan-recon.py", "--plan", str(plan), "--routes",
             str(T / "frozen.json"), "--src", str(src),
             "--freeze-fingerprint")
    s.check("plan-recon 05 F6b: 重复 freeze 覆盖 + stdout 声明新时点",
            r.returncode == 0 and "覆盖重写" in r.stdout, r.stdout[:150])
    # F1 指纹一致 → PASS
    c, out = run_final_rf()
    s.check("plan-recon 05 F1: 指纹一致 → --final --require-frozen PASS",
            c == 0, out[:200])
    # F2 冻结后改 src → FAIL（文案含重跑全部工具重出数字）
    (src / "pages" / "P001A.tsx").write_text("x-changed", encoding="utf-8")
    c, out = run_final_rf()
    s.check("plan-recon 05 F2: 冻结后改 src → FAIL（重跑全部工具重出数字）",
            c == 1 and "重跑全部工具重出数字" in out, out[:250])
    # F3 指纹不存在 → FAIL
    fp.unlink()
    c, out = run_final_rf()
    s.check("plan-recon 05 F3: 指纹不存在 → FAIL（未冻结=未完成交付准备）",
            c == 1 and "不存在" in out, out[:250])
    # F4 指纹损坏/缺字段 → FAIL（fail-closed）
    fp.write_text(json.dumps({"time": "t"}), encoding="utf-8")
    c, out = run_final_rf()
    s.check("plan-recon 05 F4: 指纹缺 src_hash 字段 → FAIL（损坏 fail-closed）",
            c == 1 and "损坏或缺 src_hash" in out, out[:250])
    # F5 空 src 树 freeze → FAIL
    empty_src = T / "empty_src"
    empty_src.mkdir(exist_ok=True)
    r = _run("plan-recon.py", "--plan", str(plan), "--routes",
             str(T / "frozen.json"), "--src", str(empty_src),
             "--freeze-fingerprint")
    s.check("plan-recon 05 F5: 空 src 树 freeze → FAIL（空指纹无意义）",
            r.returncode == 1 and "空 src 树" in r.stdout, r.stdout[:150])


def test_dom_truth(s: Suite, T: Path, fast: bool):
    """1009-18 DOM 真实性断言：透明假字/空壳 FAIL，合法隐藏只报告。"""
    if fast:
        return
    T.mkdir(parents=True, exist_ok=True)
    make = lambda d, b: (d.mkdir(parents=True, exist_ok=True),
                         (d / "index.html").write_text(
                             f"<html><body>{b}</body></html>",
                             encoding="utf-8"))
    # 透明假字 + 正常文本 + 合法隐藏（不在期望清单）
    make(T / "dt",
         '<div data-route="/p1">'
         '<span style="color: transparent">9:41 AM</span>'
         '<div>真实可见文本</div>'
         '<div style="visibility: hidden">被隐藏的旧弹窗内容</div></div>')
    (T / "t_bad.json").write_text(json.dumps(
        [{"route": "/p1", "expect_texts": ["9:41 AM", "真实可见文本"]}]),
        encoding="utf-8")
    (T / "t_good.json").write_text(json.dumps(
        [{"route": "/p1", "expect_texts": ["真实可见文本"]}]),
        encoding="utf-8")
    (T / "t_shell.json").write_text(json.dumps(
        [{"route": "/p1", "expect_texts": ["不存在的内容"]}]),
        encoding="utf-8")
    (T / "e_term.json").write_text(json.dumps(
        [{"route": "/p1", "role": "terminal", "required_exits": []}]),
        encoding="utf-8")

    def run(*a):
        r = _run("exits-audit.py", *a)
        return r.returncode, r.stdout

    run("--dist", str(T / "dt"), "--exits", str(T / "e_term.json"),
        "--truth", str(T / "t_bad.json"), "--out", str(T / "tb.json"))
    rep = (json.loads((T / "tb.json").read_text(encoding="utf-8"))
           if (T / "tb.json").is_file() else {})
    tr = next((x for x in rep.get("results", [])
               if x.get("route") == "/p1" and x.get("checks")), None)
    bad = next((x for x in (tr or {}).get("checks", [])
                if x.get("text") == "9:41 AM"), None)
    good = next((x for x in (tr or {}).get("checks", [])
                 if x.get("text") == "真实可见文本"), None)
    s.check("dom-truth: 透明假字 → FAIL（可读性）",
            bad is not None and bad.get("ok") is False
            and "不可读" in (bad.get("fail") or ""), str(bad)[:150])
    s.check("dom-truth: 真实可见文本 → PASS",
            good is not None and good.get("ok") is True, str(good)[:150])
    s.check("dom-truth: 合法隐藏节点只报告待审不 FAIL",
            tr is not None and len(tr.get("suspects_review", [])) >= 1
            and tr.get("fail") is None, str(tr.get("suspects_review"))[:150])
    # 空壳：期望不在 DOM 的文本 → FAIL
    c, out = run("--dist", str(T / "dt"), "--exits", str(T / "e_term.json"),
                 "--truth", str(T / "t_shell.json"), "--out", str(T / "tg.json"))
    rep_g = (json.loads((T / "tg.json").read_text(encoding="utf-8"))
             if (T / "tg.json").is_file() else {})
    ck = next((x2 for x in rep_g.get("results", [])
               for x2 in x.get("checks", [])), None)
    s.check("dom-truth: 空壳（期望文本不存在）→ FAIL",
            c == 1 and ck is not None and ck.get("ok") is False
            and "空壳" in (ck.get("fail") or ""), out[:200])


def test_evidence_chain(s: Suite, T: Path, fast: bool):
    """1009-17/15/01 端到端：真实工具落索引 → 消费端查询（禁手工 fixture）。

    style-lint 链（fast 可跑）：真实跑 style-lint 落索引 → evidence_index
    check 查到 → plan-recon --final 消费 verdict。
    exits 链（fast=False）：真实跑 exits-audit --src 落索引（playwright）。
    """
    T.mkdir(parents=True, exist_ok=True)
    (T / "src" / "pages").mkdir(parents=True)
    (T / "src" / "tokens.ts").write_text(
        'export const colors = { primary: "#1a73e8" };\n'
        'export const fontSize = { md: 16 };', encoding="utf-8")
    (T / "src" / "pages" / "P001A.tsx").write_text(
        'const a = <div style={{fontSize: 16, color: "#1a73e8"}}>x</div>;',
        encoding="utf-8")
    (T / "pipeline").mkdir(exist_ok=True)
    idx = T / "pipeline" / "evidence_index.jsonl"
    plan = T / "PLAN.md"
    plan.write_text(
        "# PLAN — t\n## 页面清单\n"
        "| 页id | 组 | 源图 | 模块 | 策略 | 状态 | 偏差 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| p001 | | 1.png | m | 直写 | done | |\n",
        encoding="utf-8")
    (T / "frozen.json").write_text(json.dumps(
        [{"id": "p001", "path": "/p001"}]), encoding="utf-8")

    # 真实跑 style-lint（合规 → 落 PASS 行）
    r = _run("style-lint.py", "--src", str(T / "src"), "--stack", "react",
             "--tokens", str(T / "src" / "tokens.ts"))
    s.check("evidence-chain: style-lint 真实运行 PASS", r.returncode == 0,
            r.stdout[:150])
    s.check("evidence-chain: 索引行真实落盘",
            idx.is_file() and "style-lint" in idx.read_text(encoding="utf-8"))
    # 消费端 1：evidence_index check 查到该行
    c = _run("evidence_index.py", "check", "--index", str(idx),
             "--src", str(T / "src"), "--required", "style-lint")
    s.check("evidence-chain: evidence_index check 查到真实行 → PASS",
            c.returncode == 0, c.stdout[:150])
    # 消费端 2：plan-recon --final 引用该 verdict
    r2 = _run("plan-recon.py", "--plan", str(plan), "--routes",
              str(T / "frozen.json"), "--src", str(T / "src"), "--final",
              "--index", str(idx), "--required", "style-lint")
    # style-lint 的 verdict 被消费（无其缺口）；exits 维未跑 → 覆盖不足
    # FAIL 是协议正确行为（查不到即 FAIL，1009-15）
    s.check("evidence-chain: plan-recon --final 消费真实 verdict（style-lint 无缺口）",
            "style-lint: 本工程版本" not in r2.stdout, r2.stdout[:200])
    # 反向：src 改出违规 → 重跑 style-lint FAIL → --final FAIL（不出现改判）
    (T / "src" / "pages" / "P001A.tsx").write_text(
        'const a = <div style={{fontSize: 99, color: "#123456"}}>x</div>;',
        encoding="utf-8")
    r3 = _run("style-lint.py", "--src", str(T / "src"), "--stack", "react",
              "--tokens", str(T / "src" / "tokens.ts"))
    s.check("evidence-chain: 违规后重跑 → 索引 FAIL 行（非改判）",
            r3.returncode == 1, r3.stdout[:150])
    r4 = _run("plan-recon.py", "--plan", str(plan), "--routes",
              str(T / "frozen.json"), "--src", str(T / "src"), "--final",
              "--index", str(idx), "--required", "style-lint")
    s.check("evidence-chain: 索引最新 FAIL → --final FAIL",
            r4.returncode == 1, r4.stdout[:150])
    if fast:
        return
    # exits 链端到端（playwright）
    (T / "exits.json").write_text(json.dumps(
        [{"route": "/detail", "role": "secondary",
          "required_exits": [{"intent": "nav-back",
                              "expect_url_contains": "/map-home"}]}]),
        encoding="utf-8")
    dist = T / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        '<html><body><div data-route="/detail">detail'
        '<button data-intent="nav-back" '
        "onclick=\"location.href='/map-home'\">back</button></div>"
        "</body></html>", encoding="utf-8")
    r5 = _run("exits-audit.py", "--dist", str(dist), "--exits",
              str(T / "exits.json"), "--src", str(T / "src"),
              "--out", str(T / "ex.json"))
    s.check("evidence-chain: exits-audit 真实运行落索引（--src）",
            r5.returncode == 0, r5.stdout[:150])
    rows = [json.loads(x) for x in
            idx.read_text(encoding="utf-8").splitlines() if x.strip()]
    ex_row = [x for x in rows if x.get("tool") == "exits-audit"]
    same_domain = bool(ex_row) and all(
        x.get("target").endswith("src") for x in ex_row)
    s.check("evidence-chain: exits 行 target/hash 与消费端同域"
            "（真实端到端）", bool(ex_row) and same_domain,
            str([x.get("target") for x in ex_row]))


def test_report_hash(s: Suite, T: Path, fast: bool):
    """1012-06 报告内嵌哈希校验：record 拒绝路径 + latest_valid 双校验。"""
    T.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(SCRIPTS))
    from evidence_index import (record, latest_valid, src_hash,
                                RecordRejected)
    src = T / "src"
    (src / "pages").mkdir(parents=True)
    (src / "pages" / "P001A.tsx").write_text("x", encoding="utf-8")
    idx = T / "pipeline" / "evidence_index.jsonl"
    h = src_hash(src)

    def wrep(name, body):
        p = T / name
        p.write_text(json.dumps(body), encoding="utf-8")
        return p

    # F1 一致 → 入账
    rp = wrep("ok.json", {"src_hash": h})
    row = record(idx, "t-tool", str(src), src, ["a"], {"a": "PASS"},
                 0, 1, str(rp))
    s.check("report-hash F1: 报告内嵌哈希一致 → 入账成功",
            idx.is_file() and row.get("verdict") == "PASS", str(row)[:120])
    # F2 不一致（旧报告内容配新哈希）→ RecordRejected
    (src / "pages" / "P002B.tsx").write_text("y", encoding="utf-8")
    h2 = src_hash(src)
    rp2 = wrep("old.json", {"src_hash": h})  # 报告仍是旧工程版本内容
    rejected = False
    try:
        record(idx, "t-tool", str(src), src, ["a"], {}, 0, 1, str(rp2))
    except RecordRejected:
        rejected = True
    s.check("report-hash F2: 旧报告内容配新哈希 → 拒绝（RecordRejected）",
            rejected, "")
    # F3 缺字段 → 拒绝（旧格式不设过渡豁免）
    rp3 = wrep("nofield.json", {"verdict": "PASS"})
    rejected = False
    try:
        record(idx, "t-tool", str(src), src, ["a"], {}, 0, 1, str(rp3))
    except RecordRejected:
        rejected = True
    s.check("report-hash F3: 报告缺内嵌 src_hash → 拒绝（旧格式拒绝）",
            rejected, "")
    # F4 报告不存在 → 拒绝（先写后记的顺序约定）
    rejected = False
    try:
        record(idx, "t-tool", str(src), src, ["a"], {}, 0, 1,
               str(T / "ghost.json"))
    except RecordRejected:
        rejected = True
    s.check("report-hash F4: 报告文件不存在 → 拒绝", rejected, "")
    # F5 端到端：同键两行账，最新行报告被改坏 → latest_valid None
    # 且**不回退次旧行**（回退=删新报告复活旧 PASS 的攻击面）
    rp5old = wrep("rep5old.json", {"src_hash": h2})
    record(idx, "t2", str(src), src, ["a"], {"a": "PASS"}, 0, 1, str(rp5old))
    rp5new = wrep("rep5new.json", {"src_hash": h2})
    record(idx, "t2", str(src), src, ["a"], {"a": "PASS"}, 0, 1, str(rp5new))
    row5 = latest_valid(idx, h2, "t2", str(src))
    s.check("report-hash F5a: 账行+报告一致 → latest_valid 命中最新行",
            row5 is not None, str(row5)[:100])
    rp5new.write_text(json.dumps({"src_hash": "deadbeef"}),
                      encoding="utf-8")
    row5b = latest_valid(idx, h2, "t2", str(src))
    s.check("report-hash F5b: 最新报告内嵌被改 → None（禁回退次旧行）",
            row5b is None, str(row5b)[:100])
    # F6 style-lint 默认落盘（--out 默认值必死）+ 内嵌哈希
    wsrc = T / "w" / "src"
    (wsrc / "pages").mkdir(parents=True, exist_ok=True)
    (wsrc / "tokens.ts").write_text(
        'export const colors = { primary: "#1a73e8" };', encoding="utf-8")
    (wsrc / "pages" / "P001A.tsx").write_text(
        'const a = <div style={{color: "#1a73e8"}}>x</div>;',
        encoding="utf-8")
    r = _run("style-lint.py", "--src", str(wsrc))
    rep6 = T / "w" / "pipeline" / "style-lint_report.json"
    rep = json.loads(rep6.read_text(encoding="utf-8")) if rep6.is_file() else {}
    s.check("report-hash F6: style-lint 默认落盘 pipeline/style-lint_report.json"
            " 且内嵌 src_hash",
            r.returncode == 0 and rep.get("src_hash") == src_hash(wsrc),
            f"rc={r.returncode} rep={str(rep)[:100]}")
    # 调用方两层 except 分层在位（RecordRejected 置 1 / Exception 旧语义）
    layered = 0
    for tool in ("e2e-smoke", "route-audit", "exits-audit", "explore-walk",
                 "style-lint"):
        text = (SCRIPTS / f"{tool}.py").read_text(encoding="utf-8")
        if "except RecordRejected" in text and "except Exception" in text:
            layered += 1
    s.check("report-hash F7: 五工具调用方两层 except 分层在位"
            "（拒账禁被裸 except 吞——定标点名①）",
            layered == 5, f"layered={layered}/5")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true",
                    help="跳过需 playwright 的用例")
    args = ap.parse_args()
    T = Path(tempfile.mkdtemp(prefix="pipe_tests_"))
    s = Suite()
    test_plan_io(s, T / "p")
    test_intake(s, T / "i")
    test_route_audit(s, T / "r", fast=args.fast)
    test_exits_audit(s, T / "e", fast=args.fast)
    test_e2e_assert(s, T / "m", fast=args.fast)
    test_explore_walk(s, T / "w", fast=args.fast)
    test_dom_truth(s, T / "dt2", fast=args.fast)
    test_evidence_chain(s, T / "ec", fast=args.fast)
    test_report_hash(s, T / "rh", fast=args.fast)
    test_style_lint(s, T / "s")
    test_style_lint_vue(s, T / "sv")
    test_plan_recon(s, T / "pr")
    test_plan_recon_final(s, T / "pf")
    test_contracts_lint(s, T / "c")
    test_device_probe(s, T / "dp", fast=args.fast)
    test_setup_env(s)
    print("\n" + ("ALL PASS" if s.ok else "SOME FAIL"))
    return 0 if s.ok else 1


if __name__ == "__main__":
    sys.exit(main())
