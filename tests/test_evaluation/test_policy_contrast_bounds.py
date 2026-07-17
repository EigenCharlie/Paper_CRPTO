from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
import pytest

from src.evaluation.policy_contrast_bounds import (
    PolicyContrastIndex,
    sharp_policy_contrast_bounds,
)


def _policy_pair() -> pd.DataFrame:
    pair = pd.DataFrame(
        {
            "id": pd.Series(["shared", "a-only", "shared", "b-only"], dtype="string"),
            "role": ["primary_oot"] * 4,
            "policy_label": ["policy-a", "policy-a", "policy-b", "policy-b"],
            "exposure": [60.0, 40.0, 40.0, 60.0],
            "contractual_rate": [0.10, 0.08, 0.10, 0.12],
            "conformal_lower": [0.0, 0.0, 0.0, 0.1],
            "conformal_upper": [0.8, 0.9, 0.8, 1.0],
            "expected_payoff_contribution": [5.0, 2.0, 3.0, 4.0],
        }
    )
    pair["snapshot_default"] = pd.Series([pd.NA, 0, pd.NA, 1], dtype="Int8")
    return pair


def test_sharp_policy_contrast_preserves_matching_nullable_outcome_fact() -> None:
    bounds = sharp_policy_contrast_bounds(
        _policy_pair(),
        policy_a="policy-a",
        policy_b="policy-b",
        role="primary_oot",
        lgd=0.45,
    )

    assert bounds["funded_union_loans"] == 3
    assert bounds["unresolved_union_loans"] == 1
    assert np.isfinite(bounds["realized_payoff_difference_lower"])
    assert bounds["realized_payoff_difference_lower"] <= bounds["realized_payoff_difference_upper"]
    assert bounds["realized_payoff_identification_width"] == pytest.approx(
        bounds["realized_payoff_difference_upper"] - bounds["realized_payoff_difference_lower"]
    )
    assert bounds["weighted_default_identification_width"] == pytest.approx(
        bounds["weighted_default_difference_upper"] - bounds["weighted_default_difference_lower"]
    )
    assert bounds["weighted_miscoverage_identification_width"] == pytest.approx(
        bounds["weighted_miscoverage_difference_upper"]
        - bounds["weighted_miscoverage_difference_lower"]
    )


def test_identification_width_uses_only_unresolved_exposure_difference() -> None:
    bounds = sharp_policy_contrast_bounds(
        _policy_pair(),
        policy_a="policy-a",
        policy_b="policy-b",
        role="primary_oot",
        lgd=0.45,
    )

    # Only the shared loan is unresolved; its exposure difference is USD 20.
    assert bounds["realized_payoff_identification_width"] == pytest.approx(11.0)
    assert bounds["weighted_default_identification_width"] == pytest.approx(0.2)
    assert bounds["weighted_miscoverage_identification_width"] == pytest.approx(0.2)


def test_sharp_bounds_equal_exhaustive_binary_completions() -> None:
    loan_ids = ["resolved", "missing-a", "missing-b"]
    exposure_a = np.array([50.0, 30.0, 20.0])
    exposure_b = np.array([20.0, 50.0, 30.0])
    rates = np.array([0.08, 0.12, 0.16])
    conformal_lower = np.array([0.0, 0.2, 0.0])
    conformal_upper = np.array([0.8, 1.0, 0.7])
    outcomes = np.array([0.0, np.nan, np.nan])
    allocations = pd.concat(
        [
            pd.DataFrame(
                {
                    "id": loan_ids,
                    "role": "primary_oot",
                    "policy_label": policy,
                    "exposure": exposures,
                    "expected_payoff_contribution": exposures * 0.01,
                    "contractual_rate": rates,
                    "conformal_lower": conformal_lower,
                    "conformal_upper": conformal_upper,
                    "snapshot_default": pd.Series([0, pd.NA, pd.NA], dtype="Int8"),
                }
            )
            for policy, exposures in (("policy-a", exposure_a), ("policy-b", exposure_b))
        ],
        ignore_index=True,
    )
    bounds = sharp_policy_contrast_bounds(
        allocations,
        policy_a="policy-a",
        policy_b="policy-b",
        role="primary_oot",
        lgd=0.45,
    )

    delta_exposure = exposure_a - exposure_b
    delta_weight = exposure_a / exposure_a.sum() - exposure_b / exposure_b.sum()
    completed_metrics: dict[str, list[float]] = {
        "realized_payoff": [],
        "realized_payoff_rate": [],
        "weighted_default": [],
        "weighted_miscoverage": [],
    }
    for completion in product((0.0, 1.0), repeat=2):
        realized = outcomes.copy()
        realized[~np.isfinite(realized)] = completion
        payoff = (1.0 - realized) * rates - realized * 0.45
        completed_metrics["realized_payoff"].append(float((delta_exposure * payoff).sum()))
        completed_metrics["realized_payoff_rate"].append(float((delta_weight * payoff).sum()))
        completed_metrics["weighted_default"].append(float((delta_weight * realized).sum()))
        miscovered = np.where(realized == 0.0, conformal_lower > 0.0, conformal_upper < 1.0)
        completed_metrics["weighted_miscoverage"].append(float((delta_weight * miscovered).sum()))

    for metric, values in completed_metrics.items():
        assert bounds[f"{metric}_difference_lower"] == pytest.approx(min(values))
        assert bounds[f"{metric}_difference_upper"] == pytest.approx(max(values))


@pytest.mark.parametrize(
    ("column", "conflicting_value"),
    [
        ("contractual_rate", 0.11),
        ("conformal_lower", 0.1),
        ("conformal_upper", 0.9),
        ("snapshot_default", 0),
    ],
)
def test_sharp_policy_contrast_rejects_conflicting_policy_facts(
    column: str,
    conflicting_value: float,
) -> None:
    pair = _policy_pair()
    pair.loc[
        pair["id"].eq("shared") & pair["policy_label"].eq("policy-b"),
        column,
    ] = conflicting_value

    with pytest.raises(ValueError, match="Conflicting policy facts"):
        sharp_policy_contrast_bounds(
            pair,
            policy_a="policy-a",
            policy_b="policy-b",
            role="primary_oot",
            lgd=0.45,
        )


@pytest.mark.parametrize("reverse_rows", [False, True])
def test_indexed_bounds_equal_slow_oracle_on_adversarial_union(reverse_rows: bool) -> None:
    allocations = _policy_pair()
    extra = allocations.iloc[[0, 1]].copy()
    extra["policy_label"] = "policy-c"
    extra["exposure"] = [0.0, 100.0]
    extra["expected_payoff_contribution"] = [-1.0, 9.0]
    allocations = pd.concat([allocations, extra], ignore_index=True)
    if reverse_rows:
        allocations = allocations.iloc[::-1].reset_index(drop=True)

    oracle = sharp_policy_contrast_bounds(
        allocations,
        policy_a="policy-a",
        policy_b="policy-b",
        role="primary_oot",
        lgd=0.45,
    )
    optimized = PolicyContrastIndex(allocations, role="primary_oot").sharp_bounds(
        policy_a="policy-a",
        policy_b="policy-b",
        lgd=0.45,
    )

    assert optimized.keys() == oracle.keys()
    for key, expected in oracle.items():
        if isinstance(expected, float):
            assert optimized[key] == pytest.approx(expected, rel=0.0, abs=1e-15)
        else:
            assert optimized[key] == expected


def test_indexed_bounds_reject_duplicate_allocation_and_external_fact_ids() -> None:
    allocations = _policy_pair()
    facts = allocations[
        [
            "id",
            "contractual_rate",
            "conformal_lower",
            "conformal_upper",
            "snapshot_default",
        ]
    ].drop_duplicates()

    duplicate_allocation = pd.concat([allocations, allocations.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="appears more than once"):
        PolicyContrastIndex(duplicate_allocation, role="primary_oot")

    duplicate_facts = pd.concat([facts, facts.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate IDs"):
        PolicyContrastIndex(
            allocations,
            role="primary_oot",
            loan_facts=duplicate_facts,
        )


def test_indexed_bounds_reject_conflicting_or_missing_external_facts() -> None:
    allocations = _policy_pair()
    facts = allocations[
        [
            "id",
            "contractual_rate",
            "conformal_lower",
            "conformal_upper",
            "snapshot_default",
        ]
    ].drop_duplicates()
    conflict = facts.iloc[[0]].copy()
    conflict["contractual_rate"] = 0.99
    with pytest.raises(ValueError, match="Conflicting policy facts"):
        PolicyContrastIndex(
            allocations,
            role="primary_oot",
            loan_facts=pd.concat([facts, conflict], ignore_index=True),
        )

    with pytest.raises(ValueError, match="ID mismatch: missing=1"):
        PolicyContrastIndex(
            allocations,
            role="primary_oot",
            loan_facts=facts.loc[~facts["id"].eq("b-only")],
        )


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("exposure", -1.0, "negative exposure"),
        ("expected_payoff_contribution", float("inf"), "non-finite expected"),
        ("contractual_rate", float("inf"), "contractual rate values must be finite"),
        ("conformal_lower", -0.1, "0 <= lower <= upper <= 1"),
        ("conformal_upper", 1.1, "0 <= lower <= upper <= 1"),
    ],
)
def test_indexed_bounds_reject_invalid_numeric_domains(
    column: str,
    value: float,
    message: str,
) -> None:
    allocations = _policy_pair()
    allocations.loc[allocations["id"].eq("a-only"), column] = value

    if column in {"exposure", "expected_payoff_contribution"}:
        with pytest.raises(ValueError, match=message):
            PolicyContrastIndex(allocations, role="primary_oot")
        return

    index = PolicyContrastIndex(allocations, role="primary_oot")
    with pytest.raises(ValueError, match=message):
        index.sharp_bounds(policy_a="policy-a", policy_b="policy-b", lgd=0.45)


def test_indexed_bounds_reject_invalid_lgd() -> None:
    index = PolicyContrastIndex(_policy_pair(), role="primary_oot")

    with pytest.raises(ValueError, match="LGD"):
        index.sharp_bounds(policy_a="policy-a", policy_b="policy-b", lgd=float("nan"))


def test_indexed_bounds_can_normalize_both_policies_to_committed_capital() -> None:
    index = PolicyContrastIndex(_policy_pair(), role="primary_oot")

    bounds = index.sharp_bounds(
        policy_a="policy-a",
        policy_b="policy-b",
        lgd=0.45,
        normalization_capital_a=125.0,
        normalization_capital_b=125.0,
    )

    assert bounds["policy_a_capital"] == 100.0
    assert bounds["policy_a_normalization_capital"] == 125.0
    assert bounds["policy_b_normalization_capital"] == 125.0
    assert bounds["weighted_default_identification_width"] == pytest.approx(0.16)


def test_indexed_bounds_reject_normalizer_below_invested_capital() -> None:
    index = PolicyContrastIndex(_policy_pair(), role="primary_oot")

    with pytest.raises(ValueError, match="below invested"):
        index.sharp_bounds(
            policy_a="policy-a",
            policy_b="policy-b",
            lgd=0.45,
            normalization_capital_a=99.0,
        )


def test_indexed_bounds_accepts_scale_small_solver_budget_residual() -> None:
    pair = _policy_pair()
    pair.loc[pair["policy_label"].eq("policy-a"), "exposure"] *= 150_000.00000001
    pair.loc[pair["policy_label"].eq("policy-b"), "exposure"] *= 150_000.0
    pair["expected_payoff_contribution"] = pair["exposure"] * 0.05
    index = PolicyContrastIndex(pair, role="primary_oot")

    bounds = index.sharp_bounds(
        policy_a="policy-a",
        policy_b="policy-b",
        lgd=0.45,
        normalization_capital_a=15_000_000.0,
        normalization_capital_b=15_000_000.0,
    )

    assert bounds["policy_a_normalization_capital"] == 15_000_000.0
