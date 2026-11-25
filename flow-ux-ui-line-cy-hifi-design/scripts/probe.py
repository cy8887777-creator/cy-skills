"""Material probe: inspect intake materials, pre-fill tier/device hints. Zero VLM, local only.

Usage: python probe.py <path-to-material-file-or-dir>
Output: JSON {file_count, by_type, tier_hint, device_hint, notes[]}
"""
import argparse
import json
import sys
from pathlib import Path

IMG_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
DOC_EXT = {'.pdf', '.md', '.docx', '.doc', '.txt', '.xlsx', '.csv'}
HTML_EXT = {'.html', '.htm'}


def classify(path: Path):
    ext = path.suffix.lower()
    if ext in IMG_EXT:
        return 'image'
    if ext in DOC_EXT:
        return 'doc'
    if ext in HTML_EXT:
        return 'html'
    return 'other'


def image_ratio(path: Path):
    """Return width/height ratio, or None. Try Pillow; PNG/JPEG header fallback."""
    try:
        from PIL import Image  # noqa
        with Image.open(path) as im:
            w, h = im.size
            return w / h if h else None
    except Exception:
        pass
    try:
        if path.suffix.lower() == '.png':
            with open(path, 'rb') as f:
                head = f.read(24)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                import struct
                w, h = struct.unpack('>II', head[16:24])
                return w / h if h else None
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('target', type=Path)
    args = ap.parse_args()
    if not args.target.exists():
        print(json.dumps({'error': 'path not found: ' + str(args.target)},
                         ensure_ascii=False))
        raise SystemExit(2)

    files = ([args.target] if args.target.is_file()
             else [p for p in args.target.rglob('*') if p.is_file()])
    by_type = {'image': 0, 'doc': 0, 'html': 0, 'other': 0}
    ratios = []
    names = ' '.join(p.stem.lower() for p in files)
    for p in files:
        by_type[classify(p)] += 1
        if classify(p) == 'image':
            r = image_ratio(p)
            if r:
                ratios.append(r)

    device_hint = 'unknown'
    if ratios:
        wide = sum(1 for r in ratios if r >= 1.15)
        tall = sum(1 for r in ratios if r <= 0.9)
        if tall > wide:
            device_hint = 'mobile'
        elif wide > tall:
            device_hint = 'desktop'
    if any(k in names for k in ('mobile', 'app', 'h5', 'wap')):
        device_hint = 'mobile'
    if any(k in names for k in ('admin', 'backend', 'pc', 'desktop', 'dashboard')):
        device_hint = 'desktop' if device_hint == 'unknown' else device_hint + '+desktop'

    pages_hint = by_type['image'] or by_type['doc'] * 3 or 1
    tier = 'S' if pages_hint <= 5 else ('M' if pages_hint <= 15 else 'L')

    notes = []
    if by_type['doc']:
        notes.append('docs found: read them (functional list / PRD) before U1 questioning')
    if by_type['image'] and by_type['doc'] == 0:
        notes.append('image pack without docs: treat as effect-image pack branch')
    if by_type['html']:
        notes.append('existing html present: consider continue/upgrade branch')
    if device_hint == 'unknown' and files:
        notes.append('no device clue: ask user (interrogation)')

    print(json.dumps({
        'file_count': len(files), 'by_type': by_type,
        'tier_hint': tier, 'device_hint': device_hint,
        'pages_hint': pages_hint, 'notes': notes,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
