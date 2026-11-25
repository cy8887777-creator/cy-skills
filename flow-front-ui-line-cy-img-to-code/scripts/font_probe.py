#!/usr/bin/env python3
"""font_probe.py — 字体域的样式解析（closed-set render-and-compare）。

职责 = 字体域 resolve_styles 的完整实现：
  1. 从 layout.json 选 program-verified 代表文字块（大/中/小，最多 3 块）
  2. playwright 渲染候选字体池（Google Fonts）的同文字样本（100px 基准行）
  3. 确定性形状比对：IoU 0.6 + 笔画密度 0.25 + 水平投影相关 0.15 → 每块 top (family, weight)
  4. 字号换算：size_css = 100 * 原图墨迹高css / 该组合 100px 渲染墨迹高
  5. 设计系统(--design-system JSON) 优先级高于 probe；冲突记入 conflicts（DS 胜）
  6. 产出 styles.json（带 sourced-from）+ _font_candidates.png + font_probe.json

无 ML、无识图大模型：封闭集 render-and-compare，纯确定性 CV。
在线依赖：Google Fonts CDN。离线/失败 → degraded=true，styles.json 仍写出
（字体域回退为墨迹估算），exit 0 —— 管线继续，绝不阻塞。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TARGET_H = 64
WEIGHTS = [400, 600, 700, 800, 900]
POOL_ARABIC = ["Almarai", "Tajawal", "Alexandria", "IBM Plex Sans Arabic",
               "Readex Pro", "Noto Sans Arabic", "Cairo"]
POOL_LATIN = ["Inter", "Nunito", "Rubik"]
# 中文池（2026-09-30 新增）：纯中文图此前 100% degraded（64 块全被
# CJK 过滤，"no eligible text blocks"）。池限 Google Fonts 可加载的
# 中文族——黑/宋两候选覆盖 UI 主流；更贴近的商用字体走 DS 指定。
POOL_CHINESE = ["Noto Sans SC", "Noto Serif SC"]

# 字形类别（1009-03 类别摇摆闸）：中文池 serif/sans 并存，密度拟合会
# 把"特粗衬线"与"粗黑体"互窜（实测 0.92 虚高选错类别）——类别摇摆
# 即 REVIEW 停机。新加池字体时同步登记。
FONT_CATEGORY = {"Noto Sans SC": "sans", "Noto Serif SC": "serif"}


def pick_blocks(layout, max_blocks=3):
    """选代表文字块：program-verified、池内语言、墨迹高≥8物理px，按
    面积取前 N。阈值 8：精化框是墨迹 bbox（已收缩），18 会误杀小
    字号块（实证：EXP 行精化后 h=8 被旧阈值滤空全部代表块）。
    2026-09-30：CJK 块放行——中文池（POOL_CHINESE）已建立，纯中文图
    不再整体 degraded（事故：电商长图 64 块全被 CJK 过滤）。"""
    blocks = []
    for s in layout.get("skeleton") or []:
        if s.get("type") != "text_block" or s.get("source") != "program":
            continue
        t = (s.get("text") or "").strip()
        if not t or s.get("h", 0) < 8:
            continue
        if not pool_for(t):
            continue
        blocks.append({"idx": s["index"], "text": t[:24],
                       "x": s["x"], "y": s["y"], "w": s["w"], "h": s["h"]})
    blocks.sort(key=lambda b: b["w"] * b["h"], reverse=True)
    return blocks[:max_blocks]


def all_text_blocks(layout):
    """layout.json 里的全部 text_block（全量合同用，不限 source）。"""
    out = []
    for s in layout.get("skeleton") or []:
        if s.get("type") != "text_block":
            continue
        t = (s.get("text") or "").strip()
        if not t:
            continue
        out.append({"idx": s["index"], "text": t[:24],
                    "x": s["x"], "y": s["y"], "w": s["w"], "h": s["h"]})
    return out


def blocks_from_assets(assets_path, img_w, img_h):
    """assets.json 原始标注框 → 候选文字块。

    解除字体线对 layout.json 的串行依赖：标注一落盘，字体线即可与
    抠图管线并行。box_2d 的 ±3~5% 目测误差对字体探测无伤（探测有
    墨迹统计与降级兜底）。idx 取 skeleton 数组下标 —— 与 refine 后
    layout.json 的 index 一致。"""
    data = json.loads(Path(assets_path).read_text(encoding="utf-8"))
    out = []
    for idx, s in enumerate(data.get("skeleton") or []):
        if s.get("type") != "text_block":
            continue
        t = (s.get("text") or "").strip()
        ymin, xmin, ymax, xmax = s["box_2d"]
        h = (ymax - ymin) / 1000.0 * img_h
        # 注意：不过滤 CJK —— 标注 text 是摘要（常混中文描述），且
        # 墨迹估算与语言无关。CJK 过滤只作用于探测代表块（pick_blocks）。
        if not t or h < 18:
            continue
        out.append({"idx": idx, "text": t[:24],
                    "x": round(xmin / 1000.0 * img_w),
                    "y": round(ymin / 1000.0 * img_h),
                    "w": round((xmax - xmin) / 1000.0 * img_w),
                    "h": round(h)})
    return out


def ink_stats_block(src_gray, b, css_div=2.0):
    """非代表块的墨迹估算：size_css = 墨迹高css / 0.72（cap+asc 占
    em 比例的通用近似），weight 由笔画密度分档。永不返回 None——
    墨迹不可辨时先做低对比重试，仍失败则回退块高经验系数
    （cap ≈ 0.62 × 块高）：styles.json 的字号终值不允许缺位，
    模型没有任何目测拍字号的合法空间（field failure 2026-09-29:
    Gold III 目测 15px，实测 12.5px）。
    css_div（2026-10-07）：框平面 → CSS 的除数，由输入来源 × dpr
    共同决定——硬编码 ÷2 对 1x/1.5x 图是错的。"""
    m = ink_crop(src_gray, b["x"], b["y"], b["w"], b["h"])
    if m is None or m.shape[0] < 6:
        # low-contrast retry: 18/255 still separates muted text like
        # the 首页黑改 Gold-III caption (contrast swing ~22)
        m = ink_crop(src_gray, b["x"], b["y"], b["w"], b["h"],
                     pad=5, min_contrast=18)
    if m is None or m.shape[0] < 6:
        return {"size_css": round(b["h"] / css_div * 0.62, 1),
                "weight": 400, "density": None,
                "source_note": "block-height fallback (ink undetectable)"}
    size_css = round((m.shape[0] / css_div) / 0.72, 1)
    dens = float(m.mean())
    if dens > 0.50:
        wt = 800
    elif dens > 0.40:
        wt = 700
    elif dens > 0.32:
        wt = 600
    else:
        wt = 400
    return {"size_css": size_css, "weight": wt, "density": round(dens, 2)}


def ink_mask(gray, min_contrast=30):
    """自适应阈值二值化，方向自适应：边界中位色更亮 → 深字浅底 →
    mask 取暗侧；否则（深底白字）取亮侧。对比幅低于 min_contrast 的
    区域返回空。"""
    lo, hi = float(gray.min()), float(gray.max())
    if hi - lo < min_contrast:
        return np.zeros_like(gray, bool)
    thr = lo + (hi - lo) * 0.45
    border = np.concatenate([gray[:2].ravel(), gray[-2:].ravel(),
                             gray[:, :2].ravel(), gray[:, -2:].ravel()])
    dark_text = float(np.median(border)) > (lo + hi) / 2
    return (gray < thr) if dark_text else (gray > thr)


def ink_crop(gray, x, y, w, h, pad=3, min_contrast=30):
    """裁区域并收紧到墨迹 bbox，返回 bool mask 或 None。"""
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1 = min(gray.shape[1], x + w + pad)
    y1 = min(gray.shape[0], y + h + pad)
    m = ink_mask(gray[y0:y1, x0:x1], min_contrast=min_contrast)
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def norm_mask(m, target_h=TARGET_H):
    h, w = m.shape
    tw = max(4, round(w * target_h / h))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize(
        (tw, target_h), Image.BILINEAR)
    return np.array(im) > 127


def compare(a, b):
    """归一化 mask 相似度：IoU 0.6 + 密度 0.25 + 投影相关 0.15。"""
    W = max(a.shape[1], b.shape[1])
    A = np.zeros((TARGET_H, W), bool)
    B = np.zeros((TARGET_H, W), bool)
    A[:, :a.shape[1]] = a
    B[:, :b.shape[1]] = b
    iou = float((A & B).sum()) / max(1, int((A | B).sum()))
    density = 1.0 - abs(float(A.mean()) - float(B.mean()))
    pa, pb = A.mean(axis=1), B.mean(axis=1)
    corr = (float(np.corrcoef(pa, pb)[0, 1])
            if pa.std() > 0 and pb.std() > 0 else 0.0)
    return 0.6 * iou + 0.25 * density + 0.15 * max(0.0, corr)


def is_arabic(text):
    return any("؀" <= c <= "ۿ" for c in text)


def is_chinese(text):
    return any("一" <= c <= "鿿" for c in text)


def pool_for(text):
    if is_chinese(text):
        return POOL_CHINESE
    return POOL_ARABIC if is_arabic(text) else POOL_LATIN


def _local_font_css(fams, cache_dir: Path):
    """T5 字体本地缓存：把 Google Fonts css2 与 woff2 落盘，样本页改用
    本地 css——CDN 抖动不再让探测降级/超时（同输入同输出）。缓存按
    字体名散列，二次探测零网络。失败时回退 CDN link（返回 None）。"""
    import urllib.request

    cache_dir.mkdir(parents=True, exist_ok=True)
    css_parts = []
    for f in fams:
        key = f.replace(" ", "+")
        css_name = f"{key}%3Awght@{';'.join(map(str, WEIGHTS))}"
        css_file = cache_dir / f"{css_name}.css"
        try:
            if not css_file.is_file():
                url = ("https://fonts.googleapis.com/css2?family="
                       f"{key}:wght@{';'.join(map(str, WEIGHTS))}"
                       "&display=swap")
                req = urllib.request.Request(
                    url, headers={"User-Agent":
                                  "Mozilla/5.0 Chrome/120.0"})
                css_text = urllib.request.urlopen(
                    req, timeout=20).read().decode("utf-8")
                # 把 woff2 指到本地
                import re as _re
                for i, m in enumerate(
                        _re.finditer(r"url\((https://[^)]+)\)",
                                     css_text)):
                    u = m.group(1)
                    wf = cache_dir / f"{key}_{i}.woff2"
                    if not wf.is_file():
                        urllib.request.urlretrieve(u, wf)
                    css_text = css_text.replace(u, wf.name)
                css_file.write_text(css_text, encoding="utf-8")
            css_parts.append(css_file.name)
        except Exception:
            return None  # 任一字体缓存失败 → 整体回退 CDN
    if not css_parts:
        return None
    return cache_dir, css_parts


def build_sample_html(blocks):
    """每块 × 各自字体池 × 字重，一行一个 100px 基准样本。"""
    fams = sorted({f for b in blocks for f in pool_for(b["text"])})
    cached = None
    try:
        cached = _local_font_css(
            fams, Path(__file__).resolve().parent.parent / "assets"
            / "fonts")
    except Exception:
        cached = None
    if cached:
        cache_dir, css_parts = cached
        links = "".join(
            f'<link rel="stylesheet" '
            f'href="{(cache_dir / name).resolve().as_uri()}">'
            for name in css_parts)
    else:
        links = "".join(
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
            f'?family={f.replace(" ", "+")}:wght@'
            f'{";".join(map(str, WEIGHTS))}&display=swap">'
            for f in fams)
    rows, meta = [], []
    i = 0
    for b in blocks:
        for f in pool_for(b["text"]):
            for wt in WEIGHTS:
                rows.append(
                    f'<div class="row" data-i="{i}" '
                    f'style="font-family:\'{f}\';font-weight:{wt}">'
                    f'{b["text"]}</div>')
                meta.append({"i": i, "block": b, "family": f, "weight": wt})
                i += 1
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'>" + links +
            "<style>*{margin:0}body{background:#140b26;color:#fff}"
            ".row{font-size:100px;line-height:1.25;white-space:nowrap;"
            "padding:6px 10px}</style></head><body>" + "".join(rows) +
            "</body></html>")
    return html, meta, fams


def render_and_score(src_gray, blocks, out_png):
    """playwright 渲染全部样本并比对。
    返回 (ranked_per_block, h100_map, degraded, reason)。"""
    from playwright.sync_api import sync_playwright

    html, meta, fams = build_sample_html(blocks)
    page_html = (out_png.parent / "_font_probe_page.html").resolve()
    page_html.write_text(html, "utf-8")

    ranked = {b["idx"]: [] for b in blocks}
    h100 = {}          # (family, weight) -> 100px 墨迹高 px
    shots = {}         # i -> 归一化 mask
    degraded, reason = False, ""
    try:
        with sync_playwright() as pw:
            browser, _channel = _launch(pw)
            try:
                page = browser.new_page(
                    viewport={"width": 2200, "height": 900})
                page.goto(page_html.as_uri())
                page.evaluate("() => document.fonts.ready")
                page.wait_for_timeout(600)
                available = page.evaluate(
                    """(fams) => fams.map(f => ({
                        f,
                        ok: [400,600,700,800,900].some(w =>
                            document.fonts.check(`700 40px '${f}'`))
                    }))""", fams)
                ok_fams = {r["f"] for r in available if r["ok"]}
                for m in meta:
                    if m["family"] not in ok_fams:
                        continue
                    el = page.locator(f'[data-i="{m["i"]}"]')
                    png = el.screenshot()
                    g = np.asarray(
                        Image.open(__import__("io").BytesIO(png))
                        .convert("L"), dtype=float)
                    msk = ink_crop(g, 0, 0, g.shape[1], g.shape[0], pad=1)
                    if msk is None or msk.shape[0] < 8:
                        continue
                    h100[(m["family"], m["weight"])] = msk.shape[0]
                    shots[m["i"]] = norm_mask(msk)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 — 降级而非阻塞
        return ({b["idx"]: [] for b in blocks}, {},
                True, f"render failed: {exc}")

    if not shots:
        return ({b["idx"]: [] for b in blocks}, {},
                True, "no renderable samples")

    for b in blocks:
        src_m = ink_crop(src_gray, b["x"], b["y"], b["w"], b["h"])
        if src_m is None:
            continue
        src_n = norm_mask(src_m)
        cand = []
        for m in meta:
            if m["block"]["idx"] != b["idx"] or m["i"] not in shots:
                continue
            score = compare(src_n, shots[m["i"]])
            cand.append({"family": m["family"], "weight": m["weight"],
                         "score": round(score, 4)})
        cand.sort(key=lambda c: -c["score"])
        ranked[b["idx"]] = cand[:6]

    _write_candidates_png(src_gray, blocks, ranked, meta, shots, out_png)
    return ranked, h100, False, ""


def _write_candidates_png(src_gray, blocks, ranked, meta, shots, out_png):
    """原图块 | top1..top3 渲染 并排拼图（白底黑字显示）。"""
    tiles = []
    for b in blocks:
        src_m = ink_crop(src_gray, b["x"], b["y"], b["w"], b["h"])
        if src_m is None:
            continue
        row = [_mask_tile(src_m)]
        for c in ranked.get(b["idx"], [])[:3]:
            for m in meta:
                if (m["block"]["idx"] == b["idx"]
                        and m["family"] == c["family"]
                        and m["weight"] == c["weight"]
                        and m["i"] in shots):
                    row.append(_mask_tile(shots[m["i"]]))
                    break
        tiles.append(row)
    if not tiles:
        return
    H = TARGET_H + 26
    W = max(len(r) for r in tiles) * (220 + 10) + 10
    sheet = Image.new("RGB", (W, H * len(tiles) + 10), (24, 24, 24))
    y = 5
    for row in tiles:
        x = 10
        for t in row:
            sheet.paste(t, (x, y))
            x += 220 + 10
        y += H
    sheet.save(out_png)


def _mask_tile(mask):
    """bool mask → 白底黑字 220 宽 tile。"""
    m = norm_mask(mask)
    disp = (255 - (m * 200)).astype(np.uint8)
    im = Image.fromarray(disp).convert("RGB")
    scale = 220 / im.width
    return im.resize((220, max(20, int(im.height * scale))),
                     Image.NEAREST)


def _launch(pw):
    """与 verify_page.py 相同的浏览器启动逻辑（chrome 优先，回退 chromium）。"""
    for channel in ("chrome", "msedge", "chromium"):
        try:
            return pw.chromium.launch(channel=channel, headless=True), channel
        except Exception:  # noqa: BLE001
            continue
    return pw.chromium.launch(headless=True), "chromium"


def load_design_system(path):
    """设计系统 JSON。约定键（全部可选）:
    font_family / font_family_latin / weights: [...]
    解析失败返回 (None, reason)。"""
    if not path or not Path(path).is_file():
        return None, "no design-system file"
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"design-system parse failed: {exc}"
    if not isinstance(data, dict):
        return None, "design-system must be a JSON object"
    return data, ""


def _img_md5(path) -> str:
    """源图内容指纹（锁失效判断）——同尺寸换图也逃不掉。"""
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True, help="source screenshot path")
    ap.add_argument("--layout", help="layout.json path (post-pipeline)")
    ap.add_argument("--assets", help="assets.json path (pre-pipeline — "
                                     "enables the parallel text line)")
    ap.add_argument("--out", required=True, help="work directory")
    ap.add_argument("--design-system", help="design-system JSON (optional)")
    ap.add_argument("--pool", help="comma-separated font family override")
    ap.add_argument("--dpr", type=float, default=None,
                    help="override the box-plane heuristic (assets/"
                         "legacy-layout mode); new-format layouts carry "
                         "dpr and ignore this")
    ap.add_argument("--reprobe", action="store_true",
                    help="ignore an existing styles.json and re-run the "
                         "probe (default: locked)")
    args = ap.parse_args()
    if not args.layout and not args.assets:
        ap.error("--layout or --assets is required")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Lock: an existing non-degraded styles.json IS the contract. The
    # probe's closed-set verdict varies with the font pool, so re-running
    # on the same image can mint a DIFFERENT baseline (field failure
    # 2026-09-29: same screenshot → Tajawal vs Noto/IBM Plex mix across
    # two runs) and every downstream block inherits the drift. Re-probe
    # only with --reprobe, when the source image changes (lock carries
    # source_size), or on a --layout refinement run (family stays
    # locked, size/weight refresh — the refinement was previously
    # dead code: the lock returned before it could ever run).
    # —— 块清单与字号平面：先于 lock 校验 ——（2026-10-07 第三次评审：
    # lock 失效条件必须含字号平面——同图换 --dpr 重探，旧 size_css
    # 全部作废，只比 content md5 挡不住）
    # 轻量输入优先（第五轮评审）：锁命中即 return 0，整图浮点数组
    # 只在确认要探测后才转——此处只读图片尺寸。
    src_w, src_h = Image.open(args.image).size

    # 坐标平面合同（2026-10-07）：缩放由输入来源 × dpr 共同决定，
    # 禁止硬编码 ÷2：
    #   --assets : 标注框 = 物理 px（模型在物理源图上标注）
    #              → css_div = --dpr 或墨迹锚点检测（与 extract 同一
    #              算法，第五轮评审：纯宽度启发式把 563px 的 1.5x 图
    #              猜成 2x，精化轮平面切换又引发锁失效重探 family——
    #              两条并行线必须消费同一 dpr）
    #   --layout : 带 dpr 字段（新格式）= 逻辑 px → css_div = dpr，
    #              且框须 ×dpr 回物理平面再裁 src 墨迹（平面匹配）；
    #              无 dpr 字段（旧格式）= 物理 px → 启发式
    probe_mult, css_div = 1.0, 2.0
    layout = None
    if args.assets:
        img_w, img_h = src_w, src_h
        if args.dpr:
            css_div = float(args.dpr)
        else:
            try:
                from extract_assets import detect_dpr
                _raw_top = json.loads(
                    Path(args.assets).read_text(encoding="utf-8"))
                _skel_raw = (_raw_top.get("skeleton")
                             if isinstance(_raw_top, dict) else None) or []
                # assets.json 原始格式（box_2d 列表）→ parse_skeleton
                # 的展开字段（ymin/xmin/...）——detect_dpr 消费后者，
                # 字段不齐会全部 continue 落入 default（同型接口漂移，
                # 第五轮评审在 extract 内部刚修过一次）
                # 手写展开而非复用 parse_skeleton（双轴复查）：后者对
                # 非法项 raise SystemExit（BaseException，绕过本函数
                # 的启发式回退）且强校验 SKELETON_TYPES——锚点检测应
                # 容错（标注不合规就回退宽度启发式），字段顺序合同与
                # parse_skeleton 一致（ymin,xmin,ymax,xmax），漂移由
                # contract-suite 的 detect_dpr 锚点复活单测钉住
                _skel = [{"type": s.get("type"), "text": s.get("text"),
                          "ymin": s["box_2d"][0], "xmin": s["box_2d"][1],
                          "ymax": s["box_2d"][2], "xmax": s["box_2d"][3]}
                         for s in _skel_raw
                         if isinstance(s, dict)
                         and isinstance(s.get("box_2d"), (list, tuple))
                         and len(s["box_2d"]) == 4]
                _guess = (_raw_top.get("density_guess")
                          if isinstance(_raw_top, dict) else None)
                with Image.open(args.image) as _im:
                    css_div, _anchor, _how = detect_dpr(
                        _im.copy(), _skel, _guess)
                print(f"font_probe: dpr={css_div} via ink-anchor "
                      f"({_how})")
            except Exception as _exc:  # noqa: BLE001 — 检测基础设施
                # 故障（如 extract_assets 不可 import）才回退宽度启发
                # 式；detect_dpr 的 SystemExit（冲突/低置信）是
                # BaseException，不在此捕获——直接停机，与 extract
                # 同一停机语义（2026-10-07 第六轮评审）
                css_div = 2.0 if src_w > 500 else 1.0
                print(f"font_probe: ink-anchor dpr unavailable "
                      f"({_exc}) — width heuristic {css_div}")
        all_blocks = blocks_from_assets(args.assets, img_w, img_h)
    else:
        layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
        if layout.get("dpr") is not None:
            # 平面模型（2026-10-07 修正）：逻辑框 ×dpr → 物理探测；
            # 物理墨迹 ÷dpr → CSS。css_div 必须等于 probe_mult——
            # 设 1.0 会让 2x 输入的字号翻倍（二次评审抓到的回归）
            css_div = float(layout["dpr"])
            probe_mult = float(layout["dpr"])
        else:
            _c = layout.get("canvas_contract") or {}
            css_div = float(args.dpr) if args.dpr else (
                2.0 if _c.get("w", 0) > 500 else 1.0)
            probe_mult = 1.0
        all_blocks = all_text_blocks(layout)
        if probe_mult != 1.0:
            for _b in all_blocks:
                for _k in ("x", "y", "w", "h"):
                    _b[_k] = round(_b[_k] * probe_mult)
            print(f"font_probe: layout blocks are logical px — "
                  f"scaled ×{probe_mult} to physical source for probing")

    lock_path = out_dir / "styles.json"
    refine_mode, prev_styles = False, None
    if not args.reprobe and lock_path.is_file():
        try:
            prev_styles = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            prev_styles = None
        if isinstance(prev_styles, dict) and not prev_styles.get("degraded"):
            lock_meta = prev_styles.get("lock") or {}
            locked_css_div = lock_meta.get("css_div")
            ds_md5 = (_img_md5(args.design_system)
                      if args.design_system else None)
            if lock_meta and lock_meta.get("content_md5") != _img_md5(
                    args.image):
                print("font_probe: source image changed (content md5 "
                      f"{lock_meta.get('content_md5')} → "
                      f"{_img_md5(args.image)}) — lock invalidated, "
                      "re-probing")
            elif lock_meta.get("design_system_md5") != ds_md5:
                # 设计系统是字号合同的直接输入（第五轮评审：改 DS
                # 字体定义后旧锁必须失效；旧 lock 缺字段同样失效）
                print("font_probe: design system input changed — "
                      "lock invalidated, re-probing")
            elif (locked_css_div is None or abs(
                    float(locked_css_div) - css_div) > 1e-6) \
                    and not args.layout:
                # 字号平面变了且本轮是 --assets 探测 → family 与 size
                # 均不可复用（旧 lock 无 css_div 字段同样失效）。
                # --layout 精化轮例外（第五轮评审）：首轮启发式近似 →
                # layout.dpr 终值的平面切换是精化的正常场景，family
                # 必须保持锁定、size 由 refine 按新平面重算——整锁
                # 失效反而破坏"精化轮锁 family"的设计
                print(f"font_probe: probe plane changed (css_div "
                      f"{locked_css_div} → {css_div}) — lock invalidated, "
                      "re-probing")
            elif lock_meta.get("mode") == (
                    "assets" if args.assets else "layout") and \
                    lock_meta.get("inputs_md5") != _img_md5(
                        args.assets if args.assets else args.layout):
                # 块清单合同变了（同模式下 assets.json 重标/修框）
                # → 探测对象已变，旧字号不复用（双轴复查补的维度）。
                # 模式切换（assets 探锁 → layout 精化）是合法流，
                # 不在此失效——refine 分支自会刷新 size/weight
                print("font_probe: block-source contract changed "
                      "(assets/layout md5) — lock invalidated, "
                      "re-probing")
            elif args.layout:
                refine_mode = True
                print("font_probe: --layout refinement run — family "
                      "locked from existing contract, size/weight "
                      "refreshed from layout geometry")
            else:
                print("font_probe: styles.json locked (existing contract "
                      "reused; pass --reprobe to refresh)")
                return 0
        else:
            print("font_probe: existing styles.json degraded/unreadable "
                  "— re-probing")

    # 整图浮点数组在此才转（第五轮评审：锁命中 return 0 的路径不付
    # 这个成本）
    src = np.asarray(Image.open(args.image).convert("L"), dtype=float)

    rep_blocks = pick_blocks({
        "skeleton": [{"index": b["idx"], "type": "text_block",
                      "source": "program", "text": b["text"],
                      **{k: b[k] for k in ("x", "y", "w", "h")}}
                     for b in all_blocks]})
    rep_idx = {b["idx"] for b in rep_blocks}

    ds, ds_reason = load_design_system(args.design_system)
    if args.pool:
        global POOL_ARABIC, POOL_LATIN, POOL_CHINESE
        custom = [f.strip() for f in args.pool.split(",") if f.strip()]
        POOL_ARABIC, POOL_LATIN, POOL_CHINESE = custom, custom, custom

    result = {"degraded": False, "reason": "", "blocks": [], "verdict": None}
    ranked, h100_map = {}, {}
    degraded, reason = False, ""

    # —— S4：设计系统直取 —— 有字体定义时跳过渲染比对（探测省略，
    # 族/字重/字号全部由 DS + 墨迹统计给出），styles.json 仍全量。
    ds_has_font = bool(ds and (ds.get("font_family")
                               or ds.get("font_family_latin")))
    if ds_has_font:
        reason = "design-system direct (render probe skipped)"
    elif rep_blocks:
        ranked, h100_map, degraded, reason = render_and_score(
            src, rep_blocks, out_dir / "_font_candidates.png")
    else:
        degraded, reason = True, "no eligible text blocks"

    # —— probe 投票（仅探测模式）——
    family_votes = {}
    for b in rep_blocks:
        cand = ranked.get(b["idx"]) or []
        if cand:
            key = (cand[0]["family"], cand[0]["weight"])
            family_votes[key] = (family_votes.get(key, 0.0)
                                 + cand[0]["score"])
    if family_votes:
        (bf, bw) = max(family_votes, key=family_votes.get)
        result["verdict"] = {"family": bf, "weight": bw,
                             "score": round(family_votes[(bf, bw)], 4)}

    # —— 停机闸（1009-03，PASS 含金量）：探测拿不准必须停机 REVIEW，
    # 不允许密度拟合虚高自动出合同（实测：首轮 0.52 无闸直闯、精化轮
    # 密度巧合虚推 0.92 选错衬线）。exit 2 = REVIEW，SKILL 第 3 步
    # 报告用户给 --design-system 或 --pool。DS 直取模式无探测不适用 ——
    if degraded:
        print(f"font_probe: REVIEW — {reason}; pass --design-system "
              "to pin the family, or check the text_block labeling")
        sys.exit(2)
    if result["verdict"] and not ds_has_font:
        _n = max(1, len(rep_blocks))
        _avg = result["verdict"]["score"] / _n
        if _avg < 0.70:
            print(f"font_probe: REVIEW — probe score {_avg:.2f} < 0.70 "
                  "(pool has no confident match); pass --design-system "
                  "or --pool to decide")
            sys.exit(2)
        _vcat = FONT_CATEGORY.get(result["verdict"]["family"])
        if _vcat:
            _rival = 0.0
            for _b in rep_blocks:
                _cands = [c for c in (ranked.get(_b["idx"]) or [])
                          if FONT_CATEGORY.get(c["family"])
                          not in (None, _vcat)]
                if _cands:
                    _rival += max(c["score"] for c in _cands)
            _rival_avg = _rival / _n
            if _avg - _rival_avg < 0.15:
                print(f"font_probe: REVIEW — category rivalry "
                      f"({result['verdict']['family']} {_avg:.2f} vs "
                      f"rival-category {_rival_avg:.2f} <0.15) — pass "
                      "--design-system or --pool to decide")
                sys.exit(2)

    # —— 全局族：设计系统 > probe 投票 > 无 ——
    styles = {"global": {}, "text_blocks": {}, "conflicts": [],
              "degraded": False}
    if ds:
        ds_f = ds.get("font_family")
        if ds_f:
            styles["global"]["font_family_arabic"] = {
                "value": ds_f, "source": "design-system"}
        ds_fl = ds.get("font_family_latin")
        if ds_fl:
            styles["global"]["font_family_latin"] = {
                "value": ds_fl, "source": "design-system"}
    if result["verdict"]:
        for prop in ("font_family_arabic", "font_family_latin"):
            styles["global"].setdefault(
                prop, {"value": result["verdict"]["family"],
                       "source": "probe"})

    g_latin = (styles["global"].get("font_family_latin") or {}).get("value")
    g_arabic = (styles["global"].get("font_family_arabic") or {}).get("value")

    # —— 全量合同：每个 text_block 一条（family/weight/size_css）——
    per_block = []
    n_unsourced = 0
    for b in all_blocks:
        cand = ranked.get(b["idx"]) or []
        ink = ink_stats_block(src, b, css_div)
        ds_f = (ds or {}).get("font_family") if is_arabic(b["text"]) \
            else (ds or {}).get("font_family_latin")
        gf = g_arabic if is_arabic(b["text"]) else g_latin
        entry = {"idx": b["idx"], "text": b["text"],
                 "ink_h_css": round(b["h"] / css_div, 1),
                 "candidates": cand, "family": None, "weight": None,
                 "size_css": None, "source": "unsourced"}
        if b["idx"] in rep_idx and cand:
            top = cand[0]
            h100 = h100_map.get((top["family"], top["weight"]))
            entry["weight"] = top["weight"]
            # Single-block family unification: a representative block
            # hitting a DIFFERENT family than the global verdict is how
            # one wide-glyph family sneaks into one block and invades
            # its neighbours (field failure 2026-09-29: IBM Plex block
            # vs Noto site). The contract family is site-wide: DS >
            # global probe verdict > this block's own top hit (last
            # resort only when no global verdict exists).
            entry["family"] = ds_f or gf or top["family"]
            entry["source"] = ("design-system (weight/size by probe)"
                               if ds_f else "probe (site-wide family)")
            if h100:
                # 2026-10-08 修复：b["h"] 是像素精化框高（含抗锯齿留白
                # 与行距），直接当墨迹高会把字号系统性放大 1.3-3.6 倍
                # （field failure 2026-10-08 p001-2：s2 框 34 物理 vs
                # 墨迹 19 物理 → 23.9css vs 实际 13.4css，渲染宽超原始
                # 标注框 60-80%，触发墨迹宽 gate 与 styles_consistency
                # 双 FAIL 死锁）。改为 ink_crop 实测墨迹高（物理平面，
                # 与 b 同一坐标系），框不可辨时才回退框高。
                _ink = ink_crop(src, b["x"], b["y"], b["w"], b["h"])
                if _ink is not None and _ink.shape[0] >= 6:
                    entry["size_css"] = round(
                        100.0 * (_ink.shape[0] / css_div) / h100, 1)
                else:
                    entry["size_css"] = round(
                        100.0 * (b["h"] / css_div) / h100, 1)
        else:
            # 非代表块：族取 DS/全局 verdict，档取墨迹估算
            entry["family"] = ds_f or gf
            if ink:
                entry["weight"] = ink["weight"]
                entry["size_css"] = ink["size_css"]
            entry["source"] = (("design-system family + ink estimate")
                               if ds_f else
                               ("probe family + ink estimate" if gf
                                else "ink estimate [UNSOURCED]"))
        if entry["family"] is None:
            n_unsourced += 1
        styles["text_blocks"][f"s{b['idx']}"] = {
            "family": entry["family"], "weight": entry["weight"],
            "size_css": entry["size_css"], "source": entry["source"]}
        per_block.append(entry)

    # —— conflicts（仅探测模式可比对）——
    if ds and result["verdict"]:
        ds_f = ds.get("font_family")
        if ds_f and result["verdict"]["family"] != ds_f:
            styles["conflicts"].append({
                "prop": "font_family_arabic", "design_system": ds_f,
                "probe": result["verdict"]["family"],
                "resolution": "design-system wins"})

    # 精化轮（--layout）：family 是锁定的合同（防换池漂移），本轮只
    # 按布局几何刷新 size/weight——family 从旧合同原样带回。
    if refine_mode and isinstance(prev_styles, dict):
        old_blocks = prev_styles.get("text_blocks") or {}
        for k, v in styles["text_blocks"].items():
            old = old_blocks.get(k) or {}
            if old.get("family"):
                v["family"] = old["family"]
                v["source"] = (str(old.get("source", ""))
                               + " [family locked; size refined by layout]")
    # 锁元数据：源图内容（md5）、设计系统（md5）、字号平面（css_div）
    # 或输入合同（assets.json/layout.json 的 md5）任一变化时自动失效。
    # 旧 lock 缺新字段会被校验处判失效（保守）
    _inputs_md5 = _img_md5(args.assets if args.assets else args.layout)
    styles["lock"] = {
        "image": str(args.image), "source_size": [src_w, src_h],
        "content_md5": _img_md5(args.image), "css_div": css_div,
        "inputs_md5": _inputs_md5,
        "mode": "assets" if args.assets else "layout",
        "design_system_md5": (_img_md5(args.design_system)
                              if args.design_system else None),
    }
    styles["degraded"] = bool(n_unsourced > 0 and not ds_has_font
                              and not result["verdict"])
    result["degraded"] = styles["degraded"]
    result["reason"] = reason if degraded else (
        ds_reason if (not degraded and ds_reason and not ds) else "")
    result["blocks"] = per_block
    result["coverage"] = {"total": len(all_blocks),
                          "unsourced": n_unsourced}
    (out_dir / "font_probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "styles.json").write_text(
        json.dumps(styles, ensure_ascii=False, indent=2), "utf-8")
    cand_png = ("_font_candidates.png"
                if (out_dir / "_font_candidates.png").exists()
                else "skipped (design-system direct)")
    print(f"font_probe: verdict={result['verdict']} degraded={degraded} "
          f"coverage={result['coverage']} reason={reason!r} "
          f"styles.json + {cand_png} written")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
