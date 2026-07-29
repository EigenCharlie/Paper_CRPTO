"""Exact binary conformal phase geometry.

The counterexample tests encode conditions that an adversarial review showed are
required. They must keep failing for the wrong statements: the no-interleaving
condition alone does not place the threshold below one half, and the coverage
ceiling needs a target-support hypothesis.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.binary_phase_geometry import (
    HIGH_REGIME,
    LOW_REGIME,
    build_stratum_phase_table,
    coverage_change_between_thresholds,
    coverage_decomposition_evidence,
    finite_sample_rank,
    mirror_residuals,
    outcome_free_binary_set_bounds,
    phase_geometry_evidence,
    positive_coverable_exposure_share_of_total,
    reconcile_phase_table,
    sharp_coverage_change_bounds,
)

ALPHA = 0.10
PHASE_LEARNERS = ("catboost_platt",)
PHASE_WINDOWS = ("w01", "w02", "w03")


def _fit_frame(scores, labels, *, learner="l", window="w1", group=0, taxonomy=1):
    return pd.DataFrame(
        {
            "learner": learner,
            "window_id": window,
            "taxonomy_groups": taxonomy,
            "conformal_group": group,
            "pd_point": np.asarray(scores, dtype=float),
            "terminal_default": np.asarray(labels, dtype=float),
        }
    )


def _phase_evidence_inputs(
    tmp_path: Path,
    *,
    defaults_by_window: tuple[int, int, int] = (2, 2, 1),
    coverage_by_window: tuple[float, float, float] = (0.80, 0.82, 0.81),
    rows_per_group: int = 20,
) -> tuple[Path, pd.DataFrame]:
    """Create a complete three-window, three-stratum phase fixture."""
    windows = PHASE_WINDOWS
    blocks = []
    for window_index, window_id in enumerate(windows):
        for group in range(3):
            defaults = defaults_by_window[window_index] if group == 2 else min(2, rows_per_group)
            labels = [1.0] * defaults + [0.0] * (rows_per_group - defaults)
            blocks.append(
                _fit_frame(
                    [0.10] * rows_per_group,
                    labels,
                    learner="catboost_platt",
                    window=window_id,
                    group=group,
                    taxonomy=3,
                )
            )
    fit_audit = pd.concat(blocks, ignore_index=True)
    phase = build_stratum_phase_table(
        fit_audit,
        learners=["catboost_platt"],
        window_ids=list(windows),
        taxonomy_groups=3,
        alpha=ALPHA,
    )
    frozen = phase[
        [
            "learner",
            "window_id",
            "score_stratum",
            "fit_rows",
            "finite_sample_rank",
            "recomputed_threshold",
        ]
    ].rename(columns={"recomputed_threshold": "fit_residual_quantile"})
    coverage = dict(zip(windows, coverage_by_window, strict=True))
    frozen["coverage_resolved"] = frozen["window_id"].map(coverage)
    path = tmp_path / "residual_fit_audit.parquet"
    fit_audit.to_parquet(path, index=False)
    return path, frozen


def _coverage_decomposition_table() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "coverage_resolved_y0": [0.96, 0.95],
            "coverage_resolved_y1": [0.60, 0.55],
            "resolved_y0_rows": [80, 80],
            "resolved_y1_rows": [20, 20],
        }
    )
    prevalence = frame["resolved_y1_rows"] / (frame["resolved_y0_rows"] + frame["resolved_y1_rows"])
    frame["coverage_resolved"] = (1.0 - prevalence) * frame[
        "coverage_resolved_y0"
    ] + prevalence * frame["coverage_resolved_y1"]
    return frame


def test_rank_matches_split_conformal_convention():
    assert finite_sample_rank(19, alpha=ALPHA) == math.ceil(20 * 0.9)
    assert finite_sample_rank(6238, alpha=ALPHA) == 5616
    with pytest.raises(ValueError):
        finite_sample_rank(0, alpha=ALPHA)
    with pytest.raises(ValueError):
        finite_sample_rank(10, alpha=1.0)


def test_capped_rank_has_no_phase_regime_before_the_fail_closed_stop():
    table = build_stratum_phase_table(
        _fit_frame([0.2], [0.0]),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    row = table.iloc[0]
    assert row["finite_sample_rank"] == 2
    assert row["recomputed_threshold"] == pytest.approx(1.0)
    assert bool(row["threshold_is_capped"])
    assert pd.isna(row["regime"])


def test_mirror_residuals_are_the_two_mirror_samples():
    scores = np.array([0.1, 0.2, 0.3])
    labels = np.array([0.0, 1.0, 0.0])
    np.testing.assert_allclose(mirror_residuals(scores, labels), [0.1, 0.8, 0.3])


def test_mirror_residuals_reject_scores_outside_the_unit_interval():
    with pytest.raises(ValueError, match="scores in"):
        mirror_residuals(np.array([1.5, 2.4]), np.array([0.0, 0.0]))


def test_threshold_is_the_kth_order_statistic_of_the_mirror_multiset():
    rng = np.random.default_rng(11)
    scores = rng.uniform(0.01, 0.45, size=400)
    labels = (rng.uniform(size=400) < 0.2).astype(float)
    table = build_stratum_phase_table(
        _fit_frame(scores, labels),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    rank = finite_sample_rank(400, alpha=ALPHA)
    expected = float(np.sort(np.abs(labels - scores))[rank - 1])
    assert table.loc[0, "recomputed_threshold"] == pytest.approx(expected, abs=0.0)


def test_boundary_has_the_exact_closed_form():
    rng = np.random.default_rng(5)
    for count in (37, 128, 1626, 6238):
        scores = rng.uniform(0.01, 0.4, size=count)
        labels = (rng.uniform(size=count) < 0.15).astype(float)
        table = build_stratum_phase_table(
            _fit_frame(scores, labels),
            learners=["l"],
            window_ids=["w1"],
            taxonomy_groups=1,
            alpha=ALPHA,
        )
        row = table.iloc[0]
        assert row["boundary_count"] == row["boundary_closed_form"]
        assert row["boundary_count"] == math.floor(ALPHA * (count + 1)) - 1


def test_margin_predicts_the_regime_when_every_score_is_below_one_half():
    rng = np.random.default_rng(3)
    for prevalence in (0.02, 0.08, 0.10, 0.12, 0.30):
        scores = rng.uniform(0.01, 0.49, size=500)
        labels = (rng.uniform(size=500) < prevalence).astype(float)
        table = build_stratum_phase_table(
            _fit_frame(scores, labels),
            learners=["l"],
            window_ids=["w1"],
            taxonomy_groups=1,
            alpha=ALPHA,
        )
        row = table.iloc[0]
        assert row["separation_below_half"]
        assert bool(row["margin_predicts_low"]) == bool(row["threshold_below_half"])


def test_no_interleaving_alone_does_not_place_the_threshold_below_one_half():
    """Counterexample A: (S) holds and D <= n-k, yet the threshold is above 1/2."""
    scores = np.array([0.10] * 18 + [0.70, 0.20])
    labels = np.array([0.0] * 19 + [1.0])
    table = build_stratum_phase_table(
        _fit_frame(scores, labels),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    row = table.iloc[0]
    assert row["fit_rows"] == 20
    assert row["finite_sample_rank"] == 19
    assert row["boundary_count"] == 1
    assert row["fit_defaults"] == 1
    assert row["separation_no_interleave"]  # 0.70 + 0.20 < 1
    assert not row["separation_below_half"]  # 0.70 >= 0.5
    assert row["margin_predicts_low"]  # D = 1 <= n - k = 1
    assert row["recomputed_threshold"] == pytest.approx(0.70)
    assert row["regime"] == HIGH_REGIME  # the margin criterion is wrong here
    assert not row["threshold_below_half"]


def test_interleaving_can_invert_the_margin_criterion():
    """Counterexample B: (S) fails and the threshold is below 1/2 while D > n-k."""
    scores = np.array([0.05] * 9 + [0.99])
    labels = np.array([0.0] * 9 + [1.0])
    table = build_stratum_phase_table(
        _fit_frame(scores, labels),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    row = table.iloc[0]
    assert row["finite_sample_rank"] == 10
    assert row["boundary_count"] == 0
    assert not row["separation_no_interleave"]
    assert row["recomputed_threshold"] == pytest.approx(0.05)
    assert row["threshold_below_half"]
    assert not row["margin_predicts_low"]  # D = 1 > n - k = 0


def test_exact_half_criterion_holds_even_when_separation_fails():
    """A + B >= k characterizes c < 1/2 with no separation hypothesis at all."""
    rng = np.random.default_rng(17)
    for _ in range(25):
        size = int(rng.integers(30, 300))
        scores = rng.uniform(0.01, 0.99, size=size)
        labels = (rng.uniform(size=size) < 0.35).astype(float)
        table = build_stratum_phase_table(
            _fit_frame(scores, labels),
            learners=["l"],
            window_ids=["w1"],
            taxonomy_groups=1,
            alpha=ALPHA,
        )
        row = table.iloc[0]
        assert bool(row["exact_half_criterion"]) == bool(row["threshold_below_half"])


def test_low_regime_arises_when_within_stratum_prevalence_sits_below_alpha():
    rng = np.random.default_rng(23)
    scores = rng.uniform(0.01, 0.20, size=2000)
    labels = (rng.uniform(size=2000) < 0.04).astype(float)
    table = build_stratum_phase_table(
        _fit_frame(scores, labels),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    row = table.iloc[0]
    assert row["fit_prevalence"] < ALPHA
    assert row["regime"] == LOW_REGIME
    assert row["recomputed_threshold"] < 0.5


def test_score_bins_do_not_guarantee_a_low_regime():
    """Perfect finite-bin calibration above alpha leaves every score bin high."""
    blocks = []
    for group, score in enumerate((0.20, 0.21, 0.22, 0.23, 0.24)):
        rows = 100
        defaults = int(round(score * rows))
        blocks.append(
            _fit_frame(
                [score] * rows,
                [1.0] * defaults + [0.0] * (rows - defaults),
                group=group,
                taxonomy=5,
            )
        )
    table = build_stratum_phase_table(
        pd.concat(blocks, ignore_index=True),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=5,
        alpha=ALPHA,
    )
    assert table["fit_prevalence"].is_monotonic_increasing
    assert table["fit_prevalence"].tolist() == pytest.approx([0.20, 0.21, 0.22, 0.23, 0.24])
    assert table["regime"].eq(HIGH_REGIME).all()


def test_margin_zero_and_one_belong_to_different_calibration_blocks():
    block_m0 = _fit_frame(
        [0.01] * 18 + [0.49, 0.01],
        [0.0] * 19 + [1.0],
        window="w0",
    )
    block_m1 = _fit_frame(
        [0.01] * 17 + [0.10, 0.49, 0.01],
        [0.0] * 18 + [1.0, 1.0],
        window="w1",
    )
    table = build_stratum_phase_table(
        pd.concat([block_m0, block_m1], ignore_index=True),
        learners=["l"],
        window_ids=["w0", "w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    ).set_index("window_id")
    assert table.loc["w0", "phase_margin"] == 0
    assert table.loc["w0", "recomputed_threshold"] == pytest.approx(0.49)
    assert table.loc["w1", "phase_margin"] == 1
    assert table.loc["w1", "recomputed_threshold"] == pytest.approx(0.51)


def test_phase_table_requires_every_declared_cell():
    frame = _fit_frame([0.1, 0.2, 0.3], [0.0, 0.0, 1.0])
    with pytest.raises(RuntimeError, match="window domain"):
        build_stratum_phase_table(
            frame, learners=["l"], window_ids=["w1", "w2"], taxonomy_groups=1, alpha=ALPHA
        )


def test_phase_table_rejects_fractional_conformal_group_before_cast():
    frame = _fit_frame([0.1, 0.2], [0.0, 1.0], group=0.5)
    with pytest.raises(ValueError, match="conformal_group keys must contain finite integers"):
        build_stratum_phase_table(
            frame,
            learners=["l"],
            window_ids=["w1"],
            taxonomy_groups=1,
            alpha=ALPHA,
        )


def test_phase_table_rejects_fractional_taxonomy_key_before_cast():
    frame = _fit_frame([0.1, 0.2], [0.0, 1.0], taxonomy=1.5)
    with pytest.raises(ValueError, match="taxonomy_groups must contain finite integers"):
        build_stratum_phase_table(
            frame,
            learners=["l"],
            window_ids=["w1"],
            taxonomy_groups=1,
            alpha=ALPHA,
        )


def test_phase_table_rejects_a_missing_column():
    frame = _fit_frame([0.1, 0.2], [0.0, 1.0]).drop(columns="terminal_default")
    with pytest.raises(ValueError, match="omits columns"):
        build_stratum_phase_table(
            frame, learners=["l"], window_ids=["w1"], taxonomy_groups=1, alpha=ALPHA
        )


def test_reconciliation_detects_a_drifted_frozen_threshold():
    scores = np.linspace(0.01, 0.40, 200)
    labels = np.zeros(200)
    labels[:5] = 1.0
    table = build_stratum_phase_table(
        _fit_frame(scores, labels),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    frozen = pd.DataFrame(
        {
            "learner": ["l"],
            "window_id": ["w1"],
            "score_stratum": [1],
            "fit_rows": [200],
            "finite_sample_rank": [table.loc[0, "finite_sample_rank"]],
            "fit_residual_quantile": [table.loc[0, "recomputed_threshold"]],
        }
    )
    clean = reconcile_phase_table(table, frozen)
    assert bool(clean.loc[0, "threshold_reconciles"])
    assert bool(clean.loc[0, "rows_reconcile"])
    assert bool(clean.loc[0, "rank_reconciles"])

    drifted = frozen.assign(fit_residual_quantile=frozen["fit_residual_quantile"] + 1e-6)
    assert not bool(reconcile_phase_table(table, drifted).loc[0, "threshold_reconciles"])


def test_reconciliation_rejects_fractional_score_stratum_before_cast():
    table = build_stratum_phase_table(
        _fit_frame([0.1, 0.2], [0.0, 1.0]),
        learners=["l"],
        window_ids=["w1"],
        taxonomy_groups=1,
        alpha=ALPHA,
    )
    frozen = pd.DataFrame(
        {
            "learner": ["l"],
            "window_id": ["w1"],
            "score_stratum": [1.5],
            "fit_rows": [2],
            "finite_sample_rank": [table.loc[0, "finite_sample_rank"]],
            "fit_residual_quantile": [table.loc[0, "recomputed_threshold"]],
        }
    )
    with pytest.raises(ValueError, match="score_stratum keys must contain finite integers"):
        reconcile_phase_table(table, frozen)


def test_coverage_change_uses_the_correct_closed_and_open_boundaries():
    scores = np.array([0.125, 0.375])
    labels = np.array([0.0, 1.0])
    result = coverage_change_between_thresholds(
        target_scores=scores,
        target_labels=labels,
        lower_threshold=0.25,
        upper_threshold=0.625,
    )
    assert result["default_crossing_mass"] == pytest.approx(1.0)
    assert result["coverage_change"] == pytest.approx(0.5)


def test_coverage_change_rejects_reversed_thresholds():
    scores = np.array([0.1, 0.2])
    labels = np.array([0.0, 1.0])
    with pytest.raises(ValueError, match="lower <= upper"):
        coverage_change_between_thresholds(
            target_scores=scores,
            target_labels=labels,
            lower_threshold=0.6,
            upper_threshold=0.5,
        )


@pytest.mark.parametrize("score", [float("nan"), float("inf"), float("-inf")])
def test_coverage_change_rejects_nonfinite_scores(score: float):
    with pytest.raises(ValueError, match="finite"):
        coverage_change_between_thresholds(
            target_scores=np.array([0.1, score]),
            target_labels=np.array([0.0, 1.0]),
            lower_threshold=0.2,
            upper_threshold=0.4,
        )


def test_coverage_change_equals_target_mass_between_threshold_boundaries():
    scores = np.array([0.10, 0.40, 0.60, 0.70])
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    result = coverage_change_between_thresholds(
        target_scores=scores,
        target_labels=labels,
        lower_threshold=0.30,
        upper_threshold=0.60,
    )
    assert result["nondefault_crossing_mass"] == pytest.approx(0.5)
    assert result["default_crossing_mass"] == pytest.approx(0.5)
    assert result["coverage_change"] == pytest.approx(0.5)


def test_coverage_can_jump_from_zero_to_one_with_varying_scores():
    result = coverage_change_between_thresholds(
        target_scores=np.array([0.4, 0.5]),
        target_labels=np.array([0.0, 1.0]),
        lower_threshold=0.2,
        upper_threshold=0.7,
    )
    assert result["coverage_change"] == pytest.approx(1.0)


def test_sharp_coverage_change_bounds_assign_each_unresolved_label_once():
    result = sharp_coverage_change_bounds(
        target_scores=np.array([0.10, 0.40]),
        target_labels=np.array([np.nan, 1.0]),
        lower_threshold=0.05,
        upper_threshold=0.20,
        weights=np.array([3.0, 1.0]),
    )
    assert result["coverage_change_lower"] == pytest.approx(0.0)
    assert result["coverage_change_upper"] == pytest.approx(0.75)


def test_outcome_free_bounds_use_empty_and_both_sets():
    allocations = pd.DataFrame(
        {
            "exposure": [100.0, 300.0, 600.0, 1000.0],
            "conformal_lower": [0.0, 0.05, 0.0, 0.6],
            "conformal_upper": [1.0, 0.95, 0.4, 1.0],
        }
    )
    result = outcome_free_binary_set_bounds(allocations)
    assert result["outcome_free_miscoverage_lower"] == pytest.approx(0.15)
    assert result["outcome_free_miscoverage_upper"] == pytest.approx(0.95)
    assert result["outcome_free_coverage_lower"] == pytest.approx(0.05)
    assert result["outcome_free_coverage_upper"] == pytest.approx(0.85)
    assert result["funded_exposure"] == pytest.approx(2000.0)


def test_positive_lower_endpoint_alone_is_not_an_outcome_free_miss():
    """Counterexample to the retired lower-endpoint-only floor."""
    allocations = pd.DataFrame(
        {
            "exposure": [100.0],
            "conformal_lower": [0.6],
            "conformal_upper": [1.0],
        }
    )
    result = outcome_free_binary_set_bounds(allocations)
    assert result["outcome_free_miscoverage_lower"] == pytest.approx(0.0)
    assert result["outcome_free_coverage_upper"] == pytest.approx(1.0)


def test_outcome_free_bounds_do_not_snap_near_endpoints():
    allocations = pd.DataFrame(
        {
            "exposure": [1.0, 1.0, 1.0],
            "conformal_lower": [0.2, 5.0e-13, 0.0],
            "conformal_upper": [1.0 - 5.0e-13, 1.0, 1.0],
        }
    )
    result = outcome_free_binary_set_bounds(allocations)
    assert result["empty_set_exposure"] == pytest.approx(1.0)
    assert result["both_set_exposure"] == pytest.approx(1.0)
    assert result["outcome_free_miscoverage_lower"] == pytest.approx(1.0 / 3.0)
    assert result["outcome_free_miscoverage_upper"] == pytest.approx(2.0 / 3.0)


def test_outcome_free_bounds_clip_only_out_of_range_numerical_excursions():
    allocations = pd.DataFrame(
        {
            "exposure": [1.0],
            "conformal_lower": [-5.0e-13],
            "conformal_upper": [1.0 + 5.0e-13],
        }
    )
    result = outcome_free_binary_set_bounds(allocations)
    assert result["both_set_exposure"] == pytest.approx(1.0)
    assert result["empty_set_exposure"] == pytest.approx(0.0)


def test_outcome_free_bounds_reject_negative_exposure():
    allocations = pd.DataFrame(
        {"exposure": [-1.0], "conformal_lower": [0.0], "conformal_upper": [1.0]}
    )
    with pytest.raises(ValueError, match="nonnegative"):
        outcome_free_binary_set_bounds(allocations)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("conformal_lower", -1.0e-3),
        ("conformal_lower", 1.001),
        ("conformal_upper", -1.0e-3),
        ("conformal_upper", 1.001),
    ],
)
def test_outcome_free_bounds_reject_endpoints_outside_repair_margin(
    column: str,
    value: float,
):
    allocations = pd.DataFrame(
        {"exposure": [1.0], "conformal_lower": [0.0], "conformal_upper": [1.0]}
    )
    allocations.loc[0, column] = value
    with pytest.raises(ValueError, match=r"inside \[0, 1\]"):
        outcome_free_binary_set_bounds(allocations)


@pytest.mark.parametrize("tolerance", [-1.0, float("nan"), float("inf")])
def test_outcome_free_bounds_reject_invalid_endpoint_tolerance(tolerance: float):
    allocations = pd.DataFrame(
        {"exposure": [1.0], "conformal_lower": [0.0], "conformal_upper": [1.0]}
    )
    with pytest.raises(ValueError, match="finite and nonnegative"):
        outcome_free_binary_set_bounds(allocations, tolerance=tolerance)


def test_outcome_free_bounds_are_sharp_over_all_binary_completions():
    allocations = pd.DataFrame(
        {
            "exposure": [1.0, 2.0, 3.0, 4.0],
            "conformal_lower": [0.2, 0.0, 0.2, 0.0],
            "conformal_upper": [0.8, 0.8, 1.0, 1.0],
        }
    )
    result = outcome_free_binary_set_bounds(allocations)
    misses = []
    for code in range(16):
        labels = np.array([(code >> index) & 1 for index in range(4)], dtype=float)
        lower = allocations["conformal_lower"].to_numpy()
        upper = allocations["conformal_upper"].to_numpy()
        miss = ((labels == 0.0) & (lower > 0.0)) | ((labels == 1.0) & (upper < 1.0))
        misses.append(float((allocations["exposure"].to_numpy() * miss).sum() / 10.0))
    assert min(misses) == pytest.approx(result["outcome_free_miscoverage_lower"])
    assert max(misses) == pytest.approx(result["outcome_free_miscoverage_upper"])
    assert min(misses) == pytest.approx(0.1)
    assert max(misses) == pytest.approx(0.6)


def test_positive_coverable_share_is_normalized_by_total_exposure_only():
    allocations = pd.DataFrame(
        {
            "exposure": [250.0, 250.0, 500.0],
            "conformal_upper": [1.0, 0.9999, 0.4],
        }
    )
    result = positive_coverable_exposure_share_of_total(allocations)
    assert result["positive_coverable_exposure_share_of_total"] == pytest.approx(0.25)


def test_positive_coverable_share_requires_an_exact_saturated_endpoint():
    allocations = pd.DataFrame(
        {
            "exposure": [1.0, 1.0],
            "conformal_upper": [1.0, 1.0 - 5.0e-13],
        }
    )
    result = positive_coverable_exposure_share_of_total(allocations)
    assert result["positive_coverable_exposure"] == pytest.approx(1.0)
    assert result["positive_coverable_exposure_share_of_total"] == pytest.approx(0.5)


def test_positive_coverable_share_clips_only_an_out_of_range_excursion():
    allocations = pd.DataFrame({"exposure": [1.0], "conformal_upper": [1.0 + 5.0e-13]})
    result = positive_coverable_exposure_share_of_total(allocations)
    assert result["positive_coverable_exposure_share_of_total"] == pytest.approx(1.0)


@pytest.mark.parametrize("upper", [-1.0e-3, 1.001])
def test_positive_coverable_share_rejects_endpoints_outside_repair_margin(upper: float):
    allocations = pd.DataFrame({"exposure": [1.0], "conformal_upper": [upper]})
    with pytest.raises(ValueError, match=r"inside \[0, 1\]"):
        positive_coverable_exposure_share_of_total(allocations)


def test_positive_coverable_share_is_not_conditional_positive_coverage():
    allocations = pd.DataFrame(
        {
            "exposure": [1.0, 3.0],
            "conformal_upper": [1.0, 0.4],
        }
    )
    result = positive_coverable_exposure_share_of_total(allocations)
    assert result["positive_coverable_exposure_share_of_total"] == pytest.approx(0.25)
    # If only the first unit realizes Y=1, conditional positive coverage is one.
    conditional_positive_coverage = 1.0 / 1.0
    assert conditional_positive_coverage > result["positive_coverable_exposure_share_of_total"]


@pytest.mark.parametrize("tolerance", [-1.0, float("nan"), float("inf")])
def test_positive_coverable_share_rejects_invalid_endpoint_tolerance(tolerance: float):
    allocations = pd.DataFrame({"exposure": [1.0], "conformal_upper": [1.0]})
    with pytest.raises(ValueError, match="finite and nonnegative"):
        positive_coverable_exposure_share_of_total(allocations, tolerance=tolerance)


def test_phase_evidence_returns_the_complete_declared_result(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)

    evidence, publication = phase_geometry_evidence(
        fit_audit_path=fit_path,
        frozen_strata=frozen,
        expected_learners=PHASE_LEARNERS,
        expected_window_ids=PHASE_WINDOWS,
        taxonomy_groups=3,
    )
    assert evidence["strata"] == 9
    assert evidence["threshold_reconciles_all_strata"] is True
    assert evidence["strata_with_a_capped_threshold"] == 0
    assert evidence["crossing_threshold_change"] == pytest.approx(-0.8)
    assert evidence["crossing_coverage_change"] == pytest.approx(-0.01)
    assert evidence["adjacent_noncrossing_coverage_change"] == pytest.approx(0.02)
    assert evidence["coverage_first_differences"] == pytest.approx([0.02, -0.01])
    assert {
        "count_nondefault_below_half",
        "count_default_above_half",
        "exact_half_criterion",
        "threshold_is_capped",
        "boundary_closed_form",
        "separation_no_interleave",
        "separation_below_half",
        "fit_score_max_nondefault",
        "fit_score_max_default",
    }.issubset(publication.columns)
    assert "was inspected retrospectively" in evidence["claim_boundary"]
    assert "crossing was not predeclared" in evidence["claim_boundary"]
    assert "predeclared portfolio learner" not in evidence["claim_boundary"]


@pytest.mark.parametrize(
    ("expected_learners", "expected_windows", "message"),
    [
        (
            (*PHASE_LEARNERS, "numeric_logistic_platt"),
            PHASE_WINDOWS,
            "frozen learner domain",
        ),
        (PHASE_LEARNERS, (*PHASE_WINDOWS, "w04"), "frozen window domain"),
    ],
)
def test_phase_evidence_rejects_an_entire_missing_declared_domain(
    tmp_path: Path,
    expected_learners: tuple[str, ...],
    expected_windows: tuple[str, ...],
    message: str,
):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    with pytest.raises(RuntimeError, match=message):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=expected_learners,
            expected_window_ids=expected_windows,
            taxonomy_groups=3,
        )


@pytest.mark.parametrize("domain", ["learner", "window"])
def test_phase_evidence_rejects_an_entire_missing_fit_audit_domain(
    tmp_path: Path,
    domain: str,
):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    expected_learners: tuple[str, ...]
    expected_windows: tuple[str, ...]
    if domain == "learner":
        extra = frozen.assign(learner="numeric_logistic_platt")
        complete_frozen = pd.concat([frozen, extra], ignore_index=True)
        expected_learners = (*PHASE_LEARNERS, "numeric_logistic_platt")
        expected_windows = PHASE_WINDOWS
    else:
        extra = frozen.loc[frozen["window_id"].eq(PHASE_WINDOWS[-1])].assign(window_id="w04")
        complete_frozen = pd.concat([frozen, extra], ignore_index=True)
        expected_learners = PHASE_LEARNERS
        expected_windows = (*PHASE_WINDOWS, "w04")

    with pytest.raises(RuntimeError, match=rf"residual-fit {domain} domain"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=complete_frozen,
            expected_learners=expected_learners,
            expected_window_ids=expected_windows,
            taxonomy_groups=3,
        )


def test_phase_evidence_rejects_a_fractional_frozen_key_before_cast(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    frozen["score_stratum"] = frozen["score_stratum"].astype(float)
    frozen.loc[0, "score_stratum"] = 1.5
    with pytest.raises(ValueError, match="score_stratum keys must contain finite integers"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


@pytest.mark.parametrize(
    ("column", "delta", "message"),
    [
        ("fit_residual_quantile", 1.0e-4, "threshold left"),
        ("fit_rows", 1, "counts or ranks"),
        ("finite_sample_rank", 1, "counts or ranks"),
    ],
)
def test_phase_evidence_fails_closed_on_frozen_reconciliation_drift(
    tmp_path: Path,
    column: str,
    delta: float,
    message: str,
):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    frozen.loc[0, column] += delta

    with pytest.raises(RuntimeError, match=message):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


def test_phase_evidence_fails_closed_on_above_threshold_count_drift(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    frozen["fit_residual_above_threshold"] = frozen["fit_rows"] - frozen["finite_sample_rank"]
    frozen.loc[0, "fit_residual_above_threshold"] += 1

    with pytest.raises(RuntimeError, match="residual count above"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


def test_phase_evidence_fails_closed_on_capped_rank(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(
        tmp_path,
        defaults_by_window=(0, 0, 0),
        rows_per_group=1,
    )

    with pytest.raises(RuntimeError, match="degenerate rank>n"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


@pytest.mark.parametrize(
    ("defaults_by_window", "transition_count"),
    [
        ((2, 2, 2), 0),
        ((2, 1, 2), 2),
    ],
)
def test_phase_evidence_fails_closed_on_zero_or_multiple_transitions(
    tmp_path: Path,
    defaults_by_window: tuple[int, int, int],
    transition_count: int,
):
    fit_path, frozen = _phase_evidence_inputs(
        tmp_path,
        defaults_by_window=defaults_by_window,
    )

    with pytest.raises(RuntimeError, match=rf"{transition_count} transitions detected"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


def test_phase_evidence_requires_an_adjacent_earlier_step(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(
        tmp_path,
        defaults_by_window=(2, 1, 1),
    )

    with pytest.raises(RuntimeError, match="no adjacent earlier step"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


def test_phase_evidence_rejects_duplicate_or_incomplete_frozen_keys(tmp_path: Path):
    fit_path, frozen = _phase_evidence_inputs(tmp_path)
    duplicated = pd.concat([frozen, frozen.iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="duplicated stratum key"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=duplicated,
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )

    with pytest.raises(RuntimeError, match="censuses differ"):
        phase_geometry_evidence(
            fit_audit_path=fit_path,
            frozen_strata=frozen.iloc[:-1],
            expected_learners=PHASE_LEARNERS,
            expected_window_ids=PHASE_WINDOWS,
            taxonomy_groups=3,
        )


def test_coverage_decomposition_reconciles_the_mixture_identity():
    table = _coverage_decomposition_table()
    result = coverage_decomposition_evidence(
        table,
        prevalence_lower=0.18,
        prevalence_upper=0.25,
    )
    assert result["cells"] == 2
    assert result["mixture_identity_max_abs_residual"] == pytest.approx(0.0)
    assert result["resolved_prevalence"] == pytest.approx(0.2)
    assert result["all_candidate_prevalence_bound"] == pytest.approx([0.18, 0.25])


def test_coverage_decomposition_fails_closed_on_mixture_identity_drift():
    table = _coverage_decomposition_table()
    table.loc[0, "coverage_resolved"] += 1.0e-4

    with pytest.raises(RuntimeError, match="mixture identity"):
        coverage_decomposition_evidence(
            table,
            prevalence_lower=0.18,
            prevalence_upper=0.25,
        )


def test_coverage_decomposition_fails_closed_on_nonunique_prevalence():
    table = _coverage_decomposition_table()
    table.loc[1, ["resolved_y0_rows", "resolved_y1_rows"]] = [70, 30]
    prevalence = table.loc[1, "resolved_y1_rows"] / (
        table.loc[1, "resolved_y0_rows"] + table.loc[1, "resolved_y1_rows"]
    )
    table.loc[1, "coverage_resolved"] = (1.0 - prevalence) * table.loc[
        1, "coverage_resolved_y0"
    ] + prevalence * table.loc[1, "coverage_resolved_y1"]

    with pytest.raises(RuntimeError, match="prevalence varies"):
        coverage_decomposition_evidence(
            table,
            prevalence_lower=0.18,
            prevalence_upper=0.35,
        )


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("resolved_y0_rows", 0),
        ("resolved_y1_rows", 0),
        ("resolved_y0_rows", -1),
        ("resolved_y1_rows", 1.5),
    ],
)
def test_coverage_decomposition_rejects_invalid_class_denominators(
    column: str,
    value: float,
):
    table = _coverage_decomposition_table()
    table[column] = table[column].astype(float)
    table.loc[0, column] = value

    with pytest.raises(RuntimeError, match="denominator must be a positive integer"):
        coverage_decomposition_evidence(
            table,
            prevalence_lower=0.0,
            prevalence_upper=1.0,
        )


def test_coverage_decomposition_rejects_a_zero_breakeven_denominator():
    table = _coverage_decomposition_table()
    table["coverage_resolved_y1"] = table["coverage_resolved_y0"]
    prevalence = table["resolved_y1_rows"] / (table["resolved_y0_rows"] + table["resolved_y1_rows"])
    table["coverage_resolved"] = (1.0 - prevalence) * table[
        "coverage_resolved_y0"
    ] + prevalence * table["coverage_resolved_y1"]

    with pytest.raises(RuntimeError, match="breakeven denominator"):
        coverage_decomposition_evidence(
            table,
            prevalence_lower=0.18,
            prevalence_upper=0.25,
        )


@pytest.mark.parametrize(
    ("coverage_y0", "coverage_y1"),
    [(0.85, 0.60), (0.99, 0.95)],
)
def test_coverage_decomposition_rejects_an_unattainable_breakeven(
    coverage_y0: float,
    coverage_y1: float,
):
    table = _coverage_decomposition_table()
    table.loc[0, "coverage_resolved_y0"] = coverage_y0
    table.loc[0, "coverage_resolved_y1"] = coverage_y1
    prevalence = table.loc[0, "resolved_y1_rows"] / (
        table.loc[0, "resolved_y0_rows"] + table.loc[0, "resolved_y1_rows"]
    )
    table.loc[0, "coverage_resolved"] = (1.0 - prevalence) * table.loc[
        0, "coverage_resolved_y0"
    ] + prevalence * table.loc[0, "coverage_resolved_y1"]

    with pytest.raises(RuntimeError, match=r"outside \[0, 1\]"):
        coverage_decomposition_evidence(
            table,
            prevalence_lower=0.18,
            prevalence_upper=0.25,
        )


@pytest.mark.parametrize(
    ("lower", "upper"),
    [
        (-0.1, 0.2),
        (0.3, 0.2),
        (0.2, 1.1),
        (float("nan"), 0.2),
    ],
)
def test_coverage_decomposition_rejects_invalid_prevalence_bounds(
    lower: float,
    upper: float,
):
    with pytest.raises(ValueError, match="Prevalence bounds"):
        coverage_decomposition_evidence(
            _coverage_decomposition_table(),
            prevalence_lower=lower,
            prevalence_upper=upper,
        )
