from __future__ import annotations

from scripts.run_complexity_report import (
    RADON_REQUIREMENT,
    build_radon_command,
    isolated_uvx_environment,
)
from scripts.run_ty_advisory import iter_python_files


def test_complexity_report_uses_only_declared_active_files() -> None:
    files = iter_python_files(scope="active")
    command = build_radon_command(uvx="uvx", files=files)

    assert command[:4] == ["uvx", "--from", RADON_REQUIREMENT, "radon"]
    assert "scripts/build_ijds_binary_geometry_frontier_v4_evidence.py" in command
    assert "scripts/generate_conformal_intervals.py" not in command
    assert "src/data/make_dataset.py" not in command
    assert command[-3:] == ["--show-complexity", "--min", "C"]


def test_complexity_report_isolates_uvx_interpreter_environment() -> None:
    cleaned = isolated_uvx_environment(
        {"PATH": "bin", "PYTHONHOME": "managed-python", "VIRTUAL_ENV": ".venv"}
    )

    assert cleaned == {"PATH": "bin"}
