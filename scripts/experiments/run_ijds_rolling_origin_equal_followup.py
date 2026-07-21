"""Evaluate frozen 2016/2017 CatBoost coverage at equal 39-month follow-up."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from src.ijds_audit.rolling_origin_equal_followup import run_equal_followup

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run_equal_followup(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
