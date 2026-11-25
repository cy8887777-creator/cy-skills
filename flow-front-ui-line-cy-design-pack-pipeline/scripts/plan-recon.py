#!/usr/bin/env python3
"""plan-recon — PLAN 页面清单 ↔ 冻结路由 ↔ 实现文件 三方对账（⑩，1008-09）。

实测事故：94 图清单全 pending 未回填而站级状态表全 done——铁律 1
形同虚设，断点续跑依据失灵。对账单位 = **④冻结 route_id**（不是
图数量：94 图在④归并为路由页视图，按数量对账不成立）。逐 route_id
核对：

  1. PLAN 清单有行，状态列非 pending（pending 而文件存在 = 漏回填）
  2. 实现文件存在（pending/done 而文件缺失 = 假完成）
  3. 冻结清单每条 route_id 都在 PLAN 有行（漏登记）

route_id ↔ PLAN 行的映射：--map mapping.json（④归并产物，
[{"route_id": "...", "plan_id": "..."}]）；缺省按 route_id == plan_id。
文件匹配（按栈）：react = src/pages/<P<编号>…>.tsx stem 小写以
route_id 开头；vue = src/pages/<slug>.vue（slug 取 path 去 /）。

用法：
  python plan-recon.py --plan pipeline/PLAN.md --routes pipeline/frozen_routes.json \
      --src <工程src> [--stack react|vue] [--map mapping.json]
Exit 0 = 对账通过；1 = 有缺漏。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_plan_rows(plan_path: Path) -> dict[str, str]:
    """表头驱动解析页面清单：返回 {页id: 状态}。"""
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    rows: dict[str, str] = {}
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and "页id" in ln and "状态" in ln:
            header_idx = i
            break
    if header_idx is None:
        return rows
    header = [c.strip() for c in lines[header_idx].strip("|").split("|")]
    id_col = next(j for j, c in enumerate(header) if "页id" in c)
    st_col = next(j for j, c in enumerate(header) if "状态" in c)
    for ln in lines[header_idx + 2:]:  # 跳过 |---| 分隔行
        if not ln.strip().startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) > max(id_col, st_col):
            rows[cells[id_col]] = cells[st_col]
    return rows


def _parse_device_profile(plan_text: str) -> str | None:
    """PLAN execution_policy 节 device_profile 行 → 档名（1012-01/C-09）。
    容忍 plan-template 真实形态：全角冒号/括号注释/行尾说明；解析退化
    （缺节/缺行/空值）返回 None，由调用方 fail-closed。"""
    in_sec = False
    for ln in plan_text.splitlines():
        if ln.startswith("## "):
            in_sec = ln.strip().startswith("## execution_policy")
            continue
        if not in_sec:
            continue
        s = ln.strip()
        if s.startswith("device_profile"):
            s = s.replace("：", ":")
            if ":" not in s:
                return None
            tok = s.split(":", 1)[1].strip()
            tok = tok.split("（", 1)[0].split("(", 1)[0].strip()
            tok = tok.split(" ", 1)[0]
            return tok or None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="PLAN.md 路径")
    ap.add_argument("--routes", required=True,
                    help="④冻结路由清单 json（[{id, path}]）")
    ap.add_argument("--src", required=True, help="工程 src 目录")
    ap.add_argument("--stack", default="react", choices=["react", "vue"])
    ap.add_argument("--map", help="route_id↔plan_id 映射 json（④产出，可选）")
    ap.add_argument("--final", action="store_true",
                    help="⑩终验模式：done/显式降级才过 + 证据索引断言（1009-15/01/17）")
    ap.add_argument("--index", default=None,
                    help="证据索引 jsonl（默认 <src>/../pipeline/evidence_index.jsonl）")
    ap.add_argument("--required",
                    default="style-lint,exits-audit,route-audit,e2e-smoke,explore-walk",
                    help="终验规定验收工具清单（逗号分隔）")
    ap.add_argument("--freeze-fingerprint", action="store_true",
                    help="⑩交付冻结（1012-05）：写 src 内容指纹到 pipeline/"
                         "frozen-src-fingerprint.json——出具交付报告时执行；"
                         "与 --require-frozen 互斥（同给 exit 1，防一跑既"
                         "冻结又核对的机制自洗）")
    ap.add_argument("--require-frozen", action="store_true",
                    help="交付 gate（1012-05）：核对当前 src 指纹 == 报告"
                         "冻结指纹；不一致/指纹缺失/损坏 = FAIL（仅 --final "
                         "下消费；不带它时 --final 行为与现状一致）")
    args = ap.parse_args()
    if args.freeze_fingerprint and args.require_frozen:
        print("plan-recon: --freeze-fingerprint 与 --require-frozen 互斥"
              "（同给 = 一跑既冻结又核对，每次 --final 重写指纹 → 改 src "
              "恒一致，机制自洗，1012-05）")
        return 1

    # —— 1012-05 冻结动作：独立于对账主流程（写指纹+留痕即退）——
    if args.freeze_fingerprint:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from evidence_index import src_hash
        fsrc = Path(args.src)
        if not fsrc.is_dir() or not any(fsrc.rglob("*")):
            print("plan-recon: 空 src 树——无指纹可冻结（fail-closed，1012-05）")
            return 1
        fp = fsrc.parent / "pipeline" / "frozen-src-fingerprint.json"
        existed = fp.is_file()
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps({
            "src_hash": src_hash(fsrc),
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "note": "⑩交付冻结指纹（1012-05）——报告出具时点与工程终态绑定"
                    "（口径=evidence_index.src_hash 单一口径）",
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"plan-recon: 指纹已{'覆盖重写（合法新时点动作，重复 freeze 显式声明）' if existed else '落盘'}"
              f" → {fp}")
        return 0

    frozen = json.loads(Path(args.routes).read_text(encoding="utf-8"))
    mapping = {}
    if args.map:
        mapping = {m["route_id"]: m.get("plan_id", m["route_id"])
                   for m in json.loads(
                       Path(args.map).read_text(encoding="utf-8"))}
    plan_rows = parse_plan_rows(Path(args.plan))
    if not plan_rows:
        print("plan-recon: PLAN 未解析出页面清单（表头须含 页id+状态 列）")
        return 1

    src = Path(args.src)
    if args.stack == "vue":
        impl_names = {p.stem.lower(): p for p in (src / "pages").rglob("*.vue")}
    else:
        impl_names = {p.stem.lower(): p for p in (src / "pages").rglob("*.tsx")}

    def find_impl(route_id: str, path: str):
        if args.stack == "vue":
            slug = path.strip("/").replace("/", "-").lower()
            return impl_names.get(slug)
        rid = route_id.lower()
        for stem, p in impl_names.items():
            if stem.startswith(rid):
                return p
        return None

    violations: list[str] = []
    for r in frozen:
        rid, path = r["id"], r.get("path", "")
        plan_id = mapping.get(rid, rid)
        impl = find_impl(rid, path)
        status = plan_rows.get(plan_id)
        if status is None:
            violations.append(
                f"route {rid}: PLAN 清单无行（plan_id={plan_id}）——漏登记")
            continue
        if status == "pending" and impl is not None:
            violations.append(
                f"route {rid}: PLAN 状态 pending 但实现文件已存在"
                f"（{impl.name}）——漏回填（铁律 1）")
        if status in ("done", "in_progress") and impl is None:
            violations.append(
                f"route {rid}: PLAN 状态 {status} 但实现文件缺失——假完成")
        if args.final:
            # 终验模式（1009-15）：done 或显式降级才过
            if status in ("pending", "in_progress"):
                violations.append(
                    f"route {rid}: 终验时状态 {status}——未完成且无显式降级")
            # 降级后置 = 显式降级（允许），但须带批准标记（批准:来源），
            # 无标记 = 终验 FAIL（1009-15 卡面验收）

    # 证据索引断言（1009-01/17，仅终验模式）
    if args.final:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from evidence_index import check_all, latest_valid, src_hash
        index_path = (Path(args.index) if args.index
                      else src.parent / "pipeline" / "evidence_index.jsonl")
        required = [x.strip() for x in args.required.split(",") if x.strip()]
        src_h = src_hash(src)  # 缓存（禁循环内重算全树 IO——三审性能 smell）
        ok_idx, probs = check_all(index_path, src, required)
        violations.extend(probs)
        # 视口一致性断言（1012-01/C-09）：各报告 viewport == PLAN 档
        VIEWPORT_MAP = {"phone_portrait": (375, 812),
                        "tablet": (820, 1180),
                        "landscape": (1280, 800)}
        profile = _parse_device_profile(
            Path(args.plan).read_text(encoding="utf-8"))
        if profile not in VIEWPORT_MAP:
            violations.append(
                f"device_profile={profile!r} 不在契约档位闭集 "
                f"{sorted(VIEWPORT_MAP)}（PLAN execution_policy 缺失或"
                "破坏，1012-01 fail-closed）")
        else:
            ew, eh = VIEWPORT_MAP[profile]
            for tool in required:
                if tool in ("style-lint",):
                    continue  # 无浏览器，视口豁免集（S1 定标）
                row = latest_valid(index_path, src_h, tool, str(src))
                if row is None:
                    continue  # 缺行已由 check_all 报，不重复计
                rp = Path(row.get("report_path", ""))
                try:
                    rep = json.loads(rp.read_text(encoding="utf-8"))
                except Exception:
                    violations.append(
                        f"{tool}: 报告文件不可读（{rp}）——视口核对"
                        "fail-closed（1012-01）")
                    continue
                vp = rep.get("viewport")
                if (not isinstance(vp, dict) or vp.get("width") != ew
                        or vp.get("height") != eh):
                    violations.append(
                        f"{tool}: 报告视口 {vp!r} ≠ device_profile="
                        f"{profile} 档（{ew}x{eh}）——视口静默兜底或"
                        "传参缺失（1012-01）")
        # 报告冻结指纹核对（1012-05，仅 --require-frozen 时消费；
        # src_h 用 final 分支开头缓存，禁循环内重算）
        if args.require_frozen:
            fp = src.parent / "pipeline" / "frozen-src-fingerprint.json"
            if not fp.is_file():
                violations.append(
                    "frozen-src-fingerprint.json 不存在——报告未冻结即未"
                    "完成交付准备（正常流程=出具报告时落指纹；1012-05 "
                    "fail-closed）")
            else:
                try:
                    fh = json.loads(
                        fp.read_text(encoding="utf-8")).get("src_hash")
                except Exception:
                    fh = None
                if not fh:
                    violations.append(
                        "指纹文件损坏或缺 src_hash 字段（fail-closed，"
                        "1012-05）")
                elif fh != src_h:
                    violations.append(
                        f"当前 src 指纹 {src_h} ≠ 报告冻结指纹 {fh}"
                        "——报告出具后工程仍被改动：重跑全部工具重出"
                        "数字（1012-05，对齐清场 (c)）")
        # src_h 已在 final 分支开头算好缓存（1012-01 修复：视口核对段
        # 先于原赋值点消费 src_h，原位置会 NameError）
        # 逐 route_id 关联最新 verdict；查不到即 FAIL（1009-15 卡面：
        # "查不到或 FAIL 不通过"——查不到静默通过=覆盖不足放行）
        # 键域（五审）：exits-audit per_id 键=route path；route_id→path
        # 由 frozen 清单本身提供（C-01 契约），查询双认 rid/path
        for r in frozen:
            rid, path = r["id"], r.get("path", "")
            seen = False
            for tool in ("exits-audit", "route-audit"):
                row = latest_valid(index_path, src_h, tool, str(src))
                if row is None:
                    continue
                per_id = row.get("per_id") or {}
                v = per_id.get(rid) or per_id.get(path)
                if v is None:
                    continue
                seen = True
                if v == "FAIL":
                    violations.append(
                        f"route {rid}: 索引最新 verdict=FAIL（tool={tool}）"
                        "——未修复或未重跑")
            if not seen:
                violations.append(
                    f"route {rid}: 证据索引无任何 verdict——覆盖不足放行")
        # 降级批准标记检查（三审 spec#3：卡面验收"降级无批准 FAIL"）
        for r in frozen:
            rid = r["id"]
            plan_id = mapping.get(rid, rid)
            status = plan_rows.get(plan_id)
            if status == "降级后置":
                plan_path = Path(args.plan)
                line = next((ln for ln in plan_path.read_text(
                    encoding="utf-8").splitlines()
                    if ln.strip().startswith("|") and plan_id in ln), "")
                if "批准:" not in line:  # 带冒号——"未获批准"不误判已批准（复审建议）
                    violations.append(
                        f"route {rid}: 降级后置无批准标记（PLAN 偏差列须含"
                        "批准:来源）")

    if violations:
        print(f"plan-recon: {len(violations)} 处对账缺漏：")
        for v in violations[:40]:
            print("  -", v)
        return 1
    print(f"plan-recon: 冻结 {len(frozen)} 条 route_id 三方对账通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
