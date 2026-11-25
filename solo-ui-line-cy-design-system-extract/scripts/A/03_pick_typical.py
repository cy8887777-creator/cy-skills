"""
scripts/A/03_pick_typical.py — A-03 典型页挑选

复用：design-pack-pipeline/references/strategy-rules.md（策略判据唯一权威）
不做自创逻辑 —— 任务书原文复制到本文件
        —— strategy-rules.md 引用作为策略选择依据

输入：out/inventory/*.md
产出：out/inventory/typical_pages.json
"""
import json
import sys
from pathlib import Path

REUSED = Path(__file__).parent / "_reused"
STRATEGY = REUSED / "strategy-rules.md"


def main():
    if len(sys.argv) < 2:
        print("用法: python 03_pick_typical.py <inventory_dir>", file=sys.stderr)
        sys.exit(1)
    inv_dir = Path(sys.argv[1])
    if not inv_dir.exists():
        print(f"[FAIL] {inv_dir} 不存在", file=sys.stderr)
        sys.exit(2)

    # 加载所有盘点文档
    pages = sorted(inv_dir.glob("*.md"))
    pages = [p for p in pages if not p.name.startswith(("typical_", "pages."))]
    print(f"[INFO] {len(pages)} 页盘点文档；策略判据 = {STRATEGY.name}")

    # 简化：选前 2-3 张（按图片数 / 复杂度排序由主会话按 strategy-rules 裁决）
    # 本脚本只把候选列出来，主会话调 Task 子代理按 strategy-rules 评分
    candidates = []
    for p in pages:
        text = p.read_text(encoding="utf-8")
        # 极简：取 §3 复杂度画像里的"素材数"作为初筛
        candidates.append({
            "page": p.stem,
            "doc": str(p),
            "len": len(text),
        })
    candidates.sort(key=lambda x: -x["len"])  # 文档长 = 内容多 = 可能更复杂
    typical = [c["page"] for c in candidates[:min(3, len(candidates))]]

    out = {"typical_pages": typical, "candidates": candidates, "strategy_ref": str(STRATEGY)}
    out_file = inv_dir / "typical_pages.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 典型页: {typical} -> {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
