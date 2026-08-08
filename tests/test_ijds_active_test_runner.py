from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from src.ijds_audit.active_test_runner import (
    DVC_MARKER,
    build_pytest_command,
    discover_ijds_test_files,
)


def test_discovery_is_sorted_complete_and_convention_based() -> None:
    discovered = discover_ijds_test_files(repo_root=Path.cwd())
    expected = sorted(
        {
            *(path.as_posix() for path in Path("tests").glob("test_ijds_*.py")),
            *(path.as_posix() for path in Path("tests/test_ijds_audit").glob("test_*.py")),
        }
    )

    assert discovered == expected
    assert "tests/test_ijds_calibrator_sensitivity_evidence.py" in discovered
    assert "tests/test_ijds_active_test_runner.py" in discovered


def test_every_dvc_marked_test_file_is_inside_the_discovered_surface() -> None:
    discovered = set(discover_ijds_test_files(repo_root=Path.cwd()))
    marked_files = {
        path.as_posix()
        for path in Path("tests").rglob("test_*.py")
        if DVC_MARKER in path.read_text(encoding="utf-8")
    }

    assert marked_files
    assert marked_files <= discovered


@pytest.mark.parametrize(
    ("tier", "marker_expression"),
    [("local", f"not {DVC_MARKER}"), ("dvc", DVC_MARKER)],
)
def test_tier_routes_the_same_surface_by_marker(tier: str, marker_expression: str) -> None:
    files = ["tests/test_ijds_active_claim_sync.py", "tests/test_ijds_audit/test_claim_ledger.py"]

    command = build_pytest_command(tier=tier, files=files)

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert command[3:-2] == files
    assert command[-2:] == ["-m", marker_expression]


def test_unknown_tier_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported IJDS test tier"):
        build_pytest_command(tier="unknown", files=[])


def test_just_routes_dvc_tests_only_after_pull_at_freeze_and_closeout() -> None:
    justfile = Path("justfile").read_text(encoding="utf-8")
    local_marker = '-m "not requires_dvc_materialized"'
    active = re.search(r"(?m)^ijds-active-check: (.+)$", justfile)
    ordinary = re.search(r"(?m)^submission-check: (.+)$", justfile)
    freeze = re.search(r"(?m)^submission-freeze-check: (.+)$", justfile)
    closeout = re.search(r"(?m)^submission-closeout: (.+)$", justfile)

    assert active and ordinary and freeze and closeout
    assert "ijds-active-science-tests" in active.group(1)
    assert "ijds-active-dvc-tests" not in active.group(1)
    assert "ijds-active-dvc-tests" not in ordinary.group(1)
    assert re.search(rf"(?m)^test:\s*\n\s+.*{re.escape(local_marker)}", justfile)
    assert re.search(rf"(?m)^coverage:\s*\n\s+.*{re.escape(local_marker)}", justfile)
    for final_recipe in (freeze.group(1), closeout.group(1)):
        dependencies = final_recipe.split()
        assert dependencies.index("ijds-pull") < dependencies.index("ijds-active-dvc-tests")
