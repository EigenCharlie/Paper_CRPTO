"""Contracts for transactional publication evidence generation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.ijds_audit import publication_generation
from src.ijds_audit.publication_generation import (
    PUBLICATION_IMPLEMENTATION_PATHS,
    promote_publication_generation,
    publication_implementation_descriptors,
    staged_artifact_descriptor,
    staged_output_path,
)

REPO = Path(__file__).resolve().parents[2]


def test_implementation_inventory_binds_every_acceptance_dependency() -> None:
    required = {
        "active_source_registry",
        "claim_ledger_contract",
        "publication_targets_contract",
        "evidence_builder",
        "publication_integrity_checker",
        "publication_generation_helper",
        "v4_config_loader",
        "grid_contracts",
        "endpoint_availability_sensitivity/loader",
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
