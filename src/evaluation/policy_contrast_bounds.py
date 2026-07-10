"""Sharp pairwise policy contrasts with nullable binary outcomes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _sharp_binary_sum_bounds(
    value_if_zero: np.ndarray,
    value_if_one: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    observed = np.isfinite(outcomes)
    if bool(np.any(observed & ~np.isin(outcomes, [0.0, 1.0]))):
        raise ValueError("Observed outcomes must be binary.")
    exact = np.where(outcomes == 1.0, value_if_one, value_if_zero)
    lower = np.where(observed, exact, np.minimum(value_if_zero, value_if_one))
    upper = np.where(observed, exact, np.maximum(value_if_zero, value_if_one))
    return float(lower.sum()), float(upper.sum())


def _union_policy_allocations(
    allocations: pd.DataFrame,
    *,
    policy_a: str,
    policy_b: str,
    role: str,
) -> pd.DataFrame:
    subset = allocations.loc[
        allocations["role"].eq(role) & allocations["policy_label"].isin([policy_a, policy_b])
    ].copy()
    if subset.empty:
        raise ValueError(f"No allocations found for role {role!r}.")
    counts = subset.groupby(["id", "policy_label"], observed=True).size()
    if bool((counts > 1).any()):
        raise ValueError("A loan appears more than once within a policy contrast.")
    present = set(subset["policy_label"].astype(str))
    if present != {policy_a, policy_b}:
        raise ValueError(
            f"Policy contrast is missing labels: {sorted({policy_a, policy_b} - present)}"
        )

    attributes = [
        "id",
        "contractual_rate",
        "conformal_lower",
        "conformal_upper",
        "snapshot_default",
    ]
    loans = subset[attributes].drop_duplicates(subset="id", keep="first").set_index("id")
    exposure = subset.pivot(index="id", columns="policy_label", values="exposure").fillna(0.0)
    union = loans.join(exposure, how="outer").reset_index()
    union[policy_a] = pd.to_numeric(union[policy_a], errors="coerce").fillna(0.0)
    union[policy_b] = pd.to_numeric(union[policy_b], errors="coerce").fillna(0.0)
    return union


def sharp_policy_contrast_bounds(
    allocations: pd.DataFrame,
    *,
    policy_a: str,
    policy_b: str,
    role: str,
    lgd: float,
) -> dict[str, Any]:
    """Return sharp ``policy_a - policy_b`` bounds on their funded union."""
    union = _union_policy_allocations(
        allocations,
        policy_a=policy_a,
        policy_b=policy_b,
        role=role,
    )
    exposure_a = union[policy_a].to_numpy(dtype=float)
    exposure_b = union[policy_b].to_numpy(dtype=float)
    total_a = float(exposure_a.sum())
    total_b = float(exposure_b.sum())
    if total_a <= 0.0 or total_b <= 0.0:
        raise ValueError("Both policies must allocate positive capital.")
    outcomes = pd.to_numeric(union["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    rates = union["contractual_rate"].to_numpy(dtype=float)
    lower = union["conformal_lower"].to_numpy(dtype=float)
    upper = union["conformal_upper"].to_numpy(dtype=float)
    delta_exposure = exposure_a - exposure_b
    delta_weight = exposure_a / total_a - exposure_b / total_b

    payoff_lower, payoff_upper = _sharp_binary_sum_bounds(
        delta_exposure * rates,
        delta_exposure * -float(lgd),
        outcomes,
    )
    default_lower, default_upper = _sharp_binary_sum_bounds(
        np.zeros(len(union), dtype=float),
        delta_weight,
        outcomes,
    )
    miss_if_zero = (lower > 0.0).astype(float)
    miss_if_one = (upper < 1.0).astype(float)
    miscoverage_lower, miscoverage_upper = _sharp_binary_sum_bounds(
        delta_weight * miss_if_zero,
        delta_weight * miss_if_one,
        outcomes,
    )
    expected = (
        allocations.loc[
            allocations["role"].eq(role) & allocations["policy_label"].eq(policy_a),
            "expected_payoff_contribution",
        ].sum()
        - allocations.loc[
            allocations["role"].eq(role) & allocations["policy_label"].eq(policy_b),
            "expected_payoff_contribution",
        ].sum()
    )
    return {
        "contrast": f"{policy_a}_minus_{policy_b}",
        "role": role,
        "policy_a": policy_a,
        "policy_b": policy_b,
        "policy_a_capital": total_a,
        "policy_b_capital": total_b,
        "funded_union_loans": int(len(union)),
        "unresolved_union_loans": int((~np.isfinite(outcomes)).sum()),
        "expected_objective_difference": float(expected),
        "realized_payoff_difference_lower": payoff_lower,
        "realized_payoff_difference_upper": payoff_upper,
        "realized_payoff_rate_difference_lower": payoff_lower / total_a,
        "realized_payoff_rate_difference_upper": payoff_upper / total_a,
        "weighted_default_difference_lower": default_lower,
        "weighted_default_difference_upper": default_upper,
        "weighted_miscoverage_difference_lower": miscoverage_lower,
        "weighted_miscoverage_difference_upper": miscoverage_upper,
        "payoff_direction_sign_robust": bool(payoff_lower > 0.0 or payoff_upper < 0.0),
        "default_direction_sign_robust": bool(default_lower > 0.0 or default_upper < 0.0),
        "miscoverage_direction_sign_robust": bool(
            miscoverage_lower > 0.0 or miscoverage_upper < 0.0
        ),
        "causal_interpretation": False,
    }
