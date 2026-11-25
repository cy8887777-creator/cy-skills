#!/usr/bin/env python3
"""Exercise manifest inspection, static masking, APNG build, and decode once."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    tool = Path(__file__).with_name("apng_pipeline.py")
    with tempfile.TemporaryDirectory(prefix="ui-idle-apng-") as directory:
        root = Path(directory)
        base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(base).rectangle((8, 30, 55, 53), fill=(60, 120, 180, 255))
        base.save(root / "source.png")
        mask = Image.new("L", base.size, 0)
        ImageDraw.Draw(mask).rectangle((20, 8, 44, 31), fill=255)
        mask.save(root / "mask.png")
        entries = []
        for index, rise in enumerate((0, 2, 3, 1)):
            frame = base.copy()
            draw = ImageDraw.Draw(frame)
            draw.rectangle((24, 11 - rise, 38, 25 - rise), fill=(245, 245, 238, 255))
            draw.ellipse((28, 15 - rise, 31, 18 - rise), fill=(20, 20, 20, 255))
            draw.point((2, 2), fill=(255, 0, 0, 255))
            name = f"pose-{index:02d}.png"
            frame.save(root / name)
            entries.append({"file": name, "duration_ms": 100 + index * 20})
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "base": "source.png", "editable_mask": "mask.png", "frames": entries,
        }), encoding="utf-8")
        report_path = root / "report.json"
        sheet_path = root / "sheet.png"
        output_path = root / "result.apng"
        subprocess.run([sys.executable, str(tool), "inspect", str(manifest),
                        "--report", str(report_path), "--sheet", str(sheet_path)], check=True)
        subprocess.run([sys.executable, str(tool), "build", str(manifest),
                        "--output", str(output_path)], check=True)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["frame_count"] == 4 and report["static_area_preserved"]
        assert sheet_path.is_file()
        with Image.open(output_path) as animation:
            assert animation.n_frames == 4 and animation.size == (64, 64)
            for index in range(animation.n_frames):
                animation.seek(index)
                assert animation.convert("RGBA").getpixel((2, 2)) == (0, 0, 0, 0)
        print("End-to-end smoke test passed")


if __name__ == "__main__":
    main()
