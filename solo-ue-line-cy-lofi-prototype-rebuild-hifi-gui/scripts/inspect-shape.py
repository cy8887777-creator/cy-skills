# -*- coding: utf-8 -*-
"""inspect-shape.py —— 素材判形探针（PIL ASCII 降采样 + 主色聚类 + alpha 结构判定）
用法: python inspect-shape.py <素材路径...> [--width 44] [--colors 3]
输出（stdout，可直接重定向文件后挑读，防 context 爆）:
  - 尺寸 / alpha 结构判定（中心镂空=环形框 / 实心=盘）
  - 主色聚类 TopN（粗聚类 #RRGGBB(占比%)）
  - ASCII 判形（alpha 阈值三级字符 ' .:@'，终端字符高宽比 2:1 补偿）
铁律:
  1. ASCII 判形只做辅助——会错（六枚段位徽章曾全族误判礼花），语义硬依据=nodeId 反查 raw.json
  2. 判形结论须「nodeId 反查 + 判形」双确认才可记档；错一次进档案会连环放大
  3. 判 alpha 镂空定素材结构: 中心透明=环形头像框（不是头像），alpha 实心=盘
"""
import sys
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")  # 重定向文件场景防 GBK 乱码
except Exception:
    pass

def parse_args(argv):
    paths, width, colors = [], 44, 3
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--width":
            i += 1; width = int(argv[i])
        elif a == "--colors":
            i += 1; colors = int(argv[i])
        else:
            paths.append(a)
        i += 1
    return paths, width, colors

def alpha_structure(img):
    """中心区域 alpha 检测: 镂空=环形框 / 实心=盘"""
    w, h = img.size
    im = img.convert("RGBA")
    px = im.load()
    cx, cy = w // 2, h // 2
    # 中心 5 点采样（中心 + 四向偏移 1/8 边长）
    off = max(1, min(w, h) // 8)
    samples = [(cx, cy), (cx - off, cy), (cx + off, cy), (cx, cy - off), (cx, cy + off)]
    alphas = [px[x, y][3] for x, y in samples]
    solid = sum(1 for a in alphas if a > 200)
    if solid == 0:
        return "镂空(环形/框——不可当头像填充)"
    if solid >= 4:
        return "实心(盘/图)"
    return "半镂空(复杂结构,建议看 ASCII)"

def top_colors(img, n=3):
    im = img.convert("RGBA")
    im.thumbnail((64, 64))
    buckets = {}
    total = 0
    for r, g, b, a in im.getdata():
        if a < 128:
            continue
        total += 1
        key = (r // 48, g // 48, b // 48)  # 粗聚类
        cnt, sr, sg, sb = buckets.get(key, (0, 0, 0, 0))
        buckets[key] = (cnt + 1, sr + r, sg + g, sb + b)
    out = []
    for key, (cnt, sr, sg, sb) in sorted(buckets.items(), key=lambda kv: -kv[1][0])[:n]:
        out.append("#%02X%02X%02X(%d%%)" % (sr // cnt, sg // cnt, sb // cnt, round(cnt * 100 / max(1, total))))
    return " ".join(out)

def ascii_render(img, width=44):
    im = img.convert("RGBA")
    w, h = im.size
    hh = max(1, round(h * width / w / 2))  # 终端字符高比宽约 2:1
    small = im.resize((width, hh))
    px = small.load()
    lines = []
    for y in range(hh):
        row = []
        for x in range(width):
            r, g, b, a = px[x, y]
            if a < 40:
                row.append(" ")
            elif a < 160:
                row.append(".")
            else:
                # 亮度分两档，浅色用 : 深色用 @
                lum = (r * 299 + g * 587 + b * 114) // 1000
                row.append(":" if lum > 180 else "@")
        lines.append("".join(row).rstrip())
    return "\n".join(lines)

def main():
    paths, width, colors = parse_args(sys.argv[1:])
    if not paths:
        print(__doc__)
        sys.exit(2)
    for p in paths:
        if p.lower().endswith(".svg"):
            print("### %s  [svg 不走 PIL 判形——改读文本: head -c 600 查着色机制(固定色→currentColor) + viewBox 内容占比]" % p)
            continue
        try:
            img = Image.open(p)
        except Exception as e:
            print("### %s  [打开失败: %s]" % (p, e))
            continue
        print("### %s  (%dx%d)" % (p, img.size[0], img.size[1]))
        print("  alpha结构: " + alpha_structure(img))
        try:
            print("  主色: " + top_colors(img, colors))
        except Exception as e:
            print("  主色: 解析失败 %s" % e)
        print(ascii_render(img, width))
        print()

if __name__ == "__main__":
    main()
