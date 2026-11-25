"""
scripts/core/gen_assets.py — 素材章形态生成器（v4.0 · C 组）

用法（唯一）：python gen_assets.py <项目out目录> [assets源目录]

做什么：扫描 assets 源目录的图片，产素材章缩略网格 HTML（96px 等高 + 棋盘格底衬 +
lightbox + 语义名占位），替换 design-system.html 的 s13「素材资产」章 APPLICATION 区。
语义名默认 = 文件名去扩展；agent 在定案时补语义名/分组归类。

图源优先级：assets源目录参数 > <out>/system-spec/assets > <out>/assets。
找不到图源或目标章无「素材资产」label 时安全跳过。
"""
import base64
import io
import os
import re
import sys

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def b64_embed(path):
    """小图内嵌 base64（产物自包含）；>200KB 的引用相对路径"""
    size = os.path.getsize(path)
    ext = os.path.splitext(path)[1][1:].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif", "svg": "svg+xml"}[ext]
    if ext == "svg":
        data = io.open(path, encoding="utf-8", errors="ignore").read()
        return "data:image/svg+xml;base64," + base64.b64encode(data.encode()).decode()
    if size <= 200 * 1024:
        return "data:image/%s;base64,%s" % (mime, base64.b64encode(io.open(path, "rb").read()).decode())
    return None  # 大图走文件引用


def collect(src_dir):
    out = []
    for root, _dirs, files in os.walk(src_dir):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext not in IMG_EXT:
                continue
            p = os.path.join(root, f)
            name = os.path.splitext(f)[0]
            page = os.path.basename(root)
            out.append({"path": p, "file": f, "name": name, "page": page, "size": os.path.getsize(p)})
    return out


def grid_html(items):
    cells = []
    for it in items[:200]:
        src = b64_embed(it["path"])
        if not src:
            cells.append('<div class="ast-cell"><div style="height:96px;display:grid;place-items:center;'
                         'font-size:10px;color:#9CA3AF">大图 %s（见 assets/）</div>'
                         '<div class="nm">%s</div></div>' % (it["file"], it["name"]))
            continue
        label = "%s · %s" % (it["name"], it["page"])
        cells.append(
            '<div class="ast-cell" title="%s">'
            '<div style="height:96px;display:grid;place-items:center;'
            'background:repeating-conic-gradient(#f6f7f9 0 25%%,#fff 0 50%%) 0 0/16px 16px;'
            'border-radius:8px;overflow:hidden">'
            '<img src="%s" style="max-height:96px;max-width:100%%;object-fit:contain" alt="%s"></div>'
            '<div class="nm" style="font-size:10px;color:#626A76;margin-top:4px;'
            'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">%s</div></div>'
            % (label, src, it["name"], label))
    if not cells:
        return None
    return ('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));'
            'gap:12px">' + "".join(cells) + "</div>"
            + '<p class="note" style="margin-top:10px">网格由 gen_assets 按资产目录自动产出；'
              "语义名/分组归类由 agent 在定案时补（文件名是占位）。</p>")


def main():
    if len(sys.argv) < 2:
        print("用法: python gen_assets.py <项目out目录> [assets源目录]", file=sys.stderr)
        return 2
    out_dir = sys.argv[1]
    html_path = os.path.join(out_dir, "design-system.html")
    if not os.path.exists(html_path):
        print("[FAIL] 缺 %s" % html_path, file=sys.stderr)
        return 2
    srcs = [sys.argv[2]] if len(sys.argv) > 2 else [
        os.path.join(out_dir, "system-spec", "assets"), os.path.join(out_dir, "assets")]
    items = []
    for s in srcs:
        if os.path.isdir(s):
            items = collect(s)
            break
    if not items:
        print("[skip] 无资产图源（%s）——素材章保持现状" % srcs, file=sys.stderr)
        return 0
    grid = grid_html(items)
    if not grid:
        print("[skip] 图源为空")
        return 0
    html = io.open(html_path, encoding="utf-8").read()
    m = re.search(r'<section class="chapter" id="s13">(.*?)</section>', html, re.S)
    if not m or "素材资产" not in m.group(1):
        print("[skip] 无 s13 素材资产章（形态不同构），未改动")
        return 0
    s13 = m.group(1)
    i = s13.find("素材资产")  # ch-head 之后第一个 block 起
    blk = s13.find('<div class="block">', i)
    u = s13.find('<div class="block"><div class="spec-label">USAGE', blk)
    if blk < 0 or u < 0:
        print("[skip] 素材章边界定位失败，未改动", file=sys.stderr)
        return 0
    new_block = ('<div class="block"><div class="spec-label">APPLICATION · 素材网格（%d 枚 · 语义名待补）</div>%s</div>'
                 % (min(len(items), 200), grid))
    s13_new = s13[:blk] + new_block + "\n" + s13[u:]
    html = html[:m.start(1)] + s13_new + html[m.end(1):]
    io.open(html_path, "w", encoding="utf-8", newline="\n").write(html)
    print("[ok] 素材网格重渲染：%d 枚（语义名待 agent 补）" % min(len(items), 200))
    return 0


if __name__ == "__main__":
    sys.exit(main())
