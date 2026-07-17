from __future__ import annotations

import pandas as pd
import pytest

from src.ijds_audit.allocation_granularity import (
    floor_allocations_to_lot,
    granularity_contrast_bounds,
)


def _allocations() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for period, first in (("2016-04", 62.0), ("2016-05", 57.0)):
        for identifier, exposure, amount, probability in (
            (f"{period}-a", first, 100.0, 0.10),
            (f"{period}-b", 100.0 - first, 100.0, 0.20),
        ):
            rows.append(
                {
                    "id": identifier,
                    "window_id": "w01",
                    "role": "primary_oot",
                    "period": period,
                    "policy_label": "candidate",
                    "candidate_id": "candidate",
                    "comparator_rule": "objective_matched",
                    "frontier_ruler": "objective_matched",
                    "frontier_coordinate": 0.25,
                    "frontier_cap": 0.20,
                    "gamma": 1.0,
                    "loan_amnt": amount,
                    "exposure": exposure,
                    "expected_payoff_rate": 0.05,
                    "expected_payoff_contribution": exposure * 0.05,
                    "pd_point": probability,
                    "pd_effective": probability,
                    "conformal_lower": 0.0,
                    "conformal_upper": 0.8,
                    "contractual_rate": 0.12,
                    "purpose": "debt_consolidation",
                    "scenario_purpose_cap": 1.0,
                }
            )
    return pd.DataFrame(rows)


def test_floor_allocations_retains_cash_and_preserves_constraints() -> None:
    rounded, audit = floor_allocations_to_lot(
        _allocations(),
        lot_size=25.0,
        committed_budget=100.0,
    )

    assert set(rounded["exposure"]) == {25.0, 50.0}
    assert audit["cash_residual"].tolist() == [25.0, 25.0]
    assert audit["changed_positions"].tolist() == [2, 2]
    assert rounded.groupby("period", observed=True)["weight"].sum().tolist() == [0.75, 0.75]


def test_granularity_bounds_use_committed_capital_including_cash() -> None:
    source = _allocations()
    rounded, _ = floor_allocations_to_lot(
        source,
        lot_size=25.0,
        committed_budget=100.0,
    )
    outcomes = pd.DataFrame(
        {
            "id": source["id"].astype("string"),
            "snapshot_default": pd.Series([0, 1, pd.NA, 0], dtype="Int8"),
        }
    )

    bounds = granularity_contrast_bounds(
        source,
        rounded,
        outcomes,
        committed_budget=100.0,
        periods=("2016-04", "2016-05"),
        lgd=0.45,
    ).iloc[0]

    assert bounds["policy_a_capital"] == pytest.approx(150.0)
    assert bounds["policy_a_normalization_capital"] == 200.0
    assert bounds["cash_residual_total"] == pytest.approx(50.0)
    assert (
        bounds["weighted_default_difference_lower"] <= (bounds["weighted_default_difference_upper"])
    )


def test_floor_allocations_rejects_nonpositive_lot() -> None:
    with pytest.raises(ValueError, match="Lot size"):
        floor_allocations_to_lot(
            _allocations(),
            lot_size=0.0,
            committed_budget=100.0,
        )
