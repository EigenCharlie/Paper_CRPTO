from __future__ import annotations

import math
from itertools import combinations, permutations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.stats import betabinom

from src.ijds_audit.exchangeability_transport_test import (
    beta_binomial_log_upper_tail,
    build_exchangeability_transport_test,
    holm_adjustment,
    split_conformal_beta_parameters,
)
from src.models.binary_conformal_guardrail import BinaryOutcomeConformalRecipe

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_exchangeability_transport_test_2026-07-21_v1.yaml"


def _recipe() -> BinaryOutcomeConformalRecipe:
    return BinaryOutcomeConformalRecipe(
        alpha=0.25,
        requested_groups=2,
        bin_edges=(0.0, 0.5, 1.0),
        residual_quantiles=(0.25, 0.25),
        group_counts=(4, 4),
        finite_sample_ranks=(4, 4),
        raw_finite_sample_ranks=(4, 4),
        method="fixed_taxonomy_split_mondrian_absolute_residual",
        taxonomy_provenance="test_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )


def _fixture_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scores = pd.DataFrame(
        {
            "id": list("abcdefgh"),
            "issue_d": pd.to_datetime(["2016-04-01"] * 8),
            "design_split": ["primary_oot"] * 8,
            "pd_test": [0.1, 0.2, 0.1, 0.4, 0.6, 0.8, 0.9, 0.5],
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": list("abcdefgh"),
            "snapshot_default": [0.0, 1.0, np.nan, np.nan, 1.0, 1.0, np.nan, np.nan],
        }
    )

    point = np.asarray([0.05, 0.10, 0.15, 0.25, 0.95, 0.90, 0.85, 0.75])
    labels = np.asarray([0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    group = np.asarray([0, 0, 0, 0, 1, 1, 1, 1])
    threshold = np.full(8, 0.25)
    lower = np.clip(point - threshold, 0.0, 1.0)
    upper = np.clip(point + threshold, 0.0, 1.0)
    fit_audit = pd.DataFrame(
        {
            "id": list("ijklmnop"),
            "issue_d": pd.to_datetime(["2012-01-01"] * 8),
            "learner": ["test"] * 8,
            "window_id": ["w1"] * 8,
            "taxonomy_groups": [2] * 8,
            "conformal_group": group,
            "pd_point": point,
            "conformal_lower": lower,
            "conformal_upper": upper,
            "terminal_default": labels,
            "covered": (labels >= lower) & (labels <= upper),
        }
    )
    fit_scores = pd.DataFrame(
        {
            "id": list("ijklmnop"),
            "issue_d": pd.to_datetime(["2012-01-01"] * 8),
            "design_split": ["conformal_fit"] * 8,
            "pd_test": point,
        }
    )
    scores = pd.concat([fit_scores, scores], ignore_index=True)
    return scores, outcomes, fit_audit


def _baseline_reference() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "learner": ["test", "test"],
            "window_id": ["w1", "w1"],
            "taxonomy_groups": [2, 2],
            "role": ["primary_oot", "primary_oot"],
            "conformal_group": [0, 1],
            "candidate_rows": [4, 4],
            "resolved_rows": [2, 2],
            "unresolved_rows": [2, 2],
            "coverage_resolved": [0.5, 0.5],
            "coverage_lower": [0.25, 0.25],
            "coverage_upper": [0.5, 0.5],
            "score_min": [0.1, 0.5],
            "score_max": [0.4, 0.9],
            "fit_rows": [4, 4],
            "fit_residual_quantile": [0.25, 0.25],
            "fit_score_min": [0.05, 0.75],
            "fit_score_max": [0.25, 0.95],
        }
    )


def _build(
    baseline_reference: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores, outcomes, fit_audit = _fixture_frames()
    return build_exchangeability_transport_test(
        scores,
        outcomes,
        fit_audit,
        _baseline_reference() if baseline_reference is None else baseline_reference,
        {"test": {"w1": {2: _recipe()}}},
        learners=("test",),
        window_ids=("w1",),
        role="primary_oot",
        taxonomy_groups=2,
        expected_issue_months=("2016-04",),
        expected_candidates=8,
        expected_resolved=4,
        expected_unresolved=4,
        expected_resolved_y0=1,
        expected_resolved_y1=3,
        nominal_miscoverage=0.25,
        familywise_alpha=0.05,
    )


def test_split_conformal_beta_parameters_use_the_attained_rank() -> None:
    assert split_conformal_beta_parameters(9, 9) == (1, 9)
    assert split_conformal_beta_parameters(10, 10) == (1, 10)
    with pytest.raises(ValueError, match="rank"):
        split_conformal_beta_parameters(9, 10)


def test_exact_beta_binomial_tail_matches_a_closed_form_uniform_case() -> None:
    # BetaBinomial(2, 1, 1) is uniform on {0, 1, 2}.
    assert math.exp(
        beta_binomial_log_upper_tail(
            trials=2,
            misses_at_least=1,
            beta_a=1,
            beta_b=1,
        )
    ) == pytest.approx(2.0 / 3.0)
    assert math.exp(
        beta_binomial_log_upper_tail(
            trials=2,
            misses_at_least=2,
            beta_a=1,
            beta_b=1,
        )
    ) == pytest.approx(1.0 / 3.0)


def test_beta_binomial_tail_matches_direct_exchangeable_rank_counting() -> None:
    # Conditional on the ordered values, joint continuity and exchangeability
    # make every allocation of n calibration ranks among n+m ranks equiprobable.
    n_calibration = 4
    n_target = 3
    rank = 4
    beta_a, beta_b = split_conformal_beta_parameters(n_calibration, rank)
    denominator = math.comb(n_calibration + n_target, n_calibration)
    for threshold in range(n_target + 1):
        direct_tail = 0.0
        for target_above in range(threshold, n_target + 1):
            before = math.comb(
                n_target + rank - target_above - 1,
                rank - 1,
            )
            after = math.comb(
                n_calibration - rank + target_above,
                n_calibration - rank,
            )
            direct_tail += (before * after) / denominator
        exact_tail = math.exp(
            beta_binomial_log_upper_tail(
                trials=n_target,
                misses_at_least=threshold,
                beta_a=beta_a,
                beta_b=beta_b,
            )
        )
        assert exact_tail == pytest.approx(direct_tail)


def test_beta_binomial_tail_matches_exhaustive_rank_allocations_for_interior_ranks() -> None:
    for n_calibration in range(1, 6):
        for n_target in range(1, 5):
            allocations = list(combinations(range(n_calibration + n_target), n_calibration))
            for rank in range(1, n_calibration + 1):
                beta_a, beta_b = split_conformal_beta_parameters(n_calibration, rank)
                target_above_counts: list[int] = []
                for calibration_positions in allocations:
                    calibration_set = set(calibration_positions)
                    threshold_position = calibration_positions[rank - 1]
                    target_above_counts.append(
                        sum(
                            position > threshold_position and position not in calibration_set
                            for position in range(n_calibration + n_target)
                        )
                    )
                for threshold in range(n_target + 1):
                    direct_tail = float(np.mean(np.asarray(target_above_counts) >= threshold))
                    exact_tail = math.exp(
                        beta_binomial_log_upper_tail(
                            trials=n_target,
                            misses_at_least=threshold,
                            beta_a=beta_a,
                            beta_b=beta_b,
                        )
                    )
                    assert exact_tail == pytest.approx(direct_tail, abs=1.0e-14)


def test_beta_binomial_large_tail_matches_scipy_independently() -> None:
    trials = 700
    threshold = 95
    beta_a, beta_b = 13, 113
    actual = beta_binomial_log_upper_tail(
        trials=trials,
        misses_at_least=threshold,
        beta_a=beta_a,
        beta_b=beta_b,
    )
    expected = float(betabinom.logsf(threshold - 1, trials, beta_a, beta_b))
    assert actual == pytest.approx(expected, abs=1.0e-11)


def test_strict_misses_with_ties_are_pointwise_bounded_by_lexicographic_misses() -> None:
    calibration = np.asarray([0.0, 0.0, 1.0])
    target = np.asarray([0.0, 1.0, 0.0])
    rank = 2
    scalar_threshold = float(np.sort(calibration)[rank - 1])
    deterministic_misses = int(np.sum(target > scalar_threshold))

    # Exhaust every distinct ordering of independent continuous auxiliary
    # tie breakers. This checks the pointwise domination used to extend the
    # exact continuous-rank tail conservatively to exchangeable tied scores.
    for auxiliary_order in permutations(range(len(calibration) + len(target))):
        calibration_pairs = sorted(
            zip(calibration, auxiliary_order[: len(calibration)], strict=True)
        )
        pair_threshold = calibration_pairs[rank - 1]
        lexicographic_misses = sum(
            pair > pair_threshold
            for pair in zip(target, auxiliary_order[len(calibration) :], strict=True)
        )
        assert deterministic_misses <= lexicographic_misses


def test_holm_step_down_stops_after_the_first_failure() -> None:
    result = holm_adjustment(np.log([0.01, 0.04, 0.041]), alpha=0.05)
    assert result["holm_rank"].tolist() == [1, 2, 3]
    assert result["holm_reject"].tolist() == [True, False, False]
    assert result["holm_adjusted_p_value"].tolist() == pytest.approx([0.03, 0.08, 0.08])


def test_holm_preserves_stable_tie_order_and_log_underflow() -> None:
    result = holm_adjustment(np.array([math.log(0.01), -1000.0, math.log(0.01)]), alpha=0.05)
    assert result["holm_rank"].tolist() == [2, 1, 3]
    assert result["holm_reject"].tolist() == [True, True, True]
    assert result.loc[1, "holm_adjusted_p_value"] == 0.0
    assert result.loc[0, "holm_adjusted_p_value"] == pytest.approx(0.02)
    assert result.loc[2, "holm_adjusted_p_value"] == pytest.approx(0.02)


def test_complete_test_uses_sharp_minimum_misses_and_nested_multiplicity() -> None:
    strata, cells = _build()
    assert len(strata) == 2
    assert len(cells) == 1
    assert strata["resolved_misses"].tolist() == [1, 1]
    assert strata["unresolved_min_misses"].tolist() == [1, 1]
    assert strata["unresolved_max_misses"].tolist() == [2, 2]
    assert strata["misses_min"].tolist() == [2, 2]
    assert strata["misses_max"].tolist() == [3, 3]
    assert strata["coverage_lower"].tolist() == pytest.approx([0.25, 0.25])
    assert strata["coverage_upper"].tolist() == pytest.approx([0.5, 0.5])
    assert strata["beta_a"].tolist() == [1, 1]
    assert strata["beta_b"].tolist() == [4, 4]
    assert strata["continuous_threshold_tie_singleton"].tolist() == [True, True]
    assert cells.loc[0, "cell_bonferroni_p_value"] == pytest.approx(
        min(1.0, 2.0 * strata["exact_p_value"].min())
    )
    assert cells.loc[0, "holm_adjusted_p_value"] == pytest.approx(
        cells.loc[0, "cell_bonferroni_p_value"]
    )
    assert not bool(cells.loc[0, "holm_reject_exchangeability_null"])


def test_exact_test_stops_if_active_v5_stratum_coverage_does_not_reconcile() -> None:
    corrupted = _baseline_reference()
    corrupted.loc[0, "coverage_upper"] += 1.0e-5
    with pytest.raises(RuntimeError, match="coverage_upper does not reconcile"):
        _build(corrupted)


def test_endpoint_rejects_infinite_or_nonnumeric_values_instead_of_treating_them_as_unresolved() -> (
    None
):
    scores, outcomes, fit_audit = _fixture_frames()
    for invalid in (float("inf"), "not-an-outcome"):
        corrupted = outcomes.copy()
        if isinstance(invalid, str):
            corrupted["snapshot_default"] = corrupted["snapshot_default"].astype(object)
        corrupted.loc[2, "snapshot_default"] = invalid
        with pytest.raises(RuntimeError, match="nonnumeric or infinite"):
            build_exchangeability_transport_test(
                scores,
                corrupted,
                fit_audit,
                _baseline_reference(),
                {"test": {"w1": {2: _recipe()}}},
                learners=("test",),
                window_ids=("w1",),
                role="primary_oot",
                taxonomy_groups=2,
                expected_issue_months=("2016-04",),
                expected_candidates=8,
                expected_resolved=4,
                expected_unresolved=4,
                expected_resolved_y0=1,
                expected_resolved_y1=3,
                nominal_miscoverage=0.25,
                familywise_alpha=0.05,
            )


def test_endpoint_id_alignment_is_required_even_for_an_unresolved_row() -> None:
    scores, outcomes, fit_audit = _fixture_frames()
    with pytest.raises(RuntimeError, match="Endpoint alignment is incomplete"):
        build_exchangeability_transport_test(
            scores,
            outcomes.iloc[:-1],
            fit_audit,
            _baseline_reference(),
            {"test": {"w1": {2: _recipe()}}},
            learners=("test",),
            window_ids=("w1",),
            role="primary_oot",
            taxonomy_groups=2,
            expected_issue_months=("2016-04",),
            expected_candidates=8,
            expected_resolved=4,
            expected_unresolved=4,
            expected_resolved_y0=1,
            expected_resolved_y1=3,
            nominal_miscoverage=0.25,
            familywise_alpha=0.05,
        )


def test_config_locks_sources_complete_grid_and_hierarchical_family() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["protocol_tag"] == ("protocol/ijds-exchangeability-transport-test-2026-07-21-v1")
    assert len(config["design"]["learners"]) == 5
    assert len(config["design"]["window_ids"]) == 8
    assert config["design"]["taxonomy_groups"] == 5
    assert config["design"]["issue_months"] == [
        str(period) for period in pd.period_range("2016-04", "2017-06", freq="M")
    ]
    assert config["multiplicity"] == {
        "familywise_alpha": 0.05,
        "strata_per_cell": 5,
        "within_cell_method": "bonferroni",
        "cell_family_size": 40,
        "across_cells_method": "holm",
        "dependence_requirement": "none",
    }
    assert config["source"]["scores"]["sha256"] == (
        "5795bc0a75be90e86d37cf7d297f4b4fd6e6604b38f8179bc5042c024a53a8dc"
    )
    assert config["source"]["recipes"]["sha256"] == (
        "969ecbefe46bec4893a03be57385eda29b33dd291d73e7c0120f6d488a9e9936"
    )
    assert config["source"]["fit_audit"]["sha256"] == (
        "396c30d9bec7d222220cfe6f9870ab4994cf5c33e6da8c9e4ebbd99153155353"
    )
    assert config["output"]["strata_table"].startswith("evaluation/")
    assert config["output"]["cell_table"].startswith("evaluation/")
