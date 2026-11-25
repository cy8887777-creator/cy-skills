"""
tests/test_schema.py — JSON Schema 校验单测
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sample-input" / "middle.schema.json"
EXAMPLE = ROOT / "sample-input" / "middle.example.json"


def test_schema_exists():
    assert SCHEMA.exists(), f"缺 schema 文件: {SCHEMA}"
    json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_example_validates():
    import jsonschema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)  # 不抛即通过


def test_schema_version():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("properties", {}).get("meta", {}).get("properties", {}).get("schema_version", {}).get("const") == "2.0.0"


# ---------- 紧身衣拆除验证（fixtures 真素材，不再空盒） ----------

FIXTURE = ROOT / "tests" / "fixtures" / "middle.fixture.json"
SCHEMA_PY = ROOT / "scripts" / "core" / "schema.py"


def test_fixture_validates():
    """实测小系统（2/1/1/4=8）必须合法——schema 不逼迫凑 85"""
    import jsonschema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)


def test_count_no_expect_passes():
    """count 不带期望值：任何实测计数都 exit 0"""
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", str(SCHEMA_PY), "count", str(FIXTURE)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


def test_count_wrong_expect_fails():
    """count 传 --expect-total 85 对 8-token fixture：必须 exit 1（期望值真在管事）"""
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", str(SCHEMA_PY), "count", str(FIXTURE),
                        "--expect-total", "85"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1, r.stdout + r.stderr


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
