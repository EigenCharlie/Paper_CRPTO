"""Validation and zero-copy recovery for structural-sensitivity shards."""

from __future__ import annotations

import os
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

ARTIFACT_FILES = {
    "solve_records": "solve_records.parquet",
    "allocations": "allocations.parquet",
    "endpoint_diagnostics": "endpoint_diagnostics.parquet",
    "minimum_endpoint_diagnostics": "minimum_endpoint_diagnostics.parquet",
    "objective_optimum_diagnostics": "objective_optimum_diagnostics.parquet",
    "order_sensitivity": "order_sensitivity.parquet",
    "independent_validation": "independent_validation.parquet",
}
EXPECTED_ROWS = {
    "solve_records": 1_440,
    "endpoint_diagnostics": 720,
    "minimum_endpoint_diagnostics": 600,
    "objective_optimum_diagnostics": 15,
    "order_sensitivity": 1_440,
    "independent_validation": 288,
}
FORBIDDEN_OUTCOME_COLUMNS = {
    "snapshot_default",
    "snapshot_resolution",
    "terminal_default",
    "terminal_outcome",
    "loan_status",
    "last_pymnt_d",
}


@dataclass(frozen=True)
class StructuralShardInspection:
    """Validated paths and row counts for one complete outcome-free scenario."""

    scenario_id: str
    paths: dict[str, Path]
    rows: dict[str, int]
    minimum_endpoint_retries: int
    maximum_retry_slack: float
    maximum_cap_residual: float


def inspect_structural_shard(
    scenario_root: Path,
    *,
    scenario_id: str,
    retry_slacks: Collection[float],
    cap_residual_tolerance: float,
) -> StructuralShardInspection:
    """Reject incomplete, mislabeled, outcome-bearing, or numerically invalid shards."""
    frontier = scenario_root / "frontier"
    expected_names = set(ARTIFACT_FILES.values())
    actual_names = {path.name for path in frontier.glob("*.parquet")}
    if actual_names != expected_names:
        raise RuntimeError(
            f"Structural shard {scenario_id} has artifact inventory {sorted(actual_names)}."
        )
    paths: dict[str, Path] = {}
    rows: dict[str, int] = {}
    for name, filename in ARTIFACT_FILES.items():
        path = frontier / filename
        parquet = pq.ParquetFile(path)
        columns = set(parquet.schema_arrow.names)
        forbidden = sorted(columns.intersection(FORBIDDEN_OUTCOME_COLUMNS))
        if forbidden:
            raise RuntimeError(f"Structural shard {scenario_id}/{name} has outcomes: {forbidden}.")
        if "scenario_id" not in columns:
            raise RuntimeError(f"Structural shard {scenario_id}/{name} lacks scenario identity.")
        identities = set(parquet.read(columns=["scenario_id"])["scenario_id"].to_pylist())
        if identities != {scenario_id}:
            raise RuntimeError(
                f"Structural shard {scenario_id}/{name} has identities {identities}."
            )
        row_count = int(parquet.metadata.num_rows)
        if name in EXPECTED_ROWS and row_count != EXPECTED_ROWS[name]:
            raise RuntimeError(
                f"Structural shard {scenario_id}/{name} has {row_count} rows, "
                f"not {EXPECTED_ROWS[name]}."
            )
        if name == "allocations" and row_count <= 0:
            raise RuntimeError(f"Structural shard {scenario_id} has no funded rows.")
        paths[name] = path
        rows[name] = row_count
    minimum = pq.read_table(
        paths["minimum_endpoint_diagnostics"],
        columns=[
            "minimum_endpoint_retried",
            "minimum_endpoint_retry_slack",
            "minimum_cap_residual",
        ],
    ).to_pandas()
    allowed_slacks = {0.0, *(float(value) for value in retry_slacks)}
    slack_values = set(minimum["minimum_endpoint_retry_slack"].astype(float).unique())
    if not slack_values.issubset(allowed_slacks):
        raise RuntimeError(f"Structural shard {scenario_id} has undeclared retry slack.")
    maximum_slack = float(minimum["minimum_endpoint_retry_slack"].max())
    maximum_residual = float(minimum["minimum_cap_residual"].abs().max())
    declared_maximum = max(allowed_slacks)
    if maximum_slack > declared_maximum or maximum_residual > float(cap_residual_tolerance):
        raise RuntimeError(f"Structural shard {scenario_id} exceeds its numerical contract.")
    return StructuralShardInspection(
        scenario_id=scenario_id,
        paths=paths,
        rows=rows,
        minimum_endpoint_retries=int(minimum["minimum_endpoint_retried"].sum()),
        maximum_retry_slack=maximum_slack,
        maximum_cap_residual=maximum_residual,
    )


def hardlink_structural_shard(
    inspection: StructuralShardInspection,
    *,
    destination_root: Path,
) -> dict[str, Path]:
    """Link one validated shard into a fresh run without duplicating bytes."""
    if destination_root.exists():
        raise FileExistsError(f"Structural destination already exists: {destination_root}.")
    frontier = destination_root / "frontier"
    frontier.mkdir(parents=True)
    linked: dict[str, Path] = {}
    for name, source in inspection.paths.items():
        destination = frontier / ARTIFACT_FILES[name]
        os.link(source, destination)
        linked[name] = destination
    return linked
