"""Load and verify the single active paper-evidence source registry."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from src.utils.artifact_descriptor import relative_artifact_descriptor

LINEAGE_PHASES = (
    ("binary_geometry", "outcome_free"),
    ("binary_geometry", "evaluation"),
    ("two_ruler", "outcome_free"),
    ("two_ruler", "evaluation"),
    ("credit_controls", "outcome_free"),
    ("credit_controls", "evaluation"),
)


def load_source_registry(path: Path) -> dict[str, Any]:
    """Load and structurally validate the active source registry."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Active evidence source registry must be a mapping.")
    if payload.get("status") != "active_ijds_paper_evidence_source_registry":
        raise ValueError("Unexpected active evidence source registry status.")
    lineages = payload.get("lineages")
    if not isinstance(lineages, Mapping):
        raise TypeError("Active evidence source registry omits lineages.")
    run_tags = active_lineage_run_tags(payload)
    if len(set(run_tags)) != len(run_tags):
        raise ValueError("Active evidence lineage run tags must be unique.")
    pointers = payload.get("dvc_pointers")
    if not isinstance(pointers, list) or not all(isinstance(item, str) for item in pointers):
        raise TypeError("Active evidence source registry dvc_pointers must be a string list.")
    expected = {
        f"{prefix}/experiments/ijds_audit/{tag}.dvc"
        for tag in run_tags
        for prefix in ("data/processed", "models")
    }
    if set(pointers) != expected or len(pointers) != len(expected):
        raise ValueError("Active DVC pointers do not match the six registered run tags.")
    return payload


def active_lineage_run_tags(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the six outcome-free/evaluation run tags in causal order."""
    lineages = payload.get("lineages")
    if not isinstance(lineages, Mapping):
        raise TypeError("Active evidence source registry omits lineages.")
    tags: list[str] = []
    for family, phase in LINEAGE_PHASES:
        family_payload = lineages.get(family)
        if not isinstance(family_payload, Mapping):
            raise TypeError(f"Missing lineage family: {family}")
        identity = family_payload.get(phase)
        if not isinstance(identity, Mapping):
            raise TypeError(f"Missing lineage phase: {family}.{phase}")
        for field in ("run_tag", "protocol_tag", "protocol_commit"):
            if not isinstance(identity.get(field), str) or not identity[field]:
                raise TypeError(f"Missing lineage identity: {family}.{phase}.{field}")
        tags.append(str(identity["run_tag"]))
    return tuple(tags)


def load_verified_source_registry(
    path: Path,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Return registry metadata and hash-verified source paths."""
    payload = load_source_registry(path)
    sources = payload.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise ValueError("Active evidence source registry is empty.")
    verified: dict[str, Path] = {}
    seen_paths: set[str] = set()
    for name, raw_descriptor in sources.items():
        if not isinstance(raw_descriptor, Mapping):
            raise TypeError(f"Evidence source descriptor {name!r} must be a mapping.")
        descriptor = dict(raw_descriptor)
        source_path = (repo_root / str(descriptor["path"])).resolve()
        source_path.relative_to(repo_root.resolve())
        actual = relative_artifact_descriptor(source_path, repo_root=repo_root)
        for field in ("path", "bytes", "sha256"):
            if actual[field] != descriptor.get(field):
                raise RuntimeError(f"Evidence source {name!r} mismatched on {field}.")
        if actual["path"] in seen_paths:
            raise ValueError(f"Duplicate active evidence source path: {actual['path']}")
        seen_paths.add(str(actual["path"]))
        verified[str(name)] = source_path
    return payload, verified
