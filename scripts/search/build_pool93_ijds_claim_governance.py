"""Build a claim-governance sidecar for pool93 IJDS local refinement."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.search.run_pool93_ijds_local_refinement import (  # noqa: E402
    DEFAULT_ALPHA_GRID,
    _claim_summary,
)
from src.utils.pipeline_runtime import atomic_write_json  # noqa: E402


DEFAULT_RUN_TAG = "champion-reopen-2026-06-19__pool93__ijds-local-refine-stage1"
PAPER_FACING_KEY_RENAMES = {
    "champion_return_reference": "declared_return_floor",
    "champion_return_surplus": "return_floor_surplus",
    "n_all_alpha_passers_above_champion": "n_all_alpha_passers_above_return_floor",
    "best_gamma_cp_above_champion_claim": "best_gamma_cp_return_floor_claim",
    "best_weighted_miscoverage_above_champion_claim": "best_weighted_miscoverage_return_floor_claim",
    "min_gamma_cp_above_champion": "min_gamma_cp_above_return_floor",
    "min_v_above_champion": "min_v_above_return_floor",
}

PAPER_FACING_TEXT_RENAMES = {
    "above-champion": "above-return-floor",
    "above champion": "above return floor",
    "champion_return_surplus": "return_floor_surplus",
    "champion-level return": "declared-return-floor return",
    "positive champion_return_surplus for replacement claims": (
        "nonnegative return_floor_surplus for declared-return-floor claims"
    ),
    "preserving champion-level return": "preserving the declared return floor",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _default_paths(run_tag: str) -> dict[str, Path]:
    data_dir = ROOT / "data/processed/experiments/champion_reopen" / run_tag / "portfolio"
    model_dir = ROOT / "models/experiments/champion_reopen" / run_tag / "portfolio"
    return {
        "leaderboard": data_dir / "pool93_ijds_local_refinement_leaderboard.parquet",
        "bound_eval": data_dir / "pool93_ijds_local_refinement_bound_eval.parquet",
        "manifest": model_dir / "pool93_ijds_local_refinement_manifest.json",
        "status": model_dir / "runtime_status.json",
        "output": model_dir / "pool93_ijds_claim_governance.json",
    }


def _paper_facing_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            PAPER_FACING_KEY_RENAMES.get(str(key), str(key)): _paper_facing_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_paper_facing_value(item) for item in value]
    if isinstance(value, str):
        text = value
        for old, new in PAPER_FACING_TEXT_RENAMES.items():
            text = text.replace(old, new)
        for old, new in PAPER_FACING_KEY_RENAMES.items():
            text = text.replace(old, new)
        return text
    return value


def _claim_hierarchy(summary: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    state = str(status.get("state", "unknown"))
    pct = float(status.get("pct_complete", 0.0) or 0.0)
    complete = state == "completed" or pct >= 1.0
    return {
        "status": "final" if complete else "partial_do_not_promote_yet",
        "paper_body_candidate": "balanced_return_bound_claim",
        "appendix_frontier_candidates": [
            "max_return_claim",
            "best_gamma_cp_return_floor_claim",
            "best_weighted_miscoverage_return_floor_claim",
        ],
        "do_not_claim": [
            "universal alpha robustness beyond the finite alpha grid",
            "continuous-region robustness beyond evaluated policies",
            "nominal funded-set alpha coverage when V(alpha) exceeds alpha",
            "prospective live-selection validity from retrospective OOT selection",
        ],
        "promotion_gate": [
            "run state completed",
            "selected claim passes all alpha levels in finite_grid_policy.alpha_grid",
            "zero violation at alpha=0.01",
            "nonnegative return_floor_surplus for declared-return-floor claims",
            "manuscript labels max-return point as an economic frontier endpoint if it is used",
        ],
        "current_counts": {
            "n_policies": summary.get("n_policies"),
            "n_all_alpha_passers": summary.get("n_all_alpha_passers"),
            "n_all_alpha_passers_above_return_floor": summary.get(
                "n_all_alpha_passers_above_return_floor"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", default=DEFAULT_RUN_TAG)
    parser.add_argument("--leaderboard", default="")
    parser.add_argument("--bound-eval", default="")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    paths = _default_paths(str(args.run_tag))
    leaderboard_path = Path(args.leaderboard) if args.leaderboard else paths["leaderboard"]
    bound_eval_path = Path(args.bound_eval) if args.bound_eval else paths["bound_eval"]
    manifest_path = Path(args.manifest) if args.manifest else paths["manifest"]
    status_path = Path(args.status) if args.status else paths["status"]
    output_path = Path(args.output) if args.output else paths["output"]

    leaderboard = pd.read_parquet(leaderboard_path)
    bound_eval = pd.read_parquet(bound_eval_path)
    manifest = _load_json(manifest_path)
    status = _load_json(status_path)
    alpha_grid = [float(value) for value in manifest.get("alpha_grid", DEFAULT_ALPHA_GRID)]

    raw_summary = _claim_summary(leaderboard, bound_eval, alpha_grid=alpha_grid)
    summary = _paper_facing_value(raw_summary)
    paper_status = _paper_facing_value(status)
    payload = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_tag": str(args.run_tag),
        "source_paths": {
            "leaderboard": str(leaderboard_path),
            "bound_eval": str(bound_eval_path),
            "manifest": str(manifest_path),
            "status": str(status_path),
        },
        "runtime_status": paper_status,
        "claim_summary": summary,
        "claim_hierarchy": _claim_hierarchy(summary, paper_status),
    }
    atomic_write_json(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
