"""
scripts/core/html_to_md.py — 从定案 design-system.html 派生 system-rules.md（AI 读规则版）

架构地位（v4.0）：HTML 是定案事实源；md 与 json 均为其派生视图（html_to_json.py 同理）。
用法（唯一）：python html_to_md.py <项目out目录>

生成映射（HTML 15 章 → md 10 节）：
  §0 使用方式（静态）/ §1←s1 价值观 / §2←s2 布局 / §3←s3 多端 / §4←s4 设计要求
  §5←s5 颜色（三段 token 表+对比度）+ s6-s10 实物行合成度量全量表
  §6←s11 组件概览表 / §7←s12 图标+s13 素材 / §8←s14 设计禁令（三层）/ §9 静态结构说明

诚实边界：规则散文（ch-intro / li / Do-Don't）原样文本化；实物演示剥离为值表。
生成后 agent 必须对照定案 HTML 校对一遍规则散文完整性（转换器保结构，agent 保语义）。
"""
import io
import json
import os
import re
import sys

from parse_common import txt, sec, lis, table_md, parse_keyed_table, parse_swatches, extract_metric_rows, metric_body

FLOOR_PX = 11.0


def _font_ok(tok, val):
    if not tok.startswith("--font-size"):
        return True
    m = re.match(r"([\d.]+)px", val or "")
    return not m or float(m.group(1)) >= FLOOR_PX


def blocks(sec_html):
    """[(label, block_html), ...]"""
    out = []
    for m in re.finditer(r'<div class="block">\s*<div class="spec-label">([^<]*)</div>(.*?)(?=<div class="block">|$)',
                         sec_html, re.S):
        out.append((txt(m.group(1)), m.group(2)))
    return out


def table_md(block):
    """HTML 表格 → md 表格文本；无表格返回 ''"""
    t = re.search(r"<table>(.*?)</table>", block, re.S)
    if not t:
        return ""
    head = [txt(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", t.group(1), re.S)]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", t.group(1), re.S):
        cells = [txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if cells:
            rows.append(cells)
    if not head:
        head = ["列%d" % (i + 1) for i in range(len(rows[0]) if rows else 0)]
    lines = ["| " + " | ".join(head) + " |",
             "|" + "---|" * len(head)]
    for r in rows:
        r = (r + [""] * len(head))[:len(head)]
        lines.append("| " + " | ".join(x.replace("|", "\\|") for x in r) + " |")
    return "\n".join(lines) + "\n"


def ul_md(items, numbered=False):
    if not items:
        return ""
    return "\n".join(("%d. %s" % (i + 1, x)) if numbered else ("- " + x)
                     for i, x in enumerate(items)) + "\n"


def dd_md(block):
    """Do/Don't 对比卡 → md 清单"""
    do = re.search(r'dd-head">DO[^<]*</div>\s*<ul>(.*?)</ul>', block, re.S)
    dont = re.search(r"dont[^>]*>\s*<div class=\"dd-head\">DON'T[^<]*</div>\s*<ul>(.*?)</ul>", block, re.S)
    out = []
    if do:
        out.append("**DO ✓**\n" + ul_md(lis(do.group(1))))
    if dont:
        out.append("**DON'T ✕**\n" + ul_md(lis(dont.group(1))))
    return "\n".join(out)


def usage_block(sec_html, heading="#### 使用规范"):
    for label, block in blocks(sec_html):
        if "USAGE" in label:
            body = dd_md(block)
            return heading + "\n\n" + body if body else ""
    return ""


def main():
    if len(sys.argv) != 2:
        print("用法: python html_to_md.py <项目out目录>", file=sys.stderr)
        return 2
    out_dir = sys.argv[1]
    html_path = os.path.join(out_dir, "design-system.html")
    if not os.path.exists(html_path):
        print("[FAIL] 定案 HTML 不存在: %s——先完成站④第 1 步" % html_path, file=sys.stderr)
        return 2
    html = io.open(html_path, encoding="utf-8").read()

    # meta
    hero = re.search(r'<header class="hero">(.*?)</header>', html, re.S).group(1)
    system = txt(re.search(r"<h1>(.*?)</h1>", hero, re.S).group(1))
    en = txt(re.search(r'<div class="h1-en">(.*?)</div>', hero, re.S).group(1))
    version = "v" + re.search(r"v([\d.]+)", en).group(1)
    date = ""
    dm = re.search(r'提取日期 DATE</span><span class="v">([\d-]+)', hero)
    if dm:
        date = dm.group(1)

    P = []
    P.append("# %s 设计系统规则 / %s Design System Rules" % (system, system))
    P.append("""> **产物定位**：本文件是设计系统的 **AI 可读规则版**（由定案 HTML 派生：html_to_md.py）。
> 人看版（含实物演示）见 `design-system.html`；机器版见 `system-rules.json`。
> 三者同源（定案 HTML），发现不一致以 HTML 为准并回改。""")

    # §0 静态
    P.append("""## 0. 使用方式（给 AI 的指令）

1. 生成 / 修改任何 UI 之前，**先读完本文件**，所有视觉决策从 token 表取值。
2. 表中不存在的值 = 禁止使用（不得自造颜色、字号、间距、圆角、阴影）。
3. 遇到规则未覆盖的场景：按价值观裁决，并把缺口记录回本文件。""")

    # §1 价值观 ← s1
    s1 = sec(html, "s1")
    vals = re.findall(r"<li><b>([^<]+)</b>\s*——\s*([^<]*)</li>", s1)
    P.append("## 1. 价值观（冲突裁决顺序）\n")
    P.append(" > ".join(txt(v[0]).split()[0] for v in vals) + "\n")
    for n, d in vals:
        P.append("- **%s** —— %s" % (txt(n), txt(d)))
    P.append("- 两条规则冲突时，选更符合靠前价值观的方案；新规则必须能追溯到这里，否则不立。")

    # §2 布局 ← s2 / §3 多端 ← s3 / §4 设计要求 ← s4
    for sid, num, title in (("s2", 2, "布局规则"), ("s3", 3, "多端差异规则")):
        sx = sec(html, sid)
        P.append("## %d. %s\n" % (num, title))
        intro = re.search(r'<p class="ch-intro">(.*?)</p>', sx, re.S)
        if intro:
            P.append("> " + txt(intro.group(1)) + "\n")
        for label, block in blocks(sx):
            if "USAGE" in label:
                continue
            body = table_md(block)
            P.append("### %s\n" % label)
            if body:
                P.append(body)
            li_items = lis(block)
            if li_items:
                P.append(ul_md(li_items))
        u = usage_block(sx)
        if u:
            P.append(u)

    s4 = sec(html, "s4")
    P.append("## 4. 设计要求（跨场景组装规则）\n")
    for label, block in blocks(s4):
        if "CONCEPTUAL" in label:
            P.append("### 概念性要求（理念层 · 跨页面类型普遍成立）\n" + ul_md(lis(block)))
        elif "SPECIFIC" in label:
            P.append("### 具体要求（本系统沉淀）\n" + ul_md(lis(block)))
        elif "USAGE" in label:
            P.append(dd_md(block))

    # §5 token ← s5 表格 + s6-s10 度量实物行
    s5 = sec(html, "s5")
    prim = []
    for m in re.finditer(r'<button class="swatch"[^>]*?data-hex="([^"]*)">(.*?)</button>', s5, re.S):
        nm = re.search(r'<span class="nm">([^<]*)</span>', m.group(2))
        hx = re.search(r'<span class="hx">(.*?)</span>', m.group(2), re.S)
        if nm:
            usage = re.sub(r"^#[0-9a-fA-F]{6}\s*·\s*", "", txt(hx.group(1))) if hx else ""
            prim.append((nm.group(1), m.group(1), usage))
    P.append("### 5.1 基础层 · 颜色（%d）\n" % len(prim))
    P.append("| Token | 值 | 用途 |\n|---|---|---|")
    for n, v, u in prim:
        P.append("| `--%s` | %s | %s |" % (n, v, u))

    def parse_semcomp(label_kw):
        blk = re.search(label_kw + r"[^<]*</div>(.*?</table>)", s5, re.S)
        return table_md(blk.group(1)) if blk else ""
    P.append("\n### 5.2 语义层\n\n" + parse_semcomp("SEMANTIC"))
    P.append("\n### 5.3 组件层\n\n" + parse_semcomp("COMPONENT"))
    # 度量：s6-s10 实物行（code 锚点，值=含单位的 b 或首个带·的值）
    metric, seen = [], set()
    body_all = "".join(sec(html, s) for s in ("s6", "s7", "s8", "s9", "s10"))
    for mm in re.finditer(r'<code[^>]*>(--(?:font-size|weight|line-height|space|padding|stroke|opacity|radius|shadow|z)-[\w.-]+)</code>', body_all):
        tok = mm.group(1)
        if tok in seen:
            continue
        nxt = re.search(r"<code[^>]*>--", body_all[mm.end():])
        win = body_all[mm.end(): mm.end() + (nxt.start() if nxt else 500)]
        text = txt(win).strip()
        bm = re.search(r"<b[^>]*>(.*?)</b>", win, re.S)
        bval = txt(bm.group(1)).strip() if bm else ""
        bval_ok = bval and re.search(r"px|%|ms\b|^\s*[\d.]+\s*$", bval) and re.search(r"\d", re.sub(r"Aa\s*\d+|跑腿", "", bval))
        if bval_ok and _font_ok(tok, bval):
            seen.add(tok)
            metric.append((tok, bval, re.sub(r"^[·\s]*", "", text.replace(bval, "", 1)).strip()))
            continue
        vm = re.search(r"([\d.]+(?:px|%|ms)?)\s*(（@2x\s*[\d.]+px）)?\s*·\s*(.*)", text)
        if vm:
            val = vm.group(1) + (("（@2x " + vm.group(2)[5:-1] + "）") if vm.group(2) else "")
            if not _font_ok(tok, val):
                continue
            seen.add(tok)
            metric.append((tok, val, vm.group(3).strip()))
            continue
        # 阴影实物行：值在实物 style 的 box-shadow 里（HTML 无文本值载体）
        if tok.startswith("--shadow-"):
            sm = re.search(r"box-shadow:\s*([^;\"]+)", win)
            if sm:
                seen.add(tok)
                usage = re.split(r"\s{2,}|\s·\s", text, maxsplit=1)[0]
                usage = re.sub(r"^--[\w.-]+\s*", "", usage).strip()
                metric.append((tok, " ".join(sm.group(1).split()), usage))
    # §5 标题 + 计数口径（counts 件核对依据；数字 = 本次实际解析值）
    _sem_tbl = parse_semcomp("SEMANTIC")
    _comp_tbl = parse_semcomp("COMPONENT")
    _n_sem = len([l for l in _sem_tbl.split("\n") if re.match(r"\|\s*--(?!-)", l)])
    _n_comp = len([l for l in _comp_tbl.split("\n") if re.match(r"\|\s*--(?!-)", l)])
    # 度量：完整小节优先复用 system-rules.json 的 tokens.metric（同为 HTML 派生物）；
    # HTML 实物行抓取作为无 json 时的兜底
    jpath = os.path.join(out_dir, "system-rules.json")
    jmetric = []
    if os.path.exists(jpath):
        try:
            jd = json.load(io.open(jpath, encoding="utf-8"))
            jmetric = [(t["token"], t["value"], t.get("usage", ""))
                       for t in jd.get("tokens", {}).get("metric", [])]
        except Exception:
            jmetric = []
    rows = [r for r in (jmetric if len(jmetric) >= len(metric) else metric) if _font_ok(r[0], r[1])]
    _n_total = len(prim) + _n_sem + _n_comp + len(rows)
    P.append("## 5. Token 全量参考（共 %d 个 · 四段口径）\n" % _n_total)
    P.append("> 计数口径：**基础 %d + 语义 %d + 组件 %d + 度量 %d = %d**；"
             "与 system-rules.json 的 tokens.count 同源（定案 HTML 派生）。\n"
             % (len(prim), _n_sem, _n_comp, len(rows), _n_total))
    P.append("### 5.1 基础层 · 颜色（%d）\n" % len(prim))
    P.append("| Token | 值 | 用途 |\n|---|---|---|")
    for n, v, u in prim:
        P.append("| `--%s` | %s | %s |" % (n, v, u))
    P.append("\n### 5.2 语义层（%d）\n\n%s" % (_n_sem, _sem_tbl))
    P.append("\n### 5.3 组件层（%d）\n\n%s" % (_n_comp, _comp_tbl))
    P.append("\n### 5.4 度量（%d）\n" % len(rows))
    P.append("| Token | 值 | 场景 |\n|---|---|---|")
    for tok, v, u in rows:
        P.append("| `%s` | %s | %s |" % (tok, v, u))

    ct = re.search(r'CONTRAST[^<]*</div>\s*<table>(.*?)</table>', s5, re.S)
    if ct:
        P.append("\n**对比度实测（A11Y 归位）**：\n\n" + table_md(ct.group(1)))

    # §6 组件 ← s11 组卡
    s11 = sec(html, "s11")
    P.append("## 6. 组件契约（%d 组 · 概览）\n" % len(re.findall(r'<b style="font-size:15px">\d+\.', s11)))
    P.append("> 每组件四要素：变体 / 状态 / 关键规格 / 使用说明 / 来源标注。完整实物演示见 HTML §11。\n")
    P.append("| 组件 | 来源标注 |\n|---|---|")
    for m in re.finditer(r'<b style="font-size:15px">(\d+)\. ([^<]+)</b>\s*<span[^>]*>(\w+)</span>(.*?)(?=<div style="border:1px solid #E9ECF1;border-radius:16px;overflow:hidden;flex:1;min-width:460px|$)', s11, re.S):
        badge = re.search(r"(已提取[^<]*|AI 补全[^<]*)", m.group(4))
        P.append("| **%s**（%s） | %s |" % (m.group(3), txt(m.group(2)),
                                            txt(badge.group(1)) if badge else "—"))

    # §7 图标与素材 ← s12 + s13
    s12, s13 = sec(html, "s12"), sec(html, "s13")
    P.append("## 7. 图标与素材\n")
    P.append("> 图标章与素材章的规则与资产索引；实物陈列见 HTML §12/§13。\n")
    for sx, kw in ((s12, "图标"), (s13, "素材")):
        intro = re.search(r'<p class="ch-intro">(.*?)</p>', sx, re.S)
        if intro:
            P.append("- **%s**：%s" % (kw, txt(intro.group(1))))
    u12 = usage_block(s12)
    if u12:
        P.append(u12)

    # §8 设计禁令 ← s14（三层）
    s14 = sec(html, "s14")
    P.append("## 8. 设计禁令（产出前逐条自查）\n")
    for label, block in blocks(s14):
        if "CONCEPTUAL" in label:
            P.append("### 概念性禁令（理念层）\n" + ul_md(lis(block)))
        elif "SPECIFIC" in label:
            P.append("### 具体禁令\n" + ul_md(lis(block), numbered=True))
        elif "A11Y" in label:
            P.append("### 无障碍红线（自 A11Y 归位）\n" + ul_md(lis(block)))
        elif "USAGE" in label:
            P.append(dd_md(block))

    # §9 静态
    P.append("""## 9. 人看版产物结构

`design-system.html` 单文件自包含（字体随产物打包于 `system-spec/fonts/`），
15 章：01 设计价值观 → 02 布局 → 03 多端适配 → 04 设计要求 → 05 颜色 → 06 字体 → 07 间距
→ 08 圆角 → 09 阴影 → 10 动效 → 11 组件库 → 12 图标 → 13 素材资产 → 14 设计禁令 → 15 变更日志。""")

    out = "\n\n".join(x.rstrip("\n") for x in P if x and x.strip()) + "\n"
    out = out.replace("%s。" % date, date and ("%s。" % date) or "", 0) if False else out
    dest = os.path.join(out_dir, "system-rules.md")
    io.open(dest, "w", encoding="utf-8", newline="\n").write(out)
    print("[ok] system-rules.md 派生：%d 字（%d 度量行 / %d 组件组）"
          % (len(out), len(rows), len(re.findall(r'\| \*\*\w+\*\*', out))))
    print("[校对] 规则散文已结构化带出；agent 交付前对照定案 HTML 过一遍语义完整性。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
