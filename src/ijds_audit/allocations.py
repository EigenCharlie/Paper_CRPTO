"""Outcome-free V4 guardrail, comparator, and exact-frontier construction."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.maturity_safe_portfolio import solve_outcome_free_allocation
from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_audit.portfolio import (
    PointPortfolioSession,
    PointPortfolioSolution,
    c2_cap,
    verify_c2_dominance,
)
from src.optimization.policy_selection import LinearPolicyCandidate, build_linear_policy_grid


@dataclass(frozen=True)
class OutcomeFreePortfolioAudit:
    """Frozen solve records, funded rows, and declared comparator supports."""

    records: pd.DataFrame
    allocations: pd.DataFrame
    comparator_support: pd.DataFrame
    frontier_breakpoints: pd.DataFrame


def policy_family(config: Mapping[str, Any]) -> tuple[LinearPolicyCandidate, ...]:
    grid = build_linear_policy_grid(
        risk_tolerances=[float(value) for value in config["policy"]["risk_tolerances"]],
        gammas=[float(value) for value in config["policy"]["gammas"]],
        uncertainty_aversions=[float(value) for value in config["policy"]["uncertainty_aversions"]],
    )
    if len(grid) != 9:
        raise RuntimeError("The V4 guardrail family must contain exactly nine policies.")
    return tuple(
        LinearPolicyCandidate(
            candidate_id=candidate.candidate_id,
            risk_tolerance=candidate.risk_tolerance,
            gamma=candidate.gamma,
            uncertainty_aversion=candidate.uncertainty_aversion,
            policy_mode=candidate.policy_mode,
            delta_cap_quantile=candidate.delta_cap_quantile,
            tail_focus_quantile=candidate.tail_focus_quantile,
            min_budget_utilization=float(config["policy"]["min_budget_utilization_solver"]),
            pd_cap_slack_penalty=0.0,
        )
        for candidate in grid
    )


def _cell_config(config: Mapping[str, Any]) -> dict[str, Any]:
    cell = copy.deepcopy(dict(config))
    cell["execution"]["random_seed"] = int(config["model"]["canonical_seed"])
    cell["policy"]["max_concentration_by_purpose"] = float(
        config["policy"]["max_concentration_by_purpose"]
    )
    return cell


def _period_frames(panel: pd.DataFrame, role: str) -> tuple[tuple[str, pd.DataFrame], ...]:
    frame = panel.loc[panel["design_split"].eq(role)].drop(columns="design_split")
    periods = pd.to_datetime(frame["issue_d"]).dt.to_period("M")
    return tuple(
        (str(period), frame.loc[periods.eq(period)].copy()) for period in sorted(periods.unique())
    )


def declared_menu_counts(config: Mapping[str, Any]) -> tuple[int, int]:
    """Return the exact development and primary month counts declared by the design."""
    design = config["design"]
    development = pd.period_range(
        str(design["policy_development_start"]),
        str(design["policy_development_end"]),
        freq="M",
    )
    primary = pd.period_range(
        str(design["primary_oot_start_month"]),
        str(design["primary_oot_end_month"]),
        freq="M",
    )
    return len(development), len(primary)


def _guardrail_solve(
    month: pd.DataFrame,
    *,
    candidate: LinearPolicyCandidate,
    config: Mapping[str, Any],
    role: str,
    period: str,
    window_id: str,
) -> tuple[dict[str, Any], pd.DataFrame]:
    record, allocation = solve_outcome_free_allocation(
        month,
        candidate,
        config=config,
        robust=True,
        role=role,
        period=period,
        policy_label=f"guardrail_{candidate.candidate_id}",
    )
    metadata = {
        "window_id": window_id,
        "comparator_rule": "guardrail",
        "paired_policy_id": candidate.candidate_id,
        "frontier_cap": np.nan,
    }
    record.update(metadata)
    return record, allocation.assign(**metadata)


def _solution_allocation(
    month: pd.DataFrame,
    solution: PointPortfolioSolution,
    *,
    role: str,
    period: str,
    window_id: str,
    comparator_rule: str,
    paired_policy_id: str,
    risk_cap: float,
    lgd: float,
    allocation_tolerance: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    active = solution.exposure > float(allocation_tolerance)
    funded = month.loc[active].copy()
    funded["allocation_fraction"] = solution.allocation_fraction[active]
    funded["exposure"] = solution.exposure[active]
    funded["weight"] = funded["exposure"] / solution.total_allocated
    funded["pd_effective"] = funded["pd_point"]
    funded["expected_payoff_rate"] = expected_objective_coefficients(
        funded["pd_point"].to_numpy(dtype=float),
        funded["contractual_rate"].to_numpy(dtype=float),
        lgd=float(lgd),
    )
    funded["expected_payoff_contribution"] = funded["exposure"] * funded["expected_payoff_rate"]
    policy_label = f"{comparator_rule}_{paired_policy_id}"
    if comparator_rule == "point_cap_frontier":
        policy_label = f"point_cap_frontier_{float(risk_cap):.12g}"
    metadata = {
        "role": role,
        "period": period,
        "window_id": window_id,
        "policy_label": policy_label,
        "candidate_id": f"point-{comparator_rule}-{paired_policy_id}-{period}",
        "comparator_rule": comparator_rule,
        "paired_policy_id": paired_policy_id,
        "frontier_cap": float(risk_cap),
    }
    funded = funded.assign(**metadata)
    record: dict[str, Any] = {
        **metadata,
        "risk_tolerance": float(risk_cap),
        "gamma": 0.0,
        "uncertainty_aversion": 0.0,
        "policy_mode": "point_estimate",
        "robust_guardrail": False,
        "solver_status": "Optimal",
        "solver_backend_actual": "highspy_exact_budget_simplex",
        "expected_objective": float(solution.objective_value),
        "n_candidates": int(len(month)),
        "n_positive_exposure": int(active.sum()),
        "total_allocated": float(solution.total_allocated),
        "weighted_pd_point": float(solution.weighted_point_score),
        "weighted_pd_effective": float(solution.weighted_point_score),
        "weighted_conformal_upper": float(
            funded["weight"].to_numpy(dtype=float) @ funded["conformal_upper"].to_numpy(dtype=float)
        ),
        "basis_cap_lower": float(solution.basis_cap_lower),
        "basis_cap_upper": float(solution.basis_cap_upper),
        "highs_simplex_iterations": int(solution.simplex_iterations),
    }
    return record, funded


def _point_session(
    month: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> PointPortfolioSession:
    point = month["pd_point"].to_numpy(dtype=float)
    objective = expected_objective_coefficients(
        point,
        month["contractual_rate"].to_numpy(dtype=float),
        lgd=float(config["payoff"]["lgd"]),
    )
    return PointPortfolioSession(
        month,
        point_score=point,
        objective_rate=objective,
        budget=float(config["policy"]["budget"]),
        purpose_cap=float(config["policy"]["max_concentration_by_purpose"]),
        time_limit=int(config["execution"]["solver_time_limit_seconds"]),
        threads=int(config["execution"]["threads"]),
    )


def _funded_vector(month: pd.DataFrame, allocation: pd.DataFrame) -> np.ndarray:
    exposure = allocation.set_index("id")["exposure"]
    if bool(exposure.index.duplicated().any()):
        raise RuntimeError("A guardrail allocation contains duplicate IDs.")
    return month["id"].map(exposure).fillna(0.0).to_numpy(dtype=float)


def _unique_caps(values: list[float], *, tolerance: float = 1e-10) -> tuple[float, ...]:
    output: list[float] = []
    for value in sorted(float(item) for item in values):
        if not output or value - output[-1] > tolerance:
            output.append(value)
    return tuple(output)


def build_outcome_free_portfolios(
    panels: Mapping[str, pd.DataFrame],
    config: Mapping[str, Any],
) -> OutcomeFreePortfolioAudit:
    """Build all V4 allocations without accepting an outcome dataframe."""
    if set(panels) != {str(window["id"]) for window in config["residual_specification"]["windows"]}:
        raise ValueError("Portfolio panels must cover exactly the eight declared windows.")
    cell = _cell_config(config)
    policies = policy_family(config)
    records: list[dict[str, Any]] = []
    allocations: list[pd.DataFrame] = []
    support_rows: list[dict[str, Any]] = []
    support_caps: list[float] = []
    point_cache: dict[tuple[str, str], PointPortfolioSolution] = {}
    point_sessions: dict[str, PointPortfolioSession] = {}
    expected_development, expected_primary = declared_menu_counts(config)

    for window_id, panel in panels.items():
        development = _period_frames(panel, "policy_development")
        primary = _period_frames(panel, "primary_oot")
        if len(development) != expected_development or len(primary) != expected_primary:
            raise RuntimeError(
                f"{window_id} requires {expected_development} development and "
                f"{expected_primary} primary OOT monthly menus; observed "
                f"{len(development)} and {len(primary)}."
            )
        for policy in policies:
            development_moments: list[float] = []
            for period, month in development:
                record, funded = _guardrail_solve(
                    month,
                    candidate=policy,
                    config=cell,
                    role="policy_development",
                    period=period,
                    window_id=window_id,
                )
                moment = c2_cap(
                    funded["exposure"].to_numpy(dtype=float),
                    funded["pd_point"].to_numpy(dtype=float),
                )
                record["guardrail_funded_point_moment"] = moment
                funded["guardrail_funded_point_moment"] = moment
                records.append(record)
                allocations.append(funded)
                development_moments.append(moment)
            c1 = float(np.average(development_moments))
            support_lower = float(min(development_moments))
            support_upper = float(max(development_moments))
            support_caps.extend((support_lower, support_upper))
            support_rows.append(
                {
                    "window_id": window_id,
                    "paired_policy_id": policy.candidate_id,
                    "development_months": len(development_moments),
                    "c1_cap": c1,
                    "support_lower": support_lower,
                    "support_upper": support_upper,
                }
            )
            for period, month in primary:
                guard_record, guard_funded = _guardrail_solve(
                    month,
                    candidate=policy,
                    config=cell,
                    role="primary_oot",
                    period=period,
                    window_id=window_id,
                )
                guard_vector = _funded_vector(month, guard_funded)
                point = month["pd_point"].to_numpy(dtype=float)
                objective = expected_objective_coefficients(
                    point,
                    month["contractual_rate"].to_numpy(dtype=float),
                    lgd=float(config["payoff"]["lgd"]),
                )
                contemporaneous = c2_cap(guard_vector, point)
                guard_record["guardrail_funded_point_moment"] = contemporaneous
                guard_funded["guardrail_funded_point_moment"] = contemporaneous
                records.append(guard_record)
                allocations.append(guard_funded)
                for rule, cap in (
                    ("c0_same_numeric_cap", float(policy.risk_tolerance)),
                    ("c1_development_mean", c1),
                    ("c2_contemporaneous", contemporaneous),
                ):
                    cache_key = (period, float(cap).hex())
                    solution = point_cache.get(cache_key)
                    if solution is None:
                        session = point_sessions.get(period)
                        if session is None:
                            session = _point_session(month, config=cell)
                            point_sessions[period] = session
                        solution = session.solve(cap)
                        point_cache[cache_key] = solution
                    record, funded = _solution_allocation(
                        month,
                        solution,
                        role="primary_oot",
                        period=period,
                        window_id=window_id,
                        comparator_rule=rule,
                        paired_policy_id=policy.candidate_id,
                        risk_cap=cap,
                        lgd=float(config["payoff"]["lgd"]),
                        allocation_tolerance=float(config["execution"]["allocation_tolerance"]),
                    )
                    record.update(
                        c1_cap=c1,
                        c2_cap=contemporaneous,
                        development_support_lower=support_lower,
                        development_support_upper=support_upper,
                    )
                    funded = funded.assign(
                        c1_cap=c1,
                        c2_cap=contemporaneous,
                        development_support_lower=support_lower,
                        development_support_upper=support_upper,
                    )
                    if rule == "c2_contemporaneous":
                        diagnostics = verify_c2_dominance(
                            guardrail_exposure=guard_vector,
                            point_solution=solution,
                            point_score=point,
                            objective_rate=objective,
                            tolerance=float(
                                config["comparators"]["exact_point_cap_frontier"][
                                    "objective_dominance_tolerance"
                                ]
                            ),
                        )
                        match_residual = float(solution.weighted_point_score - contemporaneous)
                        if abs(match_residual) > float(
                            config["comparators"]["exact_point_cap_frontier"]["cap_tolerance"]
                        ):
                            raise RuntimeError(
                                f"C2 funded point-risk match failed for {window_id} "
                                f"{policy.candidate_id} {period}: {match_residual:.3e}."
                            )
                        record.update(diagnostics, c2_match_residual=match_residual)
                        funded = funded.assign(c2_match_residual=match_residual)
                    records.append(record)
                    allocations.append(funded)

    frontier = config["comparators"]["exact_point_cap_frontier"]
    frontier_rows: list[dict[str, Any]] = []
    reference_panels = dict(panels)
    reference = next(iter(reference_panels.values()))
    reference_months = dict(_period_frames(reference, "primary_oot"))
    breakpoints_by_period: dict[str, tuple[float, ...]] = {}
    enumerated_lower = min(float(frontier["start"]), min(support_caps))
    enumerated_upper = max(float(frontier["stop"]), max(support_caps))
    for period, reference_month in reference_months.items():
        session = point_sessions.get(period)
        if session is None:
            session = _point_session(reference_month, config=cell)
            point_sessions[period] = session
        breakpoints = session.basis_breakpoints(
            lower_cap=enumerated_lower,
            upper_cap=enumerated_upper,
            tolerance=float(frontier["cap_tolerance"]),
        )
        breakpoints_by_period[period] = breakpoints
    global_caps = _unique_caps(
        [
            *support_caps,
            *(cap for caps in breakpoints_by_period.values() for cap in caps),
        ],
        tolerance=float(frontier["cap_tolerance"]),
    )
    for period in reference_months:
        for cap in global_caps:
            cache_key = (period, float(cap).hex())
            solution = point_cache.get(cache_key)
            if solution is None:
                solution = point_sessions[period].solve(cap)
                point_cache[cache_key] = solution
            frontier_rows.append(
                {
                    "period": period,
                    "frontier_cap": cap,
                    "basis_cap_lower": solution.basis_cap_lower,
                    "basis_cap_upper": solution.basis_cap_upper,
                    "is_enumerated_support_breakpoint": any(
                        abs(cap - item) <= float(frontier["cap_tolerance"])
                        for item in breakpoints_by_period[period]
                    ),
                    "is_global_breakpoint": any(
                        abs(cap - item) <= float(frontier["cap_tolerance"])
                        for breakpoints in breakpoints_by_period.values()
                        for item in breakpoints
                    ),
                    "objective_value": solution.objective_value,
                    "weighted_pd_point": solution.weighted_point_score,
                }
            )
            record, funded = _solution_allocation(
                reference_months[period],
                solution,
                role="primary_oot",
                period=period,
                window_id="__shared_point_frontier__",
                comparator_rule="point_cap_frontier",
                paired_policy_id="frontier",
                risk_cap=cap,
                lgd=float(config["payoff"]["lgd"]),
                allocation_tolerance=float(config["execution"]["allocation_tolerance"]),
            )
            window_specific = [
                "conformal_lower",
                "conformal_upper",
                "conformal_group",
                "learner",
                "taxonomy_groups",
            ]
            funded = funded.drop(columns=window_specific, errors="ignore")
            record["weighted_conformal_upper"] = np.nan
            records.append(record)
            allocations.append(funded)

    result_records = pd.DataFrame(records)
    result_allocations = pd.concat(allocations, ignore_index=True)
    forbidden = {"loan_status", "snapshot_default", "terminal_default", "total_pymnt"}
    if forbidden.intersection(column.casefold() for column in result_allocations.columns):
        raise AssertionError("Outcome-free allocation artifact contains an outcome field.")
    return OutcomeFreePortfolioAudit(
        records=result_records,
        allocations=result_allocations,
        comparator_support=pd.DataFrame(support_rows),
        frontier_breakpoints=pd.DataFrame(frontier_rows),
    )
