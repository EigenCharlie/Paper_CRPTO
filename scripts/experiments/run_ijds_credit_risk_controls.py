"""Run one phase of protocol-locked IJDS credit-risk learner controls."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from src.ijds_audit.credit_control_protocol import (
    evaluate_credit_controls,
    freeze_credit_controls,
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
    runner = freeze_credit_controls if args.phase == "freeze" else evaluate_credit_controls
    print(runner(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
