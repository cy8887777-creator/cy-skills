from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/init_requirements.py"


class InitRequirementsTest(unittest.TestCase):
    def run_initializer(self, project_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(project_root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def create_governed_project(self, project_root: Path) -> tuple[Path, Path, Path]:
        (project_root / "project.config.json").write_text("{}\n", encoding="utf-8")
        governance = project_root / "docs/governance/source-of-truth.md"
        governance.parent.mkdir(parents=True)
        governance.write_text(
            "\n".join(
                [
                    "# Source of Truth",
                    "docs/requirements/product.md",
                    "docs/requirements/confirmed-decisions.md",
                    "docs/acceptance/acceptance-baseline.json",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        requirements_dir = project_root / "docs/requirements"
        requirements_dir.mkdir(parents=True)
        product = requirements_dir / "product.md"
        decisions = requirements_dir / "confirmed-decisions.md"
        product.write_text("# Existing Product\n\nKEEP_PRODUCT\n", encoding="utf-8")
        decisions.write_text("# Existing Decisions\n\nKEEP_DECISIONS\n", encoding="utf-8")
        acceptance = project_root / "docs/acceptance/acceptance-baseline.json"
        acceptance.parent.mkdir(parents=True)
        acceptance.write_text(
            json.dumps({"schema_version": 1, "business_features": []}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        return product, decisions, acceptance

    def test_standalone_mode_creates_original_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            result = self.run_initializer(project_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("repository_mode=standalone", result.stdout)
            requirements_dir = project_root / "requirements"
            self.assertTrue((requirements_dir / "MASTER_REQUIREMENTS.md").is_file())
            open_questions = requirements_dir / "07-open-questions.md"
            self.assertTrue(open_questions.is_file())
            self.assertFalse((project_root / "docs/requirements").exists())

            open_questions.write_text("# Existing Questions\n\nKEEP_STANDALONE\n", encoding="utf-8")
            second = self.run_initializer(project_root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("created=none", second.stdout)
            self.assertEqual(
                open_questions.read_text(encoding="utf-8"),
                "# Existing Questions\n\nKEEP_STANDALONE\n",
            )

    def test_governed_mode_uses_host_sources_without_parallel_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            product, decisions, acceptance = self.create_governed_project(project_root)
            original = {
                product: product.read_bytes(),
                decisions: decisions.read_bytes(),
                acceptance: acceptance.read_bytes(),
            }

            first = self.run_initializer(project_root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("repository_mode=governed", first.stdout)
            self.assertIn(f"canonical_requirements={product.resolve()}", first.stdout)
            self.assertFalse((project_root / "requirements").exists())
            self.assertTrue((project_root / "docs/requirements/change-log.md").is_file())
            self.assertTrue((project_root / "docs/requirements/source-analysis").is_dir())
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

            change_log = project_root / "docs/requirements/change-log.md"
            first_change_log = change_log.read_bytes()
            second = self.run_initializer(project_root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("created=none", second.stdout)
            self.assertEqual(change_log.read_bytes(), first_change_log)
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

    def test_incomplete_governed_markers_fail_without_creating_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "project.config.json").write_text("{}\n", encoding="utf-8")

            result = self.run_initializer(project_root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Incomplete governed-project markers", result.stderr)
            self.assertFalse((project_root / "requirements").exists())

    def test_governed_mode_rejects_parallel_requirements_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self.create_governed_project(project_root)
            (project_root / "requirements").mkdir()

            result = self.run_initializer(project_root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Resolve or migrate that conflicting repository", result.stderr)

    def test_unknown_governance_mapping_fails_without_writing_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "project.config.json").write_text("{}\n", encoding="utf-8")
            governance = project_root / "docs/governance/source-of-truth.md"
            governance.parent.mkdir(parents=True)
            governance.write_text(
                "# Source of Truth\ncustom/product.md\ncustom/decisions.md\n",
                encoding="utf-8",
            )

            result = self.run_initializer(project_root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported or incomplete requirements mapping", result.stderr)
            self.assertFalse((project_root / "requirements").exists())
            self.assertFalse((project_root / "docs/requirements").exists())


if __name__ == "__main__":
    unittest.main()
