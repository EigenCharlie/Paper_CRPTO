"""Outcome-free allocation granularity transform and sharp evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.policy_contrast_bounds import PolicyContrastIndex

PORTFOLIO_KEYS = ("window_id", "role", "period", "policy_label", "comparator_rule")
TRACK_KEYS = ("window_id", "candidate_id")


def floor_allocations_to_lot(
    allocations: pd.DataFrame,
    *,
    lot_size: float,
    committed_budget: float,
    tolerance: float = 1.0e-8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Round exposures down to a fixed lot and retain residual capital as cash."""
    required = {
        *PORTFOLIO_KEYS,
        "candidate_id",
        "id",
        "loan_amnt",
        "exposure",
        "expected_payoff_rate",
        "pd_point",
        "pd_effective",
        "conformal_upper",
        "frontier_cap",
        "purpose",
        "scenario_purpose_cap",
    }
    missing = sorted(required.difference(allocations.columns))
    if missing:
        raise KeyError(f"Allocation granularity input is missing columns: {missing}.")
    if not np.isfinite(lot_size) or lot_size <= 0.0:
        raise ValueError("Lot size must be finite and positive.")
    if not np.isfinite(committed_budget) or committed_budget <= 0.0:
        raise ValueError("Committed budget must be finite and positive.")

    rounded = allocations.copy()
    exposure = pd.to_numeric(rounded["exposure"], errors="raise").to_numpy(dtype=float)
    loan_amount = pd.to_numeric(rounded["loan_amnt"], errors="raise").to_numpy(dtype=float)
    if not bool(np.isfinite(exposure).all()) or bool((exposure < -tolerance).any()):
        raise ValueError("Allocation exposures must be finite and non-negative.")
    if bool((exposure > loan_amount + tolerance).any()):
        raise ValueError("Allocation exposure exceeds the listed loan amount.")

    lot_exposure = np.floor((np.maximum(exposure, 0.0) + tolerance) / lot_size) * lot_size
    lot_exposure = np.minimum(lot_exposure, loan_amount)
    rounded["source_exposure"] = exposure
    rounded["exposure"] = lot_exposure
    rounded["allocation_fraction"] = np.divide(
        lot_exposure,
        loan_amount,
        out=np.zeros_like(lot_exposure),
        where=loan_amount > 0.0,
    )
    rounded["weight"] = lot_exposure / committed_budget
    rounded["expected_payoff_contribution"] = lot_exposure * rounded[
        "expected_payoff_rate"
    ].to_numpy(dtype=float)
    rounded["granularity_transform"] = f"floor_to_{lot_size:g}_cash_residual"
    rounded = rounded.loc[rounded["exposure"].gt(tolerance)].copy()

    original_grouped = allocations.groupby(list(PORTFOLIO_KEYS), observed=True, sort=True)
    rounded_grouped = rounded.groupby(list(PORTFOLIO_KEYS), observed=True, sort=True)
    original_total = original_grouped["exposure"].sum().rename("source_allocated")
    rounded_total = rounded_grouped["exposure"].sum().rename("rounded_allocated")
    changed = (
        allocations.assign(
            changed=np.abs(exposure - lot_exposure) > tolerance,
            source_partial=(exposure > tolerance) & (exposure < loan_amount - tolerance),
        )
        .groupby(list(PORTFOLIO_KEYS), observed=True, sort=True)
        .agg(
            changed_positions=("changed", "sum"), source_partial_positions=("source_partial", "sum")
        )
    )
    rounded_partial = (
        rounded.assign(
            rounded_partial=(
                rounded["exposure"].to_numpy(dtype=float)
                < rounded["loan_amnt"].to_numpy(dtype=float) - tolerance
            )
        )
        .groupby(list(PORTFOLIO_KEYS), observed=True, sort=True)["rounded_partial"]
        .sum()
        .rename("rounded_partial_positions")
    )
    audit = pd.concat(
        [original_total, rounded_total, changed, rounded_partial], axis=1
    ).reset_index()
    if bool(audit[["rounded_allocated", "rounded_partial_positions"]].isna().any(axis=None)):
        raise RuntimeError("Lot rounding removed an entire portfolio.")
    audit["cash_residual"] = committed_budget - audit["rounded_allocated"]
    audit["cash_share"] = audit["cash_residual"] / committed_budget
    audit["lot_size"] = float(lot_size)
    audit["committed_budget"] = float(committed_budget)
    if not np.allclose(
        audit["source_allocated"].to_numpy(dtype=float),
        committed_budget,
        atol=1.0e-4,
        rtol=0.0,
    ):
        raise RuntimeError("Source portfolios do not use the declared committed budget.")
    if bool((audit["cash_residual"] < -tolerance).any()):
        raise RuntimeError("Lot rounding increased invested capital.")

    lot_remainder = np.mod(rounded["exposure"].to_numpy(dtype=float), lot_size)
    if not bool(np.all(np.minimum(lot_remainder, lot_size - lot_remainder) <= tolerance)):
        raise RuntimeError("Rounded exposures are not exact lot multiples.")
    _validate_rounded_constraints(
        rounded,
        committed_budget=committed_budget,
        tolerance=tolerance,
    )
    return rounded.reset_index(drop=True), audit.reset_index(drop=True)


def rounded_solve_records(
    records: pd.DataFrame,
    rounded: pd.DataFrame,
    audit: pd.DataFrame,
    *,
    committed_budget: float,
) -> pd.DataFrame:
    """Update frozen solve records after the deterministic floor transform."""
    indexed = rounded.groupby(list(PORTFOLIO_KEYS), observed=True, sort=True).agg(
        n_positive_exposure=("id", "size"),
        total_allocated=("exposure", "sum"),
        expected_objective=("expected_payoff_contribution", "sum"),
    )
    weighted = (
        rounded.assign(
            weighted_pd_point_contribution=rounded["exposure"] * rounded["pd_point"],
            weighted_pd_effective_contribution=rounded["exposure"] * rounded["pd_effective"],
            weighted_upper_contribution=rounded["exposure"] * rounded["conformal_upper"],
        )
        .groupby(list(PORTFOLIO_KEYS), observed=True, sort=True)[
            [
                "weighted_pd_point_contribution",
                "weighted_pd_effective_contribution",
                "weighted_upper_contribution",
            ]
        ]
        .sum()
    )
    indexed["weighted_pd_point"] = weighted["weighted_pd_point_contribution"] / committed_budget
    indexed["weighted_pd_effective"] = (
        weighted["weighted_pd_effective_contribution"] / committed_budget
    )
    indexed["weighted_conformal_upper"] = weighted["weighted_upper_contribution"] / committed_budget
    indexed = indexed.reset_index()

    result = records.merge(
        indexed,
        on=list(PORTFOLIO_KEYS),
        how="left",
        validate="one_to_one",
        suffixes=("_source", ""),
    ).merge(
        audit[[*PORTFOLIO_KEYS, "cash_residual", "cash_share", "changed_positions"]],
        on=list(PORTFOLIO_KEYS),
        how="left",
        validate="one_to_one",
    )
    if bool(result[["total_allocated", "cash_residual"]].isna().any(axis=None)):
        raise RuntimeError("Rounded solve records do not cover every source portfolio.")
    result["budget_residual"] = result["cash_residual"]
    result["constraint_slack"] = result["risk_tolerance"] - result["weighted_pd_effective"]
    result["granularity_transform"] = "floor_to_lot_cash_residual"
    return result


def granularity_contrast_bounds(
    continuous: pd.DataFrame,
    rounded: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    committed_budget: float,
    periods: Sequence[str],
    lgd: float,
) -> pd.DataFrame:
    """Evaluate rounded-minus-continuous contrasts with cash in the denominator."""
    outcome_columns = ["id", "snapshot_default"]
    if bool(outcomes["id"].duplicated().any()):
        raise ValueError("Outcome IDs must be unique for granularity evaluation.")
    expected_periods = tuple(str(period) for period in periods)
    rows: list[dict[str, Any]] = []
    for raw_keys, source in continuous.groupby(list(TRACK_KEYS), observed=True, sort=True):
        keys = raw_keys if isinstance(raw_keys, tuple) else (raw_keys,)
        window_id, candidate_id = (str(value) for value in keys)
        transformed = rounded.loc[
            rounded["window_id"].eq(window_id) & rounded["candidate_id"].eq(candidate_id)
        ].copy()
        if set(source["period"].astype(str)) != set(expected_periods):
            raise RuntimeError(
                f"Continuous track {window_id}/{candidate_id} has an incomplete period grid."
            )
        if set(transformed["period"].astype(str)) != set(expected_periods):
            raise RuntimeError(
                f"Rounded track {window_id}/{candidate_id} has an incomplete period grid."
            )

        source = source.copy()
        source["policy_label"] = "continuous"
        transformed["policy_label"] = "rounded_lot"
        combined = pd.concat([source, transformed], ignore_index=True)
        facts = (
            combined[["id", "contractual_rate", "conformal_lower", "conformal_upper"]]
            .drop_duplicates()
            .merge(outcomes[outcome_columns], on="id", how="left", validate="one_to_one")
        )
        if len(facts) != combined["id"].nunique():
            raise RuntimeError("Granularity outcome join did not preserve the funded union.")
        committed = committed_budget * len(expected_periods)
        bounds = PolicyContrastIndex(
            combined,
            role="primary_oot",
            loan_facts=facts,
        ).sharp_bounds(
            policy_a="rounded_lot",
            policy_b="continuous",
            lgd=lgd,
            normalization_capital_a=committed,
            normalization_capital_b=committed,
        )
        rows.append(
            {
                "window_id": window_id,
                "candidate_id": candidate_id,
                "frontier_ruler": str(source["frontier_ruler"].iloc[0]),
                "frontier_coordinate": float(source["frontier_coordinate"].iloc[0]),
                "gamma": float(source["gamma"].iloc[0]),
                "periods": len(expected_periods),
                "cash_residual_total": committed - float(bounds["policy_a_capital"]),
                "cash_share": 1.0 - float(bounds["policy_a_capital"]) / committed,
                **bounds,
            }
        )
    return pd.DataFrame(rows).sort_values(list(TRACK_KEYS), kind="stable").reset_index(drop=True)


def _validate_rounded_constraints(
    rounded: pd.DataFrame,
    *,
    committed_budget: float,
    tolerance: float,
) -> None:
    grouped = rounded.groupby(list(PORTFOLIO_KEYS), observed=True, sort=False)
    risk = grouped.apply(
        lambda frame: float((frame["exposure"] * frame["pd_effective"]).sum()) / committed_budget,
        include_groups=False,
    )
    risk_cap = grouped["frontier_cap"].first()
    if bool((risk > risk_cap + tolerance).any()):
        raise RuntimeError("Lot rounding violated a risk constraint.")
    purpose = (
        rounded.groupby([*PORTFOLIO_KEYS, "purpose"], observed=True, sort=False)["exposure"].sum()
        / committed_budget
    )
    purpose_cap = rounded.groupby([*PORTFOLIO_KEYS, "purpose"], observed=True, sort=False)[
        "scenario_purpose_cap"
    ].first()
    if bool((purpose > purpose_cap + tolerance).any()):
        raise RuntimeError("Lot rounding violated a purpose constraint.")
