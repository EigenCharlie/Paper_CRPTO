from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.ijds_audit.common_panel_threshold_response import (
    _hash_ids,
    build_common_panel_threshold_response,
    validate_residual_fit_audit,
)
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)

LEARNERS = tuple(f"learner_{index}" for index in range(5))
WINDOWS = tuple(f"window_{index}" for index in range(8))
EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
QUANTILE_PATHS = (
    (0.10, 0.15, 0.15, 0.05, 0.18, 0.10, 0.10, 0.19),
    (0.25, 0.30, 0.30, 0.21, 0.35, 0.25, 0.25, 0.39),
    (0.45, 0.55, 0.55, 0.40, 0.58, 0.45, 0.45, 0.59),
    (0.35, 0.30, 0.30, 0.38, 0.25, 0.35, 0.35, 0.22),
    (0.10, 0.15, 0.15, 0.05, 0.18, 0.10, 0.10, 0.19),
)


def _recipe(
    quantiles: tuple[float, ...],
    *,
    learner: str,
    edges: tuple[float, ...] = EDGES,
) -> BinaryOutcomeConformalRecipe:
    return BinaryOutcomeConformalRecipe(
        alpha=0.10,
        requested_groups=5,
        bin_edges=edges,
        residual_quantiles=quantiles,
        group_counts=(10, 10, 10, 10, 10),
        finite_sample_ranks=(10, 10, 10, 10, 10),
        raw_finite_sample_ranks=(10, 10, 10, 10, 10),
        method="fixed_taxonomy_split_mondrian_absolute_residual",
        taxonomy_provenance=f"{learner}_201101_201112_all_status_independent_scores",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )


def _recipes() -> dict[str, dict[str, dict[int, BinaryOutcomeConformalRecipe]]]:
    return {
        learner: {
            window: {
                5: _recipe(tuple(path[window_index] for path in QUANTILE_PATHS), learner=learner)
            }
            for window_index, window in enumerate(WINDOWS)
        }
        for learner in LEARNERS
    }


def _fit_audit(
    recipes: dict[str, dict[str, dict[int, BinaryOutcomeConformalRecipe]]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for learner in LEARNERS:
        for window in WINDOWS:
            recipe = recipes[learner][window][5]
            for group, threshold in enumerate(recipe.residual_quantiles):
                count = recipe.group_counts[group]
                raw_rank = recipe.raw_finite_sample_ranks[group]
                if raw_rank > count:
                    point = (recipe.bin_edges[group] + recipe.bin_edges[group + 1]) / 2.0
                    label = 0.0
                elif group <= 2:
                    point = threshold
                    label = 0.0
                else:
                    point = float(np.nextafter(1.0 - threshold, 1.0))
                    label = 1.0
                lower = float(np.clip(point - threshold, 0.0, 1.0))
                upper = float(np.clip(point + threshold, 0.0, 1.0))
                for row_index in range(count):
                    rows.append(
                        {
                            "id": f"fit-{learner}-{window}-{group}-{row_index:02d}",
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


def _scores_and_outcomes() -> tuple[pd.DataFrame, pd.DataFrame]:
    probabilities = (
        0.05,
        0.10,
        0.15,
        0.20,
        0.30,
        0.35,
        0.40,
        0.50,
        0.55,
        0.60,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
        0.95,
    )
    labels = (
        0.0,
        0.0,
        1.0,
        np.nan,
        np.nan,
        1.0,
        np.nan,
        np.nan,
        np.nan,
        0.0,
        np.nan,
        1.0,
        0.0,
        np.nan,
        1.0,
        np.nan,
    )
    scores = pd.DataFrame(
        {
            "id": [f"id-{index:02d}" for index in range(len(probabilities))],
            "issue_d": ["2016-04-15"] * len(probabilities),
            "design_split": ["evaluation"] * len(probabilities),
            **{f"pd_{learner}": probabilities for learner in LEARNERS},
        }
    )
    outcomes = pd.DataFrame({"id": scores["id"], "snapshot_default": labels})
    return scores, outcomes


def _reference(
    scores: pd.DataFrame,
    outcomes: pd.DataFrame,
    recipes: dict[str, dict[str, dict[int, BinaryOutcomeConformalRecipe]]],
) -> pd.DataFrame:
    panel = scores.loc[scores["design_split"].eq("evaluation")].merge(
        outcomes, on="id", how="left", validate="one_to_one"
    )
    labels = panel["snapshot_default"].to_numpy(dtype=float)
    resolved = np.isfinite(labels)
    rows: list[dict[str, Any]] = []
    for learner in LEARNERS:
        probabilities = panel[f"pd_{learner}"].to_numpy(dtype=float)
        for window in WINDOWS:
            recipe = recipes[learner][window][5]
            groups, lower, upper = apply_binary_outcome_recipe(probabilities, recipe)
            contains_zero = lower <= 0.0
            contains_one = upper >= 1.0
            for group in range(5):
                mask = groups == group
                group_resolved = resolved[mask]
                group_labels = labels[mask]
                zero = contains_zero[mask]
                one = contains_one[mask]
                covered = group_resolved & (
                    ((group_labels == 0.0) & zero) | ((group_labels == 1.0) & one)
                )
                resolved_rows = int(group_resolved.sum())
                resolved_misses = resolved_rows - int(covered.sum())
                unresolved = ~group_resolved
                misses_min = resolved_misses + int(np.sum(unresolved & ~zero & ~one))
                misses_max = resolved_misses + int(np.sum(unresolved & ~(zero & one)))
                candidate_rows = int(mask.sum())
                group_scores = probabilities[mask]
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
                        "coverage_resolved": (
                            1.0 - resolved_misses / resolved_rows if resolved_rows else np.nan
                        ),
                        "misses_min": misses_min,
                        "misses_max": misses_max,
                        "coverage_lower": 1.0 - misses_max / candidate_rows,
                        "coverage_upper": 1.0 - misses_min / candidate_rows,
                        "score_min": float(group_scores.min()),
                        "score_max": float(group_scores.max()),
                        "fit_residual_quantile": recipe.residual_quantiles[group],
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def fixed_case() -> dict[str, Any]:
    scores, outcomes = _scores_and_outcomes()
    recipes = _recipes()
    return {
        "scores": scores,
        "outcomes": outcomes,
        "recipes": recipes,
        "fit_audit": _fit_audit(recipes),
        "reference": _reference(scores, outcomes, recipes),
    }


def _build(case: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    return build_common_panel_threshold_response(
        case["scores"],
        case["outcomes"],
        case["recipes"],
        case["reference"],
        fit_audit=case["fit_audit"],
        learners=LEARNERS,
        window_ids=WINDOWS,
        role="evaluation",
        taxonomy_groups=5,
        expected_issue_months=("2016-04",),
        expected_candidates=16,
        expected_resolved=8,
        expected_unresolved=8,
        expected_resolved_y0=4,
        expected_resolved_y1=4,
    )


def test_builds_exact_grids_and_pools_integer_numerators(fixed_case: dict[str, Any]) -> None:
    strata, pooled, summary = _build(fixed_case)

    assert len(strata) == 175
    assert len(pooled) == 35
    assert not strata.duplicated(["learner", "pair_index", "conformal_group"]).any()
    assert not pooled.duplicated(["learner", "pair_index"]).any()
    assert (strata["score_stratum"] == strata["conformal_group"] + 1).all()
    assert summary["status"] == "candidate_module_only_no_active_evidence"
    assert summary["strata_rows"] == 175
    assert summary["pooled_rows"] == 35

    source = strata.loc[strata["learner"].eq(LEARNERS[0]) & strata["pair_index"].eq(3)]
    target = pooled.loc[pooled["learner"].eq(LEARNERS[0]) & pooled["pair_index"].eq(3)].iloc[0]
    assert int(target["resolved_delta_numerator"]) == int(source["resolved_delta_numerator"].sum())
    assert int(target["delta_lower_numerator"]) == int(source["delta_lower_numerator"].sum())
    assert int(target["delta_upper_numerator"]) == int(source["delta_upper_numerator"].sum())
    assert target["resolved_delta_rate"] == pytest.approx(
        target["resolved_delta_numerator"] / target["resolved_rows"]
    )
    assert target["resolved_delta_rate"] != pytest.approx(source["resolved_delta_rate"].mean())


def test_bounds_equal_exhaustive_binary_completion_extrema(fixed_case: dict[str, Any]) -> None:
    strata, _, _ = _build(fixed_case)
    row = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(0)
        & strata["conformal_group"].eq(1)
    ].iloc[0]

    panel = fixed_case["scores"].merge(fixed_case["outcomes"], on="id", validate="one_to_one")
    probabilities = panel[f"pd_{LEARNERS[0]}"].to_numpy(dtype=float)
    from_groups, from_lower, from_upper = apply_binary_outcome_recipe(
        probabilities, fixed_case["recipes"][LEARNERS[0]][WINDOWS[0]][5]
    )
    to_groups, to_lower, to_upper = apply_binary_outcome_recipe(
        probabilities, fixed_case["recipes"][LEARNERS[0]][WINDOWS[1]][5]
    )
    assert np.array_equal(from_groups, to_groups)
    mask = from_groups == 1
    labels = panel.loc[mask, "snapshot_default"].to_numpy(dtype=float)
    unresolved_positions = np.flatnonzero(~np.isfinite(labels))
    deltas: list[float] = []
    for completion in product((0.0, 1.0), repeat=len(unresolved_positions)):
        completed = labels.copy()
        completed[unresolved_positions] = completion
        covered_from = np.where(completed == 0.0, from_lower[mask] <= 0.0, from_upper[mask] >= 1.0)
        covered_to = np.where(completed == 0.0, to_lower[mask] <= 0.0, to_upper[mask] >= 1.0)
        deltas.append(float(np.mean(covered_to.astype(int) - covered_from.astype(int))))

    assert row["delta_lower"] == pytest.approx(min(deltas))
    assert row["delta_upper"] == pytest.approx(max(deltas))
    assert row["delta_width"] == pytest.approx(max(deltas) - min(deltas))


def test_ordered_bands_use_exact_endpoint_inclusions_and_signs(
    fixed_case: dict[str, Any],
) -> None:
    strata, _, _ = _build(fixed_case)

    group_zero_increase = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(0)
        & strata["conformal_group"].eq(0)
    ].iloc[0]
    assert group_zero_increase["threshold_sign"] == 1
    assert group_zero_increase["potential_y0_crossed_rows"] == 1
    assert group_zero_increase["potential_y1_crossed_rows"] == 0

    group_four_increase = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(0)
        & strata["conformal_group"].eq(4)
    ].iloc[0]
    assert group_four_increase["potential_y0_crossed_rows"] == 0
    assert group_four_increase["potential_y1_crossed_rows"] == 1

    equal = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(1)
        & strata["conformal_group"].eq(0)
    ].iloc[0]
    decrease = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(2)
        & strata["conformal_group"].eq(0)
    ].iloc[0]
    assert equal["threshold_sign"] == 0
    assert equal["resolved_delta_numerator"] == 0
    assert equal["delta_width_numerator"] == 0
    assert decrease["threshold_sign"] == -1


def test_zero_resolved_cell_retains_completion_bounds(fixed_case: dict[str, Any]) -> None:
    strata, _, _ = _build(fixed_case)
    row = strata.loc[
        strata["learner"].eq(LEARNERS[0])
        & strata["pair_index"].eq(3)
        & strata["conformal_group"].eq(2)
    ].iloc[0]

    assert row["resolved_rows"] == 0
    assert np.isnan(row["resolved_delta_rate"])
    assert np.isfinite(row["delta_lower"])
    assert np.isfinite(row["delta_upper"])
    assert row["delta_lower"] <= row["delta_upper"]


def test_hashes_and_outputs_are_row_order_invariant(fixed_case: dict[str, Any]) -> None:
    strata, pooled, summary = _build(fixed_case)
    shuffled = deepcopy(fixed_case)
    shuffled["scores"] = shuffled["scores"].sample(frac=1.0, random_state=11).reset_index(drop=True)
    shuffled["outcomes"] = (
        shuffled["outcomes"].sample(frac=1.0, random_state=22).reset_index(drop=True)
    )
    shuffled["reference"] = (
        shuffled["reference"].sample(frac=1.0, random_state=33).reset_index(drop=True)
    )
    shuffled_strata, shuffled_pooled, shuffled_summary = _build(shuffled)

    assert summary == shuffled_summary
    assert_frame_equal(strata, shuffled_strata, check_exact=True)
    assert_frame_equal(pooled, shuffled_pooled, check_exact=True)


def test_id_hash_is_length_prefixed_against_concatenation_collisions() -> None:
    assert _hash_ids(np.asarray(["1", "23"])) != _hash_ids(np.asarray(["12", "3"]))


def test_fit_audit_recomputes_ranked_thresholds_and_records_ties(
    fixed_case: dict[str, Any],
) -> None:
    summary = validate_residual_fit_audit(
        fixed_case["fit_audit"],
        fixed_case["recipes"],
        learners=LEARNERS,
        window_ids=WINDOWS,
        taxonomy_groups=5,
    )

    assert summary == {
        "fit_audit_rows": 2000,
        "fit_audit_cells": 200,
        "capped_cells": 0,
        "tied_threshold_cells": 200,
    }


def test_fit_audit_accepts_the_declared_rank_cap(fixed_case: dict[str, Any]) -> None:
    recipes = deepcopy(fixed_case["recipes"])
    original = recipes[LEARNERS[0]][WINDOWS[0]][5]
    recipes[LEARNERS[0]][WINDOWS[0]][5] = replace(
        original,
        residual_quantiles=(1.0, *original.residual_quantiles[1:]),
        group_counts=(3, *original.group_counts[1:]),
        finite_sample_ranks=(3, *original.finite_sample_ranks[1:]),
        raw_finite_sample_ranks=(4, *original.raw_finite_sample_ranks[1:]),
    )
    summary = validate_residual_fit_audit(
        _fit_audit(recipes),
        recipes,
        learners=LEARNERS,
        window_ids=WINDOWS,
        taxonomy_groups=5,
    )

    assert summary["capped_cells"] == 1
    assert summary["fit_audit_rows"] == 1993


@pytest.mark.parametrize("drift", ["rank", "threshold", "assignment", "endpoint", "covered"])
def test_fit_audit_scientific_drift_fails_closed(fixed_case: dict[str, Any], drift: str) -> None:
    recipes = deepcopy(fixed_case["recipes"])
    fit_audit = fixed_case["fit_audit"].copy()
    original = recipes[LEARNERS[0]][WINDOWS[0]][5]
    if drift == "rank":
        recipes[LEARNERS[0]][WINDOWS[0]][5] = replace(
            original,
            raw_finite_sample_ranks=(9, *original.raw_finite_sample_ranks[1:]),
        )
        expected = "rank convention"
    elif drift == "threshold":
        recipes[LEARNERS[0]][WINDOWS[0]][5] = replace(
            original,
            residual_quantiles=(0.101, *original.residual_quantiles[1:]),
        )
        expected = "order statistic"
    elif drift == "assignment":
        fit_audit.loc[0, "pd_point"] = 0.30
        expected = "assignment"
    elif drift == "endpoint":
        fit_audit.loc[0, "conformal_upper"] -= 0.01
        expected = "endpoints"
    else:
        fit_audit.loc[0, "covered"] = False
        expected = "covered flag"

    with pytest.raises(RuntimeError, match=expected):
        validate_residual_fit_audit(
            fit_audit,
            recipes,
            learners=LEARNERS,
            window_ids=WINDOWS,
            taxonomy_groups=5,
        )


@pytest.mark.parametrize("mutation", ["missing_cell", "duplicate_id"])
def test_fit_audit_grid_and_id_contracts_fail_closed(
    fixed_case: dict[str, Any], mutation: str
) -> None:
    fit_audit = fixed_case["fit_audit"].copy()
    if mutation == "missing_cell":
        keep = ~(
            fit_audit["learner"].eq(LEARNERS[0])
            & fit_audit["window_id"].eq(WINDOWS[0])
            & fit_audit["conformal_group"].eq(0)
        )
        fit_audit = fit_audit.loc[keep].copy()
        expected = "cell grid"
    else:
        fit_audit = pd.concat([fit_audit, fit_audit.iloc[[0]]], ignore_index=True)
        expected = "duplicated"

    with pytest.raises(RuntimeError, match=expected):
        validate_residual_fit_audit(
            fit_audit,
            fixed_case["recipes"],
            learners=LEARNERS,
            window_ids=WINDOWS,
            taxonomy_groups=5,
        )


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "invalid_group"])
def test_reference_grid_fails_closed(fixed_case: dict[str, Any], mutation: str) -> None:
    broken = deepcopy(fixed_case)
    if mutation == "duplicate":
        broken["reference"] = pd.concat(
            [broken["reference"], broken["reference"].iloc[[0]]], ignore_index=True
        )
    elif mutation == "missing":
        broken["reference"] = broken["reference"].iloc[1:].reset_index(drop=True)
    else:
        extra = broken["reference"].iloc[[0]].copy()
        extra["conformal_group"] = 5
        broken["reference"] = pd.concat([broken["reference"], extra], ignore_index=True)

    with pytest.raises(RuntimeError, match=r"grid|duplicate|domain"):
        _build(broken)


def test_missing_recipe_window_fails_closed(fixed_case: dict[str, Any]) -> None:
    broken = deepcopy(fixed_case)
    del broken["recipes"][LEARNERS[0]][WINDOWS[-1]]

    with pytest.raises(RuntimeError, match="window domain"):
        _build(broken)


def test_changed_score_edges_fail_before_response_is_computed(fixed_case: dict[str, Any]) -> None:
    broken = deepcopy(fixed_case)
    original = broken["recipes"][LEARNERS[0]][WINDOWS[-1]][5]
    broken["recipes"][LEARNERS[0]][WINDOWS[-1]][5] = replace(
        original, bin_edges=(0.0, 0.21, 0.4, 0.6, 0.8, 1.0)
    )

    with pytest.raises(RuntimeError, match="edges changed across windows"):
        _build(broken)


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_endpoint_id_alignment_fails_closed(fixed_case: dict[str, Any], mutation: str) -> None:
    broken = deepcopy(fixed_case)
    if mutation == "missing":
        broken["outcomes"] = broken["outcomes"].iloc[1:].reset_index(drop=True)
    else:
        broken["outcomes"] = pd.concat(
            [broken["outcomes"], broken["outcomes"].iloc[[0]]], ignore_index=True
        )

    with pytest.raises(RuntimeError, match="Endpoint"):
        _build(broken)


def test_reference_integer_numerator_reconciliation_fails_closed(
    fixed_case: dict[str, Any],
) -> None:
    broken = deepcopy(fixed_case)
    broken["reference"].loc[0, "resolved_misses"] += 1

    with pytest.raises(RuntimeError, match="resolved_misses changed"):
        _build(broken)
