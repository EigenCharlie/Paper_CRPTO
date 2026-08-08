"""Contracts for the active Git-transported scientific frontiers."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

import src.ijds_audit.frontier_evidence as frontier_module
from src.ijds_audit.frontier_evidence import load_frontier_evidence
from src.ijds_audit.publication_sources import load_verified_source_registry

pytestmark = pytest.mark.requires_dvc_materialized

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "configs/ijds_active_evidence_sources.yaml"


def _evidence():
    registry, sources = load_verified_source_registry(REGISTRY, repo_root=REPO)
    evidence = load_frontier_evidence(
        sources,
        registry["lineages"]["diagnostics"],
        repo_root=REPO,
    )
    return registry, evidence


def test_frontier_registry_keeps_dvc_surface_fixed_and_uses_git_artifacts() -> None:
    registry, _ = _evidence()

    assert len(registry["dvc_pointers"]) == 53
    diagnostics = registry["lineages"]["diagnostics"]
    for name in (
        "residual_transport_frontier",
        "marginal_score_outcome_gap",
        "decision_catalog_transport",
        "funded_selection_estimands",
    ):
        identity = diagnostics[name]
        assert identity["dvc_tracked"] is False
        assert identity["artifact_transport"] == "git_force_tracked_direct_child_commit"
        assert identity["artifact_parent_commit"] == identity["protocol_commit"]
    embedding = diagnostics["set_preserving_embedding"]
    assert embedding["dvc_tracked"] is False
    assert embedding["source_artifact_parent_commit"] == embedding["protocol_commit"]
    assert embedding["artifact_parent_commit"] == embedding["source_artifact_commit"]
    assert len(embedding["source_artifact_paths"]) == 11
    assert len(embedding["artifact_paths"]) == 9


def test_residual_and_marginal_frontiers_are_complete_and_narrow() -> None:
    _, evidence = _evidence()
    residual = evidence.residual_transport
    marginal = evidence.marginal_score_outcome_gap

    assert len(residual.frames["monthly"]) == 3000
    assert len(residual.frames["pooled"]) == 200
    assert residual.findings["pooled_direction_census"] == {
        "larger_target_residual_discrepancy_dominates": 158,
        "smaller_target_residual_discrepancy_dominates": 8,
        "directional_discrepancies_not_robustly_ordered": 34,
    }
    assert len(residual.publication_tables["summary"]) == 5
    assert len(residual.publication_tables["pooled"]) == 200
    assert residual.findings["cellwise_sharp_not_joint_stochastic_order"] is True
    assert residual.findings["p_values_computed"] is False

    assert len(marginal.frames["table"]) == 5
    assert len(marginal.publication_tables["gap"]) == 5
    assert marginal.findings["all_five_gap_upper_endpoints_negative"] is True
    assert marginal.findings["least_negative_gap_upper_endpoint"] < 0.0
    assert marginal.findings["individual_or_conditional_calibration_claimed"] is False


def test_decision_and_funded_frontiers_preserve_interpretive_boundaries() -> None:
    _, evidence = _evidence()
    decision = evidence.decision_catalog_transport
    funded = evidence.funded_selection_estimands

    assert len(decision.frames["policy_score_bounds"]) == 18720
    assert len(decision.publication_tables["metric_separation"]) == 3
    assert len(decision.publication_tables["target_blocks"]) == 45
    assert (
        decision.findings["all_three_metrics_all_fifteen_target_lower_exceed_all_development_upper"]
        is True
    )
    assert decision.findings["object_is_worst_catalog_maximum_not_every_policy"] is True
    assert decision.findings["ordering_probability_reported"] is False

    assert len(funded.frames["monthly_bounds"]) == 1440
    assert len(funded.publication_tables["track_estimands"]) == 96
    assert len(funded.publication_tables["gamma_contrasts"]) == 48
    assert (
        funded.findings[
            "all_ninety_six_count_minus_invested_dollar_coverage_lower_endpoints_positive"
        ]
        is True
    )
    assert funded.findings["count_selected_upper_below_point90_tracks"] == 80
    assert funded.findings["count_selected_lower_below_point90_tracks"] == 96
    assert funded.findings["selected_set_or_fcr_validity_claimed"] is False


def test_set_preserving_embedding_is_complete_without_selecting_an_embedding() -> None:
    _, evidence = _evidence()
    embedding = evidence.set_preserving_embedding

    assert embedding.findings["set_preservation_and_allocation_change_verified"] is True
    assert embedding.findings["theta_direction_noninvariance_verified"] is True
    assert embedding.findings["set_diagnostic_rows"] == 80
    assert embedding.findings["sets_changed"] == 0
    assert embedding.findings["allocation_changes_gt_1e10"] == 9659
    assert embedding.findings["noncontrol_theta_allocation_contrasts"] == 11520
    assert embedding.findings["phase_a_gamma_zero_control_cells"] == 2880
    assert embedding.findings["pooled_gamma_zero_control_cells"] == 192
    assert embedding.findings["selected_theta_gamma_ruler_coordinate_window_or_policy"] is False
    allocation = embedding.publication_tables["allocation_summary"]
    assert allocation["ruler"].tolist() == [
        "all_rulers",
        "objective_matched",
        "normalized_score",
    ]
    assert allocation["noncontrol_theta_contrasts"].tolist() == [11520, 5760, 5760]
    assert allocation["allocation_changes_gt_1e10"].tolist() == [9659, 3899, 5760]
    assert allocation["maximum_normalized_exposure_distance"].tolist() == pytest.approx(
        [0.684049776890922, 0.5758632511294073, 0.684049776890922], abs=1e-15
    )
    assert not allocation.isna().any().any()
    directions = embedding.publication_tables["direction_census"]
    assert len(directions) == 6
    assert list(directions[["contrast_family", "metric"]].itertuples(index=False, name=None)) == [
        ("theta_minus_theta_0_within_gamma", "standardized_payoff"),
        ("theta_minus_theta_0_within_gamma", "funded_default"),
        ("theta_minus_theta_0_within_gamma", "funded_binary_miscoverage"),
        ("gamma_1_minus_gamma_0_within_theta", "standardized_payoff"),
        ("gamma_1_minus_gamma_0_within_theta", "funded_default"),
        ("gamma_1_minus_gamma_0_within_theta", "funded_binary_miscoverage"),
    ]


@pytest.mark.parametrize(
    "payload_name", ["evaluation_summary.json", "verified_evaluation_manifest.json"]
)
def test_embedding_loader_rejects_false_replay_or_confirmation_flags(
    monkeypatch: pytest.MonkeyPatch,
    payload_name: str,
) -> None:
    registry, sources = load_verified_source_registry(REGISTRY, repo_root=REPO)
    original = frontier_module._load_json_object

    def mutated(path: Path, *, label: str):
        payload = copy.deepcopy(original(path, label=label))
        if path.name == payload_name and "set-preserving-embedding" in path.as_posix():
            payload["confirmatory"] = True
            payload["replay_clean"] = True
        return payload

    monkeypatch.setattr(frontier_module, "_load_json_object", mutated)
    with pytest.raises(RuntimeError, match="selection or interpretation boundary changed"):
        load_frontier_evidence(
            sources,
            registry["lineages"]["diagnostics"],
            repo_root=REPO,
        )


def test_embedding_loader_rejects_nonzero_monthly_gamma_zero_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, sources = load_verified_source_registry(REGISTRY, repo_root=REPO)
    original = frontier_module.pd.read_parquet

    def mutated(path: Path, *args, **kwargs):
        frame = original(path, *args, **kwargs)
        if Path(path).name == "monthly_sharp_contrasts.parquet":
            frame = frame.copy()
            mask = frame["contrast_family"].eq("theta_minus_theta_0_within_gamma") & frame[
                "gamma"
            ].eq(0.0)
            frame.loc[frame.index[mask][0], "weighted_default_difference_lower"] = 1e-6
        return frame

    monkeypatch.setattr(frontier_module.pd, "read_parquet", mutated)
    with pytest.raises(RuntimeError, match="monthly or pooled gamma-zero negative control changed"):
        load_frontier_evidence(
            sources,
            registry["lineages"]["diagnostics"],
            repo_root=REPO,
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("status", "summary is not complete"),
        ("summary", "receipt no longer binds its summary"),
        ("artifacts", "summary and receipt bind different artifacts"),
        ("implementation_hash", "implementation dependency drifted"),
    ],
)
def test_frontier_loader_fails_closed_on_mutated_run_contract(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    match: str,
) -> None:
    registry, sources = load_verified_source_registry(REGISTRY, repo_root=REPO)
    original = frontier_module._load_json_object

    def mutated(path: Path, *, label: str):
        payload = copy.deepcopy(original(path, label=label))
        if path.name == "residual_transport_frontier_summary.json":
            if mutation == "status":
                payload["status"] = "incomplete"
            elif mutation == "implementation_hash":
                relative = "src/ijds_audit/residual_transport_frontier.py"
                payload["implementation_provenance"]["source_files"][relative]["sha256"] = "0" * 64
        if path.name == "execution_receipt.json" and "residual-transport" in path.as_posix():
            if mutation == "summary":
                payload["summary"]["sha256"] = "0" * 64
            elif mutation == "artifacts":
                payload["artifacts"].pop("pooled_residual_transport_frontier")
        return payload

    monkeypatch.setattr(frontier_module, "_load_json_object", mutated)
    with pytest.raises(RuntimeError, match=match):
        load_frontier_evidence(
            sources,
            registry["lineages"]["diagnostics"],
            repo_root=REPO,
        )


@pytest.mark.parametrize("field", ["path", "sha256"])
def test_frontier_registry_rejects_mutated_source_route_or_hash(
    tmp_path: Path,
    field: str,
) -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    if field == "path":
        text = text.replace(
            'path: "configs/experiments/ijds_residual_transport_frontier_2026-07-29_v1.yaml"',
            'path: "configs/experiments/ijds_decision_catalog_transport_2026-07-29_v1.yaml"',
            1,
        )
    else:
        text = text.replace(
            'sha256: "425dac935bd59a36886540a504c6a54ae7677e3a2c6f27c049a572c75f7762e0"',
            f'sha256: "{"0" * 64}"',
            1,
        )
    mutated_registry = tmp_path / "registry.yaml"
    mutated_registry.write_text(text, encoding="utf-8")

    with pytest.raises((RuntimeError, ValueError)):
        load_verified_source_registry(mutated_registry, repo_root=REPO)
