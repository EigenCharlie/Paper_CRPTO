from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.search import build_pool93_ijds_consolidated_frontier as frontier


def test_load_leaderboards_rehydrates_policy_aware_tail_bound(
    tmp_path: Path,
    monkeypatch,
) -> None:
    leaderboard_path = tmp_path / "leaderboard.parquet"
    bound_path = tmp_path / "bound.parquet"
    pd.DataFrame(
        {
            "local_candidate_id": [7],
            "semantic_policy_key": ["tail-policy"],
            "alpha01_endpoint_budget_upper": [0.50],
            "alpha01_markov_loss_cap": [0.60],
        }
    ).to_parquet(leaderboard_path, index=False)
    pd.DataFrame(
        {
            "local_candidate_id": [7],
            "semantic_policy_key": ["tail-policy"],
            "alpha": [0.01],
            "risk_tolerance": [0.20],
            "gamma_cp": [0.60],
            "weighted_pd_point": [0.10],
            "weighted_pd_constraint_used": [0.20],
            "weighted_pd_high": [0.60],
            "pd_cap_slack": [0.0],
        }
    ).to_parquet(bound_path, index=False)
    monkeypatch.setattr(frontier, "_leaderboard_path", lambda _tag: leaderboard_path)
    monkeypatch.setattr(frontier, "_bound_eval_path", lambda _tag: bound_path)

    row = frontier._load_leaderboards(["unit-tag"]).iloc[0]

    assert row["alpha01_gamma_internalized"] == pytest.approx(0.10)
    assert row["alpha01_gamma_residual"] == pytest.approx(0.40)
    assert row["alpha01_endpoint_budget"] == pytest.approx(0.60)
    assert row["alpha01_endpoint_budget_upper"] == pytest.approx(0.60)
    assert row["alpha01_markov_loss_threshold"] == pytest.approx(0.70)
    assert row["alpha01_markov_loss_cap"] == pytest.approx(0.70)


def test_body_selection_uses_exact_markov_threshold() -> None:
    eligible = pd.DataFrame(
        {
            "semantic_policy_key": ["tail", "linear"],
            "alpha01_realized_total_return": [220_000.0, 190_000.0],
            "alpha01_markov_loss_threshold": [0.70, 0.34],
        }
    )

    selected = frontier._body_candidate(eligible, markov_threshold=0.35)

    assert selected["semantic_policy_key"] == "linear"


def test_threshold_frontier_does_not_mislabel_tail_policy_as_under_half() -> None:
    eligible = pd.DataFrame(
        {
            "semantic_policy_key": ["tail", "linear"],
            "alpha01_realized_total_return": [220_000.0, 190_000.0],
            "alpha01_markov_loss_threshold": [0.70, 0.45],
        }
    )

    selected = frontier._best_under_threshold(eligible, 0.50)

    assert selected is not None
    assert selected["semantic_policy_key"] == "linear"
