#!/usr/bin/env python3
"""iconify_fetch.py — 图标取用一体脚本（查本地JSON → 查cache → Iconify API → 落缓存）

用法：
  搜索:  python iconify_fetch.py --search sword --prefix lucide,tabler [--limit 20]
  取图:  python iconify_fetch.py --fetch lucide:sword [--color "#e91e63"] [--out sword.svg]
  批取:  python iconify_fetch.py --fetch lucide:sword tabler:user --dir ./out

退出码: 0 命中（批量=全部命中）/ 1 未命中或批量部分命中 / 2 参数错误
依赖: 仅 Python 标准库。本地库目录 = 技能包 assets/icons-json/（可用 --libs 覆盖）。
"""
import argparse, json, os, re, sys, urllib.request

API = "https://api.iconify.design"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LIBS = os.path.normpath(os.path.join(HERE, "..", "assets", "icons-json"))
DEFAULT_CACHE = os.path.join(HERE, "..", "cache")
DEFAULT_SIZE = 24
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

_LIB_CACHE = {}  # prefix -> parsed json（进程内记忆化，避免大库重复 load）


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_local(prefix, libs_dir):
    p = os.path.join(libs_dir, prefix + ".json")
    if not os.path.isfile(p):
        return None
    if prefix in _LIB_CACHE:
        return _LIB_CACHE[prefix]
    try:
        data = _load_json(p)
    except Exception as e:
        print("WARN broken lib json skipped: %s (%s)" % (p, e), file=sys.stderr)
        return None
    _LIB_CACHE[prefix] = data
    return data


def _norm(s):
    return s.lower().replace("-", "").replace("_", "")


def _resolve_in_collection(data, name):
    """解析集合内图标名：直查 icons → 别名 parent → 覆盖键浅合并。返回 (icon, matched_key)。"""
    icons = data.get("icons") or {}
    if name in icons:
        return dict(icons[name]), name
    aliases = data.get("aliases") or {}
    if name in aliases:
        av = aliases[name]
        parent = av.get("parent")
        if parent and parent in icons:
            icon = dict(icons[parent])
            for k in ("width", "height", "body"):
                if k in av:
                    icon[k] = av[k]
            return icon, name
    return None, None


def _inherit_size(icon, data):
    """尺寸继承：icon 缺 width/height 时继承集合顶层；集合顶层也没有 → 默认 24。
    修复：bi.json 顶层连宽高键都没有，get 链容错；非 24px 库（ph 256/game-icons 512/noto 128…）不再被裁切。"""
    top_w = (data or {}).get("width")
    top_h = (data or {}).get("height")
    if not icon.get("width"):
        icon["width"] = top_w or DEFAULT_SIZE
    if not icon.get("height"):
        icon["height"] = top_h or DEFAULT_SIZE
    return icon


def local_search(keyword, libs_dir, prefixes=None, limit=20):
    kw = _norm(keyword)
    hits = []
    if not os.path.isdir(libs_dir):
        return hits
    for fn in sorted(os.listdir(libs_dir)):
        if not fn.endswith(".json"):
            continue
        prefix = fn[:-5]
        if prefixes and prefix not in prefixes:
            continue
        data = load_local(prefix, libs_dir)
        if not data:
            continue
        names = list((data.get("icons") or {}).keys()) + list((data.get("aliases") or {}).keys())
        for name in names:
            if kw in _norm(name):
                ref = "%s:%s" % (prefix, name)
                if ref not in hits:
                    hits.append(ref)
    # 精确命中置顶、其余字典序——变体多时真身（如 user 在 69 个 user-* 里）不会被 limit 挤出
    hits.sort(key=lambda r: (r.split(":", 1)[1] not in (keyword, kw), r))
    return hits[:limit]


def build_svg(icon, collection=None, color=None):
    icon = _inherit_size(dict(icon), collection)
    body = icon.get("body", "")
    w, h = icon["width"], icon["height"]
    # icon 级 left/top 是画布偏移（Iconify 标准，如 kubai 的 -2.5/-5.5）；无偏移省略 → 0 0，兼容旧库
    left, top = icon.get("left", 0), icon.get("top", 0)
    if color:
        if not _HEX_RE.match(color):
            print("WARN invalid color %r (expect #rgb/#rrggbb), skip recolor" % color, file=sys.stderr)
        else:
            n = body.count("currentColor")
            if n == 0:
                print("WARN no currentColor in body (multicolor icon?) — recolor was a no-op", file=sys.stderr)
            else:
                body = body.replace("currentColor", color)
                if n > 1:
                    print("WARN replaced currentColor in %d places (multicolor layer semantics may change)" % n, file=sys.stderr)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s" width="%s" height="%s">%s</svg>' % (left, top, w, h, w, h, body)


def fetch_local(prefix, name, libs_dir):
    data = load_local(prefix, libs_dir)
    if not data:
        return None, None
    icon, _ = _resolve_in_collection(data, name)
    if icon is None:
        return None, None
    return _inherit_size(icon, data), data


def fetch_api(prefix, name, cache_dir, timeout=20):
    cache_path = os.path.join(cache_dir, prefix + ".json")
    cache = {}
    if os.path.isfile(cache_path):
        try:
            cache = _load_json(cache_path)
        except Exception as e:
            print("WARN broken cache skipped (will rebuild): %s (%s)" % (cache_path, e), file=sys.stderr)
            cache = {}
    icon, _ = _resolve_in_collection(cache, name)
    if icon is not None:
        return _inherit_size(icon, cache)  # 修复：缓存命中同样继承尺寸（原来只有 API 新取分支做）
    url = "%s/%s.json?icons=%s" % (API, prefix, name)
    req = urllib.request.Request(url, headers={"User-Agent": "icon-provisioner/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    icon, _ = _resolve_in_collection(data, name)
    if icon is None:
        return None
    # 合并回缓存（icons + aliases 都沉淀；原子写防截断）
    cache.setdefault("icons", {}).update(data.get("icons") or {})
    cache.setdefault("aliases", {}).update(data.get("aliases") or {})
    for k in ("width", "height"):
        if data.get(k) and not cache.get(k):
            cache[k] = data[k]
    os.makedirs(cache_dir, exist_ok=True)
    tmp = cache_path + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, cache_path)
    return _inherit_size(icon, data)


def main():
    ap = argparse.ArgumentParser(description="icon fetch/search: local JSON -> cache -> Iconify API")
    ap.add_argument("--search", help="keyword search over local JSON key names")
    ap.add_argument("--fetch", nargs="+", metavar="PREFIX:NAME", help="fetch icon(s)")
    ap.add_argument("--prefix", help="comma-separated prefix whitelist for --search")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--color", help="replace currentColor with this hex, e.g. #e91e63")
    ap.add_argument("--out", help="write single SVG to file (default stdout)")
    ap.add_argument("--dir", help="write multiple SVGs to directory as <prefix>-<name>.svg")
    ap.add_argument("--libs", default=DEFAULT_LIBS, help="local icons-json directory")
    ap.add_argument("--cache", default=DEFAULT_CACHE, help="cache directory")
    args = ap.parse_args()

    if args.search and args.fetch:
        print("ERROR --search and --fetch are mutually exclusive", file=sys.stderr)
        return 2
    if not args.search and not args.fetch:
        ap.print_usage()
        return 2
    if args.out and len(args.fetch or []) > 1:
        print("ERROR --out applies to a single --fetch ref; use --dir for batches", file=sys.stderr)
        return 2

    prefixes = [p.strip() for p in args.prefix.split(",")] if args.prefix else None

    if args.search:
        hits = local_search(args.search, args.libs, prefixes, args.limit)
        for h in hits:
            print(h)
        return 0 if hits else 1

    for out_dir in filter(None, [args.dir, os.path.dirname(os.path.abspath(args.out)) if args.out else None]):
        os.makedirs(out_dir, exist_ok=True)

    ok, miss = [], []
    for ref in args.fetch:
        if ":" not in ref:
            print("BADREF %s (expect prefix:name)" % ref, file=sys.stderr)
            miss.append(ref)
            continue
        prefix, name = ref.split(":", 1)
        icon, coll = fetch_local(prefix, name, args.libs)
        source = "local"
        if icon is None:
            try:
                icon = fetch_api(prefix, name, args.cache)
                source = "api+cache"
            except Exception as e:
                print("APIFAIL %s:%s %s" % (prefix, name, e), file=sys.stderr)
        if icon is None:
            print("MISS %s:%s" % (prefix, name), file=sys.stderr)
            miss.append(ref)
            continue
        svg = build_svg(icon, coll, args.color)
        if args.dir:
            out = os.path.join(args.dir, "%s-%s.svg" % (prefix, name))
            with open(out, "w", encoding="utf-8") as f:
                f.write(svg)
            print("OK %s:%s -> %s [%s]" % (prefix, name, out, source))
        elif args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(svg)
            print("OK %s:%s -> %s [%s]" % (prefix, name, args.out, source))
        else:
            print(svg)
        ok.append(ref)

    return 0 if ok and not miss else 1


if __name__ == "__main__":
    sys.exit(main())
