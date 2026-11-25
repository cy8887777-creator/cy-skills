# -*- coding: utf-8 -*-
"""模板案例 md 升级 v3：章节重排（先面后细再补充）+ 模式→设计要求两层化 + 禁令两层化 + 无障碍归位。幂等。"""
import io, os, re

MP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "templates", "system-rules.md")

MD_S4_HEAD = '''## 4. 设计要求（跨场景组装规则）

> 两层：概念性要求定方向（跨页面类型普遍成立），具体要求给做法（本系统沉淀）。页面骨架见 §2 布局。

### 概念性要求（理念层）

1. **信息密度与呼吸感按页面任务平衡**——聚焦型页面敢留白、立重心；列表型页面保密度、立节奏。
2. **视觉层级必须与信息层级一致**——重要的更大更醒目，次要的退后。
3. **一致性优先于个性**——同场景永远同样式。

### 具体要求（本系统沉淀）
'''

A11Y_REDLINE = '''
### 无障碍红线（自「无障碍验收」章归位）

1. **状态不只靠颜色**——信息不得仅靠颜色传达（状态配图标/文字）；自查：转灰度看信息是否仍完整。
2. **键盘可达**——可操作元素 Tab 可达、焦点可见（--focus-ring）、Modal 内 Esc 关闭；自查：拔鼠标走完流程。
3. **可读名称**——图标按钮必带 aria-label、图片有 alt、控件有 label；自查：开屏幕阅读器听一遍。
4. **减弱动效**——尊重 prefers-reduced-motion（动效章提供了实现代码）。
5. **禁 div 充当按钮**——无键盘语义；禁移除焦点描边而不提供替代。

对比度验收（归颜色章）：正文 ≥ 4.5:1；大字（≥18px 粗体）≥ 3:1；UI 部件描边 ≥ 3:1——取色器测前景/背景比对 WCAG 表。
'''

MD_S9 = '''## 9. 人看版产物结构（HTML 应有的 15 章）

`design-system.html` 单文件自包含（中文字体随产物打包于 `system-spec/fonts/`），章节固定（先面 → 再细 → 后补充）：

01 设计价值观 → 02 布局 → 03 多端适配 → 04 设计要求 → 05 颜色 → 06 字体 → 07 间距 → 08 圆角 → 09 阴影 → 10 动效 → 11 组件库 → 12 图标 → 13 素材资产 → 14 设计禁令 → 15 变更日志

每章固定四段式：**原则 → 作用 → 应用 → 使用规范**；token 展示一律实物化；Do-Don't 对比卡收尾。
'''

def main():
    md = io.open(MP, encoding="utf-8").read()
    if "## 4. 设计要求" in md:
        print("[skip] 模板 md 已是 v3 形态")
        return
    secs = {}
    for m in re.finditer(r"(?m)^## (\d+)\. ", md):
        n = int(m.group(1))
        start = m.start()
        rest = md[m.end():]
        nxt = re.search(r"(?m)^## \d+\. ", rest)
        end = m.end() + nxt.start() if nxt else len(md)
        secs[n] = md[start:end].rstrip() + "\n"
    assert set(secs) == set(range(11)), sorted(secs)
    head = md[:md.find("## 0.")]

    s0 = secs[0].replace("从 §2 token 表取值", "从 §5 token 表取值")
    s3 = secs[3].replace("## 3. 布局规则", "## 2. 布局规则")
    s4m = secs[4].replace("## 4. 多端差异规则", "## 3. 多端差异规则")
    # §4 设计要求 = 概念头 + 原 §7 模式规则的条目（作具体要求，降级为其小节）
    s7 = secs[7].replace("## 7. 模式规则（流程级）", "#### 具体要求（本系统沉淀 · 流程级组合）")
    s7 = s7.replace("§12", "§11")
    md_s4 = MD_S4_HEAD + "\n" + s7
    # §5 token：标题与子节号 + 颜色段尾对比度
    s5 = secs[2].replace("## 2. Token 全量参考", "## 5. Token 全量参考")
    s5 = re.sub(r"(?m)^### 2\.", "### 5.", s5)
    s5 = s5.replace("### 5.2 语义层",
                    "\n**对比度验收（A11Y 归位）**：正文 ≥ 4.5:1；大字（≥18px 粗体）≥ 3:1；UI 部件描边 ≥ 3:1。"
                    "自查：取色器测前景/背景比对 WCAG 表；页面转灰度看信息是否仍完整。\n\n### 5.2 语义层", 1)
    s6 = secs[6].replace("§12", "§11")
    s7icons = secs[5].replace("## 5. 图标与素材", "## 7. 图标与素材")
    s7icons = s7icons.replace("§10", "§12").replace("§11", "§13").replace("§12 陈列", "§12 陈列")
    # §8 设计禁令 = 概念头 + 原 §8 清单（作具体禁令）+ 无障碍红线
    s8old = secs[8].replace("## 8. 禁令清单（产出前逐条自查）",
                            "### 具体禁令（产出前逐条自查）")
    md_s8 = ("## 8. 设计禁令（产出前逐条自查）\n\n"
             "### 概念性禁令（理念层）\n\n"
             "1. **禁把信息撑得太满**——布局要有呼吸感，间距留足，页面要有清晰主次。\n"
             "2. **禁为留白牺牲信息密度**——列表页每行信息必须完整可扫。（与上条成对：两头都是极端）\n"
             "3. **禁让用户思考「这是什么」**——元素含义必须自明；图标必配文字标签。\n"
             "4. **禁一屏多主任务**——一屏一个主行动；浏览列表页禁塞竞争性 CTA。\n\n"
             + s8old + "\n" + A11Y_REDLINE)
    parts = [head, s0, secs[1], s3, s4m, md_s4, s5, s6, s7icons, md_s8, MD_S9]
    out = "\n\n".join(p.rstrip("\n") for p in parts) + "\n"
    out = out.replace("design-system-extract 产出案例", "design-system-extract 产出案例")
    io.open(MP, "w", encoding="utf-8", newline="\n").write(out)
    print("[ok] 模板 md v3：10 节新序 + 设计要求/禁令两层化 + 无障碍归位")

if __name__ == "__main__":
    main()
