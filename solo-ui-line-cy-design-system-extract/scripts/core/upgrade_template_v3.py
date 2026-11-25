# -*- coding: utf-8 -*-
"""模板案例 HTML 升级 v3：16→15 章重排 + 模式/反模式两层化（设计要求/设计禁令）+ A11Y 归位
+ 字体自托管 + 图标使用形态块 + 剪贴板降级。幂等（REQUIREMENTS 标记检测）。"""
import io, os, re

T = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "templates", "system-spec")
HP = os.path.join(T, "design-system.html")

FONT_FACE = '''
  /* 自托管字体（随产物打包于 fonts/ · OFL 许可） */
  @font-face { font-family: "Noto Sans SC"; font-style: normal; font-weight: 400; font-display: swap; src: url("fonts/noto-sans-sc-chinese-simplified-400-normal.woff2") format("woff2"); }
  @font-face { font-family: "Noto Sans SC"; font-style: normal; font-weight: 500; font-display: swap; src: url("fonts/noto-sans-sc-chinese-simplified-500-normal.woff2") format("woff2"); }
  @font-face { font-family: "Noto Sans SC"; font-style: normal; font-weight: 700; font-display: swap; src: url("fonts/noto-sans-sc-chinese-simplified-700-normal.woff2") format("woff2"); }
  @font-face { font-family: "Inter"; font-style: normal; font-weight: 400; font-display: swap; src: url("fonts/inter-latin-400-normal.woff2") format("woff2"); }
  @font-face { font-family: "Inter"; font-style: normal; font-weight: 700; font-display: swap; src: url("fonts/inter-latin-700-normal.woff2") format("woff2"); }
'''

NEW_NAV = '''  <nav class="nav">
    <a href="#s1"><span class="no">01</span>设计价值观<span class="en">VALUES</span></a>
    <a href="#s2"><span class="no">02</span>布局<span class="en">LAYOUT</span></a>
    <a href="#s3"><span class="no">03</span>多端适配<span class="en">PLATFORMS</span></a>
    <a href="#s4"><span class="no">04</span>设计要求<span class="en">REQUIREMENTS</span></a>
    <a href="#s5"><span class="no">05</span>颜色<span class="en">COLOR</span></a>
    <a href="#s6"><span class="no">06</span>字体<span class="en">TYPE</span></a>
    <a href="#s7"><span class="no">07</span>间距<span class="en">SPACING</span></a>
    <a href="#s8"><span class="no">08</span>圆角<span class="en">RADIUS</span></a>
    <a href="#s9"><span class="no">09</span>阴影<span class="en">SHADOW</span></a>
    <a href="#s10"><span class="no">10</span>动效<span class="en">MOTION</span></a>
    <a href="#s11"><span class="no">11</span>组件库<span class="en">COMPONENTS</span></a>
    <a href="#s12"><span class="no">12</span>图标<span class="en">ICONS</span></a>
    <a href="#s13"><span class="no">13</span>素材资产<span class="en">ASSETS</span></a>
    <a href="#s14"><span class="no">14</span>设计禁令<span class="en">DON'T</span></a>
    <a href="#s15"><span class="no">15</span>变更日志<span class="en">CHANGELOG</span></a>
  </nav>'''

ORDER = [1, 8, 9, 13, 2, 3, 4, 5, 6, 7, 12, 10, 11, 14, 16]
NAMES = {1: "设计价值观", 8: "布局", 9: "多端适配", 13: "设计要求", 2: "颜色", 3: "字体",
         4: "间距", 5: "圆角", 6: "阴影", 7: "动效", 12: "组件库", 10: "图标",
         11: "素材资产", 14: "设计禁令", 16: "变更日志"}

def fix_chapter(sec, old_id):
    if old_id == 13:  # 模式 → 设计要求（两层）：前插概念块，原四模式块即具体要求
        sec = re.sub(r'<h2>模式<span class="en">PATTERNS</span></h2>',
                     '<h2>设计要求<span class="en">REQUIREMENTS</span></h2>', sec)
        sec = sec.replace('<p class="ch-intro">组件之上的流程级组合：表单、列表、加载、危险操作。照模式拼页面，不重新发明。</p>',
                          '<p class="ch-intro">跨场景的组装规则，分两层：概念性要求定方向（跨页面类型普遍成立），具体要求给做法（本系统沉淀）。页面骨架归 §02 布局。</p>')
        concept = ('<div class="block"><div class="spec-label">CONCEPTUAL · 概念性要求（理念层 · 跨页面类型成立）</div><ul class="plain">'
                   '<li><b>信息密度与呼吸感按页面任务平衡</b> —— 聚焦型页面敢留白、立重心；列表型页面保密度、立节奏。</li>'
                   '<li><b>视觉层级必须与信息层级一致</b> —— 重要的更大更醒目，次要的退后。</li>'
                   '<li><b>一致性优先于个性</b> —— 同场景永远同样式。</li></ul></div>\n    <div class="block">'
                   '<div class="spec-label">SPECIFIC · 具体要求（本系统沉淀）</div></div>\n    ')
        sec = sec.replace('<div class="block">\n      <div class="spec-label">FORM · 表单流程</div>', concept + '<div class="block">\n      <div class="spec-label">FORM · 表单流程</div>', 1)
    if old_id == 14:  # 反模式 → 设计禁令（两层）：前插概念块，尾插无障碍红线
        sec = re.sub(r'<h2>反模式<span class="en">[^<]*</span></h2>',
                     "<h2>设计禁令<span class=\"en\">DON'T LIST</span></h2>", sec)
        concept = ('<div class="block"><div class="spec-label">CONCEPTUAL · 概念性禁令（理念层）</div><ul class="plain">'
                   '<li><b>禁把信息撑得太满</b> —— 布局要有呼吸感，间距留足，页面要有清晰主次。</li>'
                   '<li><b>禁为留白牺牲信息密度</b> —— 列表页每行信息必须完整可扫。（与上条成对：两头都是极端）</li>'
                   '<li><b>禁让用户思考「这是什么」</b> —— 元素含义必须自明；图标必配文字标签。</li>'
                   '<li><b>禁一屏多主任务</b> —— 一屏一个主行动；浏览列表页禁塞竞争性 CTA。</li></ul></div>\n    ')
        m = re.search(r'(<div class="block">\s*<div class="spec-label">TOP 8)', sec)
        assert m, "s14 TOP8 锚点缺失"
        sec = sec[:m.start(1)] + concept + sec[m.start(1):]
        a11y = ('<div class="block"><div class="spec-label">A11Y · 无障碍红线（自「无障碍」章归位）</div><ul class="plain">'
                '<li><b>状态不只靠颜色</b> —— 信息不得仅靠颜色传达（状态配图标/文字）；自查：转灰度看信息是否完整。</li>'
                '<li><b>键盘可达</b> —— 可操作元素 Tab 可达、焦点可见（--focus-ring）、Modal 内 Esc 关闭；自查：拔鼠标走完流程。</li>'
                '<li><b>可读名称</b> —— 图标按钮必带 aria-label、图片有 alt、控件有 label；自查：开屏幕阅读器听一遍。</li>'
                '<li><b>禁 div 充当按钮</b> —— 无键盘语义；禁移除焦点描边而不提供替代。</li></ul></div>')
        sec = sec.rstrip() + "\n    " + a11y + "\n"
    if old_id == 2:  # 颜色章：USAGE 前插对比度验收块
        contrast = ('<div class="block"><div class="spec-label">CONTRAST · 对比度验收（A11Y 归位）</div><ul class="plain">'
                    '<li>正文 ≥ 4.5:1；大字（≥18px 粗体）≥ 3:1；UI 部件描边 ≥ 3:1。</li>'
                    '<li>自查：取色器测前景/背景比对 WCAG 表；页面转灰度看信息是否仍完整。</li></ul></div>\n    ')
        m = re.search(r'(<div class="block">\s*<div class="spec-label">USAGE)', sec)
        assert m, "s2 USAGE 锚点缺失"
        sec = sec[:m.start(1)] + contrast + sec[m.start(1):]
    if old_id == 12:  # 组件章：USAGE 前插触控热区（A11Y 归位：键盘可达的实现载体）
        touch = ('<div class="block"><div class="spec-label">A11Y · 键盘与焦点（自「无障碍」章归位）</div><ul class="plain">'
                 '<li>所有可操作元素 Tab 可达；焦点可见（--focus-ring）；Modal 内 Esc 关闭、焦点困住。</li>'
                 '<li>自查：拔掉鼠标走完整个流程。</li></ul></div>\n    ')
        m = re.search(r'(<div class="block">\s*<div class="spec-label">USAGE)', sec)
        if m:
            sec = sec[:m.start(1)] + touch + sec[m.start(1):]
    return sec

def main():
    h = io.open(HP, encoding="utf-8").read()
    if 'REQUIREMENTS' in h:
        print("[skip] 模板 HTML 已是 v3 形态")
        return
    # 备份
    bak = HP + ".bak-v3"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="\n").write(h)

    # 1. 字体
    h = h.replace("<style>", "<style>\n" + FONT_FACE, 1)
    # 2. 提取 16 章
    chapters = {}
    for m in re.finditer(r'<section class="chapter" id="s(\d+)">(.*?)</section>', h, re.S):
        chapters[int(m.group(1))] = m.group(0)
    assert len(chapters) == 16, len(chapters)
    chapters = {k: fix_chapter(v, k) for k, v in chapters.items()}
    # 3. 重排 + 重编号（占位符两步法，含完整 id 属性）
    parts = []
    for new_i, old in enumerate(ORDER, 1):
        sec = chapters[old]
        sec = re.sub(r'id="s\d+"', '@@SID%d@@' % new_i, sec)
        sec = re.sub(r'<span class="ch-num">\d+</span>', '<span class="ch-num">%02d</span>' % new_i, sec)
        parts.append('<!-- ============ %02d %s ============ -->\n  %s' % (new_i, NAMES[old], sec))
    body = '\n\n  '.join(parts) + '\n\n'
    for i in range(1, 16):
        body = body.replace('@@SID%d@@' % i, 'id="s%d"' % i)
    p1 = h.find('<!-- ============')
    p2 = h.find('<footer')
    assert 0 < p1 < p2
    h = h[:p1] + body + h[p2:]
    # 4. 导航
    h = re.sub(r'  <nav class="nav">.*?</nav>', NEW_NAV.replace('\\', '\\\\'), h, count=1, flags=re.S)
    # 5. 剪贴板降级（delivery 件）
    if 'execCommand' not in h and 'navigator.clipboard' in h:
        helper = ('function copyToClipboard(t, ok, fail) {\n'
                  '  function legacy() {\n'
                  '    var ta = document.createElement(\'textarea\');\n'
                  '    ta.value = t; ta.style.cssText = \'position:fixed;opacity:0\';\n'
                  '    document.body.appendChild(ta); ta.select();\n'
                  '    var done = false;\n'
                  '    try { done = document.execCommand(\'copy\'); } catch (e) {}\n'
                  '    document.body.removeChild(ta);\n'
                  '    done ? ok() : (fail || function () {}());\n'
                  '  }\n'
                  '  if (navigator.clipboard && navigator.clipboard.writeText) {\n'
                  '    navigator.clipboard.writeText(t).then(ok, legacy);\n'
                  '  } else { legacy(); }\n'
                  '}\n')
        k = h.find('navigator.clipboard.writeText')
        assert k > 0
        # 在第一个 clipboard 调用的 script 块开头注入 helper：向前找最近的 <script>
        s = h.rfind('<script>', 0, k)
        h = h[:s + len('<script>')] + '\n' + helper + h[s + len('<script>'):]
        # 所有 clipboard.writeText 调用改为 copyToClipboard
        h = re.sub(r'navigator\.clipboard\.writeText\(([^)]+)\)\.then\(', r'copyToClipboard(\1, function () { ', h)
    io.open(HP, "w", encoding="utf-8", newline="\n").write(h)
    print("[ok] 模板 HTML v3：15 章重排 + 两层化 + A11Y 归位 + 字体 + 剪贴板降级")

if __name__ == "__main__":
    main()
