"""Load and verify the single active paper-evidence source registry."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from src.utils.isolated_experiment import relative_artifact_descriptor


def load_verified_source_registry(
    path: Path,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Return registry metadata and hash-verified source paths."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Active evidence source registry must be a mapping.")
    if payload.get("status") != "active_ijds_paper_evidence_source_registry":
        raise ValueError("Unexpected active evidence source registry status.")
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
