from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.ijds_audit.endpoint_recovery import reconcile_from_json_reference
from src.utils.isolated_experiment import relative_artifact_descriptor


def _reference(tmp_path: Path) -> tuple[dict[str, object], pd.DataFrame]:
    reference = pd.DataFrame({"id": ["a", "b"], "metric": [1.0, 2.0]})
    parquet = tmp_path / "reference.parquet"
    reference.to_parquet(parquet, index=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"artifacts": {"result": relative_artifact_descriptor(parquet, repo_root=tmp_path)}}
        ),
        encoding="utf-8",
    )
    return relative_artifact_descriptor(manifest, repo_root=tmp_path), reference


def test_endpoint_recovery_allows_appended_diagnostics(tmp_path: Path) -> None:
    manifest, reference = _reference(tmp_path)
    current = reference.assign(identification_width=[0.1, 0.2])

    audit = reconcile_from_json_reference(
        {"result": current},
        reference_json=manifest,
        artifact_section="artifacts",
        repo_root=tmp_path,
    )

    assert audit["status"] == "exact_reference_column_equivalence_verified"
    assert audit["frames"]["result"]["appended_columns"] == ["identification_width"]


def test_endpoint_recovery_rejects_scientific_metric_drift(tmp_path: Path) -> None:
    manifest, reference = _reference(tmp_path)
    current = reference.copy()
    current.loc[0, "metric"] += 1.0e-12

    with pytest.raises(AssertionError):
        reconcile_from_json_reference(
            {"result": current},
            reference_json=manifest,
            artifact_section="artifacts",
            repo_root=tmp_path,
            float_atol=5.0e-14,
            float_rtol=5.0e-14,
        )


def test_endpoint_recovery_accepts_and_records_machine_float_drift(tmp_path: Path) -> None:
    manifest, reference = _reference(tmp_path)
    current = reference.copy()
    current.loc[0, "metric"] = float(current.loc[0, "metric"]) + 2.0e-15

    audit = reconcile_from_json_reference(
        {"result": current},
        reference_json=manifest,
        artifact_section="artifacts",
        repo_root=tmp_path,
        float_atol=5.0e-14,
        float_rtol=5.0e-14,
    )

    assert audit["status"] == "reference_column_equivalence_verified_with_float_tolerance"
    assert audit["equivalence"] == {
        "non_float_columns_exact": True,
        "float_atol": 5.0e-14,
        "float_rtol": 5.0e-14,
    }
    assert audit["frames"]["result"]["float_drift"]["metric"]["maximum_absolute"] > 0.0


def test_endpoint_recovery_keeps_nonfloat_columns_exact_under_float_tolerance(
    tmp_path: Path,
) -> None:
    manifest, reference = _reference(tmp_path)
    current = reference.copy()
    current.loc[0, "id"] = "changed"

    with pytest.raises(AssertionError):
        reconcile_from_json_reference(
            {"result": current},
            reference_json=manifest,
            artifact_section="artifacts",
            repo_root=tmp_path,
            float_atol=5.0e-14,
            float_rtol=5.0e-14,
        )
