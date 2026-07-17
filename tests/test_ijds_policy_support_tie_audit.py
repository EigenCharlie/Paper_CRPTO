from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.experiments.run_ijds_policy_support_tie_audit import (
    DEFAULT_CONFIG_PATH,
    load_config,
    prepare_output_paths,
)
from src.ijds_audit.policy_support import (
    build_cap_census,
    classify_cap,
    point_basis_diagnostics,
)
from src.ijds_audit.portfolio import PointPortfolioSession

ROOT = Path(__file__).resolve().parents[1]
PARENT_PORTFOLIO = (
    ROOT
    / "data/processed/experiments/ijds_audit"
    / "ijds-binary-geometry-frontier-v4-2026-07-12-v1/portfolio"
)


def test_policy_support_config_is_locked_and_outcome_free() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    assert config["protocol_status"] == "locked_outcome_free_structural_audit_before_execution"
    assert config["family_audit"]["gamma_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert config["claim_boundary"]["outcome_columns_passed"] == []
    allowed = config["source_ingest"]["allowed_raw_columns"]
    assert allowed == ["id", "loan_amnt", "int_rate", "purpose"]


def test_config_rejects_policy_promotion(tmp_path: Path) -> None:
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8").replace(
        "no_policy_promotion: true", "no_policy_promotion: false"
    )
    path = tmp_path / "broken.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="promotion must remain forbidden"):
        load_config(path)


@pytest.mark.parametrize(
    ("cap", "expected"),
    [
        (0.04, "infeasible"),
        (0.05, "minimum_boundary"),
        (0.07, "decision_active"),
        (0.10, "objective_boundary"),
        (0.12, "objective_slack"),
    ],
)
def test_cap_classification_has_explicit_boundaries(cap: float, expected: str) -> None:
    assert (
        classify_cap(
            cap,
            minimum_feasible_score=0.05,
            unconstrained_objective_score=0.10,
            tolerance=1e-10,
        )
        == expected
    )


def test_cap_classification_rejects_reversed_domain() -> None:
    with pytest.raises(ValueError, match="below the feasible minimum"):
        classify_cap(
            0.1,
            minimum_feasible_score=0.2,
            unconstrained_objective_score=0.1,
            tolerance=1e-10,
        )


def test_parent_cap_census_is_complete_and_tolerance_deduplicated() -> None:
    records = pd.read_parquet(PARENT_PORTFOLIO / "outcome_free_solve_records.parquet")
    support = pd.read_parquet(PARENT_PORTFOLIO / "development_comparator_support.parquet")
    frontier = pd.read_parquet(PARENT_PORTFOLIO / "exact_frontier_breakpoints.parquet")
    periods = sorted(records.loc[records["role"].eq("primary_oot"), "period"].unique())
    census = build_cap_census(
        records,
        support,
        frontier,
        periods=periods,
        broad_support=(0.05, 0.12),
        tolerance=1e-10,
    )
    assert len(census) == 7_297
    assert census["period"].nunique() == 15
    assert int(census["is_named_c0"].sum()) == 45
    assert int(census["is_named_c1"].sum()) == 1_080
    assert int(census["is_named_c2"].sum()) == 1_079
    assert int(census["is_period_basis_breakpoint"].sum()) == 2_952
    assert (census["cluster_cap_max"] - census["cluster_cap_min"]).max() <= 1e-10


def test_basis_diagnostics_reconcile_a_small_point_lp() -> None:
    frame = pd.DataFrame(
        {
            "loan_amnt": [60.0, 50.0, 40.0, 30.0, 20.0],
            "purpose": ["a", "a", "b", "b", "c"],
        }
    )
    point = np.array([0.03, 0.06, 0.09, 0.12, 0.15])
    objective = np.array([0.031, 0.081, 0.044, 0.103, 0.017])
    session = PointPortfolioSession(
        frame,
        point_score=point,
        objective_rate=objective,
        budget=100.0,
        purpose_cap=0.6,
        threads=1,
    )
    solution = session.solve(0.09)
    diagnostics = point_basis_diagnostics(
        session,
        solution,
        dual_tolerance=1e-7,
        primal_tolerance=1e-9,
    )
    assert diagnostics["basis_valid"] is True
    assert diagnostics["minimum_absolute_nonbasic_reduced_cost"] > 1e-7
    assert diagnostics["near_zero_nonbasic_reduced_costs"] == 0
    assert abs(diagnostics["objective_reconciliation_error"]) < 1e-12
    assert diagnostics["maximum_dual_sign_violation"] <= 1e-12


def test_output_paths_are_contained_and_no_overwrite(tmp_path: Path) -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["run_tag"] = "policy-support-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)
    assert paths.data_dir == (
        tmp_path / "data/processed/experiments/ijds_audit/policy-support-test"
    )
    assert paths.model_dir == (tmp_path / "models/experiments/ijds_audit/policy-support-test")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)
