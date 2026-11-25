# -*- coding: utf-8 -*-
"""Screenshot + programmatic verification for image-to-code-skills.

Renders the generated HTML in headless Chromium (system Edge first,
bundled Chromium as fallback) at desktop AND mobile viewports, runs the
fixed structural assertions, writes a machine-readable report and exits
0 (PASS) or 1 (FAIL). The agent never decides pass/fail — it only reads
verify_report.json and fixes what the failing checks name.

Assertions (all deterministic, sourced from layout.json when present):
  console_errors      any window/console error
  failed_requests     any request that never got a response (404, DNS…)
  img_loaded          every <img> has naturalWidth > 0
  bottom_bar          when layout.json has_bottom_bar: some element is
                      fixed/sticky/absolute AND stays aligned with the
                      body canvas (same horizontal center ±3%, bottom
                      edge at the canvas bottom ±12px) — position:fixed
                      bars that tear away from an RTL/wide-viewport body
                      FAIL here
  canvas_contract     when layout.json canvas_contract: at the contract
                      viewport the page must not scroll (scrollHeight
                      within 5% of the contract height)
  canvas_alignment    when layout.json canvas_contract, wide viewport:
                      body keeps the contract width in a 1280px window
                      (catches viewport-vs-body anchoring tears that are
                      invisible at the contract viewport)
  asset_blend         rectangular (non-alpha) crops: color distance
                      between the crop's edge ring and the page
                      background just outside it must stay under
                      threshold — catches baked-in-background seams that
                      band-averaged diffs dilute
  texts_present       when layout.json expected_texts: every string
                      appears in the page (whitespace-normalized; body
                      text first, full HTML as fallback for alt/title)
  asset_geometry      every layout asset renders as <img src*=asset_N> or
                      a fallback [data-asset=asset_N] element, within
                      max(6px, 12%) of its layout box
  text_overflow       no leaf text element scrolls wider than its box
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIEWPORTS = {"desktop": (1280, 832), "mobile": (390, 844),
             "wide": (1280, 832)}
SCROLL_TOLERANCE = 1.05
BOTTOM_ZONE_FRACTION = 0.85
GEOMETRY_TOLERANCE_ABS = 6      # px
GEOMETRY_TOLERANCE_REL = 0.12   # fraction of expected size


def _norm_text(s: str) -> str:
    """Collapse all whitespace runs to single spaces (innerText wraps
    differently than the source HTML)."""
    return " ".join((s or "").split())


def launch_browser(pw):
    try:
        return pw.chromium.launch(channel="msedge", headless=True), "msedge"
    except Exception:
        return pw.chromium.launch(headless=True), "chromium"


def build_diff_sheet(source_path: Path, render_path: Path,
                     out_path: Path, bands: int = 6,
                     block: int = 16,
                     assets: Optional[List[Dict[str, Any]]] = None,
                     text_blocks: Optional[List[Dict[str, Any]]] = None,
                     src_box_scale: float = 1.0,
                     ren_box_scale: float = 1.0
                     ) -> Optional[Dict[str, Any]]:
    """Side-by-side source-vs-render bands, worst-difference first, with
    per-block mean-color deltas drawn as red boxes. This is the visual
    audit surface for the post-PASS check: single-image eyeballing
    smooths over wrong colors, mangled assets and hallucinated elements —
    a forced A/B comparison does not.

    2026-10: text_blocks regions are greyed out on BOTH sides. Text
    quality is fully owned by data assertions (styles_consistency /
    skeleton_geometry / text_overflow / texts_present) — eyeballing
    text in the diff sheet duplicates that at 10x the cost, so the
    visual audit focuses on what actually needs eyes: asset shapes,
    colors, icon forms, page structure."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    import numpy as np

    src = Image.open(source_path).convert("RGB")
    ren = Image.open(render_path).convert("RGB")
    # Normalize to a common working size (source is often 2x device px).
    work_w = 720
    src_n = src.resize((work_w, round(src.height * work_w / src.width)),
                       Image.LANCZOS)
    ren_n = ren.resize((work_w, round(ren.height * work_w / ren.width)),
                       Image.LANCZOS)
    h = min(src_n.height, ren_n.height)
    src_n, ren_n = src_n.crop((0, 0, work_w, h)), ren_n.crop(
        (0, 0, work_w, h))

    # Grey out text-block regions (data-asserted; see docstring).
    # 分侧换算（2026-10-07 坐标合同）：框平面可能 ≠ 图平面——
    # src 侧：框 ×src_box_scale → 物理源图 → ×(work_w/src.width) → 工作平面
    # ren 侧：框 ×ren_box_scale → 逻辑截图 → ×(work_w/ren.width)
    if text_blocks:
        sc_src = work_w / src.width
        sc_ren = work_w / ren.width

        def _mask_text(im, box_scale, sc):
            ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            for tb in text_blocks:
                od.rectangle(
                    (tb["x"] * box_scale * sc, tb["y"] * box_scale * sc,
                     (tb["x"] + tb["w"]) * box_scale * sc,
                     (tb["y"] + tb["h"]) * box_scale * sc),
                    fill=(96, 96, 108, 165), outline=(210, 210, 220, 200),
                    width=1)
            return Image.alpha_composite(im.convert("RGBA"), ov).convert(
                "RGB")

        src_n = _mask_text(src_n, src_box_scale, sc_src)
        ren_n = _mask_text(ren_n, ren_box_scale, sc_ren)

    bh = h // bands
    nx = work_w // block
    band_stats = []
    for b in range(bands):
        y0, y1 = b * bh, (b + 1) * bh if b < bands - 1 else h
        ny = max(1, (y1 - y0) // block)
        # BOX resize = per-block mean color without reshape constraints
        s_blk = np.asarray(
            src_n.crop((0, y0, work_w, y1)).resize((nx, ny), Image.BOX),
            dtype=float)
        r_blk = np.asarray(
            ren_n.crop((0, y0, work_w, y1)).resize((nx, ny), Image.BOX),
            dtype=float)
        dist = np.sqrt(((s_blk - r_blk) ** 2).sum(axis=2))
        band_stats.append({
            "band": b, "y0": y0, "y1": y1,
            "avg": round(float(dist.mean()), 1),
            "max": round(float(dist.max()), 1),
            "blocks": dist,
        })
    band_stats.sort(key=lambda s: s["avg"], reverse=True)

    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    # SMALL ASSET ZOOM rows — prepared before the sheet is allocated so
    # it can grow to fit them. Per-asset shape audit at ~4x: a missing
    # part or a shifted icon reads fine inside band strips (~40px there)
    # and the band red boxes smear over exactly these defects
    # (field failures 2026-09-29).
    zoom_rows: List[Dict[str, Any]] = []
    ZOOM_H, ZOOM_LABEL = 80, 18
    label_h, pad = 24, 6
    if assets:
        for a in assets:
            bx = a.get("box_px") or {}
            if not bx or max(bx["w"], bx["h"]) >= 100:
                continue
            s_c = src.crop((round(bx["x"] * src_box_scale),
                            round(bx["y"] * src_box_scale),
                            round((bx["x"] + bx["w"]) * src_box_scale),
                            round((bx["y"] + bx["h"]) * src_box_scale)))
            r_c = ren.crop((round(bx["x"] * ren_box_scale),
                            round(bx["y"] * ren_box_scale),
                            round((bx["x"] + bx["w"]) * ren_box_scale),
                            round((bx["y"] + bx["h"]) * ren_box_scale)))
            s_z = s_c.resize(
                (max(1, round(s_c.width * ZOOM_H
                              / max(s_c.height, 1))), ZOOM_H),
                Image.LANCZOS)
            r_z = r_c.resize(
                (max(1, round(r_c.width * ZOOM_H
                              / max(r_c.height, 1))), ZOOM_H),
                Image.LANCZOS)
            zoom_rows.append({"index": a["index"],
                              "desc": str(a.get("description", ""))[:34],
                              "s": s_z, "r": r_z})
    zoom_area_h = (
        (24 + len(zoom_rows) * (ZOOM_LABEL + ZOOM_H + pad) + pad)
        if zoom_rows else 0)
    # FULL-PAGE row: whole source next to whole render. Band-by-band
    # comparison cannot catch page-level misplacement — a bottom bar
    # torn from its canvas reads as perfect inside every band.
    full_h = min(480, round(src_n.height * 0.32))
    full_w = round(src_n.width * full_h / src_n.height)
    src_full = src_n.resize((full_w, full_h), Image.LANCZOS)
    ren_full = ren_n.resize((full_w, ren_n.height * full_h
                             // ren_n.height), Image.LANCZOS)
    full_row_h = max(src_full.height, ren_full.height) + label_h
    band_h = bh + label_h
    sheet = Image.new("RGB", (work_w * 2 + pad * 3,
                              label_h + full_row_h + pad
                              + bands * (band_h + pad) + pad
                              + zoom_area_h),
                      "#222222")
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (pad, 5),
        "DIFF SHEET — left=source, right=render; FULL-PAGE row first "
        "(check page-level placement), then bands sorted by mean block "
        "color delta; red boxes = blocks over threshold",
        fill="#FFFFFF", font=font,
    )
    y = label_h
    draw.text((pad, y + 4), "FULL PAGE — source vs render",
              fill="#FFFFFF", font=font)
    y += label_h
    sheet.paste(src_full, (pad, y))
    sheet.paste(ren_full, (work_w + pad * 2, y))
    y += full_row_h - label_h + pad
    report_bands = []
    for s in band_stats:
        head = (f"BAND {s['band']}  y={s['y0']}-{s['y1']}  "
                f"avgΔ={s['avg']} maxΔ={s['max']}")
        draw.text((pad, y + 4), head,
                  fill="#FF7070" if s["avg"] > 12 else "#90EE90",
                  font=font)
        y += label_h
        sheet.paste(src_n.crop((0, s["y0"], work_w, s["y1"])), (pad, y))
        render_band = ren_n.crop((0, s["y0"], work_w, s["y1"])).copy()
        d2 = ImageDraw.Draw(render_band)
        blocks = s["blocks"]
        ny2, nx2 = blocks.shape
        bw, bhh = work_w / nx2, (s["y1"] - s["y0"]) / ny2
        for by, bx in zip(*np.where(blocks > 30)):
            d2.rectangle((bx * bw, by * bhh,
                          (bx + 1) * bw, (by + 1) * bhh),
                         outline="#FF3030", width=2)
        sheet.paste(render_band, (work_w + pad * 2, y))
        y += bh + pad
        report_bands.append({k: s[k] for k in ("band", "y0", "y1",
                                               "avg", "max")})
    if zoom_rows:
        draw.text(
            (pad, y + 4),
            "SMALL ASSET ZOOM — per-asset shape audit (source left / "
            "render right): a missing part or a shifted icon reads fine "
            "inside bands",
            fill="#FFFFFF", font=font)
        y += label_h
        for zr in zoom_rows:
            draw.text((pad, y + 2),
                      f"#{zr['index']} {zr['desc']}",
                      fill="#DDDDDD", font=font)
            y += ZOOM_LABEL
            sheet.paste(zr["s"], (pad, y))
            sheet.paste(zr["r"], (pad + zr["s"].width + 18, y))
            y += ZOOM_H + pad
    sheet.save(out_path)
    return {"path": str(out_path), "bands": report_bands,
            "zoom_assets": [zr["index"] for zr in zoom_rows]}


def check_asset_blend(render_path: Path, assets: List[Dict[str, Any]],
                      contract_scale: int, alpha_used: Dict[str, bool],
                      seam_fail: float = 60.0,
                      seam_warn: float = 35.0) -> Tuple[List[str],
                                                        List[str]]:
    """Ring seam test for rectangular (non-alpha) crops.

    A raw crop pasted onto a re-created background betrays its seam at
    the box edge: the crop's baked-in background ring (just inside the
    box) vs the page's own background (just outside it). Band-averaged
    diff sheets dilute these thin seams below visibility, so measure
    them directly. Alpha assets have no seam — skipped. Assets whose
    inner ring is busy content (high variance, the subject touches the
    box edge) can't be judged by a mean-color test — downgraded to a
    warning, never a FAIL.
    """
    from PIL import Image
    import numpy as np

    im = np.asarray(Image.open(render_path).convert("RGB"), dtype=float)
    H, W = im.shape[:2]
    fails: List[str] = []
    warns: List[str] = []
    t, o = 4, 2  # ring thickness; offset from the box edge

    def ring(x0: int, y0: int, x1: int, y1: int):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 - x0 < t + 2 or y1 - y0 < t + 2:
            return None
        return np.concatenate([
            im[y0:y0 + t, x0:x1].reshape(-1, 3),
            im[y1 - t:y1, x0:x1].reshape(-1, 3),
            im[y0:y1, x0:x0 + t].reshape(-1, 3),
            im[y0:y1, x1 - t:x1].reshape(-1, 3),
        ])

    for a in assets:
        idx = a["index"]
        if alpha_used.get(str(idx)):
            continue
        x = round(a["box_px"]["x"] / contract_scale)
        y = round(a["box_px"]["y"] / contract_scale)
        w = round(a["box_px"]["w"] / contract_scale)
        h = round(a["box_px"]["h"] / contract_scale)
        rin = ring(x + o, y + o, x + w - o, y + h - o)
        rout = ring(x - o - t, y - o - t, x + w + o + t, y + h + o + t)
        if (rin is None or rout is None
                or rin.shape[0] < 40 or rout.shape[0] < 40):
            continue
        d = float(np.sqrt(((rin.mean(axis=0)
                            - rout.mean(axis=0)) ** 2).sum()))
        if d <= seam_warn:
            continue
        in_std = float(rin.std(axis=0).max())
        label = (f"asset_{idx} seam Δ={d:.0f} "
                 f"(in-ring std {in_std:.0f})")
        if d > seam_fail and in_std < 40:
            fails.append(label)
        else:
            warns.append(label)
    return fails, warns


def build_render_check(source_path: Path, render_path: Path,
                       assets: List[Dict[str, Any]], out_path: Path,
                       contract_scale: int, zoom: int = 4,
                       per_sheet: int = 12,
                       src_box_scale: float = 1.0) -> Dict[str, Any]:
    """Side-by-side pick-up check: source crop vs rendered crop per asset.

    Band-averaged diff sheets dilute a small icon to a few pixel cells —
    a shrunken matte (handle drawn thin) or an eaten edge (bubble corner
    squared off) is invisible there. This sheet crops each asset's bbox
    from the SOURCE and the RENDER at the same box, zooms both, and
    stacks them per row.

    2026-10: each row gets a deterministic pixel diff (share of pixels
    with channel-max delta > 45 between same-size source/render crops).
    hot_ratio > 0.18 → REVIEW row (4x, sorted first); the rest are
    auto-ok rows (2x, collapsed below). The step-5 eyeball pass reads
    REVIEW rows only — a shape-level distortion is by construction a
    large-area pixel delta, so a low hot_ratio row cannot hide one;
    auto-ok rows stay in the sheet for spot checks.
    Sheets are split at `per_sheet` rows to keep every file ≤ ~1.5MB
    (a single giant sheet forces the agent into a crop-and-reread hop).
    """
    from PIL import Image, ImageDraw
    import numpy as np

    src = Image.open(source_path).convert("RGB")
    ren = Image.open(render_path).convert("RGB")
    pad, label_h = 6, 18
    rows: List[Dict[str, Any]] = []
    for a in assets:
        bx = a["box_px"]
        x, y = bx["x"], bx["y"]
        w, h = bx["w"], bx["h"]
        # src 侧：框 ×src_box_scale → 物理源图（新格式逻辑框 ×dpr）；
        # ren 侧：框 ÷contract_scale（旧格式物理框 ÷启发式；新格式 ×1）
        sc = src.crop((round(x * src_box_scale), round(y * src_box_scale),
                       round((x + w) * src_box_scale),
                       round((y + h) * src_box_scale)))
        rx, ry = round(x / contract_scale), round(y / contract_scale)
        rw, rh = round(w / contract_scale), round(h / contract_scale)
        rc = ren.crop((rx, ry, min(rx + rw, ren.width),
                       min(ry + rh, ren.height)))
        # deterministic diff on a common working size
        cw0, ch0 = 128, max(8, round(128 * h / max(w, 1)))
        s_a = np.asarray(sc.resize((cw0, ch0)), dtype=float)
        r_a = np.asarray(rc.resize((cw0, ch0)), dtype=float)
        d = np.abs(s_a - r_a).max(axis=2)
        hot_ratio = float((d > 45).mean())
        review = hot_ratio > 0.18
        rows.append({"a": a, "sc": sc, "rc": rc, "hot": hot_ratio,
                     "review": review})
    rows.sort(key=lambda r: (-int(r["review"]), -r["hot"]))
    n_review = sum(1 for r in rows if r["review"])

    sheets: List[Dict[str, Any]] = []
    for chunk_i in range(0, max(len(rows), 1), per_sheet):
        chunk = rows[chunk_i:chunk_i + per_sheet]
        if not chunk:
            break
        built: List[Image.Image] = []
        for r in chunk:
            z = zoom if r["review"] else 2
            cw = r["sc"].width * z
            ch = r["sc"].height * z
            row = Image.new("RGB",
                            (cw * 2 + pad * 3, ch + label_h + pad * 2),
                            (24, 24, 28))
            row.paste(r["sc"].resize((cw, ch), Image.LANCZOS),
                      (pad, pad + label_h))
            row.paste(r["rc"].resize((cw, ch), Image.LANCZOS),
                      (cw + pad * 2, pad + label_h))
            dr = ImageDraw.Draw(row)
            tag = (f"asset_{r['a']['index']}  REVIEW hot={r['hot']:.0%} "
                   f"left=SOURCE right=RENDER  ← READ THIS ROW")
            if not r["review"]:
                tag = (f"asset_{r['a']['index']}  auto-ok "
                       f"hot={r['hot']:.0%}  (spot-check only)")
            dr.text((pad, 3), tag,
                    fill=(255, 80, 80) if r["review"] else (120, 200, 120))
            built.append(row)
        part = chunk_i // per_sheet + 1
        out_p = (out_path.with_name(
            f"{out_path.stem}_{part}{out_path.suffix}")
            if len(rows) > per_sheet else out_path)
        total_w = max(r.width for r in built)
        total_h = sum(r.height for r in built) + pad * (len(built) + 1)
        sheet = Image.new("RGB", (total_w, total_h), (24, 24, 28))
        cy = pad
        for r in built:
            sheet.paste(r, (0, cy))
            cy += r.height + pad
        sheet.save(out_p)
        sheets.append({"path": str(out_p), "rows": len(chunk)})
    return {"paths": [s["path"] for s in sheets], "rows": len(rows),
            "review": n_review}


def _ink_stats(gray: "np.ndarray", x: int, y: int, w: int, h: int):
    """墨迹统计：二值化后 bbox 高与密度（笔画粗细的代理量）。

    极性自适应（2026-10-07 修复）：墨迹 = 与背景不同的少数派像素。
    旧实现固定 `reg > 阈值`，隐含"浅字深底"假设——真实场景深字浅
    底时选中背景，bbox 恒等于框高，墨迹高维度长期失效（ratio 恒 1，
    被"框恒等"掩盖；密度维度因反相对称碰巧可用）。
    """
    import numpy as np
    x0, y0 = max(0, x), max(0, y)
    x1 = min(gray.shape[1], x + w)
    y1 = min(gray.shape[0], y + h)
    reg = gray[y0:y1, x0:x1]
    if reg.size == 0:
        return None
    lo, hi = float(reg.min()), float(reg.max())
    thr = lo + (hi - lo) * 0.45
    bg_is_light = float(reg.mean()) > (lo + hi) / 2
    m = (reg < thr) if bg_is_light else (reg > thr)
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return {"h": float(ys.max() - ys.min() + 1),
            "density": float(m.mean())}


def _font_drift_check(source_path: Path, render_path: Path,
                      layout: dict,
                      src_box_scale: float = 1.0,
                      ren_box_scale: float = 1.0) -> list:
    """程序验证过的文字块：渲染墨迹高比 & 笔画密度 vs 原图。返回偏差列表。

    坐标合同（2026-10-07 补收口，与 build_diff_sheet 同一双乘数）：
    layout 框是逻辑 px；src 是物理源图（框 ×src_box_scale 裁），
    ren 是逻辑截图（框 ×ren_box_scale 裁）。墨迹高统一折算回逻辑
    平面再比——旧实现逻辑框直接裁物理源图，2x 图上墨迹测量整体失真。
    """
    import numpy as np
    from PIL import Image

    src = np.asarray(Image.open(source_path).convert("L"), dtype=float)
    ren_img = Image.open(render_path).convert("L")
    ren = np.asarray(ren_img, dtype=float)

    drift = []
    for s in layout.get("skeleton") or []:
        if s.get("type") != "text_block" or s.get("source") != "program":
            continue
        if s.get("h", 0) < 18:
            continue
        t = s.get("text") or ""
        if any("一" <= c <= "鿿" for c in t):
            continue
        a = _ink_stats(src, round(s["x"] * src_box_scale),
                       round(s["y"] * src_box_scale),
                       round(s["w"] * src_box_scale),
                       round(s["h"] * src_box_scale))
        b = _ink_stats(ren, round(s["x"] * ren_box_scale),
                       round(s["y"] * ren_box_scale),
                       round(s["w"] * ren_box_scale),
                       round(s["h"] * ren_box_scale))
        if not a or not b:
            continue
        # 物理墨迹高 ÷ 各自乘数 → 逻辑平面，直接比
        a_css = a["h"] / max(src_box_scale, 1e-6)
        b_css = b["h"] / max(ren_box_scale, 1e-6)
        ratio = b_css / max(1.0, a_css)
        if ratio < 0.7 or ratio > 1.45:
            drift.append(f"s{s['index']}: ink height ×{ratio:.2f} "
                         "(font-size drifted)")
        elif abs(a["density"] - b["density"]) > 0.20:
            drift.append(f"s{s['index']}: stroke density "
                         f"{a['density']:.2f}→{b['density']:.2f} "
                         "(font-weight drifted)")
    return drift


def read_json(path: Path) -> Any:
    """utf-8 first, GBK fallback (zh-CN Windows editors default to GBK)."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return json.loads(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"cannot decode {path} (tried utf-8, gbk)")


def run(html_path: Path, layout_path: Optional[Path], out_dir: Path,
        image_path: Optional[Path] = None) -> int:
    if not html_path.is_file():
        raise SystemExit(f"html not found: {html_path}")
    # 基准门禁（PASS 含金量，2026-10-07）：校准基准缺失 = 断言无锚 =
    # 守门员放行 = 假绿通道。缺 layout.json / 源图一律拒跑。
    if not layout_path or not layout_path.is_file():
        raise SystemExit("layout.json missing — verify refuses to run "
                         "without the calibrated baseline")
    if image_path is None or not Path(image_path).is_file():
        raise SystemExit("source image missing — verify must produce "
                         "diff/render sheets for the independent judge")
    layout = read_json(layout_path)
    # 坐标合同（2026-10-07 统一，单一事实源 = layout.json 的 dpr 字段）：
    #   新格式（带 dpr）：坐标已归一逻辑 px —— 直接用，scale = 1；
    #     任何"逻辑坐标 ÷ dpr"都是重复缩放（187px viewport 事故）
    #   旧格式（无 dpr 字段）：坐标物理 px —— 兼容路径 ÷(w>500→2)，
    #     启发式仅允许存在于此处；建议重跑管线迁移
    legacy_layout = layout.get("dpr") is None
    base_scale = 1
    if legacy_layout:
        _c = layout.get("canvas_contract") or {}
        base_scale = 2 if _c.get("w", 0) > 500 else 1
        print("verify: legacy layout.json (no dpr field) — physical "
              "coords via w>500 heuristic; re-run the pipeline to "
              "migrate")
    # 框→图平面乘数（与 base_scale 独立——base_scale 是坐标数值→
    # 逻辑 CSS 的除数，这两个是框落到两张不同平面图上的乘数）：
    #   src_box_scale：框 → 物理源图（源图恒为物理；新格式逻辑框 ×dpr）
    #   ren_box_scale：框 → 逻辑截图（新格式框已逻辑 ×1；旧格式 ÷base_scale）
    src_box_scale = float(layout.get("dpr") or 1.0)
    ren_box_scale = 1.0 / base_scale
    out_dir.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()

    from playwright.sync_api import sync_playwright

    checks: List[Dict[str, Any]] = []
    screenshots: Dict[str, str] = {}
    centroid_offsets: List[Dict[str, Any]] = []

    with sync_playwright() as pw:
        browser, channel = launch_browser(pw)
        try:
            for name, (vw, vh) in VIEWPORTS.items():
                contract_scale = 1
                contract = layout.get("canvas_contract")
                if contract and name != "wide":
                    # Both built-in viewports sit at the contract size: a
                    # fixed bottom bar pinned to a taller viewport (e.g.
                    # 844 vs an 812 canvas) drifts ~30px and shows as a
                    # fake offset in previews. The "wide" viewport is
                    # deliberately NOT overridden — it renders the page
                    # in a desktop-size window where a viewport-anchored
                    # bottom bar (position:fixed) visibly tears away from
                    # a body-anchored canvas (RTL pages park the body on
                    # the right, the bar stays on the left).
                    # Coordinate contract (2026-10-07, single source of
                    # truth = layout["dpr"]): new-format layouts store
                    # LOGICAL px (pipeline normalized at entry) — use
                    # contract w/h as-is, NEVER divide by dpr (that
                    # double-scales: 375/2 = 187px viewport bug). Legacy
                    # layouts (no dpr field) store PHYSICAL px —
                    # base_scale applies the w>500 heuristic, allowed
                    # nowhere else.
                    contract_scale = base_scale
                    vw = contract["w"] // contract_scale
                    vh = contract["h"] // contract_scale
                page = browser.new_page(
                    viewport={"width": vw, "height": vh}
                )
                console_errors: List[str] = []
                failed_requests: List[str] = []
                page.on(
                    "console",
                    lambda m: console_errors.append(m.text[:300])
                    if m.type == "error" else None,
                )
                page.on(
                    "requestfailed",
                    lambda r: failed_requests.append(
                        f"{r.url[:200]} ({r.failure})"
                    ),
                )
                nav_settled = True
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception:
                    # networkidle can time out on pages with long-polling;
                    # fall back to load + settle
                    try:
                        page.goto(url, wait_until="load", timeout=30000)
                        page.wait_for_timeout(1500)
                    except Exception:
                        # stalled CDN (fonts/tailwind): the local DOM is
                        # ready long before "load" fires. Proceed with a
                        # settle wait instead of crashing the whole run —
                        # geometry assertions rely on inline styles, not
                        # on the CDN having answered.
                        nav_settled = False
                        page.wait_for_timeout(2500)
                page.wait_for_timeout(300 if nav_settled else 2500)
                # S3 deterministic settle: screenshots are the basis of
                # geometry/blend assertions, so wait until web fonts are
                # ready, every image decoded, and no request is still in
                # flight — otherwise CDN jitter changes the input and
                # "same page, different verdict" (violates same-input-
                # same-output).
                try:
                    page.evaluate("() => document.fonts.ready")
                except Exception:
                    pass
                try:
                    page.wait_for_function(
                        "() => [...document.images].every("
                        "i => i.complete && i.naturalWidth > 0)",
                        timeout=15000)
                except Exception:
                    pass  # broken images are img_loaded's job, not ours
                try:
                    page.wait_for_function(
                        "() => performance.getEntriesByType('resource')"
                        ".every(r => r.responseEnd > 0)",
                        timeout=8000)
                except Exception:
                    pass  # stalled CDN — proceed, errors are reported
                page.wait_for_timeout(300)

                shot = out_dir / f"preview_{name}.png"
                page.screenshot(path=str(shot), full_page=True)
                screenshots[name] = str(shot)

                # --- img_loaded --------------------------------------
                imgs = page.evaluate(
                    """() => Array.from(document.images).map(i => ({
                        src: i.currentSrc || i.src, ok: i.naturalWidth > 0,
                    }))"""
                )
                broken = [i["src"][:200] for i in imgs if not i["ok"]]
                checks.append({
                    "name": f"img_loaded[{name}]",
                    "pass": not broken,
                    "detail": (
                        f"{len(broken)} broken of {len(imgs)}: "
                        + "; ".join(broken[:5])
                    ) if broken else f"{len(imgs)} img all loaded",
                })

                # --- console / network -------------------------------
                checks.append({
                    "name": f"console_errors[{name}]",
                    "pass": not console_errors,
                    "detail": "; ".join(console_errors[:5])
                    if console_errors else "none",
                })
                checks.append({
                    "name": f"failed_requests[{name}]",
                    "pass": not failed_requests,
                    "detail": "; ".join(failed_requests[:5])
                    if failed_requests else "none",
                })

                # --- bottom_bar --------------------------------------
                # Canvas-anchored assertion, NOT a position-kind check: on
                # a fixed non-scrolling canvas the bar may be absolute
                # (anchored to body — correct) or fixed (anchored to the
                # VIEWPORT — tears away from the body on wide/RTL
                # viewports). What must hold on EVERY viewport is that the
                # bar stays aligned with the body canvas: same horizontal
                # center, bottom edge at the canvas bottom.
                if layout.get("has_bottom_bar"):
                    bar_info = page.evaluate(
                        """() => {
                            const b = document.body.getBoundingClientRect();
                            const body = {left: b.left, width: b.width,
                                          bottom: b.bottom,
                                          centerX: b.left + b.width / 2};
                            let best = null;
                            for (const el of document.querySelectorAll(
                                    'body *')) {
                                const cs = getComputedStyle(el);
                                if (!['fixed', 'sticky', 'absolute']
                                        .includes(cs.position)) continue;
                                const r = el.getBoundingClientRect();
                                const coverage = r.width
                                    / Math.max(1, body.width);
                                if (coverage >= 0.5
                                        && (!best
                                            || r.bottom > best.bottom)) {
                                    best = {bottom: r.bottom, coverage,
                                            tag: el.tagName,
                                            pos: cs.position,
                                            centerX: r.left
                                                + r.width / 2};
                                }
                            }
                            return {bar: best, body: body};
                        }"""
                    )
                    bar, body = bar_info["bar"], bar_info["body"]
                    tol_cx = max(8.0, body["width"] * 0.03)
                    if not bar:
                        ok = False
                        detail = ("no fixed/sticky/absolute bottom-bar "
                                  "element found (layout.json says this "
                                  "screen has a bottom bar)")
                    else:
                        d_cx = abs(bar["centerX"] - body["centerX"])
                        d_bottom = body["bottom"] - bar["bottom"]
                        # A floating dock often sits a deliberate gap
                        # above the canvas bottom — that gap is part of
                        # the source design, so the tolerance is taken
                        # from layout.json's measured bottom_bar_gap_px
                        # (falling back to ±16) instead of a hard 16:
                        # forcing the bar to touch the canvas bottom to
                        # satisfy this check drags the whole bar off
                        # its measured position (field failure: a 16.5px
                        # design gap made the coder stretch the bar
                        # container, shifting it 9px off).
                        gap_px = layout.get("bottom_bar_gap_px") or 0
                        gap_css = gap_px / contract_scale
                        hi = max(16.0, gap_css + 8.0)
                        ok = (d_cx <= tol_cx
                              and -16 <= d_bottom <= hi
                              and bar["coverage"] >= 0.5)
                        detail = (
                            f"{bar['pos']} <{bar['tag']}> "
                            f"centerΔ={d_cx:.0f}px "
                            f"(tol {tol_cx:.0f}), "
                            f"bottomΔ={d_bottom:+.0f}px vs body canvas "
                            f"(design gap {gap_css:.0f}px, tol ±{hi:.0f})"
                        )
                    checks.append({
                        "name": f"bottom_bar[{name}]",
                        "pass": ok,
                        "detail": detail,
                    })

                # --- canvas_contract ----------------------------------
                contract = layout.get("canvas_contract")
                if contract and name == "desktop":
                    scroll_h = page.evaluate(
                        "document.documentElement.scrollHeight"
                    )
                    contract_h = contract["h"] / contract_scale
                    limit = contract_h * SCROLL_TOLERANCE
                    checks.append({
                        "name": "canvas_contract",
                        "pass": scroll_h <= limit,
                        "detail": (
                            f"scrollHeight={scroll_h}, contract="
                            f"{contract_h:.0f} (limit {limit:.0f}, "
                            f"{contract_scale}x source)"
                        ),
                    })

                # --- canvas_alignment (wide viewport only) -----------
                # Catches viewport-anchored vs body-anchored tears that
                # are invisible at the contract viewport: at 375px the
                # body fills the window so a position:fixed bar coincides
                # with the canvas; at 1280px (RTL especially) the body
                # parks on one side and a viewport-fixed bar stays on the
                # other. The bottom_bar check above already asserts
                # bar-vs-body alignment on every viewport; this one
                # asserts the canvas itself holds its width when the
                # window is wider.
                if contract and name == "wide":
                    # Coordinate contract: same base_scale as the main
                    # loop (new format = logical, as-is; legacy =
                    # physical, heuristic divide).
                    contract_scale_wide = base_scale
                    align = page.evaluate(
                        """() => {
                            const b = document.body.getBoundingClientRect();
                            const de = document.documentElement;
                            // widest visible direct child of body
                            let child = null;
                            for (const el of document.body.children) {
                                const r = el.getBoundingClientRect();
                                const cs = getComputedStyle(el);
                                if (cs.position === 'fixed') continue;
                                if (!child
                                        || r.width > child.width) {
                                    child = {width: r.width,
                                             left: r.left,
                                             bottom: r.bottom,
                                             tag: el.tagName};
                                }
                            }
                            return {bodyWidth: b.width,
                                    bodyLeft: b.left,
                                    innerWidth: window.innerWidth,
                                    scrollW: de.scrollWidth,
                                    child: child};
                        }"""
                    )
                    exp_w = contract["w"] / contract_scale_wide
                    dw = abs(align["bodyWidth"] - exp_w)
                    child_ok = (align["child"] is None
                                or align["child"]["width"]
                                <= exp_w * 1.02 + 2)
                    ok = dw <= 2 and child_ok
                    checks.append({
                        "name": f"canvas_alignment[{name}]",
                        "pass": ok,
                        "detail": (
                            f"body {align['bodyWidth']:.0f}px vs contract "
                            f"{exp_w:.0f}px (Δ{dw:.0f}), widest in-flow "
                            f"child "
                            f"{align['child']['width']:.0f}px"
                            f"<{align['child']['tag']}>"
                            if align["child"] else
                            f"body {align['bodyWidth']:.0f}px vs contract "
                            f"{exp_w:.0f}px"
                        ),
                    })

                # Content assertions run once, on the desktop viewport
                # (text presence and box geometry are viewport-independent
                # for these fixed-canvas deliverables).
                if name == "desktop":
                    # --- texts_present --------------------------------
                    texts = layout.get("expected_texts") or []
                    if texts:
                        body_text = page.evaluate(
                            "document.body.innerText"
                        )
                        html_src = page.evaluate(
                            "document.documentElement.outerHTML"
                        )
                        hay_body, hay_html = (
                            _norm_text(body_text), _norm_text(html_src)
                        )
                        missing = [
                            t for t in texts
                            if _norm_text(t) not in hay_body
                            and _norm_text(t) not in hay_html
                        ]
                        checks.append({
                            "name": f"texts_present[{name}]",
                            "pass": not missing,
                            "detail": (
                                f"{len(missing)} missing of {len(texts)}: "
                                + "; ".join(f'"{t}"' for t in missing[:5])
                            ) if missing else
                            f"all {len(texts)} expected texts found",
                        })

                    # --- asset_geometry --------------------------------
                    # Only for contracted canvases: box_px is device-px
                    # there (contract_scale converts to CSS px). For
                    # non-contract layouts the physical/logical ratio is
                    # undefined — asserting would false-FAIL.
                    layout_assets = (layout.get("assets") or []
                                     if layout.get("canvas_contract")
                                     else [])
                    if layout_assets:
                        problems: List[str] = []
                        for a in layout_assets:
                            idx = a["index"]
                            info = page.evaluate(
                                """(idx) => {
                                    const sels = [
                                        'img[src*="asset_' + idx + '."]',
                                        'img[src*="asset_' + idx + '_"]',
                                        '[data-asset="asset_' + idx + '"]',
                                    ];
                                    for (const sel of sels) {
                                        const el = document.querySelector(sel);
                                        if (el) {
                                            const r = el.getBoundingClientRect();
                                            return {found: true,
                                                    w: r.width, h: r.height,
                                                    tag: el.tagName};
                                        }
                                    }
                                    return {found: false};
                                }""",
                                idx,
                            )
                            exp_w = a["box_px"]["w"] / contract_scale
                            exp_h = a["box_px"]["h"] / contract_scale
                            tol_w = max(GEOMETRY_TOLERANCE_ABS,
                                        exp_w * GEOMETRY_TOLERANCE_REL)
                            tol_h = max(GEOMETRY_TOLERANCE_ABS,
                                        exp_h * GEOMETRY_TOLERANCE_REL)
                            if not info["found"]:
                                problems.append(
                                    f"asset_{idx}: no <img src*=asset_{idx}> "
                                    "nor [data-asset] fallback in page"
                                )
                            elif (abs(info["w"] - exp_w) > tol_w
                                    or abs(info["h"] - exp_h) > tol_h):
                                problems.append(
                                    f"asset_{idx} "
                                    f"'{a['description'][:14]}': rendered "
                                    f"{info['w']:.0f}x{info['h']:.0f}, "
                                    f"expected {exp_w:.0f}x{exp_h:.0f} "
                                    f"(tol ±{tol_w:.0f}x±{tol_h:.0f})"
                                )
                        checks.append({
                            "name": f"asset_geometry[{name}]",
                            "pass": not problems,
                            "detail": (
                                f"{len(problems)} of {len(layout_assets)} "
                                "off: " + "; ".join(problems[:5])
                            ) if problems else
                            f"all {len(layout_assets)} assets within "
                            "geometry tolerance",
                        })

                    # --- container_geometry ----------------------------
                    # Same contract-scale rules as asset_geometry:
                    # container boxes are 2x device px on contracted
                    # canvases. Buttons/pills opt in via
                    # data-container="cN". Geometry only — the fitted
                    # radius is a reference (real UI often uses continuous
                    # curvature corners, which a circular-arc fit
                    # under-reads), so shape is judged on the diff sheet,
                    # not asserted.
                    layout_containers = (layout.get("containers") or []
                                         if layout.get("canvas_contract")
                                         else [])
                    if layout_containers:
                        c_problems: List[str] = []
                        for c in layout_containers:
                            idx = c["index"]
                            info = page.evaluate(
                                """(idx) => {
                                    const el = document.querySelector(
                                        '[data-container="c' + idx + '"]');
                                    if (!el) return {found: false};
                                    const r = el.getBoundingClientRect();
                                    return {found: true, w: r.width,
                                            h: r.height};
                                }""",
                                idx,
                            )
                            exp_w = c["w"] / contract_scale
                            exp_h = c["h"] / contract_scale
                            tol_w = max(GEOMETRY_TOLERANCE_ABS,
                                        exp_w * GEOMETRY_TOLERANCE_REL)
                            tol_h = max(GEOMETRY_TOLERANCE_ABS,
                                        exp_h * GEOMETRY_TOLERANCE_REL)
                            if not info["found"]:
                                c_problems.append(
                                    f"c{idx}: no [data-container=c{idx}] "
                                    "element in page"
                                )
                                continue
                            if (abs(info["w"] - exp_w) > tol_w
                                    or abs(info["h"] - exp_h) > tol_h):
                                c_problems.append(
                                    f"c{idx}: size "
                                    f"{info['w']:.0f}x{info['h']:.0f}"
                                    f" vs {exp_w:.0f}x{exp_h:.0f}"
                                    f" (tol ±{tol_w:.0f}x±{tol_h:.0f})"
                                )
                        checks.append({
                            "name": f"container_geometry[{name}]",
                            "pass": not c_problems,
                            "detail": (
                                f"{len(c_problems)} of "
                                f"{len(layout_containers)} off: "
                                + "; ".join(c_problems[:5])
                            ) if c_problems else
                            f"all {len(layout_containers)} containers "
                            "within geometry tolerance",
                        })

                    # --- skeleton_geometry ------------------------------
                    # Structural elements opt in via
                    # data-skeleton="sN". Surface types assert size like
                    # containers; text blocks assert CENTER only (font
                    # metrics legitimately change the ink box, position
                    # is what alignment needs).
                    layout_skeleton = (layout.get("skeleton") or []
                                       if layout.get("canvas_contract")
                                       else [])
                    if layout_skeleton:
                        s_problems: List[str] = []
                        s_warnings: List[str] = []
                        # Ink width for every text block in one shot —
                        # the element's flex box can be stretched wide
                        # enough to blind a rect-based overflow check
                        # (field failure 2026-09-29: IBM Plex Arabic
                        # block); the Range width is the actual glyph
                        # run. Asserted against the BASE (labeled) box,
                        # not the refined one: base is the pre-pipeline
                        # ground truth.
                        tb_idxs = [s["index"] for s in layout_skeleton
                                   if s["type"] == "text_block"]
                        ink_widths = page.evaluate(
                            """(idxs) => {
                                const out = {};
                                for (const idx of idxs) {
                                    const el = document.querySelector(
                                        '[data-skeleton="s' + idx + '"]');
                                    if (!el) continue;
                                    try {
                                        const r = document.createRange();
                                        r.selectNodeContents(el);
                                        const rects = [...r.getClientRects()]
                                            .filter(x => x.width > 0);
                                        out[idx] = rects.length
                                            ? Math.max(...rects.map(
                                                x => x.width)) : 0;
                                    } catch (e) { out[idx] = 0; }
                                }
                                return out;
                            }""",
                            tb_idxs,
                        ) or {}
                        for s in layout_skeleton:
                            idx = s["index"]
                            info = page.evaluate(
                                """(idx) => {
                                    const el = document.querySelector(
                                        '[data-skeleton="s' + idx + '"]');
                                    if (!el) return {found: false};
                                    const r = el.getBoundingClientRect();
                                    return {found: true, w: r.width,
                                            h: r.height,
                                            cx: r.left + r.width / 2,
                                            cy: r.top + r.height / 2};
                                }""",
                                idx,
                            )
                            exp_w = s["w"] / contract_scale
                            exp_h = s["h"] / contract_scale
                            exp_cx = (s["x"] + s["w"] / 2) / contract_scale
                            exp_cy = (s["y"] + s["h"] / 2) / contract_scale
                            # An edge-extended box is a fade-detection
                            # heuristic, NOT ground truth — assert such
                            # elements against their BASE (labeled) box,
                            # otherwise the page is built to the
                            # over-extension and every check reads green
                            # on garbage (field failure 2026-09-29: stars
                            # drawn 6.5px high into a caption).
                            if s.get("edge_extended") and s.get("base_box"):
                                bbx = s["base_box"]
                                exp_w = bbx["w"] / contract_scale
                                exp_h = bbx["h"] / contract_scale
                                exp_cx = (bbx["x"] + bbx["w"] / 2
                                          ) / contract_scale
                                exp_cy = (bbx["y"] + bbx["h"] / 2
                                          ) / contract_scale
                            if not info["found"]:
                                s_problems.append(
                                    f"s{idx} ({s['type']}): no "
                                    "[data-skeleton] element in page"
                                )
                                continue
                            if s["type"] == "text_block":
                                tol_c = max(8, exp_w * 0.15)
                                if (abs(info["cx"] - exp_cx) > tol_c
                                        or abs(info["cy"] - exp_cy)
                                        > tol_c):
                                    s_problems.append(
                                        f"s{idx} ({s['type']}): center "
                                        f"({info['cx']:.0f},"
                                        f"{info['cy']:.0f}) vs "
                                        f"({exp_cx:.0f},{exp_cy:.0f})"
                                        f" (tol ±{tol_c:.0f})"
                                    )
                                # Rendered ink much wider than the
                                # labeled box = font metrics drift or a
                                # mismatched family. This is a FAIL, not
                                # a warning: the ink is what the user
                                # sees, and a stretched flex box hides it
                                # from rect-based overflow checks
                                # (field failure 2026-09-29: IBM Plex
                                # block invading an icon).
                                ink_w = (ink_widths.get(idx)
                                         or ink_widths.get(str(idx)) or 0)
                                # Ink gate compares against the LABELED
                                # (base) box, not the pixel-refined box:
                                # the refine step re-estimates ink from
                                # thresholded pixels and under low-contrast
                                # text (frosted cards) it can capture only
                                # a fraction of the glyphs (field case
                                # 2026-10-09: 2-char label refined to a
                                # 1-char box). base_box is what the labeler
                                # confirmed as the ink extent — same
                                # ground-truth rationale as the
                                # edge-extended fallback above. Drift
                                # detection is unchanged: real drift still
                                # exceeds base*1.15.
                                gate_w = exp_w
                                if s.get("base_box"):
                                    gate_w = (s["base_box"]["w"]
                                              / contract_scale)
                                # 1.15 = labeled-box error (±3-5%) plus
                                # nearest-font ink variance; measured
                                # IBM Plex invasion was +39% — well past
                                if ink_w > gate_w * 1.15:
                                    s_problems.append(
                                        f"s{idx} ({s['type']}): ink width "
                                        f"{ink_w:.0f}css vs labeled box "
                                        f"{gate_w:.0f}css — text invades "
                                        f"neighbours; shrink font-size "
                                        f"or fix family, never "
                                        f"negative-margin"
                                    )
                                elif info.get("w", 0) > exp_w * 1.35:
                                    s_warnings.append(
                                        f"s{idx}: rendered width "
                                        f"{info['w']:.0f}css vs box "
                                        f"{exp_w:.0f}css — font wider "
                                        f"than source; adjust font, "
                                        f"do not negative-margin"
                                    )
                            else:
                                if s.get("edge_extended"):
                                    # The box was grown over a gradient
                                    # fade — its bounds are a candidate
                                    # awaiting human calibration, not a
                                    # hard geometry contract.
                                    s_warnings.append(
                                        f"s{idx}: edge-extended box "
                                        f"({info['w']:.0f}x{info['h']:.0f}"
                                        f" rendered vs {exp_w:.0f}x"
                                        f"{exp_h:.0f} css) — size "
                                        f"assertion skipped, confirm "
                                        f"bounds cover the full "
                                        f"structure in calibration"
                                    )
                                else:
                                    tol_abs = GEOMETRY_TOLERANCE_ABS
                                    tol_rel = GEOMETRY_TOLERANCE_REL
                                    if (s.get("type") == "container"
                                            and s.get("source") == "model"):
                                        # 1009-07：model-only 容器目测框
                                        # 不可信（实测按钮 76.5×24 被写成
                                        # 82×19，5px 压扁在旧容差绿灯放行）
                                        # ——收紧容差暴露目测误差：
                                        # ±3px 封顶（8% 只影响小元素下限，
                                        # 禁 max 语义——那会让收紧失效）
                                        tol_w = min(3.0, max(
                                            1.5, exp_w * 0.08))
                                        tol_h = min(3.0, max(
                                            1.5, exp_h * 0.08))
                                    else:
                                        tol_w = max(
                                            GEOMETRY_TOLERANCE_ABS,
                                            exp_w * GEOMETRY_TOLERANCE_REL)
                                        tol_h = max(
                                            GEOMETRY_TOLERANCE_ABS,
                                            exp_h * GEOMETRY_TOLERANCE_REL)
                                    if (abs(info["w"] - exp_w) > tol_w
                                            or abs(info["h"] - exp_h)
                                            > tol_h):
                                        s_problems.append(
                                            f"s{idx} ({s['type']}): size "
                                            f"{info['w']:.0f}x"
                                            f"{info['h']:.0f}"
                                            f" vs {exp_w:.0f}x{exp_h:.0f}"
                                            f" (tol ±{tol_w:.0f}x"
                                            f"±{tol_h:.0f})"
                                        )
                        checks.append({
                            "name": f"skeleton_geometry[{name}]",
                            "pass": not s_problems,
                            "detail": (
                                f"{len(s_problems)} of "
                                f"{len(layout_skeleton)} off: "
                                + "; ".join(s_problems[:5])
                            ) if s_problems else
                            f"all {len(layout_skeleton)} skeleton items "
                            "within tolerance",
                        })
                        if s_warnings:
                            checks.append({
                                "name": f"font_drift_warning[{name}]",
                                "pass": True,
                                "detail": "; ".join(s_warnings[:5]),
                            })

                    # --- text_overflow ---------------------------------
                    overflow = page.evaluate(
                        """() => {
                            const bad = [];
                            for (const el of document.querySelectorAll('body *')) {
                                if (el.children.length) continue;
                                const t = (el.innerText || '').trim();
                                if (!t) continue;
                                const cs = getComputedStyle(el);
                                if (cs.overflowX === 'hidden'
                                        || cs.overflow === 'hidden') continue;
                                if (el.clientWidth > 0
                                        && el.scrollWidth > el.clientWidth + 2) {
                                    bad.push('<' + el.tagName.toLowerCase()
                                        + '> "' + t.slice(0, 20)
                                        + '" sw=' + el.scrollWidth
                                        + ' cw=' + el.clientWidth);
                                }
                                if (bad.length >= 5) break;
                            }
                            return bad;
                        }"""
                    )
                    checks.append({
                        "name": f"text_overflow[{name}]",
                        "pass": not overflow,
                        "detail": "; ".join(overflow) if overflow
                        else "no leaf text element overflows its box",
                    })

                    # --- layout_integrity --------------------------------
                    # Three structural defects that geometry/overflow
                    # checks are blind to (field failures, 2026-09-28):
                    # 1. a text block CROSSING a neighbouring <img> —
                    #    usually the residue of negative-margin center
                    #    fixing when the web font renders wider than the
                    #    measured box;
                    # 2. a data-container whose children spill outside
                    #    the container's own box (button label wider
                    #    than the button);
                    # 3. any negative margin used as positioning — the
                    #    rules ban it, this is the enforcement.
                    integrity = page.evaluate(
                        """(overPhotoSels) => {
                            const bad = [];
                            const ov = (a, b) =>
                                Math.max(0, Math.min(a.right, b.right)
                                    - Math.max(a.left, b.left))
                                * Math.max(0, Math.min(a.bottom, b.bottom)
                                    - Math.max(a.top, b.top));
                            const imgs = [...document.querySelectorAll('img')]
                                .filter(el => !overPhotoSels.includes(
                                    'img[data-asset="'
                                    + (el.getAttribute('data-asset') || '')
                                        + '"]'))
                                .map(el => el.getBoundingClientRect());
                            for (const el of document.querySelectorAll(
                                    '[data-skeleton]')) {
                                if (el.querySelector('img')) continue;
                                const t = (el.innerText || '').trim();
                                if (!t) continue;
                                const r = el.getBoundingClientRect();
                                for (const ir of imgs) {
                                    const a = ov(r, ir);
                                    if (a > 9) {
                                        bad.push('text "' + t.slice(0, 14)
                                            + '" crosses an img ('
                                            + a.toFixed(0) + 'px2)');
                                        break;
                                    }
                                }
                            }
                            for (const el of document.querySelectorAll(
                                    '[data-container]')) {
                                const r = el.getBoundingClientRect();
                                for (const ch of el.children) {
                                    const cr = ch.getBoundingClientRect();
                                    const out = Math.max(
                                        r.left - cr.left,
                                        cr.right - r.right,
                                        r.top - cr.top,
                                        cr.bottom - r.bottom, 0);
                                    if (out > 3) {
                                        bad.push('<'
                                            + ch.tagName.toLowerCase()
                                            + '> spills out of container '
                                            + 'by ' + out.toFixed(0) + 'px');
                                    }
                                }
                            }
                            for (const el of document.querySelectorAll(
                                    'body *')) {
                                const cs = getComputedStyle(el);
                                for (const side of ['Left', 'Right',
                                        'Top', 'Bottom']) {
                                    if (parseFloat(
                                            cs['margin' + side]) < -2) {
                                        bad.push('<'
                                            + el.tagName.toLowerCase()
                                            + '> uses negative margin-'
                                            + side + ' ('
                                            + cs['margin' + side] + ')');
                                        break;
                                    }
                                }
                                if (bad.length >= 8) break;
                            }
                            return bad;
                        }""",
                        [f'img[data-asset="asset_{a["index"]}"]'
                         for a in (layout.get("assets") or [])
                         if a.get("over_photo_text_erased")],
                    )
                    checks.append({
                        "name": f"layout_integrity[{name}]",
                        "pass": not integrity,
                        "detail": "; ".join(integrity[:6]) if integrity
                        else "no text/img crossings, no container "
                        "spill, no negative margins",
                    })

                    # --- asset centroid alignment -----------------------
                    # For every container that holds EXACTLY ONE asset,
                    # the rendered asset must sit on the container's
                    # center within tolerance. Catches a frame-shifted
                    # icon that geometry assertions bless because the
                    # render faithfully honored a mis-calibrated base
                    # box (field failure 2026-09-29: gamepad ~10px off
                    # in its selected-state tile, all checks green).
                    if name == "desktop" and layout:
                        pairs = []
                        holder_boxes = []
                        for s in layout.get("skeleton", []):
                            if s.get("type") in ("container",
                                                 "button_bar", "nav_bar"):
                                holder_boxes.append(
                                    (f"skeleton s{s.get('index')}",
                                     f'[data-skeleton="s{s.get("index")}"]',
                                     (s.get("x"), s.get("y"),
                                      s.get("w"), s.get("h"))))
                        for c in layout.get("containers", []):
                            holder_boxes.append(
                                (f"container c{c.get('index')}",
                                 f'[data-container="c{c.get("index")}"]',
                                 (c.get("x"), c.get("y"),
                                  c.get("w"), c.get("h"))))
                        _assets = [a for a in layout.get("assets", [])
                                   if a.get("box_px")]
                        for hname, hsel, (hx, hy, hw, hh) in holder_boxes:
                            if not hw or not hh:
                                continue
                            inside = [
                                a for a in _assets
                                if a["box_px"]["x"] >= hx - 2
                                and a["box_px"]["y"] >= hy - 2
                                and (a["box_px"]["x"]
                                     + a["box_px"]["w"])
                                <= hx + hw + 2
                                and (a["box_px"]["y"]
                                     + a["box_px"]["h"])
                                <= hy + hh + 2]
                            if len(inside) != 1:
                                continue  # empty or shared containers
                            a = inside[0]
                            pairs.append({
                                "container": hname, "selector": hsel,
                                "asset": f"asset_{a['index']}",
                                "asset_sel":
                                    f'img[data-asset="asset_{a["index"]}"]',
                                "tol_px": round(
                                    max(8.0, 0.12 * min(hw, hh) / 2), 1),
                            })
                        if pairs:
                            res = page.evaluate(
                                """(pairs) => pairs.map(p => {
                                    const c = document.querySelector(
                                        p.selector);
                                    const i = document.querySelector(
                                        p.asset_sel);
                                    if (!c || !i) return {
                                        ...p, error: 'element missing'};
                                    const cr = c.getBoundingClientRect();
                                    const ir = i.getBoundingClientRect();
                                    return {...p,
                                        dx: +((ir.x + ir.width / 2)
                                            - (cr.x + cr.width / 2)
                                            ).toFixed(1),
                                        dy: +((ir.y + ir.height / 2)
                                            - (cr.y + cr.height / 2)
                                            ).toFixed(1)};
                                })""",
                                pairs)
                            # INFO channel, NOT a gate: an off-center
                            # asset can be the design itself (RTL button
                            # icons hug one side) and no machine can tell
                            # that from "frame-shifted". Surface the
                            # offsets so the human check looks there —
                            # do NOT auto-FAIL (field failure 2026-09-29:
                            # gamepad ~7px off was invisible everywhere).
                            off_items = [
                                r for r in res
                                if r.get("error")
                                or abs(r.get("dx", 0)) > r["tol_px"]
                                or abs(r.get("dy", 0)) > r["tol_px"]]
                            centroid_offsets.extend(
                                {k: r.get(k) for k in
                                 ("container", "asset", "dx", "dy",
                                  "tol_px", "error")}
                                for r in off_items)
                            if off_items:
                                print(
                                    "asset centroid REVIEW (info, not a "
                                    "gate): " + "; ".join(
                                        f"{r['container']}/{r['asset']} "
                                        f"off ({r.get('dx')}px,"
                                        f"{r.get('dy')}px) "
                                        f"tol {r['tol_px']}px"
                                        for r in off_items[:8]))

                    # --- raw occlusion gate --------------------------------
                    # Opaque (RAW) crops occlude what they touch: their
                    # baked-in background is a rectangle of foreign
                    # pixels. If such an img sits on/next to (gap < 2px)
                    # a text block, the text is visually eaten even when
                    # the geometry never "intersects" (field failure
                    # 2026-09-29: swords crop covering معركة at exactly
                    # 0px gap). Alpha assets are exempt — no baked
                    # background. over_photo_text_erased assets are also
                    # exempt (2026-10-08 重影根因修复配套): their baked-in
                    # text pixels were inpainted away at extraction, the
                    # DOM text layer is SUPPOSED to sit on them.
                    if name == "desktop" and layout:
                        raw_assets = [
                            a for a in (layout.get("assets") or [])
                            if a.get("box_px") and not a.get("alpha")
                            and not a.get("over_photo_text_erased")]
                        if raw_assets:
                            raw_ids = {
                                f'img[data-asset="asset_{a["index"]}"]'
                                for a in raw_assets}
                            occ = page.evaluate(
                                """(rawSels) => {
                                    const imgs = rawSels
                                        .map(s => document.querySelector(s))
                                        .filter(Boolean)
                                        .map(el => el.getBoundingClientRect());
                                    const texts = [...document
                                        .querySelectorAll('[data-skeleton]')]
                                        .filter(el => (el.innerText || '')
                                            .trim())
                                        .map(el => el.getBoundingClientRect());
                                    const bad = [];
                                    for (const r of imgs) {
                                        for (const t of texts) {
                                            const dx = Math.max(
                                                t.left - r.right,
                                                r.left - t.right);
                                            const dy = Math.max(
                                                t.top - r.bottom,
                                                r.top - t.bottom);
                                            const sep = Math.max(dx, dy);
                                            if (sep < 2) bad.push({
                                                sep: +sep.toFixed(1)});
                                        }
                                    }
                                    return bad;
                                }""",
                                list(raw_ids))
                            checks.append({
                                "name": "raw_occlusion[desktop]",
                                "pass": not occ,
                                "detail":
                                    (f"{len(occ)} raw crop(s) touching/"
                                     f"overlapping a text block (gap<2px)"
                                     ) if occ else
                                    f"all {len(raw_assets)} raw crops "
                                    "clear of text blocks",
                            })

                    # --- icon contract gate --------------------------------
                    # Inline SVG icons are a probabilistic chain (a
                    # subagent "recognizes" a library glyph; a wrong
                    # variant reads fine in a band). Two hard gates:
                    # (1) every svg[data-icon] key must be in the
                    # human-confirmed manifest — an unconfirmed key FAILs;
                    # (2) an icon standing in for an asset pit must
                    # render its INK at the pit size — Phosphor glyphs
                    # carry ~12-22% viewBox padding, so rect size alone
                    # blesses icons that draw at 60-70% of the source
                    # (field failure 2026-09-29: cart/gear at ~65%).
                    if name == "desktop":
                        import json as _json
                        manifest_path = (Path(__file__).resolve().parent
                                         .parent / "references"
                                         / "icon_manifest.json")
                        manifest: Dict[str, Any] = {}
                        if manifest_path.is_file():
                            try:
                                manifest = _json.loads(
                                    manifest_path.read_text(
                                        encoding="utf-8"))
                            except Exception:
                                manifest = {}
                        raw_assets2 = [
                            a for a in (layout.get("assets") or [])
                            if a.get("box_px")]
                        box_by_index = {
                            a["index"]: a["box_px"] for a in raw_assets2}
                        icons = page.evaluate(
                            """() => [...document.querySelectorAll(
                                    'svg[data-icon]')].map(s => {
                                const r = s.getBoundingClientRect();
                                let bw = 0, vw = 0;
                                try {
                                    bw = s.getBBox().width;
                                    vw = s.viewBox.baseVal.width || 0;
                                } catch (e) {}
                                return {
                                    icon: s.getAttribute('data-icon'),
                                    asset: s.getAttribute('data-asset'),
                                    w: +r.width.toFixed(1), bw, vw,
                                };
                            })""")
                        icon_problems: List[str] = []
                        import numpy as _np_icon

                        def _bin_iou(a_bgr, b_bgr) -> float:
                            """二值结构 IoU（resize 32×32，Otsu 阈值）。"""
                            def _bin(im):
                                g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                                _, b = cv2.threshold(
                                    g, 0, 255, cv2.THRESH_BINARY
                                    + cv2.THRESH_OTSU)
                                return cv2.resize(
                                    b, (32, 32)) > 127
                            ba, bb = _bin(a_bgr), _bin(b_bgr)
                            inter = (ba & bb).sum()
                            union = (ba | bb).sum()
                            return (inter / union) if union else 0.0

                        for _ii, ic in enumerate(icons):
                            key = ic.get("icon") or ""
                            entry_m = manifest.get(key)
                            confirmed = bool(
                                isinstance(entry_m, dict)
                                and entry_m.get("confirmed") is True)
                            if not confirmed:
                                icon_problems.append(
                                    f"unconfirmed icon '{key}' — render, "
                                    f"check at 4x, then set confirmed:true "
                                    f"in references/icon_manifest.json")
                                continue
                            if ic.get("asset") and ic.get("vw") > 0:
                                m = re.match(r"asset_(\d+)",
                                             ic["asset"])
                                bx = (box_by_index.get(int(m.group(1)))
                                      if m else None)
                                if bx:
                                    ink = (ic["w"]
                                           * (ic["bw"] / ic["vw"]))
                                    target = (bx["w"] / contract_scale)
                                    if abs(ink - target) > target * 0.15:
                                        icon_problems.append(
                                            f"{key}: ink {ink:.0f}css vs "
                                            f"pit {target:.0f}css — "
                                            f"viewBox padding not "
                                            f"compensated")
                                # 1009-12 形态粗验（守门）：元素截图 vs
                                # 源图裁剪的二值结构 IoU——蓝牙 S 畸形
                                # 实证（manifest+墨迹宽双闸都放行了
                                # 畸形）。alpha 通道=前景（透明底图标
                                # 截图）；源图裁剪暗于局部底=前景。
                                # 无源图参照（非素材坑图标）跳过。
                                if ic.get("asset") and (
                                        layout.get("source_image")
                                        or image_path):
                                    _m2 = re.match(r"asset_(\d+)",
                                                   ic["asset"])
                                    _bx2 = (box_by_index.get(
                                        int(_m2.group(1))) if _m2
                                        else None)
                                    if _bx2:
                                        try:
                                            import io as _io
                                            from PIL import (
                                                Image as _PImg)
                                            from PIL import (
                                                ImageFilter as _PImgFil)
                                            # 形态截图须在独立透明页
                                            # 渲染——产物页面自身有背景
                                            # 色时 omit_background 不产生
                                            # alpha（实测：alpha 全 255，
                                            # 前景=整张截图，IoU 虚高
                                            # 0.79 完全失真）
                                            _outer = page.evaluate(
                                                """(idx) => document
                                                    .querySelectorAll(
                                                        'svg[data-icon]')
                                                    [idx].outerHTML""",
                                                _ii)
                                            try:
                                                _iso = page.context.new_page()
                                            except Exception:
                                                _iso = browser.new_context().new_page()
                                            _iso.set_content(
                                                '<html style='
                                                '"background:transparent">'
                                                "<body style=\"margin:0\">"
                                                + _outer + "</body></html>")
                                            _el = _iso.locator("svg").first
                                            _png = _el.screenshot(
                                                omit_background=True)
                                            _iso.close()
                                            _eli = _PImg.open(
                                                _io.BytesIO(_png)
                                                ).convert("RGBA")
                                            _aimg = _eli.split()[3].point(
                                                lambda v: 255
                                                if v > 10 else 0)
                                            _abb = _aimg.getbbox()
                                            if _abb:
                                                _aimg = _aimg.crop(_abb)
                                            _a = _aimg.resize((32, 32)).filter(
                                                _PImgFil.MaxFilter(3))
                                            _src = _PImg.open(str(
                                                layout.get("source_image")
                                                or image_path)
                                                ).convert("L")
                                            # 源图恒物理平面：逻辑框 ×
                                            # dpr 裁剪（contract_scale 是
                                            # 渲染平面换算=1，裁物理源图
                                            # 会裁到左上角背景 IoU=0）
                                            _src_scale = float(
                                                layout.get("dpr") or 1.0)
                                            _sc = _src.crop((
                                                round(_bx2["x"] * _src_scale),
                                                round(_bx2["y"] * _src_scale),
                                                round((_bx2["x"] + _bx2["w"]) * _src_scale),
                                                round((_bx2["y"] + _bx2["h"]) * _src_scale)))
                                            # 前景=与边缘中位色距离
                                            # >45 的像素（极性自适应：
                                            # 亮压暗/暗压亮都正确——
                                            # 固定暗阈值在亮图标压暗底
                                            # 时取到底板，IoU 必假低）
                                            import numpy as _npf
                                            _arr = _npf.asarray(
                                                _sc, dtype=float)
                                            _edge = _npf.concatenate([
                                                _arr[:2].ravel(),
                                                _arr[-2:].ravel(),
                                                _arr[:, :2].ravel(),
                                                _arr[:, -2:].ravel()])
                                            _bgc = float(_npf.median(
                                                _edge))
                                            _fg = (_npf.abs(_arr - _bgc)
                                                   > 45)
                                            _am = _PImg.fromarray(
                                                (_fg * 255).astype("uint8"))
                                            _bb = _am.point(
                                                lambda v: 255 if v > 127
                                                else 0).getbbox()
                                            if _bb:
                                                _am = _am.crop(_bb)
                                            # 1009-12b: 源侧与渲染侧都
                                            # 收齐到 ink bbox 再比——
                                            # 源 crop 含坑位余白而渲染
                                            # 截图紧贴元素盒，取景不齐
                                            # 使 IoU 系统性假低（搜索
                                            # 0.15/相机 0.24 实证，人眼
                                            # 形态相符）
                                            _b = _am.resize((32, 32)).filter(
                                                _PImgFil.MaxFilter(3))
                                            inter = sum(
                                                1 for i in range(32)
                                                for j in range(32)
                                                if (_a.getpixel((i, j)) > 127)
                                                == (_b.getpixel((i, j)) > 127)
                                                and _a.getpixel((i, j)) > 127)
                                            union = sum(
                                                1 for i in range(32)
                                                for j in range(32)
                                                if (_a.getpixel((i, j)) > 127)
                                                or (_b.getpixel((i, j)) > 127))
                                            iou = (inter / union) if union else 0.0
                                            if iou < 0.30:
                                                icon_problems.append(
                                                    f"{key}: form mismatch "
                                                    f"(structural IoU {iou:.2f}"
                                                    f" < 0.30 vs source crop)"
                                                )
                                        except Exception as _exc:
                                            icon_problems.append(
                                                f"{key}: form check ERROR "
                                                f"{_exc} — must be "
                                                f"investigated (silent-pass"
                                                f" forbidden)")
                        checks.append({
                            "name": "icon_contract[desktop]",
                            "pass": not icon_problems,
                            "detail": ("; ".join(icon_problems[:5])
                                       if icon_problems else
                                       f"all {len(icons)} inline icons "
                                       "manifest-confirmed and "
                                       "ink-matched"),
                        })

                    # --- styles_consistency -------------------------------
                    # styles.json (font_probe.py) is the resolved contract
                    # for text typography (family/weight/size, with
                    # sourced-from). The page must match it computed-style
                    # for style — this is what turns "typography rules"
                    # from prompt advice into a checkable contract.
                    styles_path = out_dir / "styles.json"
                    if name == "desktop" and not styles_path.is_file():
                        # 基准门禁（2026-10-07）：字体合同缺失 = 不可
                        # 审计 = FAIL，不是静默跳过
                        checks.append({
                            "name": "styles_consistency[desktop]",
                            "pass": False,
                            "detail": "styles.json missing — font "
                                      "contract unauditable (run "
                                      "font_probe)"})
                    if styles_path.is_file() and name == "desktop":
                        try:
                            styles = json.loads(
                                styles_path.read_text(encoding="utf-8"))
                        except Exception:  # noqa: BLE001
                            styles = None
                        entries = (styles or {}).get("text_blocks") or {}
                        if not entries:
                            checks.append({
                                "name": "styles_consistency[desktop]",
                                "pass": False,
                                "detail": "styles.json unreadable or "
                                          "empty — font contract "
                                          "unauditable"})
                        if entries:
                            mismatch = page.evaluate(
                                """(entries) => {
                                    const bad = [];
                                    for (const [idx, spec] of
                                            Object.entries(entries)) {
                                        const el = document.querySelector(
                                            '[data-skeleton="' + idx + '"]');
                                        if (!el) {
                                            bad.push(idx
                                                + ': no [data-skeleton] '
                                                + 'element in page');
                                            continue;
                                        }
                                        const cs = getComputedStyle(el);
                                        if (spec.family) {
                                            const head = String(spec.family)
                                                .toLowerCase().split(' ')[0];
                                            if (!cs.fontFamily.toLowerCase()
                                                    .includes(head))
                                                bad.push(idx
                                                    + ': family "'
                                                    + cs.fontFamily.slice(0, 32)
                                                    + '" vs ' + spec.family);
                                        }
                                        if (spec.weight) {
                                            const w = parseInt(cs.fontWeight);
                                            if (Math.abs(w - spec.weight) > 100)
                                                bad.push(idx
                                                    + ': weight ' + w
                                                    + ' vs ' + spec.weight);
                                        }
                                        if (spec.size_css) {
                                            const fs = parseFloat(cs.fontSize);
                                            if (Math.abs(fs - spec.size_css)
                                                    > 1.8)
                                                bad.push(idx
                                                    + ': size '
                                                    + cs.fontSize + ' vs '
                                                    + spec.size_css + 'css');
                                        }
                                    }
                                    return bad;
                                }""", entries)
                            checks.append({
                                "name": f"styles_consistency[{name}]",
                                "pass": not mismatch,
                                "detail": "; ".join(mismatch[:5])
                                if mismatch else
                                f"page matches styles.json "
                                f"({len(entries)} text blocks)",
                            })

                    # --- asset_blend ---------------------------------
                    # Seam detector for rectangular crops (see
                    # check_asset_blend). Runs on the just-taken desktop
                    # screenshot; complements the band-averaged diff
                    # sheet, which dilutes thin seams.
                    if layout_assets and "desktop" in screenshots:
                        alpha_used = page.evaluate(
                            """() => {
                                const out = {};
                                for (const i of document.images) {
                                    const s = i.currentSrc || i.src;
                                    const m = s.match(/asset_(\\d+)/);
                                    if (m) out[m[1]] = /_alpha\\./.test(s);
                                }
                                return out;
                            }"""
                        )
                        fails, warns = check_asset_blend(
                            Path(screenshots["desktop"]),
                            layout_assets, contract_scale, alpha_used,
                        )
                        checks.append({
                            "name": f"asset_blend[{name}]",
                            "pass": not fails,
                            "detail": (
                                "seam: " + "; ".join(fails[:5])
                                if fails else
                                ("soft seam (warn only): "
                                 + "; ".join(warns[:5])
                                 if warns else
                                 f"all {len(layout_assets)} crops blend "
                                 "with the page background"),
                            ),
                        })
                page.close()
        finally:
            browser.close()

    # 假 PASS 修复（2026-10-07）：passed 在此处**不得**提前计算——
    # diff/render 等裁判材料的 FAIL 项在其后追加，提前算会被漏掉
    # （PASS 项全部通过、材料 FAIL 却仍 ok 的假绿通道）。
    report = {
        "browser": channel,
        "screenshots": screenshots,
        "checks": checks,
    }
    if centroid_offsets:
        report["centroid_review"] = {
            "note": ("info only, NOT a gate — an off-center asset can be "
                     "the design itself; human check required"),
            "offsets": centroid_offsets,
        }

    # Source-vs-render diff sheet: generated on every run (PASS or FAIL)
    # — the post-PASS visual audit happens here, not on the raw preview.
    source_ref = layout.get("source_image")
    if not (source_ref and Path(source_ref).is_file()):
        source_ref = str(image_path) if image_path else None
    diff_info = None
    if source_ref and Path(source_ref).is_file() and "desktop" in screenshots:
        try:
            diff_info = build_diff_sheet(
                Path(source_ref),
                Path(screenshots["desktop"]),
                out_dir / "_diff_sheet.png",
                assets=(layout.get("assets") if layout else None),
                text_blocks=[
                    {"x": s["x"], "y": s["y"], "w": s["w"], "h": s["h"]}
                    for s in (layout.get("skeleton") or [])
                    if s.get("type") == "text_block"],
                src_box_scale=src_box_scale,
                ren_box_scale=ren_box_scale,
            )
        except Exception as exc:  # noqa: BLE001 — judge material, IS a gate
            print(f"FAIL: diff sheet failed: {exc}")
            checks.append({"name": "diff_sheet", "pass": False,
                           "detail": f"diff sheet generation failed: {exc}"})
    if source_ref and Path(source_ref).is_file() and not diff_info:
        # 守门员：材料静默缺失（函数返回 None）= 终审不可执行 = FAIL
        checks.append({"name": "diff_sheet", "pass": False,
                       "detail": "diff sheet not produced (generation "
                                 "returned None)"})
    if diff_info:
        report["diff_sheet"] = diff_info["path"]
        worst = diff_info["bands"][0] if diff_info["bands"] else None
        print(f"diff sheet: {diff_info['path']}"
              + (f" (worst band: BAND {worst['band']} avgΔ={worst['avg']})"
                 if worst else ""))

    # Per-asset pick-up check sheet (source vs render, zoomed) — the
    # step-5 mandatory eyeball pass for shape-level matte distortion
    # (shrunken icons, eaten edges) that band diffs dilute away.
    # NOTE: rc_scale follows the same coordinate contract as the main
    # loop — logical layout (dpr field present) → 1; legacy physical →
    # heuristic.
    rc_scale = base_scale
    rc_assets = layout.get("assets") or []
    if source_ref and Path(source_ref).is_file() and "desktop" in screenshots \
            and rc_assets:
        try:
            rc_info = build_render_check(
                Path(source_ref), Path(screenshots["desktop"]),
                rc_assets, out_dir / "_asset_render_check.png",
                rc_scale, src_box_scale=src_box_scale,
            )
            report["render_check"] = rc_info["paths"]
            report["render_check_review"] = rc_info["review"]
            print(f"render check: {len(rc_info['paths'])} sheet(s), "
                  f"{rc_info['rows']} rows, {rc_info['review']} REVIEW")
        except Exception as exc:  # noqa: BLE001 — judge material, IS a gate
            print(f"FAIL: render check failed: {exc}")
            checks.append({"name": "render_check", "pass": False,
                           "detail": f"render check generation failed: {exc}"})

    # --- font_drift_check (WARN channel, data-backed) ---------------------
    # Compare ink height ratio & stroke density between the source and the
    # render for every program-verified text block. Catches "font/weight/
    # size drifted from the source" with numbers instead of eyeballing —
    # the exact failure that cost two manual font rounds (2026-09-28/29).
    if source_ref and Path(source_ref).is_file() and "desktop" in screenshots \
            and layout:
        try:
            drift = _font_drift_check(
                Path(source_ref), Path(screenshots["desktop"]), layout,
                src_box_scale=src_box_scale, ren_box_scale=ren_box_scale)
            checks.append({
                "name": "font_drift_check[desktop]",
                "pass": True,
                "detail": ("; ".join(drift[:5]) if drift else
                           "text ink height & density within tolerance"),
            })
        except Exception as exc:  # noqa: BLE001 — audit aid, not a gate
            checks.append({
                "name": "font_drift_check[desktop]",
                "pass": True,
                "detail": f"skipped: {exc}",
            })

    # 最终判定：所有 check 追加完毕后统一计算（含裁判材料 FAIL）——
    # 假 PASS 修复（2026-10-07）：passed 不得在 diff/render 材料段之前算
    passed = all(c["pass"] for c in checks)
    report["ok"] = passed
    (out_dir / "verify_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )
    for c in checks:
        mark = "PASS" if c["pass"] else "FAIL"
        print(f"[{mark}] {c['name']}: {c['detail']}")
    print(f"\n{'PASS' if passed else 'FAIL'} — report: "
          f"{out_dir / 'verify_report.json'}")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", required=True, help="generated index.html")
    ap.add_argument("--layout", help="layout.json from extract_assets.py")
    ap.add_argument("--out", required=True, help="report output directory")
    ap.add_argument("--image", help="source screenshot (fallback when "
                    "layout.json has no source_image record)")
    args = ap.parse_args()
    return run(Path(args.html),
               Path(args.layout) if args.layout else None,
               Path(args.out),
               Path(args.image) if args.image else None)


if __name__ == "__main__":
    sys.exit(main())
