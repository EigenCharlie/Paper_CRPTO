"""Tests for structural-shard validation and zero-copy recovery."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from src.ijds_audit.structural_checkpoint import (
    ARTIFACT_FILES,
    EXPECTED_ROWS,
    hardlink_structural_shard,
    inspect_structural_shard,
)

SCENARIO = "b0500k_p020_l025"


def _write_shard(root: Path, *, retry_slack: float = 1.0e-12) -> Path:
    frontier = root / SCENARIO / "frontier"
    frontier.mkdir(parents=True)
    for name, filename in ARTIFACT_FILES.items():
        rows = EXPECTED_ROWS.get(name, 5)
        frame = pd.DataFrame({"scenario_id": [SCENARIO] * rows})
        if name == "minimum_endpoint_diagnostics":
            frame["minimum_endpoint_retried"] = [True] + [False] * (rows - 1)
            frame["minimum_endpoint_retry_slack"] = [retry_slack] + [0.0] * (rows - 1)
            frame["minimum_cap_residual"] = [retry_slack] + [0.0] * (rows - 1)
        frame.to_parquet(frontier / filename, index=False)
    return root / SCENARIO


def test_structural_shard_is_validated_and_hardlinked(tmp_path: Path) -> None:
    source = _write_shard(tmp_path / "source")
    inspection = inspect_structural_shard(
        source,
        scenario_id=SCENARIO,
        retry_slack=1.0e-12,
        cap_residual_tolerance=1.0e-8,
    )

    linked = hardlink_structural_shard(
        inspection,
        destination_root=tmp_path / "destination" / SCENARIO,
    )

    assert inspection.minimum_endpoint_retries == 1
    assert inspection.rows["solve_records"] == 1_440
    assert all(os.path.samefile(inspection.paths[name], path) for name, path in linked.items())


def test_structural_shard_rejects_undeclared_retry_slack(tmp_path: Path) -> None:
    source = _write_shard(tmp_path / "source", retry_slack=1.0e-9)

    with pytest.raises(RuntimeError, match="undeclared retry slack"):
        inspect_structural_shard(
            source,
            scenario_id=SCENARIO,
            retry_slack=1.0e-12,
            cap_residual_tolerance=1.0e-8,
        )


def test_structural_shard_rejects_outcome_columns(tmp_path: Path) -> None:
    source = _write_shard(tmp_path / "source")
    allocation_path = source / "frontier" / ARTIFACT_FILES["allocations"]
    frame = pd.read_parquet(allocation_path)
    frame["snapshot_default"] = 0
    frame.to_parquet(allocation_path, index=False)

    with pytest.raises(RuntimeError, match="has outcomes"):
        inspect_structural_shard(
            source,
            scenario_id=SCENARIO,
            retry_slack=1.0e-12,
            cap_residual_tolerance=1.0e-8,
        )
