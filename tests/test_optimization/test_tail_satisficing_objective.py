from __future__ import annotations

import pytest

from src.optimization.tail_satisficing_objective import (
    SatisficingThreshold,
    entropic_oce,
    evaluate_satisficing_margins,
    funded_loss_rate,
    score_tail_satisficing_objective,
    weighted_cvar,
    weighted_mean,
)


def test_weighted_cvar_uses_upper_loss_tail() -> None:
    losses = [0.01, 0.02, 0.50]
    weights = [0.45, 0.45, 0.10]

    assert weighted_cvar(losses, weights, tail=0.90) == pytest.approx(0.50)


def test_entropic_oce_is_at_least_mean_for_positive_theta() -> None:
    losses = [-0.08, 0.02, 0.25]
    weights = [0.4, 0.4, 0.2]

    assert entropic_oce(losses, weights, theta=5.0) >= weighted_mean(losses, weights)


def test_funded_loss_rate_reprices_defaults_and_performing_loans() -> None:
    losses = funded_loss_rate([1, 0, 0], [0.10, 0.12, 0.08], lgd=0.45)

    assert losses.tolist() == pytest.approx([0.45, -0.12, -0.08])


def test_satisficing_margins_support_min_max_and_equals() -> None:
    margins = evaluate_satisficing_margins(
        {
            "expected_return": 170_000.0,
            "weighted_miscoverage": 0.036,
            "exact_pass": True,
        },
        (
            SatisficingThreshold("expected_return", "min", 150_000.0),
            SatisficingThreshold("weighted_miscoverage", "max", 0.04),
            SatisficingThreshold("exact_pass", "equals", True),
        ),
    )

    assert [margin.passed for margin in margins] == [True, True, True]
    assert min(margin.margin for margin in margins) >= -1e-12


def test_tail_satisficing_score_penalizes_risk_and_shortfall() -> None:
    thresholds = (
        SatisficingThreshold("expected_return", "min", 100.0),
        SatisficingThreshold("cvar_loss_rate", "max", 0.20),
    )

    safer = score_tail_satisficing_objective(
        expected_return=120.0,
        loss_rates=[0.01, 0.02, 0.10],
        weights=[0.4, 0.4, 0.2],
        thresholds=thresholds,
        cvar_penalty=1.0,
        oce_penalty=1.0,
        satisficing_shortfall_penalty=10.0,
        risk_scale=100.0,
    )
    riskier = score_tail_satisficing_objective(
        expected_return=120.0,
        loss_rates=[0.01, 0.02, 0.50],
        weights=[0.4, 0.4, 0.2],
        thresholds=thresholds,
        cvar_penalty=1.0,
        oce_penalty=1.0,
        satisficing_shortfall_penalty=10.0,
        risk_scale=100.0,
    )

    assert safer.satisficing_pass
    assert not riskier.satisficing_pass
    assert safer.objective_value > riskier.objective_value
