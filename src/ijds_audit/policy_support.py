"""Outcome-free policy-support and point-LP stability diagnostics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

import highspy
import numpy as np
import pandas as pd

from src.ijds_audit.portfolio import PointPortfolioSession, PointPortfolioSolution

NAMED_SOURCE = {
    "c0_same_numeric_cap": "named_c0",
    "c1_development_mean": "named_c1",
    "c2_contemporaneous": "named_c2",
}


def classify_cap(
    cap: float,
    *,
    minimum_feasible_score: float,
    unconstrained_objective_score: float,
    tolerance: float,
) -> str:
    """Classify a score cap without observing any realized outcome."""
    value = float(cap)
    lower = float(minimum_feasible_score)
    upper = float(unconstrained_objective_score)
    tol = float(tolerance)
    if upper < lower - tol:
        raise ValueError("The unconstrained objective score is below the feasible minimum.")
    if value < lower - tol:
        return "infeasible"
    if abs(value - lower) <= tol:
        return "minimum_boundary"
    if value < upper - tol:
        return "decision_active"
    if abs(value - upper) <= tol:
        return "objective_boundary"
    return "objective_slack"


def point_basis_diagnostics(
    session: PointPortfolioSession,
    solution: PointPortfolioSolution,
    *,
    dual_tolerance: float,
    primal_tolerance: float,
) -> dict[str, Any]:
    """Inspect one optimal HiGHS basis for alternate-optimum warning signs."""
    raw = session.solver.getSolution()
    basis = session.solver.getBasis()
    lp = session.solver.getLp()
    values = np.asarray(raw.col_value, dtype=float)
    reduced = np.asarray(raw.col_dual, dtype=float)
    costs = np.asarray(lp.col_cost_, dtype=float)
    statuses = np.asarray(basis.col_status, dtype=object)
    basic = statuses == highspy.HighsBasisStatus.kBasic
    lower = statuses == highspy.HighsBasisStatus.kLower
    upper = statuses == highspy.HighsBasisStatus.kUpper
    nonbasic = ~basic
    if not bool(nonbasic.any()):
        raise RuntimeError("Point LP basis unexpectedly has no nonbasic columns.")
    absolute_reduced = np.abs(reduced[nonbasic])
    scaled_reduced = absolute_reduced / np.maximum(1.0, np.abs(costs[nonbasic]))
    near_zero = absolute_reduced <= float(dual_tolerance)
    basic_column_degeneracy = basic & (
        (values <= float(primal_tolerance)) | (values >= 1.0 - float(primal_tolerance))
    )

    row_statuses = np.asarray(basis.row_status, dtype=object)
    row_values = np.asarray(raw.row_value, dtype=float)
    row_lower = np.asarray(lp.row_lower_, dtype=float)
    row_upper = np.asarray(lp.row_upper_, dtype=float)
    basic_rows = row_statuses == highspy.HighsBasisStatus.kBasic
    inequality_rows = np.abs(row_upper - row_lower) > float(primal_tolerance)
    lower_distance = np.where(np.isfinite(row_lower), np.abs(row_values - row_lower), np.inf)
    upper_distance = np.where(np.isfinite(row_upper), np.abs(row_upper - row_values), np.inf)
    basic_row_degeneracy = (
        basic_rows
        & inequality_rows
        & (np.minimum(lower_distance, upper_distance) <= float(primal_tolerance))
    )

    lower_violation = float(np.maximum(reduced[lower], 0.0).max(initial=0.0))
    upper_violation = float(np.maximum(-reduced[upper], 0.0).max(initial=0.0))
    reconciled_objective = float(session.amount @ (values * session.objective))
    return {
        "basis_valid": bool(basis.valid),
        "basic_columns": int(basic.sum()),
        "lower_nonbasic_columns": int(lower.sum()),
        "upper_nonbasic_columns": int(upper.sum()),
        "minimum_absolute_nonbasic_reduced_cost": float(absolute_reduced.min()),
        "minimum_scaled_nonbasic_reduced_cost": float(scaled_reduced.min()),
        "near_zero_nonbasic_reduced_costs": int(near_zero.sum()),
        "primal_degenerate_basic_columns": int(basic_column_degeneracy.sum()),
        "primal_degenerate_basic_rows": int(basic_row_degeneracy.sum()),
        "basis_primal_degenerate": bool(
            basic_column_degeneracy.any() or basic_row_degeneracy.any()
        ),
        "maximum_dual_sign_violation": max(lower_violation, upper_violation),
        "objective_reconciliation_error": float(reconciled_objective - solution.objective_value),
    }


def _append_caps(
    target: dict[str, list[tuple[float, str]]],
    rows: Iterable[tuple[str, float, str]],
) -> None:
    for period, cap, source in rows:
        target[str(period)].append((float(cap), str(source)))


def build_cap_census(
    solve_records: pd.DataFrame,
    comparator_support: pd.DataFrame,
    frontier: pd.DataFrame,
    *,
    periods: Sequence[str],
    broad_support: tuple[float, float],
    tolerance: float,
) -> pd.DataFrame:
    """Return the tolerance-deduplicated cap-month union with source flags."""
    period_set = {str(period) for period in periods}
    if not period_set:
        raise ValueError("Point-cap census requires at least one period.")
    collected: dict[str, list[tuple[float, str]]] = defaultdict(list)
    named = solve_records.loc[solve_records["comparator_rule"].isin(NAMED_SOURCE)].copy()
    _append_caps(
        collected,
        (
            (str(row.period), float(row.frontier_cap), NAMED_SOURCE[str(row.comparator_rule)])
            for row in named.itertuples(index=False)
        ),
    )
    support_values = {
        "development_support_lower": comparator_support["support_lower"].to_numpy(dtype=float),
        "development_support_upper": comparator_support["support_upper"].to_numpy(dtype=float),
    }
    for period in sorted(period_set):
        for source, values in support_values.items():
            _append_caps(collected, ((period, float(value), source) for value in values))
        _append_caps(
            collected,
            (
                (period, float(broad_support[0]), "broad_support_lower"),
                (period, float(broad_support[1]), "broad_support_upper"),
            ),
        )
    enumerated = frontier.loc[frontier["is_enumerated_support_breakpoint"]]
    _append_caps(
        collected,
        (
            (str(row.period), float(row.frontier_cap), "period_basis_breakpoint")
            for row in enumerated.itertuples(index=False)
        ),
    )
    if set(collected) != period_set:
        raise RuntimeError("Cap census periods do not match the primary monthly menus.")

    output: list[dict[str, Any]] = []
    sources = sorted(
        {source for period_values in collected.values() for _, source in period_values}
    )
    for period in sorted(collected):
        ordered = sorted(collected[period])
        clusters: list[list[tuple[float, str]]] = []
        for item in ordered:
            if not clusters or item[0] - clusters[-1][-1][0] > float(tolerance):
                clusters.append([item])
            else:
                clusters[-1].append(item)
        for cluster in clusters:
            caps = [item[0] for item in cluster]
            observed_sources = {item[1] for item in cluster}
            output.append(
                {
                    "period": period,
                    "point_cap": float(sum(caps) / len(caps)),
                    "cluster_cap_min": float(min(caps)),
                    "cluster_cap_max": float(max(caps)),
                    "cap_sources": "|".join(sorted(observed_sources)),
                    **{f"is_{source}": source in observed_sources for source in sources},
                }
            )
    result = pd.DataFrame(output).sort_values(["period", "point_cap"]).reset_index(drop=True)
    if bool((result["cluster_cap_max"] - result["cluster_cap_min"] > tolerance).any()):
        raise RuntimeError("Tolerance-deduplicated cap cluster exceeds its declared width.")
    return result
