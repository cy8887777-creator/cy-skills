#!/usr/bin/env python3
"""contracts-lint — 写码 DoD 确定性检查（管线安全网，每页交付+⑧各跑）。

只做**可靠确定性**检查，三类伪断言明确不做：
  ✗ intent 计数 == PRD 行为条数（数量相等也可能全接错——语义映射归任务书）
  ✗ 脆弱正则判"内联实体"（误报源；实体引用只作统计信息项）
  ✗ 组件引用率作硬 PASS（零引用组件是审查项非违规项）

硬 FAIL 项：
  1. data-route 挂载：页面文件须挂 data-route 且值 ∈ 路由清单
     （页面含多个 data-route 锚点时任一命中即可——多态页共用根锚点）
  2. 路由清单一致性：routes.json 声明的每条路由都有页面挂载对应锚点
  3. 命名/目录约定（按栈适配，1008-07）+ 页面 mock 外置硬检查：
     react: src/pages/P<编号><语义>.tsx + src/mocks/pages/<同名>.ts
     vue:   src/pages/<slug>.vue（kebab-case）+ src/mocks/pages/<slug>.ts
  4. 占位字样（1010-03）：页面与 mock 禁 lorem/测试数据/示例数据/占位
     内容/xxx 类占位内容（注释行豁免）——补页"像真产品"标准的机器兜底

信息项（只统计不判 PASS）：entities 引用分布、data-intent 计数。

DOM 层断言（data-route/mock 外置）与框架无关；栈差异只在文件形态，
经 --stack 适配（1008-07 分层：脚本逻辑通用，形态表按栈）。

用法：
  python contracts-lint.py --src <工程src> --routes <routes.json> \
      [--stack react|vue] [--out report.json]
Exit 0 = 通过；1 = 有硬违规。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_ROUTE_RE = re.compile(r'''data-route(?:="([^"]+)"|=true)?''')
ENTITIES_IMPORT_RE = re.compile(
    r'''from\s+['"][^'"]*mocks/entities['"]''')

# 栈形态适配表（1008-07：强绑定收敛到这一处，其余逻辑栈无关）
STACKS = {
    "react": {
        "glob": "*.tsx",
        "page_file_re": re.compile(r"^P\d{3,4}[\w-]*\.tsx$"),
        "mock_ext": ".ts",
        "label": "P<编号><语义>.tsx",
    },
    "vue": {
        "glob": "*.vue",
        "page_file_re": re.compile(r"^[a-z0-9][a-z0-9-]*\.vue$"),
        "mock_ext": ".ts",
        "label": "<slug>.vue（kebab-case）",
    },
}


def page_files(src: Path, stack: dict) -> list[Path]:
    return sorted((src / "pages").rglob(stack["glob"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="工程 src 目录")
    ap.add_argument("--routes", required=True,
                    help="路由清单 json（[{id, path}]，manifest/源码同源产出）")
    ap.add_argument("--stack", default="react", choices=sorted(STACKS),
                    help="栈形态适配（默认 react；文件形态差异唯一分歧点）")
    ap.add_argument("--out", default="contracts_lint_report.json")
    args = ap.parse_args()

    src = Path(args.src)
    stack = STACKS[args.stack]
    routes = json.loads(Path(args.routes).read_text(encoding="utf-8"))
    route_paths = {r["path"] for r in routes}

    violations: list[str] = []
    info: dict = {}

    # 1) data-route 挂载：每页须挂载且值 ∈ 路由清单
    pages = page_files(src, stack)
    if not pages:
        print(f"contracts-lint: 未找到页面 {stack['glob']}"); return 1
    mounted: dict[str, str] = {}
    texts: dict[str, str] = {}
    for p in pages:
        text = p.read_text(encoding="utf-8", errors="replace")
        texts[p.name] = text
        hits = DATA_ROUTE_RE.findall(text)
        if not hits:
            violations.append(f"{p.name}: 未挂载 data-route（写码 DoD 第 1 条）")
            continue
        # 任一 data-route 值命中路由清单即通过（多态页共用根锚点）
        for h in hits:
            if h and h in route_paths:
                mounted[p.name] = h
                break
        else:
            violations.append(
                f"{p.name}: data-route 值 {hits[:2]} 不在路由清单内")

    missing_route = route_paths - set(mounted.values())
    for m in sorted(missing_route):
        violations.append(f"路由 {m} 无任何页面挂载对应 data-route")

    # 2) 命名约定（按栈适配）+ 页面 mock 文件外置存在性（硬检查）
    for p in pages:
        if not stack["page_file_re"].match(p.name):
            violations.append(
                f"命名违规: {p.name}（应为 {stack['label']}）")
        mock_ts = src / "mocks" / "pages" / (p.stem + stack["mock_ext"])
        if not mock_ts.is_file():
            violations.append(
                f"{p.name}: 缺页面 mock src/mocks/pages/{p.stem}{stack['mock_ext']}"
                "（mock 外置硬检查）")

    # 3) 占位字样（1010-03：页面与 mock 禁占位内容——内容真实感，写手
    #    自查+机器兜底；注释行豁免防误报）
    PLACEHOLDER_RE = re.compile(
        r"lorem|ipsum|测试(数据|文案)|示例(数据|文本|文案)|假数据"
        r"|占位(文本|内容|文字|数据)|xxx", re.IGNORECASE)
    COMMENT_LINE_RE = re.compile(r"^\s*(//|/\*|\*|<!--|#)")
    for p in pages:
        for i, line in enumerate(texts[p.name].splitlines(), 1):
            if COMMENT_LINE_RE.match(line):
                continue
            m = PLACEHOLDER_RE.search(line)
            if m:
                violations.append(
                    f"{p.name}:{i}: 占位字样「{m.group(0)}」"
                    "（写码 DoD：内容真实感禁占位）")
        mock_ts = src / "mocks" / "pages" / (p.stem + stack["mock_ext"])
        if mock_ts.is_file():
            for i, line in enumerate(
                    mock_ts.read_text(encoding="utf-8",
                                      errors="replace").splitlines(), 1):
                if COMMENT_LINE_RE.match(line):
                    continue
                m = PLACEHOLDER_RE.search(line)
                if m:
                    violations.append(
                        f"mocks/pages/{mock_ts.name}:{i}: 占位字样"
                        f"「{m.group(0)}」（mock 须实体化真实感）")

    # 4) 信息项：entities 引用 / data-intent 计数（只统计，不判 PASS）
    ent_pages = sum(1 for n, t in texts.items()
                    if ENTITIES_IMPORT_RE.search(t))
    intent_count = sum(t.count("data-intent") for t in texts.values())
    info["pages"] = len(pages)
    info["pages_importing_entities"] = ent_pages
    info["data_intent_count"] = intent_count
    info["zero_entity_pages"] = sorted(
        n for n, t in texts.items() if not ENTITIES_IMPORT_RE.search(t))

    report = {"violations": violations, "info": info,
              "ok": not violations}
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if violations:
        print(f"contracts-lint: {len(violations)} 处硬违规：")
        for v in violations[:40]:
            print("  -", v)
        return 1
    print(f"contracts-lint: {len(pages)} 页全部通过 ✓ "
          f"(entities 引用 {ent_pages}/{len(pages)} 页, "
          f"data-intent {intent_count} 处[仅统计])")
    return 0


if __name__ == "__main__":
    sys.exit(main())
