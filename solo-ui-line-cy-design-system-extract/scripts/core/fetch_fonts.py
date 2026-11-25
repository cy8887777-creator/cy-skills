# -*- coding: utf-8 -*-
"""fetch_fonts.py — 中文字体整包自托管下载（产物自包含：不赌用户机器装了什么字体）。
下载 Noto Sans SC（中文，OFL）+ Inter（数字/拉丁，OFL）woff2 到 <out>/system-spec/fonts/，
gen_html 生成的 @font-face 与字体栈（Noto Sans SC / Inter 优先）直接消费。
用法: python fetch_fonts.py <out_dir>   （幂等：已存在且大小>50KB 的文件跳过）"""
import os, sys, urllib.request

FILES = [
    ("noto-sans-sc-chinese-simplified-400-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5/files/noto-sans-sc-chinese-simplified-400-normal.woff2"),
    ("noto-sans-sc-chinese-simplified-500-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5/files/noto-sans-sc-chinese-simplified-500-normal.woff2"),
    ("noto-sans-sc-chinese-simplified-700-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5/files/noto-sans-sc-chinese-simplified-700-normal.woff2"),
    ("inter-latin-400-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/inter@5/files/inter-latin-400-normal.woff2"),
    ("inter-latin-500-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/inter@5/files/inter-latin-500-normal.woff2"),
    ("inter-latin-700-normal.woff2",
     "https://cdn.jsdelivr.net/npm/@fontsource/inter@5/files/inter-latin-700-normal.woff2"),
]

def main(out_dir):
    fonts = os.path.join(out_dir, "system-spec", "fonts")
    os.makedirs(fonts, exist_ok=True)
    fail = []
    for name, url in FILES:
        dest = os.path.join(fonts, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 50 * 1024:
            print(f"[skip] {name}")
            continue
        try:
            urllib.request.urlretrieve(url, dest)
            size = os.path.getsize(dest)
            ok = open(dest, "rb").read(4) == b"wOF2"
            print(f"[{'ok' if ok else 'BAD'}] {name} {size // 1024}KB")
            if not ok:
                fail.append(name)
        except Exception as e:
            print(f"[FAIL] {name}: {e}", file=sys.stderr)
            fail.append(name)
    if fail:
        print(f"[WARN] {len(fail)} 枚失败：{fail}——网络不可达时产物退化为系统字体栈（微软雅黑），不阻塞交付", file=sys.stderr)
        return 1
    print("[done] 字体自托管就位（6 枚 woff2 · OFL 许可 · 可随产物分发）")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python fetch_fonts.py <out_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
