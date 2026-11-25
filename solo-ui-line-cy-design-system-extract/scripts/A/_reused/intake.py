#!/usr/bin/env python3
"""盘点 — 图包文件名解析（管线①站，确定性，零看图）。

解析 `编号-页面名[-状态].png` 命名 → 图级清单；同编号图仅标 group
分组提示（**不在本站合并**——文件名不可信，真实归并在④整合同页
状态站，PRD states 背书后执行）。标记 modal（「弹-」前缀）与长图
（h/w > 2.2），产出：
  pages.manifest.json   图级清单（每图 id/组/类型/尺寸/long_page）
  PLAN.md               执行计划初稿（每图一行；④站归并后更新为路由页视图）

用法：python intake.py <图包目录> <工程目录> [--project-name NAME]
       python intake.py <图包目录> --probe   # 设备形态探针（1010-04）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # 1012-02：stderr 承载人类摘要，同 UTF-8 口径

NAME_RE = re.compile(r"^(\d+)\s*[-–—]\s*(.+?)(?:\s*[–—-]\s*(\d+))?\.(png|jpe?g|webp)$", re.I)


def scan(fig_dir: Path):
    images: list[dict] = []
    unparsed: list[str] = []
    for f in sorted(fig_dir.iterdir()):
        m = NAME_RE.match(f.name)
        if not m:
            if f.is_file() and not f.name.startswith("."):
                unparsed.append(f.name)
            continue
        num = int(m.group(1))
        title = m.group(2).strip()
        state = (m.group(3) or "").strip()
        from PIL import Image
        with Image.open(f) as im:
            w, h = im.size
        images.append({
            "id": f"p{num:03d}-{state or 'default'}",
            "num": num, "title": title, "state": state or "default",
            "file": f.name, "w": w, "h": h,
            "type": "modal" if (title.startswith("弹-") or "-弹" in title) else "page",
            "long_page": h / max(w, 1) > 2.2,
        })
    # group 分组提示：同编号 ≥2 张 → 共享 g<编号>；单图不标（不合并）
    counts = Counter(im["num"] for im in images)
    for im in images:
        if counts[im["num"]] > 1:
            im["group"] = f"g{im['num']:03d}"
    # 撞 id 防御：同编号同状态不同标题 → 序号后缀（p001-default-2）
    id_seen: dict[str, int] = {}
    for im in images:
        n = id_seen.get(im["id"], 0) + 1
        id_seen[im["id"]] = n
        if n > 1:
            im["id"] = f"{im['id']}-{n}"
            im["dup_renamed"] = True
    return images, unparsed


# ── 设备形态探针（1010-04，零 VLM/token：本地 PIL 读图头比例分布）──
# 分带定标（测试标准定稿）：ratio=w/h
BAND_PHONE_MAX = 0.60     # < 0.60 → 手机竖屏带（实机区间 0.44~0.562）
BAND_TABLET_MAX = 0.90    # 0.60~0.90 → Pad 带（0.657~0.75 实机）；0.90~1.10 灰带
BAND_SQUARE_MAX = 1.10    # 灰带上界（方形=非标准设备截图，出现即 low）
HIGH_CONF_SHARE = 85.0    # 主导带占比 ≥85%（含等号）才允许 high
MIN_SAMPLE = 3            # 样本下限：n<3 禁 high（一锤定音决策保守侧）
LONG_PAGE_HW = 2.2        # 长图阈值与 scan 同源——归一记 1/2.2 入竖带，防双口径
VIEWPORTS = {             # form → 验收视口档（三档制：横 Pad 归 landscape）
    "phone_portrait": {"width": 375, "height": 812},
    "tablet": {"width": 820, "height": 1180},
    "landscape": {"width": 1280, "height": 800},
}
BAND_TO_FORM = {"portrait": "phone_portrait", "tablet": "tablet",
                "landscape": "landscape", "square": "tablet"}


def probe_device(fig_dir: Path) -> int:
    """图包宽高比分布 → 设备形态推断（不落盘不碰工程目录）。
    接口口径（1012-02）：**stdout = 单行 JSON**（机器解析唯一对象）；
    **stderr = 人类摘要与错误提示**（人读不混入机器通道）。"""
    images, unparsed = scan(fig_dir)
    if not images:
        print(f"probe: 可解析图片 0 张（unparsed {len(unparsed)}）——"
              "图包路径错或命名不合规，不输出推断", file=sys.stderr)
        return 2
    dist: Counter = Counter()
    for im in images:
        r = im["w"] / max(im["h"], 1)
        if im["long_page"]:
            r = 1 / LONG_PAGE_HW
        if r < BAND_PHONE_MAX:
            dist["portrait"] += 1
        elif r < BAND_TABLET_MAX:
            dist["tablet"] += 1
        elif r <= BAND_SQUARE_MAX:
            dist["square"] += 1
        else:
            dist["landscape"] += 1
    n = len(images)
    form_band, dominant = dist.most_common(1)[0]
    share = dominant / n * 100
    has_square = dist.get("square", 0) > 0
    conf = ("high" if share >= HIGH_CONF_SHARE
            and n >= MIN_SAMPLE and not has_square else "low")
    form = BAND_TO_FORM[form_band]
    print(json.dumps({
        "form": form, "confidence": conf,
        "confidence_score": round(share, 1),
        "viewport": VIEWPORTS[form],
        "evidence": {"n_images": n, "dominant_band": form_band,
                     "dominant_share": round(share, 1),
                     "band_dist": dict(dist)},
    }, ensure_ascii=False))
    print(f"推断：{form}（置信 {conf}，主导带 {share:.1f}%）——"
          "表单「目标设备」项默认值依据；低置信该项必答，禁默认跳过",
          file=sys.stderr)  # 1012-02：人类摘要迁 stderr，stdout 保单行 JSON
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fig_dir")
    ap.add_argument("project_dir", nargs="?", default=None,
                    help="工程根目录（写 pipeline/ 与 manifest；--probe 时可省）")
    ap.add_argument("--project-name", default=None,
                    help="项目名（默认取图包目录名——技能内不内置任何"
                         "项目专属默认名）")
    ap.add_argument("--probe", action="store_true",
                    help="设备形态探针：读图头比例分布输出推断 JSON"
                         "（不落盘；激活协议 AskUser #1 后 #2 前本地执行）")
    args = ap.parse_args()

    fig_dir = Path(args.fig_dir)
    if args.probe:
        if not fig_dir.is_dir():
            print(f"图包目录不存在: {fig_dir}", file=sys.stderr)  # 1012-02：错误路径同迁 stderr
            return 1
        return probe_device(fig_dir)
    if not args.project_dir:
        print("缺少工程目录参数（仅探测设备形态请加 --probe）")
        return 1
    proj = Path(args.project_dir)
    if not fig_dir.is_dir():
        print(f"图包目录不存在: {fig_dir}"); return 1
    project_name = args.project_name or fig_dir.resolve().name

    images, unparsed = scan(fig_dir)
    (proj / "pipeline").mkdir(parents=True, exist_ok=True)

    manifest = {"project": project_name, "source_dir": str(fig_dir),
                "images": images}
    (proj / "pipeline" / "pages.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # PLAN.md 初稿（图级一行一图；④站归并后更新为路由页视图）
    rows = "\n".join(
        f"| {im['id']} | {im.get('group', '')} | {im['file']} | "
        f"(待盘点) | (待盘点) | pending | |"
        for im in images)
    plan = (Path(__file__).resolve().parent.parent / "templates"
            / "plan-template.md")
    plan_text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    plan_text = (plan_text
                 .replace("{{PROJECT_NAME}}", project_name)
                 .replace("{{PAGES_TABLE}}", rows)
                 .replace("{{TOTAL}}", str(len(images))))
    (proj / "pipeline" / "PLAN.md").write_text(plan_text, encoding="utf-8")

    n_grouped = sum(1 for im in images if im.get("group"))
    n_dup = sum(1 for im in images if im.get("dup_renamed"))
    print(f"盘点 done: {len(images)} images "
          f"({n_grouped} 张属同编号组待④归并, {n_dup} 张撞 id 已加后缀), "
          f"{len(unparsed)} unparsed")
    if not images:
        # 空图包 gate（八轮评审）：零张图 = 图包路径错/目录空——
        # 写空 manifest 让人检查，但 exit 2 硬信号，不放行
        print("GATE: 图包解析出 0 张图片 —— 检查图包目录是否给错"
              "（空 manifest 已落盘供检查）")
        return 2
    if unparsed:
        # gate 硬信号：产物已落盘供人工检查，但零未知命名未达成
        print(f"GATE: {len(unparsed)} 个未知命名 —— 人工确认后方可冻结")
        for u in unparsed:
            print(f"  UNPARSED: {u}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
