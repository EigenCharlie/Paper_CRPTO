"""Reusable fixed-:math:`K` JOMI primitives for outcome-blind top-K selection.

The selector orders units lexicographically by a frozen point score and a
preassigned continuous tie priority.  The priority travels with the unit: an
input row number or identifier is never used as an implicit tie breaker.

For this label-free top-K rule, Proposition 6 of Jin and Ren (2025) gives one
universal JOMI reference set for every selected focal unit.  In the total order
used here, it contains exactly the calibration units above the largest
unselected menu key.  ``swap_and_rerun_reference_oracle`` deliberately does
not use that shortcut; it is a small-instance oracle for implementation tests.

This module only implements the fixed-K mechanics.  It does not establish the
exchangeability, sampling, chronology, or outcome-completeness premises needed
for a selection-conditional coverage claim on any particular data source.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from numbers import Integral, Real

SelectionRule = Callable[[Sequence[float], Sequence[float], int], Iterable[int]]
SelectionTaxonomy = Callable[[frozenset[int]], bool]
OrderKey = tuple[float, float]


@dataclass(frozen=True)
class BetaBinomialReferenceSizeLaw:
    """Exact law of the top-K shortcut reference size under exchangeability.

    For ``K < m``, the mixture representation is

    ``R | P ~ Binomial(n, P), P ~ Beta(K + 1, m - K)``.

    When ``K == m``, every calibration unit is in the reference set and the
    returned law is the corresponding point mass at ``n``.  All probabilities
    and both moments are represented by :class:`fractions.Fraction`.
    """

    calibration_size: int
    menu_size: int
    k: int
    beta_a: int
    beta_b: int
    pmf: tuple[Fraction, ...]
    cdf: tuple[Fraction, ...]
    mean: Fraction
    variance: Fraction


@dataclass(frozen=True)
class EqualNotionalFCP:
    """Exact count and invested-dollar FCP for an equal-notional support."""

    selected_count: int
    miss_count: int
    notional_per_unit: float
    count_fcp: Fraction
    dollar_fcp: Fraction


def _integer(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{label} must be an integer of at least {minimum}.")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}.")
    return result


def _alpha_fraction(alpha: object) -> Fraction:
    if isinstance(alpha, bool) or not isinstance(alpha, Real):
        raise ValueError("alpha must be a finite real strictly inside (0, 1).")
    numeric = float(alpha)
    if not math.isfinite(numeric) or not 0.0 < numeric < 1.0:
        raise ValueError("alpha must be a finite real strictly inside (0, 1).")
    # Parsing the decimal representation avoids binary-float drift exactly at
    # an order-statistic boundary (for example alpha=0.1).
    return Fraction(str(alpha))


def _finite_reals(
    values: Sequence[object],
    *,
    label: str,
    allow_empty: bool,
) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{label} must be a sequence of finite real values.")
    raw = tuple(values)
    if not raw and not allow_empty:
        raise ValueError(f"{label} must not be empty.")
    result: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{label} must contain only finite real values.")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"{label} must contain only finite real values.")
        result.append(numeric)
    return tuple(result)


def _score_priority_pairs(
    scores: Sequence[object],
    priorities: Sequence[object],
    *,
    label: str,
    allow_empty: bool,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    score_values = _finite_reals(scores, label=f"{label} scores", allow_empty=allow_empty)
    priority_values = _finite_reals(
        priorities,
        label=f"{label} tie priorities",
        allow_empty=allow_empty,
    )
    if len(score_values) != len(priority_values):
        raise ValueError(f"{label} scores and tie priorities must have the same length.")
    if len(set(priority_values)) != len(priority_values):
        raise ValueError(f"{label} tie priorities must be pairwise distinct and preassigned.")
    return score_values, priority_values


def _validate_k_for_menu(k: object, menu_size: int) -> int:
    selected_count = _integer(k, label="K", minimum=1)
    if menu_size < selected_count:
        raise ValueError(
            f"The menu contains {menu_size} units, fewer than the required K={selected_count}."
        )
    return selected_count


def top_k_select_indices(
    scores: Sequence[object], priorities: Sequence[object], k: object
) -> tuple[int, ...]:
    """Select exactly K indices by descending ``(score, tie_priority)``.

    Priorities must be finite and pairwise distinct.  They are part of the
    frozen unit-level input, so reordering rows only reorders output indices;
    it cannot change which units are selected.
    """

    score_values, priority_values = _score_priority_pairs(
        scores,
        priorities,
        label="Menu",
        allow_empty=False,
    )
    selected_count = _validate_k_for_menu(k, len(score_values))
    return tuple(
        sorted(
            range(len(score_values)),
            key=lambda index: (score_values[index], priority_values[index]),
            reverse=True,
        )[:selected_count]
    )


def _fixed_k_inputs(
    calibration_scores: Sequence[object],
    calibration_priorities: Sequence[object],
    menu_scores: Sequence[object],
    menu_priorities: Sequence[object],
    k: object,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...], int]:
    calibration_score, calibration_priority = _score_priority_pairs(
        calibration_scores,
        calibration_priorities,
        label="Calibration",
        allow_empty=True,
    )
    menu_score, menu_priority = _score_priority_pairs(
        menu_scores,
        menu_priorities,
        label="Menu",
        allow_empty=False,
    )
    selected_count = _validate_k_for_menu(k, len(menu_score))
    all_priorities = (*calibration_priority, *menu_priority)
    if len(set(all_priorities)) != len(all_priorities):
        raise ValueError("Calibration and menu tie priorities must be globally pairwise distinct.")
    return (
        calibration_score,
        calibration_priority,
        menu_score,
        menu_priority,
        selected_count,
    )


def proposition6_reference_set(
    calibration_scores: Sequence[object],
    calibration_priorities: Sequence[object],
    menu_scores: Sequence[object],
    menu_priorities: Sequence[object],
    k: object,
) -> tuple[int, ...]:
    """Return the universal top-K JOMI reference indices from Proposition 6.

    With a total order, the selection threshold is the largest unselected menu
    key.  If every menu unit is selected (``K == m``), the threshold is below
    every key and the reference set contains the full calibration sample.
    """

    (
        calibration_score,
        calibration_priority,
        menu_score,
        menu_priority,
        selected_count,
    ) = _fixed_k_inputs(
        calibration_scores,
        calibration_priorities,
        menu_scores,
        menu_priorities,
        k,
    )
    if selected_count == len(menu_score):
        return tuple(range(len(calibration_score)))

    ranked_menu = top_k_select_indices(menu_score, menu_priority, len(menu_score))
    largest_unselected = ranked_menu[selected_count]
    cutoff: OrderKey = (
        menu_score[largest_unselected],
        menu_priority[largest_unselected],
    )
    return tuple(
        index
        for index, key in enumerate(zip(calibration_score, calibration_priority, strict=True))
        if key > cutoff
    )


def _checked_selection(
    selector: SelectionRule,
    scores: Sequence[float],
    priorities: Sequence[float],
    k: int,
) -> tuple[int, ...]:
    try:
        raw = tuple(selector(scores, priorities, k))
    except TypeError as error:
        raise RuntimeError("The selection rule did not return an iterable of indices.") from error
    if any(isinstance(index, bool) or not isinstance(index, Integral) for index in raw):
        raise RuntimeError("The selection rule returned a non-integer index.")
    selected = tuple(int(index) for index in raw)
    if len(selected) != k or len(set(selected)) != k:
        raise RuntimeError("The selection rule did not return exactly K distinct indices.")
    if any(index < 0 or index >= len(scores) for index in selected):
        raise RuntimeError("The selection rule returned an out-of-range menu index.")
    return selected


def _taxonomy_result(taxonomy: SelectionTaxonomy, selected: frozenset[int]) -> bool:
    result = taxonomy(selected)
    if not isinstance(result, bool):
        raise RuntimeError("The selection taxonomy must return a boolean scalar.")
    return result


def swap_and_rerun_reference_oracle(
    calibration_scores: Sequence[object],
    calibration_priorities: Sequence[object],
    menu_scores: Sequence[object],
    menu_priorities: Sequence[object],
    k: object,
    *,
    focal_index: object,
    selector: SelectionRule = top_k_select_indices,
    taxonomy: SelectionTaxonomy | None = None,
) -> tuple[int, ...]:
    """Build one focal reference set by literal swap-and-rerun enumeration.

    The default taxonomy conditions on the exact observed selected index set,
    the strongest top-K taxonomy needed by the fixtures.  A caller may instead
    provide another predeclared taxonomy, such as ``lambda support:
    len(support) == K``.  The oracle is intentionally computational rather than
    algebraic and is meant for small-instance verification.
    """

    (
        calibration_score,
        calibration_priority,
        menu_score,
        menu_priority,
        selected_count,
    ) = _fixed_k_inputs(
        calibration_scores,
        calibration_priorities,
        menu_scores,
        menu_priorities,
        k,
    )
    focal = _integer(focal_index, label="Focal menu index", minimum=0)
    if focal >= len(menu_score):
        raise ValueError("The focal menu index is out of range.")

    observed_order = _checked_selection(
        selector,
        menu_score,
        menu_priority,
        selected_count,
    )
    observed_support = frozenset(observed_order)
    if focal not in observed_support:
        raise ValueError("The focal menu unit must be selected by the observed rule.")

    declared_taxonomy: SelectionTaxonomy
    if taxonomy is None:

        def exact_observed_support(support: frozenset[int]) -> bool:
            return support == observed_support

        declared_taxonomy = exact_observed_support
    else:
        declared_taxonomy = taxonomy
    if not _taxonomy_result(declared_taxonomy, observed_support):
        raise RuntimeError("The observed selected support is outside the declared taxonomy.")

    reference: list[int] = []
    for calibration_index, (score, priority) in enumerate(
        zip(calibration_score, calibration_priority, strict=True)
    ):
        swapped_scores = list(menu_score)
        swapped_priorities = list(menu_priority)
        swapped_scores[focal] = score
        swapped_priorities[focal] = priority
        swapped_support = frozenset(
            _checked_selection(
                selector,
                swapped_scores,
                swapped_priorities,
                selected_count,
            )
        )
        if focal in swapped_support and _taxonomy_result(declared_taxonomy, swapped_support):
            reference.append(calibration_index)
    return tuple(reference)


def exact_conformal_rank(reference_size: object, *, alpha: object) -> int:
    """Return ``ceil((R + 1) * (1 - alpha))`` without float ambiguity."""

    size = _integer(reference_size, label="Reference-set size", minimum=0)
    error = _alpha_fraction(alpha)
    return math.ceil(Fraction(size + 1) * (1 - error))


def minimum_finite_threshold_reference_size(*, alpha: object) -> int:
    """Return the exact finite-threshold gate ``ceil(1 / alpha - 1)``.

    A finite cutoff need not produce an informative prediction set; both
    binary labels may still be included.
    """

    error = _alpha_fraction(alpha)
    return math.ceil(1 / error - 1)


def deterministic_binary_jomi_set(
    reference_nonconformity: Sequence[object],
    candidate_nonconformity: Mapping[object, object],
    *,
    alpha: object,
) -> frozenset[int]:
    """Return the deterministic binary JOMI set using an exact conformal rank.

    The threshold is the ``ceil((R+1)(1-alpha))``-th smallest reference score.
    The usual appended ``+infinity`` is handled by failing closed when that
    rank is ``R+1``: such a reference set cannot attain a finite cutoff and
    violates the prospective finite-threshold gate.
    """

    references = _finite_reals(
        reference_nonconformity,
        label="Reference nonconformity scores",
        allow_empty=True,
    )
    if not isinstance(candidate_nonconformity, Mapping):
        raise ValueError("Candidate nonconformity must map both binary labels to scores.")
    candidate: dict[int, float] = {}
    for raw_label, raw_score in candidate_nonconformity.items():
        if isinstance(raw_label, bool) or not isinstance(raw_label, Integral):
            raise ValueError("Candidate nonconformity keys must be the integer labels 0 and 1.")
        label = int(raw_label)
        if label not in {0, 1} or label in candidate:
            raise ValueError("Candidate nonconformity must contain each binary label exactly once.")
        candidate[label] = _finite_reals(
            (raw_score,),
            label=f"Candidate label-{label} nonconformity",
            allow_empty=False,
        )[0]
    if set(candidate) != {0, 1}:
        raise ValueError("Candidate nonconformity must contain each binary label exactly once.")

    rank = exact_conformal_rank(len(references), alpha=alpha)
    if rank > len(references):
        required = minimum_finite_threshold_reference_size(alpha=alpha)
        raise RuntimeError(
            f"Reference size {len(references)} cannot attain a finite conformal cutoff; "
            f"at least {required} references are required at alpha={alpha}."
        )
    threshold = sorted(references)[rank - 1]
    return frozenset(label for label in (0, 1) if candidate[label] <= threshold)


def _rising_factorial(start: int, count: int) -> int:
    result = 1
    for offset in range(count):
        result *= start + offset
    return result


def beta_binomial_reference_size_law(
    calibration_size: object,
    menu_size: object,
    k: object,
) -> BetaBinomialReferenceSizeLaw:
    """Return the exact Beta-binomial law of the Proposition-6 size ``R``."""

    n = _integer(calibration_size, label="Calibration size", minimum=0)
    m = _integer(menu_size, label="Menu size", minimum=1)
    selected_count = _validate_k_for_menu(k, m)
    beta_a = selected_count + 1
    beta_b = m - selected_count
    denominator = _rising_factorial(m + 1, n)
    probabilities = tuple(
        Fraction(
            math.comb(n, reference_size)
            * _rising_factorial(beta_a, reference_size)
            * _rising_factorial(beta_b, n - reference_size),
            denominator,
        )
        for reference_size in range(n + 1)
    )
    cumulative: list[Fraction] = []
    running = Fraction(0, 1)
    for probability in probabilities:
        running += probability
        cumulative.append(running)
    if running != 1:
        raise RuntimeError("The exact reference-size PMF failed to normalize.")
    mean = Fraction(n * (selected_count + 1), m + 1)
    variance = Fraction(
        n * (selected_count + 1) * (m - selected_count) * (m + 1 + n),
        (m + 1) ** 2 * (m + 2),
    )
    enumerated_mean = sum(
        (reference_size * probability for reference_size, probability in enumerate(probabilities)),
        Fraction(0, 1),
    )
    if enumerated_mean != mean:
        raise RuntimeError("The exact reference-size PMF failed its mean identity.")
    enumerated_variance = sum(
        (
            (Fraction(reference_size, 1) - mean) ** 2 * probability
            for reference_size, probability in enumerate(probabilities)
        ),
        Fraction(0, 1),
    )
    if enumerated_variance != variance:
        raise RuntimeError("The exact reference-size PMF failed its variance identity.")
    return BetaBinomialReferenceSizeLaw(
        calibration_size=n,
        menu_size=m,
        k=selected_count,
        beta_a=beta_a,
        beta_b=beta_b,
        pmf=probabilities,
        cdf=tuple(cumulative),
        mean=mean,
        variance=variance,
    )


def beta_binomial_reference_size_pmf(
    calibration_size: object, menu_size: object, k: object
) -> tuple[Fraction, ...]:
    """Return the exact PMF of ``R`` over ``0, ..., calibration_size``."""

    return beta_binomial_reference_size_law(calibration_size, menu_size, k).pmf


def beta_binomial_reference_size_cdf(
    calibration_size: object, menu_size: object, k: object
) -> tuple[Fraction, ...]:
    """Return the exact CDF of ``R`` over ``0, ..., calibration_size``."""

    return beta_binomial_reference_size_law(calibration_size, menu_size, k).cdf


def beta_binomial_reference_size_mean(
    calibration_size: object, menu_size: object, k: object
) -> Fraction:
    """Return ``E[R] = n (K + 1) / (m + 1)`` exactly."""

    return beta_binomial_reference_size_law(calibration_size, menu_size, k).mean


def beta_binomial_reference_size_variance(
    calibration_size: object, menu_size: object, k: object
) -> Fraction:
    """Return the exact variance of the top-K reference count ``R``."""

    return beta_binomial_reference_size_law(calibration_size, menu_size, k).variance


def equal_notional_fcp(miss_indicators: Sequence[object], budget: object) -> EqualNotionalFCP:
    """Return the exact count and dollar FCP under allocation ``B / K``.

    The returned fractions are mathematically identical.  ``budget`` is still
    required and validated so the unit-level notional is explicit rather than
    an implicit normalization convention.
    """

    if isinstance(miss_indicators, (str, bytes)):
        raise ValueError("Miss indicators must be a nonempty binary sequence.")
    raw_misses = tuple(miss_indicators)
    if not raw_misses:
        raise ValueError("Miss indicators must be a nonempty binary sequence.")
    misses: list[int] = []
    for value in raw_misses:
        if isinstance(value, bool):
            misses.append(int(value))
            continue
        if not isinstance(value, Real) or not math.isfinite(float(value)):
            raise ValueError("Miss indicators must contain only zeros and ones.")
        numeric = float(value)
        if numeric not in {0.0, 1.0}:
            raise ValueError("Miss indicators must contain only zeros and ones.")
        misses.append(int(numeric))

    if isinstance(budget, bool) or not isinstance(budget, Real):
        raise ValueError("Budget must be finite and strictly positive.")
    numeric_budget = float(budget)
    if not math.isfinite(numeric_budget) or numeric_budget <= 0.0:
        raise ValueError("Budget must be finite and strictly positive.")

    selected_count = len(misses)
    miss_count = sum(misses)
    common_fcp = Fraction(miss_count, selected_count)
    return EqualNotionalFCP(
        selected_count=selected_count,
        miss_count=miss_count,
        notional_per_unit=numeric_budget / selected_count,
        count_fcp=common_fcp,
        dollar_fcp=common_fcp,
    )


# Compact public names used by future feasibility runners.  The longer names
# above retain the exact theorem or diagnostic role in direct scientific use.
def select_top_k(
    scores: Sequence[object], tie_priorities: Sequence[object], k: object
) -> tuple[int, ...]:
    """Alias for :func:`top_k_select_indices` with an explicit tie argument."""

    return top_k_select_indices(scores, tie_priorities, k)


def top_k_reference_set(
    calibration_scores: Sequence[object],
    calibration_tie_priorities: Sequence[object],
    test_scores: Sequence[object],
    test_tie_priorities: Sequence[object],
    k: object,
) -> tuple[int, ...]:
    """Return the Proposition-6 shortcut under the compact runner API."""

    return proposition6_reference_set(
        calibration_scores,
        calibration_tie_priorities,
        test_scores,
        test_tie_priorities,
        k,
    )


def generic_swap_reference_set(
    calibration_scores: Sequence[object],
    calibration_tie_priorities: Sequence[object],
    test_scores: Sequence[object],
    test_tie_priorities: Sequence[object],
    k: object,
    *,
    focal_index: object,
    selector: SelectionRule = top_k_select_indices,
    taxonomy: SelectionTaxonomy | None = None,
) -> tuple[int, ...]:
    """Expose the literal swap oracle under the compact fixture API."""

    return swap_and_rerun_reference_oracle(
        calibration_scores,
        calibration_tie_priorities,
        test_scores,
        test_tie_priorities,
        k,
        focal_index=focal_index,
        selector=selector,
        taxonomy=taxonomy,
    )


def reference_resolution_size(alpha: object) -> int:
    """Return ``r_alpha`` for the runner's finite-threshold feasibility gate."""

    return minimum_finite_threshold_reference_size(alpha=alpha)


def deterministic_binary_prediction_sets(
    candidate_nonconformity: Sequence[object] | Mapping[object, object],
    reference_nonconformity: Sequence[object],
    alpha: object,
) -> tuple[bool, bool, float]:
    """Return ``(include_label_0, include_label_1, finite_threshold)``.

    ``candidate_nonconformity`` may be a two-element sequence ordered as
    labels ``(0, 1)`` or an explicit mapping with integer keys ``0`` and ``1``.
    """

    candidate_map: dict[object, object]
    if isinstance(candidate_nonconformity, Mapping):
        candidate_map = dict(candidate_nonconformity.items())
    else:
        if isinstance(candidate_nonconformity, (str, bytes)):
            raise ValueError("Candidate nonconformity must contain scores for labels 0 and 1.")
        candidate_values = tuple(candidate_nonconformity)
        if len(candidate_values) != 2:
            raise ValueError("Candidate nonconformity must contain scores for labels 0 and 1.")
        candidate_map = {0: candidate_values[0], 1: candidate_values[1]}
    prediction_set = deterministic_binary_jomi_set(
        reference_nonconformity,
        candidate_map,
        alpha=alpha,
    )
    references = _finite_reals(
        reference_nonconformity,
        label="Reference nonconformity scores",
        allow_empty=True,
    )
    rank = exact_conformal_rank(len(references), alpha=alpha)
    if rank > len(references):
        # The core call above must already have failed closed on this branch.
        raise RuntimeError("An infinite-cutoff rank passed the finite-threshold gate.")
    threshold = sorted(references)[rank - 1]
    return 0 in prediction_set, 1 in prediction_set, threshold
