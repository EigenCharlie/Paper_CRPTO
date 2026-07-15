from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.evaluation.coverage_transport import binary_miscoverage_bounds
from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.evaluation import build_archive_outcomes
from src.ijds_audit.geometry import (
    BOTH,
    EMPTY,
    ONE_ONLY,
    ZERO_ONLY,
    binary_set_codes,
    constant_score_population_phase,
    summarize_binary_geometry,
)
from src.ijds_audit.portfolio import (
    PointPortfolioSession,
    c2_cap,
    enumerate_basis_breakpoints,
    solve_point_portfolio,
    verify_c2_dominance,
)
from src.ijds_audit.protocol import expand_frontier_for_window
from src.ijds_audit.simulation import run_factorial_simulation
from src.models.binary_conformal_guardrail import fit_binary_outcome_recipe
from src.optimization.portfolio_model import solve_portfolio_highspy_native

ROOT = Path(__file__).resolve().parents[1]


def test_v4_config_is_closed_and_complete() -> None:
    config = load_v4_config(
        ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"
    )
    assert len(config["residual_specification"]["windows"]) == 8
    assert config["design"]["policy_development_start"] == "2013-02-01"

    recovery = load_v4_config(
        ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12_v2.yaml"
    )
    assert recovery["run_tag"].endswith("-v2")
    assert recovery["resume_outcome_free"]["source_run_tag"].endswith("-v1")

    endpoint_recovery = load_v4_config(
        ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-14_v3.yaml"
    )
    contract = endpoint_recovery["target"]["evaluation_outcome_contract"]
    assert endpoint_recovery["run_tag"].endswith("-v3")
    assert contract["mode"] == "conservative_terminal_status_reconstruction"
    assert contract["archive_is_verified_point_in_time_snapshot"] is False


def test_v4_config_rejects_unknown_critical_keys(tmp_path: Path) -> None:
    config = load_v4_config(
        ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-14_v3.yaml"
    )
    config["policy"]["budegt"] = config["policy"]["budget"]
    path = tmp_path / "typo.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(KeyError, match="budegt"):
        load_v4_config(path)


def test_binary_set_codes_and_summary() -> None:
    lower = np.array([0.1, 0.0, 0.2, 0.0])
    upper = np.array([0.9, 0.8, 1.0, 1.0])
    np.testing.assert_array_equal(
        binary_set_codes(lower, upper),
        np.array([EMPTY, ZERO_ONLY, ONE_ONLY, BOTH]),
    )
    summary = summarize_binary_geometry(lower, upper)
    assert summary["set_empty_count"] == 1
    assert summary["set_both_count"] == 1
    assert summary["width_q50"] == pytest.approx(0.8)


def test_binary_coverage_bounds_respect_empty_singleton_and_both_sets() -> None:
    outcomes = np.full(4, np.nan)
    lower = np.array([0.1, 0.0, 0.2, 0.0])
    upper = np.array([0.9, 0.8, 1.0, 1.0])
    miss_low, miss_high = binary_miscoverage_bounds(outcomes, lower, upper)
    assert 1.0 - miss_high.mean() == pytest.approx(0.25)
    assert 1.0 - miss_low.mean() == pytest.approx(0.75)


def test_reconstructed_endpoint_censors_terminal_status_after_cutoff() -> None:
    universe = pd.DataFrame(
        {
            "id": pd.Series(["a", "b", "c"], dtype="string"),
            "terminal_default": pd.Series([0, 1, pd.NA], dtype="Int8"),
            "label_available_at": pd.to_datetime(["2020-09-01", "2020-10-01", None]),
            "design_split": ["primary_oot"] * 3,
            "issue_d": pd.to_datetime(["2016-04-01"] * 3),
        }
    )
    outcomes = build_archive_outcomes(universe, evaluation_cutoff="2020-09-30")
    assert outcomes["snapshot_default"].tolist() == [0, pd.NA, pd.NA]
    assert outcomes["snapshot_resolution"].tolist() == [
        "fully_paid",
        "terminal_after_reconstructed_cutoff",
        "right_censored",
    ]


def test_constant_score_phase_transition() -> None:
    low_prevalence = constant_score_population_phase(score=0.08, prevalence=0.09, alpha=0.10)
    high_prevalence = constant_score_population_phase(score=0.08, prevalence=0.11, alpha=0.10)
    assert low_prevalence.discrete_set == "{0}"
    assert low_prevalence.coverage == pytest.approx(0.91)
    assert high_prevalence.discrete_set == "{0,1}"
    assert high_prevalence.coverage == pytest.approx(1.0)


def test_exact_budget_point_lp_and_c2_dominance() -> None:
    frame = pd.DataFrame(
        {
            "loan_amnt": [60.0, 50.0, 40.0, 30.0],
            "purpose": ["a", "a", "b", "b"],
        }
    )
    point = np.array([0.03, 0.07, 0.10, 0.14])
    rate = np.array([0.10, 0.14, 0.18, 0.22])
    objective = expected_objective_coefficients(point, rate, lgd=0.45)
    guard_exposure = np.array([60.0, 0.0, 40.0, 0.0])
    cap = c2_cap(guard_exposure, point)
    solution = solve_point_portfolio(
        frame,
        point_score=point,
        objective_rate=objective,
        budget=100.0,
        risk_cap=cap,
        purpose_cap=0.6,
    )
    assert solution.total_allocated == pytest.approx(100.0)
    assert solution.weighted_point_score <= cap + 1e-10
    diagnostics = verify_c2_dominance(
        guardrail_exposure=guard_exposure,
        point_solution=solution,
        point_score=point,
        objective_rate=objective,
    )
    assert diagnostics["point_minus_guardrail_objective"] >= -1e-5
    assert solution.basis_cap_lower <= cap <= solution.basis_cap_upper

    breakpoints = enumerate_basis_breakpoints(
        frame,
        point_score=point,
        objective_rate=objective,
        budget=100.0,
        purpose_cap=0.6,
        lower_cap=0.06,
        upper_cap=0.13,
    )
    assert breakpoints[0] == pytest.approx(0.06)
    assert breakpoints[-1] == pytest.approx(0.13)
    assert tuple(sorted(breakpoints)) == breakpoints


def test_exact_budget_formulation_matches_legacy_inequalities() -> None:
    frame = pd.DataFrame(
        {
            "loan_amnt": [55.0, 45.0, 35.0, 25.0, 20.0],
            "purpose": ["a", "b", "a", "b", "c"],
        }
    )
    point = np.array([0.025, 0.052, 0.081, 0.113, 0.147])
    rate = np.array([0.09, 0.13, 0.17, 0.20, 0.24])
    objective = expected_objective_coefficients(point, rate, lgd=0.45)
    cap = 0.075
    exact = solve_point_portfolio(
        frame,
        point_score=point,
        objective_rate=objective,
        budget=100.0,
        risk_cap=cap,
        purpose_cap=0.55,
    )
    legacy = solve_portfolio_highspy_native(
        loans=frame,
        pd_point=point,
        pd_low=point,
        pd_high=point,
        lgd=np.full(len(frame), 0.45),
        int_rates=rate,
        total_budget=100.0,
        max_concentration=0.55,
        max_portfolio_pd=cap,
        robust=False,
        min_budget_utilization=1.0,
        objective_rate_override=objective,
        threads=1,
    )
    assert exact.objective_value == pytest.approx(legacy["objective_value"], abs=1e-8)
    np.testing.assert_allclose(
        exact.allocation_fraction,
        np.asarray(legacy["allocation_vector"], dtype=float),
        rtol=0.0,
        atol=1e-8,
    )

    session = PointPortfolioSession(
        frame,
        point_score=point,
        objective_rate=objective,
        budget=100.0,
        purpose_cap=0.55,
    )
    first = session.solve(cap)
    session.solve(0.10)
    repeated = session.solve(cap)
    assert repeated.objective_value == pytest.approx(first.objective_value, abs=1e-8)
    np.testing.assert_allclose(repeated.allocation_fraction, first.allocation_fraction, atol=1e-8)


def test_factorial_simulation_smoke() -> None:
    config = load_v4_config(
        ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"
    )
    config["simulation"].update(
        repetitions=3,
        sample_size=500,
        score_shift_grid=[0.0],
        prevalence_shift_grid=[0.0],
        taxonomy_groups_grid=[1],
        censoring_rate_grid=[0.0],
    )
    repetitions, summary = run_factorial_simulation(config)
    assert len(repetitions) == 3
    assert len(summary) == 1
    assert np.isfinite(repetitions["point_minus_guardrail_objective"]).all()


def test_shared_frontier_replaces_placeholder_endpoints() -> None:
    scores = pd.DataFrame(
        {
            "id": pd.Series(["a", "b", "c", "d"], dtype="string"),
            "design_split": ["primary_oot"] * 4,
            "pd_catboost_platt": [0.1, 0.2, 0.3, 0.4],
        }
    )
    recipe = fit_binary_outcome_recipe(
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([0, 0, 1, 1]),
        alpha=0.1,
        n_groups=1,
        bin_edges=(0.0, 1.0),
    )
    shared = pd.DataFrame(
        {
            "id": pd.Series(["a", "c"], dtype="string"),
            "conformal_lower": [np.nan, np.nan],
            "conformal_upper": [np.nan, np.nan],
            "conformal_group": [np.nan, np.nan],
        }
    )
    expanded = expand_frontier_for_window(shared, scores, recipe, window_id="window")
    assert {"conformal_lower", "conformal_upper", "conformal_group"}.issubset(expanded)
    assert not any(column.endswith(("_x", "_y")) for column in expanded.columns)
    assert expanded["conformal_lower"].notna().all()
