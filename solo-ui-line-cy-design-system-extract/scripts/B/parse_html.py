"""
scripts/B/parse_html.py — B-1 静态解析（证据采集器）

复用：bs4 + 正则（标准库风格，不自造解析器；不联网）
输入：一个或多个 HTML 文件路径（多页自动合并证据）
输出：middle 证据稿 JSON（tokens 只填 CSS 变量可直得的部分；
     普通声明值全数进 raw_evidence 聚合桶，由站③/agent 命名成 token）

**血泪修正（2026-10-15，第三次同病发作）**：
旧版只扫 <style> 内联块 + --变量，**从不加载 <link> 外链本地 css、不解析普通声明**
——Figma 导出页（html+外链 style.css，无变量）必然"0 证据"，导致把工具缺陷
误判成"输入薄→降级 rawjson"。本版规则：
  1. bs4 解析 DOM
  2. CSS 来源 = <style> 块 ∪ <link rel=stylesheet> 的**本地**文件 ∪ 同目录 style.css（Figma 导出惯例）
  3. 普通声明值分类聚合（颜色/字号/行高/圆角/阴影/间距/内边距/描边/层级/透明度/动效）
  4. CSS 变量（--*）单独收集 → 直得 token 候选（hex 值→primitive；其余按名/值映射合法 category）
  5. class 频次（≥3）与 data-figma-name 线索 → raw_evidence
  6. **零证据熔断**：五桶全空 → exit 1——先怀疑工具，再怀疑输入；
     任何降级（B-1+ rawjson）必须定性上报等人拍板，禁脚本自降级、禁批量降级。

**补录（2026-10-16，第四次同病——渐变盲区）**：
旧版 BUCKETS 颜色正则只匹配 background-color，**不匹配 background 简写**——
Figma 导出的渐变全写在 `background:linear-gradient(...)` 里，全部漏抓。
本版规则追加：
  7. **渐变桶 gradients**：background/-image 简写且值含 gradient → 原样聚合+频次
  8. colors 桶扩展 background 简写**纯色**（负向排除渐变值）——壳层/页面底色证据不再漏
  9. **img_asset_refs 素材引用清单**：`<img src>` + `background-image:url()` 逐枚计数
     ——素材库"逐枚清单+预览"的原始证据
  10. **render_mode_stats 形态统计**：img 元素数 / 背景图引用数 / 样式类候选数
     ——元素形态三分支（样式渲染/切图/混合）的判定证据

**资产桶（2026-10-24 并入；本文件为 B 引擎双线合流版 v4.1）**：
  11. **第 6 桶 art_assets**：内联 SVG 分级（icon_lucide/icon/illustration；
      语义节点名 → 结构特征（渐变/色彩数/path 数）→ 相对画布比例兜底，禁绝对像素阈值）
      + img 位图清单（name_hint/alt）+ 素材 ownership 待确认标记。
      凡归属为素材的内容一律不进 css 聚合桶（output-templates 美术资产管线 v1.3）。
  12. `--source-type B1_html|B1_figma_export` 进 meta（②+ 混合包路由口径）。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup  # 复用：标准 HTML 解析

# 声明聚合桶：桶名 → (属性名正则, 值过滤正则或 None)
BUCKETS = [
    ("gradients",     r"^background(?:-image)?$",          r"gradient\("),
    ("colors",        r"(?:^color$|background(?:-color)?|border-color|fill|stroke)", r"^(?!.*gradient)"),
    ("font_sizes",    r"font-size",                       r"[\d.]+px"),
    ("line_heights",  r"line-height",                     None),
    ("radii",         r"border(?:-[a-z]+)?-radius",       None),
    ("shadows",       r"box-shadow|text-shadow",          None),
    ("spacings",      r"^(?:margin|gap|row-gap|column-gap)(?:-(?:top|bottom|left|right|inline|block))?$", None),
    ("paddings",      r"^padding(?:-(?:top|bottom|left|right|inline|block))?$", None),
    ("borders",       r"^border(?:-(?:width|style))?$",   None),
    ("z_levels",      r"^z-index$",                       None),
    ("opacities",     r"^opacity$",                       None),
    ("transitions",   r"^(?:transition|animation)(?:-[a-z]+)*$", None),
]

# CSS 变量名/值 → metric 合法 category 映射（enum 与 middle.schema.json 对齐）
METRIC_NAME_MAP = [
    ("radius", "radius"), ("shadow", "shadow"), ("font", "font_size"),
    ("line", "line_height"), ("space", "spacing"), ("gap", "spacing"),
    ("margin", "spacing"), ("pad", "padding"), ("stroke", "stroke_width"),
    ("opacity", "opacity"), ("z-", "z_index"), ("z", "z_index"),
]
SEMANTIC_NAME_MAP = [
    ("text", "text"), ("bg", "bg"), ("border", "border"), ("input", "input"),
    ("focus", "focus"), ("action", "action"), ("font-family", "font_family"),
    ("line-height", "line_height"), ("icon", "icon"), ("stroke", "stroke_color"),
]


def load_css_sources(html_path: Path, soup) -> tuple[list[str], list[str]]:
    """CSS 来源 = 内联 <style> ∪ 本地下链文件 ∪ 同目录 style.css；跳过远程/缺失并记录"""
    texts, skipped = [], []
    for tag in soup.find_all("style"):
        texts.append(tag.get_text())
    linked = [link.get("href", "") for link in soup.find_all("link")
              if "stylesheet" in (link.get("rel") or [])]
    if not linked and (html_path.parent / "style.css").exists():
        linked = ["style.css"]  # Figma 导出惯例兜底
    for href in linked:
        if href.startswith(("http://", "https://", "//")):
            skipped.append(f"远程样式未加载（B-2 先 fetch 落盘）: {href}")
            continue
        f = (html_path.parent / href.split("?")[0]).resolve()
        if f.exists():
            texts.append(f.read_text(encoding="utf-8", errors="ignore"))
        else:
            skipped.append(f"下链文件不存在: {f}")
    return texts, skipped


def aggregate_declarations(css_texts: list[str]) -> dict:
    """普通声明 value 聚合（排除 --自定义属性）"""
    buckets: dict[str, Counter] = {name: Counter() for name, _, _ in BUCKETS}
    rule_count = 0
    for text in css_texts:
        for body in re.findall(r"\{([^{}]*)\}", text):
            for prop, val in re.findall(r"([a-zA-Z-]+)\s*:\s*([^;]+)", body):
                prop = prop.strip().lower()
                if prop.startswith("--"):
                    continue
                rule_count += 1
                val = val.strip()
                for name, prop_pat, val_pat in BUCKETS:
                    if re.search(prop_pat, prop, re.I) and (not val_pat or re.search(val_pat, val, re.I)):
                        buckets[name][val] += 1
                        break
    return {
        "declaration_rules_scanned": rule_count,
        **{name: dict(cnt.most_common(40)) for name, cnt in buckets.items() if cnt},
    }


def extract_css_vars(css_texts: list[str]) -> dict:
    vars_ = {}
    for text in css_texts:
        for m in re.finditer(r"--([a-z][a-z0-9-]+)\s*:\s*([^;{}]+)", text):
            vars_[m.group(1)] = m.group(2).strip()
    return vars_


def classify_vars(css_vars: dict) -> dict:
    """变量 → 合法 token 候选：hex→primitive(neutral 待 agent 定角色)；
    其余按变量名映射合法 category；rgba/多段值进不了 colorToken 的 pattern 就留在证据桶"""
    tokens = {"primitive": {}, "semantic": {}, "component": {}, "metric": {}}
    for name, value in css_vars.items():
        v = value.strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            tokens["primitive"][name] = {"value": v.upper(), "role": "neutral",
                                         "usage": "从 CSS 变量提取（角色待站③ 定夺）", "prohibition": ""}
            continue
        low = name.lower()
        for key, cat in METRIC_NAME_MAP:
            if key in low and re.search(r"[\d.]+(px|rem|%)|^\d+$|^\d*\.\d+$", v):
                if cat == "z_index" or cat == "opacity" or cat in ("spacing", "radius", "padding", "stroke_width", "font_size") and "px" in v or re.fullmatch(r"[\d.]+", v):
                    tokens["metric"][name] = {"value": v, "category": cat, "usage": "从 CSS 变量提取"}
                    break
        else:
            for key, cat in SEMANTIC_NAME_MAP:
                if key in low:
                    tokens["semantic"][name] = {"value": v, "category": cat,
                                                "usage": "从 CSS 变量提取", "prohibition": ""}
                    break
    return tokens


def _nearest_figma_name(el) -> str:
    """最近祖先的 data-figma-name（语义名线索）"""
    for p in el.parents:
        try:
            nm = p.get("data-figma-name")
        except AttributeError:
            continue
        if nm:
            return nm
    return ""


def guess_canvas_width(css_texts: list[str]) -> int:
    """画布宽启发式：CSS 里 ≤2000 的最大定宽（Figma 导出根画板，如 750/375）"""
    ws = [int(w) for t in css_texts for w in re.findall(r"width:\s*(\d{3,4})px", t) if int(w) <= 2000]
    return max(ws) if ws else 0


def _names_before(html: str, pos: int, k: int = 3) -> list[str]:
    """svg 起点之前最近的 k 个 data-figma-name（就近祖先语义链）"""
    names: list[str] = []
    for m in re.finditer(r'data-figma-name="([^"]*)"', html[:pos]):
        if not names or names[-1] != m.group(1):
            names.append(m.group(1))
        if len(names) > k:
            names.pop(0)
    return names


def classify_svg(svg_str: str, names_before: list[str], canvas_w: int) -> dict:
    """美术资产分级：语义节点名优先 → 结构特征（渐变/色彩数/path 数）→ 相对画布比例兜底。
    禁绝对像素阈值（1x/2x/3x 导出倍率下必错）。
    实现注记：html.parser 会小写属性并破坏 svg 内部嵌套——判定一律基于原始字符串正则。"""
    vb = re.search(r'viewBox=["\']0\s+0\s+([\d.]+)[\s,]+([\d.]+)', svg_str)
    w = float(vb.group(1)) if vb else 0.0
    h = float(vb.group(2)) if vb else 0.0
    paths = len(re.findall(r"<path\b", svg_str))
    grads = len(re.findall(r"<(?:linear|radial)Gradient", svg_str, re.I))
    palette = sorted(set(re.findall(
        r'(?:fill|stroke|stop-color)["\']?\s*[:=]\s*["\']?(#[0-9A-Fa-f]{3,6})', svg_str)))
    chain = " ∣ ".join(names_before)
    if any("线性图标" in n for n in names_before):
        cls = "icon_lucide"          # 已由上游图标库（Lucide）绑定覆盖，只计数
    elif (any(("插画" in n) or ("矢量" in n) or ("渐变" in n) or ("image" in n.lower()) for n in names_before)
          or grads or len(palette) >= 3):
        cls = "illustration"
    elif paths <= 6 and len(palette) <= 2:
        cls = "icon"
    elif canvas_w and max(w, h) >= canvas_w * 0.2:
        cls = "illustration"
    elif not canvas_w:
        cls = "illustration"   # 画布宽未知 → 保守归插画（ownership 待确认），禁静默落 icon
    else:
        cls = "icon"
    ownership = ("待确认（组件件 / 素材位 / 装饰——问设计师，禁默认当组件）"
                 if cls == "illustration" else "-")
    return {"name_hint": (names_before[-1] if names_before else "")[:40],
            "chain": chain[:80], "class": cls, "ownership": ownership,
            "viewBox": f"0 0 {w:g} {h:g}" if vb else "", "paths": paths,
            "gradients": grads, "palette": palette[:8]}


def extract_art_assets(html: str, css_texts: list[str]) -> tuple[list[dict], list[dict], dict]:
    """第 6 桶：美术资产（内联 SVG 插画/图标 + img 位图清单）。
    内联 svg 过去是解析黑盒——可编辑插画/装饰全部漏采（血泪：样页重拼无米下锅）。
    实现注记：用正则切 <svg> 原文，不走 soup 树（html.parser 破坏 svg 内部嵌套）。
    token 证据边界：本桶信息只进 assets 登记，svg 内部的颜色/字号/尺寸**不进** css 聚合桶
    ——凡归属为素材的内容一律不产生 token 证据（output-templates 美术资产管线 v1.3）。"""
    canvas_w = guess_canvas_width(css_texts)
    arts, summary = [], Counter()
    for m in re.finditer(r"<svg\b[\s\S]*?</svg>", html):
        info = classify_svg(m.group(0), _names_before(html, m.start()), canvas_w)
        summary[info["class"]] += 1
        if info["class"] != "icon_lucide":
            arts.append(info)
    soup = BeautifulSoup(html, "html.parser")
    imgs = []
    for img in soup.find_all("img"):
        imgs.append({"src": img.get("src", "")[:80], "name_hint": _nearest_figma_name(img)[:40],
                     "alt": (img.get("alt") or "")[:40]})
    return arts[:80], imgs[:60], {"canvas_width": canvas_w, **dict(summary), "img_count": len(imgs)}


def parse_one(html_path: Path) -> tuple[dict, list[str], dict]:
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    css_texts, skipped = load_css_sources(html_path, soup)
    agg = aggregate_declarations(css_texts)
    css_vars = extract_css_vars(css_texts)
    class_freq = Counter()
    for el in soup.find_all(class_=True):
        for cls in el.get("class", []):
            class_freq[cls] += 1
    figma_names = sorted({el.get("data-figma-name") for el in soup.find_all(attrs={"data-figma-name": True})})[:60]
    arts, imgs, art_summary = extract_art_assets(html, css_texts)
    # 素材引用清单（素材库逐枚证据）：img src + css background-image:url()
    img_refs: Counter = Counter()
    for el in soup.find_all("img", src=True):
        img_refs[Path(el["src"].split("?")[0]).name] += 1
    bg_url_count = 0
    for text in css_texts:
        for m in re.finditer(r"url\((['\"]?)([^)'\"]+)\1\)", text):
            bg_url_count += 1
            img_refs[Path(m.group(2).split("?")[0]).name] += 1
    # 形态统计（元素形态三分支判定证据：样式渲染 / 切图 / 混合）
    render_stats = {
        "img_elements": len(soup.find_all("img")),
        "bg_image_refs": bg_url_count,
        "style_class_candidates": len(class_freq),
    }
    evidence = {
        "css_sources_loaded": len(css_texts),
        "css_sources_skipped": skipped,
        "class_freq": {c: n for c, n in class_freq.most_common(60) if n >= 3},
        "data_figma_names": figma_names,
        "inline_styles_count": len(soup.find_all(style=True)),
        "art_assets": arts,
        "img_assets": imgs,
        "art_summary": art_summary,
        "img_asset_refs": dict(img_refs.most_common(60)),
        "render_mode_stats": render_stats,
        **agg,
    }
    return classify_vars(css_vars), skipped, evidence


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 1:
        print("用法: python parse_html.py <a.html> [b.html ...] [out_middle.json] "
              "[--source-type B1_html|B1_figma_export]", file=sys.stderr)
        sys.exit(1)
    out = Path("out/middle.json")
    paths = []
    for a in args:
        p = Path(a)
        if p.suffix.lower() in (".html", ".htm"):
            if not p.exists():
                print(f"[FAIL] 输入 HTML 不存在（禁静默吞页）: {p}", file=sys.stderr)
                return 2
            paths.append(p)
        elif p.suffix == ".json":
            out = p
    if not paths:
        print("[FAIL] 无有效 HTML 输入", file=sys.stderr)
        return 2
    source_type = "B1_html"
    if "--source-type" in sys.argv:
        k = sys.argv.index("--source-type")
        if k + 1 >= len(sys.argv):
            print("[FAIL] --source-type 缺值（B1_html|B1_figma_export）", file=sys.stderr)
            return 2
        source_type = sys.argv[k + 1]
        if source_type not in ("B1_html", "B1_figma_export"):
            print(f"[FAIL] --source-type 非法枚举: {source_type}", file=sys.stderr)
            return 2

    merged_tokens = {"primitive": {}, "semantic": {}, "component": {}, "metric": {}}
    merged_evidence = {}
    all_skipped = []
    for p in paths:
        t, skipped, ev = parse_one(p)
        for seg in merged_tokens:
            merged_tokens[seg].update(t[seg])
        all_skipped += skipped
        for k, v in ev.items():
            if isinstance(v, Counter):
                merged_evidence.setdefault(k, Counter()).update(v)
            elif isinstance(v, dict):
                base = merged_evidence.setdefault(k, {})
                for kk, vv in v.items():
                    base[kk] = base.get(kk, 0) + vv if isinstance(vv, (int, float)) else vv
            elif isinstance(v, list):
                if k in ("art_assets", "img_assets"):
                    base = merged_evidence.setdefault(k, [])
                    base.extend(v)
                    merged_evidence[k] = base[:120]
                elif k == "css_sources_skipped":
                    merged_evidence[k] = merged_evidence.get(k, []) + v
                else:
                    merged_evidence[k] = sorted(set(merged_evidence.get(k, [])) | set(v))[:60] if k == "data_figma_names" else merged_evidence.get(k, v)
            else:
                merged_evidence[k] = merged_evidence.get(k, 0) + v if isinstance(v, int) else v
    # Counter 序列化
    merged_evidence = {k: (dict(c.most_common(40)) if isinstance(c, Counter) else c)
                       for k, c in merged_evidence.items()}

    middle = {
        "meta": {
            "source_type": source_type,
            "source_id": "; ".join(str(p) for p in paths),
            "extracted_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "2.0.0",
            "supplementary_notes": "parse_html 证据稿：tokens 仅含 CSS 变量直得部分；普通声明值在 raw_evidence 聚合桶，站② 末由 agent 完成 token 化后过 schema.py validate。",
        },
        "tokens": merged_tokens,
        "components": [],
        "patterns": {},
        "raw_evidence": merged_evidence,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(middle, ensure_ascii=False, indent=2), encoding="utf-8")

    ev_counts = {k: (len(v) if isinstance(v, (dict, list)) else v)
                 for k, v in merged_evidence.items() if k != "css_sources_skipped"}
    print(f"[OK] {len(paths)} 页 → {out}")
    for k, v in ev_counts.items():
        print(f"  {k}: {v}")
    print(f"  tokens直得: primitive {len(merged_tokens['primitive'])} / semantic {len(merged_tokens['semantic'])} / metric {len(merged_tokens['metric'])}")
    if all_skipped:
        print("[WARN] 跳过的 CSS 来源:", file=sys.stderr)
        for s in all_skipped:
            print(f"  - {s}", file=sys.stderr)

    # 零证据熔断（先怀疑工具，再怀疑输入）
    if merged_evidence.get("declaration_rules_scanned", 0) == 0 and not merged_tokens["primitive"] \
            and not merged_evidence.get("class_freq"):
        print("[REVIEW] 五桶全空——这是**未预期结果**：先核对 CSS 来源是否已加载（本脚本已支持外链），"
              "确属输入无证据 → **定性上报等用户拍板**再谈降级（B-1+ rawjson 按页逐个批，禁批量自降级）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
