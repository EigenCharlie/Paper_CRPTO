from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts.experiments import run_ijds_maturity_safe_challenger as challenger
from src.evaluation import maturity_safe_portfolio as portfolio
from src.evaluation.coverage_transport import (
    coverage_and_default_transport_bounds,
    coverage_and_default_transport_decomposition,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds
from src.models.binary_conformal_guardrail import BinaryOutcomeConformalRecipe
from src.optimization.policy import PolicyMode
from src.optimization.policy_selection import LinearPolicyCandidate


def _design() -> dict[str, object]:
    return {
        "term_months": 36,
        "development_end": "2010-12-31",
        "probability_calibration_start": "2011-01-01",
        "probability_calibration_end": "2011-12-31",
        "conformal_fit_start": "2012-01-01",
        "conformal_fit_end": "2012-06-30",
        "policy_development_start": "2012-07-01",
        "policy_development_end": "2012-12-31",
        "primary_oot_start_month": "2016-04",
        "primary_oot_end_month": "2017-06",
        "censored_extension_start_month": "2017-07",
        "censored_extension_end_month": "2017-09",
        "minimum_maturity_gap_months": 39,
    }


def test_predeclared_config_locks_scientific_design() -> None:
    config = challenger.load_config(challenger.DEFAULT_CONFIG_PATH)

    assert config["protocol_status"] == "locked_before_primary_outcome_analysis"
    assert config["protocol_tag"].startswith("protocol/ijds-maturity-safe-locked")
    assert config["design"]["conformal_fit_end"] == "2012-06-30"
    assert config["design"]["policy_development_start"] == "2012-07-01"
    assert config["design"]["primary_oot_start_month"] == "2016-04"
    assert config["design"]["primary_oot_end_month"] == "2017-06"
    assert config["policy"]["endpoint_budget_cap"] is None
    assert config["policy"]["risk_tolerances"] == [0.15, 0.17, 0.19]
    assert config["policy"]["gammas"] == [0.25, 0.5, 0.75]
    assert config["conformal"]["estimand"] == "binary_outcome_prediction_interval"
    assert config["design"]["unresolved_outcome_handling"] == (
        "sharp_binary_bounds_in_all_evaluation_blocks"
    )
    assert "sign-robust" in config["analysis"]["positive_claim_rule"]


def test_snapshot_target_includes_policy_variants_and_keeps_unresolved() -> None:
    statuses = pd.Series(
        [
            "Fully Paid",
            "Does not meet the credit policy. Status:Fully Paid",
            "Charged Off",
            "Does not meet the credit policy. Status:Charged Off",
            "Default",
            "Current",
            "Late (31-120 days)",
        ]
    )

    target = challenger.snapshot_default_from_status(statuses)
    resolution = challenger.snapshot_resolution_from_status(statuses)

    assert target.tolist()[:5] == [0, 0, 1, 1, 1]
    assert target.iloc[5:].isna().all()
    assert resolution.tolist() == [
        "nondefault",
        "nondefault",
        "default",
        "default",
        "default",
        "unresolved",
        "unresolved",
    ]


def test_design_splits_depend_only_on_issue_date() -> None:
    dates = pd.Series(
        pd.to_datetime(
            [
                "2010-12-01",
                "2011-07-01",
                "2012-03-01",
                "2012-09-01",
                "2016-03-01",
                "2016-04-01",
                "2017-06-01",
                "2017-07-01",
                "2017-09-01",
                "2017-10-01",
            ]
        )
    )
    statuses = pd.Series(["Current", "Default"] * 5)

    splits = challenger.assign_design_split(dates, _design())
    target = challenger.snapshot_default_from_status(statuses)

    assert splits.tolist() == [
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
        "outside_design",
        "primary_oot",
        "primary_oot",
        "censored_extension",
        "censored_extension",
        "outside_design",
    ]
    assert pd.isna(target.iloc[0])
    assert splits.iloc[0] == "pd_development"
    assert challenger.maturity_gap_months("2012-12-01", "2016-04-01") == 40


def test_temporal_tail_split_uses_a_whole_month_boundary() -> None:
    frame = pd.DataFrame(
        {
            "id": [str(value) for value in range(12)],
            "issue_d": pd.to_datetime(["2010-01-01"] * 4 + ["2010-02-01"] * 4 + ["2010-03-01"] * 4),
        }
    )

    train, validation, cutoff = challenger.temporal_tail_split(frame, tail_fraction=0.25)

    assert cutoff == pd.Timestamp("2010-03-01")
    assert train["issue_d"].max() < validation["issue_d"].min()
    assert set(train["id"]).isdisjoint(validation["id"])
    assert set(train["id"]) | set(validation["id"]) == set(frame["id"])


def test_maturity_contract_covers_all_locked_months() -> None:
    dates = pd.to_datetime(
        [
            "2010-12-01",
            "2011-12-01",
            "2012-06-01",
            *pd.date_range("2012-07-01", "2012-12-01", freq="MS").astype(str),
            *pd.date_range("2016-04-01", "2017-09-01", freq="MS").astype(str),
        ]
    )
    frame = pd.DataFrame(
        {
            "id": [str(index) for index in range(len(dates))],
            "issue_d": dates,
            "design_split": challenger.assign_design_split(pd.Series(dates), _design()),
        }
    )

    contract = challenger.validate_maturity_contract(
        frame,
        _design(),
        {"snapshot_date": "2020-09-30"},
    )

    assert contract["maturity_gap_months"] == 40
    assert contract["primary_oot_first_issue_month"] == "2016-04"
    assert contract["latest_retained_contract_maturity_month"] == "2020-09"
    assert contract["latest_contract_maturity_after_snapshot"] is False


def test_expected_and_realized_payoff_use_the_same_binary_formula() -> None:
    probabilities = np.array([0.0, 1.0, 0.2])
    rates = np.array([0.10, 0.10, 0.20])

    expected = challenger.expected_standardized_payoff_rate(probabilities, rates, lgd=0.45)
    realized_low, realized_high = challenger.realized_standardized_payoff_bounds(
        np.array([0.0, 1.0, np.nan]),
        rates,
        lgd=0.45,
    )

    np.testing.assert_allclose(expected, np.array([0.10, -0.45, 0.07]))
    np.testing.assert_allclose(realized_low, np.array([0.10, -0.45, -0.45]))
    np.testing.assert_allclose(realized_high, np.array([0.10, -0.45, 0.20]))


def test_solver_receives_adjusted_rate_and_objective_is_reconciled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = pd.DataFrame(
        {
            "id": ["a", "b"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-04-01"]),
            "loan_amnt": [100.0, 200.0],
            "purpose": ["x", "y"],
            "contractual_rate": [0.10, 0.20],
            "pd_point": [0.10, 0.25],
            "conformal_lower": [0.00, 0.10],
            "conformal_upper": [0.20, 0.40],
            "conformal_group": [0, 1],
        }
    )
    captured: dict[str, np.ndarray] = {}

    def fake_solver(**kwargs: object) -> SimpleNamespace:
        point = np.asarray(kwargs["pd_point"], dtype=float)
        adjusted_rate = np.asarray(kwargs["int_rates"], dtype=float)
        lgd = np.asarray(kwargs["lgd"], dtype=float)
        allocation = np.array([1.0, 0.5])
        exposure = allocation * frame["loan_amnt"].to_numpy(dtype=float)
        captured["int_rates"] = adjusted_rate
        return SimpleNamespace(
            solution={
                "solver_status": "Optimal",
                "solver_backend": "unit",
                "objective_value": float(exposure @ (adjusted_rate - point * lgd)),
            },
            allocation=allocation,
            effective_pd=point,
            policy_mode=PolicyMode.BLENDED_UNCERTAINTY,
            gamma=0.5,
            delta_cap_quantile=1.0,
            tail_focus_quantile=1.0,
            objective_risk_mode="legacy",
        )

    monkeypatch.setattr(portfolio, "solve_policy_allocation", fake_solver)
    candidate = LinearPolicyCandidate(
        candidate_id="linear-001",
        risk_tolerance=0.17,
        gamma=0.5,
        uncertainty_aversion=0.0,
        min_budget_utilization=1.0,
    )
    config = {
        "payoff": {"lgd": 0.45},
        "policy": {
            "budget": 200.0,
            "max_concentration_by_purpose": 1.0,
            "min_budget_utilization_solver": 1.0,
        },
        "execution": {
            "solver_time_limit_seconds": 10,
            "threads": 1,
            "solver_backend": "unit",
            "random_seed": 42,
        },
    }

    solved = challenger.solve_coherent_policy(frame, candidate, config=config, robust=True)

    np.testing.assert_allclose(
        captured["int_rates"],
        (1.0 - np.array([0.10, 0.25])) * [0.10, 0.20],
    )
    expected = challenger.expected_standardized_payoff_rate(
        frame["pd_point"].to_numpy(),
        frame["contractual_rate"].to_numpy(),
        lgd=0.45,
    )
    assert solved.expected_objective == pytest.approx(float(solved.exposure @ expected))


def test_decision_frame_rejects_outcome_and_derived_columns() -> None:
    safe = pd.DataFrame(
        {
            "id": ["a"],
            "loan_amnt": [100.0],
            "purpose": ["debt_consolidation"],
            "pd_point": [0.1],
            "conformal_lower": [0.0],
            "conformal_upper": [0.2],
        }
    )
    challenger.assert_outcome_free_decision_frame(safe)

    for forbidden in ("loan_status", "snapshot_default", "realized_payoff", "miscoverage"):
        leaked = safe.assign(**{forbidden: 0})
        with pytest.raises(ValueError, match="outcome-derived"):
            challenger.assert_outcome_free_decision_frame(leaked)


def test_binary_recipe_names_the_correct_estimand() -> None:
    recipe = challenger.fit_exact_mondrian_recipe(
        np.array([0.05, 0.10, 0.20, 0.30, 0.60, 0.80]),
        np.array([0, 0, 0, 1, 1, 1]),
        alpha=0.1,
        n_groups=2,
    )

    assert recipe.estimand == "binary_outcome_prediction_interval"
    assert recipe.learned_widening is False
    assert recipe.learned_floor is False


def test_mondrian_out_of_range_scores_map_to_outer_groups() -> None:
    groups = challenger.assign_mondrian_groups(
        np.array([-0.1, 0.15, 0.95, 1.1]),
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    )

    assert groups.tolist() == [0, 0, 4, 4]


def test_temporal_conformal_audit_reports_unresolved_bounds_and_extrapolation() -> None:
    recipe = BinaryOutcomeConformalRecipe(
        alpha=0.1,
        requested_groups=2,
        bin_edges=(0.1, 0.3, 0.5),
        residual_quantiles=(0.1, 0.2),
        group_counts=(10, 10),
        finite_sample_ranks=(9, 9),
        raw_finite_sample_ranks=(9, 9),
    )
    decision = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "issue_d": pd.to_datetime(["2016-04-01"] * 3),
            "loan_amnt": [100.0] * 3,
            "purpose": ["x"] * 3,
            "contractual_rate": [0.1] * 3,
            "pd_point": [0.05, 0.2, 0.6],
            "conformal_lower": [0.0, 0.1, 0.4],
            "conformal_upper": [0.15, 0.3, 0.8],
            "conformal_group": [0, 0, 1],
            "design_split": ["primary_oot"] * 3,
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "loan_status": ["Fully Paid", "Charged Off", "Current"],
            "snapshot_default": pd.Series([0, 1, pd.NA], dtype="Int8"),
            "snapshot_resolution": ["nondefault", "default", "unresolved"],
        }
    )

    audit = challenger.build_temporal_conformal_audit(decision, outcomes, recipe)
    pooled = audit.loc[
        audit["period"].eq("2016-04_to_2016-04") & audit["conformal_group"].eq("ALL")
    ].iloc[0]

    assert pooled["below_fit_score_range"] == 1
    assert pooled["above_fit_score_range"] == 1
    assert pooled["unresolved_rows"] == 1
    assert pooled["all_candidate_coverage_lower"] <= pooled["all_candidate_coverage_upper"]


def test_transport_decomposition_reconciles_exactly() -> None:
    candidates = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d"],
            "loan_amnt": [100.0, 200.0, 300.0, 400.0],
            "conformal_group": [0, 0, 1, 1],
            "conformal_lower": [0.0, 0.0, 0.0, 0.0],
            "conformal_upper": [0.2, 0.4, 0.3, 0.8],
            "snapshot_default": [0, 1, 0, 1],
        }
    )
    funded = candidates.loc[[0, 1, 3]].copy()
    funded["exposure"] = [500.0, 250.0, 250.0]

    decomposition = coverage_and_default_transport_decomposition(
        candidates,
        funded,
        alpha=0.1,
    )

    assert set(decomposition["metric"]) == {"binary_miscoverage", "snapshot_default"}
    assert np.allclose(decomposition["identity_residual"], 0.0, atol=1e-12)
    miss = decomposition.loc[decomposition["metric"].eq("binary_miscoverage")].iloc[0]
    reconstructed = (
        miss["row_minus_reference"]
        + miss["row_to_exposure"]
        + miss["group_composition"]
        + miss["within_group_selection"]
    )
    assert reconstructed == pytest.approx(miss["total_minus_reference"])


def test_bounded_transport_retains_unresolved_and_reconciles_both_completions() -> None:
    candidates = pd.DataFrame(
        {
            "id": ["a", "b", "c"],
            "loan_amnt": [100.0, 200.0, 300.0],
            "conformal_group": [0, 0, 1],
            "conformal_lower": [0.0, 0.0, 0.2],
            "conformal_upper": [0.2, 0.6, 0.8],
            "snapshot_default": [0.0, np.nan, 1.0],
        }
    )
    funded = candidates.copy()
    funded["exposure"] = [400.0, 300.0, 300.0]

    decomposition = coverage_and_default_transport_bounds(candidates, funded, alpha=0.1)

    assert set(decomposition["completion"]) == {"lower", "upper"}
    assert len(decomposition) == 4
    assert np.allclose(decomposition["identity_residual"], 0.0, atol=1e-12)
    defaults = decomposition.loc[decomposition["metric"].eq("snapshot_default")]
    assert (
        defaults.loc[defaults["completion"].eq("lower"), "funded_exposure_weighted"].iloc[0]
        < defaults.loc[defaults["completion"].eq("upper"), "funded_exposure_weighted"].iloc[0]
    )


def test_pairwise_policy_contrast_bounds_use_exposure_differences() -> None:
    allocations = pd.DataFrame(
        {
            "id": ["a", "b", "a"],
            "role": ["primary_oot"] * 3,
            "policy_label": ["guard", "guard", "point"],
            "exposure": [50.0, 50.0, 100.0],
            "contractual_rate": [0.10, 0.10, 0.10],
            "conformal_lower": [0.0, 0.0, 0.0],
            "conformal_upper": [0.2, 0.4, 0.2],
            "snapshot_default": [0.0, np.nan, 0.0],
            "expected_payoff_contribution": [4.0, 3.0, 8.0],
        }
    )

    bounds = sharp_policy_contrast_bounds(
        allocations,
        policy_a="guard",
        policy_b="point",
        role="primary_oot",
        lgd=0.45,
    )

    assert bounds["expected_objective_difference"] == pytest.approx(-1.0)
    assert bounds["realized_payoff_difference_lower"] == pytest.approx(-27.5)
    assert bounds["realized_payoff_difference_upper"] == pytest.approx(0.0)
    assert bounds["weighted_default_difference_lower"] == pytest.approx(0.0)
    assert bounds["weighted_default_difference_upper"] == pytest.approx(0.5)
    assert bounds["weighted_miscoverage_difference_lower"] == pytest.approx(0.0)
    assert bounds["weighted_miscoverage_difference_upper"] == pytest.approx(0.5)


def test_development_selector_uses_realized_payoff_and_deterministic_ties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = pd.DataFrame(
        {
            "id": ["a", "b"],
            "issue_d": pd.to_datetime(["2012-07-01", "2012-08-01"]),
            "loan_amnt": [100.0, 100.0],
            "purpose": ["x", "x"],
            "contractual_rate": [0.1, 0.1],
            "pd_point": [0.1, 0.1],
            "conformal_lower": [0.0, 0.0],
            "conformal_upper": [0.2, 0.2],
            "conformal_group": [0, 0],
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": ["a", "b"],
            "snapshot_default": pd.Series([0, 1], dtype="Int8"),
            "snapshot_resolution": ["nondefault", "default"],
            "loan_status": ["Fully Paid", "Charged Off"],
        }
    )
    candidates = [
        LinearPolicyCandidate("linear-001", 0.15, 0.25, 0.0),
        LinearPolicyCandidate("linear-002", 0.17, 0.50, 0.0),
    ]

    def fake_evaluate(
        _decision: pd.DataFrame,
        _outcomes: pd.DataFrame,
        candidate: LinearPolicyCandidate,
        **kwargs: object,
    ) -> tuple[dict[str, object], pd.DataFrame]:
        score = 20.0 if candidate.candidate_id == "linear-002" else 10.0
        return (
            {
                **candidate.to_record(),
                "period": str(kwargs["period"]),
                "policy_label": str(kwargs["policy_label"]),
                "full_budget": True,
                "total_allocated": 100.0,
                "expected_objective": score / 2.0,
                "realized_payoff_exact": score,
                "weighted_default_lower": 0.1,
                "weighted_miscoverage_lower": 0.1,
            },
            pd.DataFrame(),
        )

    monkeypatch.setattr(portfolio, "evaluation_record_and_allocations", fake_evaluate)
    selected, grid, monthly = portfolio.select_policy_on_development(
        decision,
        outcomes,
        [(candidate, True, "guardrail") for candidate in candidates],
        config={},
    )

    assert selected.candidate_id == "linear-002"
    assert grid.iloc[0]["candidate_id"] == "linear-002"
    assert len(monthly) == 4


def test_monthly_aggregate_uses_fresh_budget_exposure_weights() -> None:
    frame = pd.DataFrame(
        {
            "policy_label": ["fixed", "fixed"],
            "total_allocated": [1_000_000.0, 2_000_000.0],
            "expected_objective": [100.0, 300.0],
            "realized_payoff_lower": [10.0, 20.0],
            "realized_payoff_upper": [10.0, 40.0],
            "n_unresolved_candidates": [0, 2],
            "n_unresolved_positive_exposure": [0, 1],
            "weighted_pd_point": [0.1, 0.2],
            "weighted_pd_effective": [0.15, 0.25],
            "weighted_conformal_upper": [0.2, 0.4],
            "weighted_default_lower": [0.0, 0.3],
            "weighted_default_upper": [0.0, 0.5],
            "weighted_miscoverage_lower": [0.0, 0.1],
            "weighted_miscoverage_upper": [0.0, 0.2],
            "unresolved_exposure_share": [0.0, 0.2],
        }
    )

    aggregate = challenger.aggregate_monthly_evaluation(frame)

    assert aggregate["total_budget"] == 3_000_000.0
    assert aggregate["expected_objective"] == 400.0
    assert aggregate["weighted_default_lower"] == pytest.approx(0.2)
    assert aggregate["weighted_default_upper"] == pytest.approx(1.0 / 3.0)
    assert aggregate["unresolved_candidates"] == 2


def test_output_paths_are_contained_and_no_overwrite_is_default(tmp_path: Path) -> None:
    config = {
        "run_tag": "unit-maturity-safe-v1",
        "output": {
            "data_root": challenger.ALLOWED_DATA_ROOT.as_posix(),
            "model_root": challenger.ALLOWED_MODEL_ROOT.as_posix(),
        },
    }

    paths = challenger.prepare_output_paths(config, repo_root=tmp_path)

    assert paths.data_dir.parent == (tmp_path / challenger.ALLOWED_DATA_ROOT).resolve()
    assert paths.model_dir.parent == (tmp_path / challenger.ALLOWED_MODEL_ROOT).resolve()
    with pytest.raises(FileExistsError, match="fresh run tag"):
        challenger.prepare_output_paths(config, repo_root=tmp_path)


@pytest.mark.parametrize("run_tag", ["../escape", "a/b", r"a\b", "..", "."])
def test_output_paths_reject_unsafe_run_tags(tmp_path: Path, run_tag: str) -> None:
    config = {
        "run_tag": run_tag,
        "output": {
            "data_root": challenger.ALLOWED_DATA_ROOT.as_posix(),
            "model_root": challenger.ALLOWED_MODEL_ROOT.as_posix(),
        },
    }

    with pytest.raises(ValueError, match="Unsafe run_tag"):
        challenger.prepare_output_paths(config, repo_root=tmp_path)


def test_output_paths_reject_non_allowlisted_root(tmp_path: Path) -> None:
    config = {
        "run_tag": "unit-maturity-safe-v1",
        "output": {
            "data_root": "data/processed/not-allowed",
            "model_root": challenger.ALLOWED_MODEL_ROOT.as_posix(),
        },
    }

    with pytest.raises(ValueError, match="allowlisted"):
        challenger.prepare_output_paths(config, repo_root=tmp_path)
