"""Build tracked evidence from the locked decision-active simulation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.ijds_audit.decision_simulation import FACTOR_COLUMNS
from src.utils.isolated_experiment import (
    relative_artifact_descriptor,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
RUN_TAG = "ijds-decision-active-simulation-2026-07-12-v1"
MODEL_DIR = ROOT / "models/experiments/ijds_audit" / RUN_TAG
DATA_DIR = ROOT / "data/processed/experiments/ijds_audit" / RUN_TAG
SOURCE_SUMMARY = MODEL_DIR / "decision_active_simulation_summary.json"
REPETITIONS = DATA_DIR / "decision_active_repetitions.parquet"
DIRECTIONS = DATA_DIR / "decision_active_direction_counts.parquet"
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_decision_active_simulation_evidence.json"
TABLE_DIR = ROOT / "reports/crpto/tables"
MEMO_PATH = ROOT / "docs/research/ijds_decision_active_simulation_results_2026-07-12.md"
PROTOCOL_TAG = "protocol/ijds-decision-active-simulation-2026-07-12-v1"
PROTOCOL_COMMIT = "acbe65e8138ecf5cb1296e8b8780ce18b7e87dc0"


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _verify_descriptor(descriptor: Mapping[str, Any]) -> Path:
    path = (ROOT / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Decision-active source mismatch for {path}: {field}.")
    return path


def _collapse_paired(
    frame: pd.DataFrame,
    *,
    keys: list[str],
    values: list[str],
) -> pd.DataFrame:
    grouped = frame.groupby(keys, observed=True, sort=True)[values]
    if not bool(grouped.nunique().le(1).all().all()):
        raise RuntimeError(f"Paired decision-active values diverged for keys {keys}.")
    return grouped.first().reset_index()


def _coverage_table(repetitions: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "repetition",
        "score_shift",
        "calibration_log_odds_shift",
        "taxonomy_groups",
    ]
    values = [
        "candidate_coverage_full",
        "mean_width",
        "set_both_share",
        "upper_saturated_share",
    ]
    paired = _collapse_paired(repetitions, keys=keys, values=values)
    table = (
        paired.groupby(keys[1:], observed=True, sort=True)
        .agg(
            repetitions=("repetition", "size"),
            coverage_mean=("candidate_coverage_full", "mean"),
            coverage_std=("candidate_coverage_full", "std"),
            coverage_min=("candidate_coverage_full", "min"),
            coverage_max=("candidate_coverage_full", "max"),
            mean_width=("mean_width", "mean"),
            both_set_share=("set_both_share", "mean"),
            upper_saturated_share=("upper_saturated_share", "mean"),
        )
        .reset_index()
    )
    if len(table) != 12 or not bool(table["repetitions"].eq(50).all()):
        raise RuntimeError("Decision-active coverage table lost a paired factorial cell.")
    return table


def _allocation_table(repetitions: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "repetition",
        "score_shift",
        "taxonomy_groups",
        "normalized_cap_position",
    ]
    values = [
        "c0_allocation_distance",
        "c2_allocation_distance",
        "c0_allocation_changed",
        "c2_allocation_changed",
        "c0_same_numeric_cap_slack",
        "c0_point_minus_guardrail_objective",
        "point_minus_guardrail_objective",
    ]
    paired = _collapse_paired(repetitions, keys=keys, values=values)
    table = (
        paired.groupby(keys[1:], observed=True, sort=True)
        .agg(
            repetitions=("repetition", "size"),
            c0_distance_mean=("c0_allocation_distance", "mean"),
            c0_changed_rate=("c0_allocation_changed", "mean"),
            c2_distance_mean=("c2_allocation_distance", "mean"),
            c2_changed_rate=("c2_allocation_changed", "mean"),
            c0_same_numeric_cap_slack_mean=("c0_same_numeric_cap_slack", "mean"),
            c0_objective_gain_mean=("c0_point_minus_guardrail_objective", "mean"),
            c2_objective_gain_mean=("point_minus_guardrail_objective", "mean"),
        )
        .reset_index()
    )
    if len(table) != 12 or not bool(table["repetitions"].eq(50).all()):
        raise RuntimeError("Decision-active allocation table lost a paired factorial cell.")
    return table


def _direction_table(direction_counts: pd.DataFrame) -> pd.DataFrame:
    table = (
        direction_counts.groupby(
            ["comparator", "metric", "censoring_rate", "taxonomy_groups", "direction"],
            observed=True,
            sort=True,
        )["repetitions"]
        .sum()
        .reset_index()
    )
    totals = table.groupby(
        ["comparator", "metric", "censoring_rate", "taxonomy_groups"], observed=True
    )["repetitions"].sum()
    if not bool(totals.eq(900).all()):
        raise RuntimeError("Direction census must retain 900 rows per reported scope.")
    return table


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", double_precision=15))


def _memo(evidence: Mapping[str, Any]) -> str:
    results = evidence["results"]
    checks = evidence["structural_checks"]
    return f"""# IJDS Decision-Active Simulation Results

## Status and boundary

This is pre-freeze synthetic mechanism evidence from the protocol tagged
`{PROTOCOL_TAG}` at commit `{PROTOCOL_COMMIT[:7]}`. It is not empirical sign
validation and does not modify the active V4 claim registry. All 72 cells and
3,600 repetitions are retained.

## Structural result

- Every guardrail cap binds; maximum absolute slack is
  `{checks["maximum_absolute_guardrail_cap_slack"]:.3e}`.
- Maximum absolute budget residual is
  `{checks["maximum_absolute_budget_residual"]:.3e}` and maximum C2 moment
  residual is `{checks["maximum_absolute_c2_match_residual"]:.3e}`.
- C0 changes `{results["c0_changed_count"]}` of 3,600 allocations. C2 changes
  `{results["c2_changed_count"]}` of 3,600, including every five-stratum cell.
- With one stratum, C2 changes only `{results["c2_one_group_changed_count"]}` of
  1,800 allocations because the effective score is nearly a common monotone
  transformation of point PD. With five strata, group-specific residual
  quantiles alter ordering and activate C2.

## Coverage mechanism

At zero score and calibration shift, mean complete-outcome coverage is
`{results["baseline_coverage_one_group"]:.6f}` for one stratum and
`{results["baseline_coverage_five_groups"]:.6f}` for five. A log-odds
calibration shift of 1.5 lowers those means to
`{results["strong_calibration_shift_coverage_one_group"]:.6f}` and
`{results["strong_calibration_shift_coverage_five_groups"]:.6f}`. Under a score
shift of 0.08 with no calibration shift, five strata recover mean coverage
`{results["score_shift_coverage_five_groups"]:.6f}` only with mean interval
width `{results["score_shift_width_five_groups"]:.6f}` and both-outcome set share
`{results["score_shift_both_share_five_groups"]:.6f}`. Coverage and informativeness
must therefore be reported together.

## Comparator result

C0 is a positive control, not a neutral baseline. Copying the effective-score
cap onto point PD weakly enlarges the feasible set and leaves positive mean
slack in `{results["c0_positive_slack_cells"]}` of 12 allocation cells. Mean
slack ranges between `{results["c0_slack_mean_min"]:.6f}` and
`{results["c0_slack_mean_max"]:.6f}` across the reported cells. C2 removes
that funded point-moment difference, but realized payoff, default, and
miscoverage directions still reverse across cells. At 15 percent censoring,
sharp bounds cross zero in most C2 contrasts. No universal simulated economic
direction is allowed.

## Consequence for the manuscript

The earlier V4 simulation remains valid negative provenance but is no longer
the best decision-mechanism experiment: its cap was slack. This locked run can
replace that degenerate portfolio subsection while preserving the boundary that
synthetic signs do not validate Lending Club. Its strongest contribution is
mechanistic: decision activation, taxonomy-dependent ordering, and comparator
semantics are distinct from candidate coverage.
"""


def build() -> Path:
    """Verify immutable sources and write compact tracked evidence."""
    summary = _json(SOURCE_SUMMARY)
    if summary.get("status") != "complete":
        raise RuntimeError("Decision-active source run is incomplete.")
    if summary.get("protocol_tag") != PROTOCOL_TAG:
        raise RuntimeError("Decision-active protocol tag mismatch.")
    if summary.get("protocol_commit") != PROTOCOL_COMMIT:
        raise RuntimeError("Decision-active protocol commit mismatch.")
    for descriptor in summary["artifacts"].values():
        _verify_descriptor(descriptor)
    repetitions = pd.read_parquet(REPETITIONS)
    directions = pd.read_parquet(DIRECTIONS)
    if len(repetitions) != 3_600 or set(FACTOR_COLUMNS).difference(repetitions):
        raise RuntimeError("Decision-active repetition artifact is incomplete.")

    coverage = _coverage_table(repetitions)
    allocation = _allocation_table(repetitions)
    direction = _direction_table(directions)
    table_paths = {
        "coverage": write_csv_atomic(
            coverage, TABLE_DIR / "crpto_ijds_decision_active_coverage.csv"
        ),
        "allocation": write_csv_atomic(
            allocation, TABLE_DIR / "crpto_ijds_decision_active_allocation.csv"
        ),
        "directions": write_csv_atomic(
            direction, TABLE_DIR / "crpto_ijds_decision_active_directions.csv"
        ),
    }

    def coverage_value(score: float, shift: float, groups: int, column: str) -> float:
        row = coverage.loc[
            coverage["score_shift"].eq(score)
            & coverage["calibration_log_odds_shift"].eq(shift)
            & coverage["taxonomy_groups"].eq(groups)
        ].iloc[0]
        return float(row[column])

    results = {
        "c0_changed_count": int(repetitions["c0_allocation_changed"].sum()),
        "c2_changed_count": int(repetitions["c2_allocation_changed"].sum()),
        "c2_one_group_changed_count": int(
            repetitions.loc[repetitions["taxonomy_groups"].eq(1), "c2_allocation_changed"].sum()
        ),
        "c2_five_group_changed_count": int(
            repetitions.loc[repetitions["taxonomy_groups"].eq(5), "c2_allocation_changed"].sum()
        ),
        "baseline_coverage_one_group": coverage_value(0.0, 0.0, 1, "coverage_mean"),
        "baseline_coverage_five_groups": coverage_value(0.0, 0.0, 5, "coverage_mean"),
        "strong_calibration_shift_coverage_one_group": coverage_value(0.0, 1.5, 1, "coverage_mean"),
        "strong_calibration_shift_coverage_five_groups": coverage_value(
            0.0, 1.5, 5, "coverage_mean"
        ),
        "score_shift_coverage_five_groups": coverage_value(0.08, 0.0, 5, "coverage_mean"),
        "score_shift_width_five_groups": coverage_value(0.08, 0.0, 5, "mean_width"),
        "score_shift_both_share_five_groups": coverage_value(0.08, 0.0, 5, "both_set_share"),
        "c0_slack_mean_min": float(allocation["c0_same_numeric_cap_slack_mean"].min()),
        "c0_slack_mean_max": float(allocation["c0_same_numeric_cap_slack_mean"].max()),
        "c0_positive_slack_cells": int(
            allocation["c0_same_numeric_cap_slack_mean"].gt(1e-12).sum()
        ),
        "coverage_cells": _records(coverage),
        "allocation_cells": _records(allocation),
        "direction_census": _records(direction),
    }
    evidence = {
        "schema_version": "2026-07-12.1",
        "status": "complete_prefreeze_robustness_evidence",
        "active_claim_status": "not_active_until_manuscript_promotion_decision",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "claim_boundary": summary["claim_boundary"],
        "structural_checks": summary["structural_checks"],
        "results": results,
        "source_summary": relative_artifact_descriptor(SOURCE_SUMMARY, repo_root=ROOT),
        "source_artifacts": summary["artifacts"],
        "tables": {
            name: relative_artifact_descriptor(path, repo_root=ROOT)
            for name, path in table_paths.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    atomic_write_json(EVIDENCE_PATH, evidence)
    atomic_write_text(MEMO_PATH, _memo(evidence))
    return EVIDENCE_PATH


if __name__ == "__main__":
    build()
