"""Verified outcome-free parent loading for isolated IJDS challengers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.evaluation.standardized_credit_payoff import contractual_rate_decimal
from src.ijds_audit.protocol import verified_freeze_artifact_paths
from src.utils.isolated_experiment import relative_artifact_descriptor, sha256_file


def verified_parent_artifacts(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Verify the immutable parent freeze and return all referenced paths."""
    parent = config["parent"]
    descriptor = parent["protocol_freeze"]
    freeze_path = (repo_root / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(freeze_path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Parent protocol freeze mismatch for {field}.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not isinstance(freeze, dict):
        raise TypeError("Parent protocol freeze must be a JSON object.")
    expected = {
        "run_tag": str(parent["run_tag"]),
        "protocol_tag": str(parent["protocol_tag"]),
        "protocol_commit": str(parent["protocol_commit"]),
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise RuntimeError(f"Parent freeze field mismatch: {field}.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("Parent outcome-free freeze reports an outcome column.")
    return verified_freeze_artifact_paths(freeze, repo_root=repo_root), freeze


def load_outcome_free_decision_base(
    *,
    scores_path: Path,
    raw_path: Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Join frozen roles/scores to an explicit non-outcome raw-column allowlist."""
    source = config["source_ingest"]
    if sha256_file(raw_path) != str(source["raw_sha256"]):
        raise RuntimeError("Raw archive hash does not match the locked source.")
    scores = pd.read_parquet(scores_path)
    roles = {str(value) for value in config["frontier"]["roles"]}
    score_frame = scores.loc[scores["design_split"].isin(roles)].copy()
    score_frame["id"] = score_frame["id"].astype("string")
    if bool(score_frame["id"].duplicated().any()):
        raise RuntimeError("Frozen decision scores contain duplicate IDs.")
    target_ids = set(score_frame["id"].astype(str))
    allowed = [str(value) for value in source["allowed_raw_columns"]]
    pieces: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        raw_path,
        usecols=lambda column: str(column) in allowed,
        dtype={"id": "string"},
        chunksize=int(source["chunksize"]),
        low_memory=False,
    ):
        selected = chunk.loc[chunk["id"].astype(str).isin(target_ids)]
        if not selected.empty:
            pieces.append(selected)
    if not pieces:
        raise RuntimeError("No raw decision rows matched the frozen score universe.")
    raw = pd.concat(pieces, ignore_index=True)
    raw["id"] = raw["id"].astype("string")
    if bool(raw["id"].duplicated().any()) or set(raw["id"].astype(str)) != target_ids:
        raise RuntimeError("Raw decision fields do not align one-to-one with frozen scores.")
    frame = score_frame.merge(raw, on="id", how="left", validate="one_to_one")
    frame = frame.rename(columns={"pd_catboost_platt": "pd_point"})
    frame["issue_d"] = pd.to_datetime(frame["issue_d"])
    frame["loan_amnt"] = pd.to_numeric(frame["loan_amnt"], errors="raise").astype(float)
    frame["purpose"] = frame["purpose"].astype("string").fillna("unknown")
    frame["contractual_rate"] = contractual_rate_decimal(frame["int_rate"])
    frame = frame.drop(columns=["int_rate", "pd_numeric_logistic_platt"])
    tokens = tuple(str(token).casefold() for token in source["forbidden_tokens"])
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).casefold() for token in tokens)
    ]
    if forbidden:
        raise RuntimeError(f"Decision base contains forbidden columns: {forbidden}.")
    counts = frame["design_split"].value_counts().to_dict()
    expected = {"policy_development": 94_885, "primary_oot": 376_890}
    if counts != expected:
        raise RuntimeError(f"Decision role census changed: {counts}.")
    return frame.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)


def monthly_frames(frame: pd.DataFrame, role: str) -> tuple[tuple[str, pd.DataFrame], ...]:
    """Return stable monthly copies for one declared design role."""
    selected = frame.loc[frame["design_split"].eq(role)].copy()
    periods = selected["issue_d"].dt.to_period("M")
    return tuple(
        (str(period), selected.loc[periods.eq(period)].copy())
        for period in sorted(periods.unique())
    )
