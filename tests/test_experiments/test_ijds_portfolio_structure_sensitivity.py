"""Locked numerical contracts for structural-sensitivity V1--V6."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.experiments.run_ijds_portfolio_structure_sensitivity import (
    STATUS_V6,
    _frontier_config,
    _load_config,
)
from src.ijds_challengers.config import load_frontier_config

REPO = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO / "configs/experiments"
V6_CONFIG = CONFIG_DIR / "ijds_portfolio_structure_sensitivity_2026-07-15_v6.yaml"


@pytest.mark.parametrize(
    "name",
    [
        "ijds_portfolio_structure_sensitivity_2026-07-14.yaml",
        "ijds_portfolio_structure_sensitivity_2026-07-15_v2.yaml",
        "ijds_portfolio_structure_sensitivity_2026-07-15_v3.yaml",
        "ijds_portfolio_structure_sensitivity_2026-07-15_v4.yaml",
        "ijds_portfolio_structure_sensitivity_2026-07-15_v5.yaml",
        "ijds_portfolio_structure_sensitivity_2026-07-15_v6.yaml",
    ],
)
def test_every_structural_protocol_retains_its_locked_contract(name: str) -> None:
    config = _load_config(CONFIG_DIR / name)

    assert config["structural_grid"]["scenarios"] == 36
    assert config["claim_boundary"]["outcome_based_scenario_selection"] is False
    assert config["claim_boundary"]["policy_winner"] is False


def test_v6_recovers_only_complete_v5_shards_and_recomputes_one() -> None:
    config = _load_config(V6_CONFIG)
    recovery = config["execution"]["recovery"]

    assert config["protocol_status"] == STATUS_V6
    assert config["execution"]["freeze_workers"] == 1
    assert recovery["expected_recovered_scenarios"] == 35
    assert recovery["expected_missing_scenario_ids"] == ["b0500k_p020_l025"]
    assert config["lineage"]["scientific_grid_changed"] is False
    assert config["lineage"]["outcomes_inspected_for_amendment"] is False


def test_v6_overrides_only_the_diagnosed_order_tolerance() -> None:
    structural = _load_config(V6_CONFIG)
    parent = load_frontier_config(REPO / structural["parent"]["frontier_config"])

    amended = _frontier_config(parent, structural)

    assert parent["solver"]["order_exposure_distance_tolerance"] == 1.0e-10
    assert amended["solver"]["order_exposure_distance_tolerance"] == 1.0e-8
    assert amended["solver"]["order_objective_tolerance_dollars"] == 1.0e-5
    assert amended["frontier"]["normalized_score"]["minimum_endpoint_retry_slacks"] == [
        1.0e-12,
        1.0e-10,
    ]


def test_v6_rejects_a_larger_unlocked_order_tolerance(tmp_path: Path) -> None:
    payload = yaml.safe_load(V6_CONFIG.read_text(encoding="utf-8"))
    payload["numerics"]["order_exposure_distance_tolerance"] = 1.0e-7
    changed = tmp_path / "changed.yaml"
    changed.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="must remain 1e-8"):
        _load_config(changed)
