from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.experiments.run_ijds_normalized_objective_frontier_v2 import (
    preflight_output_paths,
    prepare_output_paths,
)
from src.ijds_challengers.evaluation import (
    build_endpoint_contrasts,
    direction_from_bounds,
    validate_outcome_alignment,
)
from src.ijds_challengers.evaluation_config import EXPECTED_FREEZE_SHA256, load_v2_config

ROOT = Path(__file__).resolve().parents[1]
V3_CONFIG = ROOT / "configs/experiments/ijds_normalized_objective_frontier_2026-07-14_v3.yaml"
ACTIVE_CONFIG = ROOT / "configs/experiments/ijds_normalized_objective_frontier_2026-07-15_v5.yaml"


def test_active_config_locks_freeze_grid_and_no_selection() -> None:
    config = load_v2_config(ACTIVE_CONFIG)
    assert config["source_frontier"]["freeze"]["sha256"] == EXPECTED_FREEZE_SHA256
    assert config["evaluation"]["expected_window_contrasts"] == 48
    assert config["evaluation"]["expected_monthly_contrasts"] == 720
    assert config["evaluation"]["expected_metric_directions"] == 144
    assert all(bool(value) for value in config["claim_boundary"].values())


def test_v3_reuses_v1c_freeze_with_reconstructed_endpoint() -> None:
    config = load_v2_config(V3_CONFIG)
    assert config["source_frontier"]["freeze"]["sha256"] == EXPECTED_FREEZE_SHA256
    assert config["parent"]["config"].endswith("2026-07-14_v3.yaml")
    assert config["outcomes"]["endpoint_contract"].startswith(
        "conservative_terminal_status_reconstruction"
    )


def test_v5_changes_only_endpoint_reason_taxonomy_and_recovery_implementation() -> None:
    config = load_v2_config(ACTIVE_CONFIG)
    assert config["parent"]["config"].endswith("2026-07-15_v5.yaml")
    recovery = config["endpoint_reason_recovery"]
    assert recovery["require_exact_non_float_reference_equivalence"] is True
    assert recovery["float_atol"] == 5.0e-14
    assert recovery["float_rtol"] == 5.0e-14
    assert config["evaluation"] == load_v2_config(V3_CONFIG)["evaluation"]


def test_active_config_rejects_coordinate_selection(tmp_path: Path) -> None:
    config = load_v2_config(ACTIVE_CONFIG)
    config["claim_boundary"]["no_coordinate_selection"] = False
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="claim boundary"):
        load_v2_config(path)


def test_active_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_v2_config(ACTIVE_CONFIG))
    config["run_tag"] = "frontier-v2-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)
    assert paths.data_dir == tmp_path / "data/processed/experiments/ijds_audit/frontier-v2-test"
    assert paths.model_dir == tmp_path / "models/experiments/ijds_audit/frontier-v2-test"
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)


def test_active_output_preflight_does_not_create_directories(tmp_path: Path) -> None:
    config = copy.deepcopy(load_v2_config(ACTIVE_CONFIG))
    config["run_tag"] = "frontier-v2-preflight-test"
    paths = preflight_output_paths(config, repo_root=tmp_path)
    assert not paths.data_dir.exists()
    assert not paths.model_dir.exists()
    paths.model_dir.mkdir(parents=True)
    with pytest.raises(FileExistsError, match="already exists"):
        preflight_output_paths(config, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("lower", "upper", "tolerance", "expected"),
    [
        (0.2, 0.3, 1e-6, "gamma_1_higher"),
        (-0.3, -0.2, 1e-6, "gamma_1_lower"),
        (-0.2, 0.3, 1e-6, "crosses_zero"),
        (-1e-8, 1e-8, 1e-6, "exact_zero"),
    ],
)
def test_direction_classification(
    lower: float,
    upper: float,
    tolerance: float,
    expected: str,
) -> None:
    assert direction_from_bounds(lower, upper, tolerance=tolerance) == expected


def test_outcome_alignment_requires_exact_role_and_period() -> None:
    config = copy.deepcopy(load_v2_config(ACTIVE_CONFIG))
    config["evaluation"]["evaluated_roles"] = ["primary_oot"]
    config["evaluation"]["expected_candidate_counts"] = {"primary_oot": 2}
    allocations = pd.DataFrame(
        {
            "id": ["a", "b"],
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-04"],
        }
    )
    outcomes = pd.DataFrame(
        {
            "id": ["a", "b"],
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-05"],
            "snapshot_default": pd.Series([0, 1], dtype="Int8"),
            "snapshot_resolution": ["fully_paid", "charged_off"],
        }
    )
    with pytest.raises(RuntimeError, match="role/period"):
        validate_outcome_alignment(allocations, outcomes, config=config)


def test_endpoint_contrast_uses_common_unresolved_union() -> None:
    config = copy.deepcopy(load_v2_config(ACTIVE_CONFIG))
    config["evaluation"].update(
        rulers=["normalized_score"],
        coordinates=[0.5],
        expected_primary_months=2,
    )
    rows: list[dict[str, object]] = []
    for period, outcome in (("2016-04", 0.0), ("2016-05", float("nan"))):
        for label, exposures in (
            ("normalized_score_g100_c050", (70.0, 30.0)),
            ("normalized_score_g000_c050", (30.0, 70.0)),
        ):
            for loan_id, exposure, rate in zip(
                (f"{period}-a", f"{period}-b"),
                exposures,
                (0.1, 0.2),
                strict=True,
            ):
                rows.append(
                    {
                        "window_id": "w01",
                        "role": "primary_oot",
                        "period": period,
                        "policy_label": label,
                        "id": loan_id,
                        "exposure": exposure,
                        "contractual_rate": rate,
                        "conformal_lower": 0.0,
                        "conformal_upper": 0.8,
                        "snapshot_default": outcome,
                        "expected_payoff_contribution": exposure * 0.05,
                    }
                )
    joined = pd.DataFrame(rows)
    structure = pd.DataFrame(
        {
            "window_id": ["w01", "w01"],
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-05"],
            "ruler": ["normalized_score", "normalized_score"],
            "coordinate": [0.5, 0.5],
            "normalized_exposure_distance": [0.4, 0.4],
        }
    )
    window, monthly = build_endpoint_contrasts(
        joined,
        structure,
        config=config,
        lgd=1.0,
    )
    assert len(window) == 1
    assert len(monthly) == 2
    assert window.loc[0, "unresolved_union_loans"] == 2
    assert (
        window.loc[0, "realized_payoff_difference_lower"]
        <= window.loc[0, "realized_payoff_difference_upper"]
    )


def test_endpoint_contrast_rejects_inconsistent_loan_attributes() -> None:
    config = copy.deepcopy(load_v2_config(ACTIVE_CONFIG))
    config["evaluation"].update(
        rulers=["normalized_score"],
        coordinates=[0.5],
        expected_primary_months=1,
    )
    joined = pd.DataFrame(
        {
            "window_id": ["w01", "w01"],
            "id": ["loan-a", "loan-a"],
            "role": ["primary_oot", "primary_oot"],
            "period": ["2016-04", "2016-04"],
            "policy_label": [
                "normalized_score_g100_c050",
                "normalized_score_g000_c050",
            ],
            "exposure": [60.0, 40.0],
            "contractual_rate": [0.10, 0.11],
            "conformal_lower": [0.0, 0.0],
            "conformal_upper": [0.8, 0.8],
            "snapshot_default": [0.0, 0.0],
            "expected_payoff_contribution": [3.0, 2.0],
        }
    )
    structure = pd.DataFrame(
        {
            "window_id": ["w01"],
            "role": ["primary_oot"],
            "period": ["2016-04"],
            "ruler": ["normalized_score"],
            "coordinate": [0.5],
            "normalized_exposure_distance": [0.2],
        }
    )
    with pytest.raises(RuntimeError, match="attributes disagree"):
        build_endpoint_contrasts(
            joined,
            structure,
            config=config,
            lgd=1.0,
        )
