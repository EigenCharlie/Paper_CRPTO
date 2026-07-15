"""Transactional publication outputs and implementation provenance."""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.utils.artifact_descriptor import relative_artifact_descriptor, sha256_file

PUBLICATION_IMPLEMENTATION_PATHS: dict[str, str] = {
    "active_source_registry": "configs/ijds_active_evidence_sources.yaml",
    "claim_ledger_contract": "configs/ijds_claim_ledger.yaml",
    "publication_targets_contract": "configs/crpto_publication_targets.yaml",
    "evidence_builder": "scripts/build_ijds_binary_geometry_frontier_v4_evidence.py",
    "publication_integrity_checker": "scripts/check_publication_integrity.py",
    "publication_generation_helper": "src/ijds_audit/publication_generation.py",
    "v4_config_loader": "src/ijds_audit/config.py",
    "grid_contracts": "src/ijds_audit/grid_contracts.py",
    "endpoint_availability_sensitivity/loader": "src/ijds_audit/sensitivity_evidence.py",
    "claim_ledger_loader": "src/ijds_audit/claim_ledger.py",
    "source_registry_loader": "src/ijds_audit/publication_sources.py",
    "artifact_descriptor_helper": "src/utils/artifact_descriptor.py",
    "pipeline_runtime_helper": "src/utils/pipeline_runtime.py",
}


def publication_implementation_descriptors(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Hash the complete code and contract surface that accepts publication evidence."""
    return {
        name: relative_artifact_descriptor(repo_root / relative_path, repo_root=repo_root)
        for name, relative_path in PUBLICATION_IMPLEMENTATION_PATHS.items()
    }


def staged_output_path(
    transaction_root: Path,
    target: Path,
    *,
    repo_root: Path,
) -> Path:
    """Return a staging path that mirrors a repository-contained final target."""
    relative = target.resolve().relative_to(repo_root.resolve())
    staged = transaction_root.resolve() / "outputs" / relative
    staged.parent.mkdir(parents=True, exist_ok=True)
    return staged


def staged_artifact_descriptor(
    staged: Path,
    target: Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Describe staged bytes under their canonical post-promotion path."""
    if not staged.is_file():
        raise FileNotFoundError(f"Staged publication artifact is missing: {staged}")
    relative_target = target.resolve().relative_to(repo_root.resolve()).as_posix()
    return {
        "path": relative_target,
        "bytes": int(staged.stat().st_size),
        "sha256": sha256_file(staged),
    }


def _validate_promotion_inputs(
    artifacts: Mapping[Path, Path],
    *,
    staged_manifest: Path,
    manifest_target: Path,
    repo_root: Path,
    transaction_root: Path,
) -> list[tuple[Path, Path]]:
    if not artifacts:
        raise ValueError("A publication generation must contain artifacts.")
    root = repo_root.resolve()
    transaction = transaction_root.resolve()
    transaction.relative_to(root)
    manifest_target_resolved = manifest_target.resolve()
    manifest_target_resolved.relative_to(root)
    staged_manifest_resolved = staged_manifest.resolve()
    staged_manifest_resolved.relative_to(transaction)
    if not staged_manifest_resolved.is_file():
        raise FileNotFoundError(f"Staged publication manifest is missing: {staged_manifest}")

    normalized: list[tuple[Path, Path]] = []
    staged_paths: set[Path] = set()
    for target, staged in artifacts.items():
        target_resolved = target.resolve()
        staged_resolved = staged.resolve()
        target_resolved.relative_to(root)
        staged_resolved.relative_to(transaction)
        if target_resolved == manifest_target_resolved:
            raise ValueError("The publication manifest must be promoted separately and last.")
        if not staged_resolved.is_file():
            raise FileNotFoundError(f"Staged publication artifact is missing: {staged}")
        if staged_resolved in staged_paths:
            raise ValueError(f"A staged artifact is mapped more than once: {staged}")
        staged_paths.add(staged_resolved)
        normalized.append((target_resolved, staged_resolved))
    return sorted(normalized, key=lambda item: item[0].as_posix())


def promote_publication_generation(
    artifacts: Mapping[Path, Path],
    *,
    staged_manifest: Path,
    manifest_target: Path,
    repo_root: Path,
    transaction_root: Path,
) -> tuple[Path, ...]:
    """Promote one validated generation and roll back every target on failure.

    ``artifacts`` maps canonical targets to staged files. Existing targets are
    copied to a rollback area before any replacement. The manifest is always
    replaced after every other artifact, so it never advertises an incomplete
    generation.
    """
    ordered = _validate_promotion_inputs(
        artifacts,
        staged_manifest=staged_manifest,
        manifest_target=manifest_target,
        repo_root=repo_root,
        transaction_root=transaction_root,
    )
    manifest = manifest_target.resolve()
    staged_manifest_resolved = staged_manifest.resolve()
    targets = [target for target, _ in ordered] + [manifest]
    rollback_root = transaction_root.resolve() / "rollback"
    backups: dict[Path, Path | None] = {}

    for target in targets:
        if target.exists() and not target.is_file():
            raise IsADirectoryError(f"Publication target is not a file: {target}")
        if target.is_file():
            relative = target.relative_to(repo_root.resolve())
            backup_path = rollback_root / relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_path)
            backups[target] = backup_path
        else:
            backups[target] = None

    promoted: list[Path] = []
    try:
        for target, staged in ordered:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, target)
            promoted.append(target)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_manifest_resolved, manifest)
        promoted.append(manifest)
    except BaseException as error:
        rollback_failures: list[str] = []
        for target in reversed(promoted):
            rollback_backup = backups[target]
            try:
                if rollback_backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(rollback_backup, target)
            except OSError as rollback_error:
                rollback_failures.append(f"{target}: {rollback_error}")
        if rollback_failures:
            details = "; ".join(rollback_failures)
            raise RuntimeError(f"Publication rollback was incomplete: {details}") from error
        raise

    shutil.rmtree(rollback_root, ignore_errors=True)
    return tuple(promoted)
