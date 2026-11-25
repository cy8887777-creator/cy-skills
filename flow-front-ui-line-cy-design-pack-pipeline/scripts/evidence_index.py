#!/usr/bin/env python3
"""evidence_index — 验收证据索引（1009-17，管线 01/08/14/15 的共同地基）。

每个验收工具运行结束落一行 JSONL（append-only）：
  {tool, target, src_hash, ids, per_id, exit_code, coverage,
   report_path, verdict, time}

**结清规则**：同 src_hash + 同 tool + 同 target 的**最新一次结果为当前
有效态**，旧 FAIL 保留为历史不参与当前判定。

消费方：
  - 1009-01 ⑩证据索引断言：规定工具在本 src_hash 下最新 verdict 全 PASS，
    缺行/FAIL = ⑩ FAIL（check_all）；
  - 1009-15 plan-recon 终验：逐 route_id 查最新 verdict；
  - 1009-08 ⑧批末拦截：读索引，FAIL 未修不进下一批。

命令行：
  python evidence_index.py check --index <jsonl> --src <src> \
      --required style-lint,exits-audit,route-audit,explore-walk
Exit 0 = 索引齐且全 PASS；1 = 缺行或有 FAIL。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def src_hash(src: Path) -> str:
    """工程 src 树内容指纹（相对路径+内容 sha1）——工程任何改动即变，
    用于判定"结果对应哪个版本的工程"。"""
    h = hashlib.sha1()
    for p in sorted(src.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(src)).encode("utf-8", "replace"))
            try:
                h.update(p.read_bytes())
            except OSError:
                pass
    return h.hexdigest()[:16]


class RecordRejected(Exception):
    """1012-06：报告与登记哈希不对应/缺内嵌字段/报告不可读——拒绝入账。

    与「索引 IO 失败不掩盖主判定」豁免语义切割：RecordRejected 是
    **证据本体不可信**，调用方必须显式处置（stderr + exit 置 1），
    禁被裸 except 吞掉。"""


def record(index_path: Path, tool: str, target: str, src: Path,
           ids: list, per_id: dict, exit_code: int, coverage: int,
           report_path: str) -> dict:
    """追加一行索引（由各验收工具在运行结束时调用）。

    1012-06 调用约定（五工具统一）：**先写报告（内嵌 src_hash）再
    record**——本函数读 report_path 报告文件，校验「内嵌 src_hash ==
    自算 src_hash(src)」；报告不存在/缺字段/不一致 → RecordRejected
    （旧报告配新哈希的登记通道就此关闭，不设过渡豁免）。"""
    src_h = src_hash(src) if src.exists() else "no-src"
    rp = Path(report_path) if report_path else None
    rep = None
    if rp is not None:
        try:
            rep = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            rep = None
    if rep is None:
        print(f"evidence-index: {tool} 拒账——报告不可读或缺失"
              f"（{report_path}）；调用顺序须为先写报告后 record（1012-06）",
              file=sys.stderr)
        raise RecordRejected(
            f"{tool}: 报告不可读或缺失（{report_path}）")
    inner = rep.get("src_hash")
    if not inner:
        print(f"evidence-index: {tool} 拒账——报告缺内嵌 src_hash 字段"
              f"（旧格式拒绝，不设过渡豁免，1012-06）", file=sys.stderr)
        raise RecordRejected(
            f"{tool}: 报告缺内嵌 src_hash 字段（旧格式拒绝）")
    if inner != src_h:
        print(f"evidence-index: {tool} 拒账——报告内嵌 src_hash={inner} "
              f"≠ 登记自算 {src_h}（旧报告配新哈希，1012-06）",
              file=sys.stderr)
        raise RecordRejected(
            f"{tool}: 报告内嵌 src_hash={inner} ≠ 登记自算 {src_h}")
    row = {
        "tool": tool,
        "target": target,
        "src_hash": src_h,
        "ids": ids,
        "per_id": per_id,
        "exit_code": exit_code,
        "coverage": coverage,
        "report_path": str(Path(report_path).resolve())
        if report_path else report_path,  # 1012-01 S3：绝对路径落账
        "verdict": "PASS" if exit_code == 0 else "FAIL",
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def latest_valid(index_path: Path, src_h: str, tool: str, target: str):
    """结清规则：同 src_hash+tool+target 的最新一行；无则 None。

    1012-06 双校验：命中账行后读其 report_path 报告，内嵌 src_hash
    ≠ 账行 / 报告不可达 / 缺字段 → **返回 None 视同无记录**
    （fail-closed 最严；禁向前回退次旧行——回退=「删新报告复活旧
    PASS」攻击面）。"""
    if not index_path.is_file():
        return None
    latest = None
    for ln in index_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if row.get("tool") == tool and row.get("target") == str(Path(target).resolve()) \
                and row.get("src_hash") == src_h:
            latest = row  # append-only：后写覆盖
    if latest is None:
        return None
    rp = Path(str(latest.get("report_path", "")))
    try:
        rep = json.loads(rp.read_text(encoding="utf-8"))
    except Exception:
        return None  # 报告不可达 → 该 verdict 无本体背书，视同无记录
    if rep.get("src_hash") != src_h:
        return None  # 内嵌与账行不一致 → 旧报告配新哈希嫌疑，视同无记录
    return latest


def check_all(index_path: Path, src: Path,
              required: list[str]) -> tuple[bool, list[str]]:
    """1009-01 断言：规定工具在本 src_hash 下最新 verdict 全 PASS。"""
    src_h = src_hash(src)
    problems: list[str] = []
    for tool in required:
        row = latest_valid(index_path, src_h, tool, str(src))
        if row is None:
            problems.append(f"{tool}: 本工程版本({src_h})无任何索引记录"
                            "——规定动作未执行或工程已变更未重跑")
        elif row.get("verdict") != "PASS":
            problems.append(f"{tool}: 最新 verdict={row.get('verdict')}"
                            f"（{row.get('time')}）——未修复或未重跑")
        elif not row.get("ids"):
            problems.append(f"{tool}: 索引行覆盖为空（ids 缺失）"
                            "——覆盖不足不得背书")
    return (not problems), problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["check"],
                    help="check=⑩证据索引断言（record 由各工具内嵌调用）")
    ap.add_argument("--index", default="pipeline/evidence_index.jsonl")
    ap.add_argument("--src", required=True, help="工程 src 目录")
    ap.add_argument("--required", default="style-lint,exits-audit,route-audit,e2e-smoke,explore-walk",
                    help="规定验收工具清单（逗号分隔）")
    args = ap.parse_args()
    if args.cmd != "check":
        print("unknown cmd"); return 1
    ok, problems = check_all(Path(args.index), Path(args.src),
                             [x.strip() for x in args.required.split(",")
                              if x.strip()])
    if problems:
        print(f"evidence-index: {len(problems)} 处证据缺口：")
        for x in problems:
            print("  -", x)
        return 1
    print(f"evidence-index: 规定工具在本工程版本下全部 PASS ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
