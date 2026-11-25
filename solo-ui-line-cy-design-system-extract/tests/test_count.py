"""
tests/test_count.py — 4 段 token 计数跨文件一致性单测
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEGMENT_EXPECTED = {"primitive": 19, "semantic": 19, "component": 6, "metric": 43}
TOTAL_EXPECTED = 131


def test_md_token_count():
    md = (ROOT / "out" / "system-rules.md").read_text(encoding="utf-8")
    # 找 "= 85" 或 "共 85 个"
    m = re.search(r"=\s*(\d+)\b.*?$", md, re.MULTILINE)
    assert m and int(m.group(1)) == TOTAL_EXPECTED, f"md 应含 = {TOTAL_EXPECTED}，实际 {m.group(1) if m else '无'}"


def test_html_token_count():
    html = (ROOT / "out" / "system-spec" / "design-system.html").read_text(encoding="utf-8")
    m = re.search(r"Token\s*(\d+)", html)
    assert m and int(m.group(1)) == TOTAL_EXPECTED, f"HTML 应含 Token {TOTAL_EXPECTED}，实际 {m.group(1) if m else '无'}"


def test_example_4_segments():
    import json
    data = json.loads((ROOT / "sample-input" / "middle.example.json").read_text(encoding="utf-8"))
    for seg, expected in SEGMENT_EXPECTED.items():
        actual = len(data["tokens"][seg])
        assert actual == expected, f"{seg}: 期望 {expected} 实际 {actual}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
