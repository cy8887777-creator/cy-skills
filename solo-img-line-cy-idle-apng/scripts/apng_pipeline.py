#!/usr/bin/env python3
"""Inspect ordered still frames and build a verified APNG. No model calls."""

import argparse
import json
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat


def read_image(path, mode):
    with Image.open(path) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValueError(f"Expected one still image: {path}")
        source.load()
        return source.convert(mode)


def load_manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("frames")
    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("Manifest needs at least two ordered frames")

    root = path.parent
    base = read_image(root / data["base"], "RGBA") if data.get("base") else None
    mask = read_image(root / data["editable_mask"], "L") if data.get("editable_mask") else None
    if mask is not None and base is None:
        raise ValueError("editable_mask requires base")

    raw_frames = []
    durations = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("file"):
            raise ValueError(f"Frame {index} needs a file")
        duration = entry.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 60000:
            raise ValueError(f"Frame {index} needs duration_ms between 1 and 60000")
        raw_frames.append(read_image(root / entry["file"], "RGBA"))
        durations.append(duration)

    size = raw_frames[0].size
    for image in raw_frames[1:] + [item for item in (base, mask) if item is not None]:
        if image.size != size:
            raise ValueError(f"All images and the mask must be {size}; got {image.size}")

    frames = [Image.composite(image, base, mask) for image in raw_frames] if mask else raw_frames
    return frames, durations, base, mask, raw_frames


def mean_delta(left, right):
    channel_means = ImageStat.Stat(ImageChops.difference(left, right)).mean
    return round(sum(channel_means) / len(channel_means), 3)


def inspect(frames, durations, base, mask, raw_frames):
    changes = [mean_delta(a, b) for a, b in zip(frames, frames[1:])]
    if not any(changes):
        raise ValueError("Every frame is identical; there is no animation")
    seam = mean_delta(frames[-1], frames[0])
    report = {
        "size": list(frames[0].size),
        "frame_count": len(frames),
        "duration_ms": durations,
        "adjacent_mean_delta": changes,
        "loop_seam_mean_delta": seam,
        "median_adjacent_mean_delta": median(changes),
        "notes": "Difference numbers locate jumps; they are not a pass/fail threshold. Review the actual frames and loop.",
    }
    if mask:
        outside = ImageOps.invert(mask)
        blank = Image.new("RGBA", base.size)
        report["raw_outside_mask_mean_delta"] = [
            mean_delta(Image.composite(image, base, outside), base)
            for image in raw_frames
        ]
        report["static_area_preserved"] = all(
            ImageChops.difference(Image.composite(frame, blank, outside),
                                  Image.composite(base, blank, outside)).getextrema()
            == ((0, 0),) * 4 for frame in frames
        )
    return report


def make_sheet(frames, path):
    max_side = 320
    width, height = frames[0].size
    scale = min(1.0, max_side / max(width, height))
    thumb_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    columns = min(4, len(frames))
    rows = (len(frames) + columns - 1) // columns
    cell_width, cell_height = thumb_size[0] + 20, thumb_size[1] + 38
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#e8e8e8")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x = (index % columns) * cell_width + 10
        y = (index // columns) * cell_height + 26
        thumbnail = frame.resize(thumb_size, Image.Resampling.LANCZOS)
        surface = Image.new("RGBA", thumb_size, "white")
        surface.alpha_composite(thumbnail)
        sheet.paste(surface.convert("RGB"), (x, y))
        draw.text((x, y - 18), f"{index:02d}", fill="black")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def build(frames, durations, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path, format="PNG", save_all=True, append_images=frames[1:],
        duration=durations, loop=0, disposal=0, blend=0, optimize=False,
    )
    with Image.open(path) as result:
        if result.size != frames[0].size or result.n_frames != len(frames):
            raise ValueError("APNG decoded size or frame count differs from the manifest")
        if result.info.get("loop") != 0:
            raise ValueError("APNG is not configured to loop indefinitely")
        for index, expected in enumerate(frames):
            result.seek(index)
            actual = result.convert("RGBA")
            if any(high for low, high in ImageChops.difference(actual, expected).getextrema()):
                raise ValueError(f"APNG decoded frame {index} differs from the source")
            actual_duration = result.info.get("duration")
            if actual_duration is None or abs(actual_duration - durations[index]) > 1:
                raise ValueError(f"APNG decoded duration differs at frame {index}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("manifest", type=Path)
    inspect_parser.add_argument("--report", type=Path, required=True)
    inspect_parser.add_argument("--sheet", type=Path, required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("manifest", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frames, durations, base, mask, raw_frames = load_manifest(args.manifest)
    report = inspect(frames, durations, base, mask, raw_frames)
    if args.command == "inspect":
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        make_sheet(frames, args.sheet)
        print(f"Report: {args.report.resolve()}")
        print(f"Contact sheet: {args.sheet.resolve()}")
    else:
        print(f"APNG: {build(frames, durations, args.output).resolve()}")
    print(f"Frames: {report['frame_count']}; loop seam mean delta: {report['loop_seam_mean_delta']}")


if __name__ == "__main__":
    main()
