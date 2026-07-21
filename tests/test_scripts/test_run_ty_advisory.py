from __future__ import annotations

from scripts.run_ty_advisory import (
    TY_REQUIREMENT,
    _diagnostic_lines,
    build_ty_command,
    iter_python_files,
)


def test_active_ty_scope_is_the_complete_current_code_surface() -> None:
    files = set(iter_python_files(scope="active"))

    assert "scripts/compile_ijds_submission.py" in files
    assert "scripts/build_ijds_binary_geometry_frontier_v4_evidence.py" in files
    assert "scripts/experiments/run_ijds_binary_geometry_frontier_v4.py" in files
    assert "src/models/binary_conformal_guardrail.py" in files
    assert "src/optimization/policy_selection.py" in files
    assert "src/optimization/portfolio_model.py" in files
    assert all("/archive/" not in path and "/search/" not in path for path in files)


def test_full_ty_scope_adds_only_sealed_compatibility_sources() -> None:
    active = set(iter_python_files(scope="active"))
    full = set(iter_python_files(scope="full"))

    assert active < full
    assert "src/data/make_dataset.py" in full - active
    assert "scripts/train_pd_model.py" in full - active


def test_ty_command_pins_version_and_keeps_daily_scope_advisory() -> None:
    command = build_ty_command(
        uvx="uvx",
        files=["src/example.py"],
        fail_on_diagnostics=False,
    )

    assert command[:4] == ["uvx", "--from", TY_REQUIREMENT, "ty"]
    assert "--exit-zero" in command
    assert command[-1] == "src/example.py"


def test_ty_command_can_block_the_submission_gate() -> None:
    command = build_ty_command(
        uvx="uvx",
        files=["src/example.py"],
        fail_on_diagnostics=True,
    )

    assert "--exit-zero" not in command


def test_ty_diagnostic_parser_keeps_every_error() -> None:
    first = r"src\first.py:4:2: error[invalid-return-type] first failure"
    second = r"src\second.py:10:2: error[invalid-argument-type] second failure"

    assert _diagnostic_lines(f"{first}\ninformation\n{second}\n") == [first, second]
