#!/usr/bin/env python3
"""route-audit — 全路由可达断言（管线⑩集成验收，确定性）。

三方对账（冻结清单 ↔ 源码提取路由 ↔ 待测清单，全差集 FAIL）+
无头浏览器逐路由访问：HTTP >=400、JS 异常、空白页任一命中即 FAIL；
逐路由截图落盘。SPA fallback 会让任意路径返回 200，"可达"由对账
背书。目录模式自动起**带 SPA fallback 的本地服务**（Vite build 产物
直接可测）——file:// 打不开 module script（CORS 拦截必白屏），禁止。

用法：
  python route-audit.py --dist <构建目录或 http URL> --frozen <冻结清单.json> \
      --from-source <工程src> [--routes routes.json] \
      [--out route_audit_report.json] [--shots <截图目录>]
  --frozen 必需（④冻结路由清单，[{id, path}] 或 redirect 入口
  [{id, path, redirect_to}]——契约落点真值来自 sitemap「入口契约」，
  实际落点≠契约落点 FAIL，错跳真实业务页同 FAIL）；--from-source 必需
  （提取为超集近似——注释/无关对象的 path 会计入，差集 FAIL 后人工
  裁决；未注册路由的最终裁决靠运行时探针：页面根节点须挂
  data-route="<path>"，写码契约约定，访问时验证目标组件真的渲染）。
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# react-router 路由声明（JSX <Route path="/x"> 与配置 path: "/x"）
ROUTE_RE = re.compile(r'''path\s*[=:]\s*["'](\/[^"']*)["']''')



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

def extract_routes(src_dir: Path) -> set[str]:
    """从工程源码提取全部路由 path——与冻结清单对账用。

    扫描范围栈无关（1008-07）：.ts/.tsx（React/router 配置）+ .vue
    （vue-router 可在 SFC 内声明路由）。react-router 与 vue-router 的
    path 声明同构（path: "/x" / path="/x"），同一正则覆盖。"""
    paths: set[str] = set()
    for p in (list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts"))
              + list(src_dir.rglob("*.vue"))):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        paths.update(m.group(1) for m in ROUTE_RE.finditer(text))
    return paths


class SPAHandler(SimpleHTTPRequestHandler):
    """history 路由 fallback：404 路径回 index.html（SPA 语义）。"""

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            index = Path(self.directory) / "index.html"  # type: ignore[attr-defined]
            if index.is_file():
                body = index.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        super().send_error(code, message, explain)

    def log_message(self, *a):  # 静默访问日志
        pass


def start_spa_server(root: Path, port: int = 0):
    handler = functools.partial(SPAHandler, directory=str(root))
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dist", required=True, help="构建产物目录或 http(s) URL")
    ap.add_argument("--routes", help="待测路由清单 json（[{id, path}]）")
    ap.add_argument("--from-source", dest="from_source", required=True,
                    help="工程 src 目录——提取实际路由做三方对账（必需："
                         "省略则对账退化两方，覆盖无从证明；提取为超集"
                         "近似，注释/无关对象的 path 会计入，差集按 "
                         "FAIL 处理后人工裁决）")
    ap.add_argument("--frozen", required=True,
                    help="④冻结路由清单 json（[{id, path}]）——对账基准"
                         "（必需：没有冻结清单就无法证明覆盖，SPA "
                         "fallback 下万物 200，可达全靠对账背书）")
    ap.add_argument("--viewport", default=None,
                    help='浏览器视口 "WxH"（默认 375x812；由 PLAN '
                         'device_profile 档决定，1010-04）')
    ap.add_argument("--out", default="route_audit_report.json")
    ap.add_argument("--shots", default=None,
                    help="截图目录（默认 <out 同目录>/route_shots）")
    args = ap.parse_args()

    # —— 三方对账：冻结清单 ↔ 源码实际路由 ↔ 待测清单 ——
    # SPA fallback 会让任意路径返回 200，"可达"必须先证明"覆盖"。
    # --frozen/--from-source 均必需（required），无可省略的退化形态
    frozen_list = json.loads(Path(args.frozen).read_text(encoding="utf-8"))
    # redirect 支持（1008-08）：冻结清单条目允许 {"id", "path",
    # "redirect_to"}——path 为入口，redirect_to 为契约落点（真值 =
    # sitemap「入口契约」）。判据是实际落点==契约落点，不是"跳到任意
    # 真实页"——/ 错跳任何其他业务页照样 FAIL。
    frozen = {r["path"] for r in frozen_list}
    redirect_map = {r["path"]: r.get("redirect_to")
                    for r in frozen_list if r.get("redirect_to")}
    extracted = extract_routes(Path(args.from_source))
    if not extracted:
        print("route-audit: --from-source 提取到 0 条路由——检查 "
              "src 目录/路由写法"); return 1
    if args.routes:
        routes = json.loads(Path(args.routes).read_text(encoding="utf-8"))
    else:
        routes = [{"id": p.strip("/").replace("/", "-") or "root",
                   "path": p} for p in sorted(extracted)]
    if not routes:
        print("route-audit: 待测清单为空——nothing to test（空清单"
              "不算通过）"); return 1

    recon = {"frozen_count": len(frozen),
             "extracted_count": len(extracted),
             "tested_count": len(routes)}
    fails_pre: list[str] = []
    tested = {r["path"] for r in routes}
    # 三方全差集一律 FAIL（四轮评审：部分差集只记录不 fail = 假绿——
    # SPA fallback 下未实现路径照样 200，覆盖只能靠对账背书）
    recon["frozen_not_tested"] = sorted(frozen - tested)
    recon["tested_not_frozen"] = sorted(tested - frozen)
    fails_pre.extend(f"冻结清单未测: {p}" for p in sorted(frozen - tested))
    fails_pre.extend(
        f"待测不在冻结清单: {p}" for p in sorted(tested - frozen))
    recon["implemented_not_frozen"] = sorted(extracted - frozen)
    recon["frozen_not_implemented"] = sorted(frozen - extracted)
    fails_pre.extend(
        f"实现有而冻结清单无（未归并/泄漏）: {p}"
        for p in sorted(extracted - frozen))
    fails_pre.extend(
        f"冻结清单有而未实现: {p}"
        for p in sorted(frozen - extracted))
    if fails_pre:
        print("route-audit: 对账失败（先修覆盖再逐路由访问）")
        for f in fails_pre:
            print(f"  - {f}")
    shots_dir = (Path(args.out).parent / "route_shots" if args.shots is None
                 else Path(args.shots))
    shots_dir.mkdir(parents=True, exist_ok=True)

    srv = None
    if args.dist.startswith("http"):
        base = args.dist.rstrip("/")
    else:
        root = Path(args.dist).resolve()
        if not (root / "index.html").is_file():
            print(f"dist 缺 index.html: {root}"); return 1
        srv = start_spa_server(root)
        base = f"http://127.0.0.1:{srv.server_address[1]}"

    from playwright.sync_api import sync_playwright
    results, fails = [], []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=parse_viewport(args.viewport))
        page_errors: list[str] = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        for r in routes:
            page_errors.clear()
            rec: dict = {"id": r["id"], "path": r["path"]}
            try:
                resp = page.goto(base + r["path"],
                                 wait_until="domcontentloaded", timeout=20000)
                status = resp.status if resp else 0
                page.wait_for_timeout(600)
                blank = page.evaluate(
                    "() => document.body.innerText.trim().length") == 0
                # 运行时路由真值探针（六轮评审：正则提取是超集近似，
                # 清单对账拦不住"三方恰好一致但实际未注册"——SPA
                # fallback 照样 200。页面根节点挂 data-route="<path>"
                # （写码契约），访问时验证目标组件真的渲染了。
                # 七轮评审收紧证据范围：hidden/零尺寸元素跳过（伪造
                # <div data-route hidden> 骗探针无效）+ 目标元素内部
                # 须有内容（整页文字非空但目标组件空壳仍 FAIL））
                probe = page.evaluate(
                    """() => {
                      for (const el of document.querySelectorAll(
                              '[data-route]')) {
                        const r = el.getBoundingClientRect();
                        // 任一零尺寸即不可见（OR——AND 会被 width:0
                        // 高条绕过）；opacity 0 同拒（双轴三轮）
                        if (r.width === 0 || r.height === 0) continue;
                        const cs = getComputedStyle(el);
                        if (cs.display === 'none'
                                || cs.visibility === 'hidden'
                                || Number(cs.opacity) === 0) continue;
                        return {tag: el.getAttribute('data-route'),
                                hasContent:
                                    el.innerText.trim().length > 0};
                      }
                      return null;
                    }""")
                route_tag = probe["tag"] if probe else None
                route_content = bool(probe and probe["hasContent"])
                shot = shots_dir / f"route_{r['id']}.png"
                # 全页截图（1007-22）：长页（h/w>2.2）内容必须全部进
                # 验收证据——812 视口截图曾漏掉长图 95% 内容
                page.screenshot(path=str(shot), full_page=True)
                # redirect 判据（1008-08）：访问后 URL 落在被测 path 之外
                # 时，只有"实际落点 == 契约落点（redirect_to）且落点页
                # data-route 自洽"才 PASS——错跳任何其他页（哪怕真实
                # 业务页）FAIL；未登记 redirect_to 的路径发生跳转同 FAIL
                actual = page.url[len(base):] or "/"
                path_part = actual.split("?")[0]
                redirected = path_part.rstrip("/") != r["path"].rstrip("/")
                if redirected:
                    contract = redirect_map.get(r["path"])
                    if contract and path_part.rstrip("/") == contract.rstrip("/"):
                        route_ok = (route_tag is not None
                                    and route_content
                                    and route_tag.rstrip("/")
                                    == contract.rstrip("/"))
                        rec["redirect"] = {"to": path_part,
                                           "contract": contract}
                    else:
                        route_ok = False
                        rec["redirect"] = {"to": path_part,
                                           "contract": contract,
                                           "note": "实际落点≠契约落点"
                                           if contract else
                                           "未登记 redirect_to 却发生跳转"}
                else:
                    route_ok = (route_tag is not None
                                and route_content
                                and route_tag.rstrip("/")
                                == r["path"].rstrip("/"))
                rec.update(status=status, blank=blank, route_tag=route_tag,
                           route_content=route_content,
                           errors=list(page_errors), shot=str(shot),
                           ok=status < 400 and not blank
                           and not page_errors and route_ok)
            except Exception as exc:
                rec.update(ok=False, error=str(exc)[:200])
            results.append(rec)
            if not rec["ok"]:
                fails.append(r["id"])
        browser.close()
    if srv is not None:
        srv.shutdown()

    exit_code = 1 if (fails or fails_pre) else 0
    # 1012-06 统一顺序：先写报告（内嵌 src_hash）→ 再 record（读盘校验）
    report = {"viewport": parse_viewport(args.viewport),  # 1012-01
              "total": len(routes), "base": base, "fails": fails,
              "reconciliation": recon, "results": results}
    frozen_src = Path(args.from_source).resolve()  # 1012-01 裁定④：target resolve（原文路径与消费端 resolve 比对不符=死行）
    if frozen_src.exists():
        from evidence_index import src_hash
        report["src_hash"] = src_hash(frozen_src)
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        from evidence_index import record, RecordRejected
        per_id = {r["id"]: ("PASS" if r.get("ok") else "FAIL")
                  for r in results}
        record(Path(args.from_source).parent / "pipeline" /
               "evidence_index.jsonl", "route-audit",
               str(frozen_src), frozen_src,
               [r["id"] for r in results], per_id, exit_code,
               len(routes), str(args.out))
    except RecordRejected as exc:
        # 证据本体不可信：与断言结果取或，禁静默（1012-06 定标点名①）
        print(f"route-audit: 证据拒账，exit 置 1——{exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        pass  # 索引 IO 失败不掩盖主判定（既有豁免语义）
    print(f"route-audit: {len(routes) - len(fails)}/{len(routes)} ok"
          + (f"; FAIL: {fails}" if fails else "")
          + (f"; 对账问题: {len(fails_pre)}" if fails_pre else "")
          + f"; shots: {shots_dir}")
    return exit_code  # 1012-06：拒账时取或置 1


if __name__ == "__main__":
    sys.exit(main())
