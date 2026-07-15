"""Exact scientific-output reconciliation for reason-only endpoint recoveries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.isolated_experiment import relative_artifact_descriptor


def verified_json_artifact(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Load a JSON artifact only after its path, size, and hash reconcile."""
    path = (repo_root / str(descriptor["path"])).resolve()
    path.relative_to(repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Endpoint recovery reference mismatch for {field}: {path}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Endpoint recovery reference must be a JSON object: {path}.")
    return payload


def reconcile_reference_frames(
    current: Mapping[str, pd.DataFrame],
    reference_descriptors: Mapping[str, Mapping[str, Any]],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Require exact equality on every reference column in named Parquet frames.

    A corrected lineage may append diagnostic columns, such as identification
    widths, but every column that carried the prior scientific result must be
    byte-value equivalent after Parquet loading.
    """
    if set(current) != set(reference_descriptors):
        raise RuntimeError(
            "Endpoint recovery frame inventory changed: "
            f"current={sorted(current)}, reference={sorted(reference_descriptors)}."
        )
    audits: dict[str, Any] = {}
    for name, frame in current.items():
        descriptor = reference_descriptors[name]
        path = (repo_root / str(descriptor["path"])).resolve()
        path.relative_to(repo_root)
        actual = relative_artifact_descriptor(path, repo_root=repo_root)
        for field in ("path", "bytes", "sha256"):
            if actual[field] != descriptor[field]:
                raise RuntimeError(f"Endpoint recovery artifact mismatch for {name}/{field}.")
        reference = pd.read_parquet(path)
        missing_columns = sorted(set(reference.columns).difference(frame.columns))
        if missing_columns:
            raise RuntimeError(
                f"Endpoint recovery dropped reference columns from {name}: {missing_columns}."
            )
        pd.testing.assert_frame_equal(
            frame.loc[:, reference.columns],
            reference,
            check_dtype=True,
            check_exact=True,
            check_like=False,
        )
        audits[name] = {
            "rows": int(len(reference)),
            "reference_columns": int(len(reference.columns)),
            "appended_columns": sorted(set(frame.columns).difference(reference.columns)),
            "reference": actual,
        }
    return {
        "status": "exact_reference_column_equivalence_verified",
        "frames": audits,
    }


def reconcile_from_json_reference(
    current: Mapping[str, pd.DataFrame],
    *,
    reference_json: Mapping[str, Any],
    artifact_section: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Verify one reference JSON and reconcile selected named frame artifacts."""
    payload = verified_json_artifact(reference_json, repo_root=repo_root)
    descriptors = payload.get(artifact_section)
    if not isinstance(descriptors, Mapping):
        raise KeyError(f"Reference JSON is missing artifact section {artifact_section!r}.")
    selected: dict[str, Mapping[str, Any]] = {}
    for name in current:
        descriptor = descriptors.get(name)
        if not isinstance(descriptor, Mapping):
            raise KeyError(f"Reference artifact section is missing {name!r}.")
        selected[name] = descriptor
    result = reconcile_reference_frames(current, selected, repo_root=repo_root)
    result["reference_json"] = dict(reference_json)
    result["artifact_section"] = str(artifact_section)
    return result
