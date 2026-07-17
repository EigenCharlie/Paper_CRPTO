"""Declared scenario grid and diagnostics for IJDS portfolio structure."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import Any

import numpy as np
import pandas as pd


def declared_scenarios(config: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the complete budget-purpose-LGD Cartesian product."""
    grid = config["structural_grid"]
    budgets = tuple(float(value) for value in grid["budgets"])
    purpose_caps = tuple(float(value) for value in grid["purpose_caps"])
    lgds = tuple(float(value) for value in grid["lgds"])
    if budgets != (500_000.0, 1_000_000.0, 2_000_000.0):
        raise ValueError("Budget grid must remain 0.5/1/2 million dollars.")
    if purpose_caps != (0.20, 0.25, 0.30, 1.00):
        raise ValueError("Purpose-cap grid must remain .20/.25/.30/1.00.")
    if lgds != (0.25, 0.45, 0.65):
        raise ValueError("LGD grid must remain .25/.45/.65.")
    scenarios: list[dict[str, Any]] = []
    for budget, purpose_cap, lgd in product(budgets, purpose_caps, lgds):
        scenarios.append(
            {
                "scenario_id": (
                    f"b{round(budget / 1000):04d}k_"
                    f"p{round(purpose_cap * 100):03d}_l{round(lgd * 100):03d}"
                ),
                "budget": budget,
                "purpose_cap": purpose_cap,
                "lgd": lgd,
                "is_baseline": bool(budget == 1_000_000.0 and purpose_cap == 0.25 and lgd == 0.45),
            }
        )
    if len(scenarios) != 36 or sum(item["is_baseline"] for item in scenarios) != 1:
        raise RuntimeError("Structural scenario grid is incomplete or has no unique baseline.")
    return tuple(scenarios)


def allocation_activity(
    records: pd.DataFrame,
    allocations: pd.DataFrame,
    *,
    scenario: Mapping[str, Any],
    allocation_tolerance: float,
) -> dict[str, Any]:
    """Summarize binding constraints and diversification for one scenario."""
    keys = ["window_id", "role", "period", "policy_label"]
    if bool(records.duplicated(keys).any()):
        raise RuntimeError("Structural solve records are not unique by portfolio.")
    grouped = allocations.groupby(keys, observed=True, sort=False)
    total = grouped["exposure"].sum().rename("total_exposure")
    purpose = (
        allocations.groupby([*keys, "purpose"], observed=True, sort=False)["exposure"]
        .sum()
        .groupby(level=keys)
        .max()
        .rename("maximum_purpose_exposure")
    )
    activity = pd.concat([total, purpose], axis=1)
    activity["maximum_purpose_share"] = (
        activity["maximum_purpose_exposure"] / activity["total_exposure"]
    )
    cap = float(scenario["purpose_cap"])
    purpose_binding = np.isclose(
        activity["maximum_purpose_share"].to_numpy(dtype=float),
        cap,
        atol=1e-8,
        rtol=0.0,
    )
    fractions = allocations["allocation_fraction"].to_numpy(dtype=float)
    partial = (fractions > float(allocation_tolerance)) & (
        fractions < 1.0 - float(allocation_tolerance)
    )
    normalized_slack = records["constraint_slack"].abs().to_numpy(dtype=float)
    ruler = records["frontier_ruler"].astype("string")
    binding_tolerance = np.where(ruler.eq("normalized_score"), 1e-8, 1e-5)
    weights = allocations["weight"].to_numpy(dtype=float)
    hhi = (
        allocations.assign(_weight_squared=np.square(weights))
        .groupby(keys, observed=True, sort=False)["_weight_squared"]
        .sum()
        .to_numpy(dtype=float)
    )
    return {
        **dict(scenario),
        "portfolios": int(len(records)),
        "funded_rows": int(len(allocations)),
        "purpose_cap_binding_portfolios": int(purpose_binding.sum()),
        "purpose_cap_binding_share": float(purpose_binding.mean()),
        "frontier_constraint_binding_portfolios": int(
            (normalized_slack <= binding_tolerance).sum()
        ),
        "frontier_constraint_binding_share": float((normalized_slack <= binding_tolerance).mean()),
        "partial_funded_rows": int(partial.sum()),
        "partial_rows_per_portfolio_mean": float(partial.sum() / len(records)),
        "funded_loans_per_portfolio_min": int(records["n_positive_exposure"].min()),
        "funded_loans_per_portfolio_mean": float(records["n_positive_exposure"].mean()),
        "funded_loans_per_portfolio_max": int(records["n_positive_exposure"].max()),
        "hhi_min": float(hhi.min()),
        "hhi_mean": float(hhi.mean()),
        "hhi_max": float(hhi.max()),
        "maximum_loan_weight": float(weights.max()),
        "maximum_purpose_share": float(activity["maximum_purpose_share"].max()),
    }


def scenario_result_summary(
    contrasts: pd.DataFrame,
    directions: pd.DataFrame,
    *,
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one row containing every metric hull and direction count."""
    row: dict[str, Any] = {**dict(scenario)}
    metrics = {
        "payoff": ("realized_payoff_difference_lower", "realized_payoff_difference_upper"),
        "default": ("weighted_default_difference_lower", "weighted_default_difference_upper"),
        "miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
        ),
    }
    for label, (lower, upper) in metrics.items():
        row[f"{label}_lower_min"] = float(contrasts[lower].min())
        row[f"{label}_upper_max"] = float(contrasts[upper].max())
    for metric, frame in directions.groupby("metric", observed=True, sort=True):
        counts = frame["direction"].value_counts().to_dict()
        for direction in ("gamma_1_lower", "gamma_1_higher", "crosses_zero", "exact_zero"):
            row[f"{metric}_{direction}_cells"] = int(counts.get(direction, 0))
    return row
