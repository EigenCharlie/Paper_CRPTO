"""Run the automatically discovered IJDS test surface by materialization tier."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DVC_MARKER = "requires_dvc_materialized"
TEST_PATTERNS = (
    (Path("tests"), "test_ijds_*.py"),
    (Path("tests/test_ijds_audit"), "test_*.py"),
)


def discover_ijds_test_files(*, repo_root: Path = ROOT) -> list[str]:
    """Return the complete convention-based IJDS test surface."""
    resolved_root = repo_root.resolve()
    discovered = {
        path.relative_to(resolved_root).as_posix()
        for relative_root, pattern in TEST_PATTERNS
        for path in (resolved_root / relative_root).glob(pattern)
        if path.is_file()
    }
    if not discovered:
        raise RuntimeError("No IJDS tests matched the declared discovery patterns")
    return sorted(discovered)


def build_pytest_command(*, tier: str, files: Sequence[str]) -> list[str]:
    """Build the pytest command for the local or DVC-materialized tier."""
    if tier == "local":
        marker_expression = f"not {DVC_MARKER}"
    elif tier == "dvc":
        marker_expression = DVC_MARKER
    else:
        raise ValueError(f"Unsupported IJDS test tier: {tier}")
    return [sys.executable, "-m", "pytest", *files, "-m", marker_expression]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("local", "dvc"),
        required=True,
        help="local excludes DVC-dependent tests; dvc runs only those tests",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    files = discover_ijds_test_files()
    command = build_pytest_command(tier=args.tier, files=files)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
