"""Tests for finite score-order equivalence diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from src.ijds_audit.decision_score_equivalence import (
    certify_score_order_equivalence,
    first_declared_order_disagreement,
)


def test_positive_affine_scores_are_equivalent_on_full_budget_hull() -> None:
    allocations = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    source = np.array([0.1, 0.3, 0.8])
    target = 2.5 * source + 4.0

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is True
    assert certificate.estimated_positive_scale == pytest.approx(2.5)
    assert certificate.offset_at_reference == pytest.approx(4.0)
    assert certificate.affine_dimension == 2
    assert certificate.spans_full_budget_hull is True
    assert certificate.maximum_declared_relation_error == pytest.approx(0.0, abs=1.0e-12)
    assert first_declared_order_disagreement(allocations, source, target) is None


def test_equality_normal_is_invisible_on_declared_affine_span() -> None:
    allocations = np.array(
        [
            [0.5, 0.5, 0.0, 0.0],
            [0.0, 0.0, 0.5, 0.5],
            [0.25, 0.25, 0.25, 0.25],
        ]
    )
    source = np.array([0.1, 0.2, 0.5, 0.7])
    group_normal = np.array([1.0, -1.0, 0.0, 0.0])
    target = 3.0 * source + 7.0 + 2.0 * group_normal

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is True
    assert certificate.estimated_positive_scale == pytest.approx(3.0)
    assert certificate.affine_dimension == 1
    assert certificate.spans_full_budget_hull is False


def test_non_affine_scores_expose_a_concrete_order_disagreement() -> None:
    allocations = np.eye(3)
    source = np.array([0.1, 0.3, 0.8])
    target = np.array([0.1, 0.9, 0.2])

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is False
    assert certificate.estimated_positive_scale is None
    assert first_declared_order_disagreement(allocations, source, target) == (1, 2)


def test_negative_affine_scale_reverses_order_and_is_rejected() -> None:
    allocations = np.eye(3)
    source = np.array([0.1, 0.3, 0.8])
    target = 5.0 - source

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is False
    assert certificate.estimated_positive_scale is None
    assert first_declared_order_disagreement(allocations, source, target) == (0, 1)


def test_constant_source_requires_constant_target_on_span() -> None:
    allocations = np.eye(3)
    source = np.ones(3)

    passing = certify_score_order_equivalence(allocations, source, np.full(3, 9.0))
    failing = certify_score_order_equivalence(
        allocations,
        source,
        np.array([9.0, 9.0, 8.0]),
    )

    assert passing.equivalent_on_declared_span is True
    assert passing.estimated_positive_scale == pytest.approx(1.0)
    assert failing.equivalent_on_declared_span is False


def test_zero_dimensional_span_makes_all_scores_order_equivalent() -> None:
    allocations = np.array([[0.2, 0.3, 0.5]])
    source = np.array([0.1, 0.4, 0.9])
    target = np.array([8.0, -2.0, 3.0])

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is True
    assert certificate.estimated_positive_scale == pytest.approx(1.0)
    assert certificate.affine_dimension == 0
    assert certificate.spans_full_budget_hull is False
    assert certificate.offset_at_reference == pytest.approx(
        target @ allocations[0] - source @ allocations[0]
    )
    assert first_declared_order_disagreement(allocations, source, target) is None


def test_nonconstant_budgets_do_not_claim_the_full_budget_hull() -> None:
    allocations = np.array([[1.0, 0.0], [0.0, 2.0]])
    source = np.array([0.2, 0.8])
    target = 2.0 * source

    certificate = certify_score_order_equivalence(allocations, source, target)

    assert certificate.equivalent_on_declared_span is True
    assert certificate.affine_dimension == 1
    assert certificate.constant_budget is False
    assert certificate.spans_full_budget_hull is False


def test_set_preserving_endpoints_can_change_both_ruler_allocations() -> None:
    point_score = np.array([0.3, 0.1, 0.8])
    thresholds = np.array([0.3, 0.6, 0.3])
    original_lower = np.maximum(0.0, point_score - thresholds)
    original_upper = np.minimum(1.0, point_score + thresholds)
    contracted_lower = original_lower.copy()
    contracted_upper = np.where(original_upper < 1.0, point_score, original_upper)
    simplex_witnesses = np.eye(3)

    binary_labels = np.array([0.0, 1.0])
    original_sets = (original_lower[:, None] <= binary_labels) & (
        binary_labels <= original_upper[:, None]
    )
    contracted_sets = (contracted_lower[:, None] <= binary_labels) & (
        binary_labels <= contracted_upper[:, None]
    )
    expected_sets = np.array(
        [
            [True, False],
            [True, False],
            [False, True],
        ]
    )
    np.testing.assert_allclose(original_lower, np.array([0.0, 0.0, 0.5]))
    np.testing.assert_allclose(original_upper, np.array([0.6, 0.7, 1.0]))
    np.testing.assert_allclose(contracted_upper, np.array([0.3, 0.1, 1.0]))
    np.testing.assert_array_equal(original_sets, expected_sets)
    np.testing.assert_array_equal(contracted_sets, expected_sets)

    certificate = certify_score_order_equivalence(
        simplex_witnesses,
        original_upper,
        contracted_upper,
    )

    assert certificate.equivalent_on_declared_span is False
    assert first_declared_order_disagreement(
        simplex_witnesses,
        original_upper,
        contracted_upper,
    ) == (0, 1)

    # With objective v=e3 and normalized coordinate 1/2, each score mixes the
    # objective optimum with its own minimum-score loan.
    original_normalized = np.array([0.5, 0.0, 0.5])
    contracted_normalized = np.array([0.0, 0.5, 0.5])
    eta = 0.5
    for score, allocation, expected_cap in (
        (original_upper, original_normalized, 0.8),
        (contracted_upper, contracted_normalized, 0.55),
    ):
        minimum_index = int(np.argmin(score))
        minimum_score = float(score[minimum_index])
        anchor_score = float(score[2])
        normalized_cap = minimum_score + eta * (anchor_score - minimum_score)
        maximum_objective = (normalized_cap - minimum_score) / (anchor_score - minimum_score)

        assert normalized_cap == pytest.approx(expected_cap)
        assert allocation.sum() == pytest.approx(1.0)
        assert bool((allocation >= 0.0).all())
        assert score @ allocation == pytest.approx(normalized_cap)
        assert allocation[2] == pytest.approx(maximum_objective)
        assert allocation[minimum_index] == pytest.approx(1.0 - maximum_objective)

    assert point_score @ original_normalized != pytest.approx(point_score @ contracted_normalized)

    # At common objective floor a3 >= 1/4, score minimization also chooses a
    # different residual allocation while preserving the same objective.
    original_objective_matched = np.array([0.75, 0.0, 0.25])
    contracted_objective_matched = np.array([0.0, 0.75, 0.25])
    objective_floor = 0.25
    for score, allocation, expected_minimum in (
        (original_upper, original_objective_matched, 0.7),
        (contracted_upper, contracted_objective_matched, 0.325),
    ):
        minimum_index = int(np.argmin(score))
        sharp_score_lower_bound = (
            objective_floor * score[2] + (1.0 - objective_floor) * score[minimum_index]
        )

        assert score[2] > score[minimum_index]
        assert allocation.sum() == pytest.approx(1.0)
        assert bool((allocation >= 0.0).all())
        assert allocation[2] == pytest.approx(objective_floor)
        assert allocation[minimum_index] == pytest.approx(1.0 - objective_floor)
        assert score @ allocation == pytest.approx(sharp_score_lower_bound)
        assert sharp_score_lower_bound == pytest.approx(expected_minimum)

    assert original_objective_matched[2] == pytest.approx(contracted_objective_matched[2])


def test_unit_ranking_does_not_preserve_portfolio_score_order() -> None:
    source = np.array([0.0, 0.6, 1.0])
    monotone_nonaffine = source**2
    vertices = np.eye(3)
    interior_witnesses = np.array(
        [
            [0.0, 1.0, 0.0],
            [0.5, 0.0, 0.5],
        ]
    )

    assert np.array_equal(np.argsort(source), np.argsort(monotone_nonaffine))
    assert first_declared_order_disagreement(vertices, source, monotone_nonaffine) is None
    assert (
        certify_score_order_equivalence(
            vertices,
            source,
            monotone_nonaffine,
        ).equivalent_on_declared_span
        is False
    )
    assert source @ interior_witnesses[0] > source @ interior_witnesses[1]
    assert monotone_nonaffine @ interior_witnesses[0] < monotone_nonaffine @ interior_witnesses[1]
    assert first_declared_order_disagreement(
        interior_witnesses,
        source,
        monotone_nonaffine,
    ) == (0, 1)


def test_diagnostic_rejects_invalid_shapes_and_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        certify_score_order_equivalence([1.0, 2.0], [1.0], [1.0])
    with pytest.raises(ValueError, match="finite"):
        certify_score_order_equivalence([[1.0, 0.0]], [1.0, np.nan], [1.0, 2.0])
    with pytest.raises(ValueError, match="matching dimensions"):
        first_declared_order_disagreement([[1.0, 0.0]], [1.0], [1.0])


@pytest.mark.parametrize(
    "keyword_arguments",
    [
        {"absolute_tolerance": -1.0},
        {"relative_tolerance": -1.0},
        {"rank_tolerance": -1.0},
        {"rank_tolerance": np.nan},
        {"budget_tolerance": -1.0},
    ],
)
def test_diagnostic_rejects_invalid_tolerances(
    keyword_arguments: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="finite and nonnegative"):
        certify_score_order_equivalence(
            [[1.0, 0.0], [0.0, 1.0]],
            [0.1, 0.2],
            [0.3, 0.4],
            **keyword_arguments,
        )

    with pytest.raises(ValueError, match="finite and nonnegative"):
        first_declared_order_disagreement(
            [[1.0, 0.0], [0.0, 1.0]],
            [0.1, 0.2],
            [0.3, 0.4],
            tolerance=-1.0,
        )
