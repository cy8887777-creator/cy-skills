#!/usr/bin/env python3
"""build_icons_json.py — 把本地 SVG 目录编译成 Iconify JSON 格式（每库一个 .json）

用法：
  python build_icons_json.py <svg目录> --out <prefix>.json [--prefix <prefix>] [--default-size 24]

说明：
  输入：递归收集目录下全部 .svg（文件名 = 图标名，子目录名 slug 化后作名称前缀）
  输出：Iconify JSON {"prefix","icons":{name:{body,height,width}},"aliases":{}}
  body = <svg> 内部标记：根上的展示属性（fill/stroke 等）包 <g> 保留，xmlns/尺寸除外
依赖: 仅标准库。
"""
import argparse, json, os, re, sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ROOT_DROP_ATTRS = {"xmlns", "viewBox", "width", "height", "version"}
ROOT_KEEP_ATTRS = {"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
                   "stroke-dasharray", "opacity", "class", "style", "fill-opacity", "fill-rule"}
_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slug(s):
    s = _SLUG_RE.sub("-", s.lower())
    return re.sub(r"-{2,}", "-", s).strip("-")


def parse_svg(path, default_size):
    """解析单个 SVG → {"body","width","height"}；解析失败返回 (None, 原因)。"""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return None, "parse error: %s" % e
    except Exception as e:
        return None, "read error: %s" % e
    root = tree.getroot()
    tag = root.tag
    if tag == "svg":  # 裸 <svg>（无 xmlns）按 SVG 命名空间兜底
        tag = "{%s}svg" % SVG_NS
    if tag != "{%s}svg" % SVG_NS:
        return None, "root is not <svg>"

    vb = root.get("viewBox")
    width = root.get("width")
    height = root.get("height")

    def _num(v):
        if v is None:
            return None
        m = re.match(r"^\s*(-?[0-9.]+)\s*(px)?\s*$", v)  # viewBox 坐标可为负（如 kubai 的 -2.5）
        if not m:  # 含 % 或其他单位 → 视为无效，走 default
            return None
        f = float(m.group(1))
        return int(f) if f == int(f) else f

    if vb:
        parts = vb.replace(",", " ").split()
        # viewBox 的 min-x/min-y 是画布偏移（如 kubai 的 "-2.5 -5.5 36 36"），必须进 left/top，
        # 丢了交付渲染就会偏移/裁剪；画布尺寸同样以 viewBox 为准（根 width/height 可能只是显示尺寸）
        x, y = _num(parts[0]) if len(parts) > 0 else None, _num(parts[1]) if len(parts) > 1 else None
        w, h = _num(parts[2]) if len(parts) > 2 else None, _num(parts[3]) if len(parts) > 3 else None
    else:
        x, y = None, None
        w, h = _num(width), _num(height)

    # 根上展示属性 → <g> 包裹保留（fill/stroke 等丢了会渲染成实心黑块）
    keep = {}
    for k, v in root.attrib.items():
        short = k.split("}")[-1]
        if short in ROOT_KEEP_ATTRS and not k.startswith("{"):  # 带命名空间的属性（xlink:href 等）原样留在子元素
            keep[short] = v
    inner_parts = []
    if keep:
        g_attrs = " ".join('%s="%s"' % (k, v.replace('"', "&quot;")) for k, v in keep.items())
        inner_parts.append("<g %s>" % g_attrs)
    for child in root:
        inner_parts.append(ET.tostring(child, encoding="unicode"))
    if keep:
        inner_parts.append("</g>")
    body = "".join(inner_parts)
    # 只剥根级 xmlns 声明残留（子元素的 xmlns:xxx 声明保留——删了会 unbound prefix）
    body = re.sub(r"\sxmlns=\"[^\"]*\"", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return None, "empty body"
    return {"body": body, "left": x, "top": y,
            "width": w or _num(width) or default_size,
            "height": h or _num(height) or default_size}, None


def main():
    ap = argparse.ArgumentParser(description="compile a directory of SVGs into one Iconify JSON")
    ap.add_argument("src", help="SVG directory (recursive)")
    ap.add_argument("--out", required=True, help="output <prefix>.json path")
    ap.add_argument("--prefix", help="collection prefix (default: output filename stem)")
    ap.add_argument("--default-size", type=int, default=24)
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        print("ERROR src directory not found: %s" % args.src, file=sys.stderr)
        return 2

    prefix = args.prefix or os.path.splitext(os.path.basename(args.out))[0]
    icons, aliases = {}, {}
    count, parse_fail, slug_clash = 0, [], 0
    for dirpath, _dirnames, filenames in os.walk(args.src):
        rel = os.path.relpath(dirpath, args.src)
        for fn in sorted(filenames):
            if not fn.lower().endswith(".svg"):
                continue
            base = slug(fn[:-4])
            if not base:
                parse_fail.append("%s: slug empty" % fn)
                continue
            name = base if rel == "." else (slug(rel.replace(os.sep, "-")) + "-" + base)
            icon, err = parse_svg(os.path.join(dirpath, fn), args.default_size)
            if not icon:
                parse_fail.append("%s: %s" % (fn, err))
                continue
            if name in icons:
                slug_clash += 1
                continue
            entry = {"body": icon["body"], "width": icon["width"], "height": icon["height"]}
            if icon.get("left") not in (None, 0) or icon.get("top") not in (None, 0):
                entry["left"], entry["top"] = icon["left"], icon["top"]
            icons[name] = entry
            count += 1

    out = {"prefix": prefix, "icons": icons, "aliases": aliases,
           "width": args.default_size, "height": args.default_size}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("compiled %d icons -> %s, %.1f KB | parse-fail %d, slug-clash %d" % (
        count, args.out, os.path.getsize(args.out) / 1024, len(parse_fail), slug_clash))
    for line in parse_fail[:10]:
        print("  skipped: %s" % line, file=sys.stderr)
    if slug_clash:
        print("  skipped slug clashes: %d" % slug_clash, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
