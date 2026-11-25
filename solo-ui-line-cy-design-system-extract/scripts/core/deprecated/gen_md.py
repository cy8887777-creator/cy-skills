"""
scripts/core/gen_md.py — md 产物生成（AI 读规则版 · 区域重渲染）

用法（唯一）：python gen_md.py <normalized.json 路径> <out system-rules.md 路径>

策略：**区域重渲染**（不是占位符替换——模板里从来没有 {{}} 占位符，
旧方案从未生效，是"空转机"事故根因之一）。数据驱动整段再生：
  · §2 全部四段 + 分组表：由 normalized.tokens 全量生成（不看模板组清单——
    模板曾停留在 64 行旧账，跟随式渲染会漏 21 行）
  · §6 组件表 / §7 模式 bullets：同上
  · 标题 / 版本 / 日期 / 系统名 / 计数声明行：全局替换
诚实边界：§3 布局 / §4 多端 / §5 图标素材 / §8 禁令 / §9 验收 / §10 结构说明
是案例规则原文——主会话 agent 必须按项目实测复写，self_check 三件套兜底。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / "templates" / "system-rules.md"

PRIM_GROUPS = [("主色组", "primary"), ("主色辅助", "primary_tint"),
               ("中性", "neutral"), ("功能", "functional")]
METRIC_GROUPS = [("间距", "spacing", "页面布局间距必须取档；组件内部尺寸按 §6 组件规格执行（豁免）"),
                 ("圆角", "radius", ""), ("阴影", "shadow", ""), ("字号", "font_size", ""),
                 ("行高", "line_height", ""), ("内边距", "padding", ""),
                 ("描边宽度", "stroke_width", ""), ("透明度", "opacity", ""),
                 ("字重", "font_weight", ""), ("层级", "z_index", "")]


def table_rows(data: dict, mode: str) -> list[str]:
    """mode: 'usage' | 'owner' | 'scene'"""
    if mode == "owner":
        rows = ["| Token | 值 | 归属 | 禁用于 |", "|---|---|---|---|"]
    elif mode == "scene":
        rows = ["| Token | 值 | 场景 |", "|---|---|---|"]
    else:
        rows = ["| Token | 值 | 用途 | 禁用于 |", "|---|---|---|---|"]
    for k, v in data.items():
        v = v or {}
        val = v.get("value", "—")
        if mode == "owner":
            rows.append(f"| `--{k}` | {val} | {v.get('usage', v.get('owner', '—'))} | {v.get('prohibition') or '—'} |")
        elif mode == "scene":
            rows.append(f"| `--{k}` | {val} | {v.get('usage', '—')} |")
        else:
            rows.append(f"| `--{k}` | {val} | {v.get('usage', '—')} | {v.get('prohibition') or '—'} |")
    return rows


def render_section2(tokens: dict, total: int) -> list[str]:
    out = [f"## 2. Token 全量参考（共 {total} 个 · 四段口径）", ""]
    c = {s: len(tokens.get(s, {})) for s in ("primitive", "semantic", "component", "metric")}
    out.append(f"计数口径：**基础 {c['primitive']} + 语义 {c['semantic']} + 组件 {c['component']} + 度量 {c['metric']} = {total}**。全文只用这一个口径。")
    out.append("")
    prim = tokens.get("primitive", {})
    out.append(f"### 2.1 基础层 · 颜色（{len(prim)}）")
    out.append("")
    for label, role in PRIM_GROUPS:
        sub = {k: v for k, v in prim.items() if (v or {}).get("role") == role}
        if not sub:
            continue
        out.append(f"{label}（{len(sub)}）：")
        out.append("")
        out.extend(table_rows(sub, "usage"))
        out.append("")
    sem = tokens.get("semantic", {})
    out.append(f"### 2.2 语义层（{len(sem)}）")
    out.append("")
    out.extend(table_rows(sem, "usage"))
    out.append("")
    comp = tokens.get("component", {})
    out.append(f"### 2.3 组件层（{len(comp)}）")
    out.append("")
    out.extend(table_rows(comp, "owner"))
    out.append("")
    met = tokens.get("metric", {})
    out.append(f"### 2.4 度量（{len(met)}）")
    out.append("")
    for label, cat, note in METRIC_GROUPS:
        sub = {k: v for k, v in met.items() if (v or {}).get("category") == cat}
        if not sub:
            continue
        head = f"{label}（{len(sub)}）"
        if note:
            head += f"——**{note}**"
        out.append(head + "：")
        out.append("")
        out.extend(table_rows(sub, "scene"))
        out.append("")
    return out


def render_component_table(components: list) -> list[str]:
    rows = ["| 组件 | 变体 | 状态 | 关键规格 | 禁令 |", "|---|---|---|---|---|"]
    for c in components:
        variants = " / ".join(c.get("variants", [])) or "—"
        states = " · ".join(c.get("states", [])) or "—"
        specs = "; ".join(f"{k} {v}" for k, v in (c.get("key_specs") or {}).items()) or "—"
        rows.append(f"| **{c.get('name', '?')}** | {variants} | {states} | {specs} | {c.get('prohibition') or '—'} |")
    return rows


def regenerate(md: str, norm: dict) -> str:
    tokens = norm.get("tokens", {})
    system = norm.get("system", {})
    name = system.get("name", "示例设计系统")
    ver = system.get("version", "2.0.0")
    date = system.get("date", "")
    counts = {s: len(tokens.get(s, {})) for s in ("primitive", "semantic", "component", "metric")}
    total = sum(counts.values())
    components = norm.get("components", [])
    patterns = norm.get("patterns", {})

    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        L = lines[i]
        m2 = re.match(r"^## 2\. Token 全量参考", L)
        if m2:
            while i < n and not re.match(r"^## 3\.", lines[i]):
                i += 1
            out.extend(render_section2(tokens, total))
            continue
        m6 = re.match(r"^## 6\. 组件契约", L)
        if m6:
            out.append(f"## 6. 组件契约（{len(components)} 个）")
            i += 1
            while i < n and not lines[i].startswith("## "):
                if lines[i].startswith("|"):
                    while i < n and lines[i].startswith("|"):
                        i += 1
                    out.extend(render_component_table(components))
                    out.append("")
                    continue
                out.append(lines[i]); i += 1
            continue
        if lines[i].startswith("## 7. 模式规则"):
            out.append(lines[i]); i += 1
            while i < n and not lines[i].startswith("## "):
                if lines[i].startswith("- **"):
                    i += 1
                    continue
                out.append(lines[i]); i += 1
            for k, v in patterns.items():
                out.append(f"- **{k}**：{v}")
            continue
        # 全局替换行
        L = L.replace("v2.0.0", f"v{ver}")
        if date:
            L = L.replace("2026-10-14", date)
        if L.startswith("# ") and "设计系统规则" in L:
            out.append(f"# {name} 设计系统规则 / {name} Design System Rules")
            i += 1
            continue
        if re.match(r"^> (本例为通用演示数据|本产物由 design-system-extract)", L):
            out.append(f"> 本产物由 design-system-extract 提取生成（v{ver}），来源：{system.get('source', '—')}；计数与命名以项目实测为准。")
            i += 1
            continue
        out.append(L.replace("示例设计系统", name))
        i += 1
    return "\n".join(out)


def main():
    if len(sys.argv) != 3:
        print("用法: python gen_md.py <normalized.json> <out system-rules.md>", file=sys.stderr)
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(filled, encoding="utf-8")
    print(f"[OK] md 产物: {out_path}  ({len(filled)} chars)")
    print("[INFO] §3/§4/§5/§8/§9 正文仍为案例原文，须按项目实测复写（self_check 兜底）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
