"""Build the complete outcome-free normalized/objective frontier census."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_audit.policy_support import point_basis_diagnostics
from src.ijds_audit.portfolio import PointPortfolioSession, PointPortfolioSolution
from src.ijds_challengers.archive import monthly_frames
from src.ijds_challengers.frontier import (
    ObjectiveFloorPortfolioSession,
    ScoreFrontierSolution,
    common_objective_target,
    normalized_exposure_distance,
    normalized_score_cap,
    solve_glop_portfolio,
)
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)


@dataclass(frozen=True)
class FrontierBuild:
    """All deterministic artifacts produced before the outcome join."""

    solve_records: pd.DataFrame
    allocations: pd.DataFrame
    endpoint_diagnostics: pd.DataFrame
    objective_optimum_diagnostics: pd.DataFrame
    order_sensitivity: pd.DataFrame
    independent_validation: pd.DataFrame


@dataclass(frozen=True)
class _GammaState:
    score: np.ndarray
    minimum_score: float
    score_at_objective: float
    score_range: float
    minimum_objective: float
    normalized_session: PointPortfolioSession
    objective_session: ObjectiveFloorPortfolioSession


@dataclass(frozen=True)
class _RulerSolution:
    ruler: str
    threshold: float
    solution: ScoreFrontierSolution
    cap: float | None
    objective_target: float | None


@dataclass(frozen=True)
class _ObjectiveOptimum:
    solution: ScoreFrontierSolution
    diagnostics: dict[str, Any]


def build_outcome_free_frontiers(
    base: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    *,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
) -> FrontierBuild:
    """Solve every locked V1b cell without accepting an outcome dataframe."""
    _assert_outcome_free(base, config=config)
    frontier = config["frontier"]
    solver_config = config["solver"]
    gamma_grid = tuple(float(value) for value in frontier["gamma_grid"])
    coordinates = tuple(float(value) for value in frontier["coordinate_grid"])
    budget = float(parent_config["policy"]["budget"])
    purpose_cap = float(parent_config["policy"]["max_concentration_by_purpose"])
    lgd = float(parent_config["payoff"]["lgd"])
    threads = int(solver_config["threads"])
    time_limit = int(solver_config["time_limit_seconds"])
    allocation_tolerance = float(solver_config["allocation_tolerance"])
    budget_tolerance = float(solver_config["budget_residual_tolerance_dollars"])
    normalized_config = frontier["normalized_score"]
    objective_config = frontier["objective_matched"]
    optimum_config = frontier["objective_optimum"]
    validation_periods = {
        str(value) for value in solver_config["independent_validation"]["periods"]
    }

    records: list[dict[str, Any]] = []
    allocation_frames: list[pd.DataFrame] = []
    endpoint_rows: list[dict[str, Any]] = []
    optimum_rows: list[dict[str, Any]] = []
    order_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    objective_cache: dict[tuple[str, str], _ObjectiveOptimum] = {}
    windows = recipes["catboost_platt"]

    for window_index, (window_id, group_recipes) in enumerate(sorted(windows.items()), start=1):
        logger.info("Frontier window {}/8: {}", window_index, window_id)
        point_all = base["pd_point"].to_numpy(dtype=float)
        _, lower_all, upper_all = apply_binary_outcome_recipe(point_all, group_recipes[5])
        window_base = base.assign(
            conformal_lower=lower_all,
            conformal_upper=upper_all,
        )
        for role in frontier["roles"]:
            monthly = monthly_frames(window_base, str(role))
            expected_months = (
                int(frontier["expected_development_months"])
                if role == "policy_development"
                else int(frontier["expected_primary_months"])
            )
            if len(monthly) != expected_months:
                raise RuntimeError(
                    f"{window_id} {role} has {len(monthly)} months, not {expected_months}."
                )
            for period, month in monthly:
                point = month["pd_point"].to_numpy(dtype=float)
                upper = month["conformal_upper"].to_numpy(dtype=float)
                rates = month["contractual_rate"].to_numpy(dtype=float)
                objective = expected_objective_coefficients(point, rates, lgd=lgd)
                cache_key = (str(role), period)
                optimum = objective_cache.get(cache_key)
                if optimum is None:
                    optimum = _solve_objective_optimum(
                        month,
                        point_score=point,
                        objective_rate=objective,
                        budget=budget,
                        purpose_cap=purpose_cap,
                        time_limit=time_limit,
                        threads=threads,
                        role=str(role),
                        period=period,
                        optimum_config=optimum_config,
                        solver_config=solver_config,
                    )
                    objective_cache[cache_key] = optimum
                    optimum_rows.append(optimum.diagnostics)
                unconstrained = optimum.solution
                gamma_states = _build_gamma_states(
                    month,
                    point=point,
                    upper=upper,
                    objective=objective,
                    unconstrained=unconstrained,
                    gamma_grid=gamma_grid,
                    window_id=window_id,
                    role=str(role),
                    period=period,
                    budget=budget,
                    purpose_cap=purpose_cap,
                    time_limit=time_limit,
                    threads=threads,
                    normalized_config=normalized_config,
                )
                common_lower, _ = common_objective_target(
                    minimum_objectives=[state.minimum_objective for state in gamma_states.values()],
                    objective_optimum=unconstrained.objective_value,
                    coordinate=0.0,
                    minimum_range=float(objective_config["minimum_objective_range_dollars"]),
                )
                endpoint_solutions: dict[tuple[str, float, float], ScoreFrontierSolution] = {}
                for gamma, state in gamma_states.items():
                    for coordinate in coordinates:
                        ruler_solutions = _solve_rulers(
                            state,
                            gamma_states=gamma_states,
                            coordinate=coordinate,
                            unconstrained_objective=unconstrained.objective_value,
                            window_id=window_id,
                            role=str(role),
                            period=period,
                            gamma=gamma,
                            normalized_config=normalized_config,
                            objective_config=objective_config,
                        )
                        for solved in ruler_solutions:
                            _append_solution(
                                records,
                                allocation_frames,
                                month=month,
                                score=state.score,
                                objective=objective,
                                solution=solved.solution,
                                window_id=window_id,
                                role=str(role),
                                period=period,
                                gamma=gamma,
                                ruler=solved.ruler,
                                coordinate=coordinate,
                                cap=solved.cap,
                                objective_target=solved.objective_target,
                                common_objective_lower=common_lower,
                                state=state,
                                unconstrained_objective=unconstrained.objective_value,
                                allocation_tolerance=allocation_tolerance,
                                budget=budget,
                            )
                            if str(role) == "primary_oot" and gamma in {0.0, 1.0}:
                                endpoint_solutions[(solved.ruler, coordinate, gamma)] = (
                                    solved.solution
                                )
                                order_rows.append(
                                    _order_diagnostic(
                                        month,
                                        score=state.score,
                                        objective=objective,
                                        original=solved.solution,
                                        window_id=window_id,
                                        role=str(role),
                                        period=period,
                                        gamma=gamma,
                                        ruler=solved.ruler,
                                        coordinate=coordinate,
                                        threshold=solved.threshold,
                                        budget=budget,
                                        purpose_cap=purpose_cap,
                                        time_limit=time_limit,
                                        threads=threads,
                                    )
                                )
                                if period in validation_periods:
                                    validation_rows.append(
                                        _independent_diagnostic(
                                            month,
                                            score=state.score,
                                            objective=objective,
                                            original=solved.solution,
                                            window_id=window_id,
                                            role=str(role),
                                            period=period,
                                            gamma=gamma,
                                            ruler=solved.ruler,
                                            coordinate=coordinate,
                                            threshold=solved.threshold,
                                            budget=budget,
                                            purpose_cap=purpose_cap,
                                        )
                                    )
                if str(role) == "primary_oot":
                    for ruler in ("objective_matched", "normalized_score"):
                        for coordinate in coordinates:
                            full = endpoint_solutions[(ruler, coordinate, 1.0)]
                            point_solution = endpoint_solutions[(ruler, coordinate, 0.0)]
                            endpoint_rows.append(
                                {
                                    "window_id": window_id,
                                    "role": str(role),
                                    "period": period,
                                    "ruler": ruler,
                                    "coordinate": coordinate,
                                    "endpoint_contrast": "gamma_1_minus_gamma_0",
                                    "normalized_exposure_distance": normalized_exposure_distance(
                                        full.exposure,
                                        point_solution.exposure,
                                        budget=budget,
                                    ),
                                    "objective_difference": float(
                                        full.objective_value - point_solution.objective_value
                                    ),
                                    "full_endpoint_weighted_score": float(full.weighted_score),
                                    "point_endpoint_weighted_score": float(
                                        point_solution.weighted_score
                                    ),
                                    "full_endpoint_point_moment": float(
                                        full.exposure @ point / budget
                                    ),
                                    "point_endpoint_point_moment": float(
                                        point_solution.exposure @ point / budget
                                    ),
                                    "unconstrained_objective": float(unconstrained.objective_value),
                                }
                            )

    result = FrontierBuild(
        solve_records=pd.DataFrame(records),
        allocations=pd.concat(allocation_frames, ignore_index=True),
        endpoint_diagnostics=pd.DataFrame(endpoint_rows),
        objective_optimum_diagnostics=pd.DataFrame(optimum_rows),
        order_sensitivity=pd.DataFrame(order_rows),
        independent_validation=pd.DataFrame(validation_rows),
    )
    _validate_complete_build(
        result, config=config, budget=budget, budget_tolerance=budget_tolerance
    )
    return result


def _solve_objective_optimum(
    month: pd.DataFrame,
    *,
    point_score: np.ndarray,
    objective_rate: np.ndarray,
    budget: float,
    purpose_cap: float,
    time_limit: int,
    threads: int,
    role: str,
    period: str,
    optimum_config: Mapping[str, Any],
    solver_config: Mapping[str, Any],
) -> _ObjectiveOptimum:
    session = PointPortfolioSession(
        month,
        point_score=point_score,
        objective_rate=objective_rate,
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=time_limit,
        threads=threads,
    )
    raw_solution = session.solve(1.0)
    solution = _from_point_solution(raw_solution)
    basis = point_basis_diagnostics(
        session,
        raw_solution,
        dual_tolerance=float(optimum_config["dual_tolerance"]),
        primal_tolerance=float(optimum_config["primal_tolerance"]),
    )
    minimum_reduced_cost = float(basis["minimum_absolute_nonbasic_reduced_cost"])
    near_zero = int(basis["near_zero_nonbasic_reduced_costs"])
    if near_zero > 0 or minimum_reduced_cost <= float(optimum_config["dual_tolerance"]):
        raise RuntimeError(
            f"Objective optimum has a near-zero nonbasic reduced cost for "
            f"{role} {period}: minimum={minimum_reduced_cost:.12g}, count={near_zero}."
        )

    reverse = month.iloc[::-1].reset_index(drop=True)
    reversed_solution = PointPortfolioSession(
        reverse,
        point_score=point_score[::-1],
        objective_rate=objective_rate[::-1],
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=time_limit,
        threads=threads,
    ).solve(1.0)
    reverse_exposure = pd.Series(
        reversed_solution.exposure,
        index=reverse["id"].astype("string"),
    )
    aligned = month["id"].astype("string").map(reverse_exposure).to_numpy(dtype=float)
    exposure_distance = normalized_exposure_distance(
        solution.exposure,
        aligned,
        budget=budget,
    )
    objective_difference = float(reversed_solution.objective_value - solution.objective_value)
    if exposure_distance > float(solver_config["order_exposure_distance_tolerance"]):
        raise RuntimeError(f"ID reversal changed the objective optimum for {role} {period}.")
    if abs(objective_difference) > float(solver_config["order_objective_tolerance_dollars"]):
        raise RuntimeError(f"ID reversal changed the objective value for {role} {period}.")

    return _ObjectiveOptimum(
        solution=solution,
        diagnostics={
            "role": role,
            "period": period,
            "n_candidates": int(len(month)),
            "objective_value": float(solution.objective_value),
            "weighted_point_score": float(solution.weighted_score),
            "minimum_absolute_nonbasic_reduced_cost": minimum_reduced_cost,
            "minimum_scaled_nonbasic_reduced_cost": float(
                basis["minimum_scaled_nonbasic_reduced_cost"]
            ),
            "near_zero_nonbasic_reduced_costs": near_zero,
            "primal_degenerate_basic_columns": int(basis["primal_degenerate_basic_columns"]),
            "primal_degenerate_basic_rows": int(basis["primal_degenerate_basic_rows"]),
            "basis_primal_degenerate": bool(basis["basis_primal_degenerate"]),
            "maximum_dual_sign_violation": float(basis["maximum_dual_sign_violation"]),
            "objective_reconciliation_error": float(basis["objective_reconciliation_error"]),
            "reversed_id_exposure_distance": exposure_distance,
            "reversed_id_objective_difference": objective_difference,
            "reversed_id_weighted_point_score_difference": float(
                reversed_solution.weighted_point_score - solution.weighted_score
            ),
        },
    )


def _build_gamma_states(
    month: pd.DataFrame,
    *,
    point: np.ndarray,
    upper: np.ndarray,
    objective: np.ndarray,
    unconstrained: ScoreFrontierSolution,
    gamma_grid: tuple[float, ...],
    window_id: str,
    role: str,
    period: str,
    budget: float,
    purpose_cap: float,
    time_limit: int,
    threads: int,
    normalized_config: Mapping[str, Any],
) -> dict[float, _GammaState]:
    states: dict[float, _GammaState] = {}
    for gamma in gamma_grid:
        score = point + gamma * (upper - point)
        normalized_session = PointPortfolioSession(
            month,
            point_score=score,
            objective_rate=objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        )
        raw_minimum = ObjectiveFloorPortfolioSession(
            month,
            score=score,
            objective_rate=objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        ).solve()
        minimum_score = float(raw_minimum.weighted_score)
        efficient_minimum = _from_point_solution(normalized_session.solve(minimum_score))
        minimum_cap_residual = float(efficient_minimum.weighted_score - minimum_score)
        if abs(minimum_cap_residual) > float(normalized_config["cap_residual_tolerance"]):
            raise RuntimeError(
                f"Minimum-score endpoint failed for {window_id} {role} "
                f"{period} gamma={gamma}: {minimum_cap_residual:.3e}."
            )
        score_at_objective = float(unconstrained.exposure @ score / budget)
        score_range = score_at_objective - minimum_score
        if score_range < float(normalized_config["minimum_score_range"]):
            raise RuntimeError(
                f"Normalized score range failed for {window_id} {role} "
                f"{period} gamma={gamma}: {score_range:.12g}."
            )
        objective_session = ObjectiveFloorPortfolioSession(
            month,
            score=score,
            objective_rate=objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        )
        states[gamma] = _GammaState(
            score=score,
            minimum_score=minimum_score,
            score_at_objective=score_at_objective,
            score_range=score_range,
            minimum_objective=float(efficient_minimum.objective_value),
            normalized_session=normalized_session,
            objective_session=objective_session,
        )
    return states


def _solve_rulers(
    state: _GammaState,
    *,
    gamma_states: Mapping[float, _GammaState],
    coordinate: float,
    unconstrained_objective: float,
    window_id: str,
    role: str,
    period: str,
    gamma: float,
    normalized_config: Mapping[str, Any],
    objective_config: Mapping[str, Any],
) -> tuple[_RulerSolution, _RulerSolution]:
    cap = normalized_score_cap(
        minimum_score=state.minimum_score,
        score_at_objective=state.score_at_objective,
        coordinate=coordinate,
        minimum_range=float(normalized_config["minimum_score_range"]),
    )
    normalized_solution = _from_point_solution(state.normalized_session.solve(cap))
    normalized_slack = float(cap - normalized_solution.weighted_score)
    if abs(normalized_slack) > float(normalized_config["cap_residual_tolerance"]):
        raise RuntimeError(
            f"Normalized cap did not bind for {window_id} {role} {period} "
            f"gamma={gamma} coordinate={coordinate}: {normalized_slack:.3e}."
        )

    _, objective_target = common_objective_target(
        minimum_objectives=[item.minimum_objective for item in gamma_states.values()],
        objective_optimum=unconstrained_objective,
        coordinate=coordinate,
        minimum_range=float(objective_config["minimum_objective_range_dollars"]),
    )
    matched_solution = state.objective_session.solve(objective_target)
    floor_slack = float(matched_solution.objective_value - objective_target)
    if abs(floor_slack) > float(objective_config["floor_residual_tolerance_dollars"]):
        raise RuntimeError(
            f"Objective floor failed for {window_id} {role} {period} "
            f"gamma={gamma} coordinate={coordinate}: {floor_slack:.3e}."
        )
    return (
        _RulerSolution(
            ruler="normalized_score",
            threshold=cap,
            solution=normalized_solution,
            cap=cap,
            objective_target=None,
        ),
        _RulerSolution(
            ruler="objective_matched",
            threshold=objective_target,
            solution=matched_solution,
            cap=None,
            objective_target=objective_target,
        ),
    )


def _from_point_solution(solution: PointPortfolioSolution) -> ScoreFrontierSolution:
    return ScoreFrontierSolution(
        allocation_fraction=solution.allocation_fraction,
        exposure=solution.exposure,
        objective_value=float(solution.objective_value),
        weighted_score=float(solution.weighted_point_score),
        total_allocated=float(solution.total_allocated),
        simplex_iterations=int(solution.simplex_iterations),
    )


def _policy_label(ruler: str, gamma: float, coordinate: float) -> str:
    return f"{ruler}_g{round(gamma * 100):03d}_c{round(coordinate * 100):03d}"


def _append_solution(
    records: list[dict[str, Any]],
    allocations: list[pd.DataFrame],
    *,
    month: pd.DataFrame,
    score: np.ndarray,
    objective: np.ndarray,
    solution: ScoreFrontierSolution,
    window_id: str,
    role: str,
    period: str,
    gamma: float,
    ruler: str,
    coordinate: float,
    cap: float | None,
    objective_target: float | None,
    common_objective_lower: float,
    state: _GammaState,
    unconstrained_objective: float,
    allocation_tolerance: float,
    budget: float,
) -> None:
    label = _policy_label(ruler, gamma, coordinate)
    if cap is not None:
        constraint_slack = float(cap - solution.weighted_score)
    elif objective_target is not None:
        constraint_slack = float(solution.objective_value - objective_target)
    else:
        raise ValueError("A frontier solution requires a cap or objective target.")
    active = solution.exposure > float(allocation_tolerance)
    funded = month.loc[active].copy()
    funded["allocation_fraction"] = solution.allocation_fraction[active]
    funded["exposure"] = solution.exposure[active]
    funded["weight"] = funded["exposure"] / solution.total_allocated
    funded["pd_effective"] = score[active]
    funded["expected_payoff_rate"] = objective[active]
    funded["expected_payoff_contribution"] = funded["exposure"] * objective[active]
    metadata = {
        "window_id": window_id,
        "role": role,
        "period": period,
        "policy_label": label,
        "candidate_id": label,
        "comparator_rule": ruler,
        "paired_policy_id": label,
        "frontier_ruler": ruler,
        "frontier_coordinate": coordinate,
        "frontier_cap": np.nan if cap is None else float(cap),
        "objective_target": np.nan if objective_target is None else float(objective_target),
        "gamma": gamma,
    }
    funded = funded.assign(**metadata)
    allocations.append(funded)
    records.append(
        {
            **metadata,
            "risk_tolerance": np.nan if cap is None else float(cap),
            "uncertainty_aversion": gamma,
            "policy_mode": ruler,
            "robust_guardrail": bool(gamma > 0.0),
            "solver_status": "Optimal",
            "solver_backend_actual": "highspy_exact_budget_simplex",
            "expected_objective": float(solution.objective_value),
            "n_candidates": int(len(month)),
            "n_positive_exposure": int(active.sum()),
            "total_allocated": float(solution.total_allocated),
            "budget_residual": float(solution.total_allocated - budget),
            "weighted_pd_point": float(solution.exposure @ month["pd_point"] / budget),
            "weighted_pd_effective": float(solution.weighted_score),
            "weighted_conformal_upper": float(
                solution.exposure @ month["conformal_upper"] / budget
            ),
            "minimum_score": state.minimum_score,
            "score_at_objective": state.score_at_objective,
            "score_range": state.score_range,
            "minimum_score_portfolio_objective": state.minimum_objective,
            "common_objective_lower": common_objective_lower,
            "unconstrained_objective": unconstrained_objective,
            "objective_retention": float(
                (solution.objective_value - common_objective_lower)
                / (unconstrained_objective - common_objective_lower)
            ),
            "constraint_slack": constraint_slack,
            "highs_simplex_iterations": int(solution.simplex_iterations),
        }
    )


def _order_diagnostic(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    original: ScoreFrontierSolution,
    window_id: str,
    role: str,
    period: str,
    gamma: float,
    ruler: str,
    coordinate: float,
    threshold: float,
    budget: float,
    purpose_cap: float,
    time_limit: int,
    threads: int,
) -> dict[str, Any]:
    reverse = month.iloc[::-1].reset_index(drop=True)
    reverse_score = score[::-1]
    reverse_objective = objective[::-1]
    if ruler == "normalized_score":
        reversed_solution = _from_point_solution(
            PointPortfolioSession(
                reverse,
                point_score=reverse_score,
                objective_rate=reverse_objective,
                budget=budget,
                purpose_cap=purpose_cap,
                time_limit=time_limit,
                threads=threads,
            ).solve(float(threshold))
        )
    else:
        reversed_solution = ObjectiveFloorPortfolioSession(
            reverse,
            score=reverse_score,
            objective_rate=reverse_objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        ).solve(float(threshold))
    reverse_exposure = pd.Series(
        reversed_solution.exposure,
        index=reverse["id"].astype("string"),
    )
    aligned = month["id"].astype("string").map(reverse_exposure).to_numpy(dtype=float)
    return {
        "window_id": window_id,
        "role": role,
        "period": period,
        "gamma": gamma,
        "ruler": ruler,
        "coordinate": coordinate,
        "threshold": threshold,
        "normalized_exposure_distance": normalized_exposure_distance(
            original.exposure,
            aligned,
            budget=budget,
        ),
        "objective_difference": float(reversed_solution.objective_value - original.objective_value),
        "weighted_score_difference": float(
            reversed_solution.weighted_score - original.weighted_score
        ),
    }


def _independent_diagnostic(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    original: ScoreFrontierSolution,
    window_id: str,
    role: str,
    period: str,
    gamma: float,
    ruler: str,
    coordinate: float,
    threshold: float,
    budget: float,
    purpose_cap: float,
) -> dict[str, Any]:
    glop = solve_glop_portfolio(
        month,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=purpose_cap,
        mode="normalized_score" if ruler == "normalized_score" else "objective_matched",
        threshold=threshold,
    )
    return {
        "window_id": window_id,
        "role": role,
        "period": period,
        "gamma": gamma,
        "ruler": ruler,
        "coordinate": coordinate,
        "threshold": threshold,
        "highs_objective": float(original.objective_value),
        "glop_objective": float(glop.objective_value),
        "objective_rate_difference": float(
            (glop.objective_value - original.objective_value) / budget
        ),
        "highs_weighted_score": float(original.weighted_score),
        "glop_weighted_score": float(glop.weighted_score),
        "weighted_score_difference": float(glop.weighted_score - original.weighted_score),
        "glop_iterations": int(glop.simplex_iterations),
    }


def _validate_complete_build(
    result: FrontierBuild,
    *,
    config: Mapping[str, Any],
    budget: float,
    budget_tolerance: float,
) -> None:
    expected_records = 8 * (11 + 15) * 5 * 3 * 2
    if len(result.solve_records) != expected_records:
        raise RuntimeError(
            f"Frontier produced {len(result.solve_records)} records, not {expected_records}."
        )
    if len(result.endpoint_diagnostics) != 8 * 15 * 3 * 2:
        raise RuntimeError("Primary endpoint diagnostic census is incomplete.")
    optimum = result.objective_optimum_diagnostics
    if len(optimum) != 11 + 15:
        raise RuntimeError("Objective-optimum diagnostic census is incomplete.")
    optimum_config = config["frontier"]["objective_optimum"]
    if int(optimum["near_zero_nonbasic_reduced_costs"].sum()) != 0 or float(
        optimum["minimum_absolute_nonbasic_reduced_cost"].min()
    ) <= float(optimum_config["dual_tolerance"]):
        raise RuntimeError("An objective optimum has an unresolved nonbasic reduced cost.")
    if len(result.order_sensitivity) != 8 * 15 * 2 * 3 * 2:
        raise RuntimeError("Primary endpoint ID-order audit census is incomplete.")
    expected_validation = 8 * 3 * 2 * 3 * 2
    if len(result.independent_validation) != expected_validation:
        raise RuntimeError("Independent GLOP validation census is incomplete.")
    maximum_budget = float(result.solve_records["budget_residual"].abs().max())
    if maximum_budget > budget_tolerance:
        raise RuntimeError(f"Frontier budget residual reached {maximum_budget:.3e} dollars.")
    order = result.order_sensitivity
    order_config = config["solver"]
    if float(optimum["reversed_id_exposure_distance"].max()) > float(
        order_config["order_exposure_distance_tolerance"]
    ):
        raise RuntimeError("ID reversal changed a score-independent objective optimum.")
    if float(optimum["reversed_id_objective_difference"].abs().max()) > float(
        order_config["order_objective_tolerance_dollars"]
    ):
        raise RuntimeError("ID reversal changed a score-independent optimum objective.")
    if float(order["normalized_exposure_distance"].max()) > float(
        order_config["order_exposure_distance_tolerance"]
    ):
        raise RuntimeError("ID reversal changed a primary endpoint allocation.")
    if float(order["objective_difference"].abs().max()) > float(
        order_config["order_objective_tolerance_dollars"]
    ):
        raise RuntimeError("ID reversal changed a primary endpoint objective.")
    validation = result.independent_validation
    independent = order_config["independent_validation"]
    if float(validation["objective_rate_difference"].abs().max()) > float(
        independent["objective_rate_tolerance"]
    ):
        raise RuntimeError("GLOP disagrees with HiGHS on a frontier objective rate.")
    if float(validation["weighted_score_difference"].abs().max()) > float(
        independent["weighted_score_tolerance"]
    ):
        raise RuntimeError("GLOP disagrees with HiGHS on a funded score.")
    if not np.isclose(
        result.solve_records["total_allocated"].to_numpy(dtype=float),
        float(budget),
        atol=budget_tolerance,
        rtol=0.0,
    ).all():
        raise RuntimeError("At least one frontier solve failed the exact-budget contract.")


def _assert_outcome_free(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> None:
    tokens = tuple(str(value).casefold() for value in config["source_ingest"]["forbidden_tokens"])
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).casefold() for token in tokens)
    ]
    if forbidden:
        raise ValueError(f"Outcome-like columns reached frontier construction: {forbidden}.")
