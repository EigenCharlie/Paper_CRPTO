from __future__ import annotations

import pandas as pd
import pytest

from scripts.experiments.run_ijds_endpoint_availability_sensitivity import (
    _primary_loan_facts,
    _window_loan_facts,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.ijds_audit.evaluation import indexed_portfolio_contrasts
from src.models.binary_conformal_guardrail import BinaryOutcomeConformalRecipe


def _adversarial_contrast_grid() -> tuple[pd.DataFrame, pd.DataFrame]:
    facts = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d", "e", "f"],
            "contractual_rate": [0.05, 0.08, 0.11, 0.13, 0.17, 0.19],
            "conformal_lower": [0.0, 0.1, 0.0, 0.2, 0.0, 1.0],
            "conformal_upper": [0.8, 1.0, 0.9, 0.7, 1.0, 1.0],
            "snapshot_default": pd.Series([0, pd.NA, 1, 0, pd.NA, 1], dtype="Int8"),
        }
    )
    fact_lookup = facts.set_index("id")
    specifications = {
        "guardrail_p1": ("guardrail", 0.12, {"a": 40.0, "b": 60.0, "f": 0.0}),
        "c0_same_numeric_cap_p1": (
            "c0_same_numeric_cap",
            0.12,
            {"a": 25.0, "c": 75.0},
        ),
        "c1_development_mean_p1": (
            "c1_development_mean",
            0.14,
            {"b": 100.0},
        ),
        "c2_contemporaneous_p1": (
            "c2_contemporaneous",
            0.16,
            {"d": 35.0, "e": 65.0},
        ),
        "guardrail_p2": ("guardrail", 0.18, {"c": 30.0, "d": 70.0}),
        "c0_same_numeric_cap_p2": (
            "c0_same_numeric_cap",
            0.18,
            {"c": 100.0},
        ),
        "c1_development_mean_p2": (
            "c1_development_mean",
            0.20,
            {"a": 10.0, "d": 90.0},
        ),
        "c2_contemporaneous_p2": (
            "c2_contemporaneous",
            0.22,
            {"e": 45.0, "f": 55.0},
        ),
        "point_cap_frontier_0.1": (
            "point_cap_frontier",
            0.10,
            {"a": 20.0, "e": 80.0},
        ),
        "point_cap_frontier_0.2": (
            "point_cap_frontier",
            0.20,
            {"b": 50.0, "c": 50.0},
        ),
        "point_cap_frontier_0.3": (
            "point_cap_frontier",
            0.30,
            {"d": 100.0},
        ),
    }
    rows: list[dict[str, object]] = []
    for policy_label, (rule, cap, exposures) in specifications.items():
        for loan_id, exposure in exposures.items():
            loan = fact_lookup.loc[loan_id]
            rows.append(
                {
                    "id": loan_id,
                    "role": "primary_oot",
                    "window_id": "w-adversarial",
                    "policy_label": policy_label,
                    "exposure": exposure,
                    "expected_payoff_contribution": exposure
                    * (float(loan["contractual_rate"]) - 0.02),
                    "comparator_rule": rule,
                    "frontier_cap": cap,
                    "contractual_rate": loan["contractual_rate"],
                    "conformal_lower": loan["conformal_lower"],
                    "conformal_upper": loan["conformal_upper"],
                    "snapshot_default": loan["snapshot_default"],
                }
            )
    allocations = pd.DataFrame(rows).sample(frac=1.0, random_state=712).reset_index(drop=True)
    return allocations, facts


def _slow_contrast_grid(
    allocations: pd.DataFrame,
    *,
    policy_ids: tuple[str, ...],
    lgd: float,
) -> pd.DataFrame:
    labels = {
        str(label): frame
        for label, frame in allocations.groupby("policy_label", observed=True, sort=False)
    }
    frontier = (
        allocations.loc[
            allocations["comparator_rule"].eq("point_cap_frontier"),
            ["policy_label", "frontier_cap"],
        ]
        .drop_duplicates()
        .sort_values("frontier_cap")
    )
    rows: list[dict[str, object]] = []
    for policy_id in policy_ids:
        guardrail = f"guardrail_{policy_id}"
        comparators = (
            ("c0_same_numeric_cap", f"c0_same_numeric_cap_{policy_id}"),
            ("c1_development_mean", f"c1_development_mean_{policy_id}"),
            ("c2_contemporaneous", f"c2_contemporaneous_{policy_id}"),
        )
        for rule, comparator in comparators:
            pair = pd.concat([labels[guardrail], labels[comparator]], ignore_index=True)
            rows.append(
                {
                    "window_id": "w-adversarial",
                    "paired_policy_id": policy_id,
                    "comparator_rule": rule,
                    "frontier_cap": float(labels[comparator]["frontier_cap"].iloc[0]),
                    **sharp_policy_contrast_bounds(
                        pair,
                        policy_a=guardrail,
                        policy_b=comparator,
                        role="primary_oot",
                        lgd=lgd,
                    ),
                }
            )
        for item in frontier.itertuples(index=False):
            comparator = str(item.policy_label)
            pair = pd.concat([labels[guardrail], labels[comparator]], ignore_index=True)
            rows.append(
                {
                    "window_id": "w-adversarial",
                    "paired_policy_id": policy_id,
                    "comparator_rule": "point_cap_frontier",
                    "frontier_cap": float(item.frontier_cap),
                    **sharp_policy_contrast_bounds(
                        pair,
                        policy_a=guardrail,
                        policy_b=comparator,
                        role="primary_oot",
                        lgd=lgd,
                    ),
                }
            )
    return pd.DataFrame(rows)


def test_indexed_grid_matches_slow_public_oracle() -> None:
    allocations, facts = _adversarial_contrast_grid()
    policy_ids = ("p1", "p2")

    oracle = _slow_contrast_grid(
        allocations,
        policy_ids=policy_ids,
        lgd=0.45,
    )
    optimized = indexed_portfolio_contrasts(
        allocations,
        loan_facts=facts,
        window_id="w-adversarial",
        policy_ids=policy_ids,
        lgd=0.45,
    )

    pd.testing.assert_frame_equal(
        optimized,
        oracle,
        check_exact=False,
        rtol=0.0,
        atol=1e-15,
    )


def test_indexed_grid_rejects_conflicting_named_comparator_caps() -> None:
    allocations, facts = _adversarial_contrast_grid()
    duplicate = (
        allocations.loc[allocations["policy_label"].eq("c0_same_numeric_cap_p1")].iloc[[0]].copy()
    )
    duplicate["id"] = "f"
    duplicate["frontier_cap"] = 0.99
    duplicate["exposure"] = 0.0
    duplicate["expected_payoff_contribution"] = 0.0
    allocations = pd.concat([allocations, duplicate], ignore_index=True)

    with pytest.raises(RuntimeError, match="conflicting cap values"):
        indexed_portfolio_contrasts(
            allocations,
            loan_facts=facts,
            window_id="w-adversarial",
            policy_ids=("p1", "p2"),
            lgd=0.45,
        )


def _endpoint_alignment_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    allocations = pd.DataFrame(
        {
            "id": ["a", "a", "b"],
            "role": ["primary_oot"] * 3,
            "period": ["2016-01", "2016-01", "2016-02"],
            "contractual_rate": [0.10, 0.10, 0.15],
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": ["a", "b", "unused"],
            "role": ["primary_oot", "primary_oot", "policy_development"],
            "period": ["2016-01", "2016-02", "2012-01"],
            "snapshot_default": pd.Series([0, pd.NA, 1], dtype="Int8"),
            "snapshot_resolution": ["fully_paid", "right_censored", "charged_off"],
        }
    )
    return allocations, outcomes


def test_primary_fact_join_is_exact_and_preserves_nullable_outcomes() -> None:
    allocations, outcomes = _endpoint_alignment_frames()

    facts = _primary_loan_facts(allocations, outcomes)

    assert facts["id"].tolist() == ["a", "b"]
    assert facts["snapshot_default"].isna().tolist() == [False, True]


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "role", "period"])
def test_primary_fact_join_rejects_id_or_metadata_drift(mutation: str) -> None:
    allocations, outcomes = _endpoint_alignment_frames()
    if mutation == "duplicate":
        outcomes = pd.concat([outcomes, outcomes.iloc[[0]]], ignore_index=True)
        match = "one nonmissing row per ID"
    elif mutation == "missing":
        outcomes = outcomes.loc[~outcomes["id"].eq("b")]
        match = "missing=1"
    elif mutation == "role":
        outcomes.loc[outcomes["id"].eq("a"), "role"] = "policy_development"
        match = "role or period"
    else:
        outcomes.loc[outcomes["id"].eq("a"), "period"] = "2016-03"
        match = "role or period"

    with pytest.raises(RuntimeError, match=match):
        _primary_loan_facts(allocations, outcomes)


def test_window_facts_require_complete_unique_score_alignment() -> None:
    allocations, outcomes = _endpoint_alignment_frames()
    base = _primary_loan_facts(allocations, outcomes)
    scores = pd.DataFrame(
        {
            "id": ["a", "b", "unused"],
            "design_split": ["primary_oot", "primary_oot", "policy_development"],
            "pd_catboost_platt": [0.1, 0.8, 0.5],
        }
    )
    recipe = BinaryOutcomeConformalRecipe(
        alpha=0.1,
        requested_groups=1,
        bin_edges=(0.0, 1.0),
        residual_quantiles=(0.2,),
        group_counts=(10,),
        finite_sample_ranks=(9,),
        raw_finite_sample_ranks=(9,),
    )

    facts = _window_loan_facts(base, scores, recipe)
    assert facts["conformal_lower"].tolist() == pytest.approx([0.0, 0.6])
    assert facts["conformal_upper"].tolist() == pytest.approx([0.3, 1.0])

    with pytest.raises(RuntimeError, match="missing=1"):
        _window_loan_facts(base, scores.loc[~scores["id"].eq("b")], recipe)
    with pytest.raises(RuntimeError, match="one nonmissing row per ID"):
        _window_loan_facts(
            base,
            pd.concat([scores, scores.iloc[[0]]], ignore_index=True),
            recipe,
        )
