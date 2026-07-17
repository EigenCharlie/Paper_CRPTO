"""Endpoint-availability sensitivity for frozen IJDS scores and allocations."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.outcome_observability import build_outcome_label_availability
from src.ijds_audit.evaluation import build_archive_outcomes


def rebuild_archive_outcomes(
    universe: pd.DataFrame,
    *,
    evaluation_cutoff: str | pd.Timestamp,
    charged_off_lag_months: int,
) -> pd.DataFrame:
    """Reconstruct one endpoint without changing candidate membership."""
    lag = int(charged_off_lag_months)
    if lag < 0:
        raise ValueError("Charged-off reporting lag must be nonnegative.")
    required = {"id", "loan_status", "last_pymnt_d", "design_split", "issue_d"}
    missing = sorted(required.difference(universe.columns))
    if missing:
        raise KeyError(f"Endpoint sensitivity universe is missing columns: {missing}.")
    labels = build_outcome_label_availability(
        universe["loan_status"],
        universe["last_pymnt_d"],
        cutoff=evaluation_cutoff,
        charged_off_lag_months=lag,
    )
    lagged = universe.copy()
    lagged["terminal_default"] = labels["terminal_outcome"].astype("Int8")
    lagged["label_available_at"] = labels["label_available_at"]
    outcomes = build_archive_outcomes(lagged, evaluation_cutoff=evaluation_cutoff)
    if len(outcomes) != len(universe) or not outcomes["id"].equals(universe["id"].astype("string")):
        raise RuntimeError("Endpoint reconstruction changed universe membership or order.")
    return outcomes


def endpoint_census(outcomes: pd.DataFrame, *, lag_months: int) -> pd.DataFrame:
    """Count resolved and unresolved candidates by declared design role."""
    rows: list[dict[str, Any]] = []
    for role, frame in outcomes.groupby("role", observed=True, sort=True):
        resolved = int(frame["snapshot_default"].notna().sum())
        rows.append(
            {
                "charged_off_lag_months": int(lag_months),
                "role": str(role),
                "candidate_rows": int(len(frame)),
                "resolved_rows": resolved,
                "unresolved_rows": int(len(frame) - resolved),
                "default_rows": int(frame["snapshot_default"].eq(1).sum()),
                "nondefault_rows": int(frame["snapshot_default"].eq(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_coverage_sensitivity(coverage: pd.DataFrame) -> pd.DataFrame:
    """Summarize complete-window canonical coverage without selecting a learner."""
    required = {
        "charged_off_lag_months",
        "learner",
        "role",
        "window_id",
        "coverage_lower",
        "coverage_upper",
    }
    missing = sorted(required.difference(coverage.columns))
    if missing:
        raise KeyError(f"Coverage sensitivity is missing columns: {missing}.")
    return (
        coverage.groupby(
            ["charged_off_lag_months", "learner", "role"],
            observed=True,
            sort=True,
        )
        .agg(
            windows=("window_id", "nunique"),
            coverage_lower_min=("coverage_lower", "min"),
            coverage_upper_max=("coverage_upper", "max"),
        )
        .reset_index()
    )


def direction_census(directions: pd.DataFrame, *, lag_months: int) -> pd.DataFrame:
    """Count every two-ruler direction, retaining crossing and exact-zero cells."""
    rows: list[dict[str, Any]] = []
    for metric, frame in directions.groupby("metric", observed=True, sort=True):
        counts = frame["direction"].value_counts().to_dict()
        for direction in ("gamma_1_lower", "gamma_1_higher", "crosses_zero", "exact_zero"):
            rows.append(
                {
                    "charged_off_lag_months": int(lag_months),
                    "metric": str(metric),
                    "direction": direction,
                    "cells": int(counts.get(direction, 0)),
                }
            )
    return pd.DataFrame(rows)


def exact_support_census(envelopes: pd.DataFrame, *, lag_months: int) -> pd.DataFrame:
    """Count exact-support directions by scope and metric."""
    census = (
        envelopes.groupby(["scope", "metric", "direction"], observed=True, sort=True)
        .size()
        .reset_index()
    )
    census.columns = ["scope", "metric", "direction", "cells"]
    return census.assign(charged_off_lag_months=int(lag_months))
