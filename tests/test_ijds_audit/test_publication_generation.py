"""Contracts for transactional publication evidence generation."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from scripts import extend_ijds_evidence_from_sealed_parent_2026_09_01 as sealed_extension
from scripts.build_ijds_binary_geometry_frontier_v4_evidence import (
    BINARY_PHASE_CENSUS_SOURCE_KEYS,
    CALIBRATOR_SOURCE_KEYS,
    CREDIT_LEARNER_ORDER,
    DECISION_REPRESENTATION_SOURCE_KEYS,
    FIGURE_STEMS,
    TABLE_TARGETS,
    _binary_phase_target_support_manifest_payload,
    _binary_phase_target_support_publication_table,
    _calibrator_sensitivity_manifest_payload,
    _common_panel_threshold_response_census_figure,
    _common_panel_threshold_response_figure,
    _joint_block_departure_table,
    _phase_transition_publication_table,
    _prepare_common_panel_figure_data,
    _require_coverage_aggregate_reconciliation,
    _require_coverage_contract,
)
from src.ijds_audit import publication_generation
from src.ijds_audit.calibrator_sensitivity_evidence import (
    calibrator_method_publication_table,
    calibrator_overall_publication_table,
    calibrator_pairwise_publication_table,
    load_calibrator_sensitivity_evidence,
)
from src.ijds_audit.publication_generation import (
    PUBLICATION_IMPLEMENTATION_PATHS,
    promote_publication_generation,
    publication_implementation_descriptors,
    require_historical_git_blob_descriptor,
    staged_artifact_descriptor,
    staged_output_path,
)
from src.ijds_audit.publication_sources import load_verified_or_sealed_source_registry

REPO = Path(__file__).resolve().parents[2]


def _synthetic_common_panel_census() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for learner_index, learner in enumerate(CREDIT_LEARNER_ORDER):
        for group in range(5):
            for pair_index in range(7):
                exact_zero = group == 0 and pair_index == 0
                positive = (learner_index + group + pair_index) % 2 == 0
                threshold_delta = (0.0001 if positive else -0.001) * (pair_index + 1)
                if exact_zero:
                    threshold_delta = 0.0
                    resolved_delta_rate = 0.0
                    delta_lower = 0.0
                    delta_upper = 0.0
                elif positive:
                    resolved_delta_rate = 0.001
                    delta_lower = 0.0008
                    delta_upper = 0.0012
                else:
                    resolved_delta_rate = -0.001
                    delta_lower = -0.0012
                    delta_upper = -0.0008
                rows.append(
                    {
                        "learner": learner,
                        "pair_index": pair_index,
                        "conformal_group": group,
                        "candidate_rows": 100,
                        "resolved_rows": 90,
                        "unresolved_rows": 10,
                        "threshold_delta": threshold_delta,
                        "resolved_delta_rate": resolved_delta_rate,
                        "delta_lower": delta_lower,
                        "delta_upper": delta_upper,
                        "delta_width": delta_upper - delta_lower,
                    }
                )
    return pd.DataFrame(rows)


def test_common_panel_figures_share_one_fail_closed_175_cell_contract(tmp_path: Path) -> None:
    census = _synthetic_common_panel_census()
    prepared = _prepare_common_panel_figure_data(census)

    assert prepared.threshold.shape == (25, 7)
    assert prepared.resolved_pp.shape == (25, 7)
    assert prepared.sharp_width_pp.shape == (25, 7)
    assert len(prepared.exact_zero_cells) == 5
    assert prepared.fixed_candidate_rows == 500
    assert prepared.fixed_resolved_rows == 450

    main = _common_panel_threshold_response_figure(census, output_dir=tmp_path)
    supplemental = _common_panel_threshold_response_census_figure(census, output_dir=tmp_path)
    assert set(main) == {"png", "pdf"}
    assert set(supplemental) == {"png", "pdf"}
    assert all(
        path.is_file() and path.stat().st_size > 0
        for path in (*main.values(), *supplemental.values())
    )
    assert main["png"].stem == FIGURE_STEMS["common_panel_threshold_response"]
    assert supplemental["png"].stem == FIGURE_STEMS["common_panel_threshold_response_census"]


def test_common_panel_figure_contract_rejects_inconsistent_sharp_width() -> None:
    census = _synthetic_common_panel_census()
    census.loc[10, "delta_width"] += 0.01

    with pytest.raises(RuntimeError, match="sharp-response bounds are inconsistent"):
        _prepare_common_panel_figure_data(census)


def test_phase_table_reports_the_exact_finite_sample_coordinate() -> None:
    phase = pd.DataFrame(
        {
            "window_id": ["high", "low"],
            "fit_rows": [20, 20],
            "fit_prevalence": [0.10, 0.05],
            "fit_score_min": [0.01, 0.01],
            "fit_score_max": [0.20, 0.20],
            "score_min": [0.01, 0.01],
            "score_max": [0.25, 0.25],
            "fit_residual_quantile": [0.80, 0.20],
            "coverage_lower": [0.80, 0.80],
            "coverage_upper": [0.90, 0.90],
            "mean_width": [0.90, 0.20],
            "set_empty_share": [0.0, 0.1],
            "set_zero_only_share": [0.9, 0.9],
            "set_both_share": [0.1, 0.0],
        }
    )

    table = _phase_transition_publication_table(phase, alpha=0.10).set_index("window_id")

    assert table.loc["high", "finite_sample_rank"] == 19
    assert table.loc["high", "finite_phase_allowance"] == 1
    assert table.loc["high", "fit_default_rows"] == 2
    assert table.loc["high", "phase_margin"] == 1
    assert table.loc["low", "phase_margin"] == 0
    assert table["phase_boundary_rate"].tolist() == pytest.approx([0.05, 0.05])
    assert table["calibration_scores_below_half"].all()

    inconsistent = phase.copy()
    inconsistent.loc[1, "fit_residual_quantile"] = 0.80
    with pytest.raises(RuntimeError, match="phase margin"):
        _phase_transition_publication_table(inconsistent, alpha=0.10)

    negative_score = phase.copy()
    negative_score.loc[0, "fit_score_min"] = -0.01
    with pytest.raises(RuntimeError, match=r"leave \[0, 1\]"):
        _phase_transition_publication_table(negative_score, alpha=0.10)

    invalid_prevalence = phase.copy()
    invalid_prevalence.loc[0, "fit_prevalence"] = 1.05
    with pytest.raises(RuntimeError, match="prevalence"):
        _phase_transition_publication_table(invalid_prevalence, alpha=0.10)


def test_phase_table_handles_alpha_boundary_when_n_plus_one_is_a_multiple_of_ten() -> None:
    phase = pd.DataFrame(
        {
            "window_id": ["boundary"],
            "fit_rows": [19],
            "fit_prevalence": [1 / 19],
            "fit_score_min": [0.01],
            "fit_score_max": [0.20],
            "score_min": [0.01],
            "score_max": [0.25],
            "fit_residual_quantile": [0.20],
            "coverage_lower": [0.80],
            "coverage_upper": [0.90],
            "mean_width": [0.20],
            "set_empty_share": [0.0],
            "set_zero_only_share": [1.0],
            "set_both_share": [0.0],
        }
    )

    table = _phase_transition_publication_table(phase, alpha=0.10).iloc[0]

    assert table["finite_sample_rank"] == 18
    assert table["finite_phase_allowance"] == 1
    assert table["fit_default_rows"] == 1
    assert table["phase_margin"] == 0


def test_complete_phase_target_support_join_is_fail_closed() -> None:
    phase = pd.read_csv(
        REPO / "reports/crpto/tables/crpto_ijds_v4_tableS6I_binary_phase_census.csv"
    )
    target = pd.read_csv(
        REPO / "reports/crpto/tables/crpto_ijds_v4_tableS6C_exchangeability_strata.csv"
    )

    table = _binary_phase_target_support_publication_table(phase, target)
    payload = _binary_phase_target_support_manifest_payload(table)

    assert len(table) == 200
    assert payload["threshold_below_half_cells"] == 87
    assert payload["target_support_cells"] == 87
    assert payload["positive_label_exclusion_cells"] == 87
    assert payload["all_low_threshold_cells_have_target_support"] is True
    assert payload["phase_margin_prevalence_boundary_reconciles_all_cells"] is True
    assert [
        row["positive_label_excluded_from_every_target_set"]
        for row in payload["ordered_stratum_census"]
    ] == [40, 40, 7, 0, 0]
    assert payload["finite_phase_boundary_rate_range"] == pytest.approx(
        [0.0990159901599016, 0.0999046711153482]
    )
    assert payload["exclusion_strata_resolved_miss_fraction_range"] == pytest.approx(
        [0.2397794701677335, 0.5845764027953737]
    )
    assert (
        payload["interpretation"][
            "nominal_coverage_impossibility_established_for_all_exclusion_cells"
        ]
        is False
    )
    assert payload["interpretation"]["stratum_specific_target_prevalence_identified"] is False

    drifted = target.copy()
    key = table.loc[table["threshold_below_half"].astype(bool)].iloc[0]
    mask = (
        drifted["learner"].eq(key["learner"])
        & drifted["window_id"].eq(key["window_id"])
        & drifted["conformal_group"].eq(key["conformal_group"])
    )
    drifted.loc[mask, "score_max"] = 1.0 - float(key["frozen_threshold"])
    with pytest.raises(RuntimeError, match="87-cell"):
        _binary_phase_target_support_publication_table(phase, drifted)


def test_joint_block_departure_pools_integer_numerators_before_division() -> None:
    cells = pd.read_csv(
        REPO / "reports/crpto/tables/crpto_ijds_v4_tableS6B_exchangeability_cells.csv"
    )
    strata = pd.read_csv(
        REPO / "reports/crpto/tables/crpto_ijds_v4_tableS6C_exchangeability_strata.csv"
    )

    table = _joint_block_departure_table(cells, strata)

    assert len(table) == 40
    assert int(table["meets_locked_nominal_holm_threshold"].sum()) == 31
    assert table["minimum_miss_rate_departure"].min() == pytest.approx(0.002379331272026275)
    assert table["minimum_miss_rate_departure"].max() == pytest.approx(0.030535024527601637)


def test_publication_inventory_is_derived_from_declared_targets() -> None:
    assert len(TABLE_TARGETS) == 46
    assert len(FIGURE_STEMS) == 5
    assert len(TABLE_TARGETS) + 2 * len(FIGURE_STEMS) == 56
    assert {
        "calibrator_fit_diagnostics",
        "calibrator_sensitivity_cells",
        "calibrator_pairwise_shared_completion",
    }.issubset(TABLE_TARGETS)
    assert len(CALIBRATOR_SOURCE_KEYS) == 21
    assert len(set(CALIBRATOR_SOURCE_KEYS)) == 21
    assert len(DECISION_REPRESENTATION_SOURCE_KEYS) == 39
    assert len(set(DECISION_REPRESENTATION_SOURCE_KEYS)) == 39
    assert len(BINARY_PHASE_CENSUS_SOURCE_KEYS) == 7
    assert len(set(BINARY_PHASE_CENSUS_SOURCE_KEYS)) == 7


def test_historical_v8_lock_is_verified_at_its_protocol_commit() -> None:
    summary_path = (
        REPO
        / "models/experiments/ijds_audit/ijds-common-panel-threshold-response-2026-07-26-v8"
        / "common_panel_threshold_response_v8_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    descriptor = summary["implementation_provenance"]["source_files"]["uv.lock"]
    protocol_commit = summary["protocol_commit"]

    assert hashlib.sha256((REPO / "uv.lock").read_bytes()).hexdigest() != descriptor["sha256"]
    require_historical_git_blob_descriptor(
        descriptor,
        commit=protocol_commit,
        relative_path="uv.lock",
        repo_root=REPO,
        label="test V8 uv.lock",
    )

    corrupted = {**descriptor, "sha256": "0" * 64}
    with pytest.raises(RuntimeError, match="pinned historical Git blob"):
        require_historical_git_blob_descriptor(
            corrupted,
            commit=protocol_commit,
            relative_path="uv.lock",
            repo_root=REPO,
            label="test corrupted V8 uv.lock",
        )
    for commit, relative_path in (
        ("HEAD", "uv.lock"),
        (protocol_commit, "../uv.lock"),
        (protocol_commit, ""),
    ):
        with pytest.raises(RuntimeError, match="invalid historical descriptor"):
            require_historical_git_blob_descriptor(
                descriptor,
                commit=commit,
                relative_path=relative_path,
                repo_root=REPO,
                label="test invalid V8 identity",
            )


def test_calibrator_manifest_is_derived_from_the_complete_overall_grid() -> None:
    registry, registered, missing = load_verified_or_sealed_source_registry(
        REPO / "configs/ijds_active_evidence_sources.yaml",
        repo_root=REPO,
        sealed_parent_commit=sealed_extension.PARENT_COMMIT,
        sealed_parent_registry_path=sealed_extension.PARENT_REGISTRY_PATH,
    )
    assert tuple(sorted(set(missing))) == missing
    if missing:
        # The pre-freeze additive path is deliberately usable without the
        # historical DVC cache.  In that environment, the exact parent seal is
        # the derivation authority; a strict rebuild still follows the branch
        # below after the publication capsule is materialized.
        _, parent = sealed_extension._load_pinned_parent()
        current = json.loads(
            (REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            current["sensitivity"]["calibrator_family"]
            == parent["sensitivity"]["calibrator_family"]
        )
        return
    identities = registry["sensitivities"]["calibrator_family"]
    evidence = load_calibrator_sensitivity_evidence(
        registered,
        identities,
        repo_root=REPO,
    )
    method_table = calibrator_method_publication_table(evidence)
    cell_table = calibrator_overall_publication_table(evidence)
    pairwise_table = calibrator_pairwise_publication_table(evidence)

    payload = _calibrator_sensitivity_manifest_payload(
        evidence,
        identities=identities,
        method_fit_table=method_table,
        cell_table=cell_table,
        pairwise_table=pairwise_table,
    )

    assert payload["result_state"] == "uniform_closed_family_shortfall_not_established"
    assert payload["overall_cells_with_coverage_upper_below_nominal"] == 18
    assert payload["overall_cells_with_coverage_upper_at_or_above_nominal"] == 14
    assert len(payload["method_fit_rows"]) == 4
    assert len(payload["cell_rows"]) == 192
    assert len(payload["pairwise_rows"]) == 288
    assert payload["interpretation"]["calibrator_winner"] is None
    assert payload["interpretation"]["portfolio_optimization_run"] is False
    assert payload["interpretation"]["pre_existing_platt_score_remains_primary_portfolio_score"]
    assert payload["interpretation"]["alternative_calibrator_maps_propagated_to_portfolio"] is False
    assert payload["interpretation"][
        "uniform_shortfall_not_established_is_not_true_coverage_dependence"
    ]
    assert payload["interpretation"]["temporal_transport_established"] is False
    assert payload["interpretation"]["prospective_transport_established"] is False
    json.dumps(payload, allow_nan=False)

    frames = dict(evidence.frames)
    mutated_overall = frames["overall"].copy()
    first_true = mutated_overall.index[
        mutated_overall["coverage_upper_below_nominal"].astype(bool)
    ][0]
    mutated_overall.loc[first_true, "coverage_upper_below_nominal"] = False
    frames["overall"] = mutated_overall
    mutated = replace(evidence, frames=frames)
    with pytest.raises(RuntimeError, match="result census changed"):
        _calibrator_sensitivity_manifest_payload(
            mutated,
            identities=identities,
            method_fit_table=method_table,
            cell_table=cell_table,
            pairwise_table=pairwise_table,
        )


def test_closed_coverage_contract_fails_on_invalid_bounds_or_denominators() -> None:
    valid = pd.DataFrame(
        {
            "learner": ["a", "a"],
            "candidate_rows": [10, 10],
            "resolved_rows": [8, 8],
            "unresolved_rows": [2, 2],
            "coverage_resolved": [0.75, 0.875],
            "coverage_lower": [0.6, 0.7],
            "coverage_upper": [0.8, 0.9],
        }
    )
    _require_coverage_contract(valid, label="test", constant_within=("learner",))

    broken_partition = valid.copy()
    broken_partition.loc[1, "unresolved_rows"] = 1
    with pytest.raises(RuntimeError, match="partition"):
        _require_coverage_contract(broken_partition, label="test", constant_within=("learner",))

    reversed_bound = valid.copy()
    reversed_bound.loc[0, "coverage_lower"] = 0.95
    with pytest.raises(RuntimeError, match="lower coverage bound"):
        _require_coverage_contract(reversed_bound, label="test", constant_within=("learner",))

    changing_denominator = valid.copy()
    changing_denominator.loc[1, ["candidate_rows", "resolved_rows"]] = [11, 9]
    changing_denominator.loc[1, "coverage_resolved"] = 8 / 9
    changing_denominator.loc[1, "coverage_lower"] = 8 / 11
    changing_denominator.loc[1, "coverage_upper"] = 10 / 11
    with pytest.raises(RuntimeError, match="changes its candidate denominators"):
        _require_coverage_contract(changing_denominator, label="test", constant_within=("learner",))

    nonintegral_hits = valid.copy()
    nonintegral_hits.loc[0, "coverage_resolved"] = 0.85
    with pytest.raises(RuntimeError, match="integer resolved-hit"):
        _require_coverage_contract(nonintegral_hits, label="test", constant_within=("learner",))

    inconsistent_sharp_bound = valid.copy()
    inconsistent_sharp_bound.loc[0, "coverage_lower"] = 0.61
    with pytest.raises(RuntimeError, match="integer coverage_lower numerators"):
        _require_coverage_contract(
            inconsistent_sharp_bound, label="test", constant_within=("learner",)
        )

    with pytest.raises(RuntimeError, match="locked global candidate census"):
        _require_coverage_contract(
            valid,
            label="test",
            constant_within=("learner",),
            expected_counts=(11, 9, 2),
        )


def test_closed_coverage_aggregate_reconciles_exact_frozen_strata() -> None:
    frame = pd.DataFrame(
        {
            "learner": ["a", "a", "a"],
            "taxonomy_groups": [2, 2, 2],
            "role": ["primary_oot", "primary_oot", "primary_oot"],
            "window_id": ["w01", "w01", "w01"],
            "conformal_group": [-1, 0, 1],
            "candidate_rows": [10, 4, 6],
            "resolved_rows": [8, 3, 5],
            "unresolved_rows": [2, 1, 1],
            "coverage_resolved": [0.75, 2 / 3, 0.8],
            "coverage_lower": [0.6, 0.5, 4 / 6],
            "coverage_upper": [0.8, 0.75, 5 / 6],
        }
    )
    _require_coverage_aggregate_reconciliation(
        frame,
        label="test aggregate",
        expected_counts=(10, 8, 2),
    )

    broken = frame.copy()
    broken.loc[2, "coverage_resolved"] = 0.6
    broken.loc[2, "coverage_lower"] = 0.5
    broken.loc[2, "coverage_upper"] = 4 / 6
    with pytest.raises(RuntimeError, match="coverage hits do not reconcile"):
        _require_coverage_aggregate_reconciliation(
            broken,
            label="test aggregate",
            expected_counts=(10, 8, 2),
        )

    broken_sharp_lower = frame.copy()
    broken_sharp_lower.loc[2, "coverage_lower"] = 5 / 6
    with pytest.raises(RuntimeError, match="coverage hits do not reconcile"):
        _require_coverage_aggregate_reconciliation(
            broken_sharp_lower,
            label="test aggregate",
            expected_counts=(10, 8, 2),
        )


def test_implementation_inventory_binds_every_acceptance_dependency() -> None:
    required = {
        "active_source_registry",
        "claim_ledger_contract",
        "publication_targets_contract",
        "evidence_builder",
        "sealed_parent_extension_builder",
        "sealed_parent_target_support_extension_builder",
        "policy_support_evidence_builder",
        "publication_integrity_checker",
        "paper_pdf_auditor",
        "publication_generation_helper",
        "publication_table_schemas",
        "v4_config_loader",
        "grid_contracts",
        "calibrator_sensitivity/loader",
        "decision_representation/loader",
        "binary_phase_census/loader",
        "endpoint_availability_sensitivity/loader",
        "portfolio_structure_sensitivity/loader",
        "robustness_sensitivities/loader",
        "scientific_frontiers/loader",
        "claim_ledger_loader",
        "source_registry_loader",
        "artifact_descriptor_helper",
        "pipeline_runtime_helper",
    }
    assert set(PUBLICATION_IMPLEMENTATION_PATHS) == required
    descriptors = publication_implementation_descriptors(REPO)
    assert set(descriptors) == required
    for descriptor in descriptors.values():
        assert (REPO / descriptor["path"]).is_file()
        assert descriptor["bytes"] > 0
        assert len(descriptor["sha256"]) == 64


def test_staged_descriptor_uses_canonical_target_path(tmp_path: Path) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    target = repo / "reports/tables/table.csv"
    staged = staged_output_path(transaction, target, repo_root=repo)
    staged.write_text("value\n1\n", encoding="utf-8")

    descriptor = staged_artifact_descriptor(staged, target, repo_root=repo)

    assert descriptor["path"] == "reports/tables/table.csv"
    assert descriptor["bytes"] == staged.stat().st_size
    assert len(descriptor["sha256"]) == 64


def test_promotion_replaces_manifest_after_every_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    targets = [repo / "reports/b.csv", repo / "reports/a.csv"]
    artifacts: dict[Path, Path] = {}
    for index, target in enumerate(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"old-{index}", encoding="utf-8")
        staged = staged_output_path(transaction, target, repo_root=repo)
        staged.write_text(f"new-{index}", encoding="utf-8")
        artifacts[target] = staged
    manifest = repo / "reports/evidence.json"
    manifest.write_text("old-manifest", encoding="utf-8")
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_replace = os.replace
    calls: list[tuple[Path, Path]] = []

    def recording_replace(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        calls.append((Path(source).resolve(), Path(destination).resolve()))
        real_replace(source, destination)

    monkeypatch.setattr(publication_generation.os, "replace", recording_replace)
    promoted = promote_publication_generation(
        artifacts,
        staged_manifest=staged_manifest,
        manifest_target=manifest,
        repo_root=repo,
        transaction_root=transaction,
    )

    assert promoted[-1] == manifest.resolve()
    assert calls[-1][1] == manifest.resolve()
    assert [target for _, target in calls[:-1]] == sorted(
        (target.resolve() for target in targets),
        key=Path.as_posix,
    )
    assert manifest.read_text(encoding="utf-8") == "new-manifest"
    assert {target.read_text(encoding="utf-8") for target in targets} == {"new-0", "new-1"}


def test_failed_manifest_promotion_restores_previous_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    targets = [repo / "reports/a.csv", repo / "reports/b.csv"]
    artifacts: dict[Path, Path] = {}
    for index, target in enumerate(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"old-{index}", encoding="utf-8")
        staged = staged_output_path(transaction, target, repo_root=repo)
        staged.write_text(f"new-{index}", encoding="utf-8")
        artifacts[target] = staged
    manifest = repo / "reports/evidence.json"
    manifest.write_text("old-manifest", encoding="utf-8")
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_replace = os.replace
    injected = False

    def fail_once_on_manifest(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        nonlocal injected
        if Path(source).resolve() == staged_manifest.resolve() and not injected:
            injected = True
            raise OSError("injected manifest promotion failure")
        real_replace(source, destination)

    monkeypatch.setattr(publication_generation.os, "replace", fail_once_on_manifest)
    with pytest.raises(OSError, match="injected manifest promotion failure"):
        promote_publication_generation(
            artifacts,
            staged_manifest=staged_manifest,
            manifest_target=manifest,
            repo_root=repo,
            transaction_root=transaction,
        )

    assert manifest.read_text(encoding="utf-8") == "old-manifest"
    assert [target.read_text(encoding="utf-8") for target in targets] == ["old-0", "old-1"]


def test_promotion_retries_a_transient_windows_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    target = repo / "reports/table.csv"
    staged = staged_output_path(transaction, target, repo_root=repo)
    staged.write_text("new-table", encoding="utf-8")
    manifest = repo / "reports/evidence.json"
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_replace = os.replace
    manifest_attempts = 0
    delays: list[float] = []

    def fail_first_manifest_replace(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        nonlocal manifest_attempts
        if Path(destination).resolve() == manifest.resolve():
            manifest_attempts += 1
            if manifest_attempts == 1:
                raise PermissionError("injected transient Windows lock")
        real_replace(source, destination)

    monkeypatch.setattr(publication_generation.os, "replace", fail_first_manifest_replace)
    monkeypatch.setattr(publication_generation.time, "sleep", delays.append)

    promote_publication_generation(
        {target: staged},
        staged_manifest=staged_manifest,
        manifest_target=manifest,
        repo_root=repo,
        transaction_root=transaction,
    )

    assert manifest_attempts == 2
    assert delays == [0.05]
    assert target.read_text(encoding="utf-8") == "new-table"
    assert manifest.read_text(encoding="utf-8") == "new-manifest"


def test_copy_promotion_preserves_stage_and_promotes_manifest_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    target = repo / "reports/table.csv"
    target.parent.mkdir(parents=True)
    target.write_text("old-table", encoding="utf-8")
    staged = staged_output_path(transaction, target, repo_root=repo)
    staged.write_text("new-table", encoding="utf-8")
    manifest = repo / "reports/evidence.json"
    manifest.write_text("old-manifest", encoding="utf-8")
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_copy = publication_generation._copy_bytes_with_retry
    calls: list[Path] = []

    def recording_copy(source: Path, destination: Path) -> None:
        calls.append(destination.resolve())
        real_copy(source, destination)

    monkeypatch.setattr(publication_generation, "_copy_bytes_with_retry", recording_copy)
    promoted = promote_publication_generation(
        {target: staged},
        staged_manifest=staged_manifest,
        manifest_target=manifest,
        repo_root=repo,
        transaction_root=transaction,
        preserve_target_permissions=True,
    )

    assert calls == [target.resolve(), manifest.resolve()]
    assert promoted == (target.resolve(), manifest.resolve())
    assert target.read_text(encoding="utf-8") == "new-table"
    assert manifest.read_text(encoding="utf-8") == "new-manifest"
    assert staged.read_text(encoding="utf-8") == "new-table"
    assert staged_manifest.read_text(encoding="utf-8") == "new-manifest"


def test_failed_copy_promotion_rolls_back_existing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    target = repo / "reports/table.csv"
    target.parent.mkdir(parents=True)
    target.write_text("old-table", encoding="utf-8")
    staged = staged_output_path(transaction, target, repo_root=repo)
    staged.write_text("new-table", encoding="utf-8")
    manifest = repo / "reports/evidence.json"
    manifest.write_text("old-manifest", encoding="utf-8")
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_copy = publication_generation._copy_bytes_with_retry
    injected = False

    def fail_manifest_once(source: Path, destination: Path) -> None:
        nonlocal injected
        if destination.resolve() == manifest.resolve() and not injected:
            injected = True
            destination.write_text("partial-manifest", encoding="utf-8")
            raise OSError("injected copy promotion failure")
        real_copy(source, destination)

    monkeypatch.setattr(publication_generation, "_copy_bytes_with_retry", fail_manifest_once)
    with pytest.raises(OSError, match="injected copy promotion failure"):
        promote_publication_generation(
            {target: staged},
            staged_manifest=staged_manifest,
            manifest_target=manifest,
            repo_root=repo,
            transaction_root=transaction,
            preserve_target_permissions=True,
        )

    assert target.read_text(encoding="utf-8") == "old-table"
    assert manifest.read_text(encoding="utf-8") == "old-manifest"


def test_mid_copy_failure_rolls_back_the_current_partially_written_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path
    transaction = repo / ".transaction"
    target = repo / "reports/table.csv"
    target.parent.mkdir(parents=True)
    target.write_text("old-table", encoding="utf-8")
    staged = staged_output_path(transaction, target, repo_root=repo)
    staged.write_text("new-table", encoding="utf-8")
    manifest = repo / "reports/evidence.json"
    manifest.write_text("old-manifest", encoding="utf-8")
    staged_manifest = staged_output_path(transaction, manifest, repo_root=repo)
    staged_manifest.write_text("new-manifest", encoding="utf-8")

    real_copy = publication_generation._copy_bytes_with_retry
    injected = False

    def corrupt_current_target_then_fail(source: Path, destination: Path) -> None:
        nonlocal injected
        if destination.resolve() == target.resolve() and not injected:
            injected = True
            destination.write_text("partial", encoding="utf-8")
            raise OSError("injected mid-copy failure")
        real_copy(source, destination)

    monkeypatch.setattr(
        publication_generation,
        "_copy_bytes_with_retry",
        corrupt_current_target_then_fail,
    )
    with pytest.raises(OSError, match="injected mid-copy failure"):
        promote_publication_generation(
            {target: staged},
            staged_manifest=staged_manifest,
            manifest_target=manifest,
            repo_root=repo,
            transaction_root=transaction,
            preserve_target_permissions=True,
        )

    assert target.read_text(encoding="utf-8") == "old-table"
    assert manifest.read_text(encoding="utf-8") == "old-manifest"
