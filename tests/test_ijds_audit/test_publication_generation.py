"""Contracts for transactional publication evidence generation."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_ijds_binary_geometry_frontier_v4_evidence import (
    _require_coverage_aggregate_reconciliation,
    _require_coverage_contract,
)
from src.ijds_audit import publication_generation
from src.ijds_audit.publication_generation import (
    PUBLICATION_IMPLEMENTATION_PATHS,
    promote_publication_generation,
    publication_implementation_descriptors,
    staged_artifact_descriptor,
    staged_output_path,
)

REPO = Path(__file__).resolve().parents[2]


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
        "policy_support_evidence_builder",
        "publication_integrity_checker",
        "paper_pdf_auditor",
        "publication_generation_helper",
        "v4_config_loader",
        "grid_contracts",
        "endpoint_availability_sensitivity/loader",
        "portfolio_structure_sensitivity/loader",
        "robustness_sensitivities/loader",
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
