#!/usr/bin/env python3
"""S1: vendor ALL external dependencies for offline delivery.

用法：
  python vendor_local.py --html <产物>/index.html            # 扫描+落盘+改写
  python vendor_local.py --html <产物>/index.html --offline-check
                                                            # 断网复测

扫描 index.html 的**全部**外部引用（script/link/img src、href、
srcset、CSS url()、@import——不维护固定栈清单，任何 CDN 的
框架/字体/图标都覆盖），逐个下载到 assets/vendor/，改写为本地相对
路径；CSS 内的 url()/@import 递归落盘并改写。改写完成后**自动**
用无头浏览器离线复测（零外部请求 + 本地资源全部加载成功才算交付
成立；浏览器不可用降级为字符串级检查并如实提示）。
`--offline-check` 单独运行可对已有产物复测。

Exit 0 = 已离线化且离线复测通过；1 = 下载失败（依赖树任一层）/ 改写
后仍有外链残留 / 离线复测发现外部请求或本地断链。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}


def _abs_url(u: str) -> str:
    """协议相对（//host/x）归一为 https——file:// 场景浏览器无法解析。"""
    return u if u.startswith("http") else f"https:{u}"


def scan_refs(text: str) -> list[tuple[str, str]]:
    """HTML/CSS 中全部绝对外链，返回 (原文形态, 归一 URL) 列表。

    覆盖 https?:// 与协议相对 //host/ 两种形态（2026-10-07 第三次
    评审：//cdn... 引用此前根本进不了候选集），统一归一为 https。
    srcset（2026-10-07 双轴复查补）按逗号切候选、取首段 URL。

    返回原文形态的原因（2026-10-07 第五轮评审：确定性 bug——此前
    返回归一 URL，改写 html.replace(归一) 对原文 //cdn 匹配不到，
    改写静默落空且残留只 WARN 仍退出 0=假成功）：改写必须按原文。
    """
    refs: list[tuple[str, str]] = []
    for m in re.finditer(
            r'(?:src|href|poster)\s*=\s*["\']?((?:https?:)?//[^"\'\s>]+)',
            text):
        refs.append((m.group(1), _abs_url(m.group(1))))
    for m in re.finditer(r'srcset\s*=\s*["\']([^"\']+)["\']', text):
        for cand in m.group(1).split(","):
            parts = cand.strip().split()
            if parts and (parts[0].startswith("//")
                          or parts[0].startswith("http")):
                refs.append((parts[0], _abs_url(parts[0])))
    for m in re.finditer(r'url\(\s*["\']?((?:https?:)?//[^"\')\s]+)', text):
        refs.append((m.group(1), _abs_url(m.group(1))))
    for m in re.finditer(
            r'@import\s+(?:url\(\s*)?["\']?((?:https?:)?//[^"\')\s;]+)',
            text):
        refs.append((m.group(1), _abs_url(m.group(1))))
    return refs


def rewrite_refs(text: str, entries: list[tuple[str, str]],
                 resolve) -> tuple[str, set[str]]:
    """按原文形态替换全部引用（2026-10-07 第五轮评审：改写与归一
    必须同源）。resolve(norm_url) → 替换串；None = 下载失败。
    返回 (新文本, 失败的归一 URL 集合)。

    前缀嵌套防护必须**跨组全局**按 raw 长度降序（2026-10-07 第六轮
    评审实测：a.js 与 a.js?v=1 是两个不同 norm——组内排序防不住
    跨组前缀吞噬，短者先替换把长者的前缀吃掉，产物 SHORT?v=1 用错
    下载结果且零外链残留）。分组仅用于 resolve 去重，替换统一走
    展平后的全局降序列表。"""
    by_norm: dict[str, list[str]] = {}
    for raw, norm in entries:
        by_norm.setdefault(norm, []).append(raw)
    fails: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for norm, raws in by_norm.items():
        rep = resolve(norm)
        if rep is None:
            fails.add(norm)
            continue
        for raw in raws:
            pairs.append((raw, rep))
    for raw, rep in sorted(pairs, key=lambda p: len(p[0]), reverse=True):
        text = text.replace(raw, rep)
    return text, fails


ROOT_REL_RE = re.compile(
    r'(?:src|href|poster)\s*=\s*["\'](/[^/"\'\s>][^"\'\s>]*)["\']')


def scan_root_relative(text: str) -> set[str]:
    """HTML 层根相对引用（src="/fonts/x.woff2"）。

    HTML 是本地文件、没有 base URL，这类引用无法代为解析（浏览器
    file:// 下同样打不开）——不能静默放过，收集起来如实报告。
    """
    return {m.group(1) for m in ROOT_REL_RE.finditer(text)}


REL_URL_RE = re.compile(r'''url\(\s*["']?([^"')\s#][^"')\s]*)["']?\s*\)''')
REL_IMPORT_RE = re.compile(r'''@import\s+(?:url\(\s*)?["']([^"']+)["']''')
SKIP_PREFIX = ("data:", "#", "http")


def scan_rel_urls(css_text: str) -> set[str]:
    """CSS 内 url()/@import 中除 data:/锚点/绝对 http 外的全部引用。

    根相对（/fonts/x.woff2）与协议相对（//cdn/x.js）都在内——CSS 有
    自身 URL 作 base，urljoin 可解析（2026-10-07 第三次评审：此前
    / 开头被直接跳过，Google Fonts 类字体文件静默不落盘）。
    """
    out: set[str] = set()
    for pat in (REL_URL_RE, REL_IMPORT_RE):
        for m in pat.finditer(css_text):
            ref = m.group(1).strip()
            if ref.startswith(SKIP_PREFIX):
                continue
            out.add(ref)
    return out


def is_css_response(url: str, content_type: str = "") -> bool:
    """CSS 判定单一出处（2026-10-07 双轴复查：local_name 与
    vendor_url 两处口径不一，极端组合会"存成 .js 却按 CSS 递归"）。
    响应头 text/css 优先，URL 路径 .css 结尾兜底（个别 CDN 头缺失）。"""
    if "text/css" in (content_type or "").lower():
        return True
    return urlparse(url).path.lower().endswith(".css")


def fetch(url: str) -> tuple[bytes, str]:
    """返回 (body, Content-Type)——判型看响应头，不看响应体猜。"""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), (resp.headers.get("Content-Type") or "")


def local_name(url: str, data: bytes, content_type: str = "") -> str:
    """稳定本地名：路径尾名 + 内容短 hash（防跨源同名冲突）。

    扩展名判定：响应头 Content-Type 优先（css2?... 这类无扩展名
    URL 的真身是 CSS——按响应体猜会存成 .js 并跳过递归，字体文件
    全部漏盘，2026-10-07 第三次评审）。
    """
    path = urlparse(url).path
    tail = path.rstrip("/").rsplit("/", 1)[-1] or "index"
    tail = re.sub(r"[^A-Za-z0-9._-]", "_", tail)[-60:]
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    if "." not in tail:
        ct = content_type.lower()
        if is_css_response(url, content_type) or tail.startswith("_"):
            ext = "css"
        elif "javascript" in ct:
            ext = "js"
        elif "font" in ct or "woff" in ct:
            ext = "woff2"
        elif "png" in ct:
            ext = "png"
        elif "svg" in ct:
            ext = "svg"
        else:
            ext = "bin"
        tail = f"{tail}.{ext}"
    return f"{h}_{tail}"


def vendor_url(url: str, vendor_dir: Path, done: dict,
               tree_fails: set) -> str | None:
    """落盘单个 URL 及其全部子依赖。

    tree_fails（2026-10-07 第六轮评审）：整棵依赖树共享的失败收集器
    ——CSS 子资源下载失败必须向顶层传播，否则父 CSS 照常返回成功、
    字体静默不落盘（成功条件是整棵树落盘，不是父资源返回非 None）。"""
    if url in done:
        rel = done[url]
        if rel is None:
            tree_fails.add(url)
        return rel
    try:
        data, content_type = fetch(url)
    except Exception as exc:
        print(f"vendor_local: FETCH FAIL {url}: {exc}")
        done[url] = None
        tree_fails.add(url)
        return None
    name = local_name(url, data, content_type)
    (vendor_dir / name).write_bytes(data)
    rel = f"assets/vendor/{name}"
    done[url] = rel
    print(f"vendor_local: {url} -> {rel} ({len(data) // 1024} KB)")
    is_css = is_css_response(url, content_type) or name.endswith(".css")
    if is_css:
        css = data.decode("utf-8", errors="replace")
        # 相对子引用集合先于绝对改写提取（改写后的本地文件名会被
        # 相对扫描器二次解析，浪费一次 404 请求）
        rel_refs = sorted(scan_rel_urls(css))
        # 绝对子引用 → 递归落盘；CSS 内改写为**文件名**（同目录）——
        # 写 assets/vendor/ 前缀会被浏览器相对 CSS 目录再拼一次 → 404。
        # 按原文形态替换（//cdn 与 https://cdn 各替换各的）；子树失败
        # 汇入共享收集器
        css, _ = rewrite_refs(
            css, scan_refs(css),
            lambda sub: _basename_or_none(
                vendor_url(sub, vendor_dir, done, tree_fails)))
        # 相对/根相对/协议相对子引用 → 相对原 CSS URL 解析成绝对后
        # 同样递归；改写为文件名（urljoin 对三类形态统一正确解析）
        from urllib.parse import urljoin
        for ref in rel_refs:
            sub_abs = urljoin(url, ref)
            sub_rel = vendor_url(sub_abs, vendor_dir, done, tree_fails)
            if sub_rel:
                css = css.replace(ref, Path(sub_rel).name)
        (vendor_dir / name).write_text(css, encoding="utf-8")
    return rel


def _basename_or_none(rel: str | None) -> str | None:
    """CSS 内改写目标：本地文件名（同目录相对）。"""
    return Path(rel).name if rel else None


def offline_check(html_path: Path) -> tuple[list[str], list[str]]:
    """无头浏览器拦截全部外部请求；同时检测**本地资源加载失败**
    （404/断链——离线改写错路径时 external 为零但页面照样残缺）。"""
    from playwright.sync_api import sync_playwright
    external: list[str] = []
    local_failures: list[str] = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        def block(route, request):
            if request.url.startswith("http"):
                external.append(request.url)
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block)
        page.on("response", lambda r: local_failures.append(
            f"{r.status} {r.url}") if r.status >= 400 else None)
        page.on("requestfailed", lambda r: local_failures.append(
            f"FAILED {r.url}") if not r.url.startswith("http") else None)
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.wait_for_timeout(1500)
        browser.close()
    return external, local_failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", required=True,
                    help="path to the delivered index.html")
    ap.add_argument("--offline-check", action="store_true",
                    help="不落盘，仅断网复测（拦截外部请求）")
    args = ap.parse_args()
    html_path = Path(args.html)
    if not html_path.is_file():
        print(f"vendor_local: html not found: {html_path}")
        return 1

    if args.offline_check:
        external, local_failures = offline_check(html_path)
        if external:
            print(f"vendor_local OFFLINE FAIL: {len(external)} external "
                  f"request(s) still made:")
            for u in sorted(set(external))[:10]:
                print(f"  - {u}")
            return 1
        if local_failures:
            print(f"vendor_local OFFLINE FAIL: {len(local_failures)} "
                  f"local resource(s) failed to load:")
            for u in sorted(set(local_failures))[:10]:
                print(f"  - {u}")
            return 1
        print("vendor_local: offline check PASS — zero external "
              "requests, all local resources loaded")
        return 0

    html = html_path.read_text(encoding="utf-8")
    entries = scan_refs(html)
    root_rel = scan_root_relative(html)
    if root_rel:
        # 根相对引用无 base URL 可解析（本地 HTML 浏览器也打不开），
        # 不能静默放过——如实报告，交用户决策
        print(f"vendor_local WARN: {len(root_rel)} root-relative ref(s) "
              f"cannot be vendored (no base URL): {sorted(root_rel)[:5]}")
    if not entries:
        print("vendor_local: no external references found — already "
              "offline (run --offline-check to verify)")
        return 0
    vendor_dir = html_path.parent / "assets" / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    done: dict[str, str | None] = {}
    tree_fails: set[str] = set()
    html, fails = rewrite_refs(
        html, entries,
        lambda norm: vendor_url(norm, vendor_dir, done, tree_fails))
    if fails or tree_fails:
        # 依赖树任一层失败都 FAIL（第六轮评审：CSS 子资源失败不得被
        # 父资源吞掉）
        all_fails = sorted(set(fails) | tree_fails)
        print(f"vendor_local FAILED — {len(all_fails)} download(s) "
              f"unavailable: {all_fails[:5]}; "
              "index.html left untouched")
        return 1
    html_path.write_text(html, encoding="utf-8")
    # 残留检查（2026-10-07 第五轮评审升级）：改写后仍含外链 = 离线化
    # 不完整 = 交付失败，FAIL 退出 1——WARN+exit 0 是假成功通道
    residual = scan_refs(html)
    if residual:
        print(f"vendor_local FAILED: {len(residual)} external ref(s) "
              f"remain after rewrite: {sorted(set(n for _, n in residual))[:5]}")
        return 1
    # 成功条件 = 整棵依赖树落盘**并通过离线加载**（2026-10-07 第六轮
    # 评审全局建议：字符串残留为零不代表资源正确——自动复测，浏览器
    # 不可用时降级为残留检查结果并如实提示）
    try:
        ext, locfail = offline_check(html_path)
        if ext or locfail:
            print(f"vendor_local FAILED: offline recheck found "
                  f"{len(ext)} external request(s) / "
                  f"{len(locfail)} local failure(s) "
                  f"（index.html 已改写落盘——按失败项修依赖后重跑或 "
                  f"--offline-check 复测）")
            for u in (ext + locfail)[:8]:
                print(f"  - {u}")
            return 1
        print("vendor_local: offline recheck PASS — zero external "
              "requests, all local resources loaded")
    except Exception as exc:  # noqa: BLE001 — 无浏览器环境降级
        print(f"vendor_local WARN: offline recheck unavailable ({exc}) "
              "— only string-level checks ran")
    print("vendor_local: index.html rewritten to local refs — "
          "delivery verified offline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
