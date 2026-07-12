from __future__ import annotations

from scripts.run_ty_advisory import (
    TY_REQUIREMENT,
    _diagnostic_lines,
    build_ty_command,
    iter_python_files,
)


def test_active_ty_scope_excludes_archived_optional_and_protected_paths() -> None:
    files = set(iter_python_files(scope="active"))

    assert "scripts/generate_conformal_intervals.py" not in files
    assert "scripts/train_pd_model.py" not in files
    assert "scripts/run_spo_real.py" not in files
    assert "src/optimization/cuopt_adapter.py" not in files
    assert all(not path.startswith("scripts/archive/") for path in files)
    assert "scripts/experiments/ijds_policy_support.py" in files
    assert "scripts/experiments/run_ijds_calibration_selected_policy_challenger.py" in files
    assert "scripts/experiments/run_ijds_exact_alpha_grid_challenger.py" in files
    assert all(
        not (path.startswith("scripts/search/run_") and path.endswith(".py")) for path in files
    )


def test_active_ty_scope_keeps_live_ijds_helpers() -> None:
    files = set(iter_python_files(scope="active"))

    assert "scripts/compile_ijds_submission.py" in files
    assert "scripts/build_ijds_calibration_selected_evidence.py" in files
    assert "scripts/search/build_pool93_body_allocation_audit.py" in files
    assert "src/models/conformal_alpha_grid.py" in files
    assert "src/optimization/policy_selection.py" in files
    assert "src/optimization/portfolio_model.py" in files


def test_full_ty_scope_keeps_every_python_file_under_src_and_scripts() -> None:
    files = set(iter_python_files(scope="full"))

    assert "scripts/generate_conformal_intervals.py" in files
    assert "scripts/train_pd_model.py" in files
    assert "src/optimization/cuopt_adapter.py" in files


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
