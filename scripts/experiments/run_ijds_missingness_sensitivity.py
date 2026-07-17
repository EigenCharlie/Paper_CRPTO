"""Run one phase of the protocol-locked IJDS missingness sensitivity."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from src.ijds_audit.missingness_sensitivity import (
    evaluate_missingness_sensitivity,
    freeze_missingness_sensitivity,
)

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "evaluate"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    runner = (
        freeze_missingness_sensitivity
        if args.phase == "freeze"
        else evaluate_missingness_sensitivity
    )
    print(runner(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
