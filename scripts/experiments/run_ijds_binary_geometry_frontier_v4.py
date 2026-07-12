"""Run one phase of the tagged IJDS V4 binary-geometry audit."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from src.ijds_audit.protocol import evaluate_frozen, freeze_outcome_free

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "evaluate"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    runner = freeze_outcome_free if args.phase == "freeze" else evaluate_frozen
    print(runner(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
