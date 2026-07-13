from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.run_ijds_decision_active_simulation import (
    _direction_counts,
    prepare_output_paths,
)
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.decision_simulation import (
    FACTOR_COLUMNS,
    run_decision_active_simulation,
    validate_locked_decision_active_config,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/experiments/ijds_decision_active_simulation_2026-07-12.yaml"


def _tiny_config() -> dict[str, object]:
    config = load_v4_config(CONFIG_PATH)
    simulation = config["decision_active_simulation"]
    simulation.update(
        repetitions=2,
        fit_sample_size=800,
        candidate_sample_size=360,
        funded_units=36,
        score_shift_grid=[0.0],
        calibration_log_odds_shift_grid=[0.0, 1.5],
        taxonomy_groups_grid=[1, 5],
        normalized_cap_position_grid=[0.25, 0.75],
        censoring_rate_grid=[0.0, 0.15],
    )
    return config


@pytest.fixture(scope="module")
def tiny_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    return run_decision_active_simulation(_tiny_config())


def test_locked_decision_active_config_is_complete() -> None:
    config = load_v4_config(CONFIG_PATH)
    validate_locked_decision_active_config(config)
    simulation = config["decision_active_simulation"]
    cells = int(
        np.prod(
            [
                len(simulation[name])
                for name in (
                    "score_shift_grid",
                    "calibration_log_odds_shift_grid",
                    "taxonomy_groups_grid",
                    "normalized_cap_position_grid",
                    "censoring_rate_grid",
                )
            ]
        )
    )
    assert cells == 72
    assert cells * int(simulation["repetitions"]) == 3_600
    assert simulation["factor_pairing"] == "common_random_numbers_by_repetition"


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("role", "empirical_validation", "cannot be promoted"),
        ("random_seed", 7, "seed changed"),
        ("factor_pairing", "independent_cells", "paired common random numbers"),
    ],
)
def test_locked_validator_rejects_claim_or_design_drift(
    field: str, replacement: object, message: str
) -> None:
    config = load_v4_config(CONFIG_PATH)
    config["decision_active_simulation"][field] = replacement
    with pytest.raises(ValueError, match=message):
        validate_locked_decision_active_config(config)


def test_small_factorial_is_deterministic(
    tiny_results: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    repetitions, summary = tiny_results
    replay_repetitions, replay_summary = run_decision_active_simulation(_tiny_config())
    pd.testing.assert_frame_equal(repetitions, replay_repetitions, check_exact=True)
    pd.testing.assert_frame_equal(summary, replay_summary, check_exact=True)
    assert len(repetitions) == 32
    assert len(summary) == 16


def test_common_random_number_pairing_holds(
    tiny_results: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    repetitions, _ = tiny_results
    assert repetitions.groupby("repetition")["fit_prevalence"].nunique().eq(1).all()
    geometry_groups = ["repetition", "score_shift", "taxonomy_groups"]
    assert (
        repetitions.groupby(geometry_groups, observed=True)[
            ["mean_width", "set_both_share", "recipe_residual_quantile_max"]
        ]
        .nunique()
        .eq(1)
        .all()
        .all()
    )
    outcome_groups = [
        "repetition",
        "score_shift",
        "calibration_log_odds_shift",
        "taxonomy_groups",
    ]
    assert (
        repetitions.groupby(outcome_groups, observed=True)[
            ["candidate_outcome_prevalence", "candidate_coverage_full"]
        ]
        .nunique()
        .eq(1)
        .all()
        .all()
    )


def test_decision_constraints_and_sharp_bounds_reconcile(
    tiny_results: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    repetitions, _ = tiny_results
    assert repetitions["guardrail_cap_binding"].all()
    assert repetitions["guardrail_cap_slack"].abs().max() <= 1e-7
    assert (
        repetitions[["guardrail_budget_residual", "c0_budget_residual", "c2_budget_residual"]]
        .abs()
        .to_numpy()
        .max()
        <= 1e-8
    )
    assert repetitions["c2_match_residual"].abs().max() <= 1e-10
    assert repetitions["c0_point_minus_guardrail_objective"].min() >= -1e-5
    assert repetitions["point_minus_guardrail_objective"].min() >= -1e-5
    np.testing.assert_allclose(
        repetitions["guardrail_realized_normalized_cap_position"],
        repetitions["normalized_cap_position"],
        rtol=0.0,
        atol=1e-7,
    )
    for comparator in ("c0", "c2"):
        for metric in ("payoff", "default", "miscoverage"):
            prefix = f"guardrail_minus_{comparator}_{metric}"
            assert (repetitions[f"{prefix}_lower"] <= repetitions[f"{prefix}_full"] + 1e-12).all()
            assert (repetitions[f"{prefix}_full"] <= repetitions[f"{prefix}_upper"] + 1e-12).all()
    assert repetitions.loc[repetitions["taxonomy_groups"].eq(5), "c0_allocation_changed"].any()
    assert repetitions.loc[repetitions["taxonomy_groups"].eq(5), "c2_allocation_changed"].any()


def test_direction_census_retains_every_cell_and_repetition(
    tiny_results: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    repetitions, _ = tiny_results
    directions = _direction_counts(repetitions, tolerance=1e-12)
    totals = directions.groupby(["comparator", "metric"])["repetitions"].sum()
    assert totals.eq(len(repetitions)).all()
    per_cell = directions.groupby(["comparator", "metric", *FACTOR_COLUMNS], observed=True)[
        "repetitions"
    ].sum()
    assert per_cell.eq(2).all()


def test_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_v4_config(CONFIG_PATH))
    config["run_tag"] = "decision-active-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)
    assert paths.data_dir == (
        tmp_path / "data/processed/experiments/ijds_audit/decision-active-test"
    )
    assert paths.model_dir == (tmp_path / "models/experiments/ijds_audit/decision-active-test")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)
