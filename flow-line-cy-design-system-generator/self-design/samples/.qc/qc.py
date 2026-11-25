# -*- coding: utf-8 -*-
"""sample-C.html QC v2: proper hierarchical XPath + UTF-8 report file."""
import re, sys, io
from lxml import html as LH

P = r"C:\Users\admin\.claude\skills\design-system-generator\self-design\samples\sample-C.html"
R = r"C:\Users\admin\.claude\skills\design-system-generator\self-design\samples\.qc\qc-report.txt"
raw = open(P, encoding="utf-8").read()
doc = LH.fromstring(raw)
buf = io.StringIO()
ok = True

def check(name, cond, detail=""):
    global ok
    buf.write(("PASS " if cond else "FAIL ") + name + ((" | " + str(detail)) if detail else "") + "\n")
    if not cond:
        ok = False

def T(tok):
    return "contains(concat(' ',normalize-space(@class),' '),' %s ')" % tok

# ---------- 1. structure ----------
cards = [c for c in doc.xpath("//*[%s]" % T("card")) if c.tag == "article"]
check("卡片数量 = 4", len(cards) == 4, len(cards))
for i, c in enumerate(cards, 1):
    swrs = c.xpath(".//*[%s]" % T("swr"))
    cells = c.xpath(".//*[%s]" % T("cell"))
    tags = c.xpath(".//*[%s]" % T("tag"))
    foot = c.xpath(".//*[%s]" % T("foot"))
    t1 = c.xpath(".//*[%s]" % T("t1")); t2 = c.xpath(".//*[%s]" % T("t2"))
    check(f"卡{i}: ramp{len(swrs)} 语义{len(cells)} 状态{len(tags)} 尾注{len(foot)} 字阶{len(t1)}/{len(t2)}",
          len(swrs) in (3, 5) and len(cells) == 8 and len(tags) == 3 and len(foot) == 1 and len(t1) == 1 and len(t2) == 1)
badges = doc.xpath("//*[%s]" % T("badge"))
check("已选定徽标 x1 且在卡2", len(badges) == 1 and (badges[0] in cards[1].xpath(".//*[%s]" % T("badge"))))
check("当前步实底块 x1", len(doc.xpath("//*[%s and %s]" % (T("step"), T("now")))) == 1)
check("顶栏品牌行逐字", doc.xpath("//*[%s]" % T("brand"))[0].text_content().strip() == "工作台自举 · 共创工作台")
chips_box = doc.xpath("//*[%s]" % T("chips"))[0]
chips = [x.text_content().strip() for x in chips_box.xpath("./*[%s]" % T("chip"))]
check("顶栏 chips 三枚逐字",
      any("决策链 v1" in x for x in chips) and any("第三步 设计令牌" in x for x in chips) and any("素材链接×4" in x for x in chips),
      chips)
tabs = [x.text_content().strip() for x in doc.xpath("//*[%s]" % T("tab"))]
check("Tab = 工作台/预览", tabs == ["工作台", "预览"], tabs)
rail = doc.xpath("//*[%s]" % T("rail"))[0]
steps = rail.xpath(".//*[%s]" % T("step"))
step_b = [s.xpath(".//b")[0].text_content().strip() for s in steps if "now" not in (s.get("class") or "").split()]
check("已完成步 3 项逐字", step_b == ["第〇步 画像", "第一步 外部输入", "第二步 风格定义层"], step_b)
now_b = [s for s in steps if "now" in s.get("class").split()][0]
check("当前步块标题逐字", now_b.xpath(".//b")[0].text_content().strip() == "第三步 设计令牌")
check("当前步副题逐字", now_b.xpath(".//small")[0].text_content().strip() == "靛蓝纸底撞色文气")
todo_lis = rail.xpath(".//ul/li")
todo = [x.text_content().strip() for x in todo_lis]
check("未至步 6 项逐字", todo == ["组件风格", "图片素材", "图标风格", "查漏", "样品页", "收尾"], todo)
check("未至步组标 3~8", "3~8" in rail.xpath(".//*[%s]" % T("todo-cap"))[0].text_content())
h1 = re.sub(r"\s+", "", doc.xpath("//h1")[0].text_content())
check("决策区标题 = 第三步设计令牌", h1 == "第三步设计令牌", h1)
mat_links = [a.text_content().strip() for a in doc.xpath("//*[%s]//a" % T("pop"))]
check("素材弹层 4 链接", len(mat_links) == 4 and all(l.endswith(".html") for l in mat_links), mat_links)

# ---------- 2. data fidelity vs chain.json ----------
expect_ramp = {
 1: ["#2C664F","#3D8B6E","#7FBFA4","#CDE7DC","#EAF4EF"],
 2: ["#3550C4","#4C6FFF","#8B9BFF","#D6DCFF","#EEF1FF"],
 3: ["#1F5C5C","#2E8B8B","#6FB3B3","#C2DEDE","#E9F3F3"],
 4: ["#5A8A5A","#C9A87C","#3F6640"],
}
expect_sem = {
 1: ["#2C664F","#3D8B6E","#7FBFA4","#FBFCFB","#F4F6F5","#26312C","#8A9791","#E4E9E7"],
 2: ["#3550C4","#4C6FFF","#8B9BFF","#FAFAF7","#F5F4F0","#23283B","#7C86A0","#E2E6F2"],
 3: ["#1F5C5C","#2E8B8B","#6FB3B3","#F8FAF9","#F0F4F4","#1F2E2E","#7E9696","#DDE8E8"],
 4: ["#3F6640","#5A8A5A","#C9A87C","#F7F6F2","#F2F0EA","#2A2E26","#8A9184","#E5E3DA"],
}
expect_stat = {
 1: ["#3D8B6E","#D9932C","#C75450"],
 2: ["#3D8B6E","#D9932C","#C75450"],
 3: ["#2E8B8B","#D9932C","#C75450"],
 4: ["#5A8A5A","#C9A87C","#C75450"],
}
names = ["雾青 · 同色系层次", "靛蓝纸底 · 撞色强调（文气）", "青瓷 · 邻近协调", "苔绿纸感 · 双色调 + 等宽"]
concepts = ["同色系层次 · 最贴「清新」本义", "撞色强调 · 暖纸底×冷靛蓝 · editorial 文气",
            "邻近色协调 · 比雾青冷半度 · 精密感", "双色调 · JetBrains Mono 强化代码块候选气质"]
def shx(el):
    m = re.search(r"#([0-9A-Fa-f]{6})", el.get("style") or "")
    return ("#" + m.group(1).upper()) if m else None
for i, c in enumerate(cards, 1):
    swrs = c.xpath(".//*[%s]" % T("swr"))
    ramp = [shx(w.xpath("./*[%s]" % T("sw"))[0]) for w in swrs]
    labs = [w.xpath("./*[%s]" % T("hx"))[0].text_content().strip().upper() for w in swrs]
    cells = c.xpath(".//*[%s]" % T("cell"))
    sem = [shx(x.xpath("./*[%s]" % T("sw"))[0]) for x in cells]
    roles = [x.xpath("./*[%s]" % T("role"))[0].text_content().strip() for x in cells]
    tags = c.xpath(".//*[%s]" % T("tag"))
    stat = [shx(t.xpath("./*[contains(@style,'background')][1]")[0]) for t in tags]
    stat_nm = [t.xpath("./*[%s]" % T("nm"))[0].text_content().strip() for t in tags]
    check(f"卡{i} 名称逐字", c.xpath(".//h3")[0].text_content().strip() == names[i - 1])
    check(f"卡{i} 概念句逐字", c.xpath(".//*[%s]" % T("cpt"))[0].text_content().strip() == concepts[i - 1])
    check(f"卡{i} ramp 逐字", ramp == [x.upper() for x in expect_ramp[i]], ramp)
    check(f"卡{i} ramp 标签=色块", labs == ramp, labs)
    check(f"卡{i} 语义8色逐字", sem == [x.upper() for x in expect_sem[i]], sem)
    check(f"卡{i} 语义角色顺序", roles == ["CTA", "主色", "次色", "底色", "面色", "正文", "次文", "边框"], roles)
    check(f"卡{i} 状态3色逐字", stat == [x.upper() for x in expect_stat[i]], stat)
    check(f"卡{i} 状态标签文案", stat_nm == ["成功", "警告", "危险"], stat_nm)
    check(f"卡{i} 尾注『选 {i}』", ("『选 %d』" % i) in c.xpath(".//*[%s]" % T("foot"))[0].text_content())
code_hexes = set(re.findall(r"#(?:FAFAF7|4C6FFF|3550C4|23283B|7C86A0|E2E6F2|3D8B6E|D9932C|C75450)",
                            doc.xpath("//*[%s]" % T("code-body"))[0].text_content()))
check("代码块 9 令牌齐全", len(code_hexes) == 9, sorted(code_hexes))
hint = doc.xpath("//*[%s]" % T("hint"))[0].text_content()
check("提示语含 选N/微调/再来一批/第四步", all(k in hint for k in ["选 N", "描述微调", "再来一批", "第四步"]))

# ---------- 3. locked token strings ----------
locked = ["#FAFAF7", "#4C6FFF", "#3550C4", "#23283B", "#7C86A0", "#E2E6F2", "#3D8B6E", "#D9932C", "#C75450",
          "rgba(255,255,255,.66)", "blur(10px)", "blur(12px)", "0 4px 16px rgba(35,40,59,.08)",
          "0 4px 12px rgba(76,111,255,.35)", "rgba(255,255,255,.38)", "Noto Serif SC", "Consolas",
          "『选 1』", "『选 2』", "『选 3』", "『选 4』", "思源宋", "思源黑"]
for s in locked:
    check("锁值/文案在稿: " + s, s in raw)

# ---------- 4. discipline audits ----------
css = re.search(r"<style>(.*?)</style>", raw, re.S).group(1)
sizes = sorted(set(float(m) for m in re.findall(r"font:\s*\w+\s+(\d+(?:\.\d+)?)px", css)))
scale = {28.0, 20.0, 16.0, 14.0, 12.5, 11.0, 32.0}
off = [s for s in sizes if s not in scale]
check("CSS 字阶全在档(28档C诠释至32)", not off, "sizes=%s off=%s" % (sizes, off))
inline_sizes = sorted(set(float(x) for x in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", raw)))
off2 = [s for s in inline_sizes if s not in scale]
check("内联字号在档", not off2, inline_sizes)
blurs = sorted(set(float(x) for x in re.findall(r"blur\((\d+(?:\.\d+)?)px\)", raw)))
check("blur 集合 = {6,10,12}面板 + {22,24,26}氛围", set(blurs) == {6.0, 10.0, 12.0, 22.0, 24.0, 26.0}, blurs)
atmo = re.findall(r"\.b\d\{.*?rgba\([^\)]*,\s*([\d.]+)\).*?blur\((\d+)px\)", css, re.S)
ops = [float(o) for o, b in atmo]; bl = [int(b) for o, b in atmo]
check("氛围斑 x4 · op .25-.30 · blur>=22", len(atmo) == 4 and all(.25 <= o <= .30 for o in ops) and all(b >= 22 for b in bl), list(zip(ops, bl)))
radii = sorted(set(float(x) for x in re.findall(r"border-radius:\s*(\d+(?:\.\d+)?)px", raw)))
check("圆角只用 6/8/10", set(radii) <= {6.0, 8.0, 10.0}, radii)
durs = sorted(set(round(float(x) * 10) for x in re.findall(r"animation:\s*fadeUp\s+\.?(\d+(?:\.\d+)?)s", css)))
check("动效 200-300ms", all(200 <= d <= 300 for d in durs), durs)
stag = sorted(set(float(x) if "." in x else float(x) / 100 for x in re.findall(r"animation-delay:\s*\.?(\d+(?:\.\d+)?)s", css)))
gaps = [round((b - a) * 1000) for a, b in zip(stag, stag[1:])]
check("stagger 相邻差 <= 40ms (delay 秒=%s)" % stag, all(g <= 40 for g in gaps), gaps)
mono_heads = re.findall(r"clamp|vw|vh", css)
check("无视差/大位移动画字样", "parallax" not in raw.lower())

# ---------- 5. width arithmetic @1440 ----------
content = 1240 - 64 - 264 - 24
cardw = (content - 20) / 2
inner = cardw - 48
cell = (inner - 4 * 7) / 8
hexw = 7 * 11 * 0.55
check("1440 语义格宽 %.1f >= hex 标签 %.1f" % (cell, hexw), cell >= hexw, "content=%d card=%.0f inner=%.0f" % (content, cardw, inner))
rampw = (inner - 6 * 4) / 5
check("1440 色阶格宽 %.1f >= hex %.1f" % (rampw, hexw), rampw >= hexw)

buf.write("\nQC " + ("ALL PASS" if ok else "HAS FAILURES") + "\n")
open(R, "w", encoding="utf-8").write(buf.getvalue())
sys.exit(0 if ok else 1)
