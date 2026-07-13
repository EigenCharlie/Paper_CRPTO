"""Decision-active synthetic mechanism experiment for the IJDS audit."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

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

FACTOR_COLUMNS = (
    "score_shift",
    "calibration_log_odds_shift",
    "taxonomy_groups",
    "normalized_cap_position",
    "censoring_rate",
)

LOCKED_GRID = {
    "score_shift_grid": (0.0, 0.08),
    "calibration_log_odds_shift_grid": (0.0, 0.75, 1.5),
    "taxonomy_groups_grid": (1, 5),
    "normalized_cap_position_grid": (0.25, 0.5, 0.75),
    "censoring_rate_grid": (0.0, 0.15),
}


def validate_locked_decision_active_config(config: Mapping[str, Any]) -> None:
    """Reject changes to the predeclared full-factorial simulation contract."""
    simulation = config.get("decision_active_simulation")
    if not isinstance(simulation, Mapping) or simulation.get("enabled") is not True:
        raise ValueError("The locked decision-active simulation must remain enabled.")
    if simulation.get("role") != "mechanism_only_no_empirical_sign_validation":
        raise ValueError("The simulation cannot be promoted to empirical validation.")
    for name, expected in LOCKED_GRID.items():
        observed = tuple(float(value) for value in simulation[name])
        if observed != expected:
            raise ValueError(f"Locked decision-active grid changed for {name}: {observed}.")
    cell_count = int(np.prod([len(values) for values in LOCKED_GRID.values()]))
    repetitions = int(simulation["repetitions"])
    if cell_count != 72 or repetitions != 50 or cell_count * repetitions != 3_600:
        raise ValueError("The locked simulation must contain 72 cells and 3,600 repetitions.")
    candidate_size = int(simulation["candidate_sample_size"])
    funded_units = int(simulation["funded_units"])
    if int(simulation["fit_sample_size"]) <= 0 or not 0 < funded_units < candidate_size:
        raise ValueError("Locked simulation sample sizes or funded budget are invalid.")
    if int(simulation["random_seed"]) != 20_260_712:
        raise ValueError("The locked simulation seed changed.")
    if simulation.get("factor_pairing") != "common_random_numbers_by_repetition":
        raise ValueError("The locked factorial must retain paired common random numbers.")
    if config["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Decision-active outputs must retain hard no-overwrite semantics.")


def _allocation_distance(left: PointPortfolioSolution, right: PointPortfolioSolution) -> float:
    total = float(left.total_allocated + right.total_allocated)
    return float(np.abs(left.exposure - right.exposure).sum() / total)


def _weighted_mean(exposure: np.ndarray, values: np.ndarray) -> float:
    total = float(exposure.sum())
    if total <= 0.0:
        raise ValueError("Weighted mean requires positive exposure.")
    return float(exposure @ values / total)


def _sharp_binary_sum_bounds(
    value_if_zero: np.ndarray,
    value_if_one: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    observed = np.isfinite(outcomes)
    exact = np.where(outcomes == 1.0, value_if_one, value_if_zero)
    lower = np.where(observed, exact, np.minimum(value_if_zero, value_if_one))
    upper = np.where(observed, exact, np.maximum(value_if_zero, value_if_one))
    return float(lower.sum()), float(upper.sum())


def _sharp_payoff_difference(
    exposure_a: np.ndarray,
    exposure_b: np.ndarray,
    rates: np.ndarray,
    outcomes: np.ndarray,
    *,
    lgd: float,
) -> tuple[float, float]:
    delta = exposure_a - exposure_b
    return _sharp_binary_sum_bounds(delta * rates, delta * -float(lgd), outcomes)


def _sharp_default_difference(
    exposure_a: np.ndarray,
    exposure_b: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    total = float(exposure_a.sum())
    lower, upper = _sharp_binary_sum_bounds(
        np.zeros(len(exposure_a), dtype=float), exposure_a - exposure_b, outcomes
    )
    return lower / total, upper / total


def _sharp_miscoverage_difference(
    exposure_a: np.ndarray,
    exposure_b: np.ndarray,
    lower_endpoint: np.ndarray,
    upper_endpoint: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    total = float(exposure_a.sum())
    delta = exposure_a - exposure_b
    miss_if_zero = (lower_endpoint > 0.0).astype(float)
    miss_if_one = (upper_endpoint < 1.0).astype(float)
    lower, upper = _sharp_binary_sum_bounds(
        delta * miss_if_zero,
        delta * miss_if_one,
        outcomes,
    )
    return lower / total, upper / total


def _require_bound_contains(
    lower: float, upper: float, value: float, *, name: str, tolerance: float = 1e-12
) -> None:
    if value < lower - tolerance or value > upper + tolerance:
        raise RuntimeError(f"{name}={value:.12g} lies outside [{lower:.12g}, {upper:.12g}].")


def _selected_default_bounds(
    exposure: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    total = float(exposure.sum())
    lower, upper = _sharp_binary_sum_bounds(
        np.zeros(len(exposure), dtype=float), exposure, outcomes
    )
    return lower / total, upper / total


def _selected_miscoverage_bounds(
    exposure: np.ndarray,
    lower_endpoint: np.ndarray,
    upper_endpoint: np.ndarray,
    outcomes: np.ndarray,
) -> tuple[float, float]:
    total = float(exposure.sum())
    miss_if_zero = (lower_endpoint > 0.0).astype(float)
    miss_if_one = (upper_endpoint < 1.0).astype(float)
    lower, upper = _sharp_binary_sum_bounds(
        exposure * miss_if_zero,
        exposure * miss_if_one,
        outcomes,
    )
    return lower / total, upper / total


def _true_probability(score: np.ndarray, log_odds_shift: float) -> np.ndarray:
    clipped = np.clip(score, 1e-6, 1.0 - 1e-6)
    logit = np.log(clipped) - np.log1p(-clipped)
    return 1.0 / (1.0 + np.exp(-(logit + float(log_odds_shift))))


def _minimum_equal_unit_score(score: np.ndarray, funded_units: int) -> float:
    if funded_units <= 0 or funded_units > len(score):
        raise ValueError("funded_units must be in [1, number of candidates].")
    selected = np.partition(score, funded_units - 1)[:funded_units]
    return float(np.mean(selected))


def _one_repetition(
    *,
    seed_sequence: np.random.SeedSequence,
    score_shift: float,
    calibration_log_odds_shift: float,
    taxonomy_groups: int,
    normalized_cap_position: float,
    censoring_rate: float,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    simulation = config["decision_active_simulation"]
    fit_rng, candidate_rng, outcome_rng, censor_rng = [
        np.random.default_rng(stream) for stream in seed_sequence.spawn(4)
    ]
    beta_a, beta_b = (float(value) for value in simulation["beta_shape"])
    fit_size = int(simulation["fit_sample_size"])
    candidate_size = int(simulation["candidate_sample_size"])
    funded_units = int(simulation["funded_units"])
    alpha = float(config["conformal"]["alpha"])

    fit_score = fit_rng.beta(beta_a, beta_b, size=fit_size)
    fit_outcome = (fit_rng.random(fit_size) < fit_score).astype(int)
    edges = np.quantile(
        fit_score,
        np.linspace(0.0, 1.0, int(taxonomy_groups) + 1),
        method="linear",
    )
    if bool(np.any(np.diff(edges) <= 0.0)):
        raise RuntimeError("Decision-active simulation produced repeated taxonomy edges.")
    recipe = fit_binary_outcome_recipe(
        fit_score,
        fit_outcome,
        alpha=alpha,
        n_groups=int(taxonomy_groups),
        bin_edges=tuple(float(value) for value in edges),
        taxonomy_provenance="decision_active_simulation_fit_score_quantiles",
        taxonomy_method="fixed_empirical_linear_score_quantiles",
    )

    candidate_base = candidate_rng.beta(beta_a, beta_b, size=candidate_size)
    candidate_score = np.clip(candidate_base + float(score_shift), 1e-6, 1.0 - 1e-6)
    _, lower, upper = apply_binary_outcome_recipe(candidate_score, recipe)
    gamma = float(simulation["gamma"])
    effective_score = candidate_score + gamma * (upper - candidate_score)
    rate_config = simulation["rate"]
    rates = np.clip(
        float(rate_config["intercept"])
        + float(rate_config["score_slope"]) * candidate_score
        + candidate_rng.normal(0.0, float(rate_config["noise_sd"]), candidate_size),
        float(rate_config["lower"]),
        float(rate_config["upper"]),
    )
    lgd = float(simulation["lgd"])
    objective = expected_objective_coefficients(candidate_score, rates, lgd=lgd)
    frame = pd.DataFrame(
        {
            "loan_amnt": np.ones(candidate_size, dtype=float),
            "purpose": np.full(candidate_size, "all", dtype=object),
        }
    )
    budget = float(funded_units)
    purpose_cap = float(simulation["purpose_cap"])
    threads = int(simulation["threads"])
    guardrail_session = PointPortfolioSession(
        frame,
        point_score=effective_score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=purpose_cap,
        threads=threads,
    )
    unconstrained = guardrail_session.solve(1.0)
    minimum_score = _minimum_equal_unit_score(effective_score, funded_units)
    unconstrained_score = float(unconstrained.weighted_point_score)
    score_range = unconstrained_score - minimum_score
    if score_range < float(simulation["minimum_effective_score_range"]):
        raise RuntimeError(
            f"Decision-active score range {score_range:.3e} is below the locked minimum."
        )
    guardrail_cap = minimum_score + float(normalized_cap_position) * score_range
    guardrail = guardrail_session.solve(guardrail_cap)
    binding_slack = float(guardrail_cap - guardrail.weighted_point_score)
    if abs(binding_slack) > float(simulation["binding_tolerance"]):
        raise RuntimeError(f"Guardrail cap is not decision-active: slack={binding_slack:.3e}.")

    point_session = PointPortfolioSession(
        frame,
        point_score=candidate_score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=purpose_cap,
        threads=threads,
    )
    c0 = point_session.solve(guardrail_cap)
    c0_objective_dominance = float(c0.objective_value - guardrail.objective_value)
    if c0_objective_dominance < -float(simulation["objective_dominance_tolerance"]):
        raise RuntimeError(
            "Same-cap point objective dominance failed by "
            f"{c0_objective_dominance:.6f} simulation-currency units."
        )
    c2_risk_cap = c2_cap(guardrail.exposure, candidate_score)
    c2 = point_session.solve(c2_risk_cap)
    c2_residual = float(c2.weighted_point_score - c2_risk_cap)
    if abs(c2_residual) > float(simulation["c2_match_tolerance"]):
        raise RuntimeError(f"Decision-active C2 moment mismatch: {c2_residual:.3e}.")
    dominance = verify_c2_dominance(
        guardrail_exposure=guardrail.exposure,
        point_solution=c2,
        point_score=candidate_score,
        objective_rate=objective,
        tolerance=float(simulation["objective_dominance_tolerance"]),
    )

    # Candidate outcomes are intentionally generated only after all allocations.
    true_probability = _true_probability(candidate_score, calibration_log_odds_shift)
    candidate_outcome = (outcome_rng.random(candidate_size) < true_probability).astype(float)
    observed_outcome = candidate_outcome.copy()
    censored = censor_rng.random(candidate_size) < float(censoring_rate)
    observed_outcome[censored] = np.nan
    observed = np.isfinite(observed_outcome)
    if not bool(observed.any()):
        raise RuntimeError("Decision-active simulation produced no observed outcomes.")
    covered = (observed_outcome >= lower) & (observed_outcome <= upper)
    observed_covered = int(covered[observed].sum())
    full_covered = (candidate_outcome >= lower) & (candidate_outcome <= upper)
    full_coverage = float(np.mean(full_covered))
    coverage_lower = float(observed_covered / candidate_size)
    coverage_upper = float((observed_covered + censored.sum()) / candidate_size)
    _require_bound_contains(
        coverage_lower,
        coverage_upper,
        full_coverage,
        name="full candidate coverage",
    )
    geometry = summarize_binary_geometry(lower, upper)

    guard_default = _selected_default_bounds(guardrail.exposure, observed_outcome)
    c0_default = _selected_default_bounds(c0.exposure, observed_outcome)
    c2_default = _selected_default_bounds(c2.exposure, observed_outcome)
    guard_miss = _selected_miscoverage_bounds(guardrail.exposure, lower, upper, observed_outcome)
    c0_miss = _selected_miscoverage_bounds(c0.exposure, lower, upper, observed_outcome)
    c2_miss = _selected_miscoverage_bounds(c2.exposure, lower, upper, observed_outcome)
    c0_payoff = _sharp_payoff_difference(
        guardrail.exposure,
        c0.exposure,
        rates,
        observed_outcome,
        lgd=lgd,
    )
    c2_payoff = _sharp_payoff_difference(
        guardrail.exposure,
        c2.exposure,
        rates,
        observed_outcome,
        lgd=lgd,
    )
    c0_default_difference = _sharp_default_difference(
        guardrail.exposure, c0.exposure, observed_outcome
    )
    c2_default_difference = _sharp_default_difference(
        guardrail.exposure, c2.exposure, observed_outcome
    )
    c0_miscoverage_difference = _sharp_miscoverage_difference(
        guardrail.exposure,
        c0.exposure,
        lower,
        upper,
        observed_outcome,
    )
    c2_miscoverage_difference = _sharp_miscoverage_difference(
        guardrail.exposure,
        c2.exposure,
        lower,
        upper,
        observed_outcome,
    )
    c0_full_payoff = _sharp_payoff_difference(
        guardrail.exposure,
        c0.exposure,
        rates,
        candidate_outcome,
        lgd=lgd,
    )[0]
    c2_full_payoff = _sharp_payoff_difference(
        guardrail.exposure,
        c2.exposure,
        rates,
        candidate_outcome,
        lgd=lgd,
    )[0]
    c0_full_default = _sharp_default_difference(guardrail.exposure, c0.exposure, candidate_outcome)[
        0
    ]
    c2_full_default = _sharp_default_difference(guardrail.exposure, c2.exposure, candidate_outcome)[
        0
    ]
    c0_full_miscoverage = _sharp_miscoverage_difference(
        guardrail.exposure,
        c0.exposure,
        lower,
        upper,
        candidate_outcome,
    )[0]
    c2_full_miscoverage = _sharp_miscoverage_difference(
        guardrail.exposure,
        c2.exposure,
        lower,
        upper,
        candidate_outcome,
    )[0]
    for name, bounds, full_value in (
        ("C0 payoff", c0_payoff, c0_full_payoff),
        ("C2 payoff", c2_payoff, c2_full_payoff),
        ("C0 default", c0_default_difference, c0_full_default),
        ("C2 default", c2_default_difference, c2_full_default),
        ("C0 miscoverage", c0_miscoverage_difference, c0_full_miscoverage),
        ("C2 miscoverage", c2_miscoverage_difference, c2_full_miscoverage),
    ):
        _require_bound_contains(*bounds, full_value, name=name)
    distance_tolerance = float(simulation["allocation_distance_tolerance"])
    c0_distance = _allocation_distance(guardrail, c0)
    c2_distance = _allocation_distance(guardrail, c2)
    return {
        "fit_prevalence": float(np.mean(fit_outcome)),
        "candidate_true_probability_mean": float(np.mean(true_probability)),
        "candidate_outcome_prevalence": float(np.mean(candidate_outcome)),
        "candidate_resolved_rows": int(observed.sum()),
        "candidate_coverage_resolved": float(np.mean(covered[observed])),
        "candidate_coverage_full": full_coverage,
        "candidate_coverage_lower": coverage_lower,
        "candidate_coverage_upper": coverage_upper,
        "recipe_group_count_min": int(min(recipe.group_counts)),
        "recipe_group_count_max": int(max(recipe.group_counts)),
        "recipe_residual_quantile_min": float(min(recipe.residual_quantiles)),
        "recipe_residual_quantile_max": float(max(recipe.residual_quantiles)),
        "effective_score_minimum_portfolio": minimum_score,
        "effective_score_unconstrained_portfolio": unconstrained_score,
        "effective_score_decision_range": score_range,
        "guardrail_cap": guardrail_cap,
        "guardrail_weighted_effective_score": float(guardrail.weighted_point_score),
        "guardrail_realized_normalized_cap_position": float(
            (guardrail.weighted_point_score - minimum_score) / score_range
        ),
        "guardrail_cap_slack": binding_slack,
        "guardrail_cap_binding": bool(abs(binding_slack) <= float(simulation["binding_tolerance"])),
        "guardrail_budget_residual": float(guardrail.total_allocated - budget),
        "c0_budget_residual": float(c0.total_allocated - budget),
        "c2_budget_residual": float(c2.total_allocated - budget),
        "guardrail_weighted_point_score": c2_risk_cap,
        "c0_weighted_point_score": float(c0.weighted_point_score),
        "c0_same_numeric_cap_slack": float(guardrail_cap - c0.weighted_point_score),
        "c2_weighted_point_score": float(c2.weighted_point_score),
        "c2_cap": c2_risk_cap,
        "c2_match_residual": c2_residual,
        "guardrail_expected_objective": float(guardrail.objective_value),
        "c0_expected_objective": float(c0.objective_value),
        "c2_expected_objective": float(c2.objective_value),
        "guardrail_minus_c0_expected_objective": float(
            guardrail.objective_value - c0.objective_value
        ),
        "c0_point_minus_guardrail_objective": c0_objective_dominance,
        "guardrail_minus_c2_expected_objective": float(
            guardrail.objective_value - c2.objective_value
        ),
        "c0_allocation_distance": c0_distance,
        "c2_allocation_distance": c2_distance,
        "c0_allocation_changed": bool(c0_distance > distance_tolerance),
        "c2_allocation_changed": bool(c2_distance > distance_tolerance),
        "guardrail_true_risk": _weighted_mean(guardrail.exposure, true_probability),
        "c0_true_risk": _weighted_mean(c0.exposure, true_probability),
        "c2_true_risk": _weighted_mean(c2.exposure, true_probability),
        "guardrail_default_lower": guard_default[0],
        "guardrail_default_upper": guard_default[1],
        "c0_default_lower": c0_default[0],
        "c0_default_upper": c0_default[1],
        "c2_default_lower": c2_default[0],
        "c2_default_upper": c2_default[1],
        "guardrail_miscoverage_lower": guard_miss[0],
        "guardrail_miscoverage_upper": guard_miss[1],
        "c0_miscoverage_lower": c0_miss[0],
        "c0_miscoverage_upper": c0_miss[1],
        "c2_miscoverage_lower": c2_miss[0],
        "c2_miscoverage_upper": c2_miss[1],
        "guardrail_minus_c0_payoff_lower": c0_payoff[0],
        "guardrail_minus_c0_payoff_upper": c0_payoff[1],
        "guardrail_minus_c0_payoff_full": c0_full_payoff,
        "guardrail_minus_c2_payoff_lower": c2_payoff[0],
        "guardrail_minus_c2_payoff_upper": c2_payoff[1],
        "guardrail_minus_c2_payoff_full": c2_full_payoff,
        "guardrail_minus_c0_default_lower": c0_default_difference[0],
        "guardrail_minus_c0_default_upper": c0_default_difference[1],
        "guardrail_minus_c0_default_full": c0_full_default,
        "guardrail_minus_c2_default_lower": c2_default_difference[0],
        "guardrail_minus_c2_default_upper": c2_default_difference[1],
        "guardrail_minus_c2_default_full": c2_full_default,
        "guardrail_minus_c0_miscoverage_lower": c0_miscoverage_difference[0],
        "guardrail_minus_c0_miscoverage_upper": c0_miscoverage_difference[1],
        "guardrail_minus_c0_miscoverage_full": c0_full_miscoverage,
        "guardrail_minus_c2_miscoverage_lower": c2_miscoverage_difference[0],
        "guardrail_minus_c2_miscoverage_upper": c2_miscoverage_difference[1],
        "guardrail_minus_c2_miscoverage_full": c2_full_miscoverage,
        **dominance,
        **geometry,
    }


def run_decision_active_simulation(
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run every locked decision-active factorial cell."""
    simulation = config["decision_active_simulation"]
    if simulation.get("enabled") is not True:
        raise ValueError("The decision-active simulation must remain enabled.")
    rows: list[dict[str, Any]] = []
    grid = product(
        enumerate(simulation["score_shift_grid"]),
        enumerate(simulation["calibration_log_odds_shift_grid"]),
        enumerate(simulation["taxonomy_groups_grid"]),
        enumerate(simulation["normalized_cap_position_grid"]),
        enumerate(simulation["censoring_rate_grid"]),
    )
    for (_, score_shift), (_, calibration_shift), (_, groups), (_, cap_position), (
        _,
        censoring_rate,
    ) in grid:
        for repetition in range(int(simulation["repetitions"])):
            sequence = np.random.SeedSequence(
                [
                    int(simulation["random_seed"]),
                    repetition,
                ]
            )
            rows.append(
                {
                    "score_shift": float(score_shift),
                    "calibration_log_odds_shift": float(calibration_shift),
                    "taxonomy_groups": int(groups),
                    "normalized_cap_position": float(cap_position),
                    "censoring_rate": float(censoring_rate),
                    "repetition": repetition,
                    **_one_repetition(
                        seed_sequence=sequence,
                        score_shift=float(score_shift),
                        calibration_log_odds_shift=float(calibration_shift),
                        taxonomy_groups=int(groups),
                        normalized_cap_position=float(cap_position),
                        censoring_rate=float(censoring_rate),
                        config=config,
                    ),
                }
            )
    repetitions = pd.DataFrame(rows)
    numeric = [
        column
        for column in repetitions.select_dtypes(include=[np.number, "bool"]).columns
        if column not in {*FACTOR_COLUMNS, "repetition"}
    ]
    summary = repetitions.groupby(list(FACTOR_COLUMNS), observed=True, sort=True)[numeric].agg(
        ["mean", "std", "min", "max"]
    )
    summary.columns = [f"{column}_{statistic}" for column, statistic in summary.columns]
    return repetitions, summary.reset_index()
