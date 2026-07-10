from __future__ import annotations

import pandas as pd
import pytest

import scripts.search.run_portfolio_bound_exact_eval as exact_eval
from scripts.search.build_portfolio_exact_priority_context import build_priority_context
from scripts.search.run_portfolio_bound_exact_eval import (
    ROOT,
    _context_exact_threads,
    _context_max_candidates,
    _context_random_states,
    _exact_eval_plan,
    _load_completed_bound_eval,
    _load_partial_bound_eval,
    _repo_relative,
    _resume_exact_rows,
    _search_space_payload,
    _shortlist_exact_path,
    _validate_alpha_grid_supported,
)


def test_load_completed_bound_eval_reuses_complete_cache(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    expected = pd.DataFrame(
        {
            "alpha": [0.01, 0.03],
            "all_bounds_hold": [True, True],
            "gamma_cp": [0.18, 0.18],
            "weighted_miscoverage_V": [0.03, 0.03],
        }
    )
    expected.to_parquet(path, index=False)

    cached = _load_completed_bound_eval(bound_eval_path=path, expected_checks=2)

    assert cached is not None
    assert cached.equals(expected)


def test_load_completed_bound_eval_rejects_incomplete_cache(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    pd.DataFrame(
        {
            "alpha": [0.01],
            "all_bounds_hold": [True],
            "gamma_cp": [0.18],
            "weighted_miscoverage_V": [0.03],
        }
    ).to_parquet(path, index=False)

    assert _load_completed_bound_eval(bound_eval_path=path, expected_checks=2) is None


def test_load_partial_bound_eval_reuses_checkpoint_rows(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    pd.DataFrame(
        {
            "candidate_rank": [1, 1],
            "eval_random_state": [42, 42],
            "alpha": [0.01, 0.01],
            "all_bounds_hold": [False, True],
            "gamma_cp": [0.20, 0.18],
            "weighted_miscoverage_V": [0.04, 0.03],
            "solver_status": ["unknown", "optimal"],
        }
    ).to_parquet(path, index=False)

    cached = _load_partial_bound_eval(bound_eval_path=path)

    assert len(cached) == 1
    assert bool(cached.iloc[0]["all_bounds_hold"]) is True
    assert cached.iloc[0]["allocator_solver_backend"] == "highspy_fallback_highs_sparse"
    assert cached.iloc[0]["allocator_native_solver_error"] == ""


def test_exact_context_overrides_proxy_sampling() -> None:
    context = {
        "max_candidates": 100000,
        "exact_max_candidates": 0,
        "random_states": [42],
        "exact_random_states": "42,52,62",
    }

    assert _context_max_candidates(context) == 0
    assert _context_random_states(context) == [42, 52, 62]


def test_exact_plan_dedupes_full_universe_random_states(monkeypatch) -> None:
    monkeypatch.delenv("EXACT_THREADS", raising=False)
    context = {
        "alpha_grid": [0.01, 0.03],
        "max_candidates": 100000,
        "exact_max_candidates": 0,
        "random_states": [42],
        "requested_exact_random_states": "42,52,62",
        "exact_checkpoint_every": 7,
        "exact_threads": 3,
    }

    plan = _exact_eval_plan(context=context, shortlist_rows=5)

    assert plan.requested_random_states == [42, 52, 62]
    assert plan.random_states == [42]
    assert plan.full_universe_seed_deduped is True
    assert plan.expected_checks == 10
    assert plan.exact_threads == 3
    assert plan.checkpoint_every == 7


def test_exact_threads_can_come_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("EXACT_THREADS", "8")

    assert _context_exact_threads({"exact_threads": 2}) == 8


def test_shortlist_exact_path_uses_explicit_output() -> None:
    expected = ROOT / "data" / "processed" / "portfolio_bound_aware_shortlist_exact.parquet"
    context: dict[str, object] = {
        "shortlist_path": str(
            ROOT / "data" / "processed" / "portfolio_bound_aware_shortlist.parquet"
        ),
        "shortlist_exact_path": str(expected),
    }

    assert _shortlist_exact_path(context) == expected


def test_repo_relative_keeps_artifact_paths_standalone() -> None:
    path = ROOT / "models" / "portfolio_bound_aware" / "selection.json"

    assert _repo_relative(path) == "models/portfolio_bound_aware/selection.json"


def test_resume_exact_rows_filters_out_irrelevant_seeds(tmp_path) -> None:
    path = tmp_path / "bound_eval.parquet"
    pd.DataFrame(
        {
            "candidate_rank": [1, 1, 2],
            "eval_random_state": [42, 52, 42],
            "alpha": [0.01, 0.01, 0.03],
            "all_bounds_hold": [True, True, False],
        }
    ).to_parquet(path, index=False)

    rows, keys = _resume_exact_rows(bound_eval_path=path, random_states=[42])

    assert len(rows) == 2
    assert keys == {(1, 42, 0.01), (2, 42, 0.03)}


def test_search_space_payload_records_requested_alpha_grid() -> None:
    context: dict[str, object] = {"search_space": {"alpha_grid": [0.01], "mode": ["capped"]}}

    payload = _search_space_payload(context=context, alpha_grid=[0.01, 0.03])

    assert payload["alpha_grid"] == [0.01, 0.03]
    assert payload["requested_alpha_grid"] == [0.01]
    assert payload["effective_alpha_grid"] == [0.01, 0.03]
    assert payload["mode"] == ["capped"]


def test_validate_alpha_grid_supported_accepts_sweep_values(tmp_path, monkeypatch) -> None:
    sweep_path = tmp_path / "data" / "processed" / "alpha_sweep_pareto_mondrian.parquet"
    sweep_path.parent.mkdir(parents=True)
    pd.DataFrame({"alpha": [0.01, 0.03, 0.05]}).to_parquet(sweep_path, index=False)
    monkeypatch.setattr(exact_eval, "ROOT", tmp_path)

    _validate_alpha_grid_supported([0.01, 0.03])


def test_validate_alpha_grid_supported_rejects_missing_sweep_values(
    tmp_path,
    monkeypatch,
) -> None:
    sweep_path = tmp_path / "data" / "processed" / "alpha_sweep_pareto_mondrian.parquet"
    sweep_path.parent.mkdir(parents=True)
    pd.DataFrame({"alpha": [0.01, 0.03, 0.05]}).to_parquet(sweep_path, index=False)
    monkeypatch.setattr(exact_eval, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="absent"):
        _validate_alpha_grid_supported([0.01, 0.02])


def test_priority_context_orders_claim_candidates_and_dedupes_full_universe_seeds(
    tmp_path,
) -> None:
    shortlist_path = tmp_path / "shortlist.parquet"
    pd.DataFrame(
        {
            "candidate_rank": [1, 2, 3],
            "shortlist_bucket": [
                "incumbent_region",
                "forced_incumbent_neighbors",
                "conservative_proxy",
            ],
            "risk_tolerance": [0.15, 0.16, 0.20],
            "policy_mode": ["blended_uncertainty"] * 3,
            "gamma": [0.45, 0.45, 0.0],
            "uncertainty_aversion": [0.0, 0.1, 0.0],
            "realized_total_return": [160_000.0, 175_000.0, 180_000.0],
            "ab_pass_all": [True, True, True],
        }
    ).to_parquet(shortlist_path, index=False)
    context_path = tmp_path / "context.json"
    context_path.write_text(
        """
{
  "shortlist_path": "__SHORTLIST__",
  "random_states": [42],
  "exact_random_states": [42, 52, 62],
  "max_candidates": 100000,
  "exact_max_candidates": 0,
  "selection_policy": {}
}
""".replace("__SHORTLIST__", shortlist_path.as_posix()),
        encoding="utf-8",
    )

    payload = build_priority_context(
        context_path=context_path,
        champion_return=170_464.54,
    )

    priority = pd.read_parquet(payload["priority_shortlist_path"])
    assert priority.iloc[0]["candidate_rank"] == 2
    assert priority.iloc[0]["exact_priority_reason"] == "above_champion_forced_incumbent_region"
    assert payload["effective_exact_random_states"] == [42]
    assert payload["full_universe_seed_deduped"] is True
