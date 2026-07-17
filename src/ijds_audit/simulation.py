"""Locked factorial mechanism simulation for binary geometry and C2."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.coverage_transport import binary_miscoverage_bounds
from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_audit.geometry import summarize_binary_geometry
from src.ijds_audit.portfolio import (
    PointPortfolioSession,
    PointPortfolioSolution,
    c2_cap,
    verify_c2_dominance,
)
from src.models.binary_conformal_guardrail import (
    apply_binary_outcome_recipe,
    fit_binary_outcome_recipe,
)


def _allocation_distance(left: PointPortfolioSolution, right: PointPortfolioSolution) -> float:
    total = float(left.total_allocated + right.total_allocated)
    return float(np.abs(left.exposure - right.exposure).sum() / total)


def _sharp_payoff_difference(
    exposure_a: np.ndarray,
    exposure_b: np.ndarray,
    rates: np.ndarray,
    outcomes: np.ndarray,
    *,
    lgd: float,
) -> tuple[float, float]:
    delta = exposure_a - exposure_b
    value_zero = delta * rates
    value_one = delta * -float(lgd)
    observed = np.isfinite(outcomes)
    exact = np.where(outcomes == 1.0, value_one, value_zero)
    lower = np.where(observed, exact, np.minimum(value_zero, value_one))
    upper = np.where(observed, exact, np.maximum(value_zero, value_one))
    return float(lower.sum()), float(upper.sum())


def _one_repetition(
    *,
    seed_sequence: np.random.SeedSequence,
    sample_size: int,
    score_shift: float,
    prevalence_shift: float,
    taxonomy_groups: int,
    censoring_rate: float,
    policy: Mapping[str, Any],
    alpha: float,
) -> dict[str, Any]:
    fit_rng, candidate_rng, censor_rng = [
        np.random.default_rng(stream) for stream in seed_sequence.spawn(3)
    ]
    fit_score = fit_rng.beta(2.0, 18.0, size=sample_size)
    fit_outcome = fit_rng.binomial(1, fit_score).astype(int)
    edges = np.quantile(
        fit_score,
        np.linspace(0.0, 1.0, int(taxonomy_groups) + 1),
        method="linear",
    )
    recipe = fit_binary_outcome_recipe(
        fit_score,
        fit_outcome,
        alpha=float(alpha),
        n_groups=int(taxonomy_groups),
        bin_edges=tuple(float(value) for value in edges),
        taxonomy_provenance="simulation_fit_score_quantiles",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )
    candidate_score = np.clip(
        candidate_rng.beta(2.0, 18.0, size=sample_size) + float(score_shift),
        1e-6,
        1.0 - 1e-6,
    )
    candidate_probability = np.clip(candidate_score + float(prevalence_shift), 1e-6, 1.0 - 1e-6)
    candidate_outcome = candidate_rng.binomial(1, candidate_probability).astype(float)
    censored = censor_rng.random(sample_size) < float(censoring_rate)
    observed_outcome = candidate_outcome.copy()
    observed_outcome[censored] = np.nan
    _, lower, upper = apply_binary_outcome_recipe(candidate_score, recipe)
    observed = np.isfinite(observed_outcome)
    miss_low, miss_high = binary_miscoverage_bounds(observed_outcome, lower, upper)
    geometry = summarize_binary_geometry(lower, upper)

    frame = pd.DataFrame(
        {
            "loan_amnt": np.ones(sample_size, dtype=float),
            "purpose": np.full(sample_size, "all", dtype=object),
        }
    )
    rates = np.clip(
        0.06 + 0.70 * candidate_score + candidate_rng.normal(0.0, 0.01, sample_size), 0.03, 0.40
    )
    lgd = float(policy["lgd"])
    objective = expected_objective_coefficients(candidate_score, rates, lgd=lgd)
    gamma = float(policy["gamma"])
    effective = candidate_score + gamma * (upper - candidate_score)
    guardrail = PointPortfolioSession(
        frame,
        point_score=effective,
        objective_rate=objective,
        budget=float(policy["budget_units"]),
        purpose_cap=float(policy["purpose_cap"]),
        threads=1,
    ).solve(float(policy["risk_tolerance"]))
    point_session = PointPortfolioSession(
        frame,
        point_score=candidate_score,
        objective_rate=objective,
        budget=float(policy["budget_units"]),
        purpose_cap=float(policy["purpose_cap"]),
        threads=1,
    )
    same_cap = point_session.solve(float(policy["risk_tolerance"]))
    contemporaneous_cap = c2_cap(guardrail.exposure, candidate_score)
    contemporaneous = point_session.solve(contemporaneous_cap)
    dominance = verify_c2_dominance(
        guardrail_exposure=guardrail.exposure,
        point_solution=contemporaneous,
        point_score=candidate_score,
        objective_rate=objective,
    )
    c0_lower, c0_upper = _sharp_payoff_difference(
        guardrail.exposure,
        same_cap.exposure,
        rates,
        observed_outcome,
        lgd=lgd,
    )
    c2_lower, c2_upper = _sharp_payoff_difference(
        guardrail.exposure,
        contemporaneous.exposure,
        rates,
        observed_outcome,
        lgd=lgd,
    )
    return {
        "fit_prevalence": float(np.mean(fit_outcome)),
        "candidate_prevalence": float(np.mean(candidate_outcome)),
        "resolved_rows": int(observed.sum()),
        "coverage_resolved": float(1.0 - miss_low[observed].mean()),
        "coverage_lower": float(1.0 - miss_high.mean()),
        "coverage_upper": float(1.0 - miss_low.mean()),
        "guardrail_weighted_effective_score": guardrail.weighted_point_score,
        "guardrail_weighted_point_score": c2_cap(guardrail.exposure, candidate_score),
        "same_cap_allocation_distance": _allocation_distance(guardrail, same_cap),
        "c2_allocation_distance": _allocation_distance(guardrail, contemporaneous),
        "same_cap_payoff_difference_lower": c0_lower,
        "same_cap_payoff_difference_upper": c0_upper,
        "c2_payoff_difference_lower": c2_lower,
        "c2_payoff_difference_upper": c2_upper,
        **dominance,
        **geometry,
    }


def run_factorial_simulation(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run every locked factorial cell and return repetitions plus cell summaries."""
    simulation = config["simulation"]
    if simulation.get("enabled") is not True:
        raise ValueError("The V4 simulation must remain enabled.")
    rows: list[dict[str, Any]] = []
    grid = product(
        enumerate(simulation["score_shift_grid"]),
        enumerate(simulation["prevalence_shift_grid"]),
        enumerate(simulation["taxonomy_groups_grid"]),
        enumerate(simulation["censoring_rate_grid"]),
    )
    for (score_index, score_shift), (prevalence_index, prevalence_shift), (
        group_index,
        groups,
    ), (censor_index, censoring) in grid:
        for repetition in range(int(simulation["repetitions"])):
            sequence = np.random.SeedSequence(
                [
                    int(simulation["random_seed"]),
                    score_index,
                    prevalence_index,
                    group_index,
                    censor_index,
                    repetition,
                ]
            )
            rows.append(
                {
                    "score_shift": float(score_shift),
                    "prevalence_shift": float(prevalence_shift),
                    "taxonomy_groups": int(groups),
                    "censoring_rate": float(censoring),
                    "repetition": repetition,
                    **_one_repetition(
                        seed_sequence=sequence,
                        sample_size=int(simulation["sample_size"]),
                        score_shift=float(score_shift),
                        prevalence_shift=float(prevalence_shift),
                        taxonomy_groups=int(groups),
                        censoring_rate=float(censoring),
                        policy=simulation["mechanism_policy"],
                        alpha=float(config["conformal"]["alpha"]),
                    ),
                }
            )
    repetitions = pd.DataFrame(rows)
    keys = ["score_shift", "prevalence_shift", "taxonomy_groups", "censoring_rate"]
    numeric = [
        column
        for column in repetitions.select_dtypes(include=[np.number]).columns
        if column not in {*keys, "repetition"}
    ]
    summary = repetitions.groupby(keys, observed=True, sort=True)[numeric].agg(
        ["mean", "std", "min", "max"]
    )
    summary.columns = [f"{column}_{statistic}" for column, statistic in summary.columns]
    return repetitions, summary.reset_index()
