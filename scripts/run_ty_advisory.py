"""Run pinned ty as an advisory or blocking checker for CRPTO."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "ci" / "ty-advisory.txt"
TY_REQUIREMENT = "ty==0.0.59"

SOURCE_ROOTS = ("src", "scripts")
ACTIVE_EXCLUDED_FILES = {
    "scripts/build_ijds_calibration_selected_evidence.py",
    "scripts/build_ijds_comparator_stringency_evidence.py",
    "scripts/build_ijds_fixed_taxonomy_c2_evidence.py",
    "scripts/build_ijds_maturity_safe_evidence.py",
    "scripts/generate_conformal_intervals.py",
    "scripts/run_cqr_comparison.py",
    "scripts/run_crpto_vs_spo_stability.py",
    "scripts/run_spo_comparison.py",
    "scripts/run_spo_real.py",
    "scripts/train_pd_model.py",
    "scripts/search/build_pool93_body_allocation_audit.py",
    "src/optimization/cuopt_adapter.py",
}
ACTIVE_EXPERIMENT_FILES = {
    "scripts/experiments/ijds_policy_support.py",
    "scripts/experiments/run_ijds_binary_geometry_frontier_v4.py",
    "scripts/experiments/run_ijds_decision_active_simulation.py",
    "scripts/experiments/run_ijds_normalized_objective_frontier.py",
    "scripts/experiments/run_ijds_normalized_objective_frontier_v2.py",
    "scripts/experiments/run_ijds_policy_support_tie_audit.py",
}
SUMMARY_RE = re.compile(r"^Found \d+ diagnostics", flags=re.MULTILINE)


def _relative_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def iter_python_files(*, scope: str) -> list[str]:
    """Return the Python files ty should check for a given advisory scope."""
    files: list[str] = []
    for root_name in SOURCE_ROOTS:
        for path in sorted((ROOT / root_name).rglob("*.py")):
            rel = _relative_posix(path)
            parts = rel.split("/")
            if scope == "active":
                if parts[:2] == ["scripts", "archive"]:
                    continue
                if parts[:2] == ["scripts", "experiments"] and rel not in (ACTIVE_EXPERIMENT_FILES):
                    continue
                if parts[:2] == ["scripts", "search"] and path.name.startswith("run_"):
                    continue
                if rel in ACTIVE_EXCLUDED_FILES:
                    continue
            files.append(rel)
    return files


def build_ty_command(*, uvx: str, files: Sequence[str], fail_on_diagnostics: bool) -> list[str]:
    """Build the pinned ty command for advisory or blocking use."""
    command = [
        uvx,
        "--from",
        TY_REQUIREMENT,
        "ty",
        "check",
        "--python",
        ".venv",
        "--output-format",
        "concise",
        "--no-progress",
    ]
    if not fail_on_diagnostics:
        command.append("--exit-zero")
    return [*command, *files]


def _diagnostic_lines(output: str) -> list[str]:
    """Return every concise ty error line."""
    return [line for line in output.splitlines() if ": error[" in line]


def run_ty(scope: str, output: Path, *, fail_on_diagnostics: bool = False) -> int:
    """Run pinned ty, persist its report, and optionally enforce diagnostics."""
    uvx = shutil.which("uvx")
    if uvx is None:
        raise RuntimeError("uvx is required to run the ty advisory check.")

    files = iter_python_files(scope=scope)
    command = build_ty_command(
        uvx=uvx,
        files=files,
        fail_on_diagnostics=fail_on_diagnostics,
    )
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    raw_output = f"{result.stdout}{result.stderr}"
    diagnostics = _diagnostic_lines(raw_output)
    effective_return_code = result.returncode
    output.parent.mkdir(parents=True, exist_ok=True)
    report = (
        f"# ty advisory report\n"
        f"requirement: {TY_REQUIREMENT}\n"
        f"scope: {scope}\n"
        f"blocking: {str(fail_on_diagnostics).lower()}\n"
        f"files_checked: {len(files)}\n"
        f"raw_return_code: {result.returncode}\n"
        f"effective_return_code: {effective_return_code}\n"
        f"diagnostics: {len(diagnostics)}\n"
        f"\n"
        f"{raw_output}"
    )
    output.write_text(report, encoding="utf-8")
    summary = SUMMARY_RE.search(report)
    if diagnostics:
        print(f"Found {len(diagnostics)} diagnostics")
    elif summary:
        print(summary.group(0))
    elif effective_return_code == 0:
        print("ty advisory clean")
    else:
        print(f"ty failed with return code {effective_return_code}")
    print(f"Full report: {output.relative_to(ROOT)}")
    return effective_return_code if fail_on_diagnostics else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=["active", "full"], default="active")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--fail-on-diagnostics",
        action="store_true",
        help="Return ty's nonzero status when diagnostics are present.",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    return run_ty(
        scope=args.scope,
        output=output,
        fail_on_diagnostics=args.fail_on_diagnostics,
    )


if __name__ == "__main__":
    raise SystemExit(main())
