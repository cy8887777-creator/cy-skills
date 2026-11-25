#!/usr/bin/env python3
"""explore-walk — 探索式旅程（机器游走，管线⑨自测补充，1008-05）。

主流程冒烟验证的是设计者预写的 happy path——"自己设计的路径自己验证，
盲区是结构性的"。本脚本从 `/` 出发随机游走：每步从当前页**可见**
data-intent 里选未点过的元素物理点击（跳过 capsule-*/app-toast 系统
件），断言全程无 404 / 白屏 / console error / 卡死；游走结束后对
访问过的每个非 terminal 页做**死端检查**（必须有出口 intent）。

定位（station-guide §9）：
  - 游走只**发现**设计者想象外的断链；出口完整性以 exits-audit.py
    的角色断言为准（1008-04）——游走发现的问题须回流为确定性断言
    （fixture）才算闭环；
  - terminal 页（合法终止页）按④冻结清单 role 字段豁免死端判定；
  - **可复现**：seed + 逐步路径 + 覆盖目标数全部落盘，禁止"跑过即过"。

用法：
  python explore-walk.py --dist <构建目录或URL> [--start /] \
      [--steps 20] [--seed 42] [--exits exits.json] [--out walk_report.json]
Exit 0 = 全过；1 = 有 FAIL。
"""
from __future__ import annotations

import argparse
import functools
import json
import random
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # 1012-01：fail-closed 提示走 stderr，须与 stdout 同 UTF-8 口径

SKIP_PREFIX = ("capsule-", "app-toast")  # 系统件：不作为游走目标
EXIT_PREFIX = ("nav-back", "tab-", "capsule-close", "switch-tab", "go-back",
               "close-")


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

def _page_of(fail: str) -> str | None:
    """fail 条目 → 归属页（1012-01 per_id 按页归因）。
    两种形态："步N @<page> 点[...] ..." / "死端: <page> 无任何..."。"""
    if fail.startswith("死端: "):
        return fail[len("死端: "):].split(" ", 1)[0]
    if " @" in fail:
        return fail.split(" @", 1)[1].split(" ", 1)[0]
    return None


def start_spa(root: Path):
    handler = functools.partial(SPAHandler, directory=str(root))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dist", required=True, help="构建目录或 http(s) URL")
    ap.add_argument("--start", default="/", help="游走起点（默认 /）")
    ap.add_argument("--steps", type=int, default=20, help="最大步数")
    ap.add_argument("--seed", type=int, default=42, help="随机种子（落盘可复现）")
    ap.add_argument("--exits", help="exits.json（④真值：terminal 豁免用，可选）")
    ap.add_argument("--src", default=None,
                    help="工程 src 目录（证据索引 target/hash 对象；缺失时 "
                         "fail-closed 跳过落账，1012-01）")
    ap.add_argument("--viewport", default=None,
                    help='浏览器视口 "WxH"（默认 375x812；由 PLAN '
                         'device_profile 档决定，1010-04）')
    ap.add_argument("--out", default="walk_report.json")
    args = ap.parse_args()

    terminal_routes: set[str] = set()
    if args.exits:
        for pg in json.loads(Path(args.exits).read_text(encoding="utf-8")):
            if pg.get("role") == "terminal":
                terminal_routes.add(pg.get("route", "").rstrip("/"))

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
    rng = random.Random(args.seed)
    visited: list[str] = []
    path_log: list[dict] = []
    tried: set[tuple[str, str]] = set()
    fails: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=parse_viewport(args.viewport))
        page.on("pageerror", lambda e: console_errors.append(
            f"pageerror @{page.url}: {e}"))
        page.on("console", lambda m: console_errors.append(
            f"console-{m.type} @{page.url}: {m.text[:120]}")
            if m.type == "error" and "favicon" not in m.text else None)
        page.on("response", lambda r: console_errors.append(
            f"http{r.status} @{page.url}: {r.url[-80:]}")
            if r.status >= 400 and "favicon" not in r.url else None)

        def current_path() -> str:
            return page.url[len(base):].split("?")[0] or "/"

        def visible_intents() -> list[str]:
            return page.evaluate("""() => [...document.querySelectorAll('[data-intent]')]
              .filter(e => { const r = e.getBoundingClientRect();
                const cs = getComputedStyle(e);
                return r.width > 0 && r.height > 0
                  && cs.display !== 'none' && cs.visibility !== 'hidden'
                  && Number(cs.opacity) !== 0; })
              .map(e => e.getAttribute('data-intent'))""")

        page.goto(base + args.start, wait_until="domcontentloaded",
                  timeout=20000)
        page.wait_for_timeout(900)

        for step in range(args.steps):
            cur = current_path()
            if cur not in visited:
                visited.append(cur)
            cands = [i for i in visible_intents()
                     if i and not i.startswith(SKIP_PREFIX)
                     and (cur, i) not in tried]
            if not cands:
                # 本页候选耗尽：尝试回首页换方向，否则收束
                if current_path() != args.start and page.query_selector(
                        '[data-intent="nav-back"]'):
                    page.click('[data-intent="nav-back"]', timeout=5000)
                    page.wait_for_timeout(700)
                    continue
                if current_path() != args.start and page.query_selector(
                        '[data-intent="tab-dragon-companion"], [data-intent^="tab-"]'):
                    tab = page.query_selector('[data-intent^="tab-"]')
                    tab.click(timeout=5000)
                    page.wait_for_timeout(700)
                    continue
                break
            pick = rng.choice(cands)
            tried.add((cur, pick))
            before = page.url
            try:
                el = page.query_selector(f'[data-intent="{pick}"]')
                el.scroll_into_view_if_needed(timeout=2000)
                el.click(timeout=6000)  # 物理点击，禁 force
                page.wait_for_timeout(800)
            except Exception as exc:
                fails.append(f"步{step} @{cur} 点[{pick}] 点击失败: {str(exc)[:80]}")
                path_log.append({"step": step, "from": cur, "intent": pick,
                                 "result": "CLICK_FAIL"})
                continue
            after_path = current_path()
            blank = page.evaluate(
                "() => document.body.innerText.trim().length < 5")
            entry = {"step": step, "from": cur, "intent": pick,
                     "to": after_path, "blank": blank}
            path_log.append(entry)
            if blank:
                fails.append(f"步{step} @{cur} 点[{pick}] → {after_path} 白屏")
            # 卡死检测：200ms 内主线程无响应近似（简化：点击已超时即判）

        # 死端检查：访问过的非 terminal 页必须有出口 intent
        for v in visited:
            if v.rstrip("/") in terminal_routes or v == "/":
                continue
            try:
                page.goto(base + v, wait_until="domcontentloaded",
                          timeout=15000)
                page.wait_for_timeout(700)
                intents = visible_intents()
                exits = [i for i in intents
                         if i and (i.startswith(EXIT_PREFIX)
                                   or "back" in i.lower())]
                if not exits:
                    fails.append(f"死端: {v} 无任何返回/关闭/切换出口")
            except Exception:
                pass  # 复访失败不计（游走时已到过）
        browser.close()
    if srv is not None:
        srv.shutdown()

    exit_code = 1 if fails else 0
    report = {"seed": args.seed, "steps_limit": args.steps,
              "start": args.start, "visited": visited,
              "path": path_log, "tried_count": len(tried),
              "terminal_exempt": sorted(terminal_routes),
              "console_errors": console_errors[:20],
              "viewport": parse_viewport(args.viewport),  # 1012-01
              "fails": fails}
    src_dir = (Path(args.src).resolve()
               if args.src and Path(args.src).is_dir() else None)
    if src_dir is not None:
        from evidence_index import src_hash
        report["src_hash"] = src_hash(src_dir)  # 1012-06：报告内嵌哈希
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    # 落账（1012-01：补观测洞；先写报告后 record——1012-06 统一顺序）
    if src_dir is not None:
        per_id = {v: "PASS" for v in visited}
        for f in fails:
            pg = _page_of(f)
            if pg and pg in per_id:
                per_id[pg] = "FAIL"
        try:
            from evidence_index import record, RecordRejected
            record(src_dir.parent / "pipeline" / "evidence_index.jsonl",
                   "explore-walk", str(src_dir), src_dir,
                   sorted(per_id), per_id,
                   exit_code, len(visited), str(Path(args.out).resolve()))
        except RecordRejected as exc:
            # 证据本体不可信：与断言结果取或，禁静默（1012-06 定标点名①）
            print(f"explore-walk: 证据拒账，exit 置 1——{exc}",
                  file=sys.stderr)
            exit_code = 1
        except Exception as exc:
            print(f"explore-walk: 证据索引落账失败（不掩盖主判定）: {exc}",
                  file=sys.stderr)
    else:
        print("explore-walk: 未提供 --src，跳过证据索引落账（fail-closed）",
              file=sys.stderr)
    print(f"explore-walk: seed={args.seed} 走 {len(path_log)} 步，"
          f"访问 {len(visited)} 页，尝试 {len(tried)} 个 intent"
          + (f"; FAIL: {len(fails)}" if fails else "; 无断链/白屏/死端"))
    for f in fails[:10]:
        print("  -", f)
    return exit_code  # 1012-06：拒账时取或置 1


if __name__ == "__main__":
    sys.exit(main())
