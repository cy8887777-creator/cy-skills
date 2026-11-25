"""
scripts/C/figma_ingest.py — C-1 Figma 工具 JSON 消费

复用：标准 JSON 解析（**不自造** Figma 解析器）
输入：Figma 工具（Atomize 类）导出的 JSON
产出：out/middle.json（按 middle.schema.json）

规则（SKILL.md 站 ② C-1）：
  1. Figma Variables → 基础层 + 语义层
  2. Figma Styles → 组件层候选
  3. Components（若 JSON 含）→ 组件清单
"""
import json
import sys
from pathlib import Path


def ingest(figma_json_path: Path) -> dict:
    data = json.loads(figma_json_path.read_text(encoding="utf-8"))

    # Figma 工具导出格式：Variables 数组 + Styles 数组 + Components 数组
    variables = data.get("variables", data.get("Variables", []))
    styles = data.get("styles", data.get("Styles", []))
    components = data.get("components", data.get("Components", []))

    middle = {
        "meta": {
            "source_type": "C1_figma",
            "source_id": figma_json_path.stem,
            "extracted_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "2.0.0",
        },
        "tokens": {"primitive": {}, "semantic": {}, "component": {}, "metric": {}},
        "components": [],
        "patterns": {},
        "raw_evidence": {
            "figma_variables_count": len(variables),
            "figma_styles_count": len(styles),
            "figma_components_count": len(components),
        },
    }

    # 简化映射：
    # Variables: [{name, type, value}] → 基础层
    for v in variables:
        name = v.get("name", v.get("Name", ""))
        value = v.get("value", v.get("Value", ""))
        vtype = v.get("type", v.get("Type", "color"))
        if vtype == "color":
            middle["tokens"]["primitive"][name] = {
                "value": value, "role": "neutral", "usage": "Figma Variable", "prohibition": ""
            }
        else:
            middle["tokens"]["metric"][name] = {
                "value": value, "category": vtype, "usage": "Figma Variable"
            }

    # Styles → 语义层
    for s in styles:
        name = s.get("name", s.get("Name", ""))
        value = s.get("value", s.get("Value", ""))
        middle["tokens"]["semantic"][name] = {
            "value": value, "category": "text", "usage": "Figma Style", "prohibition": ""
        }

    # Components → 组件清单
    for c in components:
        middle["components"].append({
            "name": c.get("name", c.get("Name", "?")),
            "variants": c.get("variants", []),
            "states": c.get("states", []),
            "key_specs": c.get("specs", {}),
        })

    return middle


def main():
    if len(sys.argv) < 2:
        print("用法: python figma_ingest.py <figma_export.json> [out_middle.json]", file=sys.stderr)
        sys.exit(1)
    figma_path = Path(sys.argv[1])
    if not figma_path.exists():
        print(f"[FAIL] {figma_path} 不存在", file=sys.stderr)
        sys.exit(2)

    middle = ingest(figma_path)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out/middle.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(middle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {figma_path.name} → {out}")
    print(f"  primitive: {len(middle['tokens']['primitive'])}")
    print(f"  semantic:  {len(middle['tokens']['semantic'])}")
    print(f"  metric:    {len(middle['tokens']['metric'])}")
    print(f"  components: {len(middle['components'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
