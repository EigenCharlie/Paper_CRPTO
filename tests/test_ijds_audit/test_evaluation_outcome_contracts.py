from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from src.ijds_audit.evaluation import evaluate_frozen_portfolios, temporal_coverage_audit


def _portfolio_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    records = pd.DataFrame(
        {
            "window_id": ["w01"],
            "role": ["primary_oot"],
            "period": ["2016-04"],
            "policy_label": ["policy"],
            "comparator_rule": ["guardrail"],
            "n_candidates": [2],
            "robust_guardrail": [False],
            "total_allocated": [100.0],
        }
    )
    allocations = pd.DataFrame(
        {
            "id": pd.Series(["funded-null"], dtype="string"),
            "window_id": ["w01"],
            "role": ["primary_oot"],
            "period": ["2016-04"],
            "policy_label": ["policy"],
            "comparator_rule": ["guardrail"],
            "contractual_rate": [0.10],
            "conformal_lower": [0.0],
            "conformal_upper": [0.8],
            "exposure": [100.0],
            "weight": [1.0],
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": pd.Series(["funded-null", "unfunded"], dtype="string"),
            "snapshot_default": pd.Series([pd.NA, 0], dtype="Int8"),
            "snapshot_resolution": pd.Series(["right_censored", "fully_paid"], dtype="string"),
            "role": pd.Series(["primary_oot", "primary_oot"], dtype="string"),
            "period": pd.Series(["2016-04", "2016-04"], dtype="string"),
        }
    )
    config: dict[str, Any] = {
        "payoff": {"lgd": 0.45},
        "policy": {"budget": 100.0},
    }
    return records, allocations, outcomes, config


def _coverage_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.DataFrame(
        {
            "id": pd.Series(["a", "b"], dtype="string"),
            "issue_d": pd.to_datetime(["2016-04-01", "2016-04-15"]),
            "design_split": pd.Series(["primary_oot", "primary_oot"], dtype="string"),
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": pd.Series(["a", "b"], dtype="string"),
            "snapshot_default": pd.Series([0, pd.NA], dtype="Int8"),
            "role": pd.Series(["primary_oot", "primary_oot"], dtype="string"),
            "period": pd.Series(["2016-04", "2016-04"], dtype="string"),
        }
    )
    return scores, outcomes


def test_evaluate_frozen_portfolios_preserves_nullable_outcome_fact() -> None:
    records, allocations, outcomes, config = _portfolio_inputs()

    evaluated, joined = evaluate_frozen_portfolios(
        records,
        allocations,
        outcomes,
        config=config,
    )

    assert pd.isna(joined.loc[0, "snapshot_default"])
    assert evaluated.loc[0, "n_unresolved_candidates"] == 1
    assert evaluated.loc[0, "n_unresolved_positive_exposure"] == 1


@pytest.mark.parametrize("invalid_count", [1.5, float("inf"), -1])
def test_evaluate_frozen_portfolios_rejects_invalid_declared_candidate_count(
    invalid_count: float,
) -> None:
    records, allocations, outcomes, config = _portfolio_inputs()
    records["n_candidates"] = records["n_candidates"].astype(float)
    records.loc[0, "n_candidates"] = invalid_count

    with pytest.raises(RuntimeError, match="invalid candidate census"):
        evaluate_frozen_portfolios(records, allocations, outcomes, config=config)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "missing=1, extra=0"),
        ("extra", "missing=0, extra=1"),
        ("duplicate", "duplicate IDs"),
    ],
)
def test_evaluate_frozen_portfolios_rejects_outcome_census_mutations(
    mutation: str,
    message: str,
) -> None:
    records, allocations, outcomes, config = _portfolio_inputs()
    if mutation == "missing":
        outcomes = outcomes.loc[~outcomes["id"].eq("unfunded")].copy()
    elif mutation == "extra":
        extra = outcomes.iloc[[1]].assign(id="extra")
        outcomes = pd.concat([outcomes, extra], ignore_index=True)
    else:
        outcomes = pd.concat([outcomes, outcomes.iloc[[1]]], ignore_index=True)

    with pytest.raises(RuntimeError, match=message):
        evaluate_frozen_portfolios(records, allocations, outcomes, config=config)


@pytest.mark.parametrize(
    ("column", "value"),
    [("role", "policy_development"), ("period", "2016-05")],
)
def test_evaluate_frozen_portfolios_rejects_outcome_metadata_mismatch(
    column: str,
    value: str,
) -> None:
    records, allocations, outcomes, config = _portfolio_inputs()
    outcomes.loc[outcomes["id"].eq("funded-null"), column] = value

    with pytest.raises(RuntimeError, match=f"Outcome {column} disagrees"):
        evaluate_frozen_portfolios(records, allocations, outcomes, config=config)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "missing=1, extra=0"),
        ("extra", "missing=0, extra=1"),
        ("duplicate", "duplicate IDs"),
    ],
)
def test_temporal_coverage_rejects_outcome_census_mutations(
    mutation: str,
    message: str,
) -> None:
    scores, outcomes = _coverage_inputs()
    if mutation == "missing":
        outcomes = outcomes.loc[~outcomes["id"].eq("b")].copy()
    elif mutation == "extra":
        extra = outcomes.iloc[[0]].assign(id="extra")
        outcomes = pd.concat([outcomes, extra], ignore_index=True)
    else:
        outcomes = pd.concat([outcomes, outcomes.iloc[[0]]], ignore_index=True)

    with pytest.raises(RuntimeError, match=message):
        temporal_coverage_audit(
            scores,
            outcomes,
            {},
            pd.DataFrame(),
            roles=("primary_oot",),
        )


@pytest.mark.parametrize(
    ("column", "value"),
    [("role", "policy_development"), ("period", "2016-05")],
)
def test_temporal_coverage_rejects_outcome_metadata_mismatch(
    column: str,
    value: str,
) -> None:
    scores, outcomes = _coverage_inputs()
    outcomes.loc[outcomes["id"].eq("a"), column] = value

    with pytest.raises(RuntimeError, match=f"Outcome {column} disagrees"):
        temporal_coverage_audit(
            scores,
            outcomes,
            {},
            pd.DataFrame(),
            roles=("primary_oot",),
        )
