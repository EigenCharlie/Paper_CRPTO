"""Outcome-free binary-set-native robust-counterpart frontier."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.evaluation.policy_contrast_bounds import PolicyContrastIndex
from src.evaluation.standardized_credit_payoff import expected_objective_coefficients
from src.ijds_audit.portfolio import PointPortfolioSession
from src.ijds_challengers.archive import monthly_frames
from src.ijds_challengers.frontier import (
    ObjectiveFloorPortfolioSession,
    ScoreFrontierSolution,
    common_objective_target,
    normalized_exposure_distance,
    normalized_score_cap,
)
from src.ijds_challengers.normalized_frontier import (
    _build_gamma_states,
    _independent_diagnostic,
    _order_diagnostic,
    _solve_objective_optimum,
)
from src.models.binary_conformal_guardrail import (
    BinaryOutcomeConformalRecipe,
    apply_binary_outcome_recipe,
)

RUN_TAG = "ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
PROTOCOL_TAG = "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
ROLES = ("policy_development", "primary_oot")
RULERS = ("objective_matched", "normalized_score")
COORDINATES = (0.25, 0.5, 0.75)
SET_TYPES = ("empty", "singleton_zero", "singleton_one", "two_label")
METADATA_PREFIXES = {
    "record": "__record__",
    "audit": "__audit__",
    "taxonomy": "__taxonomy__",
}


@dataclass(frozen=True)
class SetNativeCell:
    """One atomic, outcome-free window--month--ruler--coordinate cell."""

    record: dict[str, Any]
    allocations: pd.DataFrame
    audit: dict[str, Any]
    taxonomy: dict[str, Any]

    @property
    def identity(self) -> tuple[str, str, str, str, float]:
        return (
            str(self.record["window_id"]),
            str(self.record["role"]),
            str(self.record["period"]),
            str(self.record["frontier_ruler"]),
            float(self.record["frontier_coordinate"]),
        )


@dataclass(frozen=True)
class _CellSolution:
    ruler: str
    solution: ScoreFrontierSolution
    cap: float | None
    objective_target: float | None


def _strict_float_grid(values: Sequence[Any], expected: tuple[float, ...], label: str) -> None:
    observed = tuple(float(value) for value in values)
    if observed != expected:
        raise ValueError(f"{label} must equal {expected}, not {observed}.")


def _valid_basename(value: Any, *, label: str) -> str:
    name = str(value)
    if (
        not name
        or name in {".", ".."}
        or PurePath(name).name != name
        or "/" in name
        or "\\" in name
    ):
        raise ValueError(f"{label} must be one safe basename.")
    return name


def load_set_native_config(path: Path) -> dict[str, Any]:
    """Load the Phase-A contract and reject estimand-defining drift."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Set-native configuration must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "phase_authority",
        "parent",
        "source_ingest",
        "set_native_score",
        "frontier",
        "solver",
        "expected_census",
        "phase_b_design",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    if set(payload) != {*required, "hypothesis"}:
        raise ValueError("Set-native Phase-A top-level contract changed.")
    if (
        payload["protocol_status"] != "locked_candidate_phase_a_before_execution"
        or payload["protocol_tag"] != PROTOCOL_TAG
        or payload["run_tag"] != RUN_TAG
    ):
        raise ValueError("Set-native Phase-A identity changed.")

    score = payload["set_native_score"]
    expected_score = {
        "source_model": "catboost_platt_primary_only",
        "source_recipe": "fixed_taxonomy_split_mondrian_absolute_residual",
        "canonical_groups": 5,
        "calibration_windows": "all_eight_declared_windows",
        "label_space": [0, 1],
        "default_label": 1,
        "definition": "zero_iff_exact_singleton_zero_else_one",
        "singleton_zero": 0.0,
        "empty_set": 1.0,
        "singleton_one": 1.0,
        "two_label_set": 1.0,
        "empty_set_semantics": ("explicit_fail_closed_decision_convention_not_conformal_theorem"),
        "interval_membership": "zero_iff_lower_equals_zero_one_iff_upper_equals_one",
        "no_continuous_endpoint_magnitude": True,
    }
    if score != expected_score:
        raise ValueError("The exact binary-set score or empty-set convention changed.")

    frontier = payload["frontier"]
    if tuple(str(value) for value in frontier["roles"]) != ROLES:
        raise ValueError(f"roles must equal {ROLES}.")
    if tuple(str(value) for value in frontier["rulers"]) != RULERS:
        raise ValueError(f"rulers must equal {RULERS}.")
    _strict_float_grid(frontier["coordinate_grid"], COORDINATES, "coordinate_grid")
    if (
        int(frontier["expected_development_months"]) != 11
        or int(frontier["expected_primary_months"]) != 15
        or int(frontier["expected_windows"]) != 8
        or frontier["normalized_score"]["definition"]
        != "score_min_plus_coordinate_times_score_at_objective_minus_score_min"
        or float(frontier["normalized_score"]["minimum_score_range"]) != 1.0e-4
        or float(frontier["normalized_score"]["cap_residual_tolerance"]) != 1.0e-8
        or tuple(
            float(value) for value in frontier["normalized_score"]["minimum_endpoint_retry_slacks"]
        )
        != (1.0e-10, 1.0e-9, 1.0e-8)
        or frontier["objective_matched"]["definition"]
        != "score_minimizer_subject_to_coordinate_plugin_objective_floor"
        or float(frontier["objective_matched"]["minimum_objective_range_dollars"]) != 1.0e-4
        or float(frontier["objective_matched"]["floor_residual_tolerance_dollars"]) != 1.0e-5
    ):
        raise ValueError("A set-native frontier definition changed.")

    census = payload["expected_census"]
    expected_census = {
        "windows": 8,
        "role_months_per_window": 26,
        "menu_cells": 208,
        "rulers": 2,
        "coordinates": 3,
        "phase_a_cells": 1248,
        "primary_cells": 720,
        "set_taxonomy_rows": 208,
        "solver_audit_rows": 1248,
        "phase_b_v1d_contrasts": 18000,
    }
    if census != expected_census:
        raise ValueError("The complete 8x26x2x3 census changed.")

    source = payload["source_ingest"]
    if (
        source["raw_path"] != "data/raw/Loan_status_2007-2020Q3.csv"
        or source["raw_sha256"]
        != "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f"
        or source["allowed_raw_columns"] != ["id", "loan_amnt", "int_rate", "purpose"]
        or source["forbidden_tokens"]
        != ["status", "outcome", "default", "pymnt", "realized", "miscoverage"]
        or int(source["chunksize"]) != 100_000
    ):
        raise ValueError("The outcome-free source contract changed.")

    solver = payload["solver"]
    if (
        solver["primary"] != "highspy_exact_budget_simplex"
        or int(solver["threads"]) != 1
        or int(solver["time_limit_seconds"]) != 300
        or solver["determinism"]["scope"] != "all_1248_cells_fresh_same_order"
        or solver["reversal"]["scope"] != "all_1248_cells"
        or solver["independent_validation"]["solver"] != "ortools_glop"
        or solver["independent_validation"]["scope"] != "all_1248_cells"
    ):
        raise ValueError("The complete solver-audit scope changed.")
    tolerances = (
        solver["allocation_tolerance"],
        solver["budget_residual_tolerance_dollars"],
        solver["order_exposure_distance_tolerance"],
        solver["order_objective_tolerance_dollars"],
        solver["determinism"]["exposure_distance_tolerance"],
        solver["determinism"]["objective_tolerance_dollars"],
        solver["determinism"]["weighted_score_tolerance"],
        solver["reversal"]["objective_tolerance_dollars"],
        solver["reversal"]["weighted_score_tolerance"],
        solver["independent_validation"]["objective_rate_tolerance"],
        solver["independent_validation"]["weighted_score_tolerance"],
    )
    if any(float(value) <= 0.0 for value in tolerances):
        raise ValueError("Every numerical tolerance must be positive.")
    if not all(payload["stop_rules"].values()):
        raise ValueError("Every set-native stop rule must remain enabled.")
    if not all(payload["claim_boundary"].values()):
        raise ValueError("Every set-native claim boundary must remain enabled.")
    if payload["phase_b_design"]["status"] != ("blocked_until_separate_hash_pinned_config_and_tag"):
        raise ValueError("Phase B is no longer blocked behind a separate tag.")
    output = payload["output"]
    expected_output = {
        "data_root": "data/processed/experiments/ijds_audit",
        "model_root": "models/experiments/ijds_audit",
        "immutability": (
            "external_atomic_runtime_shards_then_four_immutable_consolidated_parquets"
        ),
        "runtime_checkpoint_root": "localappdata_crpto_runtime_or_explicit_cli",
        "shard_directory": "cell_shards",
        "phase_a_intent": "phase_a_intent.json",
        "solve_records": "frontier_solve_records.parquet",
        "allocations": "frontier_funded_allocations.parquet",
        "set_taxonomy": "set_taxonomy_diagnostics.parquet",
        "solver_audit": "solver_audit.parquet",
        "phase_a_manifest": "verified_phase_a_manifest.json",
        "outcome_free_summary": "outcome_free_summary.json",
        "outcome_free_receipt": "outcome_free_execution_receipt.json",
        "protocol_freeze": "protocol_freeze.json",
    }
    if output != expected_output:
        raise ValueError("Runtime checkpoint or official Phase-A output contract changed.")
    for key in (
        "phase_a_intent",
        "solve_records",
        "allocations",
        "set_taxonomy",
        "solver_audit",
        "phase_a_manifest",
        "outcome_free_summary",
        "outcome_free_receipt",
        "protocol_freeze",
    ):
        _valid_basename(output[key], label=key)
    return payload


def binary_set_risk_score(
    lower: Sequence[float] | np.ndarray,
    upper: Sequence[float] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return exact set taxonomy and fail-closed worst-label score ``r(S)``."""
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    if (
        low.ndim != 1
        or high.shape != low.shape
        or not bool(np.isfinite(low).all())
        or not bool(np.isfinite(high).all())
        or bool(np.any((low < 0.0) | (low > 1.0)))
        or bool(np.any((high < 0.0) | (high > 1.0)))
        or bool(np.any(low > high))
    ):
        raise ValueError("Binary interval endpoints must be aligned ordered values in [0, 1].")
    contains_zero = low == 0.0
    contains_one = high == 1.0
    set_type = np.select(
        (
            contains_zero & contains_one,
            contains_zero & ~contains_one,
            ~contains_zero & contains_one,
        ),
        ("two_label", "singleton_zero", "singleton_one"),
        default="empty",
    ).astype(str)
    risk = np.where(set_type == "singleton_zero", 0.0, 1.0)
    if not bool(np.isin(set_type, SET_TYPES).all()) or not bool(np.isin(risk, (0.0, 1.0)).all()):
        raise RuntimeError("Binary-set taxonomy failed to partition the label space.")
    if not np.array_equal(risk == 0.0, set_type == "singleton_zero"):
        raise RuntimeError("Fail-closed score is not zero exactly on singleton zero sets.")
    return set_type, risk


def taxonomy_diagnostic(
    set_type: np.ndarray,
    risk: np.ndarray,
    *,
    window_id: str,
    role: str,
    period: str,
) -> dict[str, Any]:
    """Summarize one complete menu partition without outcomes."""
    kinds = np.asarray(set_type, dtype=str)
    score = np.asarray(risk, dtype=float)
    if len(kinds) == 0 or score.shape != kinds.shape:
        raise ValueError("Set taxonomy and risk score must be nonempty and aligned.")
    counts = {kind: int(np.sum(kinds == kind)) for kind in SET_TYPES}
    result = {
        "window_id": str(window_id),
        "role": str(role),
        "period": str(period),
        "n_candidates": int(len(kinds)),
        **{f"n_{kind}": count for kind, count in counts.items()},
        "n_risk_zero": int(np.sum(score == 0.0)),
        "n_risk_one": int(np.sum(score == 1.0)),
        "empty_set_score": 1.0,
    }
    if (
        sum(counts.values()) != len(kinds)
        or result["n_risk_zero"] != counts["singleton_zero"]
        or result["n_risk_one"] != len(kinds) - counts["singleton_zero"]
    ):
        raise RuntimeError("Set-native taxonomy diagnostic does not reconcile.")
    return result


def _from_point_solution(solution: Any) -> ScoreFrontierSolution:
    return ScoreFrontierSolution(
        allocation_fraction=np.asarray(solution.allocation_fraction, dtype=float),
        exposure=np.asarray(solution.exposure, dtype=float),
        objective_value=float(solution.objective_value),
        weighted_score=float(solution.weighted_point_score),
        total_allocated=float(solution.total_allocated),
        simplex_iterations=int(solution.simplex_iterations),
    )


def _fresh_solution(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    ruler: str,
    threshold: float,
    budget: float,
    purpose_cap: float,
    time_limit: int,
    threads: int,
) -> ScoreFrontierSolution:
    if ruler == "normalized_score":
        point = PointPortfolioSession(
            month,
            point_score=score,
            objective_rate=objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        ).solve(threshold)
        return _from_point_solution(point)
    if ruler == "objective_matched":
        return ObjectiveFloorPortfolioSession(
            month,
            score=score,
            objective_rate=objective,
            budget=budget,
            purpose_cap=purpose_cap,
            time_limit=time_limit,
            threads=threads,
        ).solve(threshold)
    raise ValueError(f"Unknown set-native ruler: {ruler}.")


def _solve_atomic_cell(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    state: Any,
    unconstrained_objective: float,
    ruler: str,
    coordinate: float,
    window_id: str,
    role: str,
    period: str,
    budget: float,
    purpose_cap: float,
    config: Mapping[str, Any],
) -> _CellSolution:
    """Solve one cell from a fresh solver so shards do not depend on warm history."""
    frontier = config["frontier"]
    if ruler == "normalized_score":
        cap = normalized_score_cap(
            minimum_score=float(state.minimum_score),
            score_at_objective=float(state.score_at_objective),
            coordinate=float(coordinate),
            minimum_range=float(frontier["normalized_score"]["minimum_score_range"]),
        )
        objective_target = None
        threshold = cap
    elif ruler == "objective_matched":
        _, objective_target = common_objective_target(
            minimum_objectives=[float(state.minimum_objective)],
            objective_optimum=float(unconstrained_objective),
            coordinate=float(coordinate),
            minimum_range=float(frontier["objective_matched"]["minimum_objective_range_dollars"]),
        )
        cap = None
        threshold = objective_target
    else:
        raise ValueError(f"Unknown set-native ruler: {ruler}.")
    solution = _fresh_solution(
        month,
        score=score,
        objective=objective,
        ruler=ruler,
        threshold=float(threshold),
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=int(config["solver"]["time_limit_seconds"]),
        threads=int(config["solver"]["threads"]),
    )
    if cap is not None:
        residual = float(cap - solution.weighted_score)
        tolerance = float(frontier["normalized_score"]["cap_residual_tolerance"])
    else:
        residual = float(solution.objective_value - float(threshold))
        tolerance = float(frontier["objective_matched"]["floor_residual_tolerance_dollars"])
    if abs(residual) > tolerance:
        raise RuntimeError(
            f"Atomic set-native threshold did not bind for {window_id} {role} {period} "
            f"{ruler} c={coordinate}: {residual:.3e}."
        )
    return _CellSolution(
        ruler=ruler,
        solution=solution,
        cap=cap,
        objective_target=objective_target,
    )


def solver_audit(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    solution: ScoreFrontierSolution,
    window_id: str,
    role: str,
    period: str,
    ruler: str,
    coordinate: float,
    threshold: float,
    budget: float,
    purpose_cap: float,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Run same-order, ID-reversal, and independent-solver checks for one cell."""
    solver = config["solver"]
    fresh = _fresh_solution(
        month,
        score=score,
        objective=objective,
        ruler=ruler,
        threshold=threshold,
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=int(solver["time_limit_seconds"]),
        threads=int(solver["threads"]),
    )
    deterministic_distance = normalized_exposure_distance(
        solution.exposure, fresh.exposure, budget=budget
    )
    deterministic_objective = float(fresh.objective_value - solution.objective_value)
    deterministic_score = float(fresh.weighted_score - solution.weighted_score)
    deterministic = solver["determinism"]
    if (
        deterministic_distance > float(deterministic["exposure_distance_tolerance"])
        or abs(deterministic_objective) > float(deterministic["objective_tolerance_dollars"])
        or abs(deterministic_score) > float(deterministic["weighted_score_tolerance"])
    ):
        raise RuntimeError(f"Same-order determinism failed for {window_id} {period} {ruler}.")

    reversal = _order_diagnostic(
        month,
        score=score,
        objective=objective,
        original=solution,
        window_id=window_id,
        role=role,
        period=period,
        gamma=0.0,
        ruler=ruler,
        coordinate=coordinate,
        threshold=threshold,
        budget=budget,
        purpose_cap=purpose_cap,
        time_limit=int(solver["time_limit_seconds"]),
        threads=int(solver["threads"]),
    )
    reversal_spec = solver["reversal"]
    if abs(float(reversal["objective_difference"])) > float(
        reversal_spec["objective_tolerance_dollars"]
    ) or abs(float(reversal["weighted_score_difference"])) > float(
        reversal_spec["weighted_score_tolerance"]
    ):
        raise RuntimeError(f"ID-reversal objective/score audit failed for {window_id} {period}.")

    independent = _independent_diagnostic(
        month,
        score=score,
        objective=objective,
        original=solution,
        window_id=window_id,
        role=role,
        period=period,
        gamma=0.0,
        ruler=ruler,
        coordinate=coordinate,
        threshold=threshold,
        budget=budget,
        purpose_cap=purpose_cap,
    )
    independent_spec = solver["independent_validation"]
    if abs(float(independent["objective_rate_difference"])) > float(
        independent_spec["objective_rate_tolerance"]
    ) or abs(float(independent["weighted_score_difference"])) > float(
        independent_spec["weighted_score_tolerance"]
    ):
        raise RuntimeError(f"Independent-solver audit failed for {window_id} {period}.")
    return {
        "window_id": window_id,
        "role": role,
        "period": period,
        "ruler": ruler,
        "coordinate": float(coordinate),
        "deterministic_exposure_distance": deterministic_distance,
        "deterministic_objective_difference": deterministic_objective,
        "deterministic_weighted_score_difference": deterministic_score,
        "reversal_exposure_distance": float(reversal["normalized_exposure_distance"]),
        "reversal_objective_difference": float(reversal["objective_difference"]),
        "reversal_weighted_score_difference": float(reversal["weighted_score_difference"]),
        "independent_objective_rate_difference": float(independent["objective_rate_difference"]),
        "independent_weighted_score_difference": float(independent["weighted_score_difference"]),
    }


def _policy_label(ruler: str, coordinate: float) -> str:
    return f"set_native_{ruler}_c{round(100 * coordinate):03d}"


def _materialize_cell(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    solution: ScoreFrontierSolution,
    solved: Any,
    state: Any,
    taxonomy: dict[str, Any],
    audit: dict[str, Any],
    window_id: str,
    role: str,
    period: str,
    coordinate: float,
    budget: float,
    allocation_tolerance: float,
    unconstrained_objective: float,
) -> SetNativeCell:
    ruler = str(solved.ruler)
    label = _policy_label(ruler, coordinate)
    cap = None if solved.cap is None else float(solved.cap)
    objective_target = None if solved.objective_target is None else float(solved.objective_target)
    threshold = cap if cap is not None else objective_target
    if threshold is None:
        raise RuntimeError("Set-native frontier solution has no threshold.")
    constraint_slack = (
        float(cap - solution.weighted_score)
        if cap is not None
        else float(solution.objective_value - threshold)
    )
    active = solution.exposure > allocation_tolerance
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
        "paired_policy_id": label,
        "comparator_rule": ruler,
        "frontier_ruler": ruler,
        "frontier_coordinate": float(coordinate),
        "frontier_cap": np.nan if cap is None else cap,
        "objective_target": np.nan if objective_target is None else objective_target,
    }
    funded = funded.assign(**metadata)
    record = {
        **metadata,
        "risk_tolerance": np.nan if cap is None else cap,
        "policy_mode": ruler,
        "robust_guardrail": True,
        "set_native_score": "zero_iff_exact_singleton_zero_else_one",
        "empty_set_convention": "fail_closed_one",
        "solver_status": "Optimal",
        "solver_backend_actual": "highspy_exact_budget_simplex",
        "expected_objective": float(solution.objective_value),
        "n_candidates": int(len(month)),
        "n_positive_exposure": int(active.sum()),
        "total_allocated": float(solution.total_allocated),
        "budget_residual": float(solution.total_allocated - budget),
        "cash_variable_present": False,
        "weighted_pd_point": float(solution.exposure @ month["pd_point"] / budget),
        "weighted_pd_effective": float(solution.weighted_score),
        "weighted_set_risk": float(solution.weighted_score),
        "weighted_conformal_upper": float(solution.exposure @ month["conformal_upper"] / budget),
        "minimum_score": float(state.minimum_score),
        "score_at_objective": float(state.score_at_objective),
        "score_range": float(state.score_range),
        "minimum_score_portfolio_objective": float(state.minimum_objective),
        "unconstrained_objective": float(unconstrained_objective),
        "objective_retention": float(
            (solution.objective_value - state.minimum_objective)
            / (unconstrained_objective - state.minimum_objective)
        ),
        "constraint_slack": constraint_slack,
        "highs_simplex_iterations": int(solution.simplex_iterations),
    }
    return SetNativeCell(
        record=record,
        allocations=funded,
        audit=audit,
        taxonomy=taxonomy,
    )


def _assert_outcome_free(frame: pd.DataFrame, config: Mapping[str, Any]) -> None:
    tokens = tuple(str(value).casefold() for value in config["source_ingest"]["forbidden_tokens"])
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).casefold() for token in tokens)
    ]
    if forbidden:
        raise ValueError(f"Set-native decision input contains outcome-like columns: {forbidden}.")


def iter_set_native_cells(
    base: pd.DataFrame,
    recipes: Mapping[str, Mapping[str, Mapping[int, BinaryOutcomeConformalRecipe]]],
    *,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
    skip_identities: set[tuple[str, str, str, str, float]] | None = None,
) -> Iterator[SetNativeCell]:
    """Yield all 1,248 cells; the caller can atomically persist each one."""
    _assert_outcome_free(base, config)
    frontier = config["frontier"]
    solver = config["solver"]
    budget = float(parent_config["policy"]["budget"])
    purpose_cap = float(parent_config["policy"]["max_concentration_by_purpose"])
    lgd = float(parent_config["payoff"]["lgd"])
    objective_cache: dict[tuple[str, str], Any] = {}
    skipped = set() if skip_identities is None else set(skip_identities)
    windows = recipes["catboost_platt"]
    if len(windows) != int(frontier["expected_windows"]):
        raise RuntimeError("Set-native recipe window census changed.")

    for window_id, group_recipes in sorted(windows.items()):
        completed_in_window = sum(identity[0] == str(window_id) for identity in skipped)
        expected_per_window = int(frontier["expected_development_months"])
        expected_per_window += int(frontier["expected_primary_months"])
        expected_per_window *= len(RULERS) * len(COORDINATES)
        if completed_in_window == expected_per_window:
            continue
        if completed_in_window > expected_per_window:
            raise RuntimeError(f"Completed-shard census exceeds one window: {window_id}.")
        point_all = base["pd_point"].to_numpy(dtype=float)
        groups, lower, upper = apply_binary_outcome_recipe(point_all, group_recipes[5])
        set_type, risk = binary_set_risk_score(lower, upper)
        window_base = base.assign(
            conformal_group=groups,
            conformal_lower=lower,
            conformal_upper=upper,
            binary_set_type=set_type,
            set_risk=risk,
        )
        for role in ROLES:
            months = monthly_frames(window_base, role)
            expected_months = (
                int(frontier["expected_development_months"])
                if role == "policy_development"
                else int(frontier["expected_primary_months"])
            )
            if len(months) != expected_months:
                raise RuntimeError(f"{window_id} {role} month census changed.")
            for period, month in months:
                point = month["pd_point"].to_numpy(dtype=float)
                set_score = month["set_risk"].to_numpy(dtype=float)
                rates = month["contractual_rate"].to_numpy(dtype=float)
                objective = expected_objective_coefficients(point, rates, lgd=lgd)
                cache_key = (role, period)
                optimum = objective_cache.get(cache_key)
                if optimum is None:
                    optimum = _solve_objective_optimum(
                        month,
                        point_score=point,
                        objective_rate=objective,
                        budget=budget,
                        purpose_cap=purpose_cap,
                        time_limit=int(solver["time_limit_seconds"]),
                        threads=int(solver["threads"]),
                        role=role,
                        period=period,
                        optimum_config=frontier["objective_optimum"],
                        solver_config=solver,
                    )
                    objective_cache[cache_key] = optimum
                states = _build_gamma_states(
                    month,
                    point=set_score,
                    upper=set_score,
                    objective=objective,
                    unconstrained=optimum.solution,
                    gamma_grid=(0.0,),
                    window_id=str(window_id),
                    role=role,
                    period=period,
                    budget=budget,
                    purpose_cap=purpose_cap,
                    time_limit=int(solver["time_limit_seconds"]),
                    threads=int(solver["threads"]),
                    normalized_config=frontier["normalized_score"],
                )
                state = states[0.0]
                taxonomy = taxonomy_diagnostic(
                    month["binary_set_type"].to_numpy(dtype=str),
                    set_score,
                    window_id=str(window_id),
                    role=role,
                    period=period,
                )
                for coordinate in COORDINATES:
                    coordinate_identities = {
                        (str(window_id), role, period, ruler, float(coordinate)) for ruler in RULERS
                    }
                    if coordinate_identities.issubset(skipped):
                        continue
                    for ruler in RULERS:
                        identity = (str(window_id), role, period, ruler, float(coordinate))
                        if identity in skipped:
                            continue
                        solved = _solve_atomic_cell(
                            month,
                            score=set_score,
                            objective=objective,
                            state=state,
                            unconstrained_objective=float(optimum.solution.objective_value),
                            ruler=ruler,
                            coordinate=coordinate,
                            window_id=str(window_id),
                            role=role,
                            period=period,
                            budget=budget,
                            purpose_cap=purpose_cap,
                            config=config,
                        )
                        if solved.cap is not None:
                            threshold = float(solved.cap)
                        elif solved.objective_target is not None:
                            threshold = float(solved.objective_target)
                        else:
                            raise RuntimeError("Atomic cell solution has no threshold.")
                        audit = solver_audit(
                            month,
                            score=set_score,
                            objective=objective,
                            solution=solved.solution,
                            window_id=str(window_id),
                            role=role,
                            period=period,
                            ruler=ruler,
                            coordinate=coordinate,
                            threshold=threshold,
                            budget=budget,
                            purpose_cap=purpose_cap,
                            config=config,
                        )
                        cell = _materialize_cell(
                            month,
                            score=set_score,
                            objective=objective,
                            solution=solved.solution,
                            solved=solved,
                            state=state,
                            taxonomy=taxonomy,
                            audit=audit,
                            window_id=str(window_id),
                            role=role,
                            period=period,
                            coordinate=coordinate,
                            budget=budget,
                            allocation_tolerance=float(solver["allocation_tolerance"]),
                            unconstrained_objective=float(optimum.solution.objective_value),
                        )
                        if abs(float(cell.record["budget_residual"])) > float(
                            solver["budget_residual_tolerance_dollars"]
                        ):
                            raise RuntimeError(
                                f"Set-native full-budget equality failed: {cell.identity}."
                            )
                        yield cell


def shard_relative_path(cell: SetNativeCell) -> Path:
    """Return the unique repository-independent path of one atomic cell shard."""
    window, role, period, ruler, coordinate = cell.identity
    return Path(window) / role / period / f"{ruler}_c{round(100 * coordinate):03d}.parquet"


def cell_to_shard_frame(cell: SetNativeCell) -> pd.DataFrame:
    """Encode allocation plus scalar authority in one atomic Parquet object."""
    if cell.allocations.empty:
        raise RuntimeError("A full-budget cell cannot have an empty funded allocation.")
    shard = cell.allocations.copy()
    for group, values in (
        ("record", cell.record),
        ("audit", cell.audit),
        ("taxonomy", cell.taxonomy),
    ):
        prefix = METADATA_PREFIXES[group]
        for key, value in values.items():
            shard[f"{prefix}{key}"] = value
    return shard


def _decode_metadata(frame: pd.DataFrame, prefix: str, *, label: str) -> dict[str, Any]:
    columns = [str(column) for column in frame.columns if str(column).startswith(prefix)]
    if not columns:
        raise RuntimeError(f"Atomic shard lacks {label} metadata.")
    values: dict[str, Any] = {}
    for column in columns:
        series = frame[column]
        if len(series.drop_duplicates()) != 1:
            raise RuntimeError(f"Atomic shard has conflicting {label} field {column}.")
        values[column.removeprefix(prefix)] = series.iloc[0]
    return values


def cell_from_shard_frame(frame: pd.DataFrame) -> SetNativeCell:
    """Decode and internally reconcile one previously materialized shard."""
    if frame.empty:
        raise RuntimeError("Atomic cell shard is empty.")
    record = _decode_metadata(frame, METADATA_PREFIXES["record"], label="record")
    audit = _decode_metadata(frame, METADATA_PREFIXES["audit"], label="audit")
    taxonomy = _decode_metadata(frame, METADATA_PREFIXES["taxonomy"], label="taxonomy")
    metadata_columns = [
        column
        for column in frame.columns
        if any(str(column).startswith(prefix) for prefix in METADATA_PREFIXES.values())
    ]
    cell = SetNativeCell(
        record=record,
        allocations=frame.drop(columns=metadata_columns),
        audit=audit,
        taxonomy=taxonomy,
    )
    expected_identity = (
        str(audit["window_id"]),
        str(audit["role"]),
        str(audit["period"]),
        str(audit["ruler"]),
        float(audit["coordinate"]),
    )
    if cell.identity != expected_identity:
        raise RuntimeError("Atomic shard record and audit identities disagree.")
    total = float(cell.allocations["exposure"].sum())
    if not np.isclose(total, float(record["total_allocated"]), rtol=0.0, atol=1.0e-8):
        raise RuntimeError("Atomic shard exposure does not reconcile to its solve record.")
    return cell


def validate_phase_a_metadata(
    records: pd.DataFrame,
    audits: pd.DataFrame,
    taxonomy: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> None:
    """Fail closed on the terminal 1,248-cell metadata census."""
    expected = config["expected_census"]
    keys = ["window_id", "role", "period", "frontier_ruler", "frontier_coordinate"]
    if len(records) != int(expected["phase_a_cells"]) or bool(records.duplicated(keys).any()):
        raise RuntimeError("Set-native Phase-A cell census is incomplete or duplicated.")
    if len(audits) != int(expected["solver_audit_rows"]):
        raise RuntimeError("Set-native solver-audit census is incomplete.")
    taxonomy_keys = ["window_id", "role", "period"]
    if len(taxonomy) != int(expected["set_taxonomy_rows"]) or bool(
        taxonomy.duplicated(taxonomy_keys).any()
    ):
        raise RuntimeError("Set-native taxonomy census is incomplete or duplicated.")
    if set(records["frontier_ruler"].astype(str)) != set(RULERS) or set(
        pd.to_numeric(records["frontier_coordinate"], errors="raise")
    ) != set(COORDINATES):
        raise RuntimeError("Set-native ruler or coordinate grid is incomplete.")
    if int(records["window_id"].nunique()) != int(expected["windows"]):
        raise RuntimeError("Set-native window census is incomplete.")
    primary = records.loc[records["role"].eq("primary_oot")]
    if len(primary) != int(expected["primary_cells"]):
        raise RuntimeError("Set-native primary cell census is incomplete.")
    if float(records["budget_residual"].abs().max()) > float(
        config["solver"]["budget_residual_tolerance_dollars"]
    ):
        raise RuntimeError("Set-native Phase A violates full-budget equality.")


def build_robust_minus_v1d_contrasts(
    robust_joined: pd.DataFrame,
    v1d_joined: pd.DataFrame,
    robust_records: pd.DataFrame,
    v1d_records: pd.DataFrame,
    *,
    budget: float,
    lgd: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the complete monthly and pooled robust-minus-V1d sharp census."""
    keys = ["window_id", "period", "frontier_ruler", "frontier_coordinate"]
    required_robust = {*keys, "role", "policy_label"}
    required_v1d = {*required_robust, "theta", "gamma"}
    if missing := sorted(required_robust - set(robust_records.columns)):
        raise KeyError(f"Robust records lack comparison columns: {missing}.")
    if missing := sorted(required_v1d - set(v1d_records.columns)):
        raise KeyError(f"V1d records lack comparison columns: {missing}.")
    robust = robust_records.loc[robust_records["role"].eq("primary_oot")].copy()
    v1d = v1d_records.loc[v1d_records["role"].eq("primary_oot")].copy()
    if len(robust) != 720 or len(v1d) != 18_000:
        raise RuntimeError("Robust/V1d primary solve-record census is not 720/18,000.")
    if bool(robust.duplicated(keys).any()):
        raise RuntimeError("A robust comparison cell is duplicated.")
    if bool(v1d.duplicated([*keys, "theta", "gamma"]).any()):
        raise RuntimeError("A V1d comparison cell is duplicated.")

    monthly_rows: list[dict[str, Any]] = []
    for raw_key, robust_record in robust.groupby(keys, observed=True, sort=True):
        key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        selectors = np.ones(len(v1d), dtype=bool)
        for column, value in zip(keys, key, strict=True):
            selectors &= v1d[column].eq(value).to_numpy(dtype=bool)
        comparators = v1d.loc[selectors].sort_values(["theta", "gamma"], kind="mergesort")
        if len(robust_record) != 1 or len(comparators) != 25:
            raise RuntimeError(f"A monthly robust/V1d menu is not 1-to-25: {key}.")
        allocation_selector = np.ones(len(robust_joined), dtype=bool)
        v1d_allocation_selector = np.ones(len(v1d_joined), dtype=bool)
        for column, value in zip(keys, key, strict=True):
            allocation_selector &= robust_joined[column].eq(value).to_numpy(dtype=bool)
            v1d_allocation_selector &= v1d_joined[column].eq(value).to_numpy(dtype=bool)
        combined = pd.concat(
            [
                robust_joined.loc[allocation_selector],
                v1d_joined.loc[v1d_allocation_selector],
            ],
            ignore_index=True,
        )
        index = PolicyContrastIndex(combined, role="primary_oot")
        robust_policy = str(robust_record["policy_label"].iloc[0])
        for comparator in comparators.to_dict(orient="records"):
            monthly_rows.append(
                {
                    "scope": "primary_month",
                    **dict(zip(keys, key, strict=True)),
                    "theta": float(comparator["theta"]),
                    "gamma": float(comparator["gamma"]),
                    "robust_policy": robust_policy,
                    "embedding_policy": str(comparator["policy_label"]),
                    **index.sharp_bounds(
                        policy_a=robust_policy,
                        policy_b=str(comparator["policy_label"]),
                        lgd=float(lgd),
                        normalization_capital_a=float(budget),
                        normalization_capital_b=float(budget),
                    ),
                }
            )
    monthly = pd.DataFrame(monthly_rows)
    if len(monthly) != 18_000:
        raise RuntimeError("Monthly robust-minus-V1d contrast census is not 18,000.")

    pooled_rows: list[dict[str, Any]] = []
    pooled_keys = ["window_id", "frontier_ruler", "frontier_coordinate"]
    for raw_key, robust_group in robust.groupby(pooled_keys, observed=True, sort=True):
        key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        selectors = np.ones(len(v1d), dtype=bool)
        allocation_selector = np.ones(len(robust_joined), dtype=bool)
        v1d_allocation_selector = np.ones(len(v1d_joined), dtype=bool)
        for column, value in zip(pooled_keys, key, strict=True):
            selectors &= v1d[column].eq(value).to_numpy(dtype=bool)
            allocation_selector &= robust_joined[column].eq(value).to_numpy(dtype=bool)
            v1d_allocation_selector &= v1d_joined[column].eq(value).to_numpy(dtype=bool)
        comparators = v1d.loc[selectors, ["theta", "gamma", "policy_label"]].drop_duplicates()
        if len(robust_group) != 15 or len(comparators) != 25:
            raise RuntimeError(f"A pooled robust/V1d menu is not 15 months by 25: {key}.")
        combined = pd.concat(
            [
                robust_joined.loc[allocation_selector],
                v1d_joined.loc[v1d_allocation_selector],
            ],
            ignore_index=True,
        )
        index = PolicyContrastIndex(combined, role="primary_oot")
        robust_labels = robust_group["policy_label"].astype(str).unique()
        if len(robust_labels) != 1:
            raise RuntimeError(f"Pooled robust policy label changed across months: {key}.")
        robust_policy = str(robust_labels[0])
        for comparator in comparators.sort_values(["theta", "gamma"], kind="mergesort").to_dict(
            orient="records"
        ):
            pooled_rows.append(
                {
                    "scope": "pooled_primary_window",
                    **dict(zip(pooled_keys, key, strict=True)),
                    "theta": float(comparator["theta"]),
                    "gamma": float(comparator["gamma"]),
                    "robust_policy": robust_policy,
                    "embedding_policy": str(comparator["policy_label"]),
                    **index.sharp_bounds(
                        policy_a=robust_policy,
                        policy_b=str(comparator["policy_label"]),
                        lgd=float(lgd),
                        normalization_capital_a=15.0 * float(budget),
                        normalization_capital_b=15.0 * float(budget),
                    ),
                }
            )
    pooled = pd.DataFrame(pooled_rows)
    if len(pooled) != 1_200:
        raise RuntimeError("Pooled robust-minus-V1d contrast census is not 1,200.")
    return monthly, pooled
