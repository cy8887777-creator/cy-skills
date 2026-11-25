"""
scripts/core/gen_html.py — HTML 产物生成（人看演示版 · 区域重渲染）

用法（唯一）：python gen_html.py <normalized.json 路径> <out design-system.html 路径>

策略：**区域重渲染**（模板里没有 {{}} 占位符，旧的 replace("{{css_vars}}")
从未生效过——那是"空转机"事故的根因之一）。本脚本真实替换：
  1) :root token 变量块（4 段全部变量按 normalized 重新生成）
  2) 页脚统计行「Token N · 组件 M」
  3) 全文版本号 v2.0.0 / 日期 2026-10-14 / 「示例设计系统」名称
  4) 章节导航/标题里的「N 组件」计数
  5) 文档皮肤 apply_skin：页面底色明度 <0.4 判深色项目 → 皮肤变量挂项目实值
诚实边界：正文实物演示（色板卡、组件实物、表格数值）在模板中是**案例字面**——
主会话 agent 必须以 normalized.json 为唯一数据源全量复写（复制模板骨架、
替换演示值、保留交互代码）；手搓空白生成器从骨架复制起步，
self_check 十一件套（功能存活 + 裸值品牌污染扫描）负责抓丢功能与抄漏。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / "templates" / "system-spec" / "design-system.html"

# 皮肤变量 → 取值来源（semantic 语义 token / primitive 角色）
SKIN_SOURCES = [
    ("--skin-page-bg",      "color-bg-page"),
    ("--skin-page-ink",     "color-text-primary"),
    ("--skin-ink-soft",     "color-text-secondary"),
    ("--skin-line",         "color-border-subtle"),
]


def build_css_vars(normalized: dict) -> str:
    tokens = normalized.get("tokens", {})
    lines = []
    for seg, title in (("primitive", "Primitive"), ("semantic", "Semantic"),
                       ("component", "Component"), ("metric", "Metric")):
        data = tokens.get(seg, {})
        if not data:
            continue
        lines.append(f"    /* {title} */")
        for k, v in data.items():
            val = (v or {}).get("value", "transparent")
            # 引用型值（如 gray-900）自动包 var()
            if re.fullmatch(r"[a-z][a-z0-9-]*", str(val)):
                val = f"var(--{val})"
            lines.append(f"    --{k}: {val};")
        lines.append("")
    return "\n".join(lines).rstrip()


def regenerate(html: str, normalized: dict) -> str:
    tokens = normalized.get("tokens", {})
    system = normalized.get("system", {})
    name = system.get("name", "示例设计系统")
    ver = system.get("version", "2.0.0")
    date = system.get("date", "")
    counts = {s: len(tokens.get(s, {})) for s in ("primitive", "semantic", "component", "metric")}
    total = sum(counts.values())
    ncomp = len(normalized.get("components", []))

    out = html
    # 1) :root token 块（选变量最多且含 --* 的那个块）
    css = build_css_vars(normalized)

    def _root_sub(m):
        block = m.group(0)
        if "--skin-page-bg:" in block:  # 皮肤块不是 token 块，禁替换
            return block
        if len(re.findall(r"--[a-z0-9-]+\s*:", block)) >= 20:
            return ":root {\n" + css + "\n  }"
        return block

    out = re.sub(r":root\s*\{[^}]*\}", _root_sub, out, flags=re.DOTALL)
    # 2) 页脚统计行
    out = re.sub(r"Token\s*\d+(\s*·\s*组件)\s*\d+", f"Token {total}\\1 {ncomp}", out)
    out = re.sub(r"Token\s*\d+(?=\s*(个|｜|\||<))", f"Token {total}", out)
    # 3) 版本 / 日期 / 名称
    out = out.replace("v2.0.0", f"v{ver}")
    if date:
        out = out.replace("2026-10-14", date)
    out = out.replace("示例设计系统", name)
    # 4) 「25 组件」类计数（契约字典字样不动，只动统计口径）
    out = re.sub(r"(?<![\d.])25 组件", f"{ncomp} 组件", out)
    return out


def _resolve_hex(value, prim: dict):
    """token 值 → (css值, rgb三元组或None)。支持 hex / 引用名 / rgba() 原文。"""
    v = str(value).strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", v)
    if m:
        h = m.group(1)
        return v, tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if re.fullmatch(r"[a-z][a-z0-9-]*", v) and v in prim:
        return _resolve_hex(prim[v].get("value", ""), prim)
    m = re.match(r"rgba?\(([^)]+)\)", v)
    if m:
        parts = [float(x) for x in m.group(1).split(",")[:3]]
        return v, tuple(int(x) for x in parts)
    return None, None


def _luminance(rgb) -> float:
    """简化相对亮度 0-1（sRGB 加权，不做 gamma 展开——皮肤判定够用）"""
    if not rgb:
        return 1.0
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lighten(hexstr: str, mix: float) -> str:
    """向白色混合 mix 比例（程序派生，不做第三色字面）"""
    h = hexstr.lstrip("#")
    rgb = [min(255, int(int(h[i:i + 2], 16) + (255 - int(h[i:i + 2], 16)) * mix)) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(rgb)


def _darken(hexstr: str, factor: float) -> str:
    h = hexstr.lstrip("#")
    rgb = [max(0, int(int(h[i:i + 2], 16) * factor)) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(rgb)


def _apply_and_verify(html, swaps):
    """替换皮肤变量并自校验：产物实际值 ≠ 预期值即 FAIL 退出（换肤失败曾 WARN 裸奔全绿）"""
    out = html
    failed = []
    for var, val in swaps.items():
        out, n = re.subn(rf"({re.escape(var)}:\s*)[^;]+;", rf"\g<1>{val};", out, count=1)
        got = re.search(re.escape(var) + r":\s*([^;]+);", out)
        if n != 1 or not got or got.group(1).strip() != val.strip():
            failed.append(f"{var} 期望 {val} 实际 {got.group(1).strip() if got else '缺失'}")
    if failed:
        for f in failed:
            print(f"[FAIL] 换肤校验不过: {f}", file=sys.stderr)
        print("[FAIL] 换肤失败——产物将带模板默认色出厂，禁止交付；检查模板 --skin-* 块形态", file=sys.stderr)
        sys.exit(1)
    return out


def apply_skin(html: str, normalized: dict) -> str:
    """按项目气质换文档皮肤：页面底明度 <0.4 判深色项目；浅色项目皮肤同样跟随项目 token
    （2026-10-19 修正——浅色不再保持模板纸感，与被提取系统气质统一）。皮肤色全部来自项目 token。"""
    tokens = normalized.get("tokens", {})
    prim = tokens.get("primitive", {})
    sem = tokens.get("semantic", {})

    page_bg_css, page_bg_rgb = _resolve_hex(sem.get("color-bg-page", {}).get("value", ""), prim)
    if not page_bg_rgb:
        print("[INFO] 皮肤：默认纸感（缺 color-bg-page，未换肤）")
        return html

    def sem_css(name):
        css, _ = _resolve_hex(sem.get(name, {}).get("value", ""), prim)
        return css

    _prim_keys = [k for k, v in prim.items() if v.get("role") == "primary"]
    accent_css = None
    if _prim_keys:
        _base = next((k for k in _prim_keys if "-500" in k), None)  # 品牌主档优先 500
        if _base is None:
            _l = sorted(_prim_keys, key=lambda k: _luminance(_resolve_hex(prim[k]["value"], prim)[1]))
            _base = _l[len(_l) // 2]
        accent_css = _resolve_hex(prim[_base]["value"], prim)[0]

    if _luminance(page_bg_rgb) >= 0.4:
        # 浅色项目分支（跑腿产物手动方案的机制化）
        def _lum(css):
            _, rgb = _resolve_hex(css, prim)
            return _luminance(rgb) if rgb else 1.0

        def _first_ok(cands, page):
            last = cands[-1]
            for c in cands:
                if not c:
                    continue
                l1, l2 = sorted([_lum(c), _lum(page)], reverse=True)
                last = c
                if (l1 + 0.05) / (l2 + 0.05) >= 4.5:
                    return c
            return last

        soft = _first_ok([sem_css("color-text-tertiary"), sem_css("color-text-secondary"),
                          sem_css("color-text-placeholder")], page_bg_css)
        swaps = {
            "--skin-page-bg": page_bg_css,
            "--skin-page-ink": sem_css("color-text-primary") or "#20252C",
            "--skin-ink-soft": soft,
            "--skin-line": sem_css("color-border") or sem_css("color-border-subtle") or "#E9ECF1",
            "--skin-sidebar-bg": sem_css("color-text-primary") or _darken(page_bg_css, 0.55),
            "--skin-sidebar-ink": _lighten(sem_css("color-text-primary") or page_bg_css, 0.82),
            "--skin-accent": accent_css or page_bg_css,
            "--skin-grid": "transparent",
            "--skin-code-bg": sem_css("color-bg-subtle") or "#F6F7F9",
            "--skin-code-ink": sem_css("color-text-primary") or "#20252C",
            "--skin-card-bg": sem_css("color-bg-card") or "#FFFFFF",
            "--skin-card-ink": sem_css("color-text-primary") or "#20252C",
            "--skin-badge-bg": sem_css("color-text-primary") or "#20252C",
            "--skin-badge-ink": page_bg_css,
        }
        out = _apply_and_verify(html, swaps)
        print(f"[INFO] 皮肤：浅色（项目 token 驱动：底 {page_bg_css} / 侧栏 {swaps['--skin-sidebar-bg']} / 点缀 {swaps['--skin-accent']}；格纹关闭）")
        return out

    swaps = {
        "--skin-page-bg": page_bg_css,
        "--skin-page-ink": sem_css("color-text-primary") or "#ffffff",
        "--skin-ink-soft": sem_css("color-text-secondary") or "rgba(255,255,255,0.70)",
        "--skin-line": sem_css("color-border-subtle") or "rgba(255,255,255,0.24)",
        "--skin-sidebar-bg": _darken(page_bg_css, 0.55),
        "--skin-sidebar-ink": "rgba(255,255,255,0.85)",
        "--skin-accent": accent_css or page_bg_css,
        "--skin-grid": "rgba(255,255,255,.045)",
        "--skin-code-bg": "rgba(255,255,255,.10)",
        "--skin-code-ink": "#FFFFFF",
        "--skin-card-bg": "rgba(255,255,255,.06)",
        "--skin-card-ink": "#FFFFFF",
        "--skin-badge-bg": "rgba(255,255,255,.14)",
        "--skin-badge-ink": "#FFFFFF",
    }
    out = _apply_and_verify(html, swaps)
    print(f"[INFO] 皮肤：深色（项目 token 驱动：底 {page_bg_css} / 侧栏 {swaps['--skin-sidebar-bg']} / 点缀 {swaps['--skin-accent']}）；文档结构元素走成对皮肤变量（card/code/badge 底字成对，保对比度）")
    return out


def main():
    if len(sys.argv) != 3:
        print("用法: python gen_html.py <normalized.json> <out design-system.html>", file=sys.stderr)
        return 2
    norm_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    if not TEMPLATE.exists():
        print(f"[FAIL] 模板不存在: {TEMPLATE}", file=sys.stderr)
        return 2
    if not norm_path.exists():
        print(f"[FAIL] normalized.json 不存在: {norm_path}", file=sys.stderr)
        return 2
    norm = json.loads(norm_path.read_text(encoding="utf-8"))
    filled = regenerate(TEMPLATE.read_text(encoding="utf-8"), norm)
    filled = apply_skin(filled, norm)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(filled, encoding="utf-8")
    print(f"[OK] HTML 产物: {out_path}  ({len(filled)} chars)")
    print("[INFO] 本脚本重渲染 :root 变量 + 统计行 + 版本/日期/名称 + 文档皮肤；"
          "正文实物演示区须按 normalized.json 实测复写（self_check 十一件套兜底）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
