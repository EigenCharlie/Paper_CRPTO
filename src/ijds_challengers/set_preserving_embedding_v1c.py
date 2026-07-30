"""V1c-only scientific corrections for the retrospective embedding recovery."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.policy_contrast_bounds import PolicyContrastIndex
from src.ijds_challengers.set_preserving_embedding import (
    CONTRAST_GAMMA,
    CONTRAST_THETA,
    SetPreservingFrontierBuild,
    _contrast_specs,
    metric_direction_census,
    policy_label,
    validate_complete_evaluation,
    validate_complete_frontier,
)


def validate_v1c_complete_frontier(
    build: SetPreservingFrontierBuild,
    *,
    config: Mapping[str, Any],
    budget: float,
) -> None:
    """Retain V1a's finite-value/nullability/basis repair without active-code drift."""
    validate_complete_frontier(build, config=config, budget=budget)
    census_frames = {
        "frontier_solves": build.solve_records,
        "embedding_diagnostics": build.embedding_diagnostics,
        "minimum_score_endpoints": build.minimum_endpoint_diagnostics,
        "objective_optima": build.objective_optimum_diagnostics,
        "order_replays": build.order_sensitivity,
        "independent_solver_cells": build.independent_validation,
        "outcome_free_allocation_contrasts": build.allocation_contrasts,
        "allocations": build.allocations,
    }
    structural_not_applicable = {
        "frontier_solves": {"frontier_cap", "objective_target", "risk_tolerance"},
        "allocations": {"frontier_cap", "objective_target"},
    }
    for key, frame in census_frames.items():
        numeric = frame.select_dtypes(include=[np.number])
        checked = numeric.drop(
            columns=list(structural_not_applicable.get(key, set())), errors="ignore"
        )
        try:
            finite = np.isfinite(checked.to_numpy(dtype=float)).all()
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"{key} contains a non-numeric value in a numeric column."
            ) from error
        if not bool(finite):
            raise RuntimeError(f"{key} contains a non-finite numerical value.")
    for key, frame, nullable in (
        (
            "frontier_solves",
            build.solve_records,
            ("frontier_cap", "objective_target", "risk_tolerance"),
        ),
        ("allocations", build.allocations, ("frontier_cap", "objective_target")),
    ):
        required = {"frontier_ruler", *nullable}
        if not required.issubset(frame):
            raise RuntimeError(f"{key} omits its explicit ruler/nullability contract.")
        ruler = frame["frontier_ruler"].astype(str)
        objective = ruler.eq("objective_matched")
        normalized = ruler.eq("normalized_score")
        if not bool((objective | normalized).all()):
            raise RuntimeError(f"{key} contains an unknown frontier ruler.")
        for column in nullable:
            values = frame[column].to_numpy(dtype=float)
            if bool(np.isinf(values).any()):
                raise RuntimeError(f"{key}.{column} contains an infinite value.")
            applicable = normalized if column != "objective_target" else objective
            if not bool(np.isfinite(values[applicable]).all()) or not bool(
                np.isnan(values[~applicable]).all()
            ):
                raise RuntimeError(
                    f"{key}.{column} violates the exact ruler-specific not-applicable pattern."
                )
    optimum = build.objective_optimum_diagnostics
    if (
        "basis_valid" not in optimum
        or not pd.api.types.is_bool_dtype(optimum["basis_valid"])
        or not bool(optimum["basis_valid"].all())
    ):
        raise RuntimeError("An objective-optimum point basis is absent or invalid.")
    basis_columns = [
        "minimum_absolute_nonbasic_reduced_cost",
        "minimum_scaled_nonbasic_reduced_cost",
        "maximum_dual_sign_violation",
        "objective_reconciliation_error",
    ]
    if not bool(np.isfinite(optimum[basis_columns].to_numpy(dtype=float)).all()):
        raise RuntimeError("An objective-optimum basis contains a non-finite diagnostic.")


def _fixed_capital_rows(
    allocations: pd.DataFrame,
    *,
    scope: str,
    window_id: str,
    period: str | None,
    lgd: float,
    committed_budget_per_period: float,
    normalization_periods: int,
) -> list[dict[str, Any]]:
    if (
        not np.isfinite(committed_budget_per_period)
        or committed_budget_per_period <= 0.0
        or isinstance(normalization_periods, bool)
        or normalization_periods <= 0
    ):
        raise ValueError("Sharp-bound normalization requires a positive budget and period count.")
    normalization_capital = float(committed_budget_per_period) * int(normalization_periods)
    normalization_rule = (
        "monthly_parent_committed_budget"
        if normalization_periods == 1
        else "pooled_period_count_times_parent_committed_budget"
    )
    index = PolicyContrastIndex(allocations, role="primary_oot")
    rows: list[dict[str, Any]] = []
    for spec in _contrast_specs():
        policy_a = policy_label(spec["ruler"], spec["theta"], spec["gamma"], spec["coordinate"])
        policy_b = policy_label(
            spec["ruler"],
            spec["theta_reference"],
            spec["gamma_reference"],
            spec["coordinate"],
        )
        rows.append(
            {
                "scope": scope,
                "window_id": str(window_id),
                "period": period,
                "normalization_rule": normalization_rule,
                "normalization_periods": int(normalization_periods),
                "committed_budget_per_period": float(committed_budget_per_period),
                **spec,
                **index.sharp_bounds(
                    policy_a=policy_a,
                    policy_b=policy_b,
                    lgd=float(lgd),
                    normalization_capital_a=normalization_capital,
                    normalization_capital_b=normalization_capital,
                ),
            }
        )
    return rows


def build_v1c_sharp_embedding_contrasts(
    joined_primary_allocations: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    lgd: float,
    budget: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the complete grid with one common B or TB denominator."""
    if set(joined_primary_allocations["role"].astype(str)) != {"primary_oot"}:
        raise ValueError("Embedding contrasts may evaluate only the primary OOT role.")
    monthly_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    for window_id, window in joined_primary_allocations.groupby(
        "window_id", observed=True, sort=True
    ):
        periods = tuple(sorted(window["period"].astype(str).unique()))
        if len(periods) != int(config["frontier"]["expected_primary_months"]):
            raise RuntimeError(f"Window {window_id} does not contain all primary months.")
        window_rows.extend(
            _fixed_capital_rows(
                window,
                scope="pooled_primary_window",
                window_id=str(window_id),
                period=None,
                lgd=lgd,
                committed_budget_per_period=budget,
                normalization_periods=len(periods),
            )
        )
        for period, month in window.groupby("period", observed=True, sort=True):
            monthly_rows.extend(
                _fixed_capital_rows(
                    month,
                    scope="primary_month",
                    window_id=str(window_id),
                    period=str(period),
                    lgd=lgd,
                    committed_budget_per_period=budget,
                    normalization_periods=1,
                )
            )
    monthly = pd.DataFrame(monthly_rows)
    window = pd.DataFrame(window_rows)
    directions = metric_direction_census(window, metrics=config["metrics"])
    validate_v1c_complete_evaluation(monthly, window, directions, config=config)
    return monthly, window, directions


def validate_v1c_complete_evaluation(
    monthly: pd.DataFrame,
    window: pd.DataFrame,
    directions: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> None:
    """Apply the original complete-grid gates plus the fixed-capital repair."""
    validate_complete_evaluation(monthly, window, directions, config=config)
    for label, frame in (
        ("monthly sharp contrasts", monthly),
        ("pooled sharp contrasts", window),
        ("metric direction census", directions),
    ):
        numeric = frame.select_dtypes(include=[np.number])
        try:
            finite = np.isfinite(numeric.to_numpy(dtype=float)).all()
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{label} contains a non-numeric numeric-field value.") from error
        if not bool(finite):
            raise RuntimeError(f"{label} contains a non-finite numerical value.")
    finite_columns = [
        "normalization_periods",
        "committed_budget_per_period",
        "policy_a_capital",
        "policy_b_capital",
        "policy_a_normalization_capital",
        "policy_b_normalization_capital",
        "expected_objective_difference",
        "realized_payoff_rate_difference_lower",
        "realized_payoff_rate_difference_upper",
    ]
    for frame in (monthly, window):
        if not bool(np.isfinite(frame[finite_columns].to_numpy(dtype=float)).all()):
            raise RuntimeError("Sharp contrast normalization contains a non-finite value.")
    expected_months = int(config["frontier"]["expected_primary_months"])
    budget = float(config["normalization"]["committed_budget_per_period"])
    budget_tolerance = float(config["solver"]["budget_residual_tolerance_dollars"])
    for frame, periods, rule in (
        (monthly, 1, "monthly_parent_committed_budget"),
        (window, expected_months, "pooled_period_count_times_parent_committed_budget"),
    ):
        expected_normalizer = periods * budget
        if (
            set(frame["normalization_rule"].astype(str)) != {rule}
            or not bool(frame["normalization_periods"].eq(periods).all())
            or not bool(frame["committed_budget_per_period"].eq(budget).all())
            or not bool(frame["policy_a_normalization_capital"].eq(expected_normalizer).all())
            or not bool(frame["policy_b_normalization_capital"].eq(expected_normalizer).all())
        ):
            raise RuntimeError(
                "A sharp contrast used solver capital instead of the locked common capital."
            )
        allowed_residual = periods * budget_tolerance
        for column in ("policy_a_capital", "policy_b_capital"):
            if float((frame[column] - expected_normalizer).abs().max()) > allowed_residual:
                raise RuntimeError(
                    f"{column} does not reconcile to the committed common-capital normalizer."
                )
        for suffix in ("lower", "upper"):
            dollar = frame[f"realized_payoff_difference_{suffix}"].to_numpy(dtype=float)
            rate = frame[f"realized_payoff_rate_difference_{suffix}"].to_numpy(dtype=float)
            if not bool(
                np.allclose(
                    rate,
                    dollar / expected_normalizer,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                )
            ):
                raise RuntimeError("Payoff-rate bounds do not equal dollars over locked capital.")
    for label, frame in (("monthly", monthly), ("pooled-window", window)):
        negative = frame.loc[frame["contrast_family"].eq(CONTRAST_THETA) & frame["gamma"].eq(0.0)]
        if not bool(
            np.isfinite(
                negative[
                    [
                        "expected_objective_difference",
                        "realized_payoff_difference_lower",
                        "realized_payoff_difference_upper",
                        "weighted_default_difference_lower",
                        "weighted_default_difference_upper",
                        "weighted_miscoverage_difference_lower",
                        "weighted_miscoverage_difference_upper",
                    ]
                ].to_numpy(dtype=float)
            ).all()
        ):
            raise RuntimeError(f"The gamma=0 {label} control contains a non-finite value.")
    if set(window["contrast_family"].astype(str)) != {CONTRAST_GAMMA, CONTRAST_THETA}:
        raise RuntimeError("A V1c contrast family is missing.")
