#!/usr/bin/env python3
"""e2e-smoke — 主流程物理点击冒烟（管线⑧硬 gate）。

断言纪律（八轮评审教训固化）：
  - 关键流程**普通物理点击**（playwright click 序列），禁 force:true 与
    JS .click()——两者会绕过遮挡/层级/事件委托，掩盖死按钮（实测 p087
    遮挡不可点被 JS click 验证放行）
  - **变化检测**：点击前后截图 diff 作为辅助信号写入报告（diff=0 提示
    死交互嫌疑）；硬判据只认 expect_* 断言——diff≠0 不等于 PASS
  - **无 expect 判 FAIL**（1008-02）：步骤缺 expect_* = 断言缺失，
    空断言 all([]) 恒真已封堵——每步必须有明确预期
  - **首访链第 0 步**：主流程链至少一条 goto('/') 起步并 expect_url
    断言落点 = sitemap「入口契约」root 落点（规则在 wiring-prompt）
  - **双证据**：DOM 断言（visible/hidden/url）+ 每步截图（交视觉裁判）
  - **修复后重跑**：--only <id,id> 支持子集重跑，修复声明必须附结果

steps.json 格式：
  [{"id":"s1","name":"打开登录页","goto":"/登录"},
   {"id":"s2","name":"点击登录","click":"text=微信一键登录",
    "expect_url":"/地图导览主页"},
   {"id":"s3","name":"弹窗出现","click":"text=开启AI智游",
    "expect_visible":"提示"},
   {"id":"s4","name":"取消关闭","click":"text=取消",
    "expect_hidden":"开启龙伴游，请先购买"}]

用法：
  python e2e-smoke.py --dist <构建目录或URL> --steps steps.json \
      [--out smoke_report.json] [--only s2,s4]
Exit 0 = 全过；1 = 有失败。
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class SPAHandler(SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        if code == 404:
            index = Path(self.directory) / "index.html"  # type: ignore
            if index.is_file():
                body = index.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        super().send_error(code, message, explain)

    def log_message(self, *a):
        pass



# 验收视口（1010-04）：默认 375x812=phone_portrait 档兜底；
# 由 PLAN execution_policy.device_profile 决定传参（主会话读 PLAN 后传 --viewport）
DEFAULT_VIEWPORT = {"width": 375, "height": 812}


def parse_viewport(s: str | None) -> dict:
    if not s:
        return dict(DEFAULT_VIEWPORT)
    w, _, h = s.strip().lower().partition("x")
    if not (w.isdigit() and h.isdigit() and int(w) > 0 and int(h) > 0):
        raise SystemExit(f'--viewport 格式应为 "WxH"，收到: {s!r}')
    return {"width": int(w), "height": int(h)}

def start_spa(root: Path):
    handler = functools.partial(SPAHandler, directory=str(root))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def shot_diff_ratio(a_bytes: bytes, b_bytes: bytes) -> float:
    """辅助信号：两次视口截图的**像素级**差异占比。

    注意：不能比 PNG 原始字节——压缩噪声会让同一画面 diff≈0.98
    （实测教训）。解码为像素后按通道差 >30 判变。"""
    try:
        import io
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(io.BytesIO(a_bytes)).convert("RGB"),
                       dtype=float)
        b = np.asarray(Image.open(io.BytesIO(b_bytes)).convert("RGB"),
                       dtype=float)
        if a.shape != b.shape:
            return 1.0
        dist = np.sqrt(((a - b) ** 2).sum(axis=2))
        return round(float((dist > 30).mean()), 4)
    except Exception:
        return -1.0  # 比对失败时放弃辅助信号，不误报


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dist", required=True, help="构建目录或 http(s) URL")
    ap.add_argument("--steps", required=True, help="主流程步骤 json")
    ap.add_argument("--viewport", default=None,
                    help='浏览器视口 "WxH"（默认 375x812；由 PLAN '
                         'device_profile 档决定，1010-04）')
    ap.add_argument("--out", default="smoke_report.json")
    ap.add_argument("--shots", default=None, help="截图目录")
    ap.add_argument("--only", default=None, help="仅重跑指定步骤 id（逗号分隔）")
    ap.add_argument("--src", default=None,
                    help="工程 src 目录（证据索引 target/hash 对象，1009-17）")
    args = ap.parse_args()

    steps = json.loads(Path(args.steps).read_text(encoding="utf-8"))
    if args.only:
        keep = {x.strip() for x in args.only.split(",")}
        steps = [s for s in steps if s["id"] in keep]
        if not steps:
            print("e2e-smoke: --only 过滤后无步骤"); return 1
    shots_dir = Path(args.out).parent / "smoke_shots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    srv = None
    if args.dist.startswith("http"):
        base = args.dist.rstrip("/")
    else:
        root = Path(args.dist).resolve()
        if not (root / "index.html").is_file():
            print(f"dist 缺 index.html: {root}"); return 1
        srv = start_spa(root)
        base = f"http://127.0.0.1:{srv.server_address[1]}"

    from playwright.sync_api import sync_playwright
    results: list[dict] = []
    fails: list[str] = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=parse_viewport(args.viewport))
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        for st in steps:
            sid, name = st["id"], st.get("name", st["id"])
            rec: dict = {"id": sid, "name": name}
            try:
                if "goto" in st:
                    page.goto(base + st["goto"], wait_until="domcontentloaded",
                              timeout=20000)
                if "click" in st:
                    before = page.screenshot()
                    # 物理点击：playwright click 走真实输入序列；
                    # 显式禁 force —— 遮挡/不可点必须 FAIL 而非绕过
                    page.click(st["click"], timeout=8000)
                    page.wait_for_timeout(600)
                    after = page.screenshot()
                    rec["diff_hint"] = round(
                        shot_diff_ratio(before, after), 4)
                    # 容差判定：抗锯齿/光标渲染有 ~0.1% 底噪，
                    # diff < 0.1% 视为画面无变化；diff<0（比对失败）
                    # 不提示嫌疑——放弃辅助信号≠死交互证据
                    if 0 <= rec["diff_hint"] < 0.001:
                        rec["diff_note"] = ("点击后画面无实质变化——死交互嫌疑，"
                                            "请人工核对（辅助信号非判据）")
                else:
                    page.wait_for_timeout(400)

                rec["url"] = page.url
                if "expect_url" in st:
                    rec["url_ok"] = st["expect_url"] in page.url
                if "expect_visible" in st:
                    loc = page.get_by_text(st["expect_visible"]).first
                    rec["visible_ok"] = loc.is_visible()
                if "expect_hidden" in st:
                    loc = page.get_by_text(st["expect_hidden"])
                    rec["hidden_ok"] = loc.count() == 0 or not loc.first.is_visible()
                if "expect_pinned_bottom" in st:
                    # 1012-07 几何贴底：底部固定元素（TabBar/输入栏/提交条）
                    # 元素底缘 ∈ [vh-tol, vh+tol]——收银台按钮悬空/TabBar
                    # 漂移类几何缺陷的机器断言（app2 实锤防线）
                    sel = st["expect_pinned_bottom"]
                    vh = page.evaluate("window.innerHeight")  # 实际视口高（禁硬编码，--viewport 变体兼容）
                    tol = 8  # px（1012-07 测试角色定标建议值）
                    loc = page.locator(sel).first
                    box = (loc.bounding_box(timeout=2000)
                           if page.locator(sel).count() else None)
                    if box is None:
                        rec["pinned_ok"] = False
                        rec["pinned_error"] = (
                            f"expect_pinned_bottom: {sel} 未匹配到元素"
                            "（bounding_box=None）——禁跳过")
                    else:
                        bottom = box["y"] + box["height"]  # bounding_box 无 bottom 键，自算
                        rec["pinned_ok"] = (vh - tol <= bottom <= vh + tol)
                        if not rec["pinned_ok"]:
                            rec["pinned_error"] = (
                                f"expect_pinned_bottom: {sel} bottom="
                                f"{bottom:.1f} 超出贴底区间 "
                                f"[{vh - tol}, {vh + tol}]（vh={vh}）"
                                "——悬空/漂移（transform 祖先降级亦属真实缺陷不豁免）")

                # 空断言漏洞封堵（1008-02）：无任何 expect_* 的步骤
                # checks 恒空 → all([])=True 恒 PASS——"没写预期"不是
                # 宽容，是断言缺失，必须 FAIL（否则工具忠实执行空预期，
                # 执行端写错/不写预期都照放行）
                has_expect = any(k in st for k in (
                    "expect_url", "expect_visible", "expect_hidden",
                    "expect_pinned_bottom"))  # 1012-07：漏扩则带此断言的步骤被判无断言恒 FAIL
                checks = [v for k, v in rec.items() if k.endswith("_ok")]
                shot = shots_dir / f"step_{sid}.png"
                page.screenshot(path=str(shot))
                rec["shot"] = str(shot)
                rec["errors"] = list(errors)
                rec["ok"] = (bool(all(checks)) and not errors
                             and has_expect)
                if not has_expect:
                    rec["expect_error"] = ("步骤无 expect_* 断言——空断言"
                                           "恒真漏洞已封堵（1008-02），"
                                           "补预期后重跑")
            except Exception as exc:
                rec.update(ok=False, error=str(exc)[:300])
            results.append(rec)
            mark = "PASS" if rec.get("ok") else "FAIL"
            print(f"[{mark}] {sid} {name}"
                  + (f" | {rec.get('error', '')[:120]}" if not rec.get("ok")
                     and rec.get("error") else ""))
            if not rec.get("ok"):
                fails.append(sid)
        browser.close()
    if srv is not None:
        srv.shutdown()

    exit_code = 1 if fails else 0
    # 1012-06 统一顺序：先写报告（内嵌 src_hash）→ 再 record（读盘校验）
    report = {"total": len(steps), "fails": fails, "results": results,
              "viewport": parse_viewport(args.viewport)}  # 1012-01：实际生效视口入报告（同源 parse，抓静默兜底）
    eng_src = (Path(args.src).resolve()  # 1012-01 裁定④：target resolve 对齐消费端
               if hasattr(args, "src") and args.src
               else None)
    if eng_src is not None and eng_src.exists():
        from evidence_index import src_hash
        report["src_hash"] = src_hash(eng_src)
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        from evidence_index import record, RecordRejected
        per_id = {r["id"]: ("PASS" if r.get("ok") else "FAIL")
                  for r in results}
        if eng_src is None:
            # 1012-01 裁定③：无 --src 时 hash 对象无法与消费端对齐——
            # fail-closed 跳过落账（对齐 exits-audit 先例），禁落 cwd 脏哈希行
            print("e2e-smoke: 未提供 --src，跳过证据索引落账（fail-closed）",
                  file=sys.stderr)
        else:
            idx = eng_src.parent / "pipeline" / "evidence_index.jsonl"
            record(idx, "e2e-smoke", str(eng_src),
                   eng_src if eng_src.exists() else Path("."),
                   list(per_id), per_id, exit_code, len(results), str(args.out))
    except RecordRejected as exc:
        # 证据本体不可信：与断言结果取或，禁静默（1012-06 定标点名①）
        print(f"e2e-smoke: 证据拒账，exit 置 1——{exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        pass  # 索引 IO 失败不掩盖主判定（既有豁免语义）
    print(f"e2e-smoke: {len(steps) - len(fails)}/{len(steps)} PASS"
          + (f"; FAIL: {fails}" if fails else "")
          + f"; shots: {shots_dir}")
    return exit_code  # 1012-06：拒账时取或置 1


if __name__ == "__main__":
    sys.exit(main())
