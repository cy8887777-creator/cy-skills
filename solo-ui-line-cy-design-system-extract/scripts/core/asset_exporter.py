# -*- coding: utf-8 -*-
"""
scripts/core/asset_exporter.py — 美术资产落盘器（第 6 桶 → 产物 assets/）

输入：一个或多个来源 HTML（Figma 导出页）+ 产物 assets 目录（末个参数为目录，误传 HTML 文件会 exit 2）
输出：
  <assets>/illustrations/<语义名>-<页>.svg —— 插画级：按容器归组，N 个矢量合成一份独立 SVG
  <assets>/images/<语义名>-<页>.<ext>      —— img 位图复制
  <assets>/manifest.md                     —— 登记表（资产/类型/来源页·节点/引用/尺寸/状态/落盘文件）

说明：
- 不消费 middle.json——直接从来源 HTML 重推导；分级判据与 scripts/B/parse_html.py 第 6 桶
  保持同一套：语义名 > 结构特征 > 相对画布比例，语义词表两端一致（插画/矢量/渐变/image）。
- 插画级状态默认「待确认（组件件/素材位/装饰——问设计师）」写入 manifest 状态列，
  禁默认当组件（星空主视觉事故：结构像组件实为后台整图 PNG）；
  素材内部文字/颜色/尺寸不产生 token 证据，只随 manifest 登记。
- 幂等：同名覆盖、manifest 整体重建；同名碰撞自动加序号不覆盖。
- 守门：落盘 0 项 = 未预期结果 → exit 1（铁律 11：先怀疑脚本，再怀疑输入，定性上报）。
- 实现注记：矢量坐标/尺寸取自 style.css 类规则（css_num 带词边界守卫）；
  html.parser 破坏 svg 嵌套，svg 一律正则切原文；img 属性顺序不定——先取标签再单独抓属性。
"""
import io
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8") if hasattr(sys.stdout, "buffer") else sys.stdout

# 与 scripts/B/parse_html.py classify_svg 的语义词表保持一致（两端漂移即缺陷）
ILLUS_NAME_PAT = re.compile(r'data-figma-name="((?:Image \([^"]+\)|[^"]*(?:插画|矢量|渐变|image)[^"]*))"')


def load_css(css_dir: Path) -> str:
    return "\n".join(c.read_text(encoding="utf-8", errors="ignore")
                     for c in sorted(css_dir.glob("*.css")))


def css_rule(css: str, cls: str):
    m = re.search(r"\." + re.escape(cls) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else ""


def css_num(rule: str, prop: str, default=0.0):
    """取 <prop>: Npx——(?<![a-z-]) 前置守卫，防 padding-left / min-width / margin-top 误命中"""
    m = re.search(r"(?<![a-z-])" + prop + r":\s*(-?[\d.]+)px", rule)
    return float(m.group(1)) if m else default


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def container_block(html: str, name: str):
    """取 data-figma-name=name 的容器原文（div 配平截取）"""
    m = re.search(r'<div[^>]*data-figma-name="' + re.escape(name) + r'"[^>]*>', html)
    if not m:
        return None
    i = m.start()
    depth = 0
    for t in re.finditer(r"<div\b|</div>", html[i:]):
        depth += 1 if t.group(0).startswith("<div") else -1
        if depth == 0:
            return html[i:i + t.end()]
    return html[i:]


def build_combined_svg(block: str, css: str):
    """容器内 N 个 Vector svg 合成一份独立 SVG：
    外层 viewBox = 矢量包盒；每个 Vector 按 css 定位包 <g transform>；文本 div 转 <text>（内容转义）。
    返回 (svg_str, W, H)；容器内无 Vector 返回 None。"""
    vecs = []
    for mv in re.finditer(r'<div\b[^>]*data-figma-name="Vector"[^>]*>(\s*<svg[\s\S]*?</svg>)', block):
        cm = re.search(r'class="([^"]+)"', mv.group(0))
        cls = cm.group(1).split()[0] if cm else ""
        rule = css_rule(css, cls)
        x, y = css_num(rule, "left"), css_num(rule, "top")
        w, h = css_num(rule, "width"), css_num(rule, "height")
        svg = mv.group(1)
        vb = re.search(r'viewBox=["\']0\s+0\s+([\d.]+)[\s,]+([\d.]+)', svg)
        if vb:  # 有 viewBox：等比缩放到位
            vx, vy = float(vb.group(1)), float(vb.group(2))
            sx = (w / vx) if w and vx else 1.0
            sy = (h / vy) if h and vy else sx
        else:   # 无 viewBox（Figma 固定尺寸导出常见）：按 css 尺寸原样嵌入
            sx = sy = 1.0
            w = w or 20
            h = h or 20
        inner = re.sub(r"</?svg[^>]*>", "", svg)
        vecs.append((x, y, sx, sy, inner, w or vx, h or vy))
    if not vecs:
        return None
    W = max(v[0] + v[5] for v in vecs) or 100
    H = max(v[1] + v[6] for v in vecs) or 100
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}">']
    for x, y, sx, sy, inner, _, _ in vecs:
        parts.append(f'<g transform="translate({x:g},{y:g}) scale({sx:g},{sy:g})">{inner}</g>')
    # 文本节点 → <text>（内容转义；颜色/字号取自 css，缺省值仅为可见性兜底、不作 token 证据）
    for mt in re.finditer(r'<div\b[^>]*data-figma-name="([^"]{2,40})"[^>]*>([^<>]{1,60})</div>', block):
        name, txt = mt.group(1), esc(mt.group(2).strip())
        if not txt or name == "Vector":
            continue
        cm = re.search(r'class="([^"]+)"', mt.group(0))
        rule = css_rule(css, cm.group(1).split()[0]) if cm else ""
        x, y = css_num(rule, "left"), css_num(rule, "top") + css_num(rule, "font-size", 10)
        color = re.search(r"color:\s*(#[0-9A-Fa-f]{3,6})", rule)
        fs = css_num(rule, "font-size", 10)
        parts.append(f'<text x="{x:g}" y="{y:g}" fill="{color.group(1) if color else "#1C201F"}" '
                     f'font-size="{fs:g}" font-family="PingFang SC, sans-serif">{txt}</text>')
    parts.append("</svg>")
    return "\n".join(parts), W, H


def _names_before(html: str, pos: int, k: int = 4) -> list[str]:
    """svg 起点之前最近的 k 个 data-figma-name（就近祖先语义链）"""
    names: list[str] = []
    for m in re.finditer(r'data-figma-name="([^"]*)"', html[:pos]):
        if not names or names[-1] != m.group(1):
            names.append(m.group(1))
        if len(names) > k:
            names.pop(0)
    return names


def semantic_name(names: list[str]) -> str:
    """从语义链取第一个含中文的具名节点（跳过 Icon/Text/Vector 等泛名）作命名"""
    for n in reversed(names):
        if re.search(r"[一-龥]", n) and not re.fullmatch(r"(?:线性图标|图标|Icon|文本|Text)[\s/]*.*标注", n):
            return n
    return names[-1] if names else "未命名"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("用法: asset_exporter.py <a.html> [b.html ...] <assets目录>  （末个参数为目录；幂等，同名覆盖+碰撞加序号）",
              file=sys.stderr)
        return 2
    *pages, out_dir = args
    out = Path(out_dir)
    if out.suffix.lower() in (".html", ".htm"):
        print("[FAIL] 末个参数应是 assets 目录，不是 HTML 文件", file=sys.stderr)
        return 2
    (out / "illustrations").mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(parents=True, exist_ok=True)
    manifest = ["# 美术资产登记表（asset_exporter 自动生成）", "",
                "| 资产 | 类型 | 来源页 · 节点 | 引用 | 尺寸 | 状态 | 落盘文件 |",
                "|---|---|---|---|---|---|---|"]
    count = 0
    used = {}
    for pg in pages:
        p = Path(pg)
        html = p.read_text(encoding="utf-8", errors="ignore")
        css = load_css(p.parent)
        page_tag = p.parent.name

        def uniq(base):
            used[base] = used.get(base, 0) + 1
            return base if used[base] == 1 else f"{base}-{used[base]}"

        # 1) 插画容器（命名含 插画/矢量/渐变/image）——按容器名去重，逐容器合成
        seen = OrderedDict()
        for m in ILLUS_NAME_PAT.finditer(html):
            seen.setdefault(m.group(1), 0)
            seen[m.group(1)] += 1
        for name, refs in seen.items():
            block = container_block(html, name)
            if not block:
                continue
            built = build_combined_svg(block, css)
            if not built:
                continue
            svg, W, H = built
            safe = re.sub(r"[^\w一-龥]+", "-", name).strip("-")
            f = out / "illustrations" / f"{uniq(safe + '-' + page_tag)}.svg"
            f.write_text(svg, encoding="utf-8")
            manifest.append(f"| {name} | 插画（SVG） | {page_tag} · 节点 {refs} 处 | {refs} | {W:g}×{H:g} | "
                            "待确认（组件件/素材位/装饰——问设计师） |"
                            f" illustrations/{f.name} |")
            count += 1

        # 2) img 位图复制——属性顺序不定：先取标签再单独抓 src/alt
        for m in re.finditer(r"<img\b[^>]*>", html):
            tag = m.group(0)
            sm = re.search(r'src=["\']((?:\.\./)?assets/[^"\']+)["\']', tag)
            if not sm:
                continue
            srcf = p.parent / sm.group(1)
            if not srcf.exists():
                continue
            am = re.search(r'alt=["\']([^"\']*)["\']', tag)
            alt = am.group(1) if am else Path(sm.group(1)).stem
            safe = re.sub(r"[^\w一-龥]+", "-", alt).strip("-") or Path(sm.group(1)).stem
            dst = out / "images" / f"{uniq(safe + '-' + page_tag)}{srcf.suffix}"
            dst.write_bytes(srcf.read_bytes())
            manifest.append(f"| {alt or safe} | 位图 | {page_tag} · {sm.group(1)} | - | - | - |"
                            f" images/{dst.name} |")
            count += 1

        # 3) 图标级（非「线性图标」命名的项目私有图标）——落盘 icons/custom/ + 待比对 Lucide
        #    （v1 只计数不落盘的缺口：快捷服务等自定义描边图标被下游拿通用图标顶替——原型味来源）
        icon_seen = {}
        for m in re.finditer(r"<svg\b[\s\S]*?</svg>", html):
            s = m.group(0)
            names = _names_before(html, m.start())
            if any("线性图标" in n for n in names):
                continue                      # Lucide 已绑定，跳过
            if any(("插画" in n) or ("矢量" in n) or ("渐变" in n) or ("Image (" in n) for n in names):
                continue                      # 插画容器已归组落盘，跳过
            if re.search(r"<(?:linear|radial)Gradient", s, re.I):
                continue                      # 带渐变按插画处理
            sem = semantic_name(names)
            if not re.search(r"[一-龥]", sem):
                continue                      # 无中文语义名可命名 → 计数不落盘
            h = str(hash(s))[-8:]
            if h in icon_seen:
                continue
            icon_seen[h] = sem
            safe = re.sub(r"[^\w一-龥]+", "-", sem).strip("-")
            dst = out / "icons" / "custom" / f"{uniq(safe + '-' + page_tag)}.svg"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(s, encoding="utf-8")
            vb = re.search(r'viewBox=["\']([^"\']+)"', s)
            manifest.append(f"| {sem}（图标） | 图标（项目私有·待比对 Lucide） | {page_tag} · {names[0] if names else '-'} | - | "
                            f"{(vb.group(1) if vb else '-')} | 待比对：命中 Lucide 可整组替换 |"
                            f" icons/custom/{dst.name} |")
            count += 1

    (out / "manifest.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    if count == 0:
        print("[REVIEW] 落盘 0 项——来源页无美术资产？这是**未预期结果**（铁律 11：先怀疑脚本，"
              "再怀疑输入；定性上报等拍板，禁静默当空通过）", file=sys.stderr)
        return 1
    print(f"[OK] 落盘 {count} 项 → {out}（manifest.md 同步）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
