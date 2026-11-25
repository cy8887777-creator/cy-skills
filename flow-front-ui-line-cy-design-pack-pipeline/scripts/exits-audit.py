#!/usr/bin/env python3
"""exits-audit — 出口完整性反向断言（管线⑨自测 + ⑩验收，1008-04/1009-14）。

存在性遍历只点"存在的 intent"，证伪不了"该有的在不在"——实测
venue-intro 返回箭头是纯装饰 DIV、全页 10 个 intent 零出口=死端，
交付报告却声称"二级页返回途径全通"。本脚本按④冻结清单的**角色
机器真值**反向断言必备出口（1009-14 硬断言兑现）：

  role=secondary    → required_exits 必含返回类出口，且**返回类出口必须
                      声明 expect_url_contains（实际落点）**——返回弹
                      "暂未开通"Toast 不是回退（死出口）；
  role=tab_landing  → required_exits 须声明 tab 全件清单，断言集合齐全
                      且逐一点击切换生效；
  role=modal_host   → required_exits 须含开与关一对；
  role=terminal     → 豁免（合法终止页：支付结果/识别结果等）；
  role 缺失 / 非 terminal 而 required_exits 为空 / 出口缺预期
                    → **配置不合规 FAIL**（真值由④产出时即必填）。

对审输入纪律：预期只有两种合法形态——expect_url_contains（实际落点）
与 expect_overlay（浮层出现）；Toast 仅作信息记录，**不构成出口判定**
（返回弹"暂未开通"=死出口）。

两态覆盖（1009-14）：
  - 深链直达态：直接 goto 该页测出口与兜底（无历史可 back 时禁死端）；
  - 站内进入态：页条目声明 `enter_via`（可复现进入步骤：入口路由+点击
    序列），脚本按声明走完再测出口——未声明则记"未声明站内态"信息。

exits.json（由④冻结清单产出，机器真值）：
  [{"route": "/venue-intro", "role": "secondary",
    "required_exits": [{"intent": "nav-back",
                        "expect_url_contains": "/map-home"}],
    "enter_via": [{"goto": "/map-home", "click": "open-venue-intro"}]},
   {"route": "/photo-result", "role": "terminal", "required_exits": []}]

用法：
  python exits-audit.py --dist <构建目录或URL> --exits exits.json \
      [--out exits_report.json]
Exit 0 = 全过；1 = 有 FAIL（WARN 不影响 exit）。
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

VALID_ROLES = {"secondary", "tab_landing", "modal_host", "terminal"}
BACK_HINTS = ("nav-back", "go-back", "back")


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


def validate_config(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    """配置校验（不需要浏览器）：role 合法性 + 按 role 的必填约束 +
    逐出口预期必填。返回 (可跑列表, 配置违规列表)。"""
    ok, bad = [], []
    for pg in pages:
        route, role = pg.get("route"), pg.get("role")
        probs: list[str] = []
        if role not in VALID_ROLES:
            bad.append({"route": route, "role": role,
                        "fail": f"role 缺失或非法: {role!r}"
                        "（角色真值必须由④产出）"})
            continue
        req = pg.get("required_exits") or []
        if role != "terminal" and not req:
            bad.append({"route": route, "role": role,
                        "fail": "非 terminal 页 required_exits 为空"
                        "——出口缺失即死端（1009-14 配置不合规）"})
            continue
        if role == "secondary" and not pg.get("nav_back_exempt", False):
            has_back = any("back" in (e.get("intent") or "").lower()
                           for e in req)
            if not has_back:
                probs.append("secondary 页 required_exits 须含返回类出口")
            for e in req:
                if "back" in (e.get("intent") or "").lower() and \
                        not e.get("expect_url_contains"):
                    probs.append(f"返回类出口 {e.get('intent')!r} 必须声明 "
                                 "expect_url_contains（实际落点）——返回弹 "
                                 "Toast 不是回退")
        if role == "tab_landing":
            tabs = [e for e in req
                    if (e.get("intent") or "").startswith("tab-")]
            if len(req) < 2 or not tabs:
                probs.append("tab_landing 页 required_exits 须声明 tab "
                             "全件清单（tab-* intent 逐个列出）")
        if role == "modal_host":
            joined = " ".join((e.get("intent") or "") for e in req)
            if not ("open" in joined or "show" in joined) or \
                    not ("close" in joined or "cancel" in joined
                         or "hide" in joined):
                probs.append("modal_host 页 required_exits 须含开与关一对")
        for e in req:
            if not e.get("expect_url_contains") and \
                    not e.get("expect_overlay"):
                probs.append(f"出口 {e.get('intent')!r} 缺预期"
                             "（expect_url_contains/expect_overlay 至少"
                             "其一；Toast 不构成出口判定）")
        if probs:
            bad.append({"route": route, "role": role,
                        "fail": "；".join(probs)})
            continue
        ok.append(pg)
    return ok, bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dist", required=True, help="构建目录或 http(s) URL")
    ap.add_argument("--exits", required=True,
                    help="出口真值 json（④冻结清单产出：role+required_exits）")
    ap.add_argument("--truth", default=None,
                    help="应可见文案合同 json（1009-18 DOM 真实性断言）")
    ap.add_argument("--src", default=None,
                    help="工程 src 目录（证据索引 target/hash 对象，"
                         "1009-17 三元组统一；默认用 dist 推导）")
    ap.add_argument("--viewport", default=None,
                    help='浏览器视口 "WxH"（默认 375x812；由 PLAN '
                         'device_profile 档决定，1010-04）')
    ap.add_argument("--out", default="exits_report.json")
    args = ap.parse_args()

    pages = json.loads(Path(args.exits).read_text(encoding="utf-8"))
    if not pages:
        print("exits-audit: exits 清单为空——nothing to audit"); return 1

    # 配置预校验（不启动浏览器）
    results: list[dict] = []
    fails: list[str] = []
    warns: list[str] = []
    browsable, bad = validate_config(pages)
    results.extend(bad)
    for b in bad:
        fails.append(b["route"])
        print(f"[FAIL] {b['route']} (role={b['role']!r}) 配置不合规: {b['fail']}")
    pages = browsable

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
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=parse_viewport(args.viewport))
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def has_overlay() -> bool:
            return page.evaluate("""() => [...document.querySelectorAll('body *')]
              .some(e => { const r = e.getBoundingClientRect();
                if (r.width < 100 || r.height < 80) return false;
                const cs = getComputedStyle(e);
                if (cs.position !== 'fixed' && cs.position !== 'absolute') return false;
                if (cs.display === 'none' || cs.visibility === 'hidden'
                        || Number(cs.opacity) === 0) return false;
                return (Number(cs.zIndex) || 0) >= 10; })""")

        def audit_exits(pg: dict, mode: str, rec: dict, reset_nav=None) -> None:
            """单态出口断言（深链态/站内态共用）。
            [1010-09 ⑨站修订 D-034] 每个出口断言前重置导航回原页（reset_nav）——
            原实现顺序点击不回原页，跳页出口（nav-back/tab/navigate）点击后同页
            其余出口全部误判"出口缺失"（结构性误报，非工程缺陷）。重置不弱化
            检测：断言仍为物理点击+URL/overlay 双证据。"""
            for ex in pg.get("required_exits", []):
                intent = ex.get("intent")
                item: dict = {"intent": intent, "mode": mode}
                if reset_nav is not None:
                    try:
                        reset_nav()
                        page.wait_for_timeout(650)
                    except Exception as exc:
                        item.update(ok=False,
                                    fail=f"导航重置失败: {str(exc)[:80]}")
                        rec["exits"].append(item)
                        fails.append(f"{pg['route']}:{intent}({mode})")
                        continue
                el = page.query_selector(f'[data-intent="{intent}"]')
                if el is None:
                    item.update(ok=False, fail="出口缺失（该有的 intent 不在）")
                    rec["exits"].append(item)
                    fails.append(f"{pg['route']}:{intent}({mode})")
                    continue
                vis = page.evaluate(
                    """(sel) => { const e = document.querySelector(sel);
                         if (!e) return false;
                         const r = e.getBoundingClientRect();
                         const cs = getComputedStyle(e);
                         return r.width > 0 && r.height > 0
                           && cs.display !== 'none'
                           && cs.visibility !== 'hidden'
                           && Number(cs.opacity) !== 0; }""",
                    f'[data-intent="{intent}"]')
                if not vis:
                    item.update(ok=False, fail="出口存在但不可见（隐藏/零尺寸）")
                    rec["exits"].append(item)
                    fails.append(f"{pg['route']}:{intent}({mode})")
                    continue
                before_url = page.url
                before_overlay = has_overlay()
                try:
                    el.scroll_into_view_if_needed(timeout=2000)
                    el.click(timeout=6000)  # 物理点击：禁 force
                    page.wait_for_timeout(800)
                except Exception as exc:
                    item.update(ok=False, mode=mode,
                                fail=f"点击失败: {str(exc)[:80]}")
                    rec["exits"].append(item)
                    fails.append(f"{pg['route']}:{intent}({mode})")
                    continue
                after_url = page.url
                expect_url = ex.get("expect_url_contains")
                expect_overlay = ex.get("expect_overlay")
                if expect_url:
                    ok = expect_url in after_url
                    item.update(ok=ok, url=after_url,
                                fail=None if ok else
                                f"落点不符: 期望含 {expect_url!r},"
                                f" 实际 {after_url}")
                    if not ok:
                        fails.append(f"{pg['route']}:{intent}({mode})")
                elif expect_overlay:
                    ok = has_overlay() > before_overlay
                    item.update(ok=ok, url=after_url,
                                fail=None if ok else "期望浮层未出现")
                    if not ok:
                        fails.append(f"{pg['route']}:{intent}({mode})")
                else:  # 配置校验已拦，此处兜底
                    item.update(ok=False, fail="出口缺预期（配置校验漏网）")
                    fails.append(f"{pg['route']}:{intent}({mode})")
                if errors:
                    item["console_errors"] = list(errors)
                    item["ok"] = False
                    item["fail"] = item.get("fail") or "console/pageerror"
                    fails.append(f"{pg['route']}:{intent}({mode})")
                rec["exits"].append(item)

        for pg in pages:
            route, role = pg.get("route"), pg.get("role")
            rec: dict = {"route": route, "role": role, "exits": []}
            if role == "terminal":
                rec["skip"] = "合法终止页豁免"
                results.append(rec)
                print(f"[SKIP] {route} (terminal 豁免)")
                continue
            try:
                # 态 1：深链直达
                page.goto(base + route, wait_until="domcontentloaded",
                          timeout=20000)
                page.wait_for_timeout(700)
                errors.clear()

                def _reset_deep():
                    page.goto(base + route, wait_until="domcontentloaded",
                              timeout=20000)

                audit_exits(pg, "deep-link", rec, reset_nav=_reset_deep)
                # 态 2：站内进入（仅当声明 enter_via）
                enter = pg.get("enter_via") or []
                if enter:
                    page.goto(base + (enter[0].get("goto") or "/"),
                              wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(600)
                    ok_enter = True
                    for st in enter:
                        ci = st.get("click")
                        if not ci:
                            continue
                        cel = page.query_selector(f'[data-intent="{ci}"]')
                        if cel is None:
                            ok_enter = False
                            rec["enter_fail"] = f"进入步骤元素缺失: {ci}"
                            break
                        try:
                            cel.scroll_into_view_if_needed(timeout=2000)
                            cel.click(timeout=6000)
                            page.wait_for_timeout(700)
                        except Exception as exc:
                            ok_enter = False
                            rec["enter_fail"] = f"进入步骤点击失败 {ci}: {str(exc)[:60]}"
                            break
                    if ok_enter:
                        rec["enter_ok"] = True

                        def _reset_inapp():
                            page.goto(base + (enter[0].get("goto") or "/"),
                                      wait_until="domcontentloaded",
                                      timeout=20000)
                            page.wait_for_timeout(500)
                            for st in enter:
                                ci = st.get("click")
                                if not ci:
                                    continue
                                cel = page.query_selector(
                                    f'[data-intent="{ci}"]')
                                if cel is None:
                                    raise RuntimeError(f"进入步骤缺失 {ci}")
                                cel.scroll_into_view_if_needed(timeout=2000)
                                cel.click(timeout=6000)
                                page.wait_for_timeout(650)

                        audit_exits(pg, "in-app", rec, reset_nav=_reset_inapp)
                    else:
                        fails.append(f"{route}: 站内态进入失败")
            except Exception as exc:
                rec["fail"] = str(exc)[:200]
                fails.append(route)
            results.append(rec)
            n_bad = (1 if rec.get("fail") or rec.get("enter_fail") else
                     sum(1 for x in rec.get("exits", [])
                         if x.get("ok") is False))
            print(f"[{'FAIL' if n_bad else 'PASS'}] {route} ({role}) "
                  f"出口 {len(rec.get('exits', []))} 项")
        # ---- DOM 真实性断言（1009-18，应可见文案合同驱动）----
        if args.truth:
            try:
                truths = json.loads(Path(args.truth).read_text(
                    encoding="utf-8"))
            except Exception as exc:
                fails.append(f"dom-truth 配置解析失败: {str(exc)[:100]}")
                truths = []
            for te in truths:
                route = te.get("route")
                rec_t: dict = {"route": route, "checks": []}
                try:
                    page.goto(base + route, wait_until="domcontentloaded",
                              timeout=20000)
                    page.wait_for_timeout(900)
                    for text in te.get("expect_texts", []):
                        probe = page.evaluate(
                            """(t) => {
                              const all = [...document.querySelectorAll('body *')]
                                .filter(e => (e.textContent || '').includes(t)
                                  && ![...e.children].some(c =>
                                      (c.textContent||'').includes(t)));
                              if (!all.length) return {found: false};
                              const e = all[0];
                              const cs = getComputedStyle(e);
                              const r = e.getBoundingClientRect();
                              return {found: true, color: cs.color,
                                      vis: cs.visibility, disp: cs.display,
                                      opacity: cs.opacity,
                                      w: r.width, h: r.height};
                            }""", text)
                        item: dict = {"text": text}
                        if not probe.get("found"):
                            item.update(ok=False,
                                        fail="空壳：声明应可见但 DOM 无文本")
                            fails.append(f"dom-truth {route}:{text}")
                        else:
                            unreadable = (
                                "transparent" in probe["color"]
                                or "rgba(0, 0, 0, 0)" in probe["color"]
                                or probe["vis"] == "hidden"
                                or probe["disp"] == "none"
                                or float(probe["opacity"] or 1) == 0
                                or probe["w"] < 1 or probe["h"] < 1)
                            if unreadable:
                                item.update(ok=False,
                                            fail=f"不可读（透明假字/隐藏/"
                                            f"零尺寸）: {probe}")
                                fails.append(f"dom-truth {route}:{text}")
                            else:
                                item.update(ok=True)
                        rec_t["checks"].append(item)
                    # 隐藏可疑节点：报告待审，不 FAIL
                    suspects = page.evaluate(
                        """() => [...document.querySelectorAll('body *')]
                          .filter(e => {
                            const cs = getComputedStyle(e);
                            const t = (e.textContent||'').trim();
                            if (!t || e.children.length) return false;
                            const tr = cs.color.includes('rgba(0, 0, 0, 0)')
                              || cs.color === 'transparent';
                            return tr || cs.visibility === 'hidden'
                              || Number(cs.opacity) === 0; })
                          .map(e => ({txt: (e.textContent||'').trim().slice(0,24),
                                      cls: (e.className||'').toString().slice(0,40)}))""")
                    if suspects:
                        rec_t["suspects_review"] = suspects
                        warns.append(f"dom-truth {route}: {len(suspects)} 个"
                                     "隐藏文本节点待审")
                except Exception as exc:
                    rec_t["fail"] = str(exc)[:200]
                    fails.append(f"dom-truth {route}")
                results.append(rec_t)
                n_bad = sum(1 for x in rec_t.get("checks", [])
                            if x.get("ok") is False)
                print(f"[{'FAIL' if n_bad or rec_t.get('fail') else 'PASS'}] "
                      f"dom-truth {route} 文案 {len(rec_t.get('checks', []))} 条")
        browser.close()
    if srv is not None:
        srv.shutdown()

    exit_code = 1 if fails else 0
    # per_id 聚合（三审修正）：truth checks 的 FAIL 也计入该 route
    per_id: dict = {}
    for r in results:
        route = r.get("route")
        if route is None:
            continue  # 无 route 的配置违规条目：不进 per_id（由
                      # exit_code 兜底整场 verdict）
        bad = (r.get("fail") or r.get("enter_fail")
               or any(x.get("ok") is False
                      for x in r.get("exits", []))
               or any(x.get("ok") is False
                      for x in r.get("checks", [])))
        prev = per_id.get(route)
        per_id[route] = "FAIL" if (bad or prev == "FAIL") else "PASS"
    # --src 缺失（或 http）时不落索引——hash 对象无法与消费端
    # 一致，落了也是查不到的死行（fail-closed，复审#6）
    eng_src = (Path(args.src).resolve() if args.src
               else (Path(args.dist).resolve().parent / "src"
                     if not args.dist.startswith("http")
                     and (Path(args.dist).resolve().parent / "src").is_dir()
                     else None))
    # 1012-06 统一顺序：先写报告（内嵌 src_hash）→ 再 record（读盘校验）
    report = {"viewport": parse_viewport(args.viewport),  # 1012-01
    "total": len(pages) + len([r for r in results if r.get("fail")
                                         and "配置" in str(r.get("fail", ""))]),
              "fails": fails, "warns": warns, "results": results}
    if eng_src is not None and eng_src.exists():
        from evidence_index import src_hash
        report["src_hash"] = src_hash(eng_src)
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        from evidence_index import record, RecordRejected
        # 三元组统一（1009-17）：target=str(src)、hash(src)、
        # 索引=工程根/pipeline/evidence_index.jsonl——与消费端
        # check_all/plan-recon 完全一致（spec review：原 dist 推导
        # 与消费端 src 推导两树必然不同=真实管线永远查不到）
        if eng_src is None or not eng_src.exists():
            print("exits-audit: 未提供有效 --src——跳过证据索引"
                  "（fail-closed：该运行不计入门禁索引）")
        else:
            idx = eng_src.parent / "pipeline" / "evidence_index.jsonl"
            record(idx, "exits-audit", str(eng_src), eng_src,
                   sorted(per_id), per_id, exit_code, len(per_id),
                   str(args.out))
    except RecordRejected as exc:
        # 证据本体不可信：与断言结果取或，禁静默（1012-06 定标点名①）
        print(f"exits-audit: 证据拒账，exit 置 1——{exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        pass  # 索引 IO 失败不掩盖主判定（既有豁免语义）
    print(f"exits-audit: FAIL {len(fails)} 项"
          + (f"; FAIL: {fails[:8]}" if fails else ""))
    return exit_code  # 1012-06：拒账时取或置 1


if __name__ == "__main__":
    sys.exit(main())
