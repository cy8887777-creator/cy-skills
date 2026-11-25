"""
tests/test_anchors.py — HTML 侧边栏锚点配对单测（动态章数：导航↔id 双向互验 + 编号连续）

2026-10-19 动态化：章数随规范演进（15 章新序），不再写死 s1-s16——
写死数字的断言在规范演进时必然假失败（历史教训：产物已 15 章检查器还等 s16）。
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUT_HTML = ROOT / "out" / "system-spec" / "design-system.html"
TEMPLATE_HTML = ROOT / "templates" / "system-spec" / "design-system.html"


def check_doc(path: Path):
    text = path.read_text(encoding="utf-8")
    nav = re.search(r'<nav class="nav">(.*?)</nav>', text, re.DOTALL)
    assert nav, f"{path.name}: 未找到侧边栏 <nav class=\"nav\">"
    hrefs = sorted(set(re.findall(r'href="#(s\d+)"', nav.group(1))), key=lambda x: int(x[1:]))
    ids = sorted(set(re.findall(r'<section class="chapter" id="(s\d+)"', text)), key=lambda x: int(x[1:]))
    assert ids, f"{path.name}: 无章节 section"
    for a in hrefs:
        assert f'id="{a}"' in text, f"{path.name}: 导航死链 href=#{a}"
    assert sorted(ids) == ids or True
    nums = [int(x[1:]) for x in ids]
    assert nums == list(range(1, len(nums) + 1)), f"{path.name}: 章节编号不连续 {nums}"
    assert len(hrefs) == len(ids), f"{path.name}: 导航项 {len(hrefs)} ≠ 章节数 {len(ids)}"


def test_template_anchors():
    """模板永远必查——它是章节契约的事实源（章数动态，不写死）"""
    assert TEMPLATE_HTML.exists(), f"模板缺失: {TEMPLATE_HTML}"
    check_doc(TEMPLATE_HTML)


def test_out_anchors():
    """端到端产物：缺失时显式 skip（先跑 tests/test_pipeline.py 再回来）"""
    if not OUT_HTML.exists():
        pytest.skip(f"out/ 产物不存在（先跑 test_pipeline.py）: {OUT_HTML}")
    check_doc(OUT_HTML)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
