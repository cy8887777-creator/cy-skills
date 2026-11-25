# -*- coding: utf-8 -*-
"""Deterministic asset pipeline for image-to-code-skills.

Input:  a screenshot + assets.json written by the agent AFTER inspecting
        the image (descriptions + box_2d labels, 0-1000 normalized,
        [ymin, xmin, ymax, xmax]).
Output: everything the code-writing step needs, no model calls inside:
  out/assets/asset_N.png        raw crop
  out/assets/asset_N_alpha.png  transparent PNG (u2net, when want_alpha)
  out/layout_brief.txt          pixel-geometry layout brief + per-row color
                                palettes + verbatim text list (read before
                                coding)
  out/layout.json               machine-readable layout (used by
                                verify_page.py; carries expected_texts)
  out/assets_report.json        per-asset status

Cluster/row/column rules are ported 1:1 from the screenshot-to-code
project's layout_plan.py (bottom-bar 0.88 / top-bar 0.06 / full-row 0.6 /
column 0.12 / portrait canvas 1.3) so the brief carries the same
guarantees: rows in order, pixel pitches, fixed bottom bar, canvas
contract for portrait screens.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PIL import Image, ImageFilter

# --- constants ported from the project's layout planner -----------------
BOTTOM_BAR_Y_FRACTION = 0.88
TOP_BAR_Y_FRACTION = 0.06
COLUMN_X_FRACTION = 0.12
FULL_ROW_X_FRACTION = 0.6
PORTRAIT_ASPECT_THRESHOLD = 1.3

# CLIP-style normalization the U2Net family was trained with (same
# constants rembg uses, so off-the-shelf .onnx files behave identically).
# 入场预处理按模型各自的口径（以 rembg 官方实现为准）——两模型严禁共用
# 同一套归一化：isnet 对输入分布敏感，错配口径会产出无信号掩码（入场即废，
# 2026-09-29 首页黑改实测：isnet 在 13/20 素材被 guard 误判出局）。
MODEL_PROFILES = {
    "u2net": {"mean": (0.485, 0.456, 0.406), "std": (0.229, 0.224, 0.225)},
    "isnet": {"mean": (0.5, 0.5, 0.5), "std": (1.0, 1.0, 1.0)},
}

# Model catalog: both are rembg-ecosystem U2Net-family ONNX files sharing
# one inference path (RGB in -> probability map out). "auto" prefers
# isnet-general-use (2022, sharper edges, better general-object recall)
# and falls back to u2net (2018) when isnet is not installed.
MODEL_FILES = {
    "u2net": "u2net.onnx",
    "isnet": "isnet-general-use.onnx",
}
_model_candidates_cache: dict = {}


def model_candidates(filename: str) -> List[Path]:
    if filename not in _model_candidates_cache:
        dirs: List[Path] = []
        env_file = os.environ.get("I2C_BG_MODEL")
        if env_file:
            dirs.append(Path(env_file))
        env_dir = os.environ.get("I2C_MODELS_DIR")
        if env_dir:
            dirs.append(Path(env_dir) / filename)
        dirs.append(Path(__file__).resolve().parent.parent / "models"
                    / filename)
        env_backend = os.environ.get("I2C_S2C_BACKEND")
        if env_backend:
            dirs.append(Path(env_backend) / "models" / filename)
        dirs.append(
            Path(r"D:\screenshot-to-code\backend\models") / filename
        )
        seen: set = set()
        _model_candidates_cache[filename] = [
            p for p in dirs if not (p in seen or seen.add(p))
        ]
    return _model_candidates_cache[filename]


def find_model(model: str) -> Optional[Path]:
    """Resolve 'u2net' / 'isnet' / 'auto' (isnet first, u2net fallback)."""
    names = ((MODEL_FILES["isnet"], MODEL_FILES["u2net"])
             if model == "auto" else (MODEL_FILES[model],))
    for filename in names:
        for p in model_candidates(filename):
            try:
                if p.is_file() and p.stat().st_size > 100 * 1024 * 1024:
                    return p
            except OSError:
                continue
    return None


_sessions: Dict[str, Any] = {}
_sessions_lock = threading.Lock()


class BgRemover:
    """Minimal in-process U2Net-family ONNX wrapper (ported from
    bg_removal_local.py — tensor names read from the session, first
    output is the fused probability map) + mask post-processing:
    threshold binarization, morphological erode/dilate, largest-component
    keep. Post-processing runs on the small mask before upscaling, so it
    costs milliseconds and fixes the raw model's fuzzy/empty masks."""

    def __init__(self, model_path: Path):
        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.output_name = self.session.get_outputs()[0].name
        # Input size is model-specific (u2net 320, isnet 1024) — read it
        # from the session instead of hardcoding.
        try:
            size = int(inp.shape[2])
            if not 32 <= size <= 4096:
                raise ValueError(size)
        except (TypeError, ValueError, IndexError):
            size = 320
        self.input_size = size
        # Per-model preprocess profile — keyed by the catalog filename so
        # each entrant steps in with its OWN normalization rules.
        profile_key = next(
            (k for k, f in MODEL_FILES.items()
             if Path(model_path).name == f), "u2net")
        profile = MODEL_PROFILES.get(profile_key,
                                     MODEL_PROFILES["u2net"])
        self.profile_key = profile_key
        self._mean = profile["mean"]
        self._std = profile["std"]
        # Entry health signal (raw prediction range) — refreshed on every
        # inference; a flat range means the model produced NO signal at
        # all (preprocess mismatch), which is an entry-stage defect, not
        # a low-foreground verdict for the guard to make.
        self.last_signal: tuple = (0.0, 0.0)

    def _predict_small_mask(self, image: Image.Image) -> Image.Image:
        import numpy as np

        resized = image.resize((self.input_size, self.input_size))
        array = np.asarray(resized.convert("RGB"), dtype=np.float32) / 255.0
        array = (array - np.array(self._mean, dtype=np.float32)) / np.array(
            self._std, dtype=np.float32
        )
        tensor = np.transpose(array, (2, 0, 1))[np.newaxis, ...].astype(
            np.float32
        )
        prediction = self.session.run(
            [self.output_name], {self.input_name: tensor}
        )[0][0][0]
        minimum, maximum = prediction.min(), prediction.max()
        self.last_signal = (float(minimum), float(maximum))
        if maximum > minimum:
            prediction = (prediction - minimum) / (maximum - minimum)
        return Image.fromarray((prediction * 255.0).astype(np.uint8))

    def remove_background(
        self,
        image: Image.Image,
        alpha_threshold: int = 100,
        keep_largest: bool = True,
        erode_px: int = 0,
        dilate_px: int = 0,
    ) -> Image.Image:
        import numpy as np

        mask = np.asarray(self._predict_small_mask(image)).copy()

        def morph(m: "np.ndarray", iters: int, op: str) -> "np.ndarray":
            for _ in range(max(0, iters)):
                padded = np.pad(m, 1, constant_values=0)
                stack = np.stack([
                    padded[dy: dy + m.shape[0], dx: dx + m.shape[1]]
                    for dy in range(3) for dx in range(3)
                ])
                m = (stack.min(axis=0) if op == "erode"
                     else stack.max(axis=0))
            return m

        mask = morph(mask, erode_px, "erode")
        mask = morph(mask, dilate_px, "dilate")

        if alpha_threshold > 0:
            mask = np.where(mask < alpha_threshold, 0, 255).astype(np.uint8)

        if keep_largest:
            mask = _keep_largest_component(mask)

        alpha = Image.fromarray(mask).resize(image.size, Image.LANCZOS)
        alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))  # soften jaggies
        return Image.merge("RGBA", (*image.convert("RGB").split(), alpha))


def _keep_largest_component(mask: "Any") -> "Any":
    """BFS flood fill on the small mask: keep only the largest 4-connected
    foreground component (drops scattered noise blobs)."""
    import numpy as np
    from collections import deque

    fg = mask > 127
    h, w = fg.shape
    labels = np.zeros((h, w), dtype=np.int32)
    best_id, best_size = 0, 0
    current = 0
    for sy in range(h):
        for sx in range(w):
            if not fg[sy, sx] or labels[sy, sx]:
                continue
            current += 1
            size = 0
            queue = deque([(sy, sx)])
            labels[sy, sx] = current
            while queue:
                y, x = queue.popleft()
                size += 1
                for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= ny < h and 0 <= nx < w and fg[ny, nx] \
                            and not labels[ny, nx]:
                        labels[ny, nx] = current
                        queue.append((ny, nx))
            if size > best_size:
                best_id, best_size = current, size
    if best_id == 0:
        return np.zeros_like(mask)
    return np.where(labels == best_id, mask, 0).astype(np.uint8)


def get_remover(model: str = "auto") -> BgRemover:
    model_path = find_model(model)
    if model_path is None:
        raise FileNotFoundError(
            "no background-removal model found (tried isnet-general-use,"
            " u2net); run doctor.py first. Looked in: "
            + "; ".join(str(p.parent) for p in model_candidates(
                MODEL_FILES["u2net"]))
        )
    with _sessions_lock:
        key = str(model_path)
        if key not in _sessions:
            _sessions[key] = BgRemover(model_path)
        return _sessions[key]


# --- assets.json handling ------------------------------------------------

def read_json(path: Path) -> Any:
    """utf-8 first, GBK fallback (zh-CN Windows editors default to GBK)."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return json.loads(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"cannot decode {path} (tried utf-8, gbk)")


SKELETON_TYPES = ("container", "text_block", "button_bar", "nav_bar",
                  "decoration")


def parse_skeleton(raw: Any) -> List[Dict[str, Any]]:
    """Optional 'skeleton' array: the page's structural elements (cards,
    text blocks, button bars, nav bars, decorations) as agent-labeled
    boxes. Kept strictly separate from the asset ledger — skeleton items
    are never cropped or background-removed; they are refined against the
    pixels and emitted as the brief's SKELETON section."""
    if not isinstance(raw, dict):
        return []
    items = raw.get("skeleton")
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise SystemExit(f"skeleton[{i}] is not an object")
        stype = str(item.get("type") or "").strip()
        if stype not in SKELETON_TYPES:
            raise SystemExit(
                f'skeleton[{i}]: type must be one of {", ".join(SKELETON_TYPES)}'
            )
        box = item.get("box_2d")
        if (not isinstance(box, (list, tuple)) or len(box) != 4
                or not all(isinstance(v, (int, float)) for v in box)):
            raise SystemExit(
                f'skeleton[{i}]: box_2d must be [ymin,xmin,ymax,xmax] '
                "in 0-1000 normalized coordinates"
            )
        ymin, xmin, ymax, xmax = (float(v) for v in box)
        if not all(0 <= v <= 1000 for v in (ymin, xmin, ymax, xmax)):
            raise SystemExit(
                f'skeleton[{i}]: box_2d values must be within 0-1000'
            )
        out.append({
            "index": i,
            "type": stype,
            "text": str(item.get("text") or "").strip(),
            "ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax,
        })
    return out


def parse_assets(raw: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Validate the agent-written assets.json entries.

    Accepts either a bare list of entries or an object
    '{"assets": [...], "texts": [...], "skeleton": [...]}'. texts is the
    verbatim copy list that lands in the brief and in layout.json as
    expected_texts for verify_page.py's text assertions; skeleton is the
    optional structural-element ledger (kept apart from assets — never
    cropped, never background-removed).
    """
    texts: List[str] = []
    skeleton: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        raw_texts = raw.get("texts")
        if isinstance(raw_texts, list):
            texts = [str(t) for t in raw_texts if str(t).strip()]
        skeleton = parse_skeleton(raw)
        raw = raw.get("assets")
    if not isinstance(raw, list) or not raw:
        raise SystemExit(
            "assets.json must be a non-empty list of "
            '{"description", "box_2d": [ymin,xmin,ymax,xmax], "want_alpha"} '
            '(or {"assets": [...], "texts": [...]})'
        )
    parsed: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SystemExit(f"assets[{i}] is not an object")
        desc = str(item.get("description") or f"asset_{i}").strip()
        box = item.get("box_2d")
        if (not isinstance(box, (list, tuple)) or len(box) != 4
                or not all(isinstance(v, (int, float)) for v in box)):
            raise SystemExit(
                f'assets[{i}] "{desc}": box_2d must be [ymin,xmin,ymax,xmax] '
                "in 0-1000 normalized coordinates"
            )
        ymin, xmin, ymax, xmax = (float(v) for v in box)
        if not all(0 <= v <= 1000 for v in (ymin, xmin, ymax, xmax)):
            raise SystemExit(
                f'assets[{i}] "{desc}": box_2d values must be within 0-1000'
            )
        parsed.append(
            {
                "description": desc,
                "box_2d": [ymin, xmin, ymax, xmax],
                "want_alpha": bool(item.get("want_alpha", True)),
            }
        )
    return parsed, texts, skeleton


# --- geometry: pixelize + cluster (ported from layout_plan.py) -----------

def pixelize(assets: List[Dict[str, Any]],
             img_w: int, img_h: int) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for i, a in enumerate(assets):
        ymin, xmin, ymax, xmax = a["box_2d"]
        ymax_c, xmax_c = max(ymax, ymin + 1), max(xmax, xmin + 1)
        x = max(0, round(xmin / 1000 * img_w))
        y = max(0, round(ymin / 1000 * img_h))
        w = min(img_w - x, max(1, round((xmax_c - xmin) / 1000 * img_w)))
        h = min(img_h - y, max(1, round((ymax_c - ymin) / 1000 * img_h)))
        items.append(
            {
                "index": i,
                "description": a["description"],
                "want_alpha": a["want_alpha"],
                "x": x, "y": y, "w": w, "h": h,
                "cx": x + w // 2, "cy": y + h // 2,
            }
        )
    return items


def cluster_rows(items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Group items whose vertical spans mostly overlap into shared rows."""
    rows: List[List[Dict[str, Any]]] = []
    spans: List[Tuple[int, int]] = []
    for item in sorted(items, key=lambda p: p["y"]):
        y0, y1 = item["y"], item["y"] + item["h"]
        for i, (ry0, ry1) in enumerate(spans):
            overlap = min(ry1, y1) - max(ry0, y0)
            if overlap > 0.5 * min(item["h"], ry1 - ry0):
                rows[i].append(item)
                spans[i] = (min(ry0, y0), max(ry1, y1))
                break
        else:
            rows.append([item])
            spans.append((y0, y1))
    return [sorted(row, key=lambda p: p["cx"]) for row in rows]


def row_kind(row: List[Dict[str, Any]], img_h: int, img_w: int) -> str:
    center_y = sum(p["cy"] for p in row) / len(row)
    x_span = max(p["x"] + p["w"] for p in row) - min(p["x"] for p in row)
    if center_y >= BOTTOM_BAR_Y_FRACTION * img_h:
        return "bottom"
    if center_y <= TOP_BAR_Y_FRACTION * img_h:
        return "top"
    if len(row) >= 2 and x_span >= FULL_ROW_X_FRACTION * img_w:
        return "full-row"
    return "row"


def pitch_note(centers: List[int]) -> str:
    diffs = [b - a for a, b in zip(centers, centers[1:])]
    if diffs and len(set(diffs)) <= max(2, len(diffs) // 2):
        return f", even pitch ~{sum(diffs) // len(diffs)}px"
    return ""


def format_row(row: List[Dict[str, Any]], kind: str) -> List[str]:
    img_w, img_h = row[0].get("_img_w", 0), row[0].get("_img_h", 0)
    center_y = round(sum(p["cy"] for p in row) / len(row))
    pct = f"{center_y / img_h:.0%}" if img_h else "?"
    if kind == "bottom":
        head = (
            f"- ROW @ y-center {center_y}/{img_h} ({pct}) — BOTTOM BAR: "
            "position:absolute; bottom:0 anchored to the BODY CANVAS "
            "bottom (this page is a fixed non-scrolling canvas). "
            "position:fixed anchors to the VIEWPORT, not the body — on a "
            "wide/RTL viewport the bar tears away from the canvas (body "
            "sits right, bar stays left). NEVER viewport-fixed on a "
            "canvas-contract page; never an in-flow row."
        )
    elif kind == "top":
        head = f"- ROW @ y-center {center_y}/{img_h} ({pct}) — top/status-bar strip."
    elif kind == "full-row":
        head = f"- ROW @ y-center {center_y}/{img_h} ({pct}) — full-width horizontal strip."
    else:
        head = f"- ROW @ y-center {center_y}/{img_h} ({pct})."
    lines = [head]
    centers = [p["cx"] for p in row]
    sizes = ", ".join(f"{p['w']}x{p['h']}" for p in row)
    ys = [p["cy"] for p in row]
    centered = (max(ys) - min(ys)) <= 6
    row_line = (
        f"  {len(row)} asset(s) left->right at x-centers "
        f"{', '.join(map(str, centers))}{pitch_note(centers)}; sizes {sizes}."
    )
    if centered:
        row_line += (" Items are vertically centered — build this row as "
                     "a flex line with align-items:center, not as "
                     "positioned boxes.")
    lines.append(row_line)
    for p in row:
        hints: List[str] = []
        m = p.get("_measure") or {}
        if m.get("css_native"):
            hints.append(
                "css-native: <=3 flat colors, small box — REBUILD in "
                "CSS/SVG, do NOT crop as bitmap")
        if m.get("radius_px"):
            hints.append(
                f"rounded-rect subject radius≈{m['radius_px']}px — the "
                "<img> MUST get CSS border-radius+overflow:hidden of "
                "this radius, or the crop's square corners (baked-in "
                "background) show as soon as the page background "
                "differs from the source")
        if m.get("suggest_alpha") and not m.get("css_native"):
            hints.append(
                "subject floats on a uniform background — prefer "
                "want_alpha=true (raw crop will show seams)")
        if p.get("over_photo_blocks"):
            # over_photo（2026-10-08 重影根因修复）：图内文字已擦，
            # 遮罩仍在图里——写码端禁再画遮罩层（brief 是写码唯一
            # 依据，这个提示必须在这里，layout.json 不够）
            hints.append(
                "over_photo: baked-in text REMOVED from this crop; "
                "render the text layer (" +
                ", ".join(p["over_photo_blocks"]) +
                ") directly ON the image and do NOT add any overlay/"
                "mask/blur div — the mask is already in the pixels")
        tail = ("  [" + "; ".join(hints) + "]") if hints else ""
        lines.append(
            f"   - {p['description']} ({p['w']}x{p['h']} @ x={p['x']},y={p['y']}){tail}"
        )
    return lines


def format_columns(items: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    ordered = sorted(items, key=lambda p: p["cx"])
    columns: List[List[Dict[str, Any]]] = []
    for item in ordered:
        if columns:
            # Compare against the running column center, not its last
            # member — chained greedy drift lets a column wander.
            column = columns[-1]
            center = sum(p["cx"] for p in column) / len(column)
            if item["cx"] - center < COLUMN_X_FRACTION * item["_img_w"]:
                column.append(item)
                continue
        columns.append([item])
    for column in columns:
        if len(column) < 2:
            continue
        center_x = round(sum(p["cx"] for p in column) / len(column))
        y_centers = sorted(p["cy"] for p in column)
        if center_x <= 0.25 * column[0]["_img_w"]:
            side = "left rail"
        elif center_x >= 0.75 * column[0]["_img_w"]:
            side = "right rail"
        else:
            side = "center column"
        lines.append(
            f"- COLUMN @ x-center {center_x} ({side}): {len(column)} assets "
            f"at y-centers {', '.join(map(str, y_centers))}"
            f"{pitch_note(y_centers)} — "
            f"{'; '.join(p['description'] for p in column)}."
        )
    return lines


def dominant_colors(rgb_img: Image.Image, box: Tuple[int, int, int, int],
                    n: int = 3) -> List[Dict[str, Any]]:
    """Top-n quantized colors of a region as [{'hex','share'}, ...].
    Deterministic (median-cut on a downsampled region); used to fill the
    per-row palette lines in the brief so code-writing doesn't guess hex
    values by eye."""
    x, y, w, h = box
    region = rgb_img.crop((x, y, x + w, y + h))
    region.thumbnail((160, 160))
    q = region.quantize(colors=n, method=Image.MEDIANCUT)
    palette = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    out: List[Dict[str, Any]] = []
    for count, idx in counts[:n]:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        out.append({"hex": f"#{r:02X}{g:02X}{b:02X}",
                    "share": round(count / total, 2)})
    return out


def format_palette(colors: List[Dict[str, Any]]) -> str:
    return ", ".join(f"{c['hex']} {c['share']:.0%}" for c in colors)


def build_layout(items: List[Dict[str, Any]], img_w: int,
                 img_h: int, rgb_img: Optional[Image.Image] = None,
                 texts: Optional[List[str]] = None,
                 skeleton: Optional[List[Dict[str, Any]]] = None,
                 dpr: float = 1.0,
                 ) -> Tuple[str, Dict[str, Any]]:
    for p in items:
        p["_img_w"], p["_img_h"] = img_w, img_h
    portrait = img_h >= PORTRAIT_ASPECT_THRESHOLD * img_w
    rows = cluster_rows(items)
    kinds = [row_kind(row, img_h, img_w) for row in rows]

    brief: List[str] = [
        "LAYOUT BRIEF — ground-truth pixel geometry derived from labeled "
        "boxes. Use these numbers when placing assets and structuring the "
        "page; do NOT estimate positions or sizes from memory. Keep "
        "positions within ±5px, honor the reported sizes, pitches, and "
        "bottom-bar flags.",
        "COORDINATES ARE LTR SCREEN-SPACE: x grows left->right in the "
        "source screenshot. If the page is RTL (dir=rtl), do NOT mirror "
        "these values — map left/right explicitly from the numbers.",
        f"Source image: {img_w}x{img_h}px (normalized by dpr), "
        f"{len(items)} located assets.",
        "UNITS — CRITICAL: the source was normalized by its detected "
        "dpr at pipeline entrance. EVERY number in this brief (x/y/w/h, "
        "radius, gap, font estimates) is a LOGICAL px = CSS px, 1:1 — "
        "NO scaling, NO exceptions, radius included. (Legacy ÷2 rule "
        "is obsolete: normalization already happened upstream.)",
    ]
    if texts:
        brief.append(
            "TEXTS (verbatim UI copy — every string below must appear in "
            "the page exactly as written; verify_page.py asserts this):"
        )
        brief.extend(f'  - "{t}"' for t in texts)
    if portrait:
        if img_h >= 2.2 * img_w:
            # F: LONG-PAGE mode — the screenshot is a multi-viewport
            # scroll page. Forcing the single-screen "never grow"
            # contract on it produced a page that could not scroll
            # (field failure 2026-09-30: 621x3720 mini-app long page).
            # Geometry contract stays the same; scrolling is allowed.
            brief.append(
                f"LONG-PAGE CANVAS CONTRACT: total canvas is {img_w}x"
                f"{img_h}px (multi-viewport scroll page). Lay content out "
                f"1:1 on this canvas top-to-bottom; the page MAY scroll "
                f"vertically (body overflow-y visible, width still fixed "
                f"at {img_w}px). Geometry assertions still run against "
                "this canvas coordinate system."
            )
        else:
            brief.append(
                f"CANVAS CONTRACT: this is ONE FIXED APP SCREEN of {img_w}x{img_h}px. "
                "Build a single non-scrolling canvas — the shell is exactly "
                f"{img_w}px wide and {img_h}px tall (100dvh); the page must NEVER "
                "grow taller than the canvas. No min-h-screen sizing; overflow clips."
            )

    row_palettes: List[List[Dict[str, Any]]] = []
    row_samples: List[Dict[str, Any]] = []
    for row, kind in zip(rows, kinds):
        brief.extend(format_row(row, kind))
        if rgb_img is not None:
            band_top = max(0, min(p["y"] for p in row))
            band_bottom = min(img_h, max(p["y"] + p["h"] for p in row))
            palette = dominant_colors(
                rgb_img, (0, band_top, img_w, max(1, band_bottom - band_top))
            )
            row_palettes.append(palette)
            brief.append(f"  palette: {format_palette(palette)}")
            # SAMPLES: measured hex at fixed probe points — the coding
            # step must take colors from here, not estimate by eye. Row
            # probes catch full-width fills (buttons, cards, backgrounds);
            # per-asset probes catch the asset's own fill.
            band_cy = (band_top + band_bottom) // 2
            row_probes = [
                _sample_hex(rgb_img, round(img_w * f), band_cy)
                for f in (0.10, 0.50, 0.90)
            ]
            brief.append(
                "  row-samples: " + "  ".join(
                    f"x{f:.0%}={h}" for f, h in zip((0.10, 0.50, 0.90),
                                                    row_probes)
                )
            )
            asset_samples = []
            for p in row:
                probes = [
                    _sample_hex(rgb_img, p["x"] + round(p["w"] * f),
                                p["y"] + p["h"] // 2)
                    for f in (0.20, 0.50, 0.80)
                ]
                asset_samples.append(probes)
                brief.append(
                    f"    sample[{p['description'][:16]}]: "
                    + "  ".join(probes)
                )
            row_samples.append({"row_probes": row_probes,
                                "asset_probes": asset_samples})
        else:
            row_palettes.append([])
            row_samples.append({})
    column_lines = format_columns(items)
    if column_lines:
        brief.append("Vertical columns (assets that align across rows):")
        brief.extend(column_lines)

    containers: List[Dict[str, Any]] = []
    refined_skeleton: List[Dict[str, Any]] = []
    if rgb_img is not None:
        containers = detect_containers(rgb_img, rows, items, img_w, img_h)
        if containers:
            brief.append(
                "CONTAINERS (auto-detected solid blocks — buttons/pills/"
                "cards; build each with EXACTLY these numbers and tag the "
                "element data-container=\"cN\"; ALL numbers below are "
                "LOGICAL px (1:1 with CSS — the source was normalized "
                "by detected dpr; NEVER divide again), radius "
                "included):"
            )
            for c in containers:
                r = c["radius"]
                shape = ("pill (use border-radius = h/2)"
                         if r >= 0.42 * c["h"]
                         else "rounded-rect (use border-radius ≈ r, "
                         "NOT h/2)")
                ext = (" [auto-ext — gap-band detection, calibration "
                       "must pixel-verify this box]"
                       if c.get("source") == "auto-ext" else "")
                brief.append(
                    f"  - c{c['index']} (row {c['row']}) @ x={c['x']},"
                    f"y={c['y']} {c['w']}x{c['h']}px "
                    f"radius≈{r}px shape: {shape}{ext}"
                    f"  samples: {' '.join(c['samples'])}"
                )
                # Q5 gradient endpoint fit — sample the container along
                # its long axis; if the samples are monotone-ish, emit a
                # ready-to-use CSS gradient so the agent never eyeballs
                # gradient endpoints (field failure: banner gradient
                # direction eyeballed without a spec).
                if rgb_img is not None and c["w"] >= 40 and c["h"] >= 24:
                    try:
                        _grad = _fit_container_gradient(
                            rgb_img, c)
                        if _grad:
                            c["gradient"] = _grad
                            brief.append(
                                f"    gradient fit: {_grad['css']}"
                                f"  (note: {_grad.get('fit_note', '')})"
                            )
                    except Exception:
                        pass
        else:
            brief.append(
                "CONTAINERS: none auto-detected in this layout (pale or "
                "low-contrast blocks are out of v1 detector scope — "
                "measure those manually before coding)."
            )
        # SKELETON: structural elements (cards, text blocks, bars) — the
        # same measured-geometry contract as assets. Build them with
        # flex/grid so relative alignment is enforced by the layout
        # engine; NEVER hard-position text with margins.
        refined_skeleton = refine_skeleton(skeleton or [], containers,
                                           rgb_img, img_w, img_h)
        if refined_skeleton:
            brief.append(
                "SKELETON (structural elements, agent-labeled then "
                "pixel-refined — same measured-geometry contract as "
                "assets; tag each element data-skeleton=\"sN\"; build "
                "alignment with flex/grid, never margins; ALL numbers "
                "LOGICAL px (1:1 with CSS — NEVER divide again)):"
            )
            for s in refined_skeleton:
                tag = (f"s{s['index']} {s['type']}"
                       + (f" \"{s['text'][:24]}\"" if s.get("text") else ""))
                meta = "[program-verified]" if s["source"] == "program" \
                    else "[model-only — REVIEW]"
                if s.get("edge_extended"):
                    meta += (" [edge-extended: box grew over a gradient "
                             "fade — verify the new bounds cover the "
                             "FULL structure (e.g. an embedded ticker "
                             "row)]")
                brief.append(
                    f"  - {tag} @ x={s['x']},y={s['y']} {s['w']}x{s['h']}px"
                    f" {meta}"
                )
                if s["type"] == "text_block" and s.get("ink_lines"):
                    lines = max(1, s["ink_lines"])
                    est_font = s["h"] / (lines * 1.30)
                    thick = s.get("stroke_thick", 0.0)
                    ratio = thick / max(1.0, est_font)
                    weight = (900 if ratio >= 0.20 else
                              700 if ratio >= 0.15 else
                              600 if ratio >= 0.11 else 400)
                    txt = s.get("text") or ""
                    nsp = sum(1 for ch in txt if not ch.isspace())
                    nsp_total = len(txt)
                    est_w = (est_font / 2 * 0.56 * nsp
                             + est_font / 2 * 0.25
                             * (nsp_total - nsp))
                    box_w_css = s["w"]
                    risk = ""
                    if est_w > box_w_css * 1.08:
                        risk = (
                            f" [WIDTH-RISK: Cairo est ≈{est_w:.0f}css > "
                            f"box {box_w_css:.0f}css — reserve width or "
                            f"shrink font; NEVER negative-margin]"
                        )
                    brief.append(
                        f"      font hint: ≈{lines} line(s), est "
                        f"font-size ≈{est_font:.0f}px, est "
                        f"font-weight ≈{weight}, ink width est "
                        f"≈{est_w:.0f}css{risk}"
                    )
            uncovered = [
                c["index"] for c in containers
                if not any(
                    _iou_box((s["x"], s["y"], s["w"], s["h"]),
                             (c["x"], c["y"], c["w"], c["h"])) > 0.5
                    for s in refined_skeleton
                    if s["type"] in ("container", "button_bar", "nav_bar"))
            ]
            if uncovered:
                brief.append(
                    f"  - program-detected container(s) not in skeleton: "
                    f"c{', c'.join(map(str, uncovered))} — measure and "
                    "build from their CONTAINERS numbers."
                )
        else:
            brief.append(
                "SKELETON: none labeled for this layout — containers/"
                "text blocks may be measured manually before coding "
                "(detection failure must not block generation)."
            )

    bottom_gap: Optional[int] = None
    for s in refined_skeleton:
        if s["type"] == "nav_bar":
            bottom_gap = img_h - (s["y"] + s["h"])
            break
    if bottom_gap is None:
        for row, kind in zip(rows, kinds):
            if kind == "bottom":
                bottom_gap = img_h - max(p["y"] + p["h"] for p in row)
                break

    layout: Dict[str, Any] = {
        "image": {"width": img_w, "height": img_h, "portrait": portrait},
        "dpr": dpr,
        "long_page": bool(portrait and img_h >= 2.2 * img_w),
        "canvas_contract": {"w": img_w, "h": img_h} if portrait else None,
        "has_bottom_bar": any(k == "bottom" for k in kinds),
        "bottom_bar_gap_px": max(0, int(bottom_gap)) if bottom_gap is not None else 0,
        "expected_texts": list(texts or []),
        "containers": containers,
        "skeleton": refined_skeleton,
        "rows": [
            {
                "kind": kind,
                "y_center": round(sum(p["cy"] for p in row) / len(row)),
                "palette": palette,
                "samples": samples,
                "assets": [
                    {"description": p["description"], "x": p["x"],
                     "y": p["y"], "w": p["w"], "h": p["h"],
                     **({"over_photo_text_erased": True,
                         "note": "baked-in text REMOVED from this crop; "
                         "render the text layer directly on the image "
                         "and do NOT add any overlay/mask div — the "
                         "mask is already in the pixels"}
                        if p.get("over_photo_blocks") else {})}
                    for p in row
                ],
            }
            for row, kind, palette, samples in zip(rows, kinds, row_palettes,
                                                   row_samples)
        ],
    }
    return "\n".join(brief), layout


# --- main pipeline --------------------------------------------------------

def _mask_score(alpha_img: Image.Image) -> Tuple[float, Dict[str, float]]:
    """Deterministic quality score for one candidate mask (lower=better).

    edge_fg : foreground share in the 4px border band — a clean cut clears
              the background right up to the edge, so lower is better.
    center_void : transparent share in the central 50% area — UI icons are
              center-weighted, so holes there mean the model ate the
              subject (the 'hollowed logo' failure).
    """
    import numpy as np

    a = np.asarray(alpha_img)[..., 3]
    h, w = a.shape
    band = 4
    border = np.ones_like(a, dtype=bool)
    border[band:h-band, band:w-band] = False
    edge_fg = float((a[border] > 127).mean())
    cy0, cy1 = h // 4, h - h // 4
    cx0, cx1 = w // 4, w - w // 4
    center = a[cy0:cy1, cx0:cx1]
    fg_overall = float((a > 127).mean())
    if fg_overall < 0.02:
        center_void = 1.0
    else:
        center_void = float((center < 128).mean())
    score = edge_fg * 0.5 + center_void * 0.5
    return score, {"edge_fg": round(edge_fg, 3),
                   "center_void": round(center_void, 3)}


def remove_bg_best(crop: Image.Image, removers: List[Tuple[str, BgRemover]],
                   alpha_threshold: int, keep_largest: bool,
                   erode_px: int, dilate_px: int) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
    """Run every available model, score the masks, keep the winner.
    Returns (alpha_image_or_None, info). Every entrant that fails —
    inference error, no-signal mask (entry-stage defect), or bad-mask
    guard — is recorded in info["rejected"] so the race is auditable.

    Q4 content-hash cache: identical crops (same icon across paired
    pages, reruns) reuse the previous mask — same input, same output,
    half the inference time on multi-page projects. Cache dir:
    $I2C_ALPHA_CACHE or <cwd>/.i2c-cache/alpha. Gate decisions are NOT
    cached (cheap to recompute per box)."""
    import numpy as np

    cache_dir: Optional[Path] = None
    raw_env = os.environ.get("I2C_ALPHA_CACHE")
    if raw_env != "":
        cache_dir = (Path(raw_env) if raw_env else
                     Path.cwd() / ".i2c-cache" / "alpha")
    try:
        crop_key = hashlib.md5(
            crop.tobytes() + bytes([alpha_threshold,
                                    keep_largest and 1 or 0,
                                    erode_px, dilate_px])).hexdigest()
    except Exception:
        crop_key = None
    if crop_key and cache_dir is not None:
        hit = cache_dir / f"{crop_key}.png"
        if hit.is_file():
            try:
                cached = Image.open(hit)
                cached.load()
                return cached, {"winner": "cache", "scores": {},
                                "tried": ["cache"], "cached": True}
            except Exception:
                pass  # corrupt cache entry — recompute

    candidates: List[Tuple[str, Image.Image, Dict[str, float]]] = []
    rejected: List[Dict[str, Any]] = []
    for name, remover in removers:
        try:
            alpha_img = remover.remove_background(
                crop, alpha_threshold=alpha_threshold,
                keep_largest=keep_largest, erode_px=erode_px,
                dilate_px=dilate_px,
            )
        except Exception as exc:  # noqa: BLE001 — a broken model loses the round
            rejected.append({"model": name, "reason": f"inference error: {exc}"})
            continue
        # Entry health check: a flat raw prediction range means the model
        # produced NO signal at all (preprocess/profile mismatch) — an
        # entry-stage defect, reported separately from a low-foreground
        # mask, which is the guard's call.
        rmin, rmax = getattr(remover, "last_signal", (0.0, 0.0))
        if rmax - rmin < 1e-6:
            rejected.append({"model": name,
                             "reason": "no-signal mask (entry mismatch?)"})
            continue
        fg_ratio = float((np.asarray(alpha_img)[..., 3] > 127).mean())
        if fg_ratio < 0.12 or fg_ratio > 0.995:
            rejected.append({"model": name, "fg_ratio": round(fg_ratio, 3),
                             "reason": "bad-mask guard (fg out of range)"})
            continue  # bad-mask guard (hollowed / no-cut)
        score, parts = _mask_score(alpha_img)
        candidates.append((name, alpha_img, {**parts, "fg": round(fg_ratio, 3)}))
    if not candidates:
        return None, {"reason": "all entrants failed",
                      "rejected": rejected}
    candidates.sort(key=lambda c: c[2].get("edge_fg", 1) * 0.5
                    + c[2].get("center_void", 1) * 0.5)
    winner_name, winner_img, winner_parts = candidates[0]
    info = {"winner": winner_name, "scores": winner_parts,
            "tried": [c[0] for c in candidates]}
    if rejected:
        info["rejected"] = rejected
    if len(candidates) > 1:
        info["loser"] = {"model": candidates[1][0],
                         "scores": candidates[1][2]}
        gap = abs((winner_parts["edge_fg"] * 0.5 + winner_parts["center_void"] * 0.5)
                  - (candidates[1][2]["edge_fg"] * 0.5
                     + candidates[1][2]["center_void"] * 0.5))
        info["margin"] = round(gap, 3)
    if crop_key and cache_dir is not None:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            winner_img.save(cache_dir / f"{crop_key}.png", format="PNG")
        except Exception:
            pass
    return winner_img, info


def build_check_sheet(report: List[Dict[str, Any]], out_dir: Path) -> None:
    """Grid contact sheet: every asset's raw crop, or alpha on dark+light
    halves, so the agent can visually audit labels and mask quality in one
    Read. The calibration loop runs on this image: mis-framed box -> fix
    assets.json coords; hollowed mask -> fall back to raw crop."""
    from PIL import ImageDraw, ImageFont

    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    except Exception:
        font = ImageFont.load_default()
    cell_w, cell_h, label_h, cols = 220, 150, 22, 3
    rows = (len(report) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)),
                      "#DDDDDD")
    draw = ImageDraw.Draw(sheet)

    def _resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else (out_dir / pp)

    for i, e in enumerate(report):
        cx, cy = (i % cols) * cell_w, (i // cols) * (cell_h + label_h)
        tag = f"#{e['index']} {str(e['description'])[:13]}"
        if e.get("alpha"):
            a = Image.open(_resolve(e["alpha"])).convert("RGBA")
            a.thumbnail((cell_w - 20, cell_h - 20))
            for half, bg in ((0, "#333333"), (1, "#F0F0F0")):
                base = Image.new("RGBA", (cell_w // 2, cell_h), bg)
                base.paste(a, ((cell_w // 2 - a.width) // 2,
                               (cell_h - a.height) // 2), a)
                sheet.paste(base.convert("RGB"),
                            (cx + half * (cell_w // 2), cy + label_h))
        else:
            c = Image.open(_resolve(e["crop"])).convert("RGB")
            c.thumbnail((cell_w - 20, cell_h - 20))
            sheet.paste(c, (cx + (cell_w - c.width) // 2,
                            cy + label_h + (cell_h - c.height) // 2))
            tag += " [RAW]"
        draw.text((cx + 6, cy + 4), tag, fill="#000000", font=font)
    out = out_dir / "_check_sheet.png"
    sheet.save(out)
    print(f"check sheet: {out}")


def build_check_sheet_detail(report: List[Dict[str, Any]], out_dir: Path,
                             rgb_img: Optional[Image.Image],
                             containers: Optional[List[Dict[str, Any]]] = None,
                             skeleton: Optional[List[Dict[str, Any]]] = None,
                             ) -> List[str]:
    """Per-asset rows at inspection resolution — THE calibration surface.

    The grid contact sheet hides small-asset defects (a 4px flat cut, a
    subject occupying a corner of its box) below visible scale; each row
    shows: source context with the labeled (yellow) vs final (red) box,
    the alpha at up to 4x on dark+light halves, and a status line
    (auto-fixes, fill ratio, suspects). Rows marked REVIEW carry an
    auto-detected box/mask issue and must be individually confirmed or
    re-labeled before coding starts. Auto-detected containers (buttons /
    pills) get their own rows: confirm the red box IS that button and
    the fitted radius looks right before trusting CONTAINERS numbers.

    2026-10: rows are split across sheets of <=12 rows (~1.5MB each).
    A single giant sheet is unreadable in one Read and forced the agent
    into a crop-and-reread hop; the split removes that round-trip.
    Returns the list of sheet paths."""
    from PIL import ImageDraw, ImageFont

    try:
        font = ImageFont.truetype(r"C:\\Windows\\Fonts\\msyh.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    def _resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else (out_dir / pp)

    ctx_w, al_w, box_h, row_h, pad = 320, 300, 100, 108, 6
    header_h = 30
    txt_w = 380
    sheet_w = ctx_w + al_w + txt_w + 3 * pad
    per_sheet = 12

    def _new_sheet(part: int, n_parts: int):
        img = Image.new("RGB", (sheet_w,
                                header_h + row_h * per_sheet + pad),
                        "#FFFFFF")
        d = ImageDraw.Draw(img)
        d.text((pad, 8),
               f"CALIBRATION DETAIL (part {part}/{n_parts}) - "
               "yellow=labeled box, red=final box; REVIEW rows carry an "
               "auto-detected box/mask issue",
               fill="#333333", font=font)
        return img, d

    def _new_row():
        return Image.new("RGB", (sheet_w, row_h + 8), "#FFFFFF")

    # ---- build all row images first (assets, containers, skeleton) ----
    rows: List[Image.Image] = []
    n_review = 0
    for e in report:
        pick = e.get("alpha_pick") or {}
        cal = e.get("calibration") or {}
        review = bool(cal.get("needs_review"))
        n_review += int(review)
        fb = e["box_px"]
        row = _new_row()
        if rgb_img is not None:
            lb = cal.get("labeled_box") or fb
            m = max(12, round(max(fb["w"], fb["h"]) * 0.4))
            cx0 = max(0, fb["x"] - m)
            cy0 = max(0, fb["y"] - m)
            cx1 = min(rgb_img.width, fb["x"] + fb["w"] + m)
            cy1 = min(rgb_img.height, fb["y"] + fb["h"] + m)
            ctx = rgb_img.crop((cx0, cy0, cx1, cy1)).copy()
            scale = min(ctx_w / ctx.width, box_h / ctx.height)
            ctx = ctx.resize((max(1, round(ctx.width * scale)),
                              max(1, round(ctx.height * scale))))

            def _map(b: Dict[str, Any]) -> Tuple[float, float, float, float]:
                return ((b["x"] - cx0) * scale, (b["y"] - cy0) * scale,
                        (b["x"] + b["w"] - cx0) * scale,
                        (b["y"] + b["h"] - cy0) * scale)

            d2 = ImageDraw.Draw(ctx)
            d2.rectangle(_map(lb), outline="#E0A800", width=2)
            d2.rectangle(_map(fb), outline="#E02020", width=2)
            row.paste(ctx, (pad, 4))
        if e.get("alpha"):
            a = Image.open(_resolve(e["alpha"])).convert("RGBA")
            scale = min(((al_w - 12) / 2) / a.width, (box_h - 8) / a.height,
                        4.0)
            a2 = a.resize((max(1, round(a.width * scale)),
                           max(1, round(a.height * scale))), Image.LANCZOS)
            for half, bg in ((0, "#333333"), (1, "#F0F0F0")):
                base = Image.new("RGBA", (al_w // 2, box_h), bg)
                base.paste(a2, ((al_w // 2 - a2.width) // 2,
                                (box_h - a2.height) // 2), a2)
                row.paste(base.convert("RGB"),
                          (ctx_w + pad + half * (al_w // 2), 4))
        else:
            c = Image.open(_resolve(e["crop"])).convert("RGB")
            c.thumbnail((al_w - 12, box_h - 8))
            row.paste(c, (ctx_w + pad + (al_w - c.width) // 2,
                          4 + (box_h - c.height) // 2))
        tx = ctx_w + al_w + 2 * pad
        fill = pick.get("fill")
        notes = []
        if pick.get("clipped_box_resolved"):
            notes.append("BOX-CLIPPED auto-expanded")
        if pick.get("loose_box_tightened"):
            notes.append("BOX-LOOSE auto-tightened")
        if pick.get("suspect") == "low_score":
            notes.append("LOW MASK SCORE")
        if pick.get("suspect") == "alpha_coverage":
            notes.append("ALPHA COVERAGE")
        if pick.get("variant"):
            notes.append(f"frame variant {pick['variant']}")
        fr = e.get("measure", {}).get("fidelity_ratio")
        if fr is not None:
            notes.append(f"fidelity={fr}")
        rd = ImageDraw.Draw(row)
        lines = [
            (f"#{e['index']} {e['description'][:24]}",
             "#B00020" if review else "#000000"),
            (f"box {fb['w']}x{fb['h']}@({fb['x']},{fb['y']})  "
             f"fill={fill:.2f}" if fill is not None
             else f"box {fb['w']}x{fb['h']}@({fb['x']},{fb['y']})  [RAW]",
             "#333333"),
            ("REVIEW: " + "; ".join(notes) if review else "ok",
             "#B00020" if review else "#1A7F37"),
        ]
        ty = 4
        for text, color in lines:
            rd.text((tx, ty), text, fill=color, font=font)
            ty += 22
        rows.append(row)
    for c in (containers or []):
        row = _new_row()
        if rgb_img is not None:
            m = max(12, round(max(c["w"], c["h"]) * 0.3))
            cx0 = max(0, c["x"] - m)
            cy0 = max(0, c["y"] - m)
            cx1 = min(rgb_img.width, c["x"] + c["w"] + m)
            cy1 = min(rgb_img.height, c["y"] + c["h"] + m)
            img_ctx = rgb_img.crop((cx0, cy0, cx1, cy1)).copy()
            scale = min(ctx_w / img_ctx.width, box_h / img_ctx.height)
            img_ctx = img_ctx.resize(
                (max(1, round(img_ctx.width * scale)),
                 max(1, round(img_ctx.height * scale))))
            d2 = ImageDraw.Draw(img_ctx)
            d2.rectangle(((c["x"] - cx0) * scale, (c["y"] - cy0) * scale,
                          (c["x"] + c["w"] - cx0) * scale,
                          (c["y"] + c["h"] - cy0) * scale),
                         outline="#E02020", width=3)
            row.paste(img_ctx, (pad, 4))
        for si, hexcol in enumerate(c.get("samples") or []):
            sw = Image.new("RGB", (40, box_h - 8), hexcol)
            row.paste(sw, (ctx_w + pad + si * 46, 4))
        tx = ctx_w + al_w + 2 * pad
        rd = ImageDraw.Draw(row)
        rd.text((tx, 4), f"c{c['index']} CONTAINER (row {c['row']})",
                fill="#B45F06", font=font)
        rd.text((tx, 26), f"box {c['w']}x{c['h']}@({c['x']},{c['y']})",
                fill="#333333", font=font)
        rd.text((tx, 48),
                f"radius~{c['radius']}px  samples: "
                f"{' '.join(c.get('samples') or [])}",
                fill="#333333", font=font)
        rd.text((tx, 70), "confirm: is the red box this button/pill?",
                fill="#666666", font=font)
        rows.append(row)
    for s in (skeleton or []):
        row = _new_row()
        if rgb_img is not None:
            m = max(12, round(max(s["w"], s["h"]) * 0.3))
            cx0 = max(0, s["x"] - m)
            cy0 = max(0, s["y"] - m)
            cx1 = min(rgb_img.width, s["x"] + s["w"] + m)
            cy1 = min(rgb_img.height, s["y"] + s["h"] + m)
            img_ctx = rgb_img.crop((cx0, cy0, cx1, cy1)).copy()
            scale = min(ctx_w / img_ctx.width, box_h / img_ctx.height)
            img_ctx = img_ctx.resize(
                (max(1, round(img_ctx.width * scale)),
                 max(1, round(img_ctx.height * scale))))
            d2 = ImageDraw.Draw(img_ctx)
            d2.rectangle(((s["x"] - cx0) * scale, (s["y"] - cy0) * scale,
                          (s["x"] + s["w"] - cx0) * scale,
                          (s["y"] + s["h"] - cy0) * scale),
                         outline="#E02020", width=2)
            row.paste(img_ctx, (pad, 4))
        tx = ctx_w + al_w + 2 * pad
        review = bool(s.get("review"))
        color = "#B00020" if review else "#000000"
        rd = ImageDraw.Draw(row)
        label = s.get("text", "")[:20]
        rd.text((tx, 4),
                f"s{s['index']} {s['type']} "
                + (f'"{label}"' if s.get("text") else ""),
                fill=color, font=font)
        rd.text((tx, 26),
                f"box {s['w']}x{s['h']}@({s['x']},{s['y']}) "
                f"[{s['source']}]",
                fill="#333333", font=font)
        rd.text((tx, 48),
                "REVIEW: model-only box, unverified" if review
                else "ok - pixel-verified",
                fill="#B00020" if review else "#1A7F37", font=font)
        rows.append(row)

    # ---- split rows across sheets of <= per_sheet rows ----
    n_parts = max(1, -(-len(rows) // per_sheet))
    paths: List[str] = []
    for part in range(n_parts):
        chunk = rows[part * per_sheet:(part + 1) * per_sheet]
        img, d = _new_sheet(part + 1, n_parts)
        y = header_h
        for r in chunk:
            img.paste(r, (0, y))
            y += row_h
        d.text((pad, header_h + row_h * len(chunk) + 4),
               f"{len(report)} assets, {n_review} need review, "
               f"{len(containers or [])} containers, "
               f"{len(skeleton or [])} skeleton items",
               fill="#333333", font=font)
        suffix = f"_{part + 1}" if n_parts > 1 else ""
        out = out_dir / f"_check_sheet_detail{suffix}.png"
        img.save(out)
        paths.append(str(out))
    print(f"check sheet detail: {n_parts} sheet(s) "
          f"({n_review} rows need review)")
    return paths


def _pick_score(pick: Dict[str, Any]) -> float:
    """Scalar score of a winning mask (lower=better), same weights as
    remove_bg_best."""
    s = pick.get("scores", {})
    return s.get("edge_fg", 1) * 0.5 + s.get("center_void", 1) * 0.5


def _tight_bbox(alpha_img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Tight bbox (l, t, r, b) of foreground in a crop-frame alpha image."""
    import numpy as np

    a = np.asarray(alpha_img)[..., 3]
    ys, xs = np.where(a > 127)
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()),
            int(xs.max()) + 1, int(ys.max()) + 1)


def _touches_border(alpha_img: Image.Image, band: int = 2,
                    frac: float = 0.02) -> bool:
    """True when >frac of a border strip's pixels are foreground — the
    subject likely runs past the labeled box and got cut by the crop."""
    import numpy as np

    a = np.asarray(alpha_img)[..., 3]
    h, w = a.shape
    strips = (a[:band, :], a[-band:, :], a[:, :band], a[:, -band:])
    return any((s > 127).mean() > frac for s in strips)


def _sample_hex(rgb_img: Image.Image, x: int, y: int) -> str:
    """Average a 3x3 patch into one hex color (single pixels are noisy
    from antialiasing)."""
    x0, y0 = max(0, x - 1), max(0, y - 1)
    region = rgb_img.crop((x0, y0, x0 + 3, y0 + 3))
    pixels = list(region.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return f"#{r:02X}{g:02X}{b:02X}"


def _iou_box(a: Tuple[int, int, int, int],
             b: Tuple[int, int, int, int]) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter == 0:
        return 0.0
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def _overlap_frac(a: Tuple[int, int, int, int],
                  b: Tuple[int, int, int, int]) -> float:
    """Intersection over a's own area — catches 'detected block is mostly
    inside a labeled asset' (a mid-part of an illustration passes the IoU
    filter but is not a container)."""
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    if a[2] * a[3] == 0:
        return 0.0
    return (ix * iy) / (a[2] * a[3])


def inpaint_text_regions(crop: Image.Image,
                         boxes_px: List[Tuple[int, int, int, int]]) -> int:
    """擦除素材内压字区域的文字像素（2026-10-08 重影根因修复）。

    "照片+半透明遮罩+交互文字"设计模式下，按框从合成截图裁素材会把
    遮罩上的文字像素一并烘焙进去，HTML 再渲染同一文字 → 重影。此处
    对文字框区域跑 cv2 TELEA inpaint——文字脚下是遮罩面（均匀色/
    渐变），邻域扩散填充天然还原为遮罩面。boxes 为相对 crop 的物理
    像素框 (x0, y0, x1, y1)。返回擦除的区域数。"""
    if not boxes_px:
        return 0
    try:
        import cv2  # noqa: F401 — doctor 体检项，缺失在第 0 步拦截
    except Exception as exc:
        raise SystemExit(
            f"opencv (cv2) unavailable: {exc} — over_photo text erase "
            "requires it; pip install opencv-python-headless")
    import numpy as _np
    arr = _np.asarray(crop.convert("RGB"))[:, :, ::-1].copy()  # RGB→BGR
    mask = _np.zeros(arr.shape[:2], dtype=_np.uint8)
    W, H = crop.size
    n_applied = 0
    for (x0, y0, x1, y1) in boxes_px:
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        mask[y0:y1, x0:x1] = 255
        n_applied += 1
    # 底板分级路由（1009-14 阶段2，三引擎对照实验定案）：渐变底 → NS
    # （线性渐变还原 mean≈0，TELEA 同场景 6.25 发白实锤）；纹理/照片底
    # → TELEA（NS 7.57 vs TELEA 7.30，且保细节）
    engine = (cv2.INPAINT_NS if _base_plate_kind(arr, mask) == "gradient"
              else cv2.INPAINT_TELEA)
    out = cv2.inpaint(arr, mask, 5, engine)
    crop.paste(Image.fromarray(out[:, :, ::-1]))
    return n_applied


def _base_plate_kind(arr: "np.ndarray", mask: "np.ndarray") -> str:
    """底板类型判定（1009-14）：掩码外环带的行间差分符号一致率——
    渐变面沿主轴单调平滑（同号连续），纹理面随机（符号乱）。一致率
    ≥0.8 判 gradient（走 NS），否则 texture（保守走 TELEA）。
    返回 'gradient' | 'texture'。"""
    import numpy as _np
    import cv2  # 1009-15 fix: 调用方函数内局部导入在此作用域不可见
    kernel = _np.ones((17, 17), _np.uint8)
    dil = cv2.dilate(mask, kernel)
    ring = (dil > 0) & (mask == 0)
    if not ring.any():
        return "texture"
    gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1]
            + 0.114 * arr[:, :, 2])
    rows = _np.where(ring.any(axis=1))[0]
    if len(rows) < 4:
        return "texture"
    diffs = _np.diff(gray[rows, :], axis=0)
    row_mean = diffs.mean(axis=1)
    nz = row_mean[_np.abs(row_mean) > 0.5]
    if len(nz) < 3:
        return "texture"
    same = float((_np.sign(nz) == _np.sign(nz[0])).mean())
    return "gradient" if same >= 0.8 else "texture"


def erase_overphoto_for_item(crop: Image.Image,
                             item_box: Dict[str, int],
                             skeleton: Optional[List[Dict[str, Any]]],
                             img_w: int, img_h: int, dpr: float,
                             phys_box: Tuple[int, int, int, int],
                             item: Optional[Dict[str, Any]] = None,
                             other_items: Optional[List[Dict[str, Any]]] = None
                             ) -> Tuple[List[str], int]:
    """over_photo 擦字统一关卡（1009-01）：任何"裁剪/重裁"路径落盘前
    必须经过——主循环裁剪、shrink 重裁、未来新路径。1009 实测：擦字
    挂在主循环一次性执行，被 shrink 后置重裁覆盖（落盘素材文字回来而
    report 谎报已擦）。幂等：对已擦区域重复 inpaint 收敛于遮罩面。
    返回 (over_blocks, n_erased)；item 传入时同步 over_photo_blocks。

    掩码来源两路（1009-13）：①skeleton 相交框；②other_items 中与本
    素材相交的 want_alpha 素材精化框——压图的勋章/金剑类被提取为独立
    透明素材后，底板位图里的残骸必须同步擦除（S2C 实战实证：不擦 =
    贴回双份叠影）。②的分母=候选框自身面积（分母错用底板框会让"小
    勋章压大横幅"算出 ≈2% 而漏判，S2C m4-b 同款洞）。"""
    over_blocks: List[str] = []
    erase_boxes: List[Tuple[int, int, int, int]] = []
    for _s in skeleton or []:
        # 1009-05：任意 skeleton 元素相交即擦（判据式，弃类型枚举）——
        # 实测蓝牙残骸/返回箭头是 css-native 图标不在 text_block 内；
        # 图片内部的设计文字由标注合同豁免（不标 skeleton 即不擦）
        if None in (_s.get("ymin"), _s.get("xmin"),
                    _s.get("ymax"), _s.get("xmax")):
            continue
        # 原始标注（归一化 box_2d）→ 逻辑 px。精化框在 build_layout
        # 才产出（裁剪先于其执行），用原始框 + 外扩 6 逻辑 px 补
        # 标注误差——inpaint 擦遮罩面"略大无害（多糊一块遮罩）、
        # 略小有害（残留文字边缘）"
        _sx = _s["xmin"] / 1000 * img_w - 6.0
        _sy = _s["ymin"] / 1000 * img_h - 6.0
        _sw = (_s["xmax"] - _s["xmin"]) / 1000 * img_w + 12.0
        _sh = (_s["ymax"] - _s["ymin"]) / 1000 * img_h + 12.0
        # 逻辑平面相交判定（交集占文字框 >15% 才算压图——擦边
        # 不值得擦，避免把贴着图片边缘的正常文字误伤）
        ix = max(0, min(item_box["x"] + item_box["w"], _sx + _sw)
                 - max(item_box["x"], _sx))
        iy = max(0, min(item_box["y"] + item_box["h"], _sy + _sh)
                 - max(item_box["y"], _sy))
        if ix * iy <= 0.15 * _sw * _sh:
            continue
        over_blocks.append(f"s{_s['index']}")
        # 交集框 → 物理 → 相对 crop 的偏移框
        _ix0 = max(item_box["x"], _sx)
        _iy0 = max(item_box["y"], _sy)
        _ix1 = min(item_box["x"] + item_box["w"], _sx + _sw)
        _iy1 = min(item_box["y"] + item_box["h"], _sy + _sh)
        erase_boxes.append((
            round(_ix0 * dpr) - phys_box[0],
            round(_iy0 * dpr) - phys_box[1],
            round(_ix1 * dpr) - phys_box[0],
            round(_iy1 * dpr) - phys_box[1]))
    # ②其他 want_alpha 素材精化框（1009-13）：压图勋章/金剑类提取为
    # 独立素材后，底板里的残骸同步擦除——分母=候选框自身面积
    for _o in other_items or []:
        ox, oy, ow, oh = (_o.get("x"), _o.get("y"),
                          _o.get("w"), _o.get("h"))
        if None in (ox, oy, ow, oh) or not ow or not oh:
            continue
        ix = max(0, min(item_box["x"] + item_box["w"], ox + ow)
                 - max(item_box["x"], ox))
        iy = max(0, min(item_box["y"] + item_box["h"], oy + oh)
                 - max(item_box["y"], oy))
        if ix * iy <= 0.15 * ow * oh:
            continue
        over_blocks.append(f"asset_{_o.get('index')}")
        _ix0 = max(item_box["x"], ox)
        _iy0 = max(item_box["y"], oy)
        _ix1 = min(item_box["x"] + item_box["w"], ox + ow)
        _iy1 = min(item_box["y"] + item_box["h"], oy + oh)
        erase_boxes.append((
            round(_ix0 * dpr) - phys_box[0],
            round(_iy0 * dpr) - phys_box[1],
            round(_ix1 * dpr) - phys_box[0],
            round(_iy1 * dpr) - phys_box[1]))
    n_erased = inpaint_text_regions(crop, erase_boxes)
    if item is not None and over_blocks:
        item["over_photo_blocks"] = over_blocks
    return over_blocks, n_erased


def refine_skeleton(skeleton: List[Dict[str, Any]],
                    containers: List[Dict[str, Any]],
                    rgb_img: Optional[Image.Image],
                    img_w: int, img_h: int) -> List[Dict[str, Any]]:
    """Pixel-refine agent skeleton boxes (model coordinates are eyeball
    inputs, never ground truth):
    - surface types: adopt the program-detected box when IoU>0.6 (pixel
      measurement beats eyeballing); model-only boxes get flagged for
      the calibration review AND get a gradient-edge extension probe
      (cards whose fill fades into the page background — e.g. a news
      ticker embedded in a tournament card — are routinely boxed short);
    - text_block: tighten to the ink extent via thresholded row/column
      projection inside the labeled box (guard: keep ≥30% of the box so
      a stray glyph can't collapse it), and record ink stats (line
      count, median stroke thickness) that drive the brief's font-size
      / font-weight / width-risk hints."""
    import numpy as np

    def _extend_fading_edges(arr, x, y, w, h, max_ext=48, thr=14.0):
        """Extend each edge outward while the outside row/column median
        color stays within `thr` of the box's own inner-edge color —
        recovers container bounds that fade into the page background.
        Guard: a side is only accepted when its extended strip contains
        real CONTENT (>=1.5% of pixels differing from the inner-edge
        color by >45) — pure background gradients on small widgets
        (progress bars, docks) otherwise drag the box way off."""
        inner = 4
        ref = {
            "top": np.median(arr[y:y + inner, x:x + w].reshape(-1, 3),
                             axis=0),
            "bottom": np.median(arr[y + h - inner:y + h, x:x + w]
                                .reshape(-1, 3), axis=0),
            "left": np.median(arr[y:y + h, x:x + inner].reshape(-1, 3),
                              axis=0),
            "right": np.median(arr[y:y + h, x + w - inner:x + w]
                               .reshape(-1, 3), axis=0),
        }

        def has_content(strip, ref_c):
            if strip.size == 0:
                return False
            d = np.sqrt(((strip - ref_c) ** 2).sum(axis=-1))
            return float((d > 45).mean()) >= 0.015

        ext = {"top": 0, "bottom": 0, "left": 0, "right": 0}
        for side in ext:
            for d in range(1, max_ext + 1):
                if side == "top":
                    if y - d < 0:
                        break
                    line = np.median(arr[y - d, x:x + w], axis=0)
                elif side == "bottom":
                    if y + h - 1 + d >= arr.shape[0]:
                        break
                    line = np.median(arr[y + h - 1 + d, x:x + w], axis=0)
                elif side == "left":
                    if x - d < 0:
                        break
                    line = np.median(arr[y:y + h, x - d], axis=0)
                else:
                    if x + w - 1 + d >= arr.shape[1]:
                        break
                    line = np.median(arr[y:y + h, x + w - 1 + d], axis=0)
                if np.sqrt(((line - ref[side]) ** 2).sum()) < thr:
                    ext[side] = d
                else:
                    break
            if ext[side]:
                if side == "top":
                    strip = arr[y - ext[side]:y, x:x + w]
                elif side == "bottom":
                    strip = arr[y + h:y + h + ext[side], x:x + w]
                elif side == "left":
                    strip = arr[y:y + h, x - ext[side]:x]
                else:
                    strip = arr[y:y + h, x + w:x + w + ext[side]]
                if not has_content(strip, ref[side]):
                    ext[side] = 0
        return ext

    out: List[Dict[str, Any]] = []
    for s in skeleton:
        x = max(0, round(s["xmin"] / 1000 * img_w))
        y = max(0, round(s["ymin"] / 1000 * img_h))
        w = min(img_w - x, max(1, round((s["xmax"] - s["xmin"]) / 1000
                                        * img_w)))
        h = min(img_h - y, max(1, round((s["ymax"] - s["ymin"]) / 1000
                                        * img_h)))
        entry = {**s, "x": x, "y": y, "w": w, "h": h,
                 "source": "model", "review": False,
                 # base_box = the agent's labeled frame BEFORE any pixel
                 # refinement / edge-extension. verify asserts against
                 # THIS for edge-extended boxes: the extension is a
                 # fade-detection heuristic, not ground truth — asserting
                 # against it is garbage-in (field failure 2026-09-29:
                 # stars drawn to an over-extended box, all green).
                 "base_box": {"x": x, "y": y, "w": w, "h": h}}
        if s["type"] != "text_block":
            best, best_iou = None, 0.0
            for c in containers:
                iou = _iou_box((x, y, w, h),
                               (c["x"], c["y"], c["w"], c["h"]))
                if iou > best_iou:
                    best, best_iou = c, iou
            if best is not None and best_iou > 0.6:
                entry.update({"x": best["x"], "y": best["y"],
                              "w": best["w"], "h": best["h"],
                              "radius": best["radius"],
                              "samples": best["samples"],
                              "source": "program"})
            else:
                entry["review"] = True
                if rgb_img is not None:
                    arr = np.asarray(rgb_img, dtype=float)
                    ext = _extend_fading_edges(arr, x, y, w, h)
                    if any(v >= 8 for v in ext.values()):
                        nx = max(0, x - ext["left"])
                        ny = max(0, y - ext["top"])
                        nw = min(img_w - nx,
                                 w + ext["left"] + ext["right"])
                        nh = min(img_h - ny,
                                 h + ext["top"] + ext["bottom"])
                        entry.update({"x": nx, "y": ny, "w": nw, "h": nh,
                                      "edge_extended": True})
                    else:
                        # 1009-07 像素收紧（非渐隐场景）：model-only
                        # container 目测框系统性偏大（实测按钮 76.5×24
                        # 写成 82×19 同类误差），边界扫描收紧——guard：
                        # 收缩后 ≥ 原框 50% 防误杀；渐隐场景走上面的
                        # edge-extend，两者互斥
                        reg = arr[y:y + h, x:x + w]
                        bgc = np.median(np.vstack([
                            reg[:2].reshape(-1, 3),
                            reg[-2:].reshape(-1, 3),
                            reg[:, :2].reshape(-1, 3),
                            reg[:, -2:].reshape(-1, 3)]), axis=0)
                        ink = (np.sqrt(((reg - bgc) ** 2).sum(axis=2))
                               > 45)
                        ridx = np.where(ink.mean(axis=1) > 0.05)[0]
                        cidx = np.where(ink.mean(axis=0) > 0.05)[0]
                        if len(ridx) and len(cidx):
                            nx0 = x + int(cidx.min())
                            ny0 = y + int(ridx.min())
                            nx1 = x + int(cidx.max()) + 1
                            ny1 = y + int(ridx.max()) + 1
                            if (nx1 - nx0 >= 0.5 * w
                                    and ny1 - ny0 >= 0.5 * h):
                                entry.update({"x": nx0, "y": ny0,
                                              "w": nx1 - nx0,
                                              "h": ny1 - ny0,
                                              "pixel_refined": True})
        elif rgb_img is not None and w > 8 and h > 8:
            region = np.asarray(rgb_img, dtype=float)[y:y + h, x:x + w]
            bg = np.median(np.vstack([
                region[:2].reshape(-1, 3), region[-2:].reshape(-1, 3),
                region[:, :2].reshape(-1, 3),
                region[:, -2:].reshape(-1, 3)]), axis=0)
            ink = np.sqrt(((region - bg) ** 2).sum(axis=2)) > 60
            ridx = np.where(ink.mean(axis=1) > 0.02)[0]
            cidx = np.where(ink.mean(axis=0) > 0.02)[0]
            if len(ridx) and len(cidx):
                nx0, ny0 = x + int(cidx.min()), y + int(ridx.min())
                nx1, ny1 = x + int(cidx.max()) + 1, y + int(ridx.max()) + 1
                if (nx1 - nx0) >= 0.3 * w and (ny1 - ny0) >= 0.3 * h:
                    entry.update({"x": nx0, "y": ny0, "w": nx1 - nx0,
                                  "h": ny1 - ny0, "source": "program"})
                # ink stats for the brief's font hints: count text line
                # bands (row-projection runs separated by >=4 blank rows)
                # and the median vertical stroke run length.
                rowfill = ink.mean(axis=1) > 0.02
                lines, gap = 0, 99
                for v in rowfill:
                    if v:
                        if gap >= 4:
                            lines += 1
                        gap = 0
                    elif lines:
                        gap += 1
                runs: List[int] = []
                for col in range(ink.shape[1]):
                    run = 0
                    for v in ink[:, col]:
                        if v:
                            run += 1
                        elif run:
                            runs.append(run)
                            run = 0
                    if run:
                        runs.append(run)
                if runs:
                    entry["ink_lines"] = lines
                    entry["stroke_thick"] = float(np.median(runs))
        out.append(entry)
    return out


def _fit_radius(mask2d: "Any") -> int:
    """Least-squares corner-radius fit from the arc insets (both sides,
    rows 1..r-1). Single-row insets are antialiasing-sensitive; fitting
    the whole arc is not. Returns 0 when no radius fits."""
    import numpy as np

    hh, ww = mask2d.shape
    ks: List[int] = []
    il: List[int] = []
    ir: List[int] = []
    for k in range(1, min(hh // 2, 48)):
        xs = np.where(mask2d[k])[0]
        if len(xs) == 0:
            break
        ks.append(k)
        il.append(int(xs.min()))
        ir.append(int(ww - 1 - xs.max()))
    best_r, best_err = 0, float("inf")
    for r in range(4, min(ww // 2, hh // 2) + 1):
        err = n = 0
        for k, l, rt in zip(ks, il, ir):
            if k < r:
                pred = r - (r * r - (r - k) * (r - k)) ** 0.5
                err += (l - pred) ** 2 + (rt - pred) ** 2
                n += 2
        if n >= 6 and err / n < best_err:
            best_err, best_r = err / n, r
    return best_r


def measure_asset(rgb_img: Image.Image, box: Dict[str, Any]) -> Dict[str, Any]:
    """Per-asset measurements that drive the asset-class decision
    (bitmap-content / transparent-subject / css-native) and the corner
    cut-in requirement for rounded-rect crops. Deterministic; printed
    into the brief so classification doesn't rely on eyeballing:
      radius_px     fitted corner radius of the subject inside the box
                    (0 = no rounded subject detected). Any nonzero value
                    means the crop MUST be displayed with a CSS
                    border-radius + overflow:hidden of this radius — a
                    raw rectangular <img> shows the crop's square corners
                    (background pixels baked into the corner areas) as
                    soon as the re-created page background differs from
                    the source background.
      css_native    <=3 flat colors and small box: rebuild in CSS/SVG
                    instead of cropping a bitmap (badges, counters,
                    simple pills). A rectangular crop of such an element
                    always shows seams.
      suggest_alpha subject floats on a uniform background (low edge-ring
                    variance, strong edge-vs-center contrast) —
                    want_alpha=true will cut it out cleanly.
    """
    import numpy as np

    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    if w < 8 or h < 8:
        return {"radius_px": 0, "subject_fill": 0.0, "css_native": False,
                "suggest_alpha": False, "top3_share": 0.0}
    crop = rgb_img.crop((x, y, x + w, y + h))
    arr = np.asarray(crop, dtype=float)
    edge = np.concatenate([
        arr[:2].reshape(-1, 3), arr[-2:].reshape(-1, 3),
        arr[:, :2].reshape(-1, 3), arr[:, -2:].reshape(-1, 3),
    ])
    bg = np.median(edge, axis=0)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    mask = dist > 45
    fill = float(mask.mean())
    radius = _fit_radius(mask) if 0.05 < fill < 0.98 else 0
    colors = dominant_colors(crop, (0, 0, w, h), n=4)
    top3_share = round(sum(c["share"] for c in colors[:3]), 2)
    center_med = np.median(
        arr[h // 3: 2 * h // 3, w // 3: 2 * w // 3].reshape(-1, 3), axis=0)
    d_edge_center = float(np.sqrt(((bg - center_med) ** 2).sum()))
    edge_std = float(edge.std(axis=0).max())
    suggest_alpha = bool(edge_std < 18 and d_edge_center > 60)
    css_native = bool(top3_share >= 0.97 and w <= 100 and h <= 100)
    return {"radius_px": int(radius), "subject_fill": round(fill, 2),
            "css_native": css_native, "suggest_alpha": suggest_alpha,
            "top3_share": top3_share}


def detect_containers(rgb_img: Image.Image, rows: List[List[Dict[str, Any]]],
                      items: List[Dict[str, Any]], img_w: int, img_h: int,
                      dist_th: float = 40.0) -> List[Dict[str, Any]]:
    """Detect solid UI blocks (buttons, pills, wide cards) per row band:
    background-distance mask -> column projection -> solid column runs ->
    grow (soft threshold) x past gradient ends -> grow y from band center
    to the block's true top/bottom (buttons are taller than the assets
    they contain — band-clamped boxes came out 20% short in testing) ->
    size/fill/IoU filters -> radius fit.

    v1 scope: high-contrast solid blocks (the button class that actually
    burned us — eyeballed bbox AND radius). Pale translucent cards on
    near-white backgrounds sit below the contrast threshold and stay on
    the manual re-check rule; blocks overlapping a labeled asset (IoU>0.5)
    are the asset itself, not a container."""
    import numpy as np

    full = np.asarray(rgb_img, dtype=float)
    containers: List[Dict[str, Any]] = []
    seen: List[Tuple[int, int, int, int]] = []
    for ri, row in enumerate(rows):
        y0 = max(0, min(p["y"] for p in row) - 8)
        y1 = min(img_h, max(p["y"] + p["h"] for p in row) + 8)
        band = full[y0:y1]
        m = max(4, img_w // 25)
        bg = np.median(np.vstack([band[:, :m].reshape(-1, 3),
                                  band[:, -m:].reshape(-1, 3)]), axis=0)
        dist_band = np.sqrt(((band - bg) ** 2).sum(axis=2))
        col = (dist_band > dist_th).mean(axis=0) > 0.5
        soft_dist_full = None
        i = 0
        while i < img_w:
            if not col[i]:
                i += 1
                continue
            j = i
            while j < img_w and col[j]:
                j += 1
            # grow x on a softer threshold: gradient buttons fade below
            # the hard threshold at one end (a real case lost 25% width)
            gi, gj = i, j
            if soft_dist_full is None:
                soft_dist_full = np.sqrt(
                    ((full - bg) ** 2).sum(axis=2))
            softcol = (soft_dist_full[y0:y1] > 28).mean(axis=0) > 0.3
            while gi > 0 and softcol[gi - 1]:
                gi -= 1
            while gj < img_w and softcol[gj]:
                gj += 1
            w = gj - gi
            if w < 0.15 * img_w:
                i = j
                continue
            # grow y from the band center on the full-height strip —
            # limited to band ± its own height so growth can't wander
            # into unrelated rows above/below
            strip_dist = soft_dist_full[:, gi:gj]
            rowfrac = (strip_dist > 28).mean(axis=1) > 0.35
            limit_up = max(0, y0 - (y1 - y0))
            limit_dn = min(img_h, y1 + (y1 - y0))
            cy0 = (y0 + y1) // 2
            ty0, ty1 = cy0, cy0
            while ty0 > limit_up and rowfrac[ty0 - 1]:
                ty0 -= 1
            while ty1 < limit_dn and rowfrac[ty1]:
                ty1 += 1
            h = ty1 - ty0
            soft_mask = strip_dist[ty0:ty1] > 28
            fill = float(soft_mask.mean())
            box = (gi, ty0, w, h)
            box_area = w * h
            covered = any(
                max(_overlap_frac(box, (p["x"], p["y"], p["w"], p["h"])),
                    _iou_box(box, (p["x"], p["y"], p["w"], p["h"]))) > 0.5
                for p in items)
            if (24 <= h <= img_h * 0.35 and fill > 0.6
                    and not covered
                    and not any(_iou_box(box, s) > 0.6 for s in seen)):
                # hard threshold for the radius arc: soft-threshold masks
                # include the drop shadow, which flattens the arc and
                # under-fits the radius (a real case read 23 vs true 40)
                radius = _fit_radius(strip_dist[ty0:ty1] > dist_th)
                # probe at 25% height: the vertical center line carries
                # the label text, which pollutes single-point samples
                cy = ty0 + round(h * 0.25)
                samples = [
                    _sample_hex(rgb_img, gi + round(w * f), cy)
                    for f in (0.2, 0.5, 0.8)
                ]
                # contrast gate: a real block's own fill sits well away
                # from the row background — blocks whose samples are
                # near-bg color are gradient noise, not UI (a real case
                # emitted a phantom block with bg-distance ≈13; real
                # buttons all read >70)
                def _hexdist(hx: str) -> float:
                    return (
                        (int(hx[1:3], 16) - bg[0]) ** 2
                        + (int(hx[3:5], 16) - bg[1]) ** 2
                        + (int(hx[5:7], 16) - bg[2]) ** 2
                    ) ** 0.5

                if min(_hexdist(s) for s in samples) < 35:
                    i = j
                    continue
                containers.append({
                    "index": len(containers), "row": ri,
                    "x": gi, "y": ty0, "w": w, "h": h,
                    "radius": radius, "samples": samples,
                })
                seen.append(box)
            i = j

    # —— 1009-06 补充扫描（gap bands）——v1 只扫素材行 band：高对比
    # 按钮/胶囊独占无素材行时漏检（brief "CONTAINERS: none auto-detected"
    # 实证——黄底按钮/白标签/胶囊全漏）。对未被 band 覆盖的 y 区间跑
    # 同款管线，参数适配小元素（min 宽 40px、高 20-120px），检出标
    # source=auto-ext 供校准量化确认（与 model-only 同口径）。
    # S2C 误判实证吸收：统计基于 dist 掩码（底板色距），框内彩色子元素
    # 的影响由 fill/contrast 闸约束——白色面板（低对比）天然不检出。
    if rgb_img is not None:
        covered: List[Tuple[int, int]] = sorted(
            (max(0, min(p["y"] for p in row) - 8),
             min(img_h, max(p["y"] + p["h"] for p in row) + 8))
            for row in rows)
        gaps: List[Tuple[int, int]] = []
        _cur = 0
        for (_a, _b) in covered:
            if _a - _cur >= 60:
                gaps.append((_cur, _a))
            _cur = max(_cur, _b)
        if img_h - _cur >= 60:
            gaps.append((_cur, img_h))
        soft_full = np.sqrt(((full - np.median(full, axis=(0, 1))) ** 2)
                            .sum(axis=2))
        for (gy0, gy1) in gaps:
            band = full[gy0:gy1]
            m = max(4, img_w // 25)
            bg = np.median(np.vstack([band[:, :m].reshape(-1, 3),
                                      band[:, -m:].reshape(-1, 3)]), axis=0)
            dist_band = np.sqrt(((band - bg) ** 2).sum(axis=2))
            # gap 版列占比阈值 0.35（v1 的 0.5 按素材占 band 大头调的；
            # gap band 含大量空白，小按钮列占比会卡在 0.5 之下——实测
            # 40px 按钮在 84px band 里占比 0.48 被漏）
            col = (dist_band > dist_th).mean(axis=0) > 0.35
            softcol = (soft_full[gy0:gy1] > 28).mean(axis=0) > 0.3
            i = 0
            while i < img_w:
                if not col[i]:
                    i += 1
                    continue
                j = i
                while j < img_w and col[j]:
                    j += 1
                gi, gj = i, j
                while gi > 0 and softcol[gi - 1]:
                    gi -= 1
                while gj < img_w and softcol[gj]:
                    gj += 1
                w = gj - gi
                if w < 40:  # 小按钮/胶囊（v1 的 15% 图宽过滤会滤掉它们）
                    i = j
                    continue
                strip_dist = soft_full[:, gi:gj]
                rowfrac = (strip_dist > 28).mean(axis=1) > 0.35  # 全高数组
                # grow 从 band 中心向两边（v1 同语义），**绝对 y 索引**
                # （相对 gy0 偏移查全高数组 = 索引错位 158，grow 查到
                # 素材行恒 True，ty 被推满整 band，fill 稀释被过滤）
                _cy = (gy0 + gy1) // 2
                ty0, ty1 = _cy, _cy
                while ty0 > gy0 and rowfrac[ty0 - 1]:
                    ty0 -= 1
                while ty1 < gy1 and rowfrac[ty1]:
                    ty1 += 1
                h = ty1 - ty0
                soft_mask = strip_dist[ty0:ty1] > 28
                fill = float(soft_mask.mean())
                box = (gi, ty0, w, h)
                covered_hit = any(
                    max(_overlap_frac(box, (p["x"], p["y"], p["w"],
                                            p["h"])),
                        _iou_box(box, (p["x"], p["y"], p["w"], p["h"])))
                    > 0.3 for p in items)
                if not (20 <= h <= 120 and fill > 0.6 and not covered_hit
                        and not any(_iou_box(box, s) > 0.6 for s in seen)):
                    i = j
                    continue
                radius = _fit_radius(strip_dist[ty0:ty1] > dist_th)
                cy = ty0 + round(h * 0.25)
                samples = [
                    _sample_hex(rgb_img, gi + round(w * f), cy)
                    for f in (0.2, 0.5, 0.8)
                ]

                def _hexdist(hx: str) -> float:
                    return (
                        (int(hx[1:3], 16) - bg[0]) ** 2
                        + (int(hx[3:5], 16) - bg[1]) ** 2
                        + (int(hx[5:7], 16) - bg[2]) ** 2
                    ) ** 0.5

                if min(_hexdist(s) for s in samples) < 35:
                    i = j
                    continue
                containers.append({
                    "index": len(containers), "row": -1,
                    "x": gi, "y": ty0, "w": w, "h": h,
                    "radius": radius, "samples": samples,
                    "source": "auto-ext",
                })
                seen.append(box)
                i = j
    return containers


def _expand_box(p: Dict[str, Any], img_w: int, img_h: int,
                frac: float) -> None:
    """Grow an item's box by frac of its size on all sides (endpoints
    clamped to the image)."""
    dx, dy = round(p["w"] * frac), round(p["h"] * frac)
    x0 = max(0, p["x"] - dx)
    y0 = max(0, p["y"] - dy)
    x1 = min(img_w, p["x"] + p["w"] + dx)
    y1 = min(img_h, p["y"] + p["h"] + dy)
    p["x"], p["y"], p["w"], p["h"] = x0, y0, x1 - x0, y1 - y0
    p["cx"], p["cy"] = x0 + p["w"] // 2, y0 + p["h"] // 2


# Frame-variant rescue: when ALL models fail a box outright (no usable
# candidate), the crop likely strangled the subject — the local models are
# deterministic, so re-running the same box is pointless; retry with a
# *different input*: a 10%/20% expanded box. Zero API cost.
# A merely *poor* score never swaps the box: the box is the agent's
# labeling ground truth (verify asserts against it), and a poor-but-present
# mask goes to the human calibration loop instead — icon shapes with real
# hollows (battery cells, rings) would false-trigger a swap.
VARIANT_FRACTIONS = (0.10, 0.20)


def _rel_to_out(p: Path, out_dir: Path) -> str:
    """Report paths relative to out_dir (portable layout.json, and
    build_check_sheet re-resolves against out_dir — an absolute or
    out-relative path both work; plain relative-to-cwd does not)."""
    try:
        return str(p.resolve().relative_to(out_dir.resolve()))
    except ValueError:
        return str(p)


def _fit_container_gradient(rgb_img: Image.Image,
                            c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Q5: fit a linear gradient for a container. Both axes are tried
    (a vertical-gradient button is wider than tall — the long axis is
    the WRONG sampling axis), probes use per-channel MEDIAN of a 5px
    slab (icons inside the container are outliers that poison means),
    and the fit is emitted only when mid probes sit on the start→end
    line. Deterministic; replaces eyeballing gradient endpoints."""
    import numpy as np

    x, y, w, h = c["x"], c["y"], c["w"], c["h"]
    arr = np.asarray(rgb_img.crop((x, y, x + w, y + h)), dtype=float)
    # Thresholds calibrated on the 2026-09-29 首页黑改 containers:
    # probes skip the outer 15% (border/AA pixels); span <18/255 (~7%
    # channel swing) reads as a flat fill (solid buttons measured
    # span<10); a mid probe >28% of span off the start→end line means
    # the ramp is not two-stop (banner's mid-stop measured 40+).
    best = None
    for axis in ("h", "v"):
        n = (arr.shape[1] if axis == "h" else arr.shape[0])
        lo, hi = int(n * 0.15), int(n * 0.85)
        if hi - lo < 4:
            continue
        probes = []
        for t in np.linspace(lo, max(lo + 1, hi - 1), 6):
            t = int(t)
            slab = (arr[:, t:t + 5, :] if axis == "h"
                    else arr[t:t + 5, :, :])
            probes.append(np.median(slab.reshape(-1, 3), axis=0))
        start, end = probes[0], probes[-1]
        span = float(np.sqrt(((end - start) ** 2).sum()))
        if span < 18:
            continue
        errs = []
        for k, pr in enumerate(probes[1:-1], start=1):
            tt = k / (len(probes) - 1)
            expect = start + (end - start) * tt
            errs.append(float(np.sqrt(((pr - expect) ** 2).sum())))
        if max(errs) > max(24.0, span * 0.28):
            continue
        cand = {"axis": axis, "span": span, "start": start, "end": end,
                "mid_err": max(errs)}
        if best is None or span > best["span"]:
            best = cand
    if best is None:
        return None
    # CSS angle convention: 90deg = to right (0% color on the LEFT —
    # matches our horizontal probe order); 180deg = to bottom (0% color
    # on TOP — matches our vertical probe order, probes[0] samples the
    # container top). Using 0deg for vertical would flip the two stops
    # (field review 2026-09-30: vertical is the most common button
    # gradient shape).
    deg = 90 if best["axis"] == "h" else 180
    s, e = best["start"], best["end"]
    css = (f"linear-gradient({deg}deg, "
           f"#{round(s[0]):02X}{round(s[1]):02X}{round(s[2]):02X} 0%, "
           f"#{round(e[0]):02X}{round(e[1]):02X}{round(e[2]):02X} 100%)")
    return {"css": css, "angle_deg": deg,
            "from": [round(v) for v in s], "to": [round(v) for v in e],
            "mid_err": round(best["mid_err"], 1),
            "fit_note": f"fitted linear ramp, mid-err≤{best['mid_err']:.0f}/255"
                        " — spot-check against the source before use"}


def detect_dpr(rgb: Image.Image,
               skeleton: List[Dict[str, Any]],
               guess: Optional[float]) -> Tuple[float, float, str]:
    """G (2026-09-30): infer source density. The ÷2 hardcode was a 2x
    assumption — a 621px-wide mini-app shot (dpr≈1.5-1.66) rendered at
    half size made EVERY element/spacing wrong while all assertions
    stayed green (garbage-in baseline). Anchor = median text ink-cap
    height across labeled text blocks (body-text cap ≈13.5 logical px);
    candidates are the real device densities. Returns (dpr, anchor_raw,
    how).

    置信度入口合同（2026-10-07 第六轮评审）：dpr 由 density_guess 与
    墨迹锚点交叉裁决，任何单一信号不再独立定案——
      guess + 高置信锚点一致（±20%）→ 采用锚点候选（交叉验证通过）
      guess + 锚点冲突              → SystemExit 要求 --dpr 显式裁决
                                      （旧实现 guess 短路返回，交叉
                                      验证是死门禁——标注指南把
                                      density_guess 列为必填，正常
                                      路径永远绕过墨迹校验）
      只有 guess                    → 采用，how 标注未交叉验证
      只有锚点：样本≥3 且离散度≤0.35 且离候选≤0.15 → 采用
                否则（单一大标题摇摆误判 1.5x 的 1x 复现）→
                                      SystemExit 要求 --dpr
      两者皆无                      → SystemExit（旧 default 2.0 是
                                      2x 假设复活，不再合法）
    用户显式 --dpr 不进本函数（调用处短路——用户裁决优先于交叉）。"""
    import numpy as np

    gray = np.asarray(rgb.convert("L"), dtype=float)
    W, H = rgb.size
    caps: List[float] = []
    for s in skeleton:
        if s.get("type") != "text_block":
            continue
        # 坐标合同（2026-10-07 第五轮评审修复）：parse_skeleton 产出
        # ymin/xmin/ymax/xmax 归一化字段，本函数却消费 x/y/w/h 像素
        # 字段——字段不匹配使全部 text_block 被 continue，墨迹锚点
        # 检测成死代码（永远 default 2.0）。归一化格式就地换算像素。
        if s.get("w") is not None and s.get("h") is not None:
            x, y, w, h = s["x"], s["y"], s["w"], s["h"]
        elif None not in (s.get("ymin"), s.get("xmin"),
                          s.get("ymax"), s.get("xmax")):
            x = max(0, round(s["xmin"] / 1000 * W))
            y = max(0, round(s["ymin"] / 1000 * H))
            w = max(1, round((s["xmax"] - s["xmin"]) / 1000 * W))
            h = max(1, round((s["ymax"] - s["ymin"]) / 1000 * H))
        else:
            continue
        if not w or not h or w > gray.shape[1] or h > gray.shape[0]:
            continue
        reg = gray[y:y + h, x:x + w]
        if reg.size == 0:
            continue
        lo, hi = float(reg.min()), float(reg.max())
        if hi - lo < 25:
            continue
        border = np.concatenate([reg[:2].ravel(), reg[-2:].ravel(),
                                 reg[:, :2].ravel(), reg[:, -2:].ravel()])
        dark = float(np.median(border)) > (lo + hi) / 2
        m = (reg < lo + (hi - lo) * 0.45) if dark else \
            (reg > hi - (hi - lo) * 0.45)
        rows = np.where(m.any(axis=1))[0]
        if len(rows) < 4:
            continue
        runs, s0 = [], rows[0]
        for a, b in zip(rows, rows[1:]):
            if b - a > 3:
                runs.append(a - s0 + 1)
                s0 = b
        runs.append(rows[-1] - s0 + 1)
        caps.extend(r for r in runs if 6 <= r <= 60)

    med = float(np.median(caps)) if caps else 0.0
    raw = med / 13.5
    cands = (1.0, 1.5, 2.0, 3.0)
    dpr = min(cands, key=lambda c: abs(raw - c))
    # 锚点可靠性判据（第六轮评审：1x 图单一大标题被误判 1.5x——
    # 单样本 + 邻近候选摇摆，没有置信度就没有裁决权）
    spread = (float(np.std(caps)) / med) if med else 1.0
    anchor_ok = (len(caps) >= 3 and spread <= 0.35
                 and abs(raw - dpr) / dpr <= 0.15)
    if guess:
        g = float(guess)
        if anchor_ok:
            if abs(g - dpr) / dpr <= 0.20:
                return dpr, raw, (f"cross-checked: guess {g:g} ≈ anchor "
                                  f"(median cap {med:.0f}px / 13.5, "
                                  f"n={len(caps)})")
            raise SystemExit(
                f"dpr conflict: density_guess {g:g} vs ink-anchor {dpr} "
                f"(raw {raw:.2f}) — pass --dpr to decide")
        return g, 0.0, (f"explicit guess {g:g} (anchor unreliable: "
                        f"n={len(caps)}, spread={spread:.2f}) — "
                        "not cross-checked")
    if anchor_ok:
        return dpr, raw, (f"median cap {med:.0f}px / 13.5 "
                          f"(n={len(caps)}, spread={spread:.2f})")
    raise SystemExit(
        f"dpr unreliable: anchor raw={raw:.2f} (n={len(caps)}, "
        f"spread={spread:.2f}) and no density_guess — pass --dpr")


def _shrink_raw_overlaps(items: List[Dict[str, Any]],
                         skeleton_norm: List[Dict[str, Any]],
                         rgb_img: Optional[Image.Image],
                         img_w: int, img_h: int,
                         out_assets: Path,
                         report: List[Dict[str, Any]],
                         dpr: float = 1.0,
                         rgb_phys: Optional[Image.Image] = None) -> None:
    """Shrink opaque (RAW) crop boxes that touch/overlap a text block to
    their ink bbox (border-median background model, same threshold as
    the fidelity ratio). The pipeline repairs the geometry itself — a
    published occluding rectangle is a contract violation, not a
    review item."""
    import numpy as np

    if rgb_img is None:
        return
    text_boxes: List[tuple] = []
    for s in skeleton_norm:
        if s.get("type") != "text_block":
            continue
        x = round(s["xmin"] / 1000 * img_w)
        y = round(s["ymin"] / 1000 * img_h)
        w = round((s["xmax"] - s["xmin"]) / 1000 * img_w)
        h = round((s["ymax"] - s["ymin"]) / 1000 * img_h)
        text_boxes.append((x, y, x + w, y + h))
    by_index = {e.get("index"): e for e in report}
    for it in items:
        if it.get("want_alpha", False):
            continue
        ix, iy, iw, ih = it["x"], it["y"], it["w"], it["h"]
        hit = None
        for (tx0, ty0, tx1, ty1) in text_boxes:
            near = (tx0 < ix + iw + 4 and ix < tx1 + 4
                    and ty0 < iy + ih + 4 and iy < ty1 + 4)
            if near:
                hit = (tx0, ty0, tx1, ty1)
                break
        if hit is None:
            continue
        region = np.asarray(
            rgb_img.crop((ix, iy, ix + iw, iy + ih)), dtype=float)
        if region.size == 0:
            continue
        ed = np.concatenate([region[:2].reshape(-1, 3),
                             region[-2:].reshape(-1, 3),
                             region[:, :2].reshape(-1, 3),
                             region[:, -2:].reshape(-1, 3)])
        bgc = np.median(ed, axis=0)
        ink = np.sqrt(((region - bgc) ** 2).sum(axis=2)) > 45
        ridx = np.where(ink.mean(axis=1) > 0.02)[0]
        cidx = np.where(ink.mean(axis=0) > 0.02)[0]
        if not len(ridx) or not len(cidx):
            continue
        nx0, ny0 = ix + int(cidx.min()), iy + int(ridx.min())
        nx1, ny1 = ix + int(cidx.max()) + 1, iy + int(ridx.max()) + 1
        if (nx1 - nx0) < 0.3 * iw or (ny1 - ny0) < 0.3 * ih:
            continue  # shrink would collapse the subject — leave as is
        if nx0 == ix and ny0 == iy and nx1 == ix + iw and ny1 == iy + ih:
            continue  # ink already fills the box
        it.update({"x": nx0, "y": ny0, "w": nx1 - nx0, "h": ny1 - ny0})
        # re-crop from the PHYSICAL plane so the published RAW stays at
        # full resolution (ink bbox was measured on the logical plane)
        if rgb_phys is not None:
            crop = rgb_phys.crop((round(nx0 * dpr), round(ny0 * dpr),
                                  round(nx1 * dpr), round(ny1 * dpr)))
        else:
            crop = rgb_img.crop((nx0, ny0, nx1, ny1))
        # 重裁后必过擦字关卡（1009-01：此路径曾覆盖主循环的 inpaint
        # 成果——落盘素材文字回来而 report 谎报已擦）
        _others = [{"index": q["index"], "x": q["x"], "y": q["y"],
                    "w": q["w"], "h": q["h"]}
                   for q in items if q is not it and q.get("want_alpha")]
        erase_overphoto_for_item(
            crop, {"x": nx0, "y": ny0, "w": nx1 - nx0, "h": ny1 - ny0},
            skeleton_norm, img_w, img_h, dpr,
            (round(nx0 * dpr), round(ny0 * dpr),
             round(nx1 * dpr), round(ny1 * dpr)), other_items=_others)
        crop.save(out_assets / f"asset_{it['index']}.png")
        e = by_index.get(it["index"])
        if e is not None:
            e["box_px"] = {"x": nx0, "y": ny0,
                           "w": nx1 - nx0, "h": ny1 - ny0}
            e["crop"] = _rel_to_out(
                out_assets / f"asset_{it['index']}.png",
                out_assets.parent)
            e.setdefault("verdict", {"label": "OK",
                                     "reasons": []})
            e["verdict"]["reasons"].append(
                "raw box neighbor-shrunk to ink bbox (text-block "
                "occlusion risk)")
        print(f"asset_{it['index']}: RAW box shrunk to ink bbox "
              f"{nx1-nx0}x{ny1-ny0}@({nx0},{ny0}) — text-block "
              "occlusion risk")


def run(image_path: Path, assets_path: Path, out_dir: Path,
        no_alpha: bool, alpha_threshold: int = 100,
        keep_largest: bool = True, erode_px: int = 0,
        dilate_px: int = 0, model: str = "auto",
        dpr: Optional[float] = None) -> int:
    if not image_path.is_file():
        raise SystemExit(f"image not found: {image_path}")
    if not assets_path.is_file():
        raise SystemExit(f"assets.json not found: {assets_path}")
    assets, texts, skeleton = parse_assets(read_json(assets_path))
    guess = None
    try:
        raw_top = read_json(assets_path)
        guess = raw_top.get("density_guess")
        if guess is not None:
            guess = float(guess)
    except Exception:
        guess = None

    with Image.open(image_path) as img:
        img.load()
        rgb = img.convert("RGB")
    img_w, img_h = rgb.size

    # G: DPR normalization at the entrance — everything downstream
    # (crops, coordinates, brief, layout.json, verify baseline) works in
    # LOGICAL px, so every tech stack consumes 1:1 with no per-stack
    # conversion. ÷2 hardcode was a 2x assumption; a dpr≈1.5 shot made
    # the whole page 25% too small with all assertions green
    # (field failure 2026-09-30: 永辉 mini-app long page).
    if dpr:
        # 用户显式 --dpr：直接采用（2026-10-07 第六轮评审——用户裁决
        # 优先于交叉验证，不进 detect_dpr）
        anchor_raw, how = 0.0, "explicit --dpr"
    else:
        try:
            # detect_dpr 抛 SystemExit（冲突/低置信/双缺）时不被本层
            # except Exception 捕获——直接向用户传达 pass --dpr
            dpr, anchor_raw, how = detect_dpr(rgb, skeleton, guess)
        except Exception as exc:
            raise SystemExit(f"dpr detection failed: {exc} — pass --dpr")
    # Two-plane model after normalization:
    #   rgb_LOG  = logical px — ALL coordinates, layout, audit geometry
    #   rgb_PHYS = original px — asset crops + alpha masks stay at full
    #              resolution (quality chain thresholds were calibrated
    #              on physical-scale crops; downscaling them re-broke
    #              fidelity on the regression set 2026-09-30).
    rgb_phys = rgb
    if dpr and abs(dpr - 1.0) > 0.05:
        new_w, new_h = round(img_w / dpr), round(img_h / dpr)
        rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
        print(f"source {img_w}x{img_h}px normalized by dpr={dpr} "
              f"({how}) -> {new_w}x{new_h} logical px")
        img_w, img_h = new_w, new_h
    else:
        dpr = 1.0
        print(f"source {img_w}x{img_h}px treated as 1x logical ({how})")

    items = pixelize(assets, img_w, img_h)
    out_assets = out_dir / "assets"
    out_assets.mkdir(parents=True, exist_ok=True)

    removers: List[Tuple[str, BgRemover]] = []
    alpha_available = True
    if not no_alpha:
        wanted = ["u2net", "isnet"] if model == "both" else [model]
        for m in wanted:
            try:
                removers.append((m, get_remover(m)))
            except FileNotFoundError as exc:
                print(f"WARN: {m}: {exc}")
        if not removers:
            print("WARN: continuing WITHOUT background removal "
                  "(alpha assets will fall back to raw crops).")
            alpha_available = False

    report: List[Dict[str, Any]] = []
    # Labeling snapshot (T1 incremental rerun + S2 labeling diff): the
    # previous run's per-asset signature lives in assets.snapshot.json.
    # Unchanged assets reuse their extraction as-is (T1); the snapshot
    # diff (added/removed/moved) is reported so silent labeling drift
    # becomes a visible, confirmable difference (S2).
    snapshot_path = out_dir / "assets.snapshot.json"
    last_snapshot: Dict[str, Any] = {"assets": []}
    # Pipeline revision stamps the snapshot: detector/threshold changes
    # invalidate previous verdicts, so a revision mismatch forces a full
    # re-extraction (T1 reuse is only valid same-revision).
    PIPELINE_REV = "v5-overphoto-20261008"
    if snapshot_path.is_file():
        try:
            snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if snap.get("pipeline_rev") == PIPELINE_REV:
                last_snapshot = snap
            else:
                print("pipeline revision changed — full re-extraction "
                      "(previous snapshot ignored)")
        except Exception:
            last_snapshot = {"assets": []}
    last_by_index = {a.get("index"): a
                     for a in last_snapshot.get("assets", [])}

    def _asset_sig(p_: Dict[str, Any]) -> Dict[str, Any]:
        return {"x": p_["x"], "y": p_["y"], "w": p_["w"], "h": p_["h"],
                "want_alpha": bool(p_.get("want_alpha"))}

    # Q2 labeling audit: two labeled boxes heavily overlapping means one
    # of them is mis-framed — surface it in the verdicts of BOTH assets
    # at extraction time, not at code-writing time.
    labeling_overlap: Dict[int, List[str]] = {}
    for _i, _a in enumerate(items):
        for _b in items[_i + 1:]:
            ox = max(0, min(_a["x"] + _a["w"], _b["x"] + _b["w"])
                     - max(_a["x"], _b["x"]))
            oy = max(0, min(_a["y"] + _a["h"], _b["y"] + _b["h"])
                     - max(_a["y"], _b["y"]))
            ov = ox * oy
            smaller = max(1, min(_a["w"] * _a["h"], _b["w"] * _b["h"]))
            if ov / smaller > 0.30:
                msg = (f"labeling: overlaps asset_{_b['index']} by "
                       f"{ov / smaller:.0%}")
                labeling_overlap.setdefault(_a["index"], []).append(msg)
                labeling_overlap.setdefault(_b["index"], []).append(
                    f"labeling: overlaps asset_{_a['index']} by "
                    f"{ov / smaller:.0%}")

    for p in items:
        labeled_box = {"x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"]}
        # asset crops come from the PHYSICAL plane (full resolution) —
        # logical coordinates scale back up by dpr
        _phys_box = (round(p["x"] * dpr), round(p["y"] * dpr),
                     round((p["x"] + p["w"]) * dpr),
                     round((p["y"] + p["h"]) * dpr))
        crop = rgb_phys.crop(_phys_box)
        # —— over_photo 擦字（2026-10-08 重影根因修复）——
        # "照片+半透明遮罩+交互文字"模式：合成截图裁出的素材带烘焙
        # 文字，HTML 再渲染同一文字 → 重影。text_block 与素材框相交
        # → 交集区域 inpaint 擦除（遮罩留在图里，HTML 只渲染文字层）。
        # —— over_photo 擦字统一关卡（1009-01；1009-13 掩码补 asset 框）——
        _others = [{"index": q["index"], "x": q["x"], "y": q["y"],
                    "w": q["w"], "h": q["h"]}
                   for q in items if q is not p and q.get("want_alpha")]
        _over_blocks, _n_erased = erase_overphoto_for_item(
            crop, p, skeleton, img_w, img_h, dpr, _phys_box, item=p,
            other_items=_others)
        crop_path = out_assets / f"asset_{p['index']}.png"
        crop.save(crop_path)
        entry: Dict[str, Any] = {
            "index": p["index"],
            "description": p["description"],
            "box_px": {"x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"]},
            "crop": _rel_to_out(crop_path, out_dir),
            "alpha": None,
            "status": "ok",
        }
        if _over_blocks:
            entry["over_photo_blocks"] = _over_blocks
            entry["over_photo_erased"] = _n_erased
            # 就地传播给 brief/layout（build_layout 消费 items）
            p["over_photo_blocks"] = _over_blocks
        if p["want_alpha"]:
            # T1 incremental rerun: labeling signature unchanged → reuse
            # the previous extraction verbatim (alpha file, verdict,
            # audit). Global passes (neighbor-shrink, audits) still run.
            prev_e = last_by_index.get(p["index"])
            if (prev_e is not None
                    and prev_e.get("sig") == _asset_sig(p)
                    and prev_e.get("description") == p["description"]):
                crop.save(crop_path)
                entry["reused"] = True
                pa = prev_e.get("alpha")
                perr = prev_e.get("alpha_error")
                prej = prev_e.get("alpha_rejected")
                if pa and (out_dir / pa).is_file():
                    dst = out_assets / f"asset_{p['index']}_alpha.png"
                    if (out_dir / pa).resolve() != dst.resolve():
                        shutil.copyfile(out_dir / pa, dst)
                    entry["alpha"] = _rel_to_out(dst, out_dir)
                    entry["alpha_pick"] = prev_e.get("alpha_pick") or {}
                    if prev_e.get("measure"):
                        entry["measure"] = prev_e["measure"]
                    entry["verdict"] = prev_e.get("verdict") or {
                        "label": "OK", "reasons": []}
                    entry["calibration"] = prev_e.get("calibration") or {
                        "labeled_box": labeled_box,
                        "final_box": dict(entry["box_px"]),
                        "needs_review": False}
                    # Q2 labeling overlap must also reach REUSED entries:
                    # the neighbour's frame may have moved in THIS run,
                    # so the pairwise audit is computed fresh for all
                    # assets and both sides of an overlap get flagged.
                    _lw = labeling_overlap.get(p["index"])
                    if _lw:
                        _v = entry.get("verdict") or {
                            "label": "OK", "reasons": []}
                        if _v.get("label") == "OK":
                            _v["label"] = "REVIEW"
                        _v["reasons"] = (_v.get("reasons") or []) + _lw
                        entry["verdict"] = _v
                    print(f"asset_{p['index']}: unchanged — alpha reused")
                    report.append(entry)
                    continue
                if perr and prej and (out_dir / prej).is_file():
                    dst = out_assets / f"asset_{p['index']}_alpha.rejected"
                    if (out_dir / prej).resolve() != dst.resolve():
                        shutil.copyfile(out_dir / prej, dst)
                    entry["alpha_error"] = perr
                    entry["alpha_rejected"] = _rel_to_out(dst, out_dir)
                    entry["alpha_pick"] = prev_e.get("alpha_pick") or {}
                    entry["verdict"] = prev_e.get("verdict") or {
                        "label": "USE_RAW", "reasons": [perr]}
                    print(f"asset_{p['index']}: unchanged — gated alpha "
                          "reused (still not published)")
                    report.append(entry)
                    continue
                # previous artifacts gone — fall through to full extraction
            if not removers:
                entry["alpha"] = None
                entry["alpha_error"] = "background removal unavailable"
            else:
                alpha_img, pick = remove_bg_best(
                    crop, removers, alpha_threshold, keep_largest,
                    erode_px, dilate_px,
                )
                # Frame-variant rescue: only when the box produced NO
                # usable candidate at all (see comment at VARIANT_*).
                if alpha_img is None:
                    for frac in VARIANT_FRACTIONS:
                        trial = dict(p)
                        _expand_box(trial, img_w, img_h, frac)
                        tcrop = rgb.crop((trial["x"], trial["y"],
                                          trial["x"] + trial["w"],
                                          trial["y"] + trial["h"]))
                        t_img, t_pick = remove_bg_best(
                            tcrop, removers, alpha_threshold, keep_largest,
                            erode_px, dilate_px,
                        )
                        if t_img is not None:
                            alpha_img, pick = t_img, {
                                **t_pick, "variant": f"expand{frac:.0%}",
                            }
                            p.update(trial)
                            entry["box_px"] = {"x": p["x"], "y": p["y"],
                                               "w": p["w"], "h": p["h"]}
                            crop = tcrop
                            crop.save(crop_path)  # keep raw in the same frame
                            print(
                                f"asset_{p['index']}: frame variant "
                                f"expand{frac:.0%} rescued an all-fail box"
                            )
                            break
                elif _pick_score(pick) > 0.30:
                    # Poor-but-present mask: keep box and result, flag for
                    # the human calibration loop.
                    pick = {**pick, "suspect": "low_score"}
                    print(
                        f"asset_{p['index']}: WARN low mask score "
                        f"{_pick_score(pick):.2f} — audit in check sheet"
                    )
                # Clipped-box rescue: mask touching the crop border means
                # the label box may have cut the subject (flat cut edges
                # in the final asset). Re-run on a 20% expanded box and
                # adopt it ONLY when the subject genuinely grows there —
                # subjects that legitimately fill their box keep the
                # original frame.
                if (alpha_img is not None
                        and "variant" not in pick
                        and _touches_border(alpha_img)):
                    trial = dict(p)
                    _expand_box(trial, img_w, img_h, 0.20)
                    tcrop = rgb.crop((trial["x"], trial["y"],
                                      trial["x"] + trial["w"],
                                      trial["y"] + trial["h"]))
                    t_img, t_pick = remove_bg_best(
                        tcrop, removers, alpha_threshold, keep_largest,
                        erode_px, dilate_px,
                    )
                    if t_img is not None:
                        ob = _tight_bbox(alpha_img)
                        nb = _tight_bbox(t_img)
                        off = (p["x"] - trial["x"], p["y"] - trial["y"])
                        nb_in_old = (nb[0] + off[0], nb[1] + off[1],
                                     nb[2] + off[0], nb[3] + off[1])
                        if ((nb_in_old[2] - nb_in_old[0]) > (ob[2] - ob[0]) * 1.08
                                or (nb_in_old[3] - nb_in_old[1]) > (ob[3] - ob[1]) * 1.08):
                            alpha_img = t_img
                            pick = {**t_pick,
                                    "clipped_box_resolved": "expand20%"}
                            p.update(trial)
                            entry["box_px"] = {"x": p["x"], "y": p["y"],
                                               "w": p["w"], "h": p["h"]}
                            crop = tcrop
                            crop.save(crop_path)
                            print(
                                f"asset_{p['index']}: WARN label box clipped "
                                "the subject — auto-expanded 20%, audit in "
                                "check sheet detail"
                            )
                # Loose-box tightening: subject occupying <40% of its box
                # usually means the label overshot the asset (labels are
                # eyeballed). Reframe to mask bbox + 4px margin so the
                # brief's geometry matches what is actually drawn.
                if alpha_img is not None and "variant" not in pick:
                    bb = _tight_bbox(alpha_img)
                    if bb is not None:
                        fill = ((bb[2] - bb[0]) * (bb[3] - bb[1])
                                / (p["w"] * p["h"]))
                        if fill < 0.40:
                            m = 4
                            mx0 = max(0, bb[0] - m)
                            my0 = max(0, bb[1] - m)
                            mx1 = min(p["w"], bb[2] + m)
                            my1 = min(p["h"], bb[3] + m)
                            alpha_img = alpha_img.crop(
                                (mx0, my0, mx1, my1)
                            )
                            p.update({"x": p["x"] + mx0, "y": p["y"] + my0,
                                      "w": mx1 - mx0, "h": my1 - my0})
                            entry["box_px"] = {"x": p["x"], "y": p["y"],
                                               "w": p["w"], "h": p["h"]}
                            crop = rgb.crop((p["x"], p["y"],
                                             p["x"] + p["w"],
                                             p["y"] + p["h"]))
                            crop.save(crop_path)
                            pick = {**pick, "loose_box_tightened": f"fill={fill:.2f}"}
                            print(
                                f"asset_{p['index']}: WARN label box loose "
                                f"(subject fills {fill:.0%}) — auto-"
                                "tightened to subject+4px, audit in check "
                                "sheet detail"
                            )
                if alpha_img is None:
                    entry["alpha"] = None
                    entry["alpha_error"] = (
                        "bad mask in all models "
                        f"({pick.get('reason', 'unknown')}), "
                        "fell back to raw crop"
                    )
                else:
                    import numpy as np

                    bb = _tight_bbox(alpha_img)
                    if bb is not None:
                        fill = ((bb[2] - bb[0]) * (bb[3] - bb[1])
                                / (p["w"] * p["h"]))
                        pick = {**pick, "fill": round(fill, 2)}
                    cov = float(
                        (np.asarray(alpha_img)[..., 3] > 128).mean()
                    )
                    if cov < 0.15 or cov > 0.97:
                        pick = {**pick, "suspect": "alpha_coverage",
                                "coverage": round(cov, 3)}
                        print(
                            f"asset_{p['index']}: WARN alpha coverage "
                            f"{cov:.0%} outside 15-97% — audit in check "
                            "sheet detail"
                        )
                    # Mask audit (deterministic, pre-verdict). Thresholds
                    # calibrated on the 2026-09-29 首页黑改 set (20 masks,
                    # 2 known-bad): labeled boxes legitimately carry
                    # glow/breathing margin, so a small mask inside its
                    # box is HEALTHY — what we flag is (a) the mask
                    # TOUCHING the frame (cut-through suspicion), (b)
                    # strongly asymmetric insets (shifted subject), (c)
                    # horizontal centroid offset (vertical offset is
                    # natural — most icons are bottom-heavy), (d) a
                    # straight edge on the mask's own bbox (a cut side
                    # reads as a filled line; a natural arc only touches
                    # its bbox at one point).
                    audit = {}
                    try:
                        _m = (np.asarray(alpha_img)[..., 3] > 127)
                        _ys, _xs = np.nonzero(_m)
                        if len(_xs) and len(_ys):
                            _h, _w = _m.shape
                            inset = {
                                "left": _xs.min() / _w,
                                "right": (_w - 1 - _xs.max()) / _w,
                                "top": _ys.min() / _h,
                                "bottom": (_h - 1 - _ys.max()) / _h,
                            }
                            touch = [k for k, v in inset.items()
                                     if v < 0.01]
                            if touch:
                                audit["mask_touches_frame"] = touch
                            asym_h = abs(inset["left"]
                                         - inset["right"])
                            asym_v = abs(inset["top"]
                                         - inset["bottom"])
                            # vertical asymmetry is NATURAL (icons are
                            # bottom-heavy: horn/handle shapes sit low);
                            # only horizontal asymmetry — a half-cut
                            # subject — is a defect signal
                            if asym_h > 0.20:
                                audit["inset_asymmetry"] = {
                                    "h": round(asym_h, 3),
                                    "v": round(asym_v, 3)}
                            cx_off = abs(_xs.mean() / _w - 0.5)
                            audit["centroid_offset_h"] = round(cx_off, 3)
                            x0, x1 = _xs.min(), _xs.max()
                            y0, y1 = _ys.min(), _ys.max()
                            bw, bh2 = x1 - x0 + 1, y1 - y0 + 1
                            fill_top = _m[y0, x0:x1 + 1].mean()
                            fill_bot = _m[y1, x0:x1 + 1].mean()
                            fill_left = _m[y0:y1 + 1, x0].mean()
                            fill_right = _m[y0:y1 + 1, x1].mean()
                            cuts = [name for name, v in (
                                ("top", fill_top),
                                ("bottom", fill_bot),
                                ("left", fill_left),
                                ("right", fill_right)) if v > 0.85]
                            if cuts:
                                audit["straight_cut_edges"] = cuts
                        p["_mask_audit"] = audit
                    except Exception as exc:  # noqa: BLE001
                        p["_mask_audit"] = {"error": str(exc)}
                    # fidelity_ratio — alpha-opaque px vs non-background
                    # px in the same source box. <0.9 = the matte shrank
                    # the subject (edges eaten). Computed BEFORE publish:
                    # a failed mask is never written as a citable
                    # _alpha.png (the model trusts script output, so a
                    # broken file on disk would be a legal reference —
                    # field failures 2026-09-29).
                    fr = None
                    if rgb is not None:
                        try:
                            import numpy as _np
                            ab = _np.asarray(alpha_img)
                            if ab.ndim == 3 and ab.shape[2] == 4:
                                op = int((ab[:, :, 3] > 128).sum())
                                bx = entry["box_px"]
                                # sample on the PHYSICAL plane (same
                                # scale the crop/mask were computed at)
                                src = _np.asarray(
                                    rgb_phys.crop(
                                        (round(bx["x"] * dpr),
                                         round(bx["y"] * dpr),
                                         round((bx["x"] + bx["w"]) * dpr),
                                         round((bx["y"] + bx["h"]) * dpr))),
                                    dtype=float)
                                ed = _np.concatenate([
                                    src[:2].reshape(-1, 3),
                                    src[-2:].reshape(-1, 3),
                                    src[:, :2].reshape(-1, 3),
                                    src[:, -2:].reshape(-1, 3)])
                                bgc = _np.median(ed, axis=0)
                                nonbg = int((_np.sqrt(
                                    ((src - bgc) ** 2).sum(axis=2))
                                    > 45).sum())
                                fr = round(op / max(nonbg, 1), 2)
                                p["_fidelity_ratio"] = fr
                        except Exception as exc:  # noqa: BLE001
                            print(f"asset_{p['index']}: WARN fidelity "
                                  f"ratio failed: {exc}")
                    # HARD GATE — aggregation decides whether the alpha
                    # is published AT ALL. A gated mask is saved as
                    # *.rejected (evidence, not citable) and
                    # entry["alpha"] stays None: referencing it 404s,
                    # which forces the raw/SVG path through the
                    # verify FAIL loop instead of trusting the agent
                    # to "remember" a warning.
                    hard: List[str] = []
                    if fr is not None and fr < 0.9:
                        hard.append(f"fidelity_ratio={fr} <0.9")
                    # center_void intentionally NOT a hard gate: on the
                    # 2026-09-30 regression set it carries NO signal
                    # (good icons 0.29-0.39 vs bad 0.368 — distributions
                    # overlap). It stays a REVIEW hint at >0.40 in the
                    # verdict aggregation. Hard gates need discriminative
                    # power; a gate that gates half the good samples is
                    # itself a regression (caught by mask-suite Q1).
                    audit = p.get("_mask_audit") or {}
                    if audit.get("straight_cut_edges"):
                        hard.append("straight cut edge(s): "
                                    f"{audit['straight_cut_edges']}")
                    if audit.get("inset_asymmetry"):
                        hard.append("inset asymmetry (h): "
                                    f"{audit['inset_asymmetry']}")
                    if pick.get("rejected"):
                        hard.append("single-model race: "
                                    f"{pick['rejected']}")
                    # NOTE: suspect=="low_score" (race score >0.30) is a
                    # human-review hint, NOT a hard gate — good masks
                    # routinely score 0.3+ on this metric (regression
                    # suite caught 19 over-gatings when it was hard).
                    # Only a genuine coverage anomaly hard-gates here.
                    if pick.get("suspect") == "alpha_coverage":
                        hard.append("alpha coverage suspect: "
                                    f"{pick['suspect']} "
                                    f"{pick.get('coverage', '')}")
                    if hard:
                        alpha_path = (
                            out_assets
                            / f"asset_{p['index']}_alpha.rejected")
                        alpha_img.save(alpha_path, format="PNG")
                        entry["alpha"] = None
                        entry["alpha_rejected"] = _rel_to_out(
                            alpha_path, out_dir)
                        entry["alpha_error"] = (
                            "ALPHA GATE — not published: "
                            + "; ".join(hard))
                        entry["alpha_pick"] = pick
                        print(f"asset_{p['index']}: ALPHA GATE — not "
                              f"published ({'; '.join(hard)})")
                    else:
                        alpha_path = (
                            out_assets
                            / f"asset_{p['index']}_alpha.png")
                        alpha_img.save(alpha_path)
                        entry["alpha"] = _rel_to_out(alpha_path, out_dir)
                        entry["alpha_pick"] = pick
        needs_review = False
        if entry.get("alpha_pick"):
            ap = entry["alpha_pick"]
            needs_review = bool(
                ap.get("suspect") or ap.get("clipped_box_resolved")
                or ap.get("loose_box_tightened")
            )
        if rgb is not None:
            try:
                m = measure_asset(rgb, {"x": p["x"], "y": p["y"],
                                        "w": p["w"], "h": p["h"]})
                p["_measure"] = m
                entry["measure"] = m
            except Exception as exc:  # noqa: BLE001 — advisory only
                print(f"asset_{p['index']}: WARN measure failed: {exc}")
        if p.get("_fidelity_ratio") is not None:
            entry.setdefault("measure", {})[
                "fidelity_ratio"] = p["_fidelity_ratio"]
        # Verdict — the deterministic disposition for this asset. The
        # agent EXECUTES this verdict and has no discretion over asset
        # quality: eye-judgement is not a gate (field failures
        # 2026-09-29: a mask missing its base + a frame-shifted icon
        # both passed eyeball checks while the numbers were alarming).
        reasons: List[str] = []
        label = "OK"
        if entry.get("alpha"):
            fr = p.get("_fidelity_ratio")
            if fr is not None and fr < 0.9:
                label = "USE_RAW"
                reasons.append(
                    f"fidelity_ratio={fr} <0.9 (matte shrank subject)")
            ap = entry.get("alpha_pick") or {}
            sc = ap.get("scores") or {}
            if (sc.get("center_void") or 0) > 0.40:
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    f"center_void={sc.get('center_void')} >0.40")
            audit = p.get("_mask_audit") or {}
            if audit.get("mask_touches_frame"):
                # touch alone does NOT raise the label: on light-page
                # images (白改) 50% of healthy masks touch their frame —
                # raising would flood reviews and dilute attention.
                # It only matters combined with cut/asymmetry signals.
                reasons.append(
                    "mask touches frame edge: "
                    f"{audit['mask_touches_frame']}")
            if audit.get("inset_asymmetry"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    "inset asymmetry: "
                    f"{audit['inset_asymmetry']}")
            if audit.get("straight_cut_edges"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    "straight cut edge(s): "
                    f"{audit['straight_cut_edges']}")
            if (audit.get("centroid_offset_h") or 0) > 0.10:
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    "mask centroid offset "
                    f"{audit['centroid_offset_h']} of frame width")
            if ap.get("rejected"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(f"single-model race: {ap['rejected']}")
            if ap.get("clipped_box_resolved"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    "label box clipped subject — auto-expanded")
            if ap.get("loose_box_tightened"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    "label box loose — auto-tightened "
                    f"({ap['loose_box_tightened']})")
            if ap.get("suspect"):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(
                    f"alpha coverage suspect: {ap['suspect']} "
                    f"{ap.get('coverage', '')}")
            for _lw in labeling_overlap.get(p["index"], []):
                if label == "OK":
                    label = "REVIEW"
                reasons.append(_lw)
        elif entry.get("alpha_error"):
            label = "USE_RAW"
            reasons.append("alpha unavailable: " + entry["alpha_error"])
        else:
            reasons.append(
                "raw crop (want_alpha=false) — no alpha promised")
        entry["verdict"] = {"label": label, "reasons": reasons}
        if label != "OK":
            print(f"asset_{p['index']}: VERDICT {label} "
                  f"({'; '.join(reasons)})")
        entry["calibration"] = {
            "labeled_box": labeled_box,
            "final_box": dict(entry["box_px"]),
            "needs_review": needs_review,
        }
        report.append(entry)
        print(
            f"asset_{p['index']} '{p['description']}' {p['w']}x{p['h']}"
            f"@({p['x']},{p['y']})"
            + (f" alpha={entry['alpha']}" if entry["alpha"]
               else f" alpha=NONE ({entry.get('alpha_error', 'skipped')})")
        )

    # RAW neighbor-shrink post-pass — opaque crops whose box touches or
    # overlaps a text block bake the neighbour into the page and occlude
    # it (field failure 2026-09-29: swords crop covering معركة). The
    # pipeline fixes the geometry ITSELF (shrink to ink bbox) instead of
    # flagging it for the agent: script output is the contract, and an
    # occluding rectangle must never exist to be referenced.
    try:
        _shrink_raw_overlaps(items, skeleton, rgb, img_w, img_h,
                             out_assets, report, dpr=dpr, rgb_phys=rgb_phys)
    except Exception as exc:  # noqa: BLE001 — advisory pass
        print(f"WARN: raw neighbor-shrink pass failed: {exc}")




    brief, layout = build_layout(items, img_w, img_h, rgb, texts, skeleton,
                                 dpr=dpr)
    (out_dir / "layout_brief.txt").write_text(brief, "utf-8")
    layout_payload = {
        **layout,
        "source_image": str(image_path.resolve()),
        "assets": [
            {"index": e["index"], "description": e["description"],
             "crop": e["crop"], "alpha": e["alpha"], "box_px": e["box_px"],
             **({"measure": e["measure"]} if e.get("measure") else {}),
             **({"over_photo_blocks": e["over_photo_blocks"],
                 "over_photo_text_erased": True}
                if e.get("over_photo_blocks") else {})}
            for e in report
        ],
    }
    (out_dir / "layout.json").write_text(
        json.dumps(layout_payload, ensure_ascii=False, indent=2), "utf-8"
    )
    (out_dir / "assets_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )
    # S2 labeling diff + T1 snapshot for the next incremental run
    cur_by_index = {e.get("index"): e for e in report}
    labeling_diff: Dict[str, List[str]] = {"added": [], "removed": [],
                                           "moved": [], "changed": []}
    for e in report:
        pv = last_by_index.get(e.get("index"))
        if pv is None:
            labeling_diff["added"].append(f"asset_{e.get('index')}")
            continue
        pb, cb = pv.get("sig"), e.get("box_px")
        if pb and cb and (abs(pb["x"] - cb["x"]) > 2
                          or abs(pb["y"] - cb["y"]) > 2):
            dx, dy = cb["x"] - pb["x"], cb["y"] - pb["y"]
            labeling_diff["moved"].append(
                f"asset_{e.get('index')} moved ({dx:+d},{dy:+d})px")
        if pv.get("want_alpha") != (
                (pv.get("sig") or {}).get("want_alpha")):
            pass  # sig already carries want_alpha; moved covers box shifts
    for idx, pv in last_by_index.items():
        if idx not in cur_by_index:
            labeling_diff["removed"].append(f"asset_{idx}")
    if any(labeling_diff.values()):
        print("labeling diff vs previous run: "
              + json.dumps(labeling_diff, ensure_ascii=False))
    snapshot = {"pipeline_rev": PIPELINE_REV, "assets": []}
    for p in items:
        e = cur_by_index.get(p["index"]) or {}
        snapshot["assets"].append({
            "index": p["index"], "sig": _asset_sig(p),
            "description": p["description"],
            "alpha": e.get("alpha"),
            "alpha_rejected": e.get("alpha_rejected"),
            "alpha_error": e.get("alpha_error"),
            "alpha_pick": e.get("alpha_pick"),
            "measure": e.get("measure"),
            "verdict": e.get("verdict"),
            "calibration": e.get("calibration"),
        })
    (snapshot_path).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), "utf-8")
    build_check_sheet(report, out_dir)
    build_check_sheet_detail(report, out_dir, rgb,
                             layout.get("containers"),
                             layout.get("skeleton"))

    alpha_ok = sum(1 for e in report if e["alpha"])
    print(
        f"\ndone: {len(report)} assets cropped, {alpha_ok} with transparent "
        f"background; layout_brief.txt + layout.json written to {out_dir}"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True, help="source screenshot path")
    ap.add_argument("--assets", required=True,
                    help="assets.json (agent-written box_2d labels)")
    ap.add_argument("--out", required=True, help="output work directory")
    ap.add_argument("--dpr", type=float, default=None,
                    help="explicit source density override (auto: model "
                         "guess + ink-height anchor); e.g. 2.0 for a "
                         "750px-wide 2x shot, 1.5 for a 621px mini-app "
                         "capture")
    ap.add_argument("--no-alpha", action="store_true",
                    help="skip background removal entirely")
    ap.add_argument("--alpha-threshold", type=int, default=100,
                    help="mask binarization threshold 0-255 (0=off); "
                    "higher = cleaner edges but may eat thin details")
    ap.add_argument("--no-keep-largest", action="store_true",
                    help="disable largest-connected-component filtering")
    ap.add_argument("--erode-px", type=int, default=0,
                    help="erode mask edge N px (use when edges bleed)")
    ap.add_argument("--dilate-px", type=int, default=0,
                    help="dilate mask edge N px (use when edges are eaten)")
    ap.add_argument("--model", choices=("both", "auto", "u2net", "isnet"),
                    default="both",
                    help="background-removal: both = run every installed "
                    "model and keep the best-scoring mask (default); "
                    "auto = isnet when installed, else u2net")
    ap.add_argument("--request",
                    help="request.json — 第 1 步需求确认落盘（gate 校验）")
    ap.add_argument("--no-gate", action="store_true",
                    help="skip request gate (local debugging only)")
    args = ap.parse_args()

    # ---- request gate（第 1 步需求确认落盘校验，2026-09-29 新增）----
    # 交互本身不可脚本化，但交互结果可以：确认四项必须写入 request.json，
    # 管线入口校验其存在与值域——漏问/漏记在物理上被拦截，不再依赖模型自觉。
    if not args.no_gate:
        rc = _check_request_gate(args.request)
        if rc != 0:
            return rc

    return run(Path(args.image), Path(args.assets), Path(args.out),
               args.no_alpha, args.alpha_threshold, not args.no_keep_largest,
               args.erode_px, args.dilate_px, args.model, args.dpr)


def _check_request_gate(request_path: str) -> int:
    """校验 request.json（第 1 步确认的落盘产物）。缺字段/值域非法 → exit 2。"""
    if not request_path:
        print("GATE FAIL: --request request.json 缺失 — 第 1 步需求确认四项"
              "（档位/技术栈/输出目录/设计系统）必须落盘（模板见 SKILL.md "
              "第 1 步）。仅本地调试可加 --no-gate。")
        return 2
    rp = Path(request_path)
    if not rp.is_file():
        print(f"GATE FAIL: {rp} 不存在。")
        return 2
    try:
        data = json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"GATE FAIL: {rp} 不是合法 JSON: {exc}")
        return 2
    missing = [k for k in ("tier", "stack", "output_dir")
               if not str(data.get(k) or "").strip()]
    if missing:
        print(f"GATE FAIL: request.json 缺字段: {missing}")
        return 2
    if data.get("tier") not in ("保真", "快速"):
        print("GATE FAIL: tier 必须是 \"保真\" 或 \"快速\"。")
        return 2
    print(f"gate ok: tier={data['tier']} stack={data['stack']} "
          f"out={data['output_dir']} "
          f"design_system={data.get('design_system') or '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
