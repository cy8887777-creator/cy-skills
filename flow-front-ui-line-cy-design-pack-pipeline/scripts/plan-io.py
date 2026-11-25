#!/usr/bin/env python3
"""plan-io — PLAN.md 表格读写/统计（管线状态回填与汇总，确定性）。

表头驱动：状态/偏差列按表头列名定位——加列不破坏读写；
旧格式（无"组"列）与新格式（7 列）均兼容。

用法：
  python plan-io.py stats <PLAN.md>                    # 进度统计
  python plan-io.py set <PLAN.md> <页id> <状态> [偏差]  # 回填单页状态
  python plan-io.py pending <PLAN.md>                  # 列出未完成页
状态机：pending / in_progress / done / failed / 降级后置
"""
from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VALID = {"pending", "in_progress", "done", "failed", "降级后置"}


def _split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(cells) -> bool:
    return all(c and set(c) <= set("-: ") for c in cells)


def _table(text: str):
    """→ (col: 列名→索引, rows: 页行单元格列表)。"""
    col: dict[str, int] = {}
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _split_row(line)
        if _is_sep(cells):
            continue
        if not col:  # 第一条非分隔行 = 表头
            col = {name: i for i, name in enumerate(cells)}
            continue
        if cells and cells[0].startswith("p"):
            rows.append(cells)
    return col, rows


def _need(col: dict, name: str) -> int:
    if name in col:
        return col[name]
    raise SystemExit(f"PLAN.md 表头缺少列「{name}」（现有列={list(col)}）")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__); return 1
    op, path = sys.argv[1], sys.argv[2]
    text = open(path, encoding="utf-8").read()
    col, rows = _table(text)
    if not col:
        print("PLAN.md 无表格"); return 1
    i_pid = _need(col, "页id")
    i_status = _need(col, "状态")
    i_dev = _need(col, "偏差")

    if op == "stats":
        by: dict[str, int] = {}
        for c in rows:
            by[c[i_status]] = by.get(c[i_status], 0) + 1
        print("total:", len(rows), "|", by)
        return 0

    if op == "pending":
        for c in rows:
            if c[i_status] in ("pending", "in_progress", "failed"):
                print(c[i_pid], c[i_status])
        return 0

    if op == "set":
        if len(sys.argv) < 5:
            print("set needs: <PLAN.md> <页id> <状态> [偏差]"); return 1
        pid, status = sys.argv[3], sys.argv[4]
        dev = sys.argv[5] if len(sys.argv) > 5 else ""
        if status not in VALID:
            print(f"invalid status: {status} (valid: {sorted(VALID)})"); return 1
        lines = text.splitlines()
        hit = False
        for i, line in enumerate(lines):
            if not line.lstrip().startswith("|"):
                continue
            cells = _split_row(line)
            if _is_sep(cells) or len(cells) <= i_pid:
                continue
            if cells[i_pid] == pid:
                need = max(i_status, i_dev) + 1
                while len(cells) < need:
                    cells.append("")
                cells[i_status], cells[i_dev] = status, dev
                lines[i] = "| " + " | ".join(cells) + " |"
                hit = True
                break
        if not hit:
            print(f"row not found: {pid}"); return 1
        open(path, "w", encoding="utf-8", newline="").write(
            "\n".join(lines) + "\n")
        print(f"set {pid} -> {status}")
        return 0

    print("unknown op"); return 1


if __name__ == "__main__":
    sys.exit(main())
