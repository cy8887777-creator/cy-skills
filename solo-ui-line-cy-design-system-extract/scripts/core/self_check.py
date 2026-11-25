"""
scripts/core/self_check.py — 自检十三件套（真实项目唯一守门员；v4.1 双线合流版）

用法（唯一合法调用）：
    python self_check.py <项目out目录> [--expect-total N]

  - <项目out目录> 必填：本次**项目产物**所在的 out/ 目录。无默认路径——
    （历史教训：脚本曾硬编码读技能自身演示目录，真实项目上永远假绿，Ludo 事故自招）。
  - --expect-total N 可选：仅演示案例回归用（合流版案例传 134）。真实项目一律不传——
    **134/33 是案例实测参考值，不是及格线**，项目计数以实测为准。

输入：<dir>/design-system.html  <dir>/system-rules.md  <dir>/system-rules.json

十三件套（11 件 v4 线 + 2 件 2026-10-24 Ludo 整改线合流）：
  1 counts           4 段实测相加 = md 声明 = HTML 声明（三份自洽）
  2 anchors          HTML 侧边栏锚点 href ↔ id 动态互验
  3 contradictions   历史矛盾条文扫描（剔除反模式章与禁令章）
  4 raw_values       裸 hex / 阶梯外字号——白名单 = **本项目** normalized token 值 + 文档排版白名单
                     （演示品牌色已从白名单移除：其他项目带演示蓝 = 品牌污染 = REVIEW）
  5 features         功能存活清单（案例 7 项交互资产，防手搓生成器丢功能）
                   + 名实一致（颜色词命名必须与色相相符——粉不许叫 blue）
  6 gradient_truth   渐变 ground truth 回源（需 --source-dir）
  7 doc_contrast     文档可读性 gate（真实 CSS 底/字配对 WCAG 对比度）
  8 source_audit     溯源审计（「值 … N 处」回源核对，需 --source-dir）
  9 css_syntax       CSS 语法与文件头完整性
  10 delivery        交付自包含与交互降级
  11 workspace       交付区卫生（过程留物必须进 work/）
  12 assets_registry 素材登记对账（normalized.assets 插画 ↔ md 素材章，10/24 线）
  13 template_form   模板形态对照（templates 逐章签名 ↔ 产物 diff，10/24 线）

退出码：0 全 PASS / 1 有 REVIEW（必须升级人决，不得宣称完成）/ 2 参数或文件缺失
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import glob as _glob
import os as _os

# 历史矛盾规则（10 条）。原 15 条中的两类案例槽位绑定规则已移除：
#   - "Token 总数 32/64/78" 计数条 → 由 counts 三份自洽检查取代（真实项目不受定值约束）
#   - 4 条"禁裸 hex（演示 token 名引用）"条 → 并入 raw_values 动态白名单（更通用）
CONTRADICTION_RULES = [
    (r"输入框.*?圆角.*?sm\b|输入框.*?圆角.*?4px", "rule #1: 输入框圆角应统一为 md（8px）"),
    (r"弹层.*?动效.*?250ms|Modal.*?250ms", "rule #2: 弹层动效应为 400ms slow 档"),
    (r"字重.*?只用两档|字重.*?两档 400/600", "rule #3: 字重三档 400/600/700"),
    (r"行高\s*1\.5\b|line-height:\s*1\.5;", "rule #4: 正文行高应为 1.6"),
    (r"内边距\s*7px\s*20px|padding:\s*7px\s*20px", "rule #5: 按钮内边距应为 7px 18px"),
    (r"左上光源|left.*?light", "rule #11: 阴影应为顶部光源（x 偏移恒为 0）"),
    (r"只用两档\s*400\b", "rule #3 重检: 字重三档"),
    (r"同一视图.*?双 primary|双 primary 按钮", "rule #13: 一视图一主按钮"),
    (r"高危操作.*?文字按钮.*?替代|高危.*?无替代", "rule #14: 高危操作必须有 danger 替代变体"),
    (r"颜色仅.*?红|仅变红|仅靠颜色|单通道", "rule #15: 状态多通道传达（WCAG 1.4.1）"),
]

# 文档自身排版色（模板皮肤：纸感底 / 墨色 / 格线——不是项目色，允许出现）
RAW_DOC_HEXES = {
    "#f7f6f3", "#1c1d21", "#6b6d74", "#e3e1db", "#16181d", "#d8d9dd",
    "#8b8e96", "#9a9da5", "#55585f", "#63666e", "#edece8", "#ffffff", "#000000",
    "#c9ced6", "#b91c1c", "#9ca3af",  # 生成器结构色（占位虚线/禁令红/占位灰）
    "#eef2f7", "#dde3ea", "#7a8699",  # 线框插图三色（区域块/描边/标注灰）
}
# 注：演示品牌色（#3056d3 等 19 个）原藏在静态白名单里，现全部移除。
# 真实项目只要自己的 normalized 里没有该值，出现 ≥3 次即判品牌污染。
# 演示案例仍天然 PASS——因为它的 normalized 本来就含这些值。

# 文档自身排版字号白名单（注释 / 标签 / 网格标尺 / 骨架线框微缩标注 / hero 大数字等演示层）
DOC_SELF_SIZES = {
    "7px", "9px", "10px", "11px", "13px", "15px", "46px", "10.5px", "6px", "18px", "10.6px",
    "13.5px", "12.5px", "9.5px", "11.5px",
    "30px", "34px", "36px", "38px", "40px", "64px", "52px",
}

# 案例功能清单（人看版的交互资产——生成阶段丢失任何一项都算 REVIEW）
FEATURE_MARKERS = [
    ("侧边栏章节高亮", r"IntersectionObserver"),
    ("色板点击复制", r"clipboard|execCommand"),
    ("浅色棋盘底", r"\bchecker\b"),
    ("间距实物尺", r"gap-demo"),
    ("真实交互组件", r"addEventListener"),
    ("图标生成提示词母版", r"提示词母版|生成提示词"),
    ("三端差异矩阵", r"三端"),
]

COLOR_WORD_MAP = {
    "red": "red", "orange": "orange", "amber": "orange", "yellow": "yellow",
    "lime": "green", "green": "green", "teal": "cyan", "cyan": "cyan",
    "sky": "blue", "blue": "blue", "indigo": "blue", "violet": "purple",
    "purple": "purple", "pink": "pink", "rose": "pink",
}
HUE_BINS = [("red", 15), ("orange", 45), ("yellow", 70), ("green", 160),
            ("cyan", 200), ("blue", 258), ("purple", 295), ("pink", 345)]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def load_norm(p: Path):
    """v4：normalized 是过程数据归 work/——out 根缺失时回退 work/normalized.json"""
    if not p.exists():
        alt = p.parent / "work" / "normalized.json"
        if alt.exists():
            p = alt
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def norm_values(norm):
    """提取本项目 token 值中出现的全部 hex + px 尺寸（动态白名单）"""
    hexes, sizes = set(), set()
    if not norm:
        return hexes, sizes
    for seg in ("primitive", "semantic", "component", "metric"):
        for v in norm.get("tokens", {}).get(seg, {}).values():
            val = v.get("value", "") if isinstance(v, dict) else str(v)
            hexes |= {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", str(val))}
            sizes |= set(re.findall(r"[\d.]+px", str(val)))
            if seg == "metric":
                # 无单位裸数字也算尺寸（如 "14/22/400"、"9999"、"1.45"→无 px 的字号 token）
                for num in re.findall(r"\d+(?:\.\d+)?", str(val)):
                    sizes.add(f"{num}px")
    return hexes, sizes


def hue_family(value):
    """#rrggbb → 色相家族；近灰返回 None（不判）"""
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", str(value).strip())
    if not m:
        return None
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 0.12:
        return None
    if mx == mn:
        return None
    if mx == r:
        h = ((g - b) / (mx - mn)) % 6
    elif mx == g:
        h = (b - r) / (mx - mn) + 2
    else:
        h = (r - g) / (mx - mn) + 4
    deg = h * 60
    for fam, hi in HUE_BINS:
        if deg < hi:
            return fam
    return "red"


def check_counts(norm, md, html, expect_total, out_dir=None):
    """件套 1：4 段实测相加 = md 声明 = HTML 声明 = json 计数（三构造对账，不校验等于定值）"""
    issues = []
    total = None
    if norm:
        seg = {s: len(norm.get("tokens", {}).get(s, {}))
               for s in ("primitive", "semantic", "component", "metric")}
        # 字体下限合并（输出规则 8）：normalized 中 @2x 折 1x <11px 的 metric 档不进交付构造，
        # 交付总数 = 提取总数 - 低档数（差值可解释即不算不一致）
        n_low = 0
        for k, v in (norm.get("tokens", {}).get("metric", {}) or {}).items():
            if k.startswith("font-size"):
                val = (v or {}).get("value", "") if isinstance(v, dict) else str(v)
                m = re.match(r"([\d.]+)px", str(val))
                if m and float(m.group(1)) / 2 < 11:
                    n_low += 1
        total = sum(seg.values()) - n_low
        if expect_total is not None and total != expect_total:
            issues.append(f"--expect-total={expect_total}，实测 {total}（{seg}）")
    md_declared = set()
    for m in re.finditer(r"共\s*(\d+)\s*个\s*·?\s*四段口径", md):
        md_declared.add(int(m.group(1)))
    for m in re.finditer(r"度量\s*\d+\s*=\s*\*{0,2}(\d+)", md):
        md_declared.add(int(m.group(1)))
    html_declared = {int(x) for x in re.findall(r"Token\s*\d+", html) for x in [re.search(r"\d+", x).group()]}
    if total is None:
        issues.append("缺 normalized.json——计数无事实源，只能核 md/HTML 互自洽")
        if len(md_declared | html_declared) > 1:
            issues.append(f"md/HTML 声明不一致：{sorted(md_declared | html_declared)}")
        return False, issues
    for d in sorted(md_declared):
        if d != total:
            issues.append(f"md 声明 {d} ≠ 4 段实测总数 {total}")
    for d in sorted(html_declared):
        if d != total:
            issues.append(f"HTML 声明 Token {d} ≠ 实测总数 {total}")
    if not md_declared:
        issues.append('md 未声明「共 N 个 · 四段口径」')

    # 字体档位下限（输出规则 8）：font-size token 折 1x 后 <11px = REVIEW。
    # 口径注意：normalized 是过程数据存 @2x 原值（÷2 后比）；交付构造 md/json 主值已是 1x
    if norm:
        for seg in ("metric", "semantic"):
            for k, v in (norm.get("tokens", {}).get(seg, {}) or {}).items():
                if k.startswith("font-size"):
                    val = (v or {}).get("value", "") if isinstance(v, dict) else str(v)
                    m = re.match(r"([\d.]+)px", str(val))
                    if m and float(m.group(1)) / 2 < 11:
                        print(f"[INFO] 提取记录 {k} = {m.group(1)}px(@2x) 折 1x {float(m.group(1))/2:g}px "
                              f"低于可读下限——忠实保留于过程数据；交付构造不得立此档")
    # 三构造对账：system-rules.json（若已派生）tokens.count 必须同数 + 字体档下限（主值已 1x）
    if out_dir is not None and total is not None:
        jpath = Path(out_dir) / "system-rules.json"
        if jpath.exists():
            try:
                jd = json.loads(jpath.read_text(encoding="utf-8"))
                jcount = jd.get("tokens", {}).get("count")
                if jcount != total:
                    issues.append(f"system-rules.json tokens.count {jcount} ≠ 实测 {total}（派生不同步）")
                for r in jd.get("tokens", {}).get("metric", []):
                    m = re.match(r"([\d.]+)px", r.get("value", ""))
                    if r.get("token", "").startswith("--font-size") and m and float(m.group(1)) < 11:
                        issues.append(f"字体档 {r['token']} = {m.group(1)}px(1x) 低于可读下限 11px")
            except Exception as e:
                issues.append(f"system-rules.json 解析失败: {e}")
    return len(issues) == 0, issues


def check_anchors(md, html):
    """件套 2：侧边栏锚点动态互验——href ↔ id 双向配对 + 编号连续，不写死章数（规范演进自动跟随）"""
    issues = []
    sidebar = re.search(r'<nav class="nav">(.*?)</nav>', html, re.DOTALL)
    if not sidebar:
        return False, ['未找到 <nav class="nav"> 侧边栏块']
    hrefs = sorted(set(re.findall(r'href="#(s\d+)"', sidebar.group(1))), key=lambda x: int(x[1:]))
    ids = sorted(set(re.findall(r'<section class="chapter" id="(s\d+)"', html)), key=lambda x: int(x[1:]))
    if not ids:
        return False, ['未找到任何章节 section']
    orphan_ids = [i for i in ids if i not in hrefs]
    dead_hrefs = [a for a in hrefs if f'id="{a}"' not in html]
    if dead_hrefs:
        issues.append(f"导航死链（href 无对应章节）: {dead_hrefs}")
    if orphan_ids:
        issues.append(f"孤儿章节（未被导航引用）: {orphan_ids}")
    nums = [int(x[1:]) for x in ids]
    expect = list(range(1, len(nums) + 1))
    if nums != expect:
        issues.append(f"章节编号不连续: 实际 {nums}，应为 {expect}")
    if len(hrefs) != len(ids):
        issues.append(f"导航项 {len(hrefs)} ≠ 章节数 {len(ids)}")
    return len(issues) == 0, issues


def check_contradictions(md, html):
    """件套 3：历史矛盾正则扫描（剔除 token 定义行 / CSS 代码 / 禁令章 / 无障碍红线的否定式表述）"""
    html_no_css = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    html_no_css = re.sub(r'style="[^"]*"', "", html_no_css)
    # 产物章体常为单行——按块切行，防正则跨卡误伤（Input 卡的"输入框"连到远处 Card 的 shadow-sm）
    html_no_css = re.sub(r"</div>", "</div>\n", html_no_css)
    text = md + "\n" + html_no_css
    cleaned_lines = []
    in_antipatterns = False
    in_skip_md = False
    for line in text.split("\n"):
        m_start = re.search(r"<!--\s*=+\s*\d+\s+(反模式|设计禁令)\s+=+\s*-->", line)
        m_next = re.search(r"<!--\s*=+\s*(1[5-9]|[2-9]\d+)\s+", line)
        if m_start:
            in_antipatterns = True
            continue
        if in_antipatterns:
            if m_next:
                in_antipatterns = False
            else:
                continue
        if re.search(r"^\s*##\s*\d+\.\s*(禁令清单|设计禁令)", line):
            in_skip_md = True
        if re.search(r"^\s*##\s*\d+\.\s*人看版", line):
            in_skip_md = False
        if in_skip_md:
            continue
        if re.search(r"不得仅靠颜色|不只靠颜色|状态多通道|禁.*仅靠颜色|传达错误", line):
            continue
        if re.search(r"`--[a-z][a-z0-9-]+`", line):
            continue
        if re.search(r"--[a-z][a-z0-9-]+:\s*#", line):
            continue
        if re.search(r"<code>#[0-9a-fA-F]{6}</code>|裸 hex", line):
            continue
        if re.search(r'data-hex="#', line):
            continue
        if re.search(r":\s*#[0-9a-fA-F]{6}\b", line):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    issues = []
    for pattern, rule in CONTRADICTION_RULES:
        if re.search(pattern, cleaned, re.IGNORECASE):
            issues.append(f"命中矛盾: {rule}")
    return len(issues) == 0, issues


def check_raw_values(norm, md, html):
    """件套 4：裸值扫描——白名单 = 本项目 token 值 + 文档排版白名单"""
    text = md + "\n" + html
    issues = []
    allowed_hex, allowed_sizes = norm_values(norm)
    allowed_hex |= RAW_DOC_HEXES
    allowed_sizes |= DOC_SELF_SIZES

    found = [h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", text)]
    c = Counter(h for h in found if h not in allowed_hex)
    for h, n in c.most_common():
        if n >= 3:
            issues.append(f"hex {h} 出现 {n} 次且不在本项目 token 白名单——疑似演示残留/品牌污染或绕过 token")
    sizes = re.findall(r"font-size:\s*([\d.]+px)", text)
    cs = Counter(s for s in sizes if s not in allowed_sizes)
    for s, n in cs.most_common(5):
        issues.append(f"阶梯外字号 {s} 出现 {n} 次（应取本项目字号 token 或文档排版白名单）")
    return len(issues) == 0, issues


def check_features(norm, html):
    """件套 5：功能存活 + 名实一致"""
    issues = []
    for name, pat in FEATURE_MARKERS:
        if not re.search(pat, html):
            issues.append(f"功能丢失：{name}（案例交互资产是产物质量底线，生成阶段不许丢）")
    prim = ((norm or {}).get("tokens", {}) or {}).get("primitive", {})
    for k, v in prim.items():
        word = k.split("-")[0].lower()
        claim = COLOR_WORD_MAP.get(word)
        if not claim:
            continue
        val = v.get("value", "") if isinstance(v, dict) else str(v)
        fam = hue_family(val)
        if fam and fam != claim:
            issues.append(f"名实不符：--{k} 值 {val} 实测色相为 {fam}，命名却声称 {claim}——命名必须跟着值走")
    return len(issues) == 0, issues


def check_gradient_truth(norm, source_dir):
    """件套 6（2026-10-16 新增）：还原度检查——渐变 ground truth。
    血泪背景：三次产物（10-15 / 10-16×2）两次渐变靠 agent 手动补录、一次彻底漏提，
    而彼时五件套全绿（历史表述，现为十三件套）——机器检查没有一项对照源材料。本件套拿源码渐变种类数对照产物渐变 token 数。
    source_dir 未传 → SKIP（不进 PASS/REVIEW 统计）。"""
    if not source_dir:
        return True, ["SKIP"]
    src = Path(source_dir)
    if not src.exists():
        return True, [f"SKIP：源目录不存在 {src}"]
    src_grads = set()
    for f in list(src.rglob("*.css")):
        try:
            for m in re.finditer(r"(?:linear-gradient|radial-gradient|conic-gradient)\([^)]*\)", f.read_text(encoding="utf-8", errors="ignore")):
                src_grads.add(re.sub(r"\s+", "", m.group(0)))
        except OSError:
            continue
    prod_grads = set()
    tokens = ((norm or {}).get("tokens", {}))
    for seg in tokens.values():
        for v in seg.values():
            val = v.get("value", "") if isinstance(v, dict) else str(v)
            if "gradient(" in val.lower():
                prod_grads.add(re.sub(r"\s+", "", val))
    if not src_grads:
        return True, ["源材料无渐变声明，无需对照"]
    if not prod_grads:
        return False, [f"源材料有 {len(src_grads)} 种渐变声明，产物零渐变 token——渐变漏提（还原度失败）"]
    return True, [f"源 {len(src_grads)} 种渐变 / 产物 {len(prod_grads)} 条渐变 token，还原度对照通过"]


def _parse_color(v, base_rgb):
    """hex / rgba → 合成后的 rgb（半透明按 alpha 叠到 base 上，即浏览器实际渲染色）"""
    v = (v or "").strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", v)
    if m:
        return tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\(([^)]+)\)", v)
    if m and base_rgb:
        parts = [float(x) for x in m.group(1).split(",")]
        r, g, b = parts[:3]
        a = parts[3] if len(parts) > 3 else 1.0
        return tuple(round(c * a + b0 * (1 - a)) for c, b0 in zip((r, g, b), base_rgb))
    return None


def _contrast(rgb1, rgb2):
    def lum(c):
        vals = []
        for x in c:
            x = x / 255.0
            vals.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]
    l1, l2 = sorted([lum(rgb1), lum(rgb2)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _collect_css_vars(html):
    """全文 CSS 变量表（token 块 + 皮肤块 + 任意 :root/规则内声明）"""
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(r"--([a-z][a-z0-9-]*)\s*:\s*([^;{}]+)", html or "")}


def _resolve_var(val, vars_, depth=0):
    """var(--x) 引用链解析（最深 5 层防环）"""
    val = (val or "").strip()
    if depth > 5:
        return val
    m = re.fullmatch(r"var\(--([a-z0-9-]+)\)", val)
    if m:
        return _resolve_var(vars_.get(m.group(1), ""), vars_, depth + 1)
    return val


def _decl(css_body, prop):
    m = re.search(prop + r"\s*:\s*([^;]+)", css_body or "")
    return m.group(1).strip() if m else ""


def check_doc_contrast(html):
    """件套 7（2026-10-16 新增）：文档可读性 gate——解析真实 CSS 规则的底/字配对并计算 WCAG 对比度。
    事故背景：extract-1016 产物 table 底挂项目 token --color-bg-card（深色项目=白卡片底），
    文字挂皮肤 --ink（换肤=白）→ 白底白字整片不可读，七件套全绿。
    教训：不能只查皮肤变量自身配对——必须按**实际渲染规则**（含 var 引用链到项目 token）算对比度。"""
    if not html:
        return True, ["SKIP"]
    vars_ = _collect_css_vars(html)
    if not vars_:
        return True, ["未检测到 CSS 变量，跳过"]
    body_color = _resolve_var(_decl(re.search(r"body\s*\{([^}]*)\}", html).group(1) if re.search(r"body\s*\{([^}]*)\}", html) else "", "color"), vars_)
    page_bg = _resolve_var(_decl(re.search(r"body\s*\{([^}]*)\}", html).group(1) if re.search(r"body\s*\{([^}]*)\}", html) else "", "background"), vars_) or "#f7f6f3"
    base = _parse_color(page_bg, None) or _parse_color("#f7f6f3", None)
    targets = [("table", 4.5), ("code", 4.5), (".role-badge", 3.0), ("th", 4.5)]
    issues = []
    checked = 0
    for sel, min_ratio in targets:
        m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", html)
        if not m:
            continue
        body = m.group(1)
        bg_raw = _resolve_var(_decl(body, "background"), vars_)
        ink_raw = _resolve_var(_decl(body, "color"), vars_) or body_color
        bg = _parse_color(bg_raw, base)
        ink = _parse_color(ink_raw, bg or base)
        if not bg or not ink:
            continue
        checked += 1
        ratio = _contrast(bg, ink)
        if ratio < min_ratio:
            issues.append(f"文档元素【{sel}】对比度 {ratio:.2f}:1 < {min_ratio}:1（底 {bg_raw or '继承'} / 字 {ink_raw or '继承'}）——白底白字类不可读断裂，结构元素底/字必须用成对皮肤变量")
    if not checked:
        return True, ["未找到可检查的结构元素规则，跳过"]
    return len(issues) == 0, issues


def check_source_audit(norm, md, html, source_dir):
    """件套 8：溯源审计——产物中「值 … N 处」声明回源核对（需 --source-dir，否则 SKIP）"""
    if not source_dir:
        return True, ["SKIP"]
    css_all = ""
    for f in _glob.glob(_os.path.join(source_dir, "**", "*.css"), recursive=True):
        css_all += read(Path(f))
    text = md + "\n" + html
    issues = []
    checked = 0
    for m in re.finditer(r"(\d+(?:\.\d+)?)px[^。；\n]{0,40}?(?:源稿|实测|出现)\s*(\d+)\s*处", text):
        val, claimed = m.group(1), int(m.group(2))
        actual = css_all.count(val + "px")
        checked += 1
        if actual == 0:
            issues.append(f"溯源存疑：声明 {val}px「{claimed} 处」但源码 0 次出现——疑似瞎编溯源")
        elif actual != claimed and abs(actual - claimed) > max(2, claimed * 0.5):
            issues.append(f"溯源偏差：{val}px 声明 {claimed} 处，源码实测 {actual} 处——请复核")
    if checked == 0:
        return True, ["无「值+处数」溯源声明可核，跳过"]
    return len(issues) == 0, issues


def check_css_syntax(html):
    """件套 9：CSS 语法与文件头完整性——DOCTYPE 截断 / 头部游离块 / 缺分号粘连 / 无单位值"""
    issues = []
    body = html.lstrip()
    if not body.startswith("<!DOCTYPE html>"):
        issues.append("文件头异常：缺完整 <!DOCTYPE html> 开头（历史事故：被截断/污染块占位）")
    lt = body.find("<html")
    head_zone = body[:lt] if lt > 0 else ""
    if re.search(r"<(div|p|table|section|img|h\d)\b", head_zone):
        issues.append("文件头游离块：<html> 之前出现内容标签（历史事故：块插入 DOCTYPE 与 html 之间）")
    for m in re.finditer(r'style="([^"]{10,})"', html):
        bad = re.search(r"(?:px|%)\s*[a-z][a-z-]{1,}\s*:", m.group(1))
        if bad:
            issues.append(f"CSS 疑似缺分号粘连: ...{bad.group(0)[:36]}...")
    for m in re.finditer(r"(?<![a-z-])(border-radius|width|height|padding|margin):\s*(\d+(?:\.\d+)?)\s*[;\"']", html):
        v = m.group(2)
        if v not in ("0", "0.0") and float(v) != 0:
            issues.append(f"CSS 无单位值: {m.group(1)}:{v};（缺 px）")
    return len(issues) == 0, issues


def check_delivery(html, out_dir, norm=None):
    """件套 10：交付自包含与交互降级——字体自托管必须做（完全不做也是 REVIEW）、
    @font-face 引用的文件存在、剪贴板必须有 execCommand 降级、皮肤点缀色须来自项目品牌色。"""
    issues = []
    # 1. 字体自托管：必须存在 @font-face（2026-10-19 盲区修复：此前只查"有引用但文件缺"，
    #    agent 完全跳过 fetch_fonts 时反而 PASS——复测事故实证）
    if "@font-face" not in html:
        issues.append("产物无 @font-face 自托管字体——fetch_fonts.py 未执行，字体交付依赖用户机器（复测事故实证盲区）")
    else:
        fonts_dir = Path(out_dir) / "system-spec" / "fonts"
        woff2 = list(fonts_dir.glob("*.woff2")) if fonts_dir.exists() else []
        if not woff2:
            issues.append("fonts/ 目录无 woff2 文件——字体自托管落空（产物不自包含）")
    for m in re.finditer(r'url\("([^"]+\.woff2?)"\)', html):
        f = (Path(out_dir) / "system-spec" / m.group(1))
        if not f.exists():
            issues.append(f"字体文件缺失: {m.group(1)}（@font-face 自托管引用落空——产物不自包含）")
    # 2. 剪贴板降级
    if "navigator.clipboard" in html and "execCommand" not in html:
        issues.append("剪贴板调用无 execCommand 降级——file:// 本地打开时复制功能失效（历史事故）")
    # 3. 皮肤点缀色须来自项目品牌色（防 agent 手填占位灰——复测事故：accent 填成 color-bg-subtle 值）
    m = re.search(r"--skin-accent:\s*([^;]+);", html)
    if m and norm:
        accent = m.group(1).strip()
        prim_vals = [ (v.get("value","") if isinstance(v, dict) else str(v)).strip()
                      for v in (norm.get("tokens", {}).get("primitive", {}) or {}).values() ]
        page_bg = ((norm.get("tokens", {}).get("semantic", {}) or {}).get("color-bg-page", {}) or {}).get("value", "")
        if accent not in prim_vals and accent != page_bg:
            issues.append(f"皮肤点缀色 --skin-accent: {accent} 不在项目 token 值内——疑似手填（须为品牌主色实值，皮肤色只许来自项目 token）")
    return len(issues) == 0, issues


def check_workspace(out_dir):
    """件套 11：交付区卫生——产物根目录只准有交付物，过程留物（脚本/备份/中间 json）必须进 work/"""
    issues = []
    allowed = {"design-system.html", "system-rules.md", "system-rules.json",
               "system-spec", "assets", "hifi", "work", "source"}
    scanned = [Path(out_dir)] + [d for d in Path(out_dir).iterdir()
                                 if d.is_dir() and d.name in ("system-spec", "assets")]
    for base in scanned:
        for f in base.iterdir():
            if f.name in allowed or f.name.startswith(".") or f.is_dir():
                continue
            if f.suffix in (".py", ".bak") or ".bak-" in f.name:
                issues.append(f"交付区混入过程留物: {f.relative_to(out_dir)}（应移入 work/ 或删除——污染下游 AI 上下文）")
    return len(issues) == 0, issues


def check_assets_registry(norm: dict, md: str) -> tuple[bool, list[str]]:
    """件套 12（2026-10-24 线合流）：素材登记对账——normalized.assets 的每个插画资产，
    其语义核心词必须出现在 md 素材章。
    （资产采了却没登记 = §13 分类学作文复发。）assets 为空则跳过。"""
    assets = (norm or {}).get("assets") or []
    illus = [a for a in assets if a.get("class") == "illustration"]
    if not illus:
        return True, []
    issues = []
    for a in illus:
        core = ""
        for seg in reversed((a.get("chain") or "").split(" ∣ ")):
            if "插画" in seg:
                core = seg.replace("可编辑插画 /", "").replace("可编辑插画", "").strip()
                break
        core = core or (a.get("name_hint") or "")
        if core and core not in md:
            issues.append(f"美术资产未登记进素材章: [{core}]（来源 {a.get('name_hint', '')}）")
    return (not issues), issues


def _chapter_form(html: str) -> dict:
    """提取逐章形态签名：标题 / spec-label 关键字（·前）/ 资产元素计数"""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<section class="chapter" id="(s\d+)">', html)]
    form = {}
    for idx, (pos, sid) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(html)
        seg = html[pos:end]
        tm = re.search(r"<h2>(.*?)</h2>", seg, re.S)
        title = re.sub(r"<[^>]+>", "", tm.group(1)).strip() if tm else ""
        labels = [m.group(1).strip() for m in re.finditer(r'<div class="spec-label">([^<·]+?)\s*(?:·|</div>)', seg)]
        form[sid] = {
            "title": title,
            "labels": [re.sub(r"\s+", " ", x) for x in labels],
            "img": len(re.findall(r"<img\b", seg)),
            "svg": len(re.findall(r"<svg\b", seg)),
            "table": len(re.findall(r"<table\b", seg)),
            "lightbox": len(re.findall(r"data-full=", seg)),
            "figure": len(re.findall(r"<figure\b", seg)),
            "dd": len(re.findall(r'class="dd[" ]', seg)),
            "fontface": ("@font-face" in seg),
        }
    return form


def check_template_form(out_dir: Path, product_html: str):
    """件套 13（2026-10-24 线合流）：模板形态对照——自动从 templates/ 案例提取逐章形态签名
    （章节/标题/spec-label/资产元素），对产物做结构 diff：模板有而产物无 = REVIEW。
    签名从模板派生，换模板自动跟随，无硬编码
    （字体事故：产物缺 @font-face 照样六件全绿——守门员对模板形态是盲的）。"""
    tpl_p = Path(__file__).resolve().parents[2] / "templates" / "system-spec" / "design-system.html"
    if not tpl_p.exists():
        return False, [f"无法定位案例模板: {tpl_p}——模板形态对照无法执行，请检查技能包完整性"]
    tf = _chapter_form(tpl_p.read_text(encoding="utf-8", errors="ignore"))
    pf = _chapter_form(product_html)
    issues = []
    for sid, t in tf.items():
        if sid not in pf:
            issues.append(f"缺章节 {sid}（{t['title']}）——模板有而产物无")
            continue
        p = pf[sid]
        if t["title"] and t["title"] != p["title"]:
            issues.append(f"{sid} 章名不一致: 模板[{t['title']}] vs 产物[{p['title']}]")
        miss = [lb for lb in t["labels"] if lb not in p["labels"]]
        if miss:
            issues.append(f"{sid} 缺模板形态块: {','.join(miss)}")
        for key in ("img", "svg", "table", "lightbox", "figure", "dd", "fontface"):
            if t[key] > 0 and p[key] == 0:
                issues.append(f"{sid} 缺资产元素 {key}（模板 {t[key]} 处，产物 0）")
    for sid in pf:
        if sid not in tf:
            issues.append(f"产物多出章节 {sid}（模板无此章）")
    return (not issues), issues


def main():
    ap = argparse.ArgumentParser(description="自检十三件套（真实项目唯一守门员；8/10 两件为兜底复核，源码类坑一律前移到生成规则与生成器）")
    ap.add_argument("out_dir", help="本次项目产物 out/ 目录（必填，无默认——防假绿）")
    ap.add_argument("--expect-total", type=int, default=None,
                    help="仅演示案例回归传入（134）；真实项目不传")
    ap.add_argument("--source-dir", default=None,
                    help="源材料目录（含各页 style.css）——传入则启用第 6 件还原度与第 8 件溯源审计")
    args = ap.parse_args()

    out = Path(args.out_dir)
    md = read(out / "system-rules.md")
    html = read(out / "design-system.html")
    norm = load_norm(out / "normalized.json")
    if not md or not html:
        print(f"[FAIL] 缺产物文件: md={bool(md)} html={bool(html)}（目录：{out}）", file=sys.stderr)
        return 2
    if norm is None:
        print(f"[WARN] 缺 normalized.json：{out}——counts 与名实一致检查降级", file=sys.stderr)

    results = [
        ("counts", check_counts(norm, md, html, args.expect_total, out)),
        ("anchors", check_anchors(md, html)),
        ("contradictions", check_contradictions(md, html)),
        ("raw_values", check_raw_values(norm, md, html)),
        ("features", check_features(norm, html)),
        ("gradient_truth", check_gradient_truth(norm, args.source_dir)),
        ("doc_contrast", check_doc_contrast(html)),
        ("source_audit", check_source_audit(norm, md, html, args.source_dir)),
        ("css_syntax", check_css_syntax(html)),
        ("delivery", check_delivery(html, out, norm)),
        ("workspace", check_workspace(out)),
        ("assets_registry", check_assets_registry(norm or {}, md or "")),
        ("template_form", check_template_form(out, html)),
    ]
    reviewed_results = [(n, r) for n, r in results if r[1] != ["SKIP"]]
    for name, (ok, issues) in results:
        tag = "SKIP" if issues == ["SKIP"] else ("PASS" if ok else "REVIEW")
        print(f"[{tag}] {name}")
        for i in issues:
            print(f"  - {i}")

    total = len(reviewed_results)
    passed = sum(1 for _, (ok, _) in reviewed_results if ok)
    reviewed = total - passed
    print("\n=== 自检总结 ===")
    print(f"计分项: {total}  PASS: {passed}  REVIEW: {reviewed}")
    if reviewed == 0:
        print("结论: 可以宣告完成")
        return 0
    print(f"结论: 有 {reviewed} 项需人决，不算完成")
    return 1


if __name__ == "__main__":
    sys.exit(main())
