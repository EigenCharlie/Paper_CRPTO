"""Contracts for complete-grid portfolio-structure evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.ijds_audit.publication_sources import load_verified_source_registry
from src.ijds_audit.structural_evidence import (
    load_structural_sensitivity_evidence,
    structural_publication_table,
)

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "configs/ijds_active_evidence_sources.yaml"


def _load_active_structural_evidence():
    registry, sources = load_verified_source_registry(REGISTRY, repo_root=REPO)
    two_ruler = json.loads(sources["two_ruler_manifest"].read_text(encoding="utf-8"))
    reference = pd.read_parquet(
        two_ruler["evaluation_artifacts"]["window_endpoint_contrasts"]["path"]
    )
    return load_structural_sensitivity_evidence(
        sources["structural_sensitivity_summary"],
        freeze_path=sources["structural_sensitivity_freeze"],
        config_path=sources["structural_sensitivity_config"],
        identity=registry["sensitivities"]["portfolio_structure"],
        repo_root=REPO,
        reference_two_ruler=reference,
    )


def test_active_structural_evidence_is_complete_hash_verified_and_unselected() -> None:
    evidence = _load_active_structural_evidence()

    assert evidence.summary["scenario_count"] == 36
    assert all(value is None for value in evidence.summary["selection"].values())
    assert evidence.summary["baseline_reconciliation_maxima"] == {
        "realized_payoff_difference_lower": 0.0,
        "realized_payoff_difference_upper": 0.0,
        "weighted_default_difference_lower": 0.0,
        "weighted_default_difference_upper": 0.0,
        "weighted_miscoverage_difference_lower": 0.0,
        "weighted_miscoverage_difference_upper": 0.0,
    }
    assert evidence.findings["complete_cartesian_grid"] is True
    assert evidence.findings["universally_favorable_scenarios"] == 0
    assert evidence.findings["universally_adverse_scenarios"] == 0
    assert evidence.findings["portfolios_per_scenario"] == 1440
    assert evidence.findings["purpose_cap_binding_share_by_cap"] == {
        "0.20": 1.0,
        "0.25": 1.0,
        "0.30": 1.0,
        "1.00": 0.0,
    }
    assert evidence.findings["frontier_constraint_binding_share_by_budget"] == {
        "500000": 1.0,
        "1000000": 1.0,
        "2000000": 1.0,
    }
    assert evidence.findings["maximum_loan_weight_by_budget"] == {
        "500000": 0.08,
        "1000000": 0.04,
        "2000000": 0.02,
    }


def test_structural_publication_table_reports_every_scenario_and_direction() -> None:
    table = structural_publication_table(_load_active_structural_evidence())

    assert len(table) == 36
    assert table["scenario_id"].is_unique
    assert table["activity_portfolios"].eq(1440).all()
    assert table["activity_frontier_constraint_binding_share"].eq(1.0).all()
    for metric in ("standardized_payoff", "funded_default", "funded_binary_miscoverage"):
        columns = [
            column for column in table if column.startswith(metric) and column.endswith("_cells")
        ]
        assert len(columns) == 4
        assert table[columns].sum(axis=1).eq(48).all()
