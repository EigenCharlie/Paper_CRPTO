"""Fail-closed deterministic diagnostics over frozen IJDS artifacts.

The functions in this module do not fit models, reconstruct endpoints, rerun a
hypothesis test, or optimize a portfolio. They derive three complete
retrospective tables from already frozen inputs and keep their estimands
separate: all-candidate completion bounds, a resolved-panel mixture
reparameterization, and a p-value-selected descriptive reference magnitude.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


def all_candidate_calibration_bias_table(
    scores: pd.DataFrame,
    endpoint_resolution: pd.DataFrame,
    *,
    score_columns: Mapping[str, str],
    expected_candidates: int,
    expected_resolved_y1: int,
    expected_unresolved: int,
) -> pd.DataFrame:
    """Return sharp bounds for prevalence and ``mean(score - outcome)``."""
    required_scores = {"id", "design_split", *score_columns.values()}
    missing = required_scores.difference(scores.columns)
    if missing:
        raise ValueError(f"Frozen score table omits columns: {sorted(missing)}")
    if not score_columns:
        raise ValueError("At least one frozen score is required.")

    primary = scores.loc[
        scores["design_split"].eq("primary_oot"), sorted(required_scores)
    ].copy()
    if len(primary) != expected_candidates:
        raise RuntimeError(
            f"Primary-OOT score census changed: {len(primary)} != {expected_candidates}."
        )
    if primary["id"].isna().any() or primary["id"].duplicated().any():
        raise RuntimeError("Primary-OOT candidate identifiers are missing or duplicated.")
    for column in score_columns.values():
        if not pd.api.types.is_numeric_dtype(primary[column]):
            raise ValueError(f"Frozen score column {column!r} must be numeric.")
        values = primary[column].to_numpy(dtype=float)
        if not bool(np.isfinite(values).all()):
            raise RuntimeError(f"Frozen score column {column!r} contains a nonfinite value.")
        if bool(np.any(values < 0.0) or np.any(values > 1.0)):
            raise RuntimeError(f"Frozen score column {column!r} leaves [0, 1].")

    required_endpoint = {
        "role",
        "snapshot_resolution",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
    }
    missing_endpoint = required_endpoint.difference(endpoint_resolution.columns)
    if missing_endpoint:
        raise ValueError(
            f"Endpoint-reason table omits columns: {sorted(missing_endpoint)}"
        )
    endpoint = endpoint_resolution.loc[endpoint_resolution["role"].eq("primary_oot")].copy()
    expected_reasons = {
        "charged_off_by_reconstructed_cutoff",
        "fully_paid_by_reconstructed_cutoff",
        "nonterminal_or_unresolved_status",
        "terminal_after_reconstructed_cutoff",
        "terminal_availability_date_missing",
    }
    if set(endpoint["snapshot_resolution"].astype(str)) != expected_reasons:
        raise RuntimeError("The primary-OOT endpoint-reason partition changed.")
    if endpoint["snapshot_resolution"].duplicated().any():
        raise RuntimeError("The primary-OOT endpoint-reason table contains duplicates.")
    default = endpoint.loc[
        endpoint["snapshot_resolution"].eq("charged_off_by_reconstructed_cutoff")
    ]
    if len(default) != 1:
        raise RuntimeError("The resolved-default endpoint row is not unique.")
    actual = (
        int(endpoint["candidate_rows"].sum()),
        int(default["resolved_rows"].iloc[0]),
        int(endpoint["unresolved_rows"].sum()),
    )
    expected = (expected_candidates, expected_resolved_y1, expected_unresolved)
    if actual != expected:
        raise RuntimeError(f"The sharp outcome census changed: {actual} != {expected}.")

    prevalence_lower = expected_resolved_y1 / expected_candidates
    prevalence_upper = (expected_resolved_y1 + expected_unresolved) / expected_candidates
    rows: list[dict[str, object]] = []
    for learner, column in score_columns.items():
        mean_score = float(primary[column].mean())
        rows.append(
            {
                "learner": str(learner),
                "candidate_rows": int(expected_candidates),
                "resolved_defaults": int(expected_resolved_y1),
                "unresolved_outcomes": int(expected_unresolved),
                "mean_score": mean_score,
                "default_prevalence_lower": prevalence_lower,
                "default_prevalence_upper": prevalence_upper,
                "mean_score_minus_outcome_lower": mean_score - prevalence_upper,
                "mean_score_minus_outcome_upper": mean_score - prevalence_lower,
            }
        )
    table = pd.DataFrame.from_records(rows)
    if table["learner"].duplicated().any() or len(table) != len(score_columns):
        raise RuntimeError("The all-candidate learner census is incomplete or duplicated.")
    if not bool(table["mean_score_minus_outcome_upper"].lt(0.0).all()):
        raise RuntimeError("A declared all-candidate calibration upper endpoint is nonnegative.")
    return table.sort_values("learner").reset_index(drop=True)


def resolved_coverage_breakeven_table(
    conformal_sets: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    alpha: float,
    expected_resolved_y0: int,
    expected_resolved_y1: int,
    tolerance: float = 1.0e-12,
) -> pd.DataFrame:
    """Verify the resolved mixture and return every cellwise breakeven."""
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly inside the unit interval.")
    required = {
        "learner",
        "window_id",
        "coverage_resolved",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "resolved_y0_rows",
        "resolved_y1_rows",
    }
    missing = required.difference(conformal_sets.columns)
    if missing:
        raise ValueError(f"Conformal-set table omits columns: {sorted(missing)}")
    table = conformal_sets.loc[:, sorted(required)].copy()
    keys = ["learner", "window_id"]
    if table.duplicated(keys).any():
        raise RuntimeError("The conformal-set table contains a duplicated cell key.")
    expected_keys = {(str(a), str(b)) for a in learners for b in window_ids}
    actual_keys = set(
        zip(table["learner"].astype(str), table["window_id"].astype(str), strict=True)
    )
    if actual_keys != expected_keys or len(table) != len(expected_keys):
        raise RuntimeError("The conformal-set table left the declared learner-window grid.")
    numeric = sorted(required.difference(keys))
    values = table[numeric].to_numpy(dtype=float)
    if not bool(np.isfinite(values).all()):
        raise RuntimeError("The conformal-set table contains a nonfinite value.")
    if not bool(
        table["resolved_y0_rows"].eq(expected_resolved_y0).all()
        and table["resolved_y1_rows"].eq(expected_resolved_y1).all()
    ):
        raise RuntimeError("The common resolved-panel class census changed.")
    coverage_columns = [
        "coverage_resolved",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
    ]
    if not all(table[column].between(0.0, 1.0).all() for column in coverage_columns):
        raise RuntimeError("A resolved coverage value lies outside [0, 1].")

    resolved = expected_resolved_y0 + expected_resolved_y1
    prevalence = expected_resolved_y1 / resolved
    reconstructed = (1.0 - prevalence) * table["coverage_resolved_y0"] + (
        prevalence * table["coverage_resolved_y1"]
    )
    mixture_residual = (reconstructed - table["coverage_resolved"]).abs()
    if not bool(mixture_residual.le(tolerance).all()):
        raise RuntimeError("The resolved binary coverage mixture identity did not reconcile.")
    spread = table["coverage_resolved_y0"] - table["coverage_resolved_y1"]
    if not bool(spread.gt(0.0).all()):
        raise RuntimeError("A class-coverage spread is nonpositive.")
    breakeven = (table["coverage_resolved_y0"] - (1.0 - alpha)) / spread
    if not bool(np.isfinite(breakeven.to_numpy(dtype=float)).all()):
        raise RuntimeError("A breakeven prevalence is nonfinite.")
    if not bool(breakeven.between(0.0, 1.0).all()):
        raise RuntimeError("A breakeven prevalence lies outside [0, 1].")
    reduction = (prevalence - breakeven) / prevalence

    result = table[keys + coverage_columns].copy()
    result["resolved_y0_rows"] = int(expected_resolved_y0)
    result["resolved_y1_rows"] = int(expected_resolved_y1)
    result["resolved_prevalence"] = float(prevalence)
    result["mixture_identity_abs_residual"] = mixture_residual
    result["breakeven_prevalence"] = breakeven
    result["relative_prevalence_reduction_to_nominal"] = reduction
    return result.sort_values(keys).reset_index(drop=True)


def minimum_reference_stratum_effect_table(
    strata: pd.DataFrame,
    cells: pd.DataFrame,
    *,
    learners: Sequence[str],
    window_ids: Sequence[str],
    taxonomy_groups: int,
    expected_holm_flags: int,
) -> pd.DataFrame:
    """Return the locked p-value-selected stratum magnitude for all cells."""
    strata_required = {
        "learner",
        "window_id",
        "conformal_group",
        "exact_log_p_value",
        "miss_rate_min",
        "null_expected_miss_rate",
    }
    cell_flag = "holm_reject_exchangeability_null"
    cell_required = {"learner", "window_id", cell_flag}
    if missing := strata_required.difference(strata.columns):
        raise ValueError(f"Joint-block stratum table omits columns: {sorted(missing)}")
    if missing := cell_required.difference(cells.columns):
        raise ValueError(f"Joint-block cell table omits columns: {sorted(missing)}")
    keys = ["learner", "window_id"]
    stratum_keys = [*keys, "conformal_group"]
    if strata.duplicated(stratum_keys).any() or cells.duplicated(keys).any():
        raise RuntimeError("Joint-block source keys are duplicated.")
    expected_cells = {(str(a), str(b)) for a in learners for b in window_ids}
    expected_strata = {
        (str(a), str(b), group)
        for a in learners
        for b in window_ids
        for group in range(int(taxonomy_groups))
    }
    actual_cells = set(
        zip(cells["learner"].astype(str), cells["window_id"].astype(str), strict=True)
    )
    actual_strata = set(
        zip(
            strata["learner"].astype(str),
            strata["window_id"].astype(str),
            strata["conformal_group"].astype(int),
            strict=True,
        )
    )
    if actual_cells != expected_cells or actual_strata != expected_strata:
        raise RuntimeError("The joint-block source left the declared complete grid.")
    numeric = ["exact_log_p_value", "miss_rate_min", "null_expected_miss_rate"]
    if not bool(np.isfinite(strata[numeric].to_numpy(dtype=float)).all()):
        raise RuntimeError("The joint-block stratum table contains a nonfinite value.")
    flags = cells[cell_flag]
    if not bool(flags.isin([True, False, 0, 1]).all()):
        raise RuntimeError("The joint-block cell flag is not boolean.")
    if int(flags.astype(bool).sum()) != int(expected_holm_flags):
        raise RuntimeError("The locked nominal Holm flag census changed.")

    ordered = strata.sort_values(
        [*keys, "exact_log_p_value", "conformal_group"],
        kind="mergesort",
    )
    chosen = ordered.groupby(keys, observed=True, sort=False).head(1).copy()
    if len(chosen) != len(expected_cells):
        raise RuntimeError("The minimum-reference-stratum selection is incomplete.")
    chosen["minimum_reference_score_stratum"] = chosen["conformal_group"].astype(int) + 1
    chosen["minimum_reference_excess_miss_rate_pp"] = 100.0 * (
        chosen["miss_rate_min"] - chosen["null_expected_miss_rate"]
    )
    result = chosen[
        [
            *keys,
            "minimum_reference_score_stratum",
            "exact_log_p_value",
            "miss_rate_min",
            "null_expected_miss_rate",
            "minimum_reference_excess_miss_rate_pp",
        ]
    ].merge(cells[[*keys, cell_flag]], on=keys, how="left", validate="one_to_one")
    result = result.rename(columns={cell_flag: "meets_locked_nominal_holm_threshold"})
    if not bool(
        np.isfinite(result["minimum_reference_excess_miss_rate_pp"].to_numpy(dtype=float)).all()
    ):
        raise RuntimeError("A minimum-reference-stratum magnitude is nonfinite.")
    return result.sort_values(keys).reset_index(drop=True)


def range_summary(values: pd.Series) -> dict[str, float | int]:
    """Return a stable scalar summary for a nonempty finite numeric series."""
    data = values.astype(float)
    if data.empty or not bool(np.isfinite(data.to_numpy()).all()):
        raise ValueError("A range summary requires nonempty finite values.")
    return {
        "cells": int(len(data)),
        "minimum": float(data.min()),
        "median": float(data.median()),
        "maximum": float(data.max()),
    }
