"""Small-instance certificates for the reusable fixed-K JOMI core."""

from __future__ import annotations

import itertools
import math
from fractions import Fraction

import pytest

from src.ijds_audit.jomi_fixed_k import (
    beta_binomial_reference_size_cdf,
    beta_binomial_reference_size_law,
    beta_binomial_reference_size_mean,
    beta_binomial_reference_size_pmf,
    beta_binomial_reference_size_variance,
    deterministic_binary_jomi_set,
    deterministic_binary_prediction_sets,
    equal_notional_fcp,
    exact_conformal_rank,
    generic_swap_reference_set,
    minimum_finite_threshold_reference_size,
    proposition6_reference_set,
    reference_resolution_size,
    select_top_k,
    swap_and_rerun_reference_oracle,
    top_k_reference_set,
    top_k_select_indices,
)


def test_proposition6_shortcut_matches_literal_swap_oracle_exhaustively() -> None:
    """Enumerate every strict total ordering for small calibration/menu splits."""

    for calibration_size in range(1, 4):
        for menu_size in range(1, 5):
            total = calibration_size + menu_size
            priorities = tuple((index + 1) / (total + 1) for index in range(total))
            for ordering in itertools.permutations(range(total)):
                calibration_scores = ordering[:calibration_size]
                menu_scores = ordering[calibration_size:]
                calibration_priorities = priorities[:calibration_size]
                menu_priorities = priorities[calibration_size:]
                for k in range(1, menu_size + 1):
                    shortcut = proposition6_reference_set(
                        calibration_scores,
                        calibration_priorities,
                        menu_scores,
                        menu_priorities,
                        k,
                    )
                    selected = top_k_select_indices(menu_scores, menu_priorities, k)
                    for focal in selected:
                        oracle = swap_and_rerun_reference_oracle(
                            calibration_scores,
                            calibration_priorities,
                            menu_scores,
                            menu_priorities,
                            k,
                            focal_index=focal,
                        )
                        assert oracle == shortcut


def test_preassigned_continuous_priorities_resolve_score_ties() -> None:
    menu_scores = (0.5, 0.5, 0.5, 0.5)
    menu_priorities = (0.10, 0.40, 0.30, 0.20)
    calibration_scores = (0.5, 0.5, 0.5, 0.5)
    calibration_priorities = (0.05, 0.25, 0.35, 0.45)

    assert top_k_select_indices(menu_scores, menu_priorities, 2) == (1, 2)
    shortcut = proposition6_reference_set(
        calibration_scores,
        calibration_priorities,
        menu_scores,
        menu_priorities,
        2,
    )
    assert shortcut == (1, 2, 3)
    for focal in (1, 2):
        assert (
            swap_and_rerun_reference_oracle(
                calibration_scores,
                calibration_priorities,
                menu_scores,
                menu_priorities,
                2,
                focal_index=focal,
            )
            == shortcut
        )


def test_compact_runner_api_preserves_the_certified_core_outputs() -> None:
    calibration_scores = (0.5, 0.8, 0.6)
    calibration_priorities = (0.1, 0.2, 0.3)
    menu_scores = (0.9, 0.7, 0.4)
    menu_priorities = (0.4, 0.5, 0.6)
    selected = select_top_k(menu_scores, menu_priorities, 2)
    shortcut = top_k_reference_set(
        calibration_scores,
        calibration_priorities,
        menu_scores,
        menu_priorities,
        2,
    )
    assert selected == top_k_select_indices(menu_scores, menu_priorities, 2)
    assert shortcut == proposition6_reference_set(
        calibration_scores,
        calibration_priorities,
        menu_scores,
        menu_priorities,
        2,
    )
    assert (
        generic_swap_reference_set(
            calibration_scores,
            calibration_priorities,
            menu_scores,
            menu_priorities,
            2,
            focal_index=selected[0],
        )
        == shortcut
    )
    assert reference_resolution_size(0.25) == 3
    assert deterministic_binary_prediction_sets(
        (0.29, 0.31),
        (0.10, 0.20, 0.30),
        0.25,
    ) == (True, False, 0.30)


def test_selection_and_reference_membership_are_permutation_invariant() -> None:
    menu_units = (
        ("m0", 0.7, 0.11),
        ("m1", 0.9, 0.21),
        ("m2", 0.7, 0.31),
        ("m3", 0.2, 0.41),
    )
    calibration_units = (
        ("c0", 0.6, 0.51),
        ("c1", 0.7, 0.61),
        ("c2", 0.95, 0.71),
    )
    selected_id_sets: set[frozenset[str]] = set()
    reference_id_sets: set[frozenset[str]] = set()
    for menu_permutation in itertools.permutations(menu_units):
        menu_scores = tuple(unit[1] for unit in menu_permutation)
        menu_priorities = tuple(unit[2] for unit in menu_permutation)
        selected = top_k_select_indices(menu_scores, menu_priorities, 2)
        selected_id_sets.add(frozenset(menu_permutation[index][0] for index in selected))
        for calibration_permutation in itertools.permutations(calibration_units):
            reference = proposition6_reference_set(
                tuple(unit[1] for unit in calibration_permutation),
                tuple(unit[2] for unit in calibration_permutation),
                menu_scores,
                menu_priorities,
                2,
            )
            reference_id_sets.add(
                frozenset(calibration_permutation[index][0] for index in reference)
            )
    assert selected_id_sets == {frozenset({"m1", "m2"})}
    assert reference_id_sets == {frozenset({"c1", "c2"})}


def test_exact_binary_set_uses_the_finite_sample_rank_for_both_labels() -> None:
    alpha = 0.25
    references = (0.10, 0.20, 0.30)
    assert minimum_finite_threshold_reference_size(alpha=alpha) == 3
    assert exact_conformal_rank(len(references), alpha=alpha) == 3

    assert deterministic_binary_jomi_set(references, {0: 0.29, 1: 0.31}, alpha=alpha) == frozenset(
        {0}
    )
    assert deterministic_binary_jomi_set(references, {0: 0.31, 1: 0.30}, alpha=alpha) == frozenset(
        {1}
    )
    assert deterministic_binary_jomi_set(references, {0: 0.29, 1: 0.30}, alpha=alpha) == frozenset(
        {0, 1}
    )
    assert deterministic_binary_jomi_set(references, {0: 0.31, 1: 0.32}, alpha=alpha) == frozenset()


def test_finite_threshold_gate_fails_before_an_infinite_cutoff() -> None:
    assert minimum_finite_threshold_reference_size(alpha=0.1) == 9
    assert exact_conformal_rank(8, alpha=0.1) == 9
    with pytest.raises(RuntimeError, match="cannot attain a finite conformal cutoff"):
        deterministic_binary_jomi_set(
            (0.1,) * 8,
            {0: 0.1, 1: 0.9},
            alpha=0.1,
        )


def test_beta_binomial_pmf_cdf_and_moments_are_exact() -> None:
    for calibration_size in range(9):
        for menu_size in range(1, 7):
            for k in range(1, menu_size + 1):
                law = beta_binomial_reference_size_law(calibration_size, menu_size, k)
                assert law.pmf == beta_binomial_reference_size_pmf(calibration_size, menu_size, k)
                assert law.cdf == beta_binomial_reference_size_cdf(calibration_size, menu_size, k)
                assert law.mean == beta_binomial_reference_size_mean(calibration_size, menu_size, k)
                assert law.variance == beta_binomial_reference_size_variance(
                    calibration_size, menu_size, k
                )
                assert sum(law.pmf, Fraction(0, 1)) == 1
                assert law.cdf[-1] == 1
                assert all(left <= right for left, right in itertools.pairwise(law.cdf))
                enumerated_mean = sum(
                    (size * probability for size, probability in enumerate(law.pmf)),
                    Fraction(0, 1),
                )
                assert enumerated_mean == law.mean
                assert law.mean == Fraction(calibration_size * (k + 1), menu_size + 1)
                enumerated_variance = sum(
                    (
                        (Fraction(size, 1) - law.mean) ** 2 * probability
                        for size, probability in enumerate(law.pmf)
                    ),
                    Fraction(0, 1),
                )
                assert enumerated_variance == law.variance
                assert law.variance == Fraction(
                    calibration_size
                    * (k + 1)
                    * (menu_size - k)
                    * (menu_size + 1 + calibration_size),
                    (menu_size + 1) ** 2 * (menu_size + 2),
                )


def test_beta_binomial_law_matches_exhaustive_rank_assignments() -> None:
    calibration_size, menu_size, k = 3, 4, 2
    counts = [0] * (calibration_size + 1)
    total = 0
    for calibration_ranks in itertools.combinations(
        range(calibration_size + menu_size), calibration_size
    ):
        calibration_rank_set = set(calibration_ranks)
        menu_ranks = tuple(
            rank for rank in range(calibration_size + menu_size) if rank not in calibration_rank_set
        )
        cutoff = sorted(menu_ranks)[menu_size - k - 1]
        reference_size = sum(rank > cutoff for rank in calibration_ranks)
        counts[reference_size] += 1
        total += 1
    exhaustive = tuple(Fraction(count, total) for count in counts)
    assert exhaustive == beta_binomial_reference_size_pmf(calibration_size, menu_size, k)


def test_equal_notional_count_and_dollar_fcp_are_identical_exhaustively() -> None:
    for selected_count in range(1, 7):
        for misses in itertools.product((0, 1), repeat=selected_count):
            for budget in (0.1, 100.0, 1_000_000.0):
                result = equal_notional_fcp(misses, budget=budget)
                expected = Fraction(sum(misses), selected_count)
                assert result.selected_count == selected_count
                assert result.miss_count == sum(misses)
                assert result.notional_per_unit == pytest.approx(budget / selected_count)
                assert result.count_fcp == expected
                assert result.dollar_fcp == expected
                assert result.count_fcp == result.dollar_fcp


def test_menus_smaller_than_k_and_invalid_runtime_contracts_fail_closed() -> None:
    with pytest.raises(ValueError, match="fewer than"):
        top_k_select_indices((0.1, 0.2), (0.1, 0.2), 3)
    with pytest.raises(ValueError, match="fewer than"):
        proposition6_reference_set((0.8,), (0.3,), (0.1, 0.2), (0.1, 0.2), 3)
    with pytest.raises(ValueError, match="fewer than"):
        beta_binomial_reference_size_law(10, 2, 3)
    with pytest.raises(ValueError, match="pairwise distinct"):
        top_k_select_indices((0.1, 0.1), (0.2, 0.2), 1)
    with pytest.raises(ValueError, match="must be selected"):
        swap_and_rerun_reference_oracle(
            (0.8,),
            (0.1,),
            (0.9, 0.2),
            (0.2, 0.3),
            1,
            focal_index=1,
        )

    def broken_selector(_scores: object, _priorities: object, _k: int) -> tuple[int, ...]:
        return (0, 0)

    with pytest.raises(RuntimeError, match="exactly K distinct"):
        swap_and_rerun_reference_oracle(
            (0.8,),
            (0.1,),
            (0.9, 0.2),
            (0.2, 0.3),
            2,
            focal_index=0,
            selector=broken_selector,
        )


def test_alpha_and_binary_label_validation_are_explicit() -> None:
    for alpha in (0.0, 1.0, math.nan, math.inf):
        with pytest.raises(ValueError, match="alpha"):
            minimum_finite_threshold_reference_size(alpha=alpha)
    with pytest.raises(ValueError, match="each binary label"):
        deterministic_binary_jomi_set((0.1, 0.2, 0.3), {0: 0.1}, alpha=0.25)
    with pytest.raises(ValueError, match="integer labels"):
        deterministic_binary_jomi_set(
            (0.1, 0.2, 0.3),
            {False: 0.1, True: 0.2},
            alpha=0.25,
        )
    with pytest.raises(ValueError, match="zeros and ones"):
        equal_notional_fcp((0, 0.5, 1), budget=100.0)
