"""
scripts/B/fetch_url.py — B-2 无头浏览器抓取 URL

复用：playwright（标准浏览器自动化库，**不自造**）
输入：URL
产出：source/fetched.html（**只落快照，不链式解析**；源材料快照归产物 source/ 区）

规则（SKILL.md 站 ② B-2-a）：
  playwright 抓 + wait_until="networkidle"（避免 SPA 渲染缺失）
  **两步分离铁律（A8 修正）**：本脚本只负责抓取落盘；解析（B-1 parse_html.py）
  是站 ② 的显式第二步——脚本内自动链式跑会把上一步输入的 middle.json 覆盖掉
  （换输入丢数据还不自知）。抓完由 agent 决定是否立刻续跑解析。
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright  # 复用：playwright Python SDK


def is_valid_url(url: str) -> bool:
    try:
        r = urlparse(url)
        return r.scheme in ("http", "https") and bool(r.netloc)
    except Exception:
        return False


def fetch(url: str, out_html: Path) -> int:
    if not is_valid_url(url):
        print(f"[FAIL] URL 不合法: {url}", file=sys.stderr)
        return 2

    out_html.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            out_html.write_text(html, encoding="utf-8")
            print(f"[OK] {url} -> {out_html}  ({len(html)} chars)")
        finally:
            browser.close()
    return 0


def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_url.py <url> [out_html]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    out_html = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("source/fetched.html")

    rc = fetch(url, out_html)
    if rc != 0:
        return rc
    print(f"[INFO] 第一步（抓取）完成即止。第二步解析请显式执行：python scripts/B/parse_html.py {out_html} <out/middle.json>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
