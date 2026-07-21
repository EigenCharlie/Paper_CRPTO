from __future__ import annotations

from copy import deepcopy
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.label_mondrian import (
    apply_label_mondrian_thresholds,
    evaluate_label_mondrian,
    exact_split_conformal_threshold,
    fit_label_mondrian_thresholds,
    sharp_class_coverage_gap_bounds,
    sharp_class_coverage_ratio_bounds,
)
from src.ijds_audit.label_mondrian_protocol import (
    declared_grid,
    load_label_mondrian_config,
    require_locked_evaluation_source,
)
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
    fit_binary_outcome_recipe,
)

ROOT = Path(__file__).resolve().parents[1]
FREEZE_CONFIG = ROOT / "configs" / "experiments" / "ijds_label_mondrian_freeze_2026-07-21_v1.yaml"
EVALUATION_CONFIG = (
    ROOT / "configs" / "experiments" / "ijds_label_mondrian_evaluation_2026-07-21_v1.yaml"
)
PROTOCOL = ROOT / "docs" / "research" / "ijds_label_mondrian_sensitivity_protocol_2026-07-21.md"


def _one_group_recipe(quantile: float = 0.2) -> BinaryOutcomeConformalRecipe:
    return BinaryOutcomeConformalRecipe(
        alpha=0.1,
        requested_groups=1,
        bin_edges=(0.0, 1.0),
        residual_quantiles=(quantile,),
        group_counts=(10,),
        finite_sample_ranks=(10,),
        raw_finite_sample_ranks=(10,),
        taxonomy_provenance="test_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )


def test_exact_threshold_uses_infinity_at_rank_n_plus_one() -> None:
    rank, threshold = exact_split_conformal_threshold([0.2], alpha=0.1)
    assert rank == 2
    assert np.isposinf(threshold)


def test_exact_threshold_uses_the_unclipped_finite_order_statistic() -> None:
    residuals = np.array([0.9, 0.1, 0.7, 0.2, 0.4, 0.8, 0.3, 0.6, 0.5])
    rank, threshold = exact_split_conformal_threshold(residuals, alpha=0.1)
    assert rank == 9
    assert threshold == pytest.approx(0.9)


def test_threshold_freeze_reconciles_fit_artifacts_and_reports_full_label_grid() -> None:
    probabilities = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    labels = np.array([0, 1, 0, 1, 0, 1, 0, 1])
    recipe = fit_binary_outcome_recipe(
        probabilities,
        labels,
        alpha=0.25,
        bin_edges=(0.0, 0.5, 1.0),
        taxonomy_provenance="test_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )
    assigned, lower, upper = apply_binary_outcome_recipe(probabilities, recipe)
    covered = ((labels == 0) & (lower <= 0.0)) | ((labels == 1) & (upper >= 1.0))
    ids = [str(index) for index in range(len(labels))]
    issue_dates = pd.to_datetime(["2012-01-01"] * len(labels))
    scores = pd.DataFrame(
        {
            "id": ids,
            "issue_d": issue_dates,
            "design_split": ["conformal_fit"] * len(labels),
            "pd_test": probabilities,
        }
    )
    fit_audit = pd.DataFrame(
        {
            "id": ids,
            "issue_d": issue_dates,
            "learner": ["test"] * len(labels),
            "window_id": ["w1"] * len(labels),
            "taxonomy_groups": [2] * len(labels),
            "conformal_group": assigned,
            "pd_point": probabilities,
            "conformal_lower": lower,
            "conformal_upper": upper,
            "terminal_default": labels,
            "covered": covered,
        }
    )
    result = fit_label_mondrian_thresholds(
        scores,
        fit_audit,
        {"test": {"w1": {2: recipe}}},
        learners=("test",),
        window_ids=("w1",),
        taxonomy_groups=2,
        alpha=0.25,
    )
    assert len(result) == 4
    assert set(result[["score_stratum", "label"]].itertuples(index=False, name=None)) == {
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    }
    assert result["fit_rows"].eq(2).all()
    assert result["finite_sample_rank"].eq(3).all()
    assert result["threshold_is_infinite"].all()
    assert np.isposinf(result["threshold"]).all()


def test_threshold_freeze_rejects_evaluation_outcomes_in_score_frame() -> None:
    scores = pd.DataFrame(
        {
            "id": ["a"],
            "issue_d": pd.to_datetime(["2012-01-01"]),
            "design_split": ["conformal_fit"],
            "pd_test": [0.2],
            "snapshot_default": [0.0],
        }
    )
    with pytest.raises(RuntimeError, match="outcome columns entered"):
        fit_label_mondrian_thresholds(
            scores,
            pd.DataFrame(),
            {},
            learners=("test",),
            window_ids=("w1",),
            taxonomy_groups=1,
            alpha=0.1,
        )


def test_apply_thresholds_constructs_the_discrete_class_conditional_set() -> None:
    thresholds = pd.DataFrame(
        {
            "score_stratum": [0, 0],
            "label": [0, 1],
            "taxonomy_groups": [1, 1],
            "threshold": [0.5, 0.5],
        }
    )
    groups, contains_zero, contains_one = apply_label_mondrian_thresholds(
        np.array([0.1, 0.4, 0.6, 0.9]),
        _one_group_recipe(),
        thresholds,
    )
    assert groups.tolist() == [0, 0, 0, 0]
    assert contains_zero.tolist() == [True, True, False, False]
    assert contains_one.tolist() == [False, False, True, True]


def _enumerated_class_coverage(
    contains: np.ndarray,
    outcomes: np.ndarray,
    target_label: int,
) -> list[float]:
    unresolved = np.flatnonzero(~np.isfinite(outcomes))
    values: list[float] = []
    for assignment in product((0.0, 1.0), repeat=len(unresolved)):
        completed = outcomes.copy()
        completed[unresolved] = assignment
        mask = completed == float(target_label)
        if bool(mask.any()):
            values.append(float(contains[mask].mean()))
    return values


def test_sharp_class_ratio_bounds_equal_exhaustive_binary_completion() -> None:
    contains = np.array([True, False, True, False, True, False])
    outcomes = np.array([0.0, 0.0, 1.0, np.nan, np.nan, np.nan])
    expected = _enumerated_class_coverage(contains, outcomes, target_label=0)
    lower, upper = sharp_class_coverage_ratio_bounds(
        contains,
        outcomes,
        target_label=0,
    )
    assert lower == pytest.approx(min(expected))
    assert upper == pytest.approx(max(expected))


def test_class_ratio_is_defined_by_unresolved_rows_without_a_resolved_target_label() -> None:
    lower, upper = sharp_class_coverage_ratio_bounds(
        np.array([False, True, False]),
        np.array([0.0, np.nan, np.nan]),
        target_label=1,
    )
    assert lower == pytest.approx(0.0)
    assert upper == pytest.approx(1.0)


def test_sharp_gap_bounds_equal_exhaustive_common_completion() -> None:
    contains_zero = np.array([True, False, True, False, True, False])
    contains_one = np.array([False, True, True, False, False, True])
    outcomes = np.array([0.0, 1.0, np.nan, np.nan, np.nan, np.nan])
    unresolved = np.flatnonzero(~np.isfinite(outcomes))
    expected: list[tuple[float, int]] = []
    for assignment in product((0.0, 1.0), repeat=len(unresolved)):
        completed = outcomes.copy()
        completed[unresolved] = assignment
        gap = float(contains_zero[completed == 0.0].mean() - contains_one[completed == 1.0].mean())
        expected.append((gap, int(sum(assignment))))
    lower, upper, lower_witness, upper_witness = sharp_class_coverage_gap_bounds(
        contains_zero,
        contains_one,
        outcomes,
    )
    assert lower == pytest.approx(min(value for value, _ in expected))
    assert upper == pytest.approx(max(value for value, _ in expected))
    assert lower_witness in {
        witness for value, witness in expected if value == pytest.approx(lower)
    }
    assert upper_witness in {
        witness for value, witness in expected if value == pytest.approx(upper)
    }


def test_sharp_gap_optimizer_matches_exhaustive_completion_over_small_type_mixtures() -> None:
    generator = np.random.default_rng(20260721)
    for unresolved_rows in range(1, 7):
        for _ in range(8):
            contains_zero = generator.integers(0, 2, size=unresolved_rows + 4).astype(bool)
            contains_one = generator.integers(0, 2, size=unresolved_rows + 4).astype(bool)
            outcomes = np.array([0.0, 0.0, 1.0, 1.0, *([np.nan] * unresolved_rows)])
            brute_force: list[float] = []
            for assignment in product((0.0, 1.0), repeat=unresolved_rows):
                completed = outcomes.copy()
                completed[4:] = assignment
                brute_force.append(
                    float(
                        contains_zero[completed == 0.0].mean()
                        - contains_one[completed == 1.0].mean()
                    )
                )
            lower, upper, _, _ = sharp_class_coverage_gap_bounds(
                contains_zero,
                contains_one,
                outcomes,
            )
            assert lower == pytest.approx(min(brute_force))
            assert upper == pytest.approx(max(brute_force))


def test_evaluation_reports_sharp_bounds_set_efficiency_and_baseline_reconciliation() -> None:
    scores = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d"],
            "issue_d": pd.to_datetime(["2016-04-01"] * 4),
            "design_split": ["primary_oot"] * 4,
            "pd_test": [0.1, 0.4, 0.6, 0.9],
        }
    )
    outcomes = pd.DataFrame(
        {"id": ["a", "b", "c", "d"], "snapshot_default": [0.0, 0.0, 1.0, np.nan]}
    )
    thresholds = pd.DataFrame(
        {
            "learner": ["test", "test"],
            "window_id": ["w1", "w1"],
            "taxonomy_groups": [1, 1],
            "score_stratum": [0, 0],
            "label": [0, 1],
            "alpha": [0.1, 0.1],
            "fit_rows": [10, 10],
            "finite_sample_rank": [10, 10],
            "threshold": [0.5, 0.5],
            "threshold_is_infinite": [False, False],
        }
    )
    baseline_sets = pd.DataFrame(
        {
            "learner": ["test"],
            "window_id": ["w1"],
            "taxonomy_groups": [1],
            "role": ["primary_oot"],
            "coverage_resolved": [1.0 / 3.0],
            "coverage_resolved_y0": [0.5],
            "coverage_resolved_y1": [0.0],
            "average_set_size": [0.5],
            "singleton_share": [0.5],
            "set_empty_share": [0.5],
            "set_zero_only_share": [0.25],
            "set_one_only_share": [0.25],
            "set_both_share": [0.0],
            "mean_width": [0.35],
        }
    )
    baseline_coverage = pd.DataFrame(
        {
            "learner": ["test"],
            "window_id": ["w1"],
            "taxonomy_groups": [1],
            "role": ["primary_oot"],
            "conformal_group": [-1],
            "coverage_lower": [0.25],
            "coverage_upper": [0.5],
        }
    )
    evaluation, categories, strata, reconciliation = evaluate_label_mondrian(
        scores,
        outcomes,
        {"test": {"w1": {1: _one_group_recipe()}}},
        thresholds,
        baseline_sets,
        baseline_coverage,
        learners=("test",),
        window_ids=("w1",),
        role="primary_oot",
        taxonomy_groups=1,
        expected_issue_months=("2016-04",),
        expected_candidates=4,
        expected_resolved=3,
        expected_unresolved=1,
        expected_resolved_y0=2,
        expected_resolved_y1=1,
    )
    row = evaluation.iloc[0]
    assert row["coverage_lower"] == pytest.approx(0.75)
    assert row["coverage_upper"] == pytest.approx(1.0)
    assert row["coverage_resolved_y0"] == pytest.approx(1.0)
    assert row["coverage_resolved_y1"] == pytest.approx(1.0)
    assert row["coverage_y0_lower"] == pytest.approx(2.0 / 3.0)
    assert row["coverage_y0_upper"] == pytest.approx(1.0)
    assert row["coverage_y1_lower"] == pytest.approx(1.0)
    assert row["coverage_y1_upper"] == pytest.approx(1.0)
    assert row["average_set_size"] == pytest.approx(1.0)
    assert row["singleton_share"] == pytest.approx(1.0)
    assert row["set_empty_share"] == pytest.approx(0.0)
    assert row["set_zero_only_share"] == pytest.approx(0.5)
    assert row["set_one_only_share"] == pytest.approx(0.5)
    assert row["set_both_share"] == pytest.approx(0.0)
    assert len(categories) == 2
    y0 = categories.loc[categories["label"].eq(0)].iloc[0]
    y1 = categories.loc[categories["label"].eq(1)].iloc[0]
    assert y0["resolved_label_rows"] == 2
    assert y0["coverage_label_lower"] == pytest.approx(2.0 / 3.0)
    assert y0["coverage_label_upper"] == pytest.approx(1.0)
    assert y1["resolved_label_rows"] == 1
    assert y1["coverage_label_lower"] == pytest.approx(1.0)
    assert y1["coverage_label_upper"] == pytest.approx(1.0)
    assert len(strata) == 1
    assert strata.loc[0, "coverage_gap_y0_minus_y1_lower"] == pytest.approx(-1.0 / 3.0)
    assert strata.loc[0, "coverage_gap_y0_minus_y1_upper"] == pytest.approx(0.0)
    differences = reconciliation.filter(like="_difference").to_numpy(dtype=float)
    assert np.max(np.abs(differences)) <= 5.0e-14


def test_two_strata_remain_visible_when_an_aggregate_hides_a_category_failure() -> None:
    probabilities = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    outcomes_array = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, np.nan, np.nan])
    scores = pd.DataFrame(
        {
            "id": list("abcdefgh"),
            "issue_d": pd.to_datetime(["2016-04-01"] * 8),
            "design_split": ["primary_oot"] * 8,
            "pd_test": probabilities,
        }
    )
    outcomes = pd.DataFrame({"id": list("abcdefgh"), "snapshot_default": outcomes_array})
    recipe = BinaryOutcomeConformalRecipe(
        alpha=0.1,
        requested_groups=2,
        bin_edges=(0.0, 0.5, 1.0),
        residual_quantiles=(0.25, 0.25),
        group_counts=(10, 10),
        finite_sample_ranks=(10, 10),
        raw_finite_sample_ranks=(10, 10),
        taxonomy_provenance="test_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )
    thresholds = pd.DataFrame(
        {
            "learner": ["test"] * 4,
            "window_id": ["w1"] * 4,
            "taxonomy_groups": [2] * 4,
            "score_stratum": [0, 0, 1, 1],
            "label": [0, 1, 0, 1],
            "alpha": [0.1] * 4,
            "fit_rows": [10] * 4,
            "finite_sample_rank": [10] * 4,
            "threshold": [0.5, 0.1, 0.65, 0.25],
            "threshold_is_infinite": [False] * 4,
        }
    )
    _, baseline_lower, baseline_upper = apply_binary_outcome_recipe(probabilities, recipe)
    baseline_zero = baseline_lower <= 0.0
    baseline_one = baseline_upper >= 1.0
    resolved = np.isfinite(outcomes_array)
    resolved_labels = outcomes_array[resolved].astype(int)
    baseline_covered = np.where(
        resolved_labels == 0,
        baseline_zero[resolved],
        baseline_one[resolved],
    )
    unresolved_always = baseline_zero[~resolved] & baseline_one[~resolved]
    unresolved_never = ~baseline_zero[~resolved] & ~baseline_one[~resolved]
    cardinality = baseline_zero.astype(int) + baseline_one.astype(int)
    baseline_sets = pd.DataFrame(
        {
            "learner": ["test"],
            "window_id": ["w1"],
            "taxonomy_groups": [2],
            "role": ["primary_oot"],
            "coverage_resolved": [float(baseline_covered.mean())],
            "coverage_resolved_y0": [float(baseline_zero[resolved][resolved_labels == 0].mean())],
            "coverage_resolved_y1": [float(baseline_one[resolved][resolved_labels == 1].mean())],
            "average_set_size": [float(cardinality.mean())],
            "singleton_share": [float((cardinality == 1).mean())],
            "set_empty_share": [float((cardinality == 0).mean())],
            "set_zero_only_share": [float((baseline_zero & ~baseline_one).mean())],
            "set_one_only_share": [float((~baseline_zero & baseline_one).mean())],
            "set_both_share": [float((baseline_zero & baseline_one).mean())],
            "mean_width": [float(np.mean(baseline_upper - baseline_lower))],
        }
    )
    baseline_coverage = pd.DataFrame(
        {
            "learner": ["test"],
            "window_id": ["w1"],
            "taxonomy_groups": [2],
            "role": ["primary_oot"],
            "conformal_group": [-1],
            "coverage_lower": [float((baseline_covered.sum() + unresolved_always.sum()) / 8)],
            "coverage_upper": [float((baseline_covered.sum() + 2 - unresolved_never.sum()) / 8)],
        }
    )
    evaluation, categories, strata, _ = evaluate_label_mondrian(
        scores,
        outcomes,
        {"test": {"w1": {2: recipe}}},
        thresholds,
        baseline_sets,
        baseline_coverage,
        learners=("test",),
        window_ids=("w1",),
        role="primary_oot",
        taxonomy_groups=2,
        expected_issue_months=("2016-04",),
        expected_candidates=8,
        expected_resolved=6,
        expected_unresolved=2,
        expected_resolved_y0=5,
        expected_resolved_y1=1,
    )
    assert len(categories) == 4
    assert len(strata) == 2
    hidden = categories.loc[categories["score_stratum"].eq(1) & categories["label"].eq(1)].iloc[0]
    assert hidden["coverage_resolved_label"] == pytest.approx(0.0)
    assert evaluation.loc[0, "coverage_resolved"] > hidden["coverage_resolved_label"]
    absent = categories.loc[categories["score_stratum"].eq(0) & categories["label"].eq(1)].iloc[0]
    assert not bool(absent["conditional_coverage_defined"])
    assert absent["identification_state_at_nominal"] == "undefined"
    assert (
        bool(strata.loc[strata["score_stratum"].eq(0), "conditional_gap_defined"].iloc[0]) is False
    )


def test_configs_lock_f1_and_hash_lock_e1_to_the_freeze_and_receipt() -> None:
    freeze = load_label_mondrian_config(FREEZE_CONFIG)
    learners, windows, groups, alpha = declared_grid(freeze)
    assert freeze["phase"] == "evaluation_outcome_free_threshold_freeze"
    assert freeze["protocol_tag"] == "protocol/ijds-label-mondrian-freeze-2026-07-21-v1"
    assert len(learners) == 5
    assert len(windows) == 8
    assert groups == 5
    assert alpha == pytest.approx(0.1)
    assert freeze["design"]["expected_threshold_cells"] == 400

    evaluation = load_label_mondrian_config(EVALUATION_CONFIG)
    assert evaluation["phase"] == "endpoint_evaluation_locked"
    assert evaluation["design"]["expected_target_category_cells"] == 400
    assert evaluation["design"]["expected_target_stratum_cells"] == 200
    assert evaluation["output"]["category_evaluation"].endswith(".parquet")
    assert evaluation["output"]["stratum_evaluation"].endswith(".parquet")
    require_locked_evaluation_source(evaluation)

    locked = deepcopy(evaluation)
    locked["source"]["label_mondrian_freeze_receipt"]["bytes"] = -1
    locked["source"]["label_mondrian_freeze_receipt"]["sha256"] = (
        "PENDING_AFTER_OUTCOME_FREE_FREEZE"
    )
    with pytest.raises(RuntimeError, match="still pending"):
        require_locked_evaluation_source(locked)


def test_protocol_predeclares_exact_ranks_sharp_ratios_gap_and_claim_boundaries() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for token in (
        "5 learners x 8 windows x 5 score strata x 2 labels = 400 thresholds",
        "q_gy = +infinity",
        "sharp class-specific ratio bounds",
        "subtracting those marginal intervals",
        "enumerates every integer",
        "selected-set or funded-set validity",
        "fairness claim",
    ):
        assert token in text
