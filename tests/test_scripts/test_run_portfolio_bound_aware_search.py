from __future__ import annotations

import pandas as pd
import pytest

from scripts.search.run_portfolio_bound_aware_search import (
    _aggregate_exact_results,
    _budget_profiles,
    _build_grid_spec,
    _build_parser,
    _build_stratified_shortlist,
    _policy_semantic_key,
    _resolve_run_paths,
    _sanitize_run_label,
    _search_space_payload,
    _selection_context_payload,
    _targeted_policy_grid,
)
from src.optimization.certificate_semantics import (
    IJDS_DECLARED_ALPHA_GRID,
    IJDS_DECLARED_ALPHA_GRID_CSV,
)


def _frontier_row(
    *,
    risk_tolerance: float,
    policy_mode: str,
    gamma: float,
    uncertainty_aversion: float,
    min_budget_utilization: float,
    pd_cap_slack_penalty: float,
    realized_total_return: float,
    price_of_robustness: float,
    worst_case_pd: float,
    point_pd: float,
    ab_pass_all: bool = True,
) -> dict[str, object]:
    return {
        "risk_tolerance": risk_tolerance,
        "policy_mode": policy_mode,
        "gamma": gamma,
        "delta_cap_quantile": 1.0,
        "tail_focus_quantile": 1.0 if policy_mode != "tail_blended_uncertainty" else 0.85,
        "uncertainty_aversion": uncertainty_aversion,
        "min_budget_utilization": min_budget_utilization,
        "pd_cap_slack_penalty": pd_cap_slack_penalty,
        "solver_backend": "highs",
        "seed_count": 1,
        "sample_random_states": "42",
        "ab_pass_all": ab_pass_all,
        "ab_pass_rate": 1.0 if ab_pass_all else 0.0,
        "realized_total_return": realized_total_return,
        "realized_total_return_max": realized_total_return,
        "price_of_robustness": price_of_robustness,
        "price_of_robustness_pct": price_of_robustness / 1000.0,
        "ab_diff_total_return": realized_total_return / 100.0,
        "objective_value": realized_total_return / 10.0,
        "n_funded": 100.0,
        "total_allocated": 1_000_000.0,
        "expected_return_net_point": realized_total_return / 5.0,
        "worst_case_pd": worst_case_pd,
        "point_pd": point_pd,
        "pd_cap_slack": 0.0,
    }


def test_stratified_shortlist_keeps_alpha01_incumbent_region() -> None:
    rows = []
    for idx in range(120):
        rows.append(
            _frontier_row(
                risk_tolerance=0.18 + idx * 0.0001,
                policy_mode="tail_blended_uncertainty",
                gamma=0.7,
                uncertainty_aversion=0.1,
                min_budget_utilization=0.05,
                pd_cap_slack_penalty=1.5,
                realized_total_return=150_000.0 - idx,
                price_of_robustness=-40_000.0 + idx,
                worst_case_pd=0.18 + idx * 1e-5,
                point_pd=0.16 + idx * 1e-5,
            )
        )

    incumbent = _frontier_row(
        risk_tolerance=0.16,
        policy_mode="blended_uncertainty",
        gamma=0.5,
        uncertainty_aversion=0.0,
        min_budget_utilization=0.0,
        pd_cap_slack_penalty=0.0,
        realized_total_return=90_529.78,
        price_of_robustness=-10_261.65,
        worst_case_pd=0.077725,
        point_pd=0.0700,
    )
    rows.append(incumbent)
    frontier = pd.DataFrame(rows)

    budget_profiles: list[dict[str, object]] = [
        {"name": "free_budget", "min_budget_utilization": 0.0, "pd_cap_slack_penalty": 0.0},
        {
            "name": "floored_budget",
            "min_budget_utilization": 0.05,
            "pd_cap_slack_penalty": 1.5,
        },
    ]
    shortlist = _build_stratified_shortlist(
        frontier=frontier,
        shortlist_top_k=30,
        bucket_return_k=10,
        bucket_proxy_k=10,
        bucket_family_k=5,
        bucket_region_k=5,
        incumbent_policy={
            "risk_tolerance": 0.16,
            "policy_mode": "blended_uncertainty",
            "gamma": 0.5,
            "delta_cap_quantile": 1.0,
            "tail_focus_quantile": 1.0,
            "uncertainty_aversion": 0.0,
            "min_budget_utilization": 0.0,
            "pd_cap_slack_penalty": 0.0,
            "solver_backend": "highs",
        },
        incumbent_risk_neighbors=[0.155, 0.16, 0.165, 0.17],
        incumbent_gamma_neighbors=[0.45, 0.5, 0.55],
        incumbent_policy_modes=["blended_uncertainty", "capped_blended_uncertainty"],
        budget_profiles=budget_profiles,
        solver_backend="highs",
    )

    incumbent_key = _policy_semantic_key(incumbent)
    assert incumbent_key in set(shortlist["semantic_policy_key"])
    incumbent_row = shortlist[shortlist["semantic_policy_key"] == incumbent_key].iloc[0]
    assert str(incumbent_row["shortlist_bucket"]).startswith("forced_") or str(
        incumbent_row["shortlist_bucket"]
    ).startswith("incumbent_")


def test_aggregate_exact_results_prefers_alpha01_passers() -> None:
    shortlist = pd.DataFrame(
        [
            {
                "candidate_rank": 1,
                "risk_tolerance": 0.16,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.5,
                "delta_cap_quantile": 1.0,
                "tail_focus_quantile": 1.0,
                "uncertainty_aversion": 0.0,
                "min_budget_utilization": 0.0,
                "pd_cap_slack_penalty": 0.0,
                "solver_backend": "highs",
                "ab_pass_all": True,
                "realized_total_return": 90_000.0,
                "price_of_robustness": -10_000.0,
                "alpha01_exact_pass": False,
                "alpha01_weighted_miscoverage_V": 9.99,
                "alpha01_gamma_cp": 9.99,
            },
            {
                "candidate_rank": 2,
                "risk_tolerance": 0.18,
                "policy_mode": "tail_blended_uncertainty",
                "gamma": 0.7,
                "delta_cap_quantile": 1.0,
                "tail_focus_quantile": 0.85,
                "uncertainty_aversion": 0.1,
                "min_budget_utilization": 0.05,
                "pd_cap_slack_penalty": 1.5,
                "solver_backend": "highs",
                "ab_pass_all": True,
                "realized_total_return": 120_000.0,
                "price_of_robustness": -35_000.0,
                "alpha01_exact_pass": True,
                "alpha01_weighted_miscoverage_V": 0.01,
                "alpha01_gamma_cp": 0.01,
            },
        ]
    )

    bound_rows = []
    for eval_seed in [42, 2026]:
        for alpha in [0.01, 0.03, 0.10]:
            bound_rows.append(
                {
                    "eval_random_state": eval_seed,
                    "alpha": alpha,
                    "all_bounds_hold": True,
                    "gamma_cp": 0.17,
                    "weighted_miscoverage_V": 0.08,
                    "violation": 0.0,
                    "weighted_pd_true": 0.08,
                    "weighted_pd_constraint_used": 0.16,
                    "empirical_coverage_funded": 0.95,
                    **shortlist.iloc[0].to_dict(),
                }
            )
            bound_rows.append(
                {
                    "eval_random_state": eval_seed,
                    "alpha": alpha,
                    "all_bounds_hold": not (alpha == 0.01 and eval_seed == 2026),
                    "gamma_cp": 0.19,
                    "weighted_miscoverage_V": 0.11,
                    "violation": 0.01 if (alpha == 0.01 and eval_seed == 2026) else 0.0,
                    "weighted_pd_true": 0.11,
                    "weighted_pd_constraint_used": 0.18,
                    "empirical_coverage_funded": 0.93,
                    **shortlist.iloc[1].to_dict(),
                }
            )
    bound_eval = pd.DataFrame(bound_rows)

    ranked = _aggregate_exact_results(shortlist=shortlist, bound_eval=bound_eval)

    assert bool(ranked.iloc[0]["alpha01_exact_pass"]) is True
    assert float(ranked.iloc[0]["risk_tolerance"]) == 0.16
    assert float(ranked.iloc[0]["alpha01_weighted_miscoverage_V"]) == 0.08
    assert bool(ranked.iloc[1]["alpha01_exact_pass"]) is False
    assert not any(col.endswith(("_x", "_y")) for col in ranked.columns)


def test_targeted_policy_grid_includes_segment_tail_families() -> None:
    grid = _targeted_policy_grid(
        gamma_values=[0.5],
        delta_cap_quantiles=[0.75],
        tail_focus_quantiles=[0.9],
        policy_modes=[
            "blended_uncertainty",
            "capped_blended_uncertainty",
            "tail_blended_uncertainty",
            "segment_tail_blended_uncertainty",
            "segment_relative_tail_blended_uncertainty",
        ],
    )

    assert {row[0] for row in grid} == {
        "blended_uncertainty",
        "capped_blended_uncertainty",
        "tail_blended_uncertainty",
        "segment_tail_blended_uncertainty",
        "segment_relative_tail_blended_uncertainty",
    }
    assert grid == [
        ("blended_uncertainty", 0.5, 1.0, 1.0),
        ("capped_blended_uncertainty", 0.5, 0.75, 1.0),
        ("tail_blended_uncertainty", 0.5, 1.0, 0.9),
        ("segment_tail_blended_uncertainty", 0.5, 1.0, 0.9),
        ("segment_relative_tail_blended_uncertainty", 0.5, 1.0, 0.9),
    ]


def test_budget_profiles_are_explicit_and_reject_unknown_tokens() -> None:
    profiles = _budget_profiles("free,floored")

    assert [profile["name"] for profile in profiles] == ["free_budget", "floored_budget"]
    assert profiles[0]["min_budget_utilization"] == 0.0
    assert profiles[1]["pd_cap_slack_penalty"] == 1.5
    with pytest.raises(ValueError, match="Unsupported budget profile"):
        _budget_profiles("free,aggressive")


def test_bound_aware_default_uses_declared_ijds_alpha_grid() -> None:
    args = _build_parser().parse_args(["--conformal-intervals-path", "intervals.parquet"])

    assert args.alpha_grid == IJDS_DECLARED_ALPHA_GRID_CSV


def test_grid_spec_separates_proxy_and_exact_sampling_contracts() -> None:
    args = _build_parser().parse_args(
        [
            "--conformal-intervals-path",
            "intervals.parquet",
            "--risk-grid",
            "0.16,0.17",
            "--random-states",
            "42,52",
            "--exact-random-states",
            "62,72,82",
            "--max-candidates",
            "5000",
            "--exact-max-candidates",
            "0",
        ]
    )

    grid = _build_grid_spec(args)

    assert grid.random_states == [42, 52]
    assert grid.exact_random_states == [62, 72, 82]
    assert grid.exact_max_candidates == 0
    assert grid.alpha_grid == list(IJDS_DECLARED_ALPHA_GRID)
    assert grid.bound_total_checks(shortlist_size=5) == 5 * 8 * 3
    assert grid.frontier_total_units == 2 * 2 * (1 + grid.policy_grid_count)


def test_selection_context_payload_keeps_frontier_and_exact_paths_together(tmp_path) -> None:
    args = _build_parser().parse_args(
        [
            "--conformal-intervals-path",
            str(tmp_path / "intervals.parquet"),
            "--run-label",
            "unit/run",
            "--output-dir",
            str(tmp_path / "out"),
            "--model-dir",
            str(tmp_path / "model"),
            "--random-states",
            "42,52",
            "--exact-random-states",
            "42",
            "--policy-modes",
            "blended_uncertainty",
        ]
    )
    run_label = _sanitize_run_label(args.run_label)
    paths = _resolve_run_paths(args, run_label=run_label)
    search_space = _search_space_payload(
        args=args,
        risk_values=[0.16],
        aversion_values=[0.0],
        gamma_values=[0.5],
        delta_cap_quantiles=[1.0],
        tail_focus_quantiles=[1.0],
        budget_profiles=_budget_profiles(args.budget_profiles),
        alpha_grid=[0.01],
        random_states=[42, 52],
        exact_random_states=[42],
        exact_max_candidates=0,
        policy_modes=["blended_uncertainty"],
        cuopt_parameters={"method": "concurrent"},
        incumbent_risk_neighbors=[0.16],
        incumbent_gamma_neighbors=[0.5],
        incumbent_policy_modes=["blended_uncertainty"],
    )

    context = _selection_context_payload(
        args=args,
        paths=paths,
        run_label=run_label,
        search_space=search_space,
        exact_max_candidates=0,
        random_states=[42, 52],
        exact_random_states=[42],
        alpha_grid=[0.01],
    )

    assert run_label == "unit_run"
    assert context["search_space"]["random_states"] == [42, 52]
    assert context["search_space"]["exact_random_states"] == [42]
    assert context["shortlist_path"] == str(paths.shortlist_path)
    assert context["selection_path"] == str(paths.selection_path)
    assert context["resource_snapshot_path"] == str(paths.resource_path)
