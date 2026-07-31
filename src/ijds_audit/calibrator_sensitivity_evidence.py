"""Fail-closed loader for the active four-calibrator sensitivity.

The active lineage has four immutable Git states:

``P`` protocol -> ``A`` outcome-free artifacts -> ``B`` evaluation lock ->
``C`` evaluation artifacts.

This module verifies that chain, every registered byte descriptor, the
outcome-free/evaluation receipts, and the complete persisted grids before any
result is exposed to publication code.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype

from src.ijds_audit.calibrator_sensitivity import (
    CALIBRATOR_METHODS,
    CANONICAL_GROUPS,
    WINDOW_IDS,
    load_recipe_payload,
    unordered_method_pairs,
)
from src.ijds_audit.grid_contracts import (
    require_exact_frame,
    require_exact_grid,
    require_finite,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor

_LOCK_SHA256 = "83a10656fcad1af30b42659df24924614576e9eaa727f83e8bb10043da236149"
_PROTOCOL_COMMIT = "808827926eff5030b3cb28d2b89a87a0e6210b2e"
_SOURCE_COMMIT = "ea3e7326afc38ccc1b99b09de30792986640e3c3"
_EVALUATION_PROTOCOL_COMMIT = "753305e81e27f793acdea80b684b42e7eff2201d"
_EVALUATION_COMMIT = "6552524eae5a22ce66b50689900383d16df1ff13"
_PROTOCOL_TAG = "protocol/ijds-calibrator-sensitivity-2026-07-30-v1"
_SOURCE_TAG = "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source"
_EVALUATION_PROTOCOL_TAG = "protocol/ijds-calibrator-sensitivity-evaluation-2026-07-30-v1"
_EVALUATION_TAG = "artifacts/ijds-calibrator-sensitivity-2026-07-30-v1"
_SOURCE_RUN_TAG = "ijds-calibrator-sensitivity-2026-07-30-v1-source"
_EVALUATION_RUN_TAG = "ijds-calibrator-sensitivity-2026-07-30-v1"
_TRANSPORT = "git_force_tracked_direct_child_commit"
_RESULT_STATE = "uniform_closed_family_shortfall_not_established"
_NOMINAL_COVERAGE = 0.90
_GROUPS = (-1, 0, 1, 2, 3, 4)
_GEOMETRY_ROLES = (
    "probability_calibration",
    "conformal_fit",
    "policy_development",
    "primary_oot",
    "censored_extension",
)

_SOURCE_PATHS = (
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/"
    "calibration_fit_diagnostics.parquet",
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/"
    "outcome_free_geometry.parquet",
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/recipe_audit.parquet",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/execution_receipt.json",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/calibrator_family.pkl",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/"
    "calibrator_residual_recipes.json",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/prediction/"
    "common_q_raw_taxonomy.json",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1-source/protocol_freeze.json",
)
_EVALUATION_PROTOCOL_PATHS = (
    "configs/experiments/ijds_calibrator_sensitivity_evaluation_2026-07-30_v1.yaml",
    "docs/research/ijds_calibrator_sensitivity_v1_evaluation_lock_2026-07-30.md",
)
_EVALUATION_PATHS = (
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/evaluation/"
    "calibrator_sensitivity.parquet",
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/evaluation/"
    "calibrator_sensitivity_overall.parquet",
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/evaluation/"
    "pairwise_shared_completion.parquet",
    "data/processed/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/evaluation/"
    "platt_v5_reconciliation.parquet",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/calibrator_sensitivity_summary.json",
    "models/experiments/ijds_audit/"
    "ijds-calibrator-sensitivity-2026-07-30-v1/execution_receipt.json",
)

_REGISTERED_PATHS = {
    "calibrator_sensitivity_freeze_config": (
        "configs/experiments/ijds_calibrator_sensitivity_freeze_2026-07-30_v1.yaml"
    ),
    "calibrator_sensitivity_evaluation_config": _EVALUATION_PROTOCOL_PATHS[0],
    "calibrator_sensitivity_protocol": (
        "docs/research/ijds_calibrator_sensitivity_v1_protocol_2026-07-30.md"
    ),
    "calibrator_sensitivity_evaluation_lock": _EVALUATION_PROTOCOL_PATHS[1],
    "calibrator_sensitivity_runner": ("scripts/experiments/run_ijds_calibrator_sensitivity_v1.py"),
    "calibrator_sensitivity_implementation": ("src/ijds_audit/calibrator_sensitivity.py"),
    "calibrator_sensitivity_protocol_runner": ("src/ijds_audit/calibrator_sensitivity_protocol.py"),
    "calibrator_sensitivity_source_freeze": _SOURCE_PATHS[7],
    "calibrator_sensitivity_source_receipt": _SOURCE_PATHS[3],
    "calibrator_sensitivity_calibrator_family": _SOURCE_PATHS[4],
    "calibrator_sensitivity_taxonomy": _SOURCE_PATHS[6],
    "calibrator_sensitivity_residual_recipes": _SOURCE_PATHS[5],
    "calibrator_sensitivity_calibration_fit_diagnostics": _SOURCE_PATHS[0],
    "calibrator_sensitivity_recipe_audit": _SOURCE_PATHS[2],
    "calibrator_sensitivity_outcome_free_geometry": _SOURCE_PATHS[1],
    "calibrator_sensitivity_evaluation_summary": _EVALUATION_PATHS[4],
    "calibrator_sensitivity_evaluation_receipt": _EVALUATION_PATHS[5],
    "calibrator_sensitivity_evaluation": _EVALUATION_PATHS[0],
    "calibrator_sensitivity_overall": _EVALUATION_PATHS[1],
    "calibrator_sensitivity_pairwise": _EVALUATION_PATHS[2],
    "calibrator_sensitivity_platt_v5_reconciliation": _EVALUATION_PATHS[3],
}
_AUTHORITY_REGISTERED_PATHS = {
    "v4_config": "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml",
    "v4_summary": (
        "models/experiments/ijds_audit/"
        "ijds-binary-geometry-frontier-v4-2026-07-15-v5/"
        "binary_geometry_frontier_v4_summary.json"
    ),
    "raw_data_audit": (
        "reports/crpto/data_audit/ijds-raw-data-contract-2026-07-14-v2/evidence.json"
    ),
}
_V4_OUTCOME_FREE_CONFIG_PATH = (
    "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"
)

_FIT_COLUMNS = (
    "method",
    "rows",
    "default_rate",
    "roc_auc",
    "brier",
    "log_loss",
    "ece_10",
    "venn_multiprobability_gap_mean",
    "same_sample_descriptive_only",
    "selection_metric",
)
_RECIPE_COLUMNS = (
    "method",
    "window_id",
    "conformal_group",
    "fit_rows",
    "finite_sample_rank",
    "raw_finite_sample_rank",
    "residual_quantile",
    "platt_active_residual_quantile_difference",
    "common_membership",
)
_GEOMETRY_COLUMNS = (
    "method",
    "window_id",
    "taxonomy_groups",
    "role",
    "conformal_group",
    "score_min",
    "score_max",
    "q_raw_min",
    "q_raw_max",
    "venn_multiprobability_gap_mean",
    "venn_multiprobability_gap_q50",
    "rows",
    "mean_width",
    "average_set_size",
    "singleton_share",
    "set_empty_count",
    "set_empty_share",
    "set_zero_only_count",
    "set_zero_only_share",
    "set_one_only_count",
    "set_one_only_share",
    "set_both_count",
    "set_both_share",
    "lower_positive_share",
    "upper_saturated_share",
    "width_q00",
    "width_q10",
    "width_q25",
    "width_q50",
    "width_q75",
    "width_q90",
    "width_q100",
)
_EVALUATION_COLUMNS = (
    "method",
    "window_id",
    "taxonomy_groups",
    "role",
    "conformal_group",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
    "coverage_resolved",
    "coverage_lower",
    "coverage_upper",
    "coverage_resolved_y0",
    "coverage_resolved_y1",
    "rows",
    "mean_width",
    "average_set_size",
    "singleton_share",
    "set_empty_count",
    "set_empty_share",
    "set_zero_only_count",
    "set_zero_only_share",
    "set_one_only_count",
    "set_one_only_share",
    "set_both_count",
    "set_both_share",
    "lower_positive_share",
    "upper_saturated_share",
    "width_q00",
    "width_q10",
    "width_q25",
    "width_q50",
    "width_q75",
    "width_q90",
    "width_q100",
    "score_min",
    "score_max",
    "fit_rows",
    "fit_prevalence",
    "fit_residual_quantile",
    "fit_score_min",
    "fit_score_max",
    "scores_below_fit_range",
    "scores_above_fit_range",
    "venn_multiprobability_gap_mean",
    "venn_multiprobability_gap_q50",
    "coverage_upper_below_nominal",
)
_PLATT_BETA_AGGREGATE_EQUALITY_COLUMNS = (
    "rows",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
    "coverage_resolved",
    "coverage_lower",
    "coverage_upper",
    "coverage_resolved_y0",
    "coverage_resolved_y1",
    "average_set_size",
    "singleton_share",
    "set_empty_count",
    "set_empty_share",
    "set_zero_only_count",
    "set_zero_only_share",
    "set_one_only_count",
    "set_one_only_share",
    "set_both_count",
    "set_both_share",
    "lower_positive_share",
    "upper_saturated_share",
)
_PAIRWISE_COLUMNS = (
    "method_a",
    "method_b",
    "window_id",
    "taxonomy_groups",
    "role",
    "conformal_group",
    "candidate_rows",
    "resolved_rows",
    "unresolved_rows",
    "coverage_difference_resolved",
    "coverage_difference_lower",
    "coverage_difference_upper",
    "shared_loanwise_completion",
)
_RECONCILIATION_DIFFERENCE_COLUMNS = (
    "candidate_rows_difference",
    "resolved_rows_difference",
    "unresolved_rows_difference",
    "coverage_resolved_difference",
    "coverage_lower_difference",
    "coverage_upper_difference",
    "score_min_difference",
    "score_max_difference",
    "fit_rows_difference",
    "fit_prevalence_difference",
    "fit_residual_quantile_difference",
    "fit_score_min_difference",
    "fit_score_max_difference",
    "scores_below_fit_range_difference",
    "scores_above_fit_range_difference",
    "rows_difference",
    "mean_width_difference",
    "lower_positive_share_difference",
    "upper_saturated_share_difference",
    "set_empty_count_difference",
    "set_empty_share_difference",
    "set_zero_only_count_difference",
    "set_zero_only_share_difference",
    "set_one_only_count_difference",
    "set_one_only_share_difference",
    "set_both_count_difference",
    "set_both_share_difference",
    "width_q00_difference",
    "width_q10_difference",
    "width_q25_difference",
    "width_q50_difference",
    "width_q75_difference",
    "width_q90_difference",
    "width_q100_difference",
)
_RECONCILIATION_COLUMNS = (
    "window_id",
    "conformal_group",
    *_RECONCILIATION_DIFFERENCE_COLUMNS,
)
_SET_COUNT_COLUMNS = (
    "set_empty_count",
    "set_zero_only_count",
    "set_one_only_count",
    "set_both_count",
)
_SET_SHARE_COLUMNS = (
    "set_empty_share",
    "set_zero_only_share",
    "set_one_only_share",
    "set_both_share",
)


@dataclass(frozen=True)
class CalibratorSensitivityEvidence:
    """Verified active calibrator evidence and publication-safe findings."""

    freeze: Mapping[str, Any]
    source_receipt: Mapping[str, Any]
    summary: Mapping[str, Any]
    evaluation_receipt: Mapping[str, Any]
    taxonomy: Mapping[str, Any]
    frames: Mapping[str, pd.DataFrame]
    findings: Mapping[str, Any]


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object.")
    return payload


def _mapping(payload: Mapping[str, Any], key: str, *, label: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise TypeError(f"{label}.{key} must be a mapping.")
    return cast(Mapping[str, Any], value)


def _require_exact_columns(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    label: str,
) -> None:
    if tuple(frame.columns) != tuple(columns):
        raise RuntimeError(f"{label} persisted columns or column order changed.")


def _require_clean_execution(payload: Mapping[str, Any], *, label: str) -> None:
    if payload.get("protected_stages_run") != []:
        raise RuntimeError(f"{label} reports a protected stage execution.")
    if payload.get("protected_artifacts_written") != []:
        raise RuntimeError(f"{label} reports a protected artifact write.")


def _require_identity(
    payload: Mapping[str, Any],
    *,
    run_tag: str,
    protocol_tag: str,
    protocol_commit: str,
    status: str,
    label: str,
) -> None:
    expected = {
        "run_tag": run_tag,
        "protocol_tag": protocol_tag,
        "protocol_commit": protocol_commit,
        "status": status,
    }
    changed = {
        key: payload.get(key) for key, value in expected.items() if payload.get(key) != value
    }
    if changed:
        raise RuntimeError(f"{label} identity or completion status changed: {changed}.")


def _require_registry_identity(
    identity: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    changed = {
        key: identity.get(key) for key, value in expected.items() if identity.get(key) != value
    }
    if changed:
        raise RuntimeError(f"{label} registry identity changed: {changed}.")


def _require_registered_paths(
    registered: Mapping[str, Path],
    *,
    repo_root: Path,
) -> None:
    expected_paths = _REGISTERED_PATHS | _AUTHORITY_REGISTERED_PATHS
    missing = sorted(set(expected_paths).difference(registered))
    if missing:
        raise KeyError(f"Calibrator sensitivity registry keys are missing: {missing}.")
    root = repo_root.resolve()
    for name, relative in expected_paths.items():
        expected = (root / relative).resolve()
        actual = registered[name].resolve()
        try:
            actual.relative_to(root)
        except ValueError as error:
            raise RuntimeError(
                f"Registered calibrator source {name!r} escapes the repo."
            ) from error
        if actual != expected:
            raise RuntimeError(f"Registered calibrator source {name!r} changed path.")


def _descriptor_path(
    raw: Any,
    *,
    repo_root: Path,
    label: str,
) -> Path:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    relative = raw.get("path")
    if not isinstance(relative, str):
        raise TypeError(f"{label}.path must be text.")
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or ".." in normalized.parts or normalized.as_posix() != relative:
        raise ValueError(f"{label}.path is not a safe normalized repository path.")
    path = (repo_root / relative).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as error:
        raise ValueError(f"{label}.path escapes the repository.") from error
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    if actual != dict(raw):
        raise RuntimeError(f"{label} no longer matches the registered local bytes.")
    return path


def _exact_descriptor(raw: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    return dict(raw)


def _raw_source_descriptor(raw: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {
        "path",
        "bytes",
        "sha256",
        "dvc_md5",
    }:
        raise TypeError(f"{label} must be an exact path/bytes/sha256/dvc_md5 descriptor.")
    dvc_md5 = raw.get("dvc_md5")
    if not isinstance(dvc_md5, str) or len(dvc_md5) != 32:
        raise TypeError(f"{label}.dvc_md5 must be a 32-character checksum.")
    return {key: raw[key] for key in ("path", "bytes", "sha256")}


def _require_descriptor_matches_authority(
    raw: Any,
    authority: Any,
    *,
    repo_root: Path,
    label: str,
) -> Path:
    descriptor = _exact_descriptor(raw, label=label)
    expected = _exact_descriptor(authority, label=f"{label} authority")
    if descriptor != expected:
        raise RuntimeError(f"{label} descriptor, route, or hash changed from its active authority.")
    return _descriptor_path(descriptor, repo_root=repo_root, label=label)


def _git_text(repo_root: Path, arguments: Sequence[str], *, label: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git verification failed for {label}: {result.stderr.strip()}")
    return result.stdout.strip()


def _require_annotated_tag(
    tag: str,
    commit: str,
    *,
    repo_root: Path,
    label: str,
) -> None:
    kind = _git_text(
        repo_root,
        ("cat-file", "-t", f"refs/tags/{tag}"),
        label=f"{label} tag object",
    )
    if kind != "tag":
        raise RuntimeError(f"{label} tag {tag!r} is missing or is lightweight.")
    resolved = _git_text(
        repo_root,
        ("rev-parse", "--verify", "--end-of-options", f"refs/tags/{tag}^{{commit}}"),
        label=f"{label} tag target",
    )
    if resolved != commit:
        raise RuntimeError(f"{label} tag {tag!r} no longer resolves to {commit}.")


def _require_git_stage(
    *,
    tag: str,
    commit: str,
    parent: str,
    paths: Sequence[str],
    repo_root: Path,
    label: str,
) -> None:
    _require_annotated_tag(tag, commit, repo_root=repo_root, label=label)
    ancestry = _git_text(
        repo_root,
        ("rev-list", "--parents", "-n", "1", commit),
        label=f"{label} ancestry",
    ).split()
    if ancestry != [commit, parent]:
        raise RuntimeError(f"{label} is not the required single direct child of {parent}.")
    changed = _git_text(
        repo_root,
        ("diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", commit),
        label=f"{label} exact diff",
    ).splitlines()
    if changed != list(paths):
        raise RuntimeError(f"{label} changed {changed}, not the exact locked path list.")
    for path in paths:
        _git_text(
            repo_root,
            ("cat-file", "-e", f"{commit}:{path}"),
            label=f"{label} blob {path}",
        )


def _require_git_blob_descriptor(
    *,
    commit: str,
    descriptor: Mapping[str, Any],
    repo_root: Path,
    label: str,
) -> None:
    relative = descriptor.get("path")
    if not isinstance(relative, str):
        raise TypeError(f"{label} descriptor path must be text.")
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} is absent from pinned commit {commit}.")
    if len(result.stdout) != descriptor.get("bytes") or hashlib.sha256(
        result.stdout
    ).hexdigest() != descriptor.get("sha256"):
        raise RuntimeError(f"{label} descriptor does not match its pinned Git blob.")


def _require_implementation_provenance(
    payload: Mapping[str, Any],
    *,
    commit: str,
    repo_root: Path,
    label: str,
) -> None:
    provenance = _mapping(payload, "implementation_provenance", label=label)
    if provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError(f"{label} implementation hash algorithm changed.")
    source_files = provenance.get("source_files")
    if not isinstance(source_files, Mapping) or not source_files:
        raise TypeError(f"{label} implementation source inventory is empty.")
    for relative, raw_descriptor in source_files.items():
        if not isinstance(relative, str) or not isinstance(raw_descriptor, Mapping):
            raise TypeError(f"{label} has an invalid implementation descriptor.")
        descriptor = cast(Mapping[str, Any], raw_descriptor)
        path = _descriptor_path(
            descriptor,
            repo_root=repo_root,
            label=f"{label} implementation {relative}",
        )
        if path != (repo_root / relative).resolve():
            raise RuntimeError(f"{label} implementation key and descriptor path disagree.")
        _require_git_blob_descriptor(
            commit=commit,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"{label} implementation {relative}",
        )


def _require_git_lineage(
    identities: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if set(identities) != {"outcome_free", "evaluation"}:
        raise RuntimeError("Calibrator registry must have exactly outcome_free and evaluation.")
    source_identity = identities.get("outcome_free")
    evaluation_identity = identities.get("evaluation")
    if not isinstance(source_identity, Mapping) or not isinstance(evaluation_identity, Mapping):
        raise TypeError("Calibrator registry lineage phases must be mappings.")
    source = cast(Mapping[str, Any], source_identity)
    evaluation = cast(Mapping[str, Any], evaluation_identity)
    _require_registry_identity(
        source,
        {
            "run_tag": _SOURCE_RUN_TAG,
            "protocol_tag": _PROTOCOL_TAG,
            "protocol_commit": _PROTOCOL_COMMIT,
            "scientific_uv_lock_sha256": _LOCK_SHA256,
            "paper_role": (
                "outcome_free_closed_calibrator_family_and_common_q_raw_taxonomy_freeze"
            ),
            "dvc_tracked": False,
            "artifact_tag": _SOURCE_TAG,
            "artifact_commit": _SOURCE_COMMIT,
            "artifact_parent_commit": _PROTOCOL_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_SOURCE_PATHS),
        },
        label="calibrator outcome-free",
    )
    _require_registry_identity(
        evaluation,
        {
            "run_tag": _EVALUATION_RUN_TAG,
            "protocol_tag": _EVALUATION_PROTOCOL_TAG,
            "protocol_commit": _EVALUATION_PROTOCOL_COMMIT,
            "scientific_uv_lock_sha256": _LOCK_SHA256,
            "paper_role": "complete_retrospective_closed_calibrator_family_sensitivity",
            "dvc_tracked": False,
            "artifact_tag": _EVALUATION_TAG,
            "artifact_commit": _EVALUATION_COMMIT,
            "artifact_parent_commit": _EVALUATION_PROTOCOL_COMMIT,
            "artifact_transport": _TRANSPORT,
            "artifact_paths": list(_EVALUATION_PATHS),
        },
        label="calibrator evaluation",
    )
    _require_annotated_tag(
        _PROTOCOL_TAG,
        _PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="calibrator P protocol",
    )
    _require_git_stage(
        tag=_SOURCE_TAG,
        commit=_SOURCE_COMMIT,
        parent=_PROTOCOL_COMMIT,
        paths=_SOURCE_PATHS,
        repo_root=repo_root,
        label="calibrator A outcome-free artifact",
    )
    _require_git_stage(
        tag=_EVALUATION_PROTOCOL_TAG,
        commit=_EVALUATION_PROTOCOL_COMMIT,
        parent=_SOURCE_COMMIT,
        paths=_EVALUATION_PROTOCOL_PATHS,
        repo_root=repo_root,
        label="calibrator B evaluation protocol",
    )
    _require_git_stage(
        tag=_EVALUATION_TAG,
        commit=_EVALUATION_COMMIT,
        parent=_EVALUATION_PROTOCOL_COMMIT,
        paths=_EVALUATION_PATHS,
        repo_root=repo_root,
        label="calibrator C evaluation artifact",
    )
    return source, evaluation


def _require_active_source_authorities(
    *,
    freeze: Mapping[str, Any],
    summary: Mapping[str, Any],
    registered: Mapping[str, Path],
    repo_root: Path,
) -> None:
    phase_a_sources = _mapping(freeze, "source_artifacts", label="calibrator freeze")
    expected_phase_a = {
        "active_v4_config",
        "active_v4_freeze",
        "scores",
        "residual_recipes",
        "fit_audit",
        "catboost_model",
        "platt_calibrator",
        "raw_archive",
    }
    if set(phase_a_sources) != expected_phase_a:
        raise RuntimeError("Calibrator Phase-A source-artifact inventory changed.")

    phase_b_sources = _mapping(summary, "source_artifacts", label="calibrator summary")
    expected_phase_b = {
        "phase_a_freeze",
        "phase_a_receipt",
        "active_v5_config",
        "active_v5_summary",
        "active_v5_temporal_coverage",
        "raw_archive",
    }
    if set(phase_b_sources) != expected_phase_b:
        raise RuntimeError("Calibrator Phase-B source-artifact inventory changed.")

    _require_descriptor_matches_authority(
        phase_b_sources.get("active_v5_config"),
        relative_artifact_descriptor(registered["v4_config"], repo_root=repo_root),
        repo_root=repo_root,
        label="calibrator Phase-B active V5 config",
    )
    _require_descriptor_matches_authority(
        phase_b_sources.get("active_v5_summary"),
        relative_artifact_descriptor(registered["v4_summary"], repo_root=repo_root),
        repo_root=repo_root,
        label="calibrator Phase-B active V5 summary",
    )

    v5_summary = _load_json_object(
        registered["v4_summary"],
        label="active V5 binary-geometry summary authority",
    )
    v5_artifacts = _mapping(v5_summary, "artifacts", label="active V5 summary authority")
    _require_descriptor_matches_authority(
        phase_b_sources.get("active_v5_temporal_coverage"),
        v5_artifacts.get("temporal_coverage"),
        repo_root=repo_root,
        label="calibrator Phase-B active V5 temporal coverage",
    )

    raw_audit = _load_json_object(
        registered["raw_data_audit"],
        label="active raw-data audit authority",
    )
    raw_authority = _raw_source_descriptor(
        raw_audit.get("raw_source"),
        label="active raw-data audit authority.raw_source",
    )
    raw_descriptors: list[dict[str, Any]] = []
    for phase, descriptor in (
        ("Phase A", phase_a_sources.get("raw_archive")),
        ("Phase B", phase_b_sources.get("raw_archive")),
    ):
        exact = _exact_descriptor(
            descriptor,
            label=f"calibrator {phase} raw archive",
        )
        if exact != raw_authority:
            raise RuntimeError(
                f"Calibrator {phase} raw archive descriptor, route, or hash "
                "changed from its active authority."
            )
        raw_descriptors.append(exact)

    v5_freeze_path = _descriptor_path(
        v5_summary.get("outcome_free_freeze"),
        repo_root=repo_root,
        label="active V5 summary outcome-free freeze authority",
    )
    v5_freeze = _load_json_object(
        v5_freeze_path,
        label="active V5 outcome-free freeze authority",
    )
    if (
        v5_summary.get("run_tag") != v5_freeze.get("run_tag")
        or v5_summary.get("protocol_tag") != v5_freeze.get("protocol_tag")
        or v5_summary.get("protocol_commit") != v5_freeze.get("protocol_commit")
    ):
        raise RuntimeError("Active V5 summary and outcome-free freeze identity changed.")

    v5_lineage = _mapping(
        v5_freeze,
        "outcome_free_lineage",
        label="active V5 outcome-free freeze authority",
    )
    v4_freeze_descriptor = v5_lineage.get("source_protocol_freeze")
    v4_freeze_path = _require_descriptor_matches_authority(
        phase_a_sources.get("active_v4_freeze"),
        v4_freeze_descriptor,
        repo_root=repo_root,
        label="calibrator Phase-A active V4 outcome-free freeze",
    )
    v4_freeze = _load_json_object(
        v4_freeze_path,
        label="active V4 outcome-free freeze authority",
    )
    if (
        v4_freeze.get("run_tag") != v5_lineage.get("run_tag")
        or v4_freeze.get("protocol_tag") != v5_lineage.get("protocol_tag")
        or v4_freeze.get("protocol_commit") != v5_lineage.get("protocol_commit")
        or v4_freeze.get("status") != v5_lineage.get("status")
    ):
        raise RuntimeError("Active V4 outcome-free freeze lineage identity changed.")

    v4_provenance = _mapping(
        v4_freeze,
        "implementation_provenance",
        label="active V4 outcome-free freeze authority",
    )
    v4_source_files = _mapping(
        v4_provenance,
        "source_files",
        label="active V4 outcome-free implementation provenance",
    )
    _require_descriptor_matches_authority(
        phase_a_sources.get("active_v4_config"),
        v4_source_files.get(_V4_OUTCOME_FREE_CONFIG_PATH),
        repo_root=repo_root,
        label="calibrator Phase-A active V4 config",
    )

    v5_outcome_free = _mapping(
        v5_freeze,
        "outcome_free_artifacts",
        label="active V5 outcome-free freeze authority",
    )
    v4_outcome_free = _mapping(
        v4_freeze,
        "outcome_free_artifacts",
        label="active V4 outcome-free freeze authority",
    )
    v5_models = _mapping(
        v5_freeze,
        "model_artifacts",
        label="active V5 outcome-free freeze authority",
    )
    v4_models = _mapping(
        v4_freeze,
        "model_artifacts",
        label="active V4 outcome-free freeze authority",
    )
    authority_routes = {
        "scores": (v5_outcome_free, v4_outcome_free, "scores"),
        "residual_recipes": (v5_outcome_free, v4_outcome_free, "recipes"),
        "fit_audit": (v5_outcome_free, v4_outcome_free, "fit_audit"),
        "catboost_model": (v5_models, v4_models, "catboost"),
        "platt_calibrator": (v5_models, v4_models, "catboost_platt"),
    }
    for phase_name, (v5_section, v4_section, authority_name) in authority_routes.items():
        v5_descriptor = _exact_descriptor(
            v5_section.get(authority_name),
            label=f"active V5 authority {authority_name}",
        )
        v4_descriptor = _exact_descriptor(
            v4_section.get(authority_name),
            label=f"active V4 authority {authority_name}",
        )
        if v5_descriptor != v4_descriptor:
            raise RuntimeError(f"Active V5/V4 authority cross-link for {authority_name!r} changed.")
        _require_descriptor_matches_authority(
            phase_a_sources.get(phase_name),
            v4_descriptor,
            repo_root=repo_root,
            label=f"calibrator Phase-A {phase_name}",
        )
    _descriptor_path(
        raw_descriptors[0],
        repo_root=repo_root,
        label="calibrator Phase-A/Phase-B raw archive",
    )


def _require_artifact_descriptors(
    *,
    freeze: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
    summary: Mapping[str, Any],
    evaluation_receipt: Mapping[str, Any],
    registered: Mapping[str, Path],
    repo_root: Path,
) -> None:
    _require_active_source_authorities(
        freeze=freeze,
        summary=summary,
        registered=registered,
        repo_root=repo_root,
    )
    registered_by_relative = {
        relative: registered[name] for name, relative in _REGISTERED_PATHS.items()
    }
    for commit, paths, stage in (
        (_SOURCE_COMMIT, _SOURCE_PATHS, "calibrator A outcome-free artifact"),
        (_EVALUATION_COMMIT, _EVALUATION_PATHS, "calibrator C evaluation artifact"),
    ):
        for relative in paths:
            pinned_descriptor = relative_artifact_descriptor(
                registered_by_relative[relative],
                repo_root=repo_root,
            )
            _require_git_blob_descriptor(
                commit=commit,
                descriptor=pinned_descriptor,
                repo_root=repo_root,
                label=f"{stage} {relative}",
            )

    source_artifacts = _mapping(freeze, "outcome_free_artifacts", label="calibrator freeze")
    source_names = {
        "calibrator_family": "calibrator_sensitivity_calibrator_family",
        "taxonomy": "calibrator_sensitivity_taxonomy",
        "residual_recipes": "calibrator_sensitivity_residual_recipes",
        "calibration_fit_diagnostics": ("calibrator_sensitivity_calibration_fit_diagnostics"),
        "recipe_audit": "calibrator_sensitivity_recipe_audit",
        "outcome_free_geometry": "calibrator_sensitivity_outcome_free_geometry",
    }
    for artifact_name, registered_name in source_names.items():
        raw_descriptor = source_artifacts.get(artifact_name)
        path = _descriptor_path(
            raw_descriptor,
            repo_root=repo_root,
            label=f"calibrator freeze artifact {artifact_name}",
        )
        if path != registered[registered_name].resolve():
            raise RuntimeError(f"Calibrator source artifact {artifact_name!r} route changed.")
        _require_git_blob_descriptor(
            commit=_SOURCE_COMMIT,
            descriptor=cast(Mapping[str, Any], raw_descriptor),
            repo_root=repo_root,
            label=f"calibrator source artifact {artifact_name}",
        )

    freeze_descriptor = source_receipt.get("freeze")
    freeze_path = _descriptor_path(
        freeze_descriptor,
        repo_root=repo_root,
        label="calibrator source receipt freeze",
    )
    if freeze_path != registered["calibrator_sensitivity_source_freeze"].resolve():
        raise RuntimeError("Calibrator source receipt freeze route changed.")
    _require_git_blob_descriptor(
        commit=_SOURCE_COMMIT,
        descriptor=cast(Mapping[str, Any], freeze_descriptor),
        repo_root=repo_root,
        label="calibrator source freeze",
    )

    evaluation_artifacts = _mapping(summary, "artifacts", label="calibrator summary")
    evaluation_names = {
        "evaluation": "calibrator_sensitivity_evaluation",
        "overall_summary": "calibrator_sensitivity_overall",
        "pairwise_shared_completion": "calibrator_sensitivity_pairwise",
        "platt_v5_reconciliation": "calibrator_sensitivity_platt_v5_reconciliation",
    }
    for artifact_name, registered_name in evaluation_names.items():
        raw_descriptor = evaluation_artifacts.get(artifact_name)
        path = _descriptor_path(
            raw_descriptor,
            repo_root=repo_root,
            label=f"calibrator evaluation artifact {artifact_name}",
        )
        if path != registered[registered_name].resolve():
            raise RuntimeError(f"Calibrator evaluation artifact {artifact_name!r} route changed.")
        _require_git_blob_descriptor(
            commit=_EVALUATION_COMMIT,
            descriptor=cast(Mapping[str, Any], raw_descriptor),
            repo_root=repo_root,
            label=f"calibrator evaluation artifact {artifact_name}",
        )

    summary_descriptor = evaluation_receipt.get("summary")
    summary_path = _descriptor_path(
        summary_descriptor,
        repo_root=repo_root,
        label="calibrator evaluation receipt summary",
    )
    if summary_path != registered["calibrator_sensitivity_evaluation_summary"].resolve():
        raise RuntimeError("Calibrator evaluation receipt summary route changed.")
    _require_git_blob_descriptor(
        commit=_EVALUATION_COMMIT,
        descriptor=cast(Mapping[str, Any], summary_descriptor),
        repo_root=repo_root,
        label="calibrator evaluation summary",
    )

    phase_sources = _mapping(summary, "source_artifacts", label="calibrator summary")
    for name, registered_name in {
        "phase_a_freeze": "calibrator_sensitivity_source_freeze",
        "phase_a_receipt": "calibrator_sensitivity_source_receipt",
    }.items():
        raw_descriptor = phase_sources.get(name)
        path = _descriptor_path(
            raw_descriptor,
            repo_root=repo_root,
            label=f"calibrator evaluation source {name}",
        )
        if path != registered[registered_name].resolve():
            raise RuntimeError(f"Calibrator evaluation source {name!r} route changed.")
        _require_git_blob_descriptor(
            commit=_SOURCE_COMMIT,
            descriptor=cast(Mapping[str, Any], raw_descriptor),
            repo_root=repo_root,
            label=f"calibrator evaluation source {name}",
        )

    for registered_name, commit in {
        "calibrator_sensitivity_freeze_config": _PROTOCOL_COMMIT,
        "calibrator_sensitivity_protocol": _PROTOCOL_COMMIT,
        "calibrator_sensitivity_runner": _PROTOCOL_COMMIT,
        "calibrator_sensitivity_implementation": _PROTOCOL_COMMIT,
        "calibrator_sensitivity_protocol_runner": _PROTOCOL_COMMIT,
        "calibrator_sensitivity_evaluation_config": _EVALUATION_PROTOCOL_COMMIT,
        "calibrator_sensitivity_evaluation_lock": _EVALUATION_PROTOCOL_COMMIT,
    }.items():
        registered_descriptor = relative_artifact_descriptor(
            registered[registered_name],
            repo_root=repo_root,
        )
        _require_git_blob_descriptor(
            commit=commit,
            descriptor=registered_descriptor,
            repo_root=repo_root,
            label=registered_name,
        )


def _numeric_columns_except(frame: pd.DataFrame, excluded: Sequence[str]) -> list[str]:
    excluded_set = set(excluded)
    return [
        column
        for column in frame.select_dtypes(include=[np.number]).columns
        if column not in excluded_set
    ]


def _require_venn_gap_contract(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str],
    label: str,
) -> None:
    venn = frame["method"].eq("venn_abers")
    for column in columns:
        if not bool(frame.loc[venn, column].notna().all()):
            raise RuntimeError(f"{label} omits applicable Venn--Abers {column}.")
        if not bool(np.isfinite(frame.loc[venn, column].astype(float)).all()):
            raise RuntimeError(f"{label} has nonfinite Venn--Abers {column}.")
        if not bool(frame.loc[~venn, column].isna().all()):
            raise RuntimeError(f"{label} populates non-applicable {column}.")


def _require_set_partition(frame: pd.DataFrame, *, label: str) -> None:
    require_finite(
        frame,
        ("rows", "average_set_size", "singleton_share", *_SET_SHARE_COLUMNS),
        label=label,
    )
    if not frame["rows"].gt(0).all():
        raise RuntimeError(f"{label} contains an empty cell.")
    if not frame.loc[:, _SET_COUNT_COLUMNS].ge(0).all().all():
        raise RuntimeError(f"{label} contains a negative set count.")
    shares = frame.loc[:, _SET_SHARE_COLUMNS]
    if not (shares.ge(0.0) & shares.le(1.0)).all().all():
        raise RuntimeError(f"{label} contains an invalid set share.")
    count_sum = frame.loc[:, _SET_COUNT_COLUMNS].sum(axis=1)
    share_sum = frame.loc[:, _SET_SHARE_COLUMNS].sum(axis=1)
    expected_shares = frame.loc[:, _SET_COUNT_COLUMNS].div(
        frame["rows"].to_numpy(),
        axis=0,
    )
    expected_shares.columns = list(_SET_SHARE_COLUMNS)
    expected_singleton = frame["set_zero_only_share"] + frame["set_one_only_share"]
    expected_size = expected_singleton + 2.0 * frame["set_both_share"]
    if (
        not count_sum.eq(frame["rows"]).all()
        or not np.allclose(share_sum, 1.0, rtol=0.0, atol=2.5e-16)
        or not np.allclose(
            frame.loc[:, _SET_SHARE_COLUMNS],
            expected_shares,
            rtol=0.0,
            atol=0.0,
        )
        or not np.allclose(
            frame["singleton_share"],
            expected_singleton,
            rtol=0.0,
            atol=0.0,
        )
        or not np.allclose(
            frame["average_set_size"],
            expected_size,
            rtol=0.0,
            atol=2.5e-16,
        )
    ):
        raise RuntimeError(f"{label} set census, shares, or cardinality do not reconcile.")


def _validate_fit_diagnostics(
    frame: pd.DataFrame,
    *,
    freeze: Mapping[str, Any],
) -> None:
    _require_exact_columns(frame, _FIT_COLUMNS, label="calibrator fit diagnostics")
    require_exact_grid(
        frame,
        domains={"method": CALIBRATOR_METHODS},
        label="calibrator fit diagnostics",
    )
    require_finite(
        frame,
        ("rows", "default_rate", "roc_auc", "brier", "log_loss", "ece_10"),
        label="calibrator fit diagnostics",
    )
    if (
        len(frame) != 4
        or not frame["rows"].eq(14077).all()
        or not frame["same_sample_descriptive_only"].eq(True).all()
        or not frame["selection_metric"].eq(False).all()
        or not frame[["default_rate", "roc_auc", "brier", "ece_10"]].ge(0.0).all().all()
        or not frame[["default_rate", "roc_auc", "brier", "ece_10"]].le(1.0).all().all()
        or not frame["log_loss"].gt(0.0).all()
    ):
        raise RuntimeError("Calibrator same-sample fit diagnostic boundary changed.")
    _require_venn_gap_contract(
        frame,
        columns=("venn_multiprobability_gap_mean",),
        label="calibrator fit diagnostics",
    )
    platt = frame.loc[frame["method"].eq("platt")].iloc[0]
    reconciliation = _mapping(
        _mapping(freeze, "gates", label="calibrator freeze"),
        "active_platt_fit_reconciliation",
        label="calibrator freeze gates",
    )
    metrics = _mapping(
        reconciliation,
        "metrics",
        label="calibrator Platt fit reconciliation",
    )
    for column in ("rows", "default_rate", "roc_auc", "brier", "log_loss", "ece_10"):
        if platt[column] != metrics.get(column):
            raise RuntimeError(f"Calibrator Platt fit metric {column!r} no longer reconciles.")
    if (
        reconciliation.get("y0") != 12602
        or reconciliation.get("y1") != 1475
        or reconciliation.get("metric_tolerance") != 0.0
        or reconciliation.get("metric_max_abs_difference") != 0.0
    ):
        raise RuntimeError("Calibrator Platt fit census or exact reconciliation changed.")


def _validate_taxonomy_and_recipes(
    taxonomy: Mapping[str, Any],
    recipe_payload: Mapping[str, Any],
    recipe_audit: pd.DataFrame,
) -> None:
    if set(taxonomy) != {
        "taxonomy_groups",
        "active_platt_edges",
        "common_q_raw_edges",
        "method",
        "full_panel_assignment_changes",
    }:
        raise RuntimeError("Calibrator common-taxonomy schema changed.")
    active_edges = np.asarray(taxonomy["active_platt_edges"], dtype=float)
    common_edges = np.asarray(taxonomy["common_q_raw_edges"], dtype=float)
    if (
        taxonomy.get("taxonomy_groups") != CANONICAL_GROUPS
        or taxonomy.get("method") != "exact_inverse_transform_of_active_platt_edges"
        or taxonomy.get("full_panel_assignment_changes") != 0
        or active_edges.shape != (CANONICAL_GROUPS + 1,)
        or common_edges.shape != (CANONICAL_GROUPS + 1,)
        or not bool(np.isfinite(active_edges).all() and np.isfinite(common_edges).all())
        or not bool(np.all(np.diff(active_edges) > 0.0))
        or not bool(np.all(np.diff(common_edges) > 0.0))
        or not bool(np.all((active_edges > 0.0) & (active_edges < 1.0)))
        or not bool(np.all((common_edges > 0.0) & (common_edges < 1.0)))
    ):
        raise RuntimeError("Calibrator common q_raw taxonomy changed.")

    recipes = load_recipe_payload(recipe_payload)
    _require_exact_columns(recipe_audit, _RECIPE_COLUMNS, label="calibrator recipe audit")
    require_exact_grid(
        recipe_audit,
        domains={
            "method": CALIBRATOR_METHODS,
            "window_id": WINDOW_IDS,
            "conformal_group": tuple(range(CANONICAL_GROUPS)),
        },
        label="calibrator recipe audit",
    )
    require_finite(
        recipe_audit,
        (
            "fit_rows",
            "finite_sample_rank",
            "raw_finite_sample_rank",
            "residual_quantile",
        ),
        label="calibrator recipe audit",
    )
    if len(recipe_audit) != 160 or not recipe_audit["common_membership"].eq(True).all():
        raise RuntimeError("Calibrator recipe audit completeness changed.")
    for row in recipe_audit.to_dict(orient="records"):
        recipe = recipes[str(row["method"])][str(row["window_id"])]
        group = int(row["conformal_group"])
        expected = (
            recipe.group_counts[group],
            recipe.finite_sample_ranks[group],
            recipe.raw_finite_sample_ranks[group],
            recipe.residual_quantiles[group],
        )
        actual = (
            int(row["fit_rows"]),
            int(row["finite_sample_rank"]),
            int(row["raw_finite_sample_rank"]),
            float(row["residual_quantile"]),
        )
        if actual != expected or tuple(recipe.taxonomy_edges_q_raw) != tuple(common_edges):
            raise RuntimeError("Calibrator recipe audit does not reconstruct frozen recipes.")
        difference = row["platt_active_residual_quantile_difference"]
        if row["method"] == "platt":
            if difference != 0.0:
                raise RuntimeError("Calibrator Platt recipe no longer exactly matches active V4.")
        elif not pd.isna(difference):
            raise RuntimeError("Non-Platt recipe has a non-applicable Platt difference.")


def _validate_geometry(frame: pd.DataFrame) -> None:
    _require_exact_columns(frame, _GEOMETRY_COLUMNS, label="calibrator outcome-free geometry")
    require_exact_grid(
        frame,
        domains={
            "method": CALIBRATOR_METHODS,
            "window_id": WINDOW_IDS,
            "taxonomy_groups": (CANONICAL_GROUPS,),
            "role": _GEOMETRY_ROLES,
            "conformal_group": _GROUPS,
        },
        label="calibrator outcome-free geometry",
    )
    require_finite(
        frame,
        _numeric_columns_except(
            frame,
            ("venn_multiprobability_gap_mean", "venn_multiprobability_gap_q50"),
        ),
        label="calibrator outcome-free geometry",
    )
    if len(frame) != 960:
        raise RuntimeError("Calibrator outcome-free geometry must contain 960 cells.")
    _require_venn_gap_contract(
        frame,
        columns=(
            "venn_multiprobability_gap_mean",
            "venn_multiprobability_gap_q50",
        ),
        label="calibrator outcome-free geometry",
    )
    _require_set_partition(frame, label="calibrator outcome-free geometry")
    for _, block in frame.groupby(
        ["method", "window_id", "role"],
        observed=True,
        sort=False,
    ):
        overall = block.loc[block["conformal_group"].eq(-1)].iloc[0]
        strata = block.loc[block["conformal_group"].ge(0)]
        for column in ("rows", *_SET_COUNT_COLUMNS):
            if overall[column] != strata[column].sum():
                raise RuntimeError("Calibrator geometry overall/stratum census changed.")


def _validate_evaluation(
    evaluation: pd.DataFrame,
    overall: pd.DataFrame,
    geometry: pd.DataFrame,
    recipe_audit: pd.DataFrame,
    *,
    summary: Mapping[str, Any],
) -> None:
    _require_exact_columns(evaluation, _EVALUATION_COLUMNS, label="calibrator evaluation")
    _require_exact_columns(overall, _EVALUATION_COLUMNS, label="calibrator overall evaluation")
    require_exact_grid(
        evaluation,
        domains={
            "method": CALIBRATOR_METHODS,
            "window_id": WINDOW_IDS,
            "taxonomy_groups": (CANONICAL_GROUPS,),
            "role": ("primary_oot",),
            "conformal_group": _GROUPS,
        },
        label="calibrator evaluation",
    )
    require_exact_grid(
        overall,
        domains={
            "method": CALIBRATOR_METHODS,
            "window_id": WINDOW_IDS,
            "taxonomy_groups": (CANONICAL_GROUPS,),
            "role": ("primary_oot",),
            "conformal_group": (-1,),
        },
        label="calibrator overall evaluation",
    )
    require_finite(
        evaluation,
        _numeric_columns_except(
            evaluation,
            ("venn_multiprobability_gap_mean", "venn_multiprobability_gap_q50"),
        ),
        label="calibrator evaluation",
    )
    if len(evaluation) != 192 or len(overall) != 32:
        raise RuntimeError("Calibrator evaluation must contain 192 cells and 32 overalls.")
    _require_venn_gap_contract(
        evaluation,
        columns=(
            "venn_multiprobability_gap_mean",
            "venn_multiprobability_gap_q50",
        ),
        label="calibrator evaluation",
    )
    _require_set_partition(evaluation, label="calibrator evaluation")
    if (
        not evaluation["rows"].eq(evaluation["candidate_rows"]).all()
        or not (
            evaluation["candidate_rows"]
            - evaluation["resolved_rows"]
            - evaluation["unresolved_rows"]
        )
        .eq(0)
        .all()
        or not evaluation.loc[
            :,
            (
                "coverage_resolved",
                "coverage_lower",
                "coverage_upper",
                "coverage_resolved_y0",
                "coverage_resolved_y1",
            ),
        ]
        .apply(lambda column: column.between(0.0, 1.0))
        .all()
        .all()
        or not (evaluation["coverage_lower"] <= evaluation["coverage_resolved"]).all()
        or not (evaluation["coverage_resolved"] <= evaluation["coverage_upper"]).all()
        or not evaluation["coverage_upper_below_nominal"]
        .eq(evaluation["coverage_upper"].lt(_NOMINAL_COVERAGE))
        .all()
    ):
        raise RuntimeError("Calibrator evaluation census, bounds, or nominal flags changed.")

    expected_overall = evaluation.loc[evaluation["conformal_group"].eq(-1)]
    require_exact_frame(
        overall,
        expected_overall,
        keys=("method", "window_id", "conformal_group"),
        label="calibrator persisted overall subset",
    )
    geometry_primary = geometry.loc[geometry["role"].eq("primary_oot")]
    common_columns = tuple(column for column in _GEOMETRY_COLUMNS if column in evaluation)
    require_exact_frame(
        evaluation.loc[:, common_columns],
        geometry_primary.loc[:, common_columns],
        keys=("method", "window_id", "conformal_group"),
        label="calibrator Phase-A/Phase-B primary-OOT geometry",
    )

    for _, block in evaluation.groupby(
        ["method", "window_id"],
        observed=True,
        sort=False,
    ):
        total = block.loc[block["conformal_group"].eq(-1)].iloc[0]
        strata = block.loc[block["conformal_group"].ge(0)]
        for column in (
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            *_SET_COUNT_COLUMNS,
        ):
            if total[column] != strata[column].sum():
                raise RuntimeError("Calibrator evaluation overall/stratum census changed.")

    recipe_lookup = recipe_audit.set_index(["method", "window_id", "conformal_group"])
    strata = evaluation.loc[evaluation["conformal_group"].ge(0)]
    for row in strata.itertuples(index=False):
        recipe = recipe_lookup.loc[(str(row.method), str(row.window_id), int(row.conformal_group))]
        if int(row.fit_rows) != int(recipe["fit_rows"]) or float(
            row.fit_residual_quantile
        ) != float(recipe["residual_quantile"]):
            raise RuntimeError("Calibrator evaluation no longer uses the frozen recipes.")

    counts = _mapping(summary, "counts", label="calibrator summary")
    expected_counts = {
        "methods": 4,
        "windows": 8,
        "scopes_per_method_window": 6,
        "evaluation_cells": 192,
        "overall_cells": 32,
        "pairwise_cells": 288,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
        "resolved_y0": 307842,
        "resolved_y1": 56972,
    }
    if dict(counts) != expected_counts:
        raise RuntimeError("Calibrator evaluation summary census changed.")
    if counts["resolved_y0"] + counts["resolved_y1"] != counts["resolved_rows"]:
        raise RuntimeError("Calibrator resolved-label partition does not close.")
    census = overall[["candidate_rows", "resolved_rows", "unresolved_rows"]].drop_duplicates()
    if len(census) != 1 or census.iloc[0].to_dict() != {
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
    }:
        raise RuntimeError("Calibrator overall candidate census changed.")


def _validate_pairwise(
    pairwise: pd.DataFrame,
    evaluation: pd.DataFrame,
) -> None:
    _require_exact_columns(pairwise, _PAIRWISE_COLUMNS, label="calibrator pairwise evidence")
    require_finite(
        pairwise,
        (
            "taxonomy_groups",
            "conformal_group",
            "candidate_rows",
            "resolved_rows",
            "unresolved_rows",
            "coverage_difference_resolved",
            "coverage_difference_lower",
            "coverage_difference_upper",
        ),
        label="calibrator pairwise evidence",
    )
    expected = {
        (method_a, method_b, window_id, CANONICAL_GROUPS, "primary_oot", group)
        for method_a, method_b in unordered_method_pairs()
        for window_id in WINDOW_IDS
        for group in _GROUPS
    }
    actual = set(
        pairwise.loc[
            :,
            (
                "method_a",
                "method_b",
                "window_id",
                "taxonomy_groups",
                "role",
                "conformal_group",
            ),
        ].itertuples(index=False, name=None)
    )
    if (
        len(pairwise) != 288
        or actual != expected
        or pairwise.duplicated(["method_a", "method_b", "window_id", "conformal_group"]).any()
        or not pairwise["shared_loanwise_completion"].eq(True).all()
        or not (
            pairwise["candidate_rows"] - pairwise["resolved_rows"] - pairwise["unresolved_rows"]
        )
        .eq(0)
        .all()
        or not pairwise.loc[
            :,
            (
                "coverage_difference_resolved",
                "coverage_difference_lower",
                "coverage_difference_upper",
            ),
        ]
        .apply(lambda column: column.between(-1.0, 1.0))
        .all()
        .all()
        or not (
            pairwise["coverage_difference_lower"] <= pairwise["coverage_difference_resolved"]
        ).all()
        or not (
            pairwise["coverage_difference_resolved"] <= pairwise["coverage_difference_upper"]
        ).all()
    ):
        raise RuntimeError("Calibrator pairwise grid, census, or sharp bounds changed.")

    coverage = evaluation.set_index(["method", "window_id", "conformal_group"])
    for row in pairwise.to_dict(orient="records"):
        key_a = (str(row["method_a"]), str(row["window_id"]), int(row["conformal_group"]))
        key_b = (str(row["method_b"]), str(row["window_id"]), int(row["conformal_group"]))
        cell_a = coverage.loc[key_a]
        cell_b = coverage.loc[key_b]
        expected_difference = float(cell_a["coverage_resolved"]) - float(
            cell_b["coverage_resolved"]
        )
        if (
            not np.isclose(
                float(row["coverage_difference_resolved"]),
                expected_difference,
                rtol=0.0,
                atol=2.5e-16,
            )
            or int(row["candidate_rows"]) != int(cell_a["candidate_rows"])
            or int(row["resolved_rows"]) != int(cell_a["resolved_rows"])
            or int(row["unresolved_rows"]) != int(cell_a["unresolved_rows"])
            or not cell_a[["candidate_rows", "resolved_rows", "unresolved_rows"]].equals(
                cell_b[["candidate_rows", "resolved_rows", "unresolved_rows"]]
            )
        ):
            raise RuntimeError("Calibrator pairwise evidence does not reconcile to cells.")


def _validate_reconciliation(
    frame: pd.DataFrame,
    *,
    summary: Mapping[str, Any],
) -> None:
    _require_exact_columns(
        frame,
        _RECONCILIATION_COLUMNS,
        label="calibrator Platt/V5 reconciliation",
    )
    require_exact_grid(
        frame,
        domains={"window_id": WINDOW_IDS, "conformal_group": _GROUPS},
        label="calibrator Platt/V5 reconciliation",
    )
    require_finite(
        frame,
        _RECONCILIATION_DIFFERENCE_COLUMNS,
        label="calibrator Platt/V5 reconciliation",
    )
    gates = _mapping(summary, "gates", label="calibrator summary")
    tolerance = gates.get("platt_v5_tolerance")
    if not isinstance(tolerance, float):
        raise RuntimeError("Calibrator Platt/V5 tolerance type changed.")
    maximum = float(frame.loc[:, _RECONCILIATION_DIFFERENCE_COLUMNS].abs().max().max())
    if (
        len(frame) != 48
        or tolerance != 1.0e-12
        or maximum != gates.get("platt_v5_max_abs_difference")
        or maximum > float(tolerance)
    ):
        raise RuntimeError("Calibrator Platt/V5 reconciliation gate changed.")


def _validate_boundaries(
    *,
    freeze: Mapping[str, Any],
    summary: Mapping[str, Any],
    evaluation: pd.DataFrame,
    overall: pd.DataFrame,
    pairwise: pd.DataFrame,
) -> dict[str, Any]:
    design = _mapping(freeze, "design", label="calibrator freeze")
    if (
        tuple(design.get("methods", ())) != CALIBRATOR_METHODS
        or tuple(design.get("window_ids", ())) != WINDOW_IDS
        or design.get("taxonomy_groups") != CANONICAL_GROUPS
        or design.get("alpha") != 0.10
        or design.get("calibrator_fit_rows") != 14077
        or design.get("score_rows") != 640543
        or design.get("recipe_cells") != 160
        or design.get("geometry_cells") != 960
    ):
        raise RuntimeError("Calibrator frozen design changed.")
    freeze_gates = _mapping(freeze, "gates", label="calibrator freeze")
    if (
        freeze_gates.get("platt_roundtrip_tolerance") != 5.0e-14
        or float(freeze_gates.get("platt_roundtrip_max_abs_difference", np.inf)) > 5.0e-14
        or freeze_gates.get("q_raw_expit_margin_max_abs_difference") != 0.0
        or freeze_gates.get("full_panel_common_taxonomy_assignment_changes") != 0
        or freeze_gates.get("platt_v4_recipe_float_tolerance") != 1.0e-12
        or freeze_gates.get("platt_v4_recipe_integer_fields_exact") is not True
        or freeze_gates.get("platt_v4_recipe_max_residual_quantile_difference") != 0.0
        or freeze_gates.get("venn_abers_standard_p_prime_verified") is not True
    ):
        raise RuntimeError("Calibrator outcome-free scientific gates changed.")
    information = _mapping(freeze, "information_contract", label="calibrator freeze")
    expected_information = {
        "retrospective_archive_previously_inspected": True,
        "raw_archive_physically_read_during_phase_a": True,
        "primary_oot_status_values_may_be_read_in_underlying_csv_chunks": True,
        "primary_oot_outcomes_retained_or_used": False,
        "primary_oot_outcomes_passed_to_calibrator_or_recipe": False,
        "only_2011_probability_calibration_rows_retained_for_calibrator_fit": True,
        "learner_calibrator_window_or_result_selected": False,
        "portfolio_optimization_run": False,
    }
    if dict(information) != expected_information:
        raise RuntimeError("Calibrator Phase-A information boundary changed.")

    gates = _mapping(summary, "gates", label="calibrator summary")
    if (
        gates.get("phase_a_vector_hash_replay_exact") is not True
        or gates.get("phase_a_source_is_direct_child_of_protocol") is not True
        or gates.get("annotated_tag_chain_verified") is not True
        or gates.get("complete_grid") is not True
        or gates.get("all_methods_and_windows_reported") is not True
    ):
        raise RuntimeError("Calibrator evaluation completeness gates changed.")
    boundary = _mapping(summary, "result_boundary", label="calibrator summary")
    if (
        boundary.get("nominal_coverage") != _NOMINAL_COVERAGE
        or boundary.get("overall_cells_with_coverage_upper_below_nominal") != 18
        or boundary.get("overall_cells_with_coverage_upper_at_or_above_nominal") != 14
        or boundary.get("all_overall_cells_below_nominal") is not False
        or boundary.get("result_state") != _RESULT_STATE
        or boundary.get("no_theorem_refutation_from_archive") is not True
    ):
        raise RuntimeError("Calibrator result boundary changed.")
    identification = _mapping(summary, "identification", label="calibrator summary")
    interpretation = _mapping(summary, "interpretation", label="calibrator summary")
    if (
        identification.get("coverage_bounds") != "sharp_loanwise_binary_completion_bounds"
        or identification.get("pairwise_differences")
        != "sharp_shared_loanwise_binary_completion_bounds"
        or identification.get("sampling_confidence_intervals") is not False
        or identification.get("missing_at_random_assumption") is not False
        or interpretation.get("retrospective_sensitivity") is not True
        or interpretation.get("preregistered") is not False
        or interpretation.get("closed_calibrator_family") is not True
        or interpretation.get("common_q_raw_taxonomy") is not True
        or interpretation.get("learner_calibrator_window_or_result_selected") is not False
        or interpretation.get("all_methods_windows_and_strata_reported") is not True
        or interpretation.get("pairwise_completion_is_shared_loanwise") is not True
        or interpretation.get("if_any_upper_at_or_above_nominal") != _RESULT_STATE
        or interpretation.get("venn_abers_p_prime_is_scalarization") is not True
        or interpretation.get("venn_abers_multiprobability_guarantee_transported_to_scalarization")
        is not False
        or interpretation.get("latent_pd_interval") is not False
        or interpretation.get("policy_claim") is not False
        or interpretation.get("portfolio_optimization") is not False
        or interpretation.get("selected_set_guarantee") is not False
        or interpretation.get("funded_set_guarantee") is not False
    ):
        raise RuntimeError("Calibrator identification or interpretation boundary changed.")

    require_finite(
        overall,
        (
            "coverage_lower",
            "coverage_upper",
            "coverage_resolved",
            "average_set_size",
        ),
        label="calibrator method-level findings",
    )
    below_by_method: dict[str, int] = {}
    at_or_above_by_method: dict[str, int] = {}
    overall_method_summaries: dict[str, dict[str, int | float]] = {}
    for method in CALIBRATOR_METHODS:
        cells = overall.loc[overall["method"].eq(method)]
        if len(cells) != len(WINDOW_IDS):
            raise RuntimeError("Calibrator method-level findings grid changed.")
        below = int(cells["coverage_upper_below_nominal"].sum())
        below_by_method[method] = below
        at_or_above_by_method[method] = len(cells) - below
        overall_method_summaries[method] = {
            "upper_below_nominal": below,
            "coverage_lower_min": float(cells["coverage_lower"].min()),
            "coverage_upper_max": float(cells["coverage_upper"].max()),
            "coverage_resolved_min": float(cells["coverage_resolved"].min()),
            "coverage_resolved_max": float(cells["coverage_resolved"].max()),
            "average_set_size_min": float(cells["average_set_size"].min()),
            "average_set_size_max": float(cells["average_set_size"].max()),
        }
    if below_by_method != {
        "platt": 8,
        "isotonic": 1,
        "beta": 8,
        "venn_abers": 1,
    }:
        raise RuntimeError("Calibrator method-level nominal-boundary census changed.")
    below_total = int(overall["coverage_upper_below_nominal"].sum())
    if below_total != 18 or len(overall) - below_total != 14:
        raise RuntimeError("Calibrator overall nominal-boundary census changed.")

    equality_keys = ["window_id", "conformal_group"]
    platt = evaluation.loc[evaluation["method"].eq("platt")].set_index(equality_keys).sort_index()
    beta = evaluation.loc[evaluation["method"].eq("beta")].set_index(equality_keys).sort_index()
    if (
        len(platt) != 48
        or len(beta) != 48
        or not platt.index.equals(beta.index)
        or not platt.loc[:, _PLATT_BETA_AGGREGATE_EQUALITY_COLUMNS].equals(
            beta.loc[:, _PLATT_BETA_AGGREGATE_EQUALITY_COLUMNS]
        )
    ):
        raise RuntimeError(
            "Calibrator Platt/Beta aggregate set geometry or coverage equality changed."
        )

    platt_overall = overall.loc[overall["method"].eq("platt")].set_index("window_id").sort_index()
    alternative_set_geometry: dict[str, dict[str, int]] = {}
    for method in ("isotonic", "venn_abers"):
        alternative = overall.loc[overall["method"].eq(method)].set_index("window_id").sort_index()
        if len(alternative) != 8 or not alternative.index.equals(platt_overall.index):
            raise RuntimeError("Calibrator alternative overall set-geometry grid changed.")
        zero_empty = int(alternative["set_empty_count"].eq(0).sum())
        more_both = int(alternative["set_both_count"].gt(platt_overall["set_both_count"]).sum())
        if zero_empty != 8 or more_both != 8:
            raise RuntimeError("Calibrator alternative overall set-geometry co-movement changed.")
        alternative_set_geometry[method] = {
            "rows": 8,
            "zero_empty_set_cells": zero_empty,
            "two_label_count_greater_than_platt_cells": more_both,
        }

    require_finite(
        pairwise,
        (
            "coverage_difference_lower",
            "coverage_difference_resolved",
            "coverage_difference_upper",
        ),
        label="calibrator pairwise findings",
    )
    pairwise_overall = pairwise.loc[pairwise["conformal_group"].eq(-1)]
    expected_pairs = tuple(unordered_method_pairs())
    actual_pairs = set(
        pairwise_overall.loc[:, ("method_a", "method_b")].itertuples(
            index=False,
            name=None,
        )
    )
    if len(pairwise_overall) != 8 * len(expected_pairs) or actual_pairs != set(expected_pairs):
        raise RuntimeError("Calibrator pairwise-overall findings grid changed.")

    pairwise_overall_summaries: dict[str, dict[str, int | float | bool]] = {}
    strict_positive_pairs: set[str] = set()
    for method_a in CALIBRATOR_METHODS:
        for method_b in CALIBRATOR_METHODS:
            if method_a == method_b:
                continue
            cells = pairwise_overall.loc[
                pairwise_overall["method_a"].eq(method_a)
                & pairwise_overall["method_b"].eq(method_b)
            ]
            if len(cells) == len(WINDOW_IDS):
                lower = cells["coverage_difference_lower"]
                upper = cells["coverage_difference_upper"]
            else:
                cells = pairwise_overall.loc[
                    pairwise_overall["method_a"].eq(method_b)
                    & pairwise_overall["method_b"].eq(method_a)
                ]
                lower = -cells["coverage_difference_upper"]
                upper = -cells["coverage_difference_lower"]
            if len(cells) != len(WINDOW_IDS):
                raise RuntimeError("Calibrator oriented pairwise findings grid changed.")
            key = f"{method_a}_minus_{method_b}"
            all_bounds_strictly_positive = bool(lower.gt(0.0).all() and upper.gt(0.0).all())
            if all_bounds_strictly_positive:
                strict_positive_pairs.add(key)
            lower_min = float(lower.min())
            upper_max = float(upper.max())
            pairwise_overall_summaries[key] = {
                "rows": int(len(cells)),
                "lower_min": 0.0 if lower_min == 0.0 else lower_min,
                "upper_max": 0.0 if upper_max == 0.0 else upper_max,
                "all_bounds_strictly_positive": all_bounds_strictly_positive,
            }
    if strict_positive_pairs != {
        "isotonic_minus_platt",
        "isotonic_minus_beta",
        "isotonic_minus_venn_abers",
        "venn_abers_minus_platt",
        "venn_abers_minus_beta",
    }:
        raise RuntimeError("Calibrator 8/8 strict-positive pairwise boundary changed.")

    platt_beta = pairwise.loc[pairwise["method_a"].eq("platt") & pairwise["method_b"].eq("beta")]
    zero_bound_cells = int(
        (
            platt_beta["coverage_difference_lower"].eq(0.0)
            & platt_beta["coverage_difference_upper"].eq(0.0)
        ).sum()
    )
    if (
        len(platt_beta) != 48
        or zero_bound_cells != 48
        or not platt_beta["coverage_difference_resolved"].eq(0.0).all()
    ):
        raise RuntimeError("Calibrator Platt-minus-beta [0,0] boundary changed.")

    counts = _mapping(summary, "counts", label="calibrator summary")
    return {
        "result_state": _RESULT_STATE,
        "nominal_coverage": _NOMINAL_COVERAGE,
        "overall_cells_total": 32,
        "overall_cells_below_nominal": 18,
        "overall_cells_at_or_above_nominal": 14,
        "overall_cells_below_nominal_by_method": below_by_method,
        "overall_cells_at_or_above_nominal_by_method": at_or_above_by_method,
        "overall_method_summaries": overall_method_summaries,
        "platt_beta_aggregate_equality_cells": 48,
        "alternative_overall_set_geometry_census": alternative_set_geometry,
        "pairwise_overall_summaries": pairwise_overall_summaries,
        "platt_beta_zero_bound_cells": zero_bound_cells,
        "evaluation_row_count": 192,
        "overall_row_count": 32,
        "pairwise_row_count": 288,
        "platt_v5_reconciliation_row_count": 48,
        "candidate_count": int(counts["candidate_rows"]),
        "resolved_count": int(counts["resolved_rows"]),
        "unresolved_count": int(counts["unresolved_rows"]),
        "resolved_y0_count": int(counts["resolved_y0"]),
        "resolved_y1_count": int(counts["resolved_y1"]),
        "all_completeness_gates_passed": True,
        "platt_v5_reconciliation_passed": True,
        "retrospective_nonconfirmatory": True,
        "selected_calibrator_or_result": False,
        "portfolio_optimization_run": False,
    }


def load_calibrator_sensitivity_evidence(
    registered: Mapping[str, Path],
    identities: Mapping[str, Any],
    *,
    repo_root: Path,
) -> CalibratorSensitivityEvidence:
    """Load the active P/A/B/C calibrator lineage and fail closed on drift."""
    root = repo_root.resolve()
    _require_registered_paths(registered, repo_root=root)
    _require_git_lineage(identities, repo_root=root)

    freeze = _load_json_object(
        registered["calibrator_sensitivity_source_freeze"],
        label="calibrator source freeze",
    )
    source_receipt = _load_json_object(
        registered["calibrator_sensitivity_source_receipt"],
        label="calibrator source receipt",
    )
    summary = _load_json_object(
        registered["calibrator_sensitivity_evaluation_summary"],
        label="calibrator evaluation summary",
    )
    evaluation_receipt = _load_json_object(
        registered["calibrator_sensitivity_evaluation_receipt"],
        label="calibrator evaluation receipt",
    )
    _require_identity(
        freeze,
        run_tag=_SOURCE_RUN_TAG,
        protocol_tag=_PROTOCOL_TAG,
        protocol_commit=_PROTOCOL_COMMIT,
        status=("calibrator_maps_and_common_taxonomy_frozen_before_primary_oot_outcome_evaluation"),
        label="calibrator source freeze",
    )
    _require_identity(
        source_receipt,
        run_tag=_SOURCE_RUN_TAG,
        protocol_tag=_PROTOCOL_TAG,
        protocol_commit=_PROTOCOL_COMMIT,
        status="complete_calibrator_sensitivity_phase_a_execution_receipt",
        label="calibrator source receipt",
    )
    _require_identity(
        summary,
        run_tag=_EVALUATION_RUN_TAG,
        protocol_tag=_EVALUATION_PROTOCOL_TAG,
        protocol_commit=_EVALUATION_PROTOCOL_COMMIT,
        status="complete_retrospective_calibrator_sensitivity_evaluation",
        label="calibrator evaluation summary",
    )
    _require_identity(
        evaluation_receipt,
        run_tag=_EVALUATION_RUN_TAG,
        protocol_tag=_EVALUATION_PROTOCOL_TAG,
        protocol_commit=_EVALUATION_PROTOCOL_COMMIT,
        status="complete_calibrator_sensitivity_phase_b_execution_receipt",
        label="calibrator evaluation receipt",
    )
    for label, payload in (
        ("calibrator source freeze", freeze),
        ("calibrator source receipt", source_receipt),
        ("calibrator evaluation summary", summary),
        ("calibrator evaluation receipt", evaluation_receipt),
    ):
        _require_clean_execution(payload, label=label)
        environment = _mapping(payload, "environment", label=label)
        if environment.get("uv_lock_sha256") != _LOCK_SHA256:
            raise RuntimeError(f"{label} scientific environment lock changed.")

    _require_implementation_provenance(
        freeze,
        commit=_PROTOCOL_COMMIT,
        repo_root=root,
        label="calibrator source freeze",
    )
    _require_implementation_provenance(
        summary,
        commit=_EVALUATION_PROTOCOL_COMMIT,
        repo_root=root,
        label="calibrator evaluation summary",
    )
    _require_artifact_descriptors(
        freeze=freeze,
        source_receipt=source_receipt,
        summary=summary,
        evaluation_receipt=evaluation_receipt,
        registered=registered,
        repo_root=root,
    )

    taxonomy = _load_json_object(
        registered["calibrator_sensitivity_taxonomy"],
        label="calibrator common taxonomy",
    )
    recipes = _load_json_object(
        registered["calibrator_sensitivity_residual_recipes"],
        label="calibrator residual recipes",
    )
    frames = {
        "calibration_fit_diagnostics": pd.read_parquet(
            registered["calibrator_sensitivity_calibration_fit_diagnostics"]
        ),
        "recipe_audit": pd.read_parquet(registered["calibrator_sensitivity_recipe_audit"]),
        "outcome_free_geometry": pd.read_parquet(
            registered["calibrator_sensitivity_outcome_free_geometry"]
        ),
        "evaluation": pd.read_parquet(registered["calibrator_sensitivity_evaluation"]),
        "overall": pd.read_parquet(registered["calibrator_sensitivity_overall"]),
        "pairwise": pd.read_parquet(registered["calibrator_sensitivity_pairwise"]),
        "platt_v5_reconciliation": pd.read_parquet(
            registered["calibrator_sensitivity_platt_v5_reconciliation"]
        ),
    }
    _validate_fit_diagnostics(frames["calibration_fit_diagnostics"], freeze=freeze)
    _validate_taxonomy_and_recipes(taxonomy, recipes, frames["recipe_audit"])
    _validate_geometry(frames["outcome_free_geometry"])
    _validate_evaluation(
        frames["evaluation"],
        frames["overall"],
        frames["outcome_free_geometry"],
        frames["recipe_audit"],
        summary=summary,
    )
    _validate_pairwise(frames["pairwise"], frames["evaluation"])
    _validate_reconciliation(frames["platt_v5_reconciliation"], summary=summary)
    findings = _validate_boundaries(
        freeze=freeze,
        summary=summary,
        evaluation=frames["evaluation"],
        overall=frames["overall"],
        pairwise=frames["pairwise"],
    )
    return CalibratorSensitivityEvidence(
        freeze=freeze,
        source_receipt=source_receipt,
        summary=summary,
        evaluation_receipt=evaluation_receipt,
        taxonomy=taxonomy,
        frames=frames,
        findings=findings,
    )


def _ordered_table(
    frame: pd.DataFrame,
    *,
    method_columns: Sequence[str],
) -> pd.DataFrame:
    table = frame.copy()
    order_columns: list[str] = []
    for column in method_columns:
        order_name = f"_{column}_order"
        table[order_name] = table[column].map(
            {method: index for index, method in enumerate(CALIBRATOR_METHODS)}
        )
        order_columns.append(order_name)
    if "window_id" in table:
        table["_window_order"] = table["window_id"].map(
            {window: index for index, window in enumerate(WINDOW_IDS)}
        )
        order_columns.append("_window_order")
    if "conformal_group" in table:
        order_columns.append("conformal_group")
    table = table.sort_values(order_columns, kind="stable").drop(
        columns=[column for column in order_columns if column.startswith("_")]
    )
    return table.reset_index(drop=True)


def _json_finite_table(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    table = frame.copy()
    for column in table.columns:
        if not is_float_dtype(table[column].dtype):
            continue
        values = table[column].to_numpy(dtype=float)
        if bool(np.isinf(values).any()):
            raise RuntimeError(f"{label} contains an infinite publication value.")
        if bool(np.isnan(values).any()):
            table[column] = table[column].astype(object)
            table.loc[table[column].isna(), column] = None
    return table


def calibrator_method_publication_table(
    evidence: CalibratorSensitivityEvidence,
) -> pd.DataFrame:
    """Return four same-sample fit diagnostics; non-applicable VA gaps are null."""
    table = _ordered_table(
        evidence.frames["calibration_fit_diagnostics"],
        method_columns=("method",),
    )
    return _json_finite_table(table, label="calibrator method publication table")


def calibrator_overall_publication_table(
    evidence: CalibratorSensitivityEvidence,
) -> pd.DataFrame:
    """Return all 192 method/window/ALL-plus-stratum cells, not only 32 overalls."""
    table = _ordered_table(
        evidence.frames["evaluation"],
        method_columns=("method",),
    )
    if tuple(table.columns) != _EVALUATION_COLUMNS or len(table) != 192:
        raise RuntimeError("Calibrator full-cell publication table changed.")
    return _json_finite_table(table, label="calibrator full-cell publication table")


def calibrator_pairwise_publication_table(
    evidence: CalibratorSensitivityEvidence,
) -> pd.DataFrame:
    """Return all 288 shared-completion coverage-difference cells."""
    table = _ordered_table(
        evidence.frames["pairwise"],
        method_columns=("method_a", "method_b"),
    )
    if tuple(table.columns) != _PAIRWISE_COLUMNS or len(table) != 288:
        raise RuntimeError("Calibrator pairwise publication table changed.")
    return _json_finite_table(table, label="calibrator pairwise publication table")


__all__ = [
    "CalibratorSensitivityEvidence",
    "calibrator_method_publication_table",
    "calibrator_overall_publication_table",
    "calibrator_pairwise_publication_table",
    "load_calibrator_sensitivity_evidence",
]
