from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.build_ijds_policy_support_optimal_face_evidence import (
    EVIDENCE_PATH,
    V2_PROTOCOL_COMMIT,
    V2_PROTOCOL_TAG,
    V3A_PROTOCOL_COMMIT,
    V3A_PROTOCOL_TAG,
    _verify_descriptor,
    build,
)
from src.utils.isolated_experiment import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Optimal-face evidence must be a JSON object.")
    return payload


@pytest.mark.requires_dvc_materialized
def test_optimal_face_evidence_build_is_byte_idempotent() -> None:
    build()
    first = sha256_file(EVIDENCE_PATH)
    build()
    assert sha256_file(EVIDENCE_PATH) == first


def test_optimal_face_evidence_verifies_complete_lineage() -> None:
    evidence = _evidence()
    lineage = evidence["lineage"]
    assert evidence["status"] == "complete_outcome_free_policy_support_optimal_face_evidence"
    assert (
        evidence["certification_status"]
        == "rhs_support_coverage_recovered_numerical_uniqueness_claim_blocked"
    )
    assert evidence["publication_role"] == (
        "registered_intermediate_source_for_single_primary_evidence_manifest"
    )
    assert evidence["paper_facing_numeric_authority"] is False
    assert lineage["verified_result_artifact_descriptors"] == 17
    assert lineage["verified_deterministic_summary_descriptors"] == 2
    assert lineage["verified_execution_receipt_identity_contracts"] == 2
    assert lineage["lineage_files_described"] == 21
    assert lineage["protocol_tags_resolve_to_locked_commits"] is True
    assert lineage["v3a_retains_exact_v2_descriptor_census"] is True
    assert lineage["v2"]["protocol_tag"] == V2_PROTOCOL_TAG
    assert lineage["v2"]["protocol_commit"] == V2_PROTOCOL_COMMIT
    assert lineage["v3a"]["protocol_tag"] == V3A_PROTOCOL_TAG
    assert lineage["v3a"]["protocol_commit"] == V3A_PROTOCOL_COMMIT
    assert len(lineage["v2"]["verified_artifacts"]) == 10
    assert len(lineage["v3a"]["verified_artifacts"]) == 7


@pytest.mark.requires_dvc_materialized
def test_descriptor_verifier_fails_closed_on_hash_drift() -> None:
    descriptor = dict(_evidence()["lineage"]["v2"]["summary"])
    descriptor["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="sha256"):
        _verify_descriptor(descriptor)


def test_status_aware_rhs_semantics_recomputes_the_complete_census() -> None:
    result = _evidence()["results"]["status_aware_rhs_semantics"]
    assert result["rows"] == 7_297
    assert result["periods"] == 15
    assert result["upper_rows"] == 7_228
    assert result["basic_rows"] == 69
    assert result["v2_reported_domain_clipped_cap_containment_failures"] == 66
    assert result["status_aware_cap_containment_passes"] == 7_297
    assert result["maximum_status_aware_cap_containment_violation"] < 1e-15
    assert result["basic_row_maximum_absolute_dual"] == 0.0
    assert result["status_aware_semantics_gate_passed"] is True


def test_registered_gap_replay_recovers_only_bounded_numerical_coverage() -> None:
    results = _evidence()["results"]
    coverage = results["rhs_support_coverage"]
    assert coverage["periods"] == 15
    assert coverage["registered_support_lower"] == 0.05
    assert coverage["registered_support_upper"] == 0.12
    assert coverage["absolute_gap_tolerance"] == 1.0e-10
    assert coverage["initial_positive_gaps"] == 196
    assert coverage["registered_gap_seed_solves"] == 196
    assert coverage["upper_status_gap_seed_solves"] == 196
    assert coverage["basic_status_gap_seed_solves"] == 0
    assert coverage["strictly_interior_gap_seed_solves"] == 196
    assert coverage["maximum_seed_midpoint_match_distance"] < 1.0e-12
    assert coverage["maximum_v2_seed_expected_objective_difference"] == 0.0
    assert coverage["maximum_v2_seed_weighted_point_difference"] == 0.0
    assert coverage["status_aware_seed_cap_containment_passes"] == 196
    assert coverage["targeted_gap_coverage_passes"] == 196
    assert coverage["recomputed_target_gap_coverage_passes"] == 196
    assert coverage["covered_periods"] == 15
    assert coverage["final_positive_gaps"] == 0
    assert coverage["maximum_final_positive_gap"] == 0.0
    assert coverage["zero_tolerance_positive_seams"] == 465
    assert coverage["maximum_zero_tolerance_seam_width"] == pytest.approx(1.6653345369377348e-16)
    assert coverage["total_zero_tolerance_seam_width"] == pytest.approx(6.6405214660392176e-15)
    assert coverage["positive_gaps_at_1e_15"] == 0
    assert coverage["maximum_gap_reconstruction_difference"] == 0.0
    assert coverage["persisted_coverage_table_reconciled"] is True
    assert coverage["rhs_support_coverage_gate_passed"] is True
    assert results["rhs_coverage_recovered_without_uniqueness_promotion"] is True


def test_all_recomputed_basis_dual_and_feasibility_contracts_pass() -> None:
    contracts = _evidence()["results"]["numerical_contracts"]
    assert contracts["v2_central"]["rows"] == 7_297
    assert contracts["v2_lateral_probes"]["rows"] == 5_874
    assert contracts["v3a_gap_replay"]["rows"] == 196
    for key in ("v2_central", "v2_lateral_probes", "v3a_gap_replay"):
        contract = contracts[key]
        assert contract["valid_basis_solution_rows"] == contract["rows"]
        assert contract["unsupported_nonbasic_statuses"] == 0
        assert contract["maximum_dual_sign_violation"] == 0.0
        assert contract["maximum_absolute_objective_reconciliation_error"] < 1e-5
        assert contract["maximum_normalized_policy_constraint_violation"] < 1e-8
        assert contract["maximum_primal_bound_violation"] < 1e-9
        assert contract["numerical_contract_passed"] is True
    assert contracts["v2_all_row_slack_details"]["rows"] == 186_202
    assert contracts["v3a_all_gap_row_slack_details"]["rows"] == 2_786
    assert contracts["v2_all_row_slack_details"]["near_zero_nonbasic_rows"] == 0
    assert contracts["v3a_all_gap_row_slack_details"]["near_zero_nonbasic_rows"] == 0
    assert contracts["v2_all_row_slack_details"]["row_contract_passed"] is True
    assert contracts["v3a_all_gap_row_slack_details"]["row_contract_passed"] is True


def test_frozen_bridge_and_corrected_lateral_stability_reconcile() -> None:
    results = _evidence()["results"]
    frozen = results["frozen_allocation_reconciliation"]
    lateral = results["corrected_lateral_stability"]
    assert frozen["rows"] == 7_297
    assert frozen["passed_rows"] == 7_297
    assert frozen["maximum_l1_exposure_dollars"] < 1e-7
    assert frozen["maximum_normalized_l1_exposure"] < 1e-10
    assert frozen["frozen_allocation_reconciliation_gate_passed"] is True
    assert lateral["breakpoint_rows"] == 2_952
    assert lateral["allocation_difference_rows"] == 0
    assert lateral["corrected_same_cap_mobility_cooccurrence_rows"] == 0
    assert lateral["allocation_difference_without_same_cap_mobility_rows"] == 0
    assert lateral["lateral_objective_discrepancy_rows"] == 0
    assert lateral["lateral_weighted_point_discrepancy_rows"] == 0
    assert lateral["maximum_pairwise_allocation_distance"] < 1e-10
    assert lateral["v2_misreported_cooccurrence_rows"] == 7
    assert lateral["corrected_lateral_gate_passed"] is True


def test_scale_aware_warnings_block_uniqueness_without_claiming_an_exact_tie() -> None:
    warnings = _evidence()["results"]["warnings_and_mobility"]
    assert warnings["v2_warning_rows"] == 13
    assert warnings["v2_central_warning_rows"] == 5
    assert warnings["v2_lateral_warning_rows"] == 8
    assert warnings["v2_unique_cap_variable_targets"] == 8
    assert warnings["v3a_gap_seed_warning_rows"] == 1
    assert warnings["v3a_warning_repeats_same_v2_variable_at_both_neighbor_endpoints"] is True
    assert warnings["v3a_warning_period"] == "2016-05"
    assert warnings["v3a_warning_variable_name"] == "79672779"
    assert warnings["v3a_warning_registered_seed_cap"] == pytest.approx(0.0772591347422286)
    assert warnings["combined_warning_rows"] == 14
    assert warnings["v2_conditional_range_rows"] == 8
    assert warnings["minimum_conditional_solver_run_time_seconds"] > 0.0
    assert (
        warnings["maximum_conditional_solver_run_time_seconds"]
        >= warnings["minimum_conditional_solver_run_time_seconds"]
    )
    assert warnings["maximum_conditional_face_primal_bound_violation"] < 1.0e-9
    assert warnings["maximum_v2_normalized_coordinate_mobility"] == pytest.approx(
        9.615019985630913e-7
    )
    assert warnings["maximum_v2_coordinate_exposure_mobility_dollars"] == pytest.approx(
        0.9615019985630913
    )
    assert warnings["epsilon_near_optimal_mobility_is_exact_alternate_optimum"] is False
    assert warnings["warnings_block_strict_numerical_uniqueness_promotion"] is True
    assert warnings["strict_numerical_uniqueness_gate_passed"] is False


def test_evidence_remains_outcome_free_and_claim_bounded() -> None:
    evidence = _evidence()
    boundary = evidence["claim_boundary"]
    assert evidence["outcome_columns_passed"] == []
    assert evidence["protected_stages_run"] == []
    assert evidence["protected_artifacts_written"] == []
    assert boundary["outcome_columns_passed"] == []
    assert boundary["retrospective"] is True
    assert boundary["preregistered"] is False
    assert boundary["confirmatory"] is False
    assert boundary["prospective"] is False
    assert boundary["rhs_coverage_is_numerical_and_support_bounded"] is True
    assert boundary["strict_numerical_uniqueness_claim_active"] is False
    assert boundary["exact_symbolic_optimal_face_claim_active"] is False
    assert boundary["exact_nonuniqueness_claim_active"] is False
    assert boundary["global_optimal_face_diameter_claim_active"] is False
    assert boundary["continuous_joint_frontier_uniqueness_claim_active"] is False
    assert (
        boundary["exact_continuous_outcome_envelope_over_all_optimal_allocations_claim_active"]
        is False
    )
    assert boundary["epsilon_mobility_is_exact_nonuniqueness_evidence"] is False
    assert boundary["policy_cap_or_tie_break_selected"] is False
    assert boundary["empirical_outcome_direction_claim_active"] is False
    assert boundary["selected_or_funded_set_conformal_claim_active"] is False
