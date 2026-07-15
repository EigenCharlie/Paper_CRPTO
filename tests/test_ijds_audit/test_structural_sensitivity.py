"""Tests for the complete structural-sensitivity grid."""

from __future__ import annotations

from src.ijds_audit.structural_sensitivity import declared_scenarios


def test_declared_structural_grid_is_complete_and_has_one_baseline() -> None:
    config = {
        "structural_grid": {
            "budgets": [500_000.0, 1_000_000.0, 2_000_000.0],
            "purpose_caps": [0.20, 0.25, 0.30, 1.00],
            "lgds": [0.25, 0.45, 0.65],
        }
    }
    scenarios = declared_scenarios(config)
    assert len(scenarios) == 36
    assert len({item["scenario_id"] for item in scenarios}) == 36
    assert sum(item["is_baseline"] for item in scenarios) == 1
