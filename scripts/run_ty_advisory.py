"""Run pinned ty as an advisory or blocking checker for CRPTO."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "ci" / "ty-advisory.txt"
TY_REQUIREMENT = "ty==0.0.61"

SOURCE_ROOTS = ("src", "scripts")
COMPATIBILITY_SOURCE_FILES = {
    "src/data/make_dataset.py",
    "src/data/prepare_dataset.py",
    "src/optimization/tail_satisficing_objective.py",
}
SUMMARY_RE = re.compile(r"^Found \d+ diagnostics", flags=re.MULTILINE)


def _relative_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def iter_python_files(*, scope: str) -> list[str]:
    """Return the Python files ty should check for a given advisory scope."""
    if scope not in {"active", "full"}:
        raise ValueError(f"Unsupported ty scope: {scope}")
    full = [
        _relative_posix(path)
        for root_name in SOURCE_ROOTS
        for path in sorted((ROOT / root_name).rglob("*.py"))
    ]
    if scope == "full":
        return full

    publication = yaml.safe_load(
        (ROOT / "configs/crpto_publication_targets.yaml").read_text(encoding="utf-8")
    )
    surface = publication["active_scientific_contract"]["active_code_surface"]
    active_scripts = {
        *surface["paper_pipeline"],
        *surface["protocol_entrypoints"],
        *surface["support_tools"],
        "scripts/__init__.py",
        "scripts/experiments/__init__.py",
    }
    return [
        path
        for path in full
        if (path.startswith("src/") and path not in COMPATIBILITY_SOURCE_FILES)
        or path in active_scripts
    ]


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


def run_ty(
    scope: str,
    output: Path | None,
    *,
    fail_on_diagnostics: bool = False,
) -> int:
    """Run pinned ty, optionally persist its report, and enforce diagnostics."""
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
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    elif raw_output.strip():
        print(raw_output.rstrip())
    summary = SUMMARY_RE.search(report)
    if diagnostics:
        print(f"Found {len(diagnostics)} diagnostics")
    elif summary:
        print(summary.group(0))
    elif effective_return_code == 0:
        print("ty advisory clean")
    else:
        print(f"ty failed with return code {effective_return_code}")
    if output is not None:
        try:
            display_path = output.relative_to(ROOT)
        except ValueError:
            display_path = output
        print(f"Full report: {display_path}")
    return effective_return_code if fail_on_diagnostics else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=["active", "full"], default="active")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write a report file; emit diagnostics to the terminal only.",
    )
    parser.add_argument(
        "--fail-on-diagnostics",
        action="store_true",
        help="Return ty's nonzero status when diagnostics are present.",
    )
    args = parser.parse_args()
    output = None
    if not args.no_report:
        output = args.output if args.output.is_absolute() else ROOT / args.output
    return run_ty(
        scope=args.scope,
        output=output,
        fail_on_diagnostics=args.fail_on_diagnostics,
    )


if __name__ == "__main__":
    raise SystemExit(main())
