"""Scientific-output reconciliation for reason-only endpoint recoveries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype

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
    float_atol: float = 0.0,
    float_rtol: float = 0.0,
) -> dict[str, Any]:
    """Reconcile every reference column in named Parquet frames.

    A corrected lineage may append diagnostic columns, such as identification
    widths. Non-floating columns remain exact. Floating columns may use a
    protocol-declared machine-precision tolerance; the observed maximum drift
    is persisted for audit.
    """
    for name, value in (("float_atol", float_atol), ("float_rtol", float_rtol)):
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and non-negative.")
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
        reference_columns = frame.loc[:, reference.columns]
        exact = float_atol == 0.0 and float_rtol == 0.0
        pd.testing.assert_frame_equal(
            reference_columns,
            reference,
            check_dtype=True,
            check_exact=exact,
            check_like=False,
            atol=float_atol,
            rtol=float_rtol,
        )
        float_drift: dict[str, dict[str, float]] = {}
        for column in reference.columns:
            if not is_float_dtype(reference[column].dtype):
                continue
            current_values = reference_columns[column].to_numpy(dtype=float)
            reference_values = reference[column].to_numpy(dtype=float)
            finite = np.isfinite(current_values) & np.isfinite(reference_values)
            absolute = np.abs(current_values[finite] - reference_values[finite])
            scale = np.maximum(np.abs(reference_values[finite]), np.finfo(float).tiny)
            relative = absolute / scale
            float_drift[str(column)] = {
                "maximum_absolute": float(absolute.max(initial=0.0)),
                "maximum_relative": float(relative.max(initial=0.0)),
            }
        audits[name] = {
            "rows": int(len(reference)),
            "reference_columns": int(len(reference.columns)),
            "appended_columns": sorted(set(frame.columns).difference(reference.columns)),
            "float_drift": float_drift,
            "reference": actual,
        }
    return {
        "status": (
            "exact_reference_column_equivalence_verified"
            if float_atol == 0.0 and float_rtol == 0.0
            else "reference_column_equivalence_verified_with_float_tolerance"
        ),
        "equivalence": {
            "non_float_columns_exact": True,
            "float_atol": float(float_atol),
            "float_rtol": float(float_rtol),
        },
        "frames": audits,
    }


def reconcile_from_json_reference(
    current: Mapping[str, pd.DataFrame],
    *,
    reference_json: Mapping[str, Any],
    artifact_section: str,
    repo_root: Path,
    float_atol: float = 0.0,
    float_rtol: float = 0.0,
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
    result = reconcile_reference_frames(
        current,
        selected,
        repo_root=repo_root,
        float_atol=float_atol,
        float_rtol=float_rtol,
    )
    result["reference_json"] = dict(reference_json)
    result["artifact_section"] = str(artifact_section)
    return result
