from __future__ import annotations

import copy
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.run_ijds_normalized_objective_frontier import prepare_output_paths
from src.ijds_audit.portfolio import PointPortfolioSession
from src.ijds_challengers.config import load_frontier_config
from src.ijds_challengers.frontier import (
    ObjectiveFloorPortfolioSession,
    common_objective_target,
    normalized_exposure_distance,
    normalized_score_cap,
    solve_glop_portfolio,
)
from src.ijds_challengers.normalized_frontier import _solve_objective_optimum

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1c.yaml"


def _small_menu() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    frame = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d"],
            "loan_amnt": [1.0, 1.0, 1.0, 1.0],
            "purpose": ["a", "a", "b", "b"],
        }
    )
    score = np.array([0.03, 0.08, 0.12, 0.19])
    objective = np.array([0.04, 0.11, 0.07, 0.15])
    return frame, score, objective


def _enumerated_optimum(
    *,
    score: np.ndarray,
    objective: np.ndarray,
    mode: str,
    threshold: float,
) -> tuple[float, float]:
    equality = np.ones((1, 4))
    equality_rhs = np.array([2.0])
    inequalities: list[np.ndarray] = []
    rhs: list[float] = []
    for index in range(4):
        upper = np.zeros(4)
        upper[index] = 1.0
        inequalities.append(upper)
        rhs.append(1.0)
        lower = np.zeros(4)
        lower[index] = -1.0
        inequalities.append(lower)
        rhs.append(0.0)
    inequalities.extend([np.array([1.0, 1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0, 1.0])])
    rhs.extend([1.5, 1.5])
    if mode == "normalized_score":
        inequalities.append(score.copy())
        rhs.append(float(threshold) * 2.0)
    else:
        inequalities.append(-objective.copy())
        rhs.append(-float(threshold))
    matrix = np.vstack(inequalities)
    bound = np.asarray(rhs)
    feasible: list[np.ndarray] = []
    for active in itertools.combinations(range(len(matrix)), 3):
        system = np.vstack([equality, matrix[list(active)]])
        if np.linalg.matrix_rank(system) < 4:
            continue
        candidate = np.linalg.solve(system, np.concatenate([equality_rhs, bound[list(active)]]))
        if bool(np.all(matrix @ candidate <= bound + 1e-9)):
            feasible.append(candidate)
    assert feasible
    if mode == "normalized_score":
        optimum = max(feasible, key=lambda value: float(value @ objective))
    else:
        optimum = min(feasible, key=lambda value: float(value @ score))
    return float(optimum @ objective), float(optimum @ score / 2.0)


def test_frontier_config_is_locked_and_outcome_free() -> None:
    config = load_frontier_config(CONFIG)
    assert config["frontier"]["gamma_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert config["frontier"]["coordinate_grid"] == [0.25, 0.5, 0.75]
    assert config["claim_boundary"]["outcome_columns_passed"] == []
    assert config["frontier"]["rulers"]["primary"] == "objective_matched"
    assert config["frontier"]["objective_optimum"]["diagnostic"] == (
        "nonbasic_reduced_costs_plus_reversed_id_order"
    )
    assert config["solver"]["budget_residual_tolerance_dollars"] == 1.0e-4


def test_frontier_config_rejects_policy_winner(tmp_path: Path) -> None:
    text = CONFIG.read_text(encoding="utf-8").replace(
        "no_policy_winner: true",
        "no_policy_winner: false",
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="claim boundary"):
        load_frontier_config(path)


def test_frontier_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_frontier_config(CONFIG))
    config["run_tag"] = "normalized-frontier-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)
    assert paths.data_dir == (
        tmp_path / "data/processed/experiments/ijds_audit/normalized-frontier-test"
    )
    assert paths.model_dir == (tmp_path / "models/experiments/ijds_audit/normalized-frontier-test")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)


def test_normalized_cap_is_positive_affine_invariant() -> None:
    frame, score, objective = _small_menu()
    budget = 2.0
    base_min = ObjectiveFloorPortfolioSession(
        frame,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve()
    base_objective = PointPortfolioSession(
        frame,
        point_score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(1.0)
    transformed = 0.5 * score + 0.2
    transformed_min = ObjectiveFloorPortfolioSession(
        frame,
        score=transformed,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve()
    coordinate = 0.5
    base_cap = normalized_score_cap(
        minimum_score=base_min.weighted_score,
        score_at_objective=float(base_objective.exposure @ score / budget),
        coordinate=coordinate,
    )
    transformed_cap = normalized_score_cap(
        minimum_score=transformed_min.weighted_score,
        score_at_objective=float(base_objective.exposure @ transformed / budget),
        coordinate=coordinate,
    )
    assert transformed_cap == pytest.approx(0.5 * base_cap + 0.2)
    base_solution = PointPortfolioSession(
        frame,
        point_score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(base_cap)
    transformed_solution = PointPortfolioSession(
        frame,
        point_score=transformed,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(transformed_cap)
    assert (
        normalized_exposure_distance(
            base_solution.exposure,
            transformed_solution.exposure,
            budget=budget,
        )
        < 1e-10
    )


def test_both_rulers_match_vertex_enumeration_and_glop() -> None:
    frame, score, objective = _small_menu()
    budget = 2.0
    minimum = ObjectiveFloorPortfolioSession(
        frame,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve()
    unconstrained = PointPortfolioSession(
        frame,
        point_score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(1.0)
    cap = normalized_score_cap(
        minimum_score=minimum.weighted_score,
        score_at_objective=float(unconstrained.exposure @ score / budget),
        coordinate=0.5,
    )
    normalized = PointPortfolioSession(
        frame,
        point_score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(cap)
    brute_objective, brute_score = _enumerated_optimum(
        score=score,
        objective=objective,
        mode="normalized_score",
        threshold=cap,
    )
    glop = solve_glop_portfolio(
        frame,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
        mode="normalized_score",
        threshold=cap,
    )
    assert normalized.objective_value == pytest.approx(brute_objective, abs=1e-9)
    assert normalized.weighted_point_score == pytest.approx(brute_score, abs=1e-9)
    assert glop.objective_value == pytest.approx(brute_objective, abs=1e-9)
    assert glop.weighted_score == pytest.approx(brute_score, abs=1e-9)

    lower, target = common_objective_target(
        minimum_objectives=[minimum.objective_value, minimum.objective_value - 0.01],
        objective_optimum=unconstrained.objective_value,
        coordinate=0.5,
    )
    assert lower == pytest.approx(minimum.objective_value)
    matched = ObjectiveFloorPortfolioSession(
        frame,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
    ).solve(target)
    brute_objective, brute_score = _enumerated_optimum(
        score=score,
        objective=objective,
        mode="objective_matched",
        threshold=target,
    )
    glop = solve_glop_portfolio(
        frame,
        score=score,
        objective_rate=objective,
        budget=budget,
        purpose_cap=0.75,
        mode="objective_matched",
        threshold=target,
    )
    assert matched.objective_value == pytest.approx(brute_objective, abs=1e-9)
    assert matched.weighted_score == pytest.approx(brute_score, abs=1e-9)
    assert glop.objective_value == pytest.approx(brute_objective, abs=1e-9)
    assert glop.weighted_score == pytest.approx(brute_score, abs=1e-9)


def test_objective_optimum_uses_basis_and_order_diagnostics() -> None:
    config = load_frontier_config(CONFIG)
    frame, score, objective = _small_menu()
    optimum = _solve_objective_optimum(
        frame,
        point_score=score,
        objective_rate=objective,
        budget=2.0,
        purpose_cap=0.75,
        time_limit=30,
        threads=1,
        role="primary_oot",
        period="2016-04",
        optimum_config=config["frontier"]["objective_optimum"],
        solver_config=config["solver"],
    )
    assert optimum.diagnostics["near_zero_nonbasic_reduced_costs"] == 0
    assert optimum.diagnostics["reversed_id_exposure_distance"] < 1e-10


def test_objective_optimum_rejects_alternate_optimum() -> None:
    config = load_frontier_config(CONFIG)
    frame, score, objective = _small_menu()
    objective[:] = 0.1
    with pytest.raises(RuntimeError, match="near-zero nonbasic reduced cost"):
        _solve_objective_optimum(
            frame,
            point_score=score,
            objective_rate=objective,
            budget=2.0,
            purpose_cap=0.75,
            time_limit=30,
            threads=1,
            role="primary_oot",
            period="2016-04",
            optimum_config=config["frontier"]["objective_optimum"],
            solver_config=config["solver"],
        )
