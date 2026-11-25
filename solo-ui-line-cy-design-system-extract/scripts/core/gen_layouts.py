"""
scripts/core/gen_layouts.py — 布局章线框生成器（v4.0 · C 组简版）

用法（唯一）：python gen_layouts.py <项目out目录>

做什么：九类骨架的区域色块线框（375 框 + 灰阶色块 + 区域名标注）脚本产出，
替换 design-system.html 的 s02 布局章「线框示意」区。
迷你示例页的组件拼装是 agent 的语义活——不在本生成器范围（写进站④细则）。
真案例已有手工线框时不覆盖（label 定位不到即安全跳过）。
"""
import io
import os
import re
import sys

# 九类骨架 → 区域序列（自上而下；区域名标注）
SKELETONS = [
    ("枢纽 Hub", [("导航区", 40), ("插画头部", 90), ("宫格入口", 80), ("推荐卡片流", 130), ("TabBar", 46)]),
    ("聚焦 Focus", [("导航区", 40), ("聚焦内容卡", 220), ("操作按钮", 44), ("TabBar", 46)]),
    ("流览 Feed", [("导航区", 40), ("状态分段", 36), ("卡片列表 ×N", 260), ("TabBar", 46)]),
    ("表单配置 Form", [("导航区", 40), ("表单输入行 ×N", 200), ("提交按钮", 44), ("TabBar", 46)]),
    ("详情 Detail", [("导航区", 40), ("主图/标题", 110), ("信息分区 ×N", 160), ("底部行动栏", 50)]),
    ("档案 Profile", [("沉浸头部", 120), ("用户信息卡", 80), ("功能菜单行 ×N", 160), ("TabBar", 46)]),
    ("对话 Chat", [("导航区", 40), ("消息气泡流", 280), ("输入栏", 44)]),
    ("过渡 Onboarding", [("全屏插画/文案", 300), ("行动按钮", 44), ("跳过/指示器", 30)]),
    ("系统 System", [("系统态占位", 220), ("行动按钮", 44)]),
]


def wireframe(name, regions):
    total_h = sum(h for _, h in regions) + (len(regions) - 1) * 8
    scale = min(1.0, 300.0 / total_h)
    rows = []
    for rname, h in regions:
        hh = max(14, int(h * scale))
        rows.append('<div style="height:%dpx;background:#EEF2F7;border:1px solid #DDE3EA;'
                    'border-radius:6px;display:grid;place-items:center;font-size:9px;'
                    'color:#7A8699">%s</div>' % (hh, rname))
    body = '<div style="display:flex;flex-direction:column;gap:4px">%s</div>' % "".join(rows)
    return ('<div style="flex:none;width:170px"><div style="border:1.5px solid #C9CED6;border-radius:14px;'
            'padding:6px;background:#fff;height:%dpx;display:flex;flex-direction:column;justify-content:center">%s</div>'
            '<div style="text-align:center;font-size:11px;font-weight:700;margin-top:6px">%s</div></div>'
            % (int(total_h * scale) + 16, body, name))


def main():
    if len(sys.argv) != 2:
        print("用法: python gen_layouts.py <项目out目录>", file=sys.stderr)
        return 2
    out_dir = sys.argv[1]
    html_path = os.path.join(out_dir, "design-system.html")
    if not os.path.exists(html_path):
        print("[FAIL] 缺 %s" % html_path, file=sys.stderr)
        return 2
    html = io.open(html_path, encoding="utf-8").read()
    m = re.search(r'<section class="chapter" id="s2">(.*?)</section>', html, re.S)
    if not m:
        print("[skip] 无 s02 布局章")
        return 0
    s2 = m.group(1)
    # 插入式：线框区补充在九类布局区之前（不覆盖既有迷你页形态）
    i = s2.find("九类")
    if i < 0:
        print("[skip] 布局章无九类区（形态不同构），未改动")
        return 0
    if "gen_layouts" in s2:
        print("[skip] 线框区已存在（幂等跳过）")
        return 0
    cards = "".join(wireframe(n, rs) for n, rs in SKELETONS)
    new_block = ('<div class="block"><div class="spec-label">WIREFRAME · 九类骨架线框（gen_layouts 自动产出）</div>'
                 '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">%s</div>'
                 '<p class="note" style="margin-top:10px">线框=区域结构示意（自动产出）；'
                 "token 渲染迷你示例页由 agent 用产物归档组件拼装（见下方九类布局区）。</p></div>\n    " % cards)
    blk = s2.rfind('<div class="block">', 0, i)
    if blk < 0:
        print("[skip] 布局区边界定位失败", file=sys.stderr)
        return 0
    s2_new = s2[:blk] + new_block + s2[blk:]
    html = html[:m.start(1)] + s2_new + html[m.end(1):]
    io.open(html_path, "w", encoding="utf-8", newline="\n").write(html)
    print("[ok] 九类线框插入（迷你页拼装归 agent）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
