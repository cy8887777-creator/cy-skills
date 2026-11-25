"""
tests/test_converters.py — v4 派生转换器单测（html_to_json / html_to_md）

对象 = 技能 out/ 真实案例（站④产物）；缺失时显式 skip。
断言：json 134 四段拆分 / md 计数声明行 / 三构造计数对齐。
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
JSON_F = OUT / "system-rules.json"
MD_F = OUT / "system-rules.md"
HTML_F = OUT / "system-spec" / "design-system.html"


def _skip_if_missing():
    for f in (JSON_F, MD_F, HTML_F):
        if not f.exists():
            pytest.skip(f"out/ 三构造不全（先跑站④派生链）: {f.name}")


def test_json_count_and_segments():
    _skip_if_missing()
    d = json.loads(JSON_F.read_text(encoding="utf-8"))
    toks = d["tokens"]
    total = len(toks["primitive"]) + len(toks["semantic"]) + len(toks["component"]) + len(toks["metric"])
    assert toks.get("count") == total, f"json tokens.count {toks.get('count')} ≠ 实算 {total}"
    assert total >= 100, f"token 总量异常: {total}"


def test_md_count_declaration():
    _skip_if_missing()
    t = MD_F.read_text(encoding="utf-8")
    m = re.search(r"共\s*(\d+)\s*个\s*·?\s*四段口径", t)
    assert m, "md 缺「共 N 个 · 四段口径」计数声明（html_to_md 必须生成）"
    d = json.loads(JSON_F.read_text(encoding="utf-8"))
    assert int(m.group(1)) == d["tokens"]["count"], "md 声明 ≠ json tokens.count（派生不同步）"


def test_three_way_count_alignment():
    _skip_if_missing()
    d = json.loads(JSON_F.read_text(encoding="utf-8"))
    md = MD_F.read_text(encoding="utf-8")
    html = HTML_F.read_text(encoding="utf-8")
    j = d["tokens"]["count"]
    hm = re.search(r"Token\s*(\d+)", html)
    assert hm, "HTML 无 Token 计数声明"
    assert int(hm.group(1)) == j == int(re.search(r"共\s*(\d+)\s*个", md).group(1)), \
        f"三构造计数不齐: html={hm.group(1)} json={j} md"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
