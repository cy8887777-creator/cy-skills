"""
scripts/core/schema.py — JSON Schema 校验（中间表契约守卫）

用法：
    python scripts/core/schema.py validate <middle.json>
    python scripts/core/schema.py count <middle.json> [--expect-total N]
退出码：0 PASS / 1 REVIEW / 2 FAIL

**计数纪律（2026-10-15 修正，与 self_check counts 件套同源）**：
schema 校验只管结构合法；计数**只报实测**——85/19/17/6/43 是演示案例实测值
（CASE_REFERENCE），真实项目以实测为准，仅案例回归传 --expect-total 85 硬校验。
"""
import json
import sys
from pathlib import Path
from collections import Counter

# 演示案例实测值——**参考，不是及格线**
CASE_REFERENCE = {
    "primitive": 19,   # 案例：主色 2 + 主色辅助 3 + 中性 8 + 功能 6
    "semantic": 17,    # 案例：含 stroke_color 2
    "component": 6,    # 案例
    "metric": 43,      # 案例
}

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "sample-input" / "middle.schema.json"


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        print(f"[FAIL] schema 不存在: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(2)
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_data(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[FAIL] 数据文件不存在: {p}", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def validate(data_path: str) -> int:
    """校验 middle.json 符合 schema + 4 段计数符合权威口径"""
    try:
        import jsonschema
    except ImportError:
        print("[FAIL] 缺 jsonschema：pip install jsonschema", file=sys.stderr)
        return 2

    schema = load_schema()
    data = load_data(data_path)

    # 1) Schema 校验
    try:
        jsonschema.validate(data, schema)
        print("[PASS] schema 校验通过")
    except jsonschema.ValidationError as e:
        print(f"[FAIL] schema 校验失败: {e.message}", file=sys.stderr)
        return 2

    # 2) 4 段计数只报实测（结构合法 ≠ 数量等于案例值）
    actual = {seg: len(data.get("tokens", {}).get(seg, {})) for seg in CASE_REFERENCE}
    total = sum(actual.values())
    print(f"[INFO] 4 段实测: {actual} 合计 {total}（案例参考 {sum(CASE_REFERENCE.values())}，真实项目以实测为准）")

    for seg in CASE_REFERENCE:
        if actual[seg] == 0:
            print(f"[REVIEW] {seg} 段实测为 0——提取无证据，需人决", file=sys.stderr)
            return 1
    return 0


def count(data_path: str, expect_total=None) -> int:
    """打印 4 段实测计数与分类细分；仅 --expect-total 传入时硬校验总数"""
    data = load_data(data_path)
    tokens = data.get("tokens", {})
    print(f"=== 4 段计数（实测）===")
    for seg in CASE_REFERENCE:
        n = len(tokens.get(seg, {}))
        print(f"  {seg:10s}: {n:3d}  (案例参考 {CASE_REFERENCE[seg]:3d})")
    total = sum(len(tokens.get(seg, {})) for seg in CASE_REFERENCE)
    flag = ""
    rc = 0
    if expect_total is not None:
        ok = total == expect_total
        flag = f"  [{'OK' if ok else 'REVIEW'}]"
        rc = 0 if ok else 1
    print(f"  {'TOTAL':10s}: {total:3d}{flag}")
    print()
    print(f"=== metric 段按 category 细分 ===")
    metric = tokens.get("metric", {})
    cats = Counter(t.get("category", "?") for t in metric.values())
    for c, n in sorted(cats.items()):
        print(f"  {c:18s}: {n}")
    return rc


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("validate", "count"):
        print("用法: python schema.py validate|count <middle.json> [--expect-total N]")
        sys.exit(1)
    cmd, data_path = sys.argv[1], sys.argv[2]
    if cmd == "validate":
        sys.exit(validate(data_path))
    elif cmd == "count":
        expect = None
        if "--expect-total" in sys.argv:
            expect = int(sys.argv[sys.argv.index("--expect-total") + 1])
        sys.exit(count(data_path, expect))


if __name__ == "__main__":
    main()
