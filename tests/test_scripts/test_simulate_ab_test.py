from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.simulate_ab_test import _resolve_robust_policy


def test_resolve_robust_policy_uses_guardrail_champion_priority(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "champion_portfolio_policy.json").write_text(
        json.dumps(
            {
                "selected_policy": {"risk_tolerance": 0.10, "gamma": 0.1},
                "selected_policy_balanced_robustness": {
                    "risk_tolerance": 0.11,
                    "policy_mode": "balanced",
                    "gamma": 0.2,
                },
                "selected_policy_guardrail_robustness": {
                    "risk_tolerance": 0.12,
                    "policy_mode": "guardrail",
                    "gamma": 0.3,
                },
            }
        ),
        encoding="utf-8",
    )

    policy = _resolve_robust_policy(
        max_portfolio_pd=0.20,
        policy_selector="guardrail_robustness",
    )

    assert policy["source"] == "champion_policy_artifact::guardrail_robustness"
    assert policy["policy_mode"] == "guardrail"
    assert policy["risk_tolerance"] == 0.12
    assert policy["gamma"] == 0.3


def test_resolve_robust_policy_uses_summary_when_champion_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    summary_path = tmp_path / "data" / "processed" / "portfolio_robustness_summary.parquet"
    summary_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "risk_tolerance": 0.15,
                "best_robust_lambda": 0.2,
                "best_robust_min_budget_utilization": 0.90,
                "best_robust_pd_cap_slack_penalty": 1.0,
                "best_robust_return": 100.0,
                "best_robust_policy_mode": "hard_worst_case",
                "best_robust_gamma": 0.8,
                "best_robust_delta_cap_quantile": 0.95,
            },
            {
                "risk_tolerance": 0.18,
                "best_robust_lambda": 0.4,
                "best_robust_min_budget_utilization": 0.91,
                "best_robust_pd_cap_slack_penalty": 2.0,
                "best_robust_return": 200.0,
                "best_robust_policy_mode": "blended_uncertainty",
                "best_robust_gamma": 0.6,
                "best_robust_delta_cap_quantile": 0.90,
            },
        ]
    ).to_parquet(summary_path, index=False)

    policy = _resolve_robust_policy(max_portfolio_pd=0.17)

    assert policy["source"] == "portfolio_robustness_summary"
    assert policy["risk_tolerance"] == 0.15
    assert policy["uncertainty_aversion"] == 0.2
    assert policy["gamma"] == 0.8


def test_resolve_robust_policy_explicit_champion_only_requires_artifact(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        _resolve_robust_policy(
            max_portfolio_pd=0.20,
            policy_selector="explicit_champion_only",
        )
