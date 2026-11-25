"""
scripts/core/tokenize.py — 体系化（middle.json → normalized.json）

输入：out/middle.json（6 路引擎产出，schema 已校验）
输出：out/normalized.json（4 段 token + 组件清单 + 模式）

规则：
- 4 段 token 命名去重
- 缺命名补 demo 值（参考 templates/system-rules.md 占位逻辑）
- 必含项断言：success/warning/danger、focus-ring、font-family-base、--space-4/6/8
- 输出口径与 schema 完全一致
"""
import json
import sys
from pathlib import Path
from collections import Counter
from copy import deepcopy

# 必含项（演示版标准；项目实提取后值可改，键名不可改）
MUST_HAVE = {
    "primitive": ["blue-600", "blue-700", "success", "warning", "danger", "gray-900", "gray-50"],
    "semantic": ["color-text-primary", "color-bg-page", "color-border", "focus-ring",
                 "font-family-base", "line-height-body", "color-action-primary"],
    "component": ["button-bg-primary", "button-bg-danger", "tag-bg-brand"],
    "metric": ["space-1", "space-2", "space-3", "space-4", "space-6", "space-8", "space-12",
               "radius-sm", "radius-md", "radius-lg",
               "font-size-body", "font-size-caption", "font-size-title",
               "shadow-sm", "shadow-md", "shadow-lg", "z-dropdown", "z-modal", "z-toast"],
}


def load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[FAIL] 缺文件: {p}", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def save(path: str, data: dict):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 写入 {path}")


def deduplicate_names(tokens: dict) -> tuple[dict, list[str]]:
    """去重同名 token，重复改名加后缀 _2/_3/..."""
    seen = {}
    renamed = []
    for seg in tokens:
        new = {}
        for k, v in tokens[seg].items():
            if k in seen:
                # 改名：原 key_2 / key_3 ...
                i = 2
                while f"{k}_{i}" in seen or f"{k}_{i}" in new:
                    i += 1
                new_key = f"{k}_{i}"
                seen[new_key] = seg
                renamed.append(f"{seg}.{k} -> {new_key}")
                new[new_key] = v
            else:
                seen[k] = seg
                new[k] = v
        tokens[seg] = new
    return tokens, renamed


def check_must_have(tokens: dict) -> list[str]:
    """必含项断言；缺则报告（不强行补 demo）"""
    missing = []
    for seg, keys in MUST_HAVE.items():
        actual = set(tokens.get(seg, {}).keys())
        for k in keys:
            if k not in actual:
                missing.append(f"{seg}.{k}")
    return missing


def tokenize(middle_path: str, out_path: str) -> int:
    data = load(middle_path)
    tokens = deepcopy(data.get("tokens", {}))

    # 1) 去重
    tokens, renamed = deduplicate_names(tokens)
    if renamed:
        print(f"[INFO] 去重改名 {len(renamed)} 个：")
        for r in renamed[:10]:
            print(f"  - {r}")
        if len(renamed) > 10:
            print(f"  ... +{len(renamed) - 10} 个")

    # 2) 必含项
    missing = check_must_have(tokens)
    if missing:
        print(f"[REVIEW] 必含项缺失 {len(missing)} 个：", file=sys.stderr)
        for m in missing[:20]:
            print(f"  - {m}", file=sys.stderr)
        if len(missing) > 20:
            print(f"  ... +{len(missing) - 20} 个", file=sys.stderr)

    # 3) 组装 normalized
    normalized = {
        "system": {
            "name": data.get("system", {}).get("name", "示例设计系统"),
            "version": data.get("system", {}).get("version", "2.0.0"),
            "date": data.get("system", {}).get("date", "2026-10-14"),
            "source": data.get("meta", {}).get("source_id", ""),
            "source_type": data.get("meta", {}).get("source_type", ""),
        },
        "tokens": tokens,
        "components": data.get("components", []),
        "patterns": data.get("patterns", {}),
        "assets": data.get("raw_evidence", {}).get("art_assets", [])[:80],
        "raw_evidence": data.get("raw_evidence", {}),
        "token_count_summary": {
            seg: len(tokens.get(seg, {}))
            for seg in ("primitive", "semantic", "component", "metric")
        },
    }
    normalized["token_count_summary"]["total"] = sum(
        normalized["token_count_summary"][s]
        for s in ("primitive", "semantic", "component", "metric")
    )

    save(out_path, normalized)

    # 4) 报告
    print(f"\n=== 体系化结果 ===")
    for seg, n in normalized["token_count_summary"].items():
        if seg != "total":
            print(f"  {seg:10s}: {n}")
    print(f"  {'TOTAL':10s}: {normalized['token_count_summary']['total']}")
    print(f"  components: {len(normalized['components'])}")
    print(f"  patterns:   {len(normalized['patterns'])}")

    return 1 if missing else 0


def main():
    if len(sys.argv) != 3:
        print("用法: python tokenize.py <middle.json> <normalized.json>")
        sys.exit(1)
    sys.exit(tokenize(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
