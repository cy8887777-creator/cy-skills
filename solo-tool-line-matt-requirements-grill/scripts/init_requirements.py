#!/usr/bin/env python3
"""Initialize a durable requirements repository without overwriting existing files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


STANDALONE_FILES = {
    "00-project-overview.md": """# Project Overview

## Background

OPEN

## Goals

OPEN

## Users and Platforms

OPEN

## Scope and Phases

OPEN

## Excluded Scope

OPEN

## External Systems and Constraints

OPEN

## Source Inventory

| Source | Version/Date | Authority | Notes |
|---|---|---|---|
""",
    "01-roles-permissions.md": """# Roles and Permissions

Record actors, roles, operation permissions, data scopes, ownership, visibility, and approval authority.

| PERM ID | Status | Role | Operation | Data Scope | Restrictions | Source |
|---|---|---|---|---|---|---|
""",
    "02-functional-requirements.md": """# Functional Requirements

Organize by client/platform -> primary module -> secondary module -> function.

| FR ID | Status | Phase | Client | Module | Function | Actor | Description | Acceptance | Source |
|---|---|---|---|---|---|---|---|---|---|
""",
    "03-business-rules.md": """# Business Rules

| BR ID | Status | Module | Trigger | Rule | Result | Related IDs | Source |
|---|---|---|---|---|---|---|---|
""",
    "04-workflows.md": """# Workflows

Record main, exceptional, reverse, and invalid transitions.

| WF ID | Status | Workflow | Actor | Preconditions | Flow/Transitions | Exceptions | Related IDs | Source |
|---|---|---|---|---|---|---|---|---|
""",
    "05-edge-cases.md": """# Edge Cases

| EDGE ID | Status | Module | Scenario | Expected Behavior | Related IDs | Source |
|---|---|---|---|---|---|---|
""",
    "06-decisions-rejected.md": """# Decisions and Rejected Options

Preserve accepted major decisions, alternatives, rejected options, reasons, and impact.

| Decision ID/Date | Status | Decision | Rejected Alternative | Reason | Impact | Source |
|---|---|---|---|---|---|---|
""",
    "07-open-questions.md": """# Open Questions

| Question ID | Priority | Blocking | Module | Question | Related IDs | Recommendation | Assumption | Status |
|---|---|---|---|---|---|---|---|---|
""",
    "08-change-log.md": """# Requirements Change Log

Record meaningful requirement changes, not trivial wording edits.

| Date | Requirement IDs | Old | New | Reason | Source |
|---|---|---|---|---|---|
""",
    "MASTER_REQUIREMENTS.md": """# MASTER REQUIREMENTS

Status: DRAFT

This normalized document is the single source of truth for final Excel and PRD deliverables. Build it from the canonical detail files; preserve OPEN, REJECTED, DEFERRED, and OUT_OF_SCOPE items.

## Project Overview

OPEN

## Scope and Phases

OPEN

## Actors, Roles, and Permissions

OPEN

## Module Tree and Functional Requirements

OPEN

## Business Rules and Workflows

OPEN

## Exceptions, Integrations, and Non-Functional Requirements

OPEN

## Acceptance Criteria

OPEN

## Rejected, Deferred, Out-of-Scope, and Open Items

OPEN
""",
}

GOVERNED_FILES = {
    "docs/requirements/product.md": """# 产品需求

状态：未确认。

## 项目概览与范围

OPEN

## 用户、角色与权限

OPEN

## 功能需求

OPEN

## 业务规则与流程

OPEN

## 异常、集成与非功能要求

OPEN

## 验收口径

OPEN
""",
    "docs/requirements/confirmed-decisions.md": """# 已确认决策与待决事项

## 已确认

OPEN

## 已拒绝、延期与范围外

OPEN

## 待确认

OPEN

## 外部依赖

OPEN
""",
    "docs/requirements/change-log.md": """# 需求变更记录

只记录范围、流程、权限、规则、阶段、重要字段或验收口径的实质变化。

| 日期 | 需求编号 | 原口径 | 新口径 | 原因 | 来源 |
|---|---|---|---|---|---|
""",
}

GOVERNED_MARKERS = (
    Path("project.config.json"),
    Path("docs/governance/source-of-truth.md"),
)
GOVERNED_ACCEPTANCE = Path("docs/acceptance/acceptance-baseline.json")
GOVERNED_REQUIRED_PATHS = (
    "docs/requirements/product.md",
    "docs/requirements/confirmed-decisions.md",
    "docs/acceptance/acceptance-baseline.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create missing requirements repository files without overwriting existing work."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    return parser.parse_args()


def resolve_mode(project_root: Path) -> str:
    marker_state = [((project_root / marker).is_file()) for marker in GOVERNED_MARKERS]
    if all(marker_state):
        return "governed"
    if any(marker_state):
        missing = [
            str(marker)
            for marker, exists in zip(GOVERNED_MARKERS, marker_state, strict=True)
            if not exists
        ]
        raise SystemExit(
            "Incomplete governed-project markers; refusing to create a parallel "
            "requirements repository. Missing: " + ", ".join(missing)
        )
    return "standalone"


def create_missing_files(project_root: Path, files: dict[str, str]) -> tuple[list[str], list[str]]:
    created: list[str] = []
    preserved: list[str] = []
    for relative_name, content in files.items():
        path = project_root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        except FileExistsError:
            preserved.append(relative_name)
        else:
            created.append(relative_name)
    return created, preserved


def verify_files(project_root: Path, files: dict[str, str]) -> None:
    for relative_name in files:
        path = project_root / relative_name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise SystemExit(f"Initialization verification failed: {path}")


def verify_acceptance_baseline(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Governed acceptance baseline is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Governed acceptance baseline is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("business_features"), list):
        raise SystemExit(
            "Governed acceptance baseline must be an object with a business_features array: "
            f"{path}"
        )


def verify_governance_contract(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    missing = [declared_path for declared_path in GOVERNED_REQUIRED_PATHS if declared_path not in content]
    if missing:
        raise SystemExit(
            "Host governance uses an unsupported or incomplete requirements mapping. "
            "Resolve its authoritative paths before initialization. Missing declarations: "
            + ", ".join(missing)
        )


def main() -> int:
    args = parse_args()
    project_root = args.project_root.expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"Project root does not exist or is not a directory: {project_root}")

    mode = resolve_mode(project_root)
    if mode == "governed":
        parallel_root = project_root / "requirements"
        if parallel_root.exists():
            raise SystemExit(
                "Governed project already contains top-level requirements/. "
                "Resolve or migrate that conflicting repository explicitly before discovery."
            )
        verify_governance_contract(project_root / GOVERNED_MARKERS[1])
        acceptance_baseline = project_root / GOVERNED_ACCEPTANCE
        verify_acceptance_baseline(acceptance_baseline)
        created, preserved = create_missing_files(project_root, GOVERNED_FILES)
        verify_files(project_root, GOVERNED_FILES)
        requirements_dir = project_root / "docs/requirements"
        canonical_requirements = requirements_dir / "product.md"
        decision_register = requirements_dir / "confirmed-decisions.md"
        open_question_register = decision_register
        change_log = requirements_dir / "change-log.md"
        source_analysis_root = requirements_dir / "source-analysis"
        source_analysis_root.mkdir(parents=True, exist_ok=True)
        change_log_key = "docs/requirements/change-log.md"
        initialization_row = "需求仓库 | - | 已初始化 | 需求调研启动 | SYSTEM"
    else:
        standalone_files = {
            f"requirements/{filename}": content
            for filename, content in STANDALONE_FILES.items()
        }
        created, preserved = create_missing_files(project_root, standalone_files)
        verify_files(project_root, standalone_files)
        requirements_dir = project_root / "requirements"
        canonical_requirements = requirements_dir / "MASTER_REQUIREMENTS.md"
        decision_register = requirements_dir / "06-decisions-rejected.md"
        open_question_register = requirements_dir / "07-open-questions.md"
        change_log = requirements_dir / "08-change-log.md"
        source_analysis_root = requirements_dir / "source-analysis"
        source_analysis_root.mkdir(parents=True, exist_ok=True)
        acceptance_baseline = None
        change_log_key = "requirements/08-change-log.md"
        initialization_row = "Repository | - | Initialized | Discovery startup | SYSTEM"

    if change_log_key in created:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with change_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"\n| {stamp} | {initialization_row} |\n")

    print(f"repository_mode={mode}")
    print(f"project_config={project_root / 'project.config.json' if mode == 'governed' else 'none'}")
    print(
        "governance_file="
        + str(project_root / GOVERNED_MARKERS[1] if mode == "governed" else "none")
    )
    print(f"requirements_dir={requirements_dir}")
    print(f"canonical_requirements={canonical_requirements}")
    print(f"decision_register={decision_register}")
    print(f"open_question_register={open_question_register}")
    print(f"change_log={change_log}")
    print(f"source_analysis_root={source_analysis_root}")
    print(f"acceptance_baseline={acceptance_baseline or 'none'}")
    print("created=" + (",".join(created) if created else "none"))
    print("preserved=" + (",".join(preserved) if preserved else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
