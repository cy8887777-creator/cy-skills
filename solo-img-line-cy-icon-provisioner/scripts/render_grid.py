#!/usr/bin/env python3
"""render_grid.py — 候选图标编号网格对比图（视觉批审用）

用法：
  python render_grid.py --refs lucide:sword tabler:sword game-icons:crossed-swords \
      --out grid.png [--color "#333"] [--cell 96] [--label]

流程：候选 SVG → 拼编号网格 HTML → Edge/Chrome headless 截图 → PNG
输出：PNG 路径（read_image 一次看一批；每格左上角编号对应 refs 顺序）
退出码: 0 成功 / 1 全部候选无效 / 2 截图失败或环境缺失
依赖: 标准库 + 本机 msedge 或 chrome（headless 截图）
"""
import argparse, html, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from iconify_fetch import build_svg, fetch_local, fetch_api, DEFAULT_LIBS, DEFAULT_CACHE
except ImportError:
    print("ERROR render_grid.py must be deployed together with iconify_fetch.py", file=sys.stderr)
    sys.exit(2)

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]
MIN_CELL = 18
TIMEOUT = 60


def find_browser():
    for p in EDGE_CANDIDATES:
        if os.path.isfile(p):
            return p
    for name in ("msedge", "chrome"):
        w = shutil.which(name)
        if w:
            return w
    return None


def _svg_fragments(svg_text, color):
    """统一解析：提取 viewBox 与内体，应用改色，返回 (viewBox, inner) 或 (None, None)。"""
    if color:
        svg_text = svg_text.replace("currentColor", color)
    m = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', svg_text)
    vb = m.group(1) if m else "0 0 24 24"
    if svg_text.strip().startswith("<?xml"):
        svg_text = svg_text.split("?>", 1)[1]
    start = svg_text.find("<svg")
    if start == -1:
        return None, None
    gt = svg_text.find(">", start)
    inner = svg_text[gt + 1: svg_text.rfind("</svg>")]
    return vb, inner


def resolve_svg(ref, libs, cache, color):
    """返回 (viewBox, inner) 或 (None, None)。支持 prefix:name / svg 文件路径 / data URI。"""
    if ref.startswith("data:"):
        try:
            from urllib.parse import unquote
            payload = ref.split(",", 1)[1]
            svg_text = unquote(payload)
        except Exception:
            return None, None
        return _svg_fragments(svg_text, color)
    if ref.startswith("http://") or ref.startswith("https://"):
        print("SKIP remote URL not supported: %s" % ref, file=sys.stderr)
        return None, None
    if os.path.isfile(ref):
        try:
            with open(ref, encoding="utf-8") as f:
                return _svg_fragments(f.read(), color)
        except Exception:
            return None, None
    if ":" not in ref:
        return None, None
    prefix, name = ref.split(":", 1)
    icon, _coll = fetch_local(prefix, name, libs)
    if icon is None:
        try:
            icon = fetch_api(prefix, name, cache)
        except Exception:
            return None, None
    if icon is None:
        return None, None
    svg = build_svg(icon, {"width": icon.get("width"), "height": icon.get("height")}, color)
    return _svg_fragments(svg, color)


def main():
    ap = argparse.ArgumentParser(description="candidate icon grid image for batch visual review")
    ap.add_argument("--refs", nargs="+", required=True, help="prefix:name / svg path / data URI")
    ap.add_argument("--out", required=True, help="output png path")
    ap.add_argument("--color", help="replace currentColor with hex")
    ap.add_argument("--cell", type=int, default=96, help="cell size px (min %d)" % MIN_CELL)
    ap.add_argument("--label", action="store_true", help="show ref text under each cell")
    ap.add_argument("--libs", default=DEFAULT_LIBS)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    args = ap.parse_args()

    cell = max(MIN_CELL, args.cell)
    cells, valid = [], 0
    for i, ref in enumerate(args.refs, 1):
        vb, inner = resolve_svg(ref, args.libs, args.cache, args.color)
        if inner is None:
            inner = '<text x="12" y="14" font-size="9" fill="#c00">miss</text>'
            vb = vb or "0 0 24 24"
        else:
            valid += 1
        label = html.escape(ref) if args.label else ""
        cells.append(
            '<div class="c"><div class="n">%d</div><svg viewBox="%s" width="%d" height="%d">%s</svg>'
            '<div class="l">%s</div></div>' % (i, html.escape(vb), cell - 18, cell - 18, inner, label)
        )
    if valid == 0:
        print("no valid candidates (all miss) — not rendering", file=sys.stderr)
        return 1

    cols = min(6, max(3, int(len(cells) ** 0.5) + 1))
    rows = (len(cells) + cols - 1) // cols
    html_doc = """<!doctype html><meta charset="utf-8"><style>
body{margin:0;background:#fff;font:10px Consolas,monospace}
.g{display:grid;grid-template-columns:repeat(%d,1fr);gap:6px;padding:6px}
.c{position:relative;border:1px solid #e3e3e3;border-radius:6px;height:%dpx;display:flex;
align-items:center;justify-content:center;background:#fff}
.n{position:absolute;top:2px;left:4px;font-size:11px;font-weight:700;color:#fff;background:#2563eb;
border-radius:4px;padding:0 5px;z-index:2}
.l{position:absolute;bottom:2px;left:3px;right:3px;font-size:8px;color:#666;overflow:hidden;
white-space:nowrap;text-overflow:ellipsis}
svg{max-width:70%%;max-height:70%%}
</style><div class="g">%s</div>""" % (cols, cell, "".join(cells))

    tmp_html = os.path.join(tempfile.gettempdir(), "icon-grid-%d.html" % os.getpid())
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html_doc)

    edge = find_browser()
    if not edge:
        print("no headless browser found (msedge/chrome)", file=sys.stderr)
        return 2
    profile = os.path.join(tempfile.gettempdir(), "edge-icongrid-%d" % os.getpid())
    # 余量按实测反推：DPI 缩放下窄窗口会挤压 grid 列导致后列塌陷（680px/3列 已验证稳定）
    win_w = int(cols * cell * 1.8) + 60
    win_h = int(rows * cell * 1.3) + 60
    try:
        rc = subprocess.run([edge, "--headless", "--disable-gpu", "--no-first-run",
                             "--user-data-dir=" + profile, "--virtual-time-budget=3000",
                             "--screenshot=" + os.path.abspath(args.out),
                             "--window-size=%d,%d" % (win_w, win_h),
                             tmp_html], capture_output=True, timeout=TIMEOUT)
        if rc.returncode != 0 or not os.path.isfile(args.out):
            print("screenshot failed: rc=%s" % rc.returncode, file=sys.stderr)
            return 2
    except subprocess.TimeoutExpired:
        print("screenshot timeout (%ss)" % TIMEOUT, file=sys.stderr)
        return 2
    finally:
        try:
            os.remove(tmp_html)
        except OSError:
            pass
    print("GRID %s (%d candidates, %d valid)" % (os.path.abspath(args.out), len(cells), valid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
