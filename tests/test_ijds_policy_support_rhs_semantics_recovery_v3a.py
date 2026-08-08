from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import pytest

from scripts.experiments.run_ijds_policy_support_rhs_semantics_recovery_v3a import (
    DEFAULT_CONFIG_PATH,
    _correct_lateral_comparisons,
    corrected_central_rhs_ranges,
    coverage_by_period,
    initial_gap_census,
    load_config,
    merge_intervals,
    preflight_output_paths,
    support_gaps,
    verify_v2_source,
)


def test_locked_v3_config_is_outcome_free_and_fail_closed() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)

    assert config["schema_version"] == "2026-07-21.3"
    assert config["source_ingest"]["outcome_columns_passed"] == []
    assert config["coverage"]["registered_support"] == [0.05, 0.12]
    assert config["coverage"]["gap_fill_passes"] == 1
    assert config["coverage"]["adaptive_additional_solves_after_registered_pass"] is False
    assert config["claim_boundary"]["no_continuous_joint_frontier_uniqueness"] is True
    assert config["claim_boundary"]["epsilon_mobility_is_not_nonuniqueness"] is True


def test_interval_merge_and_gap_detection_respect_registered_tolerance() -> None:
    intervals = [(0.05, 0.07), (0.07 + 5.0e-11, 0.08), (0.09, 0.12)]

    merged = merge_intervals(intervals, tolerance=1.0e-10)
    gaps = support_gaps(
        merged,
        support_lower=0.05,
        support_upper=0.12,
        tolerance=1.0e-10,
    )

    assert len(merged) == 2
    assert merged[0] == pytest.approx((0.05, 0.08))
    assert merged[1] == pytest.approx((0.09, 0.12))
    assert len(gaps) == 1
    assert gaps[0] == pytest.approx((0.08, 0.09))


@pytest.mark.parametrize(
    "intervals",
    [
        [(0.2, 0.1)],
        [(float("nan"), 0.2)],
        [(0.1, float("inf"))],
    ],
)
def test_interval_merge_rejects_invalid_intervals(
    intervals: list[tuple[float, float]],
) -> None:
    with pytest.raises(ValueError, match="finite and ordered"):
        merge_intervals(intervals, tolerance=1.0e-10)


def test_status_aware_central_correction_separates_active_and_basic_semantics() -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["v2_source"]["expected"].update(
        {
            "central_rows": 2,
            "central_risk_upper_rows": 1,
            "central_risk_basic_rows": 1,
            "v2_domain_clipped_cap_containment_failures": 1,
            "corrected_cap_containment_passes": 2,
        }
    )
    central = pd.DataFrame(
        {
            "period": ["2018-01", "2018-01"],
            "point_cap": [0.15, 0.25],
            "fresh_basis_cap_lower": [0.10, 0.10],
            "fresh_basis_cap_upper": [0.20, 0.20],
        }
    )
    rows = pd.DataFrame(
        {
            "period": ["2018-01", "2018-01"],
            "point_cap": [0.15, 0.25],
            "solve_origin": ["central", "central"],
            "row_name": ["point_risk_cap", "point_risk_cap"],
            "basis_status": ["upper", "basic"],
            "row_value": [150_000.0, 200_000.0],
            "row_lower": [-float("inf"), -float("inf")],
            "row_upper": [150_000.0, 250_000.0],
            "row_dual": [1.0, 0.0],
        }
    )

    corrected = corrected_central_rhs_ranges(central, rows, config=config)

    active = corrected.loc[corrected["risk_row_basis_status"].eq("upper")].iloc[0]
    basic = corrected.loc[corrected["risk_row_basis_status"].eq("basic")].iloc[0]
    assert active["status_aware_rhs_lower"] == pytest.approx(0.10)
    assert active["status_aware_rhs_upper"] == pytest.approx(0.20)
    assert bool(active["v2_reported_domain_clipped_cap_contained"]) is True
    assert basic["status_aware_rhs_lower"] == pytest.approx(0.20)
    assert basic["status_aware_rhs_upper"] == pytest.approx(1.0)
    assert bool(basic["v2_reported_domain_clipped_cap_contained"]) is False
    assert bool(basic["status_aware_cap_contained"]) is True


def test_initial_gap_maps_to_exact_registered_left_seed() -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["v2_source"]["expected"]["initial_positive_gaps"] = 1
    corrected = pd.DataFrame(
        {
            "period": ["2018-01", "2018-01"],
            "status_aware_rhs_lower": [0.05, 0.08],
            "status_aware_rhs_upper": [0.07, 0.12],
        }
    )
    probes = pd.DataFrame(
        {
            "period": ["2018-01"],
            "probe_side": ["left"],
            "point_cap": [0.08],
            "seed_cap": [0.075],
            "seed_expected_objective": [10.0],
            "seed_weighted_point_score": [0.075],
        }
    )

    gaps = initial_gap_census(corrected, probes, config=config)

    assert len(gaps) == 1
    assert gaps.loc[0, "target_gap_lower"] == pytest.approx(0.07)
    assert gaps.loc[0, "target_gap_upper"] == pytest.approx(0.08)
    assert gaps.loc[0, "registered_seed_cap"] == pytest.approx(0.075)
    assert gaps.loc[0, "seed_midpoint_match_distance"] == pytest.approx(0.0)


def test_coverage_table_distinguishes_initial_gap_from_final_connected_cover() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    corrected = pd.DataFrame(
        {
            "period": ["2018-01", "2018-01"],
            "status_aware_rhs_lower": [0.05, 0.08],
            "status_aware_rhs_upper": [0.07, 0.12],
        }
    )
    gap = pd.DataFrame(
        {
            "period": ["2018-01"],
            "status_aware_rhs_lower": [0.07],
            "status_aware_rhs_upper": [0.08],
            "target_gap_covered": [True],
        }
    )

    coverage = coverage_by_period(corrected, gap, config=config)

    assert int(coverage.loc[0, "initial_positive_gaps"]) == 1
    assert float(coverage.loc[0, "initial_maximum_positive_gap"]) == pytest.approx(0.01)
    assert int(coverage.loc[0, "final_positive_gaps"]) == 0
    assert bool(coverage.loc[0, "registered_support_covered"]) is True


@pytest.mark.requires_dvc_materialized
def test_real_v2_source_hashes_and_gap_census_reconcile() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    summary, paths = verify_v2_source(config)
    central = pd.read_parquet(paths["central_basis_diagnostics"])
    rows = pd.read_parquet(paths["row_slack_details"])
    probes = pd.read_parquet(paths["lateral_probe_diagnostics"])
    comparisons = pd.read_parquet(paths["breakpoint_comparisons"])
    faces = pd.read_parquet(paths["optimal_face_ranges"])

    corrected = corrected_central_rhs_ranges(central, rows, config=config)
    gaps = initial_gap_census(corrected, probes, config=config)
    lateral = _correct_lateral_comparisons(comparisons, faces, config=config)

    assert summary["results"]["certification_status"] == ("numerical_contract_failed_claim_blocked")
    assert len(corrected) == 7_297
    assert int(corrected["status_aware_cap_contained"].sum()) == 7_297
    assert int((~corrected["v2_reported_domain_clipped_cap_contained"]).sum()) == 66
    assert len(gaps) == 196
    assert gaps["period"].nunique() == 15
    assert gaps["target_gap_width"].max() == pytest.approx(0.0014766337338472102)
    assert gaps["seed_midpoint_match_distance"].max() <= 1.4e-16
    assert len(lateral) == 2_952
    assert not bool(lateral["allocation_difference_cooccurs_with_same_cap_epsilon_mobility"].any())
    assert not bool(lateral["lateral_numerical_discrepancy"].any())


def test_v3_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_config(DEFAULT_CONFIG_PATH))
    config["output"]["data_root"] = "data/processed/experiments/ijds_audit"
    config["output"]["model_root"] = "models/experiments/ijds_audit"

    paths = preflight_output_paths(config, repo_root=tmp_path)

    assert paths.data_dir.is_relative_to(tmp_path.resolve())
    assert paths.model_dir.is_relative_to(tmp_path.resolve())
    paths.data_dir.mkdir(parents=True)
    with pytest.raises(FileExistsError, match="output already exists"):
        preflight_output_paths(config, repo_root=tmp_path)
