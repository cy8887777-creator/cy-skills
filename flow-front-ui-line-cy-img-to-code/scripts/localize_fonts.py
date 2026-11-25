#!/usr/bin/env python3
"""1009-04: 产物字体子集本地化——产物独立性红线（渲染硬依赖不得外链）。

用法：
  python localize_fonts.py --html <产物>/index.html

页面含 Google Fonts 外链（css2）时：提取页面实际用到的字符 → 按字重
请求子集 CSS → 解析 woff2 URL 逐个下载到 assets/fonts/ → 用本地
@font-face 替换外链。子集后每个字重约 10-20KB（全量 Noto Sans SC 单
字重 ~10MB——子集是可行性的关键）。无 Google Fonts 外链则零操作。

核心逻辑拆为纯函数（collect_chars/parse_subset_css/build_font_face）
供 contract-suite 离线单测；网络请求集中在 localize()。

Exit 0 = 已本地化（或本无外链）；1 = 下载失败或写回失败。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}


def collect_chars(html: str) -> str:
    """页面实际字符集（去 HTML 标签/脚本样式内容/空白，保序去重）。"""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html,
                  flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", "", body)
    seen: dict[str, None] = {}
    for ch in body:
        if not ch.isspace() and ch not in seen:
            seen[ch] = None
    return "".join(seen)


def parse_subset_css(css: str) -> list[dict]:
    """解析 css2 返回的 @font-face 块 → [{family,weight,url,format,
    unicode_range}]。text= 子集请求返回 fonts.gstatic.com/l/font?kit=
    且 format('truetype')——不是 .woff2（实测），URL 与 format 都按
    实际返回解析。"""
    faces = []
    for m in re.finditer(r"@font-face\s*\{([^}]+)\}", css):
        blk = m.group(1)
        fam = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", blk)
        wgt = re.search(r"font-weight:\s*(\d+)", blk)
        url = re.search(r"url\((https://[^)]+)\)\s*format\(['\"]([a-z0-9]+)['\"]\)",
                        blk)
        urange = re.search(r"unicode-range:\s*([^;]+);", blk)
        if fam and url:
            faces.append({
                "family": fam.group(1),
                "weight": int(wgt.group(1)) if wgt else 400,
                "url": url.group(1),
                "format": url.group(2),
                "unicode_range": urange.group(1).strip() if urange else None,
            })
    return faces


def build_font_face(faces: list[dict], files: dict[str, str]) -> str:
    """本地 @font-face 块（files: url → 相对路径）。"""
    out = []
    for f in faces:
        rel = files.get(f["url"])
        if not rel:
            continue
        ur = (f"\n  unicode-range: {f['unicode_range']};"
              if f["unicode_range"] else "")
        out.append(
            f"@font-face {{\n  font-family: '{f['family']}';\n"
            f"  font-style: normal;\n  font-weight: {f['weight']};\n"
            f"  src: url('{rel}') format('woff2');{ur}\n}}")
    return "\n".join(out)


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read()


def localize(html_path: Path) -> int:
    html = html_path.read_text(encoding="utf-8")
    links = re.findall(
        r'<link[^>]+href="(https://fonts\.googleapis\.com/css2\?[^"]+)"',
        html)
    if not links:
        print("localize_fonts: no Google Fonts link — nothing to do")
        return 0
    chars = collect_chars(html)
    if not chars:
        print("localize_fonts WARN: no visible chars extracted — skip")
        return 0
    text_param = urllib.parse.quote(chars[:400])
    fonts_dir = html_path.parent / "assets" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    all_faces: list[dict] = []
    for link in links:
        base, _, q = link.partition("?")
        q_clean = re.sub(r"&?text=[^&]*", "", q)
        subset_url = f"{base}?{q_clean}&text={text_param}"
        try:
            css = _fetch(subset_url).decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"localize_fonts FAILED: subset css {exc}")
            return 1
        for f in parse_subset_css(css):
            try:
                data = _fetch(f["url"])
            except Exception as exc:
                print(f"localize_fonts FAILED: woff2 {exc}")
                return 1
            h = hashlib.sha256(f["url"].encode()).hexdigest()[:8]
            _ext = {"truetype": "ttf"}.get(f.get("format"), "woff2")
            name = (f"{h}_{re.sub(r'[^A-Za-z0-9.-]', '_', f['family'])}"
                    f"-{f['weight']}.{_ext}")
            (fonts_dir / name).write_bytes(data)
            f["_file"] = name
            all_faces.append(f)
            print(f"localize_fonts: {f['family']} {f['weight']} -> "
                  f"assets/fonts/{name} ({len(data) // 1024} KB)")
    if not all_faces:
        print("localize_fonts FAILED: no @font-face parsed")
        return 1
    files = {f["url"]: f"assets/fonts/{f['_file']}"
             for f in all_faces if "_file" in f}
    block = build_font_face(all_faces, files)
    html = re.sub(r'<link[^>]+href="https://fonts\.googleapis\.com/css2[^"]*"[^>]*>',
                  "", html)
    html = html.replace("</head>", f"<style>\n{block}\n</style>\n</head>", 1)
    html_path.write_text(html, encoding="utf-8")
    residual = re.findall(r"fonts\.googleapis\.com", html)
    if residual:
        print("localize_fonts FAILED: google fonts link still present")
        return 1
    print(f"localize_fonts: {len(all_faces)} face(s) localized — "
          "product is link-free")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", required=True)
    args = ap.parse_args()
    html_path = Path(args.html)
    if not html_path.is_file():
        print(f"localize_fonts: html not found: {html_path}")
        return 1
    return localize(html_path)


if __name__ == "__main__":
    sys.exit(main())
