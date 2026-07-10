"""Build a compact IJDS-facing frontier table from a pool93 refinement run."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def _default_paths(run_tag: str) -> tuple[Path, Path, Path]:
    data_dir = ROOT / "data/processed/experiments/champion_reopen" / run_tag / "portfolio"
    model_dir = ROOT / "models/experiments/champion_reopen" / run_tag / "portfolio"
    return (
        data_dir / "pool93_ijds_local_refinement_leaderboard.parquet",
        model_dir / "pool93_ijds_local_refinement_claim_summary.json",
        model_dir / "pool93_ijds_frontier_claim_table.json",
    )


def _row_payload(row: pd.Series, role: str) -> dict[str, object]:
    return {
        "role": role,
        "local_candidate_id": int(row["local_candidate_id"]),
        "family": str(row["local_family"]),
        "tau": float(row["risk_tolerance"]),
        "policy": str(row["policy_mode"]),
        "gamma": float(row["gamma"]),
        "uncertainty_aversion": float(row["uncertainty_aversion"]),
        "return": round(float(row["alpha01_realized_total_return"]), 6),
        "Gamma_CP": round(float(row["alpha01_gamma_cp"]), 6),
        "V": round(float(row["alpha01_weighted_miscoverage_V"]), 6),
        "endpoint_budget_upper": round(float(row["alpha01_endpoint_budget_upper"]), 9),
        "Markov_cap": round(float(row["alpha01_markov_loss_cap"]), 9),
        "alpha_pass": f"{int(row['alpha_exact_pass_count'])}/{int(row['alpha_exact_check_count'])}",
        "n_funded_mean": float(row["n_funded_mean"]),
    }


def _first_or_none(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    return df.iloc[0]


def _append_unique(rows: list[dict[str, object]], row: pd.Series | None, role: str) -> None:
    if row is None:
        return
    payload = _row_payload(row, role)
    key = (payload["local_candidate_id"], payload["role"])
    if key in {(item["local_candidate_id"], item["role"]) for item in rows}:
        return
    rows.append(payload)


def build_frontier_table(
    leaderboard: pd.DataFrame,
    claim_summary: dict[str, object],
    *,
    caps: list[float],
) -> dict[str, object]:
    eligible = leaderboard[
        (leaderboard["alpha_exact_pass_count"] == leaderboard["alpha_exact_check_count"])
        & (leaderboard["return_floor_surplus"] >= 0)
    ].copy()
    rows: list[dict[str, object]] = []

    summary_candidates = {
        "bound-tight endpoint": "best_gamma_cp_return_floor_claim",
        "body/default balanced return-bound point": "balanced_return_bound_claim",
        "lowest realized V return-bound point": "best_weighted_miscoverage_return_floor_claim",
        "max-return economic endpoint": "max_return_claim",
    }
    for role, key in summary_candidates.items():
        candidate = claim_summary.get(key, {})
        if not isinstance(candidate, dict) or "local_candidate_id" not in candidate:
            continue
        candidate = cast(dict[str, Any], candidate)
        candidate_id = int(candidate["local_candidate_id"])
        _append_unique(
            rows,
            _first_or_none(leaderboard[leaderboard["local_candidate_id"] == candidate_id]),
            role,
        )

    for cap in caps:
        cap_df = eligible[eligible["alpha01_markov_loss_cap"] <= cap].sort_values(
            "alpha01_realized_total_return",
            ascending=False,
        )
        _append_unique(
            rows,
            _first_or_none(cap_df),
            f"highest return under cap<={cap:g}",
        )

    return {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "selection_rule": {
            "eligible": "all-alpha pass and nonnegative return_floor_surplus",
            "caps": caps,
            "role_semantics": "finite-grid frontier roles, not continuous optima",
        },
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--leaderboard", default="")
    parser.add_argument("--claim-summary", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--caps", default="0.33,0.345,0.36,0.50")
    args = parser.parse_args(argv)

    leaderboard_path, claim_summary_path, output_path = _default_paths(str(args.run_tag))
    if args.leaderboard:
        leaderboard_path = Path(args.leaderboard)
    if args.claim_summary:
        claim_summary_path = Path(args.claim_summary)
    if args.output:
        output_path = Path(args.output)

    caps = [float(part.strip()) for part in str(args.caps).split(",") if part.strip()]
    leaderboard = pd.read_parquet(leaderboard_path)
    claim_summary = json.loads(claim_summary_path.read_text(encoding="utf-8"))
    payload = build_frontier_table(leaderboard, claim_summary, caps=caps)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
