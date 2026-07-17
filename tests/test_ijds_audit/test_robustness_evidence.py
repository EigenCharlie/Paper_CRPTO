"""Contracts for fit-label completion and allocation-granularity evidence."""

from __future__ import annotations

from pathlib import Path

from src.ijds_audit.publication_sources import load_verified_source_registry
from src.ijds_audit.robustness_evidence import (
    allocation_granularity_publication_table,
    fit_label_completion_publication_table,
    load_allocation_granularity_evidence,
    load_fit_label_completion_evidence,
)

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "configs/ijds_active_evidence_sources.yaml"


def _registry():
    return load_verified_source_registry(REGISTRY, repo_root=REPO)


def test_active_fit_label_completion_is_complete_unselected_and_hash_verified() -> None:
    registry, sources = _registry()
    evidence = load_fit_label_completion_evidence(
        sources["fit_label_completion_summary"],
        freeze_path=sources["fit_label_completion_freeze"],
        identity=registry["sensitivities"]["fit_label_completion"],
        repo_root=REPO,
    )

    assert evidence.findings == {
        "coverage_cells": 32,
        "phase_cells": 32,
        "all_scenarios_all_windows_upper_below_nominal": True,
        "w7_w8_crossing_by_scenario": {
            "observed_only": True,
            "all_unavailable_nondefault": True,
            "all_unavailable_default": False,
            "hindsight_terminal": True,
        },
        "w7_w8_crossing_scenarios": 3,
        "w7_w8_crossing_in_all_scenarios": False,
        "unavailable_fit_labels_by_split": {
            "pd_development": 41,
            "probability_calibration": 24,
            "conformal_fit": 150,
        },
        "unavailable_fit_labels_total": 215,
    }
    assert evidence.freeze["evaluation_outcome_columns_passed_to_fitting"] == []
    assert set(evidence.outcome_free_artifacts) == {
        "scores",
        "fit_audit",
        "scenario_audit",
        "recipes",
    }


def test_fit_label_publication_table_reports_all_declared_corners() -> None:
    registry, sources = _registry()
    evidence = load_fit_label_completion_evidence(
        sources["fit_label_completion_summary"],
        freeze_path=sources["fit_label_completion_freeze"],
        identity=registry["sensitivities"]["fit_label_completion"],
        repo_root=REPO,
    )
    table = fit_label_completion_publication_table(evidence)

    assert len(table) == 4
    assert table["fit_label_scenario"].is_unique
    assert table["windows_upper_below_nominal"].eq(8).all()
    assert table["coverage_upper_max"].lt(0.90).all()
    assert int(table["w7_w8_stratum2_crossing"].sum()) == 3


def test_active_allocation_granularity_is_complete_unselected_and_hash_verified() -> None:
    registry, sources = _registry()
    evidence = load_allocation_granularity_evidence(
        sources["allocation_granularity_summary"],
        freeze_path=sources["allocation_granularity_freeze"],
        identity=registry["sensitivities"]["allocation_granularity"],
        repo_root=REPO,
    )

    assert evidence.findings["tracks"] == 96
    assert evidence.findings["portfolios"] == 1440
    assert evidence.findings["changed_rows"] == 2985
    assert evidence.findings["cash_share_max"] < 3.4e-5
    assert evidence.findings["payoff_rate_perturbation_abs_max"] < 3.5e-6
    assert evidence.findings["default_rate_perturbation_abs_max"] < 1.3e-5
    assert evidence.findings["miscoverage_rate_perturbation_abs_max"] < 1.2e-5
    assert evidence.freeze["outcome_columns_passed_to_rounding"] == []
    assert set(evidence.outcome_free_artifacts) == {
        "rounded_allocations",
        "rounded_solve_records",
        "granularity_audit",
    }


def test_allocation_granularity_publication_table_is_one_complete_row() -> None:
    registry, sources = _registry()
    evidence = load_allocation_granularity_evidence(
        sources["allocation_granularity_summary"],
        freeze_path=sources["allocation_granularity_freeze"],
        identity=registry["sensitivities"]["allocation_granularity"],
        repo_root=REPO,
    )
    table = allocation_granularity_publication_table(evidence)

    assert len(table) == 1
    assert int(table.iloc[0]["tracks"]) == 96
    assert int(table.iloc[0]["source_rows"]) == 143175
