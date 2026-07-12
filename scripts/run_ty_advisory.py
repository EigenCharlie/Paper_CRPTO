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
TY_REQUIREMENT = "ty==0.0.57"

SOURCE_ROOTS = ("src", "scripts")
ACTIVE_EXCLUDED_FILES = {
    "scripts/generate_conformal_intervals.py",
    "scripts/run_cqr_comparison.py",
    "scripts/run_crpto_vs_spo_stability.py",
    "scripts/run_spo_comparison.py",
    "scripts/run_spo_real.py",
    "scripts/train_pd_model.py",
    "src/optimization/cuopt_adapter.py",
}
ACTIVE_EXPERIMENT_FILES = {
    "scripts/experiments/ijds_policy_support.py",
    "scripts/experiments/run_ijds_calibration_selected_policy_challenger.py",
    "scripts/experiments/run_ijds_exact_alpha_grid_challenger.py",
}
SUMMARY_RE = re.compile(r"^Found \d+ diagnostics", flags=re.MULTILINE)
FROZEN_DIAGNOSTIC_PREFIXES = (
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:526:9: error[invalid-argument-type]",
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:590:17: error[invalid-argument-type]",
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:1167:28: error[no-matching-overload]",
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:1167:50: error[invalid-argument-type]",
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:1216:20: error[no-matching-overload]",
    r"scripts\experiments\run_ijds_fixed_taxonomy_c2.py:1216:35: error[invalid-argument-type]",
    r"src\evaluation\comparator_transport_simulation.py:362:45: error[invalid-argument-type]",
)


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


def _partition_diagnostics(output: str) -> tuple[list[str], list[str]]:
    """Separate exact frozen-source diagnostics from actionable diagnostics."""
    diagnostics = [line for line in output.splitlines() if ": error[" in line]
    frozen = [
        line
        for line in diagnostics
        if any(line.startswith(prefix) for prefix in FROZEN_DIAGNOSTIC_PREFIXES)
    ]
    actionable = [line for line in diagnostics if line not in frozen]
    return frozen, actionable


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
    frozen, actionable = _partition_diagnostics(raw_output)
    if fail_on_diagnostics and result.returncode != 0 and frozen and not actionable:
        effective_return_code = 0
    else:
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
        f"frozen_diagnostics: {len(frozen)}\n"
        f"actionable_diagnostics: {len(actionable)}\n"
        f"\n"
        f"{raw_output}"
    )
    output.write_text(report, encoding="utf-8")
    summary = SUMMARY_RE.search(report)
    if actionable:
        print(f"Found {len(actionable)} actionable diagnostics")
    elif frozen:
        print(f"ty clean apart from {len(frozen)} protocol-frozen diagnostics")
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
