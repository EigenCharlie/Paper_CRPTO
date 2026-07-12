from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.optimization.certificate_semantics import (
    IJDS_DECLARED_ALPHA_GRID,
    IJDS_DECLARED_ALPHA_GRID_CSV,
    add_policy_aware_bound_columns,
    compute_funded_certificate_metrics,
)

ROOT = Path(__file__).resolve().parents[2]


def test_historical_ijds_alpha_grid_matches_its_profile() -> None:
    profile_path = ROOT / "configs" / "profiles" / "search_portfolio_pool93_stage1_claim_26_06.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    assert profile["grids"]["alpha_grid"] == IJDS_DECLARED_ALPHA_GRID_CSV
    assert IJDS_DECLARED_ALPHA_GRID == (0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20)


def test_linear_blend_certificate_decomposition() -> None:
    weights = np.array([0.25, 0.75])
    point = np.array([0.10, 0.20])
    high = np.array([0.50, 0.60])
    gamma = 0.50
    effective = point + gamma * (high - point)

    metrics = compute_funded_certificate_metrics(
        weights,
        outcomes=np.array([0.0, 1.0]),
        pd_point=point,
        pd_high=high,
        pd_effective=effective,
        alpha=0.01,
        risk_tolerance=float(weights @ effective),
    )

    assert metrics.gamma_cp == pytest.approx(0.40)
    assert metrics.gamma_internalized == pytest.approx(gamma * metrics.gamma_cp)
    assert metrics.gamma_residual == pytest.approx((1.0 - gamma) * metrics.gamma_cp)
    assert metrics.endpoint_budget == pytest.approx(float(weights @ high))
    assert metrics.endpoint_budget_upper == pytest.approx(metrics.endpoint_budget)
    assert metrics.markov_loss_threshold == pytest.approx(metrics.endpoint_budget + 0.10)
    assert metrics.markov_loss_cap == pytest.approx(metrics.markov_loss_threshold)


def test_tail_policy_uses_actual_residual_not_linear_blend_shortcut() -> None:
    weights = np.array([0.50, 0.50])
    point = np.array([0.10, 0.10])
    high = np.array([0.50, 0.90])
    gamma = 0.50
    effective = np.array([0.10, 0.50])

    metrics = compute_funded_certificate_metrics(
        weights,
        outcomes=np.array([0.0, 1.0]),
        pd_point=point,
        pd_high=high,
        pd_effective=effective,
        alpha=0.01,
        risk_tolerance=float(weights @ effective),
    )

    linear_shortcut = (1.0 - gamma) * metrics.gamma_cp
    assert metrics.gamma_cp == pytest.approx(0.60)
    assert metrics.gamma_internalized == pytest.approx(0.20)
    assert metrics.gamma_residual == pytest.approx(0.40)
    assert linear_shortcut == pytest.approx(0.30)
    assert metrics.gamma_residual > linear_shortcut
    assert metrics.endpoint_budget_upper == pytest.approx(metrics.endpoint_budget)


def test_policy_cap_slack_is_included_in_endpoint_upper() -> None:
    metrics = compute_funded_certificate_metrics(
        weights=np.array([1.0]),
        outcomes=np.array([1.0]),
        pd_point=np.array([0.10]),
        pd_high=np.array([0.60]),
        pd_effective=np.array([0.40]),
        alpha=0.04,
        risk_tolerance=0.35,
        pd_cap_slack=0.05,
    )

    assert metrics.endpoint_budget == pytest.approx(0.60)
    assert metrics.gamma_residual == pytest.approx(0.20)
    assert metrics.endpoint_budget_upper == pytest.approx(0.60)
    assert metrics.markov_loss_cap == pytest.approx(0.80)
    assert metrics.effective_constraint_excess == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("weights", "match"),
    [
        (np.array([0.25, 0.25]), "sum to one"),
        (np.array([1.1, -0.1]), "nonnegative"),
    ],
)
def test_certificate_rejects_invalid_weights(weights: np.ndarray, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        compute_funded_certificate_metrics(
            weights=weights,
            outcomes=np.array([0.0, 1.0]),
            pd_point=np.array([0.10, 0.20]),
            pd_high=np.array([0.30, 0.40]),
            pd_effective=np.array([0.20, 0.30]),
            alpha=0.01,
            risk_tolerance=0.30,
        )


def test_bound_frame_rehydrates_tail_policy_without_linear_shortcut() -> None:
    frame = pd.DataFrame(
        {
            "alpha": [0.01],
            "risk_tolerance": [0.20],
            "gamma": [0.50],
            "gamma_cp": [0.60],
            "weighted_pd_point": [0.10],
            "weighted_pd_constraint_used": [0.20],
            "weighted_pd_high": [0.60],
            "pd_cap_slack": [0.0],
        }
    )

    result = add_policy_aware_bound_columns(frame).iloc[0]

    assert result["gamma_internalized"] == pytest.approx(0.10)
    assert result["gamma_residual"] == pytest.approx(0.40)
    assert result["endpoint_budget"] == pytest.approx(0.60)
    assert result["endpoint_budget_upper"] == pytest.approx(0.60)
    assert result["markov_loss_threshold"] == pytest.approx(0.70)
    assert result["markov_loss_cap"] == pytest.approx(0.70)
    assert pytest.approx(0.50) == 0.20 + (1.0 - 0.50) * 0.60


def test_bound_frame_separates_exact_threshold_from_slack_upper() -> None:
    frame = pd.DataFrame(
        {
            "alpha": [0.04],
            "tau": [0.50],
            "weighted_pd_constraint_used": [0.40],
            "weighted_pd_high": [0.60],
        }
    )

    result = add_policy_aware_bound_columns(frame).iloc[0]

    assert result["effective_constraint_slack"] == pytest.approx(0.10)
    assert result["endpoint_budget"] == pytest.approx(0.60)
    assert result["endpoint_budget_upper"] == pytest.approx(0.70)
    assert result["markov_loss_threshold"] == pytest.approx(0.80)
    assert result["markov_loss_cap"] == pytest.approx(0.90)
