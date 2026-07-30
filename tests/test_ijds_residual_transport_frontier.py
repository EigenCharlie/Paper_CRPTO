from __future__ import annotations

from copy import deepcopy
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.residual_transport_frontier import (
    build_residual_transport_frontier,
    completion_directional_ks_frontier,
    directional_ks,
)
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    assign_conformal_groups,
)

LEARNERS = tuple(f"learner_{index}" for index in range(5))
WINDOWS = tuple(f"window_{index}" for index in range(8))
MONTHS = tuple(str(value) for value in pd.period_range("2016-04", "2017-06", freq="M"))
EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
FIT_POINTS = (0.125, 0.25, 0.50, 0.75, 0.875)
FIT_LABELS = (0.0, 0.0, 0.0, 1.0, 1.0)
QUANTILES = (0.125, 0.25, 0.50, 0.25, 0.125)


def _recipe(learner: str) -> BinaryOutcomeConformalRecipe:
    return BinaryOutcomeConformalRecipe(
        alpha=0.10,
        requested_groups=5,
        bin_edges=EDGES,
        residual_quantiles=QUANTILES,
        group_counts=(10, 10, 10, 10, 10),
        finite_sample_ranks=(10, 10, 10, 10, 10),
        raw_finite_sample_ranks=(10, 10, 10, 10, 10),
        method="fixed_taxonomy_split_mondrian_absolute_residual",
        taxonomy_provenance=f"{learner}_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )


def _recipes() -> dict[str, dict[str, dict[int, BinaryOutcomeConformalRecipe]]]:
    return {learner: {window: {5: _recipe(learner)} for window in WINDOWS} for learner in LEARNERS}


def _fit_audit() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for learner in LEARNERS:
        for window in WINDOWS:
            for group, (point, label, threshold) in enumerate(
                zip(FIT_POINTS, FIT_LABELS, QUANTILES, strict=True)
            ):
                lower = float(np.clip(point - threshold, 0.0, 1.0))
                upper = float(np.clip(point + threshold, 0.0, 1.0))
                for index in range(10):
                    rows.append(
                        {
                            "id": f"fit-{learner}-{window}-{group}-{index}",
                            "issue_d": "2012-01-15",
                            "learner": learner,
                            "window_id": window,
                            "taxonomy_groups": 5,
                            "conformal_group": group,
                            "pd_point": point,
                            "conformal_lower": lower,
                            "conformal_upper": upper,
                            "terminal_default": label,
                            "covered": True,
                        }
                    )
    return pd.DataFrame(rows)


def _target() -> tuple[pd.DataFrame, pd.DataFrame]:
    ids: list[str] = []
    dates: list[str] = []
    probabilities: list[float] = []
    labels: list[float] = []
    for month_index, month in enumerate(MONTHS):
        for group, center in enumerate(FIT_POINTS):
            for status, offset in (("resolved", -0.025), ("unresolved", 0.025)):
                ids.append(f"{month}-{group}-{status}")
                dates.append(f"{month}-15")
                probabilities.append(center + offset)
                if status == "unresolved":
                    labels.append(np.nan)
                else:
                    labels.append(float((group + month_index) % 3 == 0))
    scores = pd.DataFrame(
        {
            "id": ids,
            "issue_d": dates,
            "design_split": ["evaluation"] * len(ids),
            **{f"pd_{learner}": probabilities for learner in LEARNERS},
        }
    )
    outcomes = pd.DataFrame({"id": ids, "snapshot_default": labels})
    return scores, outcomes


def _reference(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    fit_audit: pd.DataFrame,
) -> pd.DataFrame:
    panel = scores.merge(outcomes, on="id", validate="one_to_one")
    labels = panel["snapshot_default"].to_numpy(dtype=float)
    resolved = np.isfinite(labels)
    rows: list[dict[str, Any]] = []
    for learner in LEARNERS:
        probability = panel[f"pd_{learner}"].to_numpy(dtype=float)
        groups = assign_conformal_groups(probability, EDGES)
        for window in WINDOWS:
            for group, threshold in enumerate(QUANTILES):
                mask = groups == group
                cell_probability = probability[mask]
                cell_labels = labels[mask]
                cell_resolved = resolved[mask]
                resolved_residual = np.abs(
                    cell_labels[cell_resolved] - cell_probability[cell_resolved]
                )
                unresolved_probability = cell_probability[~cell_resolved]
                miss_zero = unresolved_probability > threshold
                miss_one = 1.0 - unresolved_probability > threshold
                resolved_misses = int(np.sum(resolved_residual > threshold))
                misses_min = resolved_misses + int(np.sum(np.minimum(miss_zero, miss_one)))
                misses_max = resolved_misses + int(np.sum(np.maximum(miss_zero, miss_one)))
                candidate_rows = int(mask.sum())
                resolved_rows = int(cell_resolved.sum())
                fit_block = fit_audit.loc[
                    fit_audit["learner"].eq(learner)
                    & fit_audit["window_id"].eq(window)
                    & fit_audit["conformal_group"].eq(group)
                ]
                rows.append(
                    {
                        "learner": learner,
                        "window_id": window,
                        "taxonomy_groups": 5,
                        "conformal_group": group,
                        "role": "evaluation",
                        "candidate_rows": candidate_rows,
                        "resolved_rows": resolved_rows,
                        "unresolved_rows": candidate_rows - resolved_rows,
                        "resolved_misses": resolved_misses,
                        "misses_min": misses_min,
                        "misses_max": misses_max,
                        "coverage_resolved": 1.0 - resolved_misses / resolved_rows,
                        "coverage_lower": 1.0 - misses_max / candidate_rows,
                        "coverage_upper": 1.0 - misses_min / candidate_rows,
                        "score_min": float(cell_probability.min()),
                        "score_max": float(cell_probability.max()),
                        "fit_rows": int(len(fit_block)),
                        "fit_residual_quantile": threshold,
                        "fit_score_min": float(fit_block["pd_point"].min()),
                        "fit_score_max": float(fit_block["pd_point"].max()),
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fixed_case() -> dict[str, Any]:
    scores, outcomes = _target()
    fit_audit = _fit_audit()
    labels = outcomes["snapshot_default"].to_numpy(dtype=float)
    resolved = np.isfinite(labels)
    return {
        "scores": scores,
        "outcomes": outcomes,
        "recipes": _recipes(),
        "fit_audit": fit_audit,
        "reference": _reference(scores, outcomes, fit_audit),
        "expected_resolved": int(resolved.sum()),
        "expected_unresolved": int((~resolved).sum()),
        "expected_y0": int(np.sum(labels == 0.0)),
        "expected_y1": int(np.sum(labels == 1.0)),
    }


def _build(case: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    return build_residual_transport_frontier(
        case["scores"],
        case["outcomes"],
        case["recipes"],
        case["reference"],
        fit_audit=case["fit_audit"],
        learners=LEARNERS,
        window_ids=WINDOWS,
        role="evaluation",
        taxonomy_groups=5,
        expected_issue_months=MONTHS,
        expected_candidates=len(case["scores"]),
        expected_resolved=case["expected_resolved"],
        expected_unresolved=case["expected_unresolved"],
        expected_resolved_y0=case["expected_y0"],
        expected_resolved_y1=case["expected_y1"],
    )


def test_directional_ks_orients_cdf_differences_and_reports_witnesses() -> None:
    result = directional_ks([0.1, 0.2, 0.3], [0.2, 0.3, 0.4])

    assert result["calibration_minus_target_ks"] == pytest.approx(1.0 / 3.0)
    assert result["calibration_minus_target_witness"] == pytest.approx(0.1)
    assert result["calibration_minus_target_numerator"] == 3
    assert result["ks_denominator"] == 9
    assert result["target_minus_calibration_ks"] == 0.0
    assert result["target_minus_calibration_witness"] == pytest.approx(0.4)


def test_completion_frontier_matches_exhaustive_binary_completions() -> None:
    calibration = np.asarray([0.05, 0.2, 0.35, 0.7, 0.9])
    resolved = np.asarray([0.1, 0.4, 0.8])
    unresolved = np.asarray([0.15, 0.45, 0.82])
    frontier = completion_directional_ks_frontier(calibration, resolved, unresolved)
    calibration_direction: list[float] = []
    target_direction: list[float] = []
    for completion in product((0.0, 1.0), repeat=len(unresolved)):
        completed = np.asarray(completion)
        residual = np.where(completed == 0.0, unresolved, 1.0 - unresolved)
        result = directional_ks(calibration, np.concatenate((resolved, residual)))
        calibration_direction.append(float(result["calibration_minus_target_ks"]))
        target_direction.append(float(result["target_minus_calibration_ks"]))

    assert frontier["calibration_minus_target_ks_min"] == pytest.approx(min(calibration_direction))
    assert frontier["calibration_minus_target_ks_max"] == pytest.approx(max(calibration_direction))
    assert frontier["target_minus_calibration_ks_min"] == pytest.approx(min(target_direction))
    assert frontier["target_minus_calibration_ks_max"] == pytest.approx(max(target_direction))


@pytest.mark.parametrize(
    ("calibration", "target", "expected"),
    [
        (
            [0.05, 0.10, 0.15],
            [0.80, 0.85, 0.90],
            "larger_target_residual_discrepancy_dominates",
        ),
        (
            [0.80, 0.85, 0.90],
            [0.05, 0.10, 0.15],
            "smaller_target_residual_discrepancy_dominates",
        ),
        (
            [0.10, 0.90],
            [0.10, 0.90],
            "directional_discrepancies_not_robustly_ordered",
        ),
    ],
)
def test_directional_discrepancy_comparison_is_symmetric_and_tie_conservative(
    calibration: list[float], target: list[float], expected: str
) -> None:
    result = completion_directional_ks_frontier(calibration, target, [])

    assert result["sharp_directional_discrepancy_comparison"] == expected


def test_builds_complete_monthly_and_pooled_grids_with_exact_q_reconciliation(
    fixed_case: dict[str, Any],
) -> None:
    monthly, pooled, summary = _build(fixed_case)

    assert len(monthly) == 3000
    assert len(pooled) == 200
    assert not monthly.duplicated(["learner", "window_id", "conformal_group", "issue_month"]).any()
    assert not pooled.duplicated(["learner", "window_id", "conformal_group"]).any()
    assert pooled["v5_q_and_coverage_reconciled"].all()
    assert (
        monthly["calibration_minus_target_ks_min"]
        <= monthly["calibration_minus_target_ks_max"] + 1.0e-15
    ).all()
    assert (
        monthly["target_minus_calibration_ks_min"]
        <= monthly["target_minus_calibration_ks_max"] + 1.0e-15
    ).all()
    assert summary["status"] == "candidate_module_only_no_active_evidence"
    assert summary["directional_ks_p_values_computed"] is False
    assert summary["directional_discrepancy_comparison_uses_strict_separation"] is True
    assert summary["monthly_to_pooled_q_counts_reconciled"] is True

    selected = monthly.loc[
        monthly["learner"].eq(LEARNERS[0])
        & monthly["window_id"].eq(WINDOWS[0])
        & monthly["conformal_group"].eq(0)
    ]
    pooled_row = pooled.loc[
        pooled["learner"].eq(LEARNERS[0])
        & pooled["window_id"].eq(WINDOWS[0])
        & pooled["conformal_group"].eq(0)
    ].iloc[0]
    assert int(selected["misses_min"].sum()) == int(pooled_row["misses_min"])
    assert int(selected["misses_max"].sum()) == int(pooled_row["misses_max"])


def test_pooled_v5_quantile_reconciliation_fails_closed(fixed_case: dict[str, Any]) -> None:
    broken = deepcopy(fixed_case)
    broken["reference"] = broken["reference"].copy()
    broken["reference"].loc[0, "fit_residual_quantile"] += 1.0e-4

    with pytest.raises(RuntimeError, match="fit_residual_quantile did not reconcile"):
        _build(broken)


@pytest.mark.parametrize("invalid", [float("inf"), "not-an-outcome"])
def test_endpoint_invalid_values_are_not_treated_as_unresolved(
    fixed_case: dict[str, Any], invalid: object
) -> None:
    broken = deepcopy(fixed_case)
    broken["outcomes"] = broken["outcomes"].copy()
    if isinstance(invalid, str):
        broken["outcomes"]["snapshot_default"] = broken["outcomes"]["snapshot_default"].astype(
            object
        )
    broken["outcomes"].loc[1, "snapshot_default"] = invalid

    with pytest.raises(RuntimeError, match="nonnumeric or infinite"):
        _build(broken)
