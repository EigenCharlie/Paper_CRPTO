"""Fail-closed paper-facing loader for the binary phase census.

The loader verifies the immutable Git-native protocol/artifact lineage, the
three registered outputs, and every cell-level identity before exposing the
complete 200-row table.  Its findings distinguish a condition that is not
applicable from a condition that failed where applicable.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from pathlib import Path, PurePosixPath
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.binary_phase_census import CELL_OUTPUT_COLUMNS
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import dataframe_schema

_UV_LOCK_SHA256 = "41a982834374d96995457704ff291d2f6dc4a9ae9d9809cd3dc0a21b23b25367"
_TRANSPORT = "git_force_tracked_direct_child_commit"
_RUN_TAG = "ijds-binary-phase-census-2026-08-01-v1"
_PROTOCOL_TAG = "protocol/ijds-binary-phase-census-2026-08-01-v1"
_PROTOCOL_COMMIT = "8f3219ee2591f63a0bbf17af49b004e4cec7351f"
_ARTIFACT_TAG = "artifacts/ijds-binary-phase-census-2026-08-01-v1"
_ARTIFACT_COMMIT = "17b3614c18e755fd755839e3bab815cdec2dbc32"
_PAPER_ROLE = "complete_retrospective_outcome_free_binary_phase_census"
_SCHEMA_VERSION = "2026-08-01.1"
_SUMMARY_STATUS = "complete_hash_bound_binary_phase_census"
_RECEIPT_STATUS = "complete_protocol_tagged_execution_receipt"

_LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
_WINDOWS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
_GROUPS = 5
_EXPECTED_CELLS = 200
_EXPECTED_CELLS_PER_GROUP = 40
_ALPHA = 0.10
_TOLERANCE = 1.0e-15

_CONFIG_PATH = "configs/experiments/ijds_binary_phase_census_2026-08-01_v1.yaml"
_PROTOCOL_PATH = "docs/research/ijds_binary_phase_census_v1_protocol_2026-08-01.md"
_RUNNER_PATH = "scripts/experiments/run_ijds_binary_phase_census_v1.py"
_IMPLEMENTATION_PATH = "src/ijds_audit/binary_phase_census.py"
_TEST_PATH = "tests/test_ijds_audit/test_binary_phase_census.py"
_TABLE_PATH = (
    "data/processed/experiments/ijds_audit/"
    "ijds-binary-phase-census-2026-08-01-v1/binary_phase_census.csv"
)
_SUMMARY_PATH = (
    "models/experiments/ijds_audit/"
    "ijds-binary-phase-census-2026-08-01-v1/binary_phase_census_summary.json"
)
_RECEIPT_PATH = (
    "models/experiments/ijds_audit/ijds-binary-phase-census-2026-08-01-v1/execution_receipt.json"
)
_ARTIFACT_PATHS = (_TABLE_PATH, _SUMMARY_PATH, _RECEIPT_PATH)

_REGISTERED_PATHS = {
    "binary_phase_census_config": _CONFIG_PATH,
    "binary_phase_census_protocol": _PROTOCOL_PATH,
    "binary_phase_census_runner": _RUNNER_PATH,
    "binary_phase_census_implementation": _IMPLEMENTATION_PATH,
    "binary_phase_census_table": _TABLE_PATH,
    "binary_phase_census_summary": _SUMMARY_PATH,
    "binary_phase_census_receipt": _RECEIPT_PATH,
}

_IMPLEMENTATION_PROVENANCE_PATHS = {
    _CONFIG_PATH,
    _PROTOCOL_PATH,
    _IMPLEMENTATION_PATH,
    _RUNNER_PATH,
    _TEST_PATH,
    "src/utils/isolated_experiment.py",
    "src/utils/pipeline_runtime.py",
    "pyproject.toml",
    "uv.lock",
}

_EXPECTED_OUTPUT = {
    "data_root": "data/processed/experiments/ijds_audit",
    "model_root": "models/experiments/ijds_audit",
    "immutability": "hard_no_overwrite_choose_fresh_run_tag",
    "cell_table": "binary_phase_census.csv",
    "summary": "binary_phase_census_summary.json",
    "execution_receipt": "execution_receipt.json",
}
_EXPECTED_CLAIM_BOUNDARY = {
    "retrospective": True,
    "preregistered": False,
    "confirmatory": False,
    "complete_grid_only": True,
    "complete_ordered_stratum_summary": True,
    "learner_window_permutation_symmetric_summary": True,
    "no_stratum_omission_or_selection": True,
    "no_named_path_or_winner": True,
    "no_evaluation_endpoint_or_target_join": True,
    "no_coverage_transport_or_validity_claim": True,
    "no_optimization_policy_or_funded_set_claim": True,
    "no_unconditional_phase_margin_interpretation": True,
    "no_automatic_paper_or_claim_promotion": True,
}
_EXPECTED_SOURCE_READ_CONTRACT = {
    "hash_bound_source_count": 4,
    "unparsed_provenance_witness_count": 2,
    "allowlisted_scientific_table_count": 2,
    "evaluation_endpoint_tables_read": 0,
}
_EXPECTED_REPORTING_CONTRACT = {
    "complete_identifier_bearing_cell_table": True,
    "learner_window_summary_permutation_symmetric": True,
    "complete_ordered_stratum_summary": True,
    "all_strata_reported_without_selection": True,
    "learner_window_identifier_breakdowns": False,
    "learner_window_identifier_values_in_summary": False,
    "cell_extrema_in_summary": False,
}

_STRING_COLUMNS = (
    "learner",
    "window_id",
    "expected_threshold_source_branch",
    "threshold_source_branch",
)
_FLOAT_COLUMNS = (
    "alpha",
    "fit_default_prevalence",
    "frozen_threshold",
    "recomputed_threshold",
    "threshold_gap",
    "recomputed_score_min",
    "recomputed_score_max",
    "frozen_score_min",
    "frozen_score_max",
    "fit_score_max_nondefault",
    "fit_score_max_default",
)
_INTEGER_COLUMNS = (
    "taxonomy_groups",
    "conformal_group",
    "fit_rows",
    "fit_defaults",
    "fit_nondefaults",
    "finite_sample_rank",
    "boundary_count",
    "boundary_closed_form",
    "phase_margin",
    "frozen_fit_rows",
    "frozen_finite_sample_rank",
    "recomputed_residual_below_threshold",
    "recomputed_residual_equal_threshold",
    "recomputed_residual_above_threshold",
    "frozen_residual_below_threshold",
    "frozen_residual_equal_threshold",
    "frozen_residual_above_threshold",
    "count_nondefault_score_below_half",
    "count_default_score_above_half",
)
_BOOLEAN_COLUMNS = tuple(
    column
    for column in CELL_OUTPUT_COLUMNS
    if column not in {*_STRING_COLUMNS, *_FLOAT_COLUMNS, *_INTEGER_COLUMNS}
)
_FORBIDDEN_TABLE_TOKENS = (
    "target",
    "outcome",
    "coverage",
    "selected",
    "selection",
    "optim",
    "allocation",
    "funded",
    "policy",
    "endpoint",
    "resolved",
    "unresolved",
)


@dataclass(frozen=True)
class BinaryPhaseCensusEvidence:
    """Verified paper-facing phase-census evidence."""

    summary: Mapping[str, Any]
    receipt: Mapping[str, Any]
    cell_table: pd.DataFrame
    findings: Mapping[str, Any]


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object.")
    return payload


def _load_yaml_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a YAML mapping.")
    return cast(dict[str, Any], payload)


def _mapping(payload: Mapping[str, Any], key: str, *, label: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise TypeError(f"{label}.{key} must be a mapping.")
    return cast(Mapping[str, Any], value)


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
        raise RuntimeError(f"{label} tag {tag!r} is missing or lightweight.")
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
        raise RuntimeError(f"{label} changed {changed}, not the exact three-output path list.")
    for path in paths:
        _git_text(
            repo_root,
            ("cat-file", "-e", f"{commit}:{path}"),
            label=f"{label} blob {path}",
        )


def _require_registered_paths(registered: Mapping[str, Path], *, repo_root: Path) -> None:
    missing = sorted(set(_REGISTERED_PATHS).difference(registered))
    if missing:
        raise KeyError(f"Binary phase census registry keys are missing: {missing}.")
    root = repo_root.resolve()
    for name, relative in _REGISTERED_PATHS.items():
        actual = registered[name].resolve()
        expected = (root / relative).resolve()
        try:
            actual.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"Registered source {name!r} escapes the repository.") from exc
        if actual != expected:
            raise RuntimeError(f"Registered source {name!r} changed path.")


def _expected_identity() -> dict[str, Any]:
    return {
        "run_tag": _RUN_TAG,
        "protocol_tag": _PROTOCOL_TAG,
        "protocol_commit": _PROTOCOL_COMMIT,
        "scientific_uv_lock_sha256": _UV_LOCK_SHA256,
        "paper_role": _PAPER_ROLE,
        "dvc_tracked": False,
        "artifact_tag": _ARTIFACT_TAG,
        "artifact_commit": _ARTIFACT_COMMIT,
        "artifact_parent_commit": _PROTOCOL_COMMIT,
        "artifact_transport": _TRANSPORT,
        "artifact_paths": list(_ARTIFACT_PATHS),
    }


def _require_identity_and_transport(identity: Mapping[str, Any], *, repo_root: Path) -> None:
    expected = _expected_identity()
    if dict(identity) != expected:
        changed = {
            key: identity.get(key)
            for key in set(identity).union(expected)
            if identity.get(key) != expected.get(key)
        }
        raise RuntimeError(f"Binary phase census registry identity changed: {changed}.")
    _require_annotated_tag(
        _PROTOCOL_TAG,
        _PROTOCOL_COMMIT,
        repo_root=repo_root,
        label="binary phase census protocol",
    )
    _require_git_stage(
        tag=_ARTIFACT_TAG,
        commit=_ARTIFACT_COMMIT,
        parent=_PROTOCOL_COMMIT,
        paths=_ARTIFACT_PATHS,
        repo_root=repo_root,
        label="binary phase census artifact",
    )


def _exact_descriptor(raw: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "bytes", "sha256"}:
        raise TypeError(f"{label} must be an exact path/bytes/sha256 descriptor.")
    path = raw.get("path")
    size = raw.get("bytes")
    digest = raw.get("sha256")
    if (
        not isinstance(path, str)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
        or not isinstance(digest, str)
        or len(digest) != 64
    ):
        raise TypeError(f"{label} contains an invalid descriptor field.")
    return {"path": path, "bytes": size, "sha256": digest}


def _descriptor_path(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
    label: str,
    cache: dict[tuple[str, int, str], Path],
) -> Path:
    exact = _exact_descriptor(descriptor, label=label)
    key = (str(exact["path"]), int(exact["bytes"]), str(exact["sha256"]))
    if key in cache:
        return cache[key]
    pure = PurePosixPath(key[0])
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise RuntimeError(f"{label} descriptor path is not repository-relative canonical POSIX.")
    path = (repo_root / Path(*pure.parts)).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} descriptor escapes the repository.") from exc
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    if actual != exact:
        raise RuntimeError(f"{label} descriptor differs from the local artifact.")
    cache[key] = path
    return path


def _require_git_blob_descriptor(
    *,
    commit: str,
    descriptor: Mapping[str, Any],
    repo_root: Path,
    label: str,
) -> None:
    exact = _exact_descriptor(descriptor, label=label)
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{exact['path']}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} is absent from pinned commit {commit}.")
    if (
        len(result.stdout) != exact["bytes"]
        or hashlib.sha256(result.stdout).hexdigest() != exact["sha256"]
    ):
        raise RuntimeError(f"{label} descriptor differs from its pinned Git blob.")


def _registered_descriptor(
    registered: Mapping[str, Path], name: str, *, repo_root: Path
) -> dict[str, Any]:
    return relative_artifact_descriptor(registered[name], repo_root=repo_root)


def _require_registered_blobs(
    registered: Mapping[str, Path], *, repo_root: Path
) -> dict[str, dict[str, Any]]:
    descriptors: dict[str, dict[str, Any]] = {}
    protocol_keys = (
        "binary_phase_census_config",
        "binary_phase_census_protocol",
        "binary_phase_census_runner",
        "binary_phase_census_implementation",
    )
    artifact_keys = (
        "binary_phase_census_table",
        "binary_phase_census_summary",
        "binary_phase_census_receipt",
    )
    for name in protocol_keys:
        descriptor = _registered_descriptor(registered, name, repo_root=repo_root)
        _require_git_blob_descriptor(
            commit=_PROTOCOL_COMMIT,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"registered {name}",
        )
        descriptors[name] = descriptor
    for name in artifact_keys:
        descriptor = _registered_descriptor(registered, name, repo_root=repo_root)
        _require_git_blob_descriptor(
            commit=_ARTIFACT_COMMIT,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"registered {name}",
        )
        descriptors[name] = descriptor
    return descriptors


def _require_implementation_provenance(
    payload: Mapping[str, Any],
    *,
    registered_descriptors: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    cache: dict[tuple[str, int, str], Path],
    label: str,
) -> None:
    provenance = _mapping(payload, "implementation_provenance", label=label)
    if set(provenance) != {"source_files", "hash_algorithm"}:
        raise RuntimeError(f"{label} implementation provenance schema changed.")
    if provenance.get("hash_algorithm") != "sha256":
        raise RuntimeError(f"{label} implementation hash algorithm changed.")
    source_files = provenance.get("source_files")
    if (
        not isinstance(source_files, Mapping)
        or set(source_files) != _IMPLEMENTATION_PROVENANCE_PATHS
    ):
        raise RuntimeError(f"{label} implementation file inventory changed.")

    registered_by_path = {
        str(descriptor["path"]): descriptor
        for name, descriptor in registered_descriptors.items()
        if name
        in {
            "binary_phase_census_config",
            "binary_phase_census_protocol",
            "binary_phase_census_runner",
            "binary_phase_census_implementation",
        }
    }
    for relative, raw in source_files.items():
        if not isinstance(relative, str):
            raise TypeError(f"{label} implementation key must be text.")
        descriptor = _exact_descriptor(raw, label=f"{label} implementation {relative}")
        if descriptor["path"] != relative:
            raise RuntimeError(f"{label} implementation key and descriptor path disagree.")
        _require_git_blob_descriptor(
            commit=_PROTOCOL_COMMIT,
            descriptor=descriptor,
            repo_root=repo_root,
            label=f"{label} implementation {relative}",
        )
        registered_descriptor = registered_by_path.get(relative)
        if registered_descriptor is not None:
            if descriptor != registered_descriptor:
                raise RuntimeError(f"{label} registered implementation descriptor changed.")
            _descriptor_path(
                descriptor,
                repo_root=repo_root,
                label=f"{label} implementation {relative}",
                cache=cache,
            )


def _require_exact_keys(payload: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    if set(payload) != expected:
        raise RuntimeError(
            f"{label} keys changed; missing={sorted(expected.difference(payload))}, "
            f"extra={sorted(set(payload).difference(expected))}."
        )


def _validate_config(config: Mapping[str, Any]) -> None:
    expected_top = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_path",
        "protocol_tag",
        "artifact_tag",
        "source",
        "design",
        "execution_gate",
        "output",
        "claim_boundary",
        "stop_rules",
    }
    _require_exact_keys(config, expected_top, label="phase census config")
    if (
        config.get("schema_version") != _SCHEMA_VERSION
        or config.get("protocol_status") != "retrospectively_locked_before_execution"
        or config.get("run_tag") != _RUN_TAG
        or config.get("protocol_path") != _PROTOCOL_PATH
        or config.get("protocol_tag") != _PROTOCOL_TAG
        or config.get("artifact_tag") != _ARTIFACT_TAG
    ):
        raise RuntimeError("Phase census config identity changed.")

    design = _mapping(config, "design", label="phase census config")
    expected_design = {
        "alpha": _ALPHA,
        "taxonomy_groups": _GROUPS,
        "expected_cells": _EXPECTED_CELLS,
        "require_both_classes_nonempty": True,
        "require_uncapped_rank": True,
        "threshold_tolerance": _TOLERANCE,
        "learners": list(_LEARNERS),
        "window_ids": list(_WINDOWS),
    }
    if dict(design) != expected_design:
        raise RuntimeError("Phase census design changed.")
    if dict(_mapping(config, "output", label="phase census config")) != _EXPECTED_OUTPUT:
        raise RuntimeError("Phase census output contract changed.")
    if (
        dict(_mapping(config, "claim_boundary", label="phase census config"))
        != _EXPECTED_CLAIM_BOUNDARY
    ):
        raise RuntimeError("Phase census claim boundary changed.")

    execution_gate = _mapping(config, "execution_gate", label="phase census config")
    if set(execution_gate) != {
        "require_clean_worktree",
        "require_protocol_tag_at_head",
        "require_annotated_protocol_tag",
        "require_fresh_output_directories",
        "require_implementation_hash_stability",
    } or not all(value is True for value in execution_gate.values()):
        raise RuntimeError("Phase census execution gate changed.")
    stop_rules = _mapping(config, "stop_rules", label="phase census config")
    if not stop_rules or not all(value is True for value in stop_rules.values()):
        raise RuntimeError("Phase census stop rules were weakened.")

    source = _mapping(config, "source", label="phase census config")
    expected_roles = {
        "credit_control_freeze": "provenance_witness_unparsed",
        "residual_fit_audit": "scientific_table_allowlisted_columns",
        "exchangeability_summary": "provenance_witness_unparsed",
        "exchangeability_strata": "scientific_table_allowlisted_columns",
    }
    if set(source) != set(expected_roles):
        raise RuntimeError("Phase census four-source inventory changed.")
    for name, role in expected_roles.items():
        descriptor = source.get(name)
        if not isinstance(descriptor, Mapping) or set(descriptor) != {
            "path",
            "bytes",
            "sha256",
            "role",
        }:
            raise RuntimeError(f"Phase census source descriptor {name} changed schema.")
        _exact_descriptor(
            {key: descriptor[key] for key in ("path", "bytes", "sha256")},
            label=f"phase census source {name}",
        )
        if descriptor.get("role") != role:
            raise RuntimeError(f"Phase census source role changed for {name}.")


def _require_table_schema(frame: pd.DataFrame) -> None:
    forbidden = sorted(
        column
        for column in frame.columns
        if any(token in column.lower() for token in _FORBIDDEN_TABLE_TOKENS)
    )
    if forbidden:
        raise RuntimeError(
            f"Binary phase census contains forbidden paper-facing columns: {forbidden}."
        )
    if tuple(frame.columns) != tuple(CELL_OUTPUT_COLUMNS):
        raise RuntimeError("Binary phase census columns or column order changed.")
    expected_dtypes = {
        **dict.fromkeys(_STRING_COLUMNS, "str"),
        **dict.fromkeys(_FLOAT_COLUMNS, "float64"),
        **dict.fromkeys(_INTEGER_COLUMNS, "int64"),
        **dict.fromkeys(_BOOLEAN_COLUMNS, "bool"),
    }
    if set(expected_dtypes) != set(CELL_OUTPUT_COLUMNS):
        raise RuntimeError("Internal phase-census dtype coverage is incomplete.")
    actual_dtypes = {column: str(dtype) for column, dtype in frame.dtypes.items()}
    if actual_dtypes != expected_dtypes:
        raise RuntimeError("Binary phase census dtypes changed.")
    numeric = frame.loc[:, [*_FLOAT_COLUMNS, *_INTEGER_COLUMNS]].to_numpy(dtype=float)
    if not bool(np.isfinite(numeric).all()):
        raise RuntimeError("Binary phase census contains a nonfinite scientific value.")
    for column in _STRING_COLUMNS:
        if bool(frame[column].isna().any() or frame[column].str.strip().eq("").any()):
            raise RuntimeError(f"Binary phase census string column {column} is incomplete.")


def _equal_float(left: pd.Series, right: pd.Series | np.ndarray | float) -> pd.Series:
    return pd.Series(
        np.isclose(
            left.to_numpy(dtype=float),
            np.asarray(right, dtype=float),
            atol=_TOLERANCE,
            rtol=0.0,
        ),
        index=left.index,
    )


def _require_all(mask: pd.Series | np.ndarray, *, message: str) -> None:
    if not bool(np.asarray(mask, dtype=bool).all()):
        raise RuntimeError(message)


def _validate_cell_table(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate every census identity and return independently recomputed findings."""
    _require_table_schema(frame)
    if len(frame) != _EXPECTED_CELLS:
        raise RuntimeError("Binary phase census must contain exactly 200 cells.")
    keys = ["learner", "window_id", "conformal_group"]
    if bool(frame.duplicated(keys).any()):
        raise RuntimeError("Binary phase census contains a duplicate cell key.")
    expected_keys = set(product(_LEARNERS, _WINDOWS, range(_GROUPS)))
    actual_keys = set(frame.loc[:, keys].itertuples(index=False, name=None))
    if actual_keys != expected_keys:
        raise RuntimeError("Binary phase census is not the exact complete 5-by-8-by-5 grid.")
    _require_all(frame["taxonomy_groups"].eq(_GROUPS), message="Taxonomy group count changed.")
    _require_all(frame["alpha"].eq(_ALPHA), message="Phase census alpha changed.")

    rows = frame["fit_rows"]
    defaults = frame["fit_defaults"]
    nondefaults = frame["fit_nondefaults"]
    _require_all(rows.gt(0), message="A phase-census cell has no calibration rows.")
    _require_all(
        defaults.gt(0) & nondefaults.gt(0) & defaults.add(nondefaults).eq(rows),
        message="A phase-census cell has an empty or inconsistent binary class.",
    )
    _require_all(
        frame["both_classes_nonempty"].eq(True),
        message="The nonempty-class certificate failed.",
    )
    _require_all(
        _equal_float(frame["fit_default_prevalence"], defaults / rows),
        message="Default prevalence does not reconcile to calibration counts.",
    )

    expected_rank = np.ceil((rows.to_numpy(dtype=float) + 1.0) * (1.0 - _ALPHA)).astype(np.int64)
    _require_all(
        frame["finite_sample_rank"].eq(expected_rank) & frame["finite_sample_rank"].le(rows),
        message="A finite-sample rank changed or became capped.",
    )
    boundary = rows - frame["finite_sample_rank"]
    closed = np.floor(_ALPHA * (rows.to_numpy(dtype=float) + 1.0)).astype(np.int64) - 1
    _require_all(
        frame["boundary_count"].eq(boundary)
        & frame["boundary_closed_form"].eq(closed)
        & frame["boundary_identity_reconciles"].eq(True),
        message="The exact rank-boundary identity failed.",
    )
    _require_all(
        frame["phase_margin"].eq(defaults - boundary),
        message="A phase margin left its exact count definition.",
    )

    _require_all(
        frame["frozen_fit_rows"].eq(rows) & frame["rows_reconcile"].eq(True),
        message="Frozen and recomputed calibration row counts differ.",
    )
    _require_all(
        frame["frozen_finite_sample_rank"].eq(frame["finite_sample_rank"])
        & frame["rank_reconciles"].eq(True),
        message="Frozen and recomputed finite-sample ranks differ.",
    )
    _require_all(
        frame["frozen_threshold"].between(0.0, 1.0)
        & frame["recomputed_threshold"].between(0.0, 1.0),
        message="A phase threshold lies outside [0, 1].",
    )
    threshold_equal = _equal_float(frame["recomputed_threshold"], frame["frozen_threshold"])
    _require_all(
        threshold_equal & frame["threshold_reconciles"].eq(threshold_equal),
        message="Frozen and recomputed thresholds differ.",
    )
    _require_all(
        _equal_float(
            frame["threshold_gap"],
            np.abs(
                frame["recomputed_threshold"].to_numpy(dtype=float)
                - frame["frozen_threshold"].to_numpy(dtype=float)
            ),
        ),
        message="Threshold-gap bookkeeping changed.",
    )
    threshold_below = frame["recomputed_threshold"].lt(0.5)
    _require_all(
        frame["threshold_below_half"].eq(threshold_below),
        message="The threshold-half classification changed.",
    )

    recomputed_below = frame["recomputed_residual_below_threshold"]
    recomputed_equal = frame["recomputed_residual_equal_threshold"]
    recomputed_above = frame["recomputed_residual_above_threshold"]
    rank_bracket = recomputed_below.lt(frame["finite_sample_rank"]) & frame[
        "finite_sample_rank"
    ].le(recomputed_below + recomputed_equal)
    tie_total = recomputed_below + recomputed_equal + recomputed_above
    _require_all(
        recomputed_below.ge(0)
        & recomputed_equal.gt(0)
        & recomputed_above.ge(0)
        & tie_total.eq(rows)
        & rank_bracket
        & frame["rank_bracket_reconciles"].eq(True),
        message="Residual tie counts do not bracket the exact rank.",
    )
    frozen_ties_equal = (
        frame["frozen_residual_below_threshold"].eq(recomputed_below)
        & frame["frozen_residual_equal_threshold"].eq(recomputed_equal)
        & frame["frozen_residual_above_threshold"].eq(recomputed_above)
    )
    _require_all(
        frozen_ties_equal & frame["tie_counts_reconcile"].eq(True),
        message="Frozen and recomputed residual tie counts differ.",
    )

    score_domain = (
        frame["recomputed_score_min"].between(0.0, 1.0)
        & frame["recomputed_score_max"].between(0.0, 1.0)
        & frame["recomputed_score_min"].le(frame["recomputed_score_max"])
        & frame["fit_score_max_nondefault"].between(0.0, 1.0)
        & frame["fit_score_max_default"].between(0.0, 1.0)
        & frame["fit_score_max_nondefault"].le(frame["recomputed_score_max"])
        & frame["fit_score_max_default"].le(frame["recomputed_score_max"])
    )
    score_equal = _equal_float(
        frame["recomputed_score_min"], frame["frozen_score_min"]
    ) & _equal_float(frame["recomputed_score_max"], frame["frozen_score_max"])
    _require_all(score_domain, message="A recomputed score extremum is invalid.")
    _require_all(
        score_equal & frame["score_extrema_reconcile"].eq(True),
        message="Frozen and recomputed score extrema differ.",
    )

    _require_all(
        frame["count_nondefault_score_below_half"].between(0, nondefaults)
        & frame["count_default_score_above_half"].between(0, defaults),
        message="A half-score count exceeds its calibration class.",
    )
    exact_half_expected = (
        frame["count_nondefault_score_below_half"] + frame["count_default_score_above_half"]
    ).ge(frame["finite_sample_rank"])
    exact_half_pass = exact_half_expected.eq(threshold_below)
    _require_all(
        frame["exact_half_criterion_expected"].eq(exact_half_expected)
        & frame["exact_half_criterion_observed"].eq(threshold_below)
        & frame["exact_half_criterion_pass"].eq(exact_half_pass)
        & exact_half_pass,
        message="The exact half-threshold identity failed.",
    )

    half_applicable = frame["recomputed_score_max"].lt(0.5)
    _require_all(
        frame["max_score_below_half_condition"].eq(half_applicable)
        & frame["phase_margin_half_check_applicable"].eq(half_applicable),
        message="The half-threshold applicability condition changed.",
    )
    computed_half_pass = frame["phase_margin"].le(0).eq(threshold_below)
    half_failed = half_applicable & (~computed_half_pass | ~frame["phase_margin_half_check_pass"])
    if bool(half_failed.any()):
        raise RuntimeError("An applicable phase-margin half check failed.")

    source_applicable = (
        frame["fit_score_max_nondefault"].add(frame["fit_score_max_default"]).lt(1.0)
    )
    _require_all(
        frame["no_interleaving_condition"].eq(source_applicable)
        & frame["phase_margin_source_check_applicable"].eq(source_applicable),
        message="The mirror-source applicability condition changed.",
    )
    expected_source = pd.Series(
        np.where(
            source_applicable,
            np.where(frame["phase_margin"].le(0), "nondefault_mirror", "default_mirror"),
            "condition_not_met",
        ),
        index=frame.index,
        dtype="str",
    )
    _require_all(
        frame["expected_threshold_source_branch"].eq(expected_source),
        message="The expected mirror-source branch changed.",
    )
    _require_all(
        frame.loc[~source_applicable, "threshold_source_branch"].eq("condition_not_met"),
        message="An inapplicable mirror-source cell received a branch label.",
    )
    source_failed = source_applicable & (
        ~frame["threshold_source_branch"].eq(expected_source)
        | ~frame["phase_margin_source_check_pass"]
    )
    if bool(source_failed.any()):
        raise RuntimeError("An applicable phase-margin source check failed.")

    cell_expected = (
        frame["both_classes_nonempty"]
        & frame["boundary_identity_reconciles"]
        & frame["rows_reconcile"]
        & frame["rank_reconciles"]
        & frame["threshold_reconciles"]
        & frame["tie_counts_reconcile"]
        & frame["score_extrema_reconcile"]
        & frame["rank_bracket_reconciles"]
        & frame["exact_half_criterion_pass"]
        & ~half_failed
        & ~source_failed
    )
    _require_all(
        frame["cell_reconciles"].eq(cell_expected) & cell_expected,
        message="A binary phase census cell does not reconcile.",
    )
    return _paper_findings(frame, half_failed=half_failed, source_failed=source_failed)


def _paper_findings(
    frame: pd.DataFrame,
    *,
    half_failed: pd.Series,
    source_failed: pd.Series,
) -> dict[str, Any]:
    ordered: list[dict[str, Any]] = []
    for group in range(_GROUPS):
        cell = frame["conformal_group"].eq(group)
        half_applicable = cell & frame["phase_margin_half_check_applicable"]
        source_applicable = cell & frame["phase_margin_source_check_applicable"]
        ordered.append(
            {
                "conformal_group": group,
                "cells": int(cell.sum()),
                "threshold_below_half": int((cell & frame["threshold_below_half"]).sum()),
                "phase_margin_nonpositive": int((cell & frame["phase_margin"].le(0)).sum()),
                "half_condition_applicable": int(half_applicable.sum()),
                "half_condition_inapplicable": int((cell & ~half_applicable).sum()),
                "half_condition_failed_when_applicable": int((cell & half_failed).sum()),
                "source_condition_applicable": int(source_applicable.sum()),
                "source_condition_inapplicable": int((cell & ~source_applicable).sum()),
                "source_condition_failed_when_applicable": int((cell & source_failed).sum()),
                "exact_half_failures": int((cell & ~frame["exact_half_criterion_pass"]).sum()),
                "reconciliation_failures": int((cell & ~frame["cell_reconciles"]).sum()),
            }
        )
    half_applicable = frame["phase_margin_half_check_applicable"]
    source_applicable = frame["phase_margin_source_check_applicable"]
    return {
        "cells": int(len(frame)),
        "learner_count": int(frame["learner"].nunique()),
        "window_count": int(frame["window_id"].nunique()),
        "conformal_group_count": int(frame["conformal_group"].nunique()),
        "cells_per_conformal_group": _EXPECTED_CELLS_PER_GROUP,
        "ordered_conformal_groups": ordered,
        "global": {
            "threshold_below_half": int(frame["threshold_below_half"].sum()),
            "phase_margin_nonpositive": int(frame["phase_margin"].le(0).sum()),
            "half_condition_applicable": int(half_applicable.sum()),
            "half_condition_inapplicable": int((~half_applicable).sum()),
            "half_condition_failed_when_applicable": int(half_failed.sum()),
            "source_condition_applicable": int(source_applicable.sum()),
            "source_condition_inapplicable": int((~source_applicable).sum()),
            "source_condition_failed_when_applicable": int(source_failed.sum()),
            "exact_half_failures": int((~frame["exact_half_criterion_pass"]).sum()),
            "reconciliation_failures": int((~frame["cell_reconciles"]).sum()),
        },
        "retrospective": True,
        "confirmatory": False,
        "learner_window_breakdown_emitted": False,
        "forbidden_columns": [],
    }


def _recomputed_results(frame: pd.DataFrame) -> dict[str, Any]:
    half_applicable = frame["phase_margin_half_check_applicable"]
    source_applicable = frame["phase_margin_source_check_applicable"]
    source = frame.loc[source_applicable, "threshold_source_branch"]
    counts = {
        "cells_both_classes_nonempty": int(frame["both_classes_nonempty"].sum()),
        "cells_with_uncapped_rank": int(frame["finite_sample_rank"].le(frame["fit_rows"]).sum()),
        "cells_threshold_below_half": int(frame["threshold_below_half"].sum()),
        "cells_threshold_at_or_above_half": int((~frame["threshold_below_half"]).sum()),
        "cells_phase_margin_nonpositive": int(frame["phase_margin"].le(0).sum()),
        "cells_phase_margin_positive": int(frame["phase_margin"].gt(0).sum()),
        "cells_exact_half_criterion_pass": int(frame["exact_half_criterion_pass"].sum()),
        "cells_max_score_below_half_condition": int(half_applicable.sum()),
        "cells_phase_margin_half_check_pass_when_applicable": int(
            frame.loc[half_applicable, "phase_margin_half_check_pass"].sum()
        ),
        "cells_no_interleaving_condition": int(source_applicable.sum()),
        "cells_phase_margin_source_check_pass_when_applicable": int(
            frame.loc[source_applicable, "phase_margin_source_check_pass"].sum()
        ),
        "cells_nondefault_mirror_source_under_condition": int(source.eq("nondefault_mirror").sum()),
        "cells_default_mirror_source_under_condition": int(source.eq("default_mirror").sum()),
        "cells_reconciled": int(frame["cell_reconciles"].sum()),
    }
    ordered = []
    for group in range(_GROUPS):
        stratum = frame.loc[frame["conformal_group"].eq(group)]
        stratum_half = stratum["phase_margin_half_check_applicable"]
        stratum_source = stratum["phase_margin_source_check_applicable"]
        ordered.append(
            {
                "conformal_group": group,
                "expected_cells": _EXPECTED_CELLS_PER_GROUP,
                "observed_cells": int(len(stratum)),
                "cells_both_classes_nonempty": int(stratum["both_classes_nonempty"].sum()),
                "cells_with_uncapped_rank": int(
                    stratum["finite_sample_rank"].le(stratum["fit_rows"]).sum()
                ),
                "cells_threshold_below_half": int(stratum["threshold_below_half"].sum()),
                "cells_phase_margin_nonpositive": int(stratum["phase_margin"].le(0).sum()),
                "cells_exact_half_criterion_pass": int(stratum["exact_half_criterion_pass"].sum()),
                "cells_max_score_below_half_condition": int(stratum_half.sum()),
                "cells_phase_margin_half_check_pass_when_applicable": int(
                    stratum.loc[stratum_half, "phase_margin_half_check_pass"].sum()
                ),
                "cells_no_interleaving_condition": int(stratum_source.sum()),
                "cells_phase_margin_source_check_pass_when_applicable": int(
                    stratum.loc[stratum_source, "phase_margin_source_check_pass"].sum()
                ),
                "cells_reconciled": int(stratum["cell_reconciles"].sum()),
            }
        )
    return {
        "status": "complete_outcome_free_binary_phase_census",
        "design_cardinalities": {
            "learner_count": 5,
            "window_count": 8,
            "stratum_count_per_learner_window": 5,
            "expected_cells": 200,
            "observed_cells": int(len(frame)),
        },
        "global_counts": counts,
        "complete_ordered_stratum_summary": ordered,
        "global_checks": {
            "complete_grid": len(frame) == _EXPECTED_CELLS,
            "all_cells_both_classes_nonempty": bool(frame["both_classes_nonempty"].all()),
            "all_ranks_uncapped": bool(frame["finite_sample_rank"].le(frame["fit_rows"]).all()),
            "boundary_identity_all_cells": bool(frame["boundary_identity_reconciles"].all()),
            "exact_half_criterion_all_cells": bool(frame["exact_half_criterion_pass"].all()),
            "all_applicable_condition_checks_pass": bool(
                frame.loc[half_applicable, "phase_margin_half_check_pass"].all()
                and frame.loc[source_applicable, "phase_margin_source_check_pass"].all()
            ),
            "all_cells_reconcile": bool(frame["cell_reconciles"].all()),
        },
        "reporting_contract": dict(_EXPECTED_REPORTING_CONTRACT),
    }


def _require_result_contract(summary: Mapping[str, Any], frame: pd.DataFrame) -> None:
    results = _mapping(summary, "results", label="phase census summary")
    expected = _recomputed_results(frame)
    if dict(results) != expected:
        raise RuntimeError("Phase census summary results do not recompute from all 200 cells.")


def _clean_git_state(raw: Any, *, label: str) -> None:
    expected = {
        "commit": _PROTOCOL_COMMIT,
        "dirty": False,
        "dirty_entries": 0,
        "dirty_paths": [],
    }
    if not isinstance(raw, Mapping) or dict(raw) != expected:
        raise RuntimeError(f"{label} Git state is not the clean protocol commit.")


def _require_no_side_effects(payload: Mapping[str, Any], *, label: str) -> None:
    for key in (
        "protected_stages_run",
        "protected_artifacts_read",
        "protected_artifacts_written",
    ):
        if payload.get(key) != []:
            raise RuntimeError(f"{label} reports a forbidden protected side effect in {key}.")


def _validate_payloads(
    summary: Mapping[str, Any],
    receipt: Mapping[str, Any],
    config: Mapping[str, Any],
    frame: pd.DataFrame,
    *,
    registered_descriptors: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    cache: dict[tuple[str, int, str], Path],
) -> None:
    summary_keys = {
        "schema_version",
        "status",
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "planned_artifact_tag",
        "protocol",
        "source_artifacts",
        "source_read_contract",
        "results",
        "cell_table_schema",
        "artifacts",
        "claim_boundary",
        "implementation_provenance",
        "environment",
        "initial_git",
        "artifact_commit_status",
        "protected_stages_run",
        "protected_artifacts_read",
        "protected_artifacts_written",
    }
    receipt_keys = {
        "schema_version",
        "status",
        "run_tag",
        "started_at_utc",
        "completed_at_utc",
        "runtime_seconds",
        "protocol_tag",
        "protocol_commit",
        "planned_artifact_tag",
        "protocol",
        "implementation_provenance",
        "sources",
        "summary",
        "artifacts",
        "initial_git",
        "final_git",
        "environment",
        "promotion_boundary",
        "protected_stages_run",
        "protected_artifacts_read",
        "protected_artifacts_written",
    }
    _require_exact_keys(summary, summary_keys, label="phase census summary")
    _require_exact_keys(receipt, receipt_keys, label="phase census receipt")
    if (
        summary.get("schema_version") != _SCHEMA_VERSION
        or summary.get("status") != _SUMMARY_STATUS
        or summary.get("run_tag") != _RUN_TAG
        or summary.get("protocol_tag") != _PROTOCOL_TAG
        or summary.get("protocol_commit") != _PROTOCOL_COMMIT
        or summary.get("planned_artifact_tag") != _ARTIFACT_TAG
    ):
        raise RuntimeError("Phase census summary identity changed.")
    if (
        receipt.get("schema_version") != _SCHEMA_VERSION
        or receipt.get("status") != _RECEIPT_STATUS
        or receipt.get("run_tag") != _RUN_TAG
        or receipt.get("protocol_tag") != _PROTOCOL_TAG
        or receipt.get("protocol_commit") != _PROTOCOL_COMMIT
        or receipt.get("planned_artifact_tag") != _ARTIFACT_TAG
    ):
        raise RuntimeError("Phase census receipt identity changed.")
    runtime = receipt.get("runtime_seconds")
    if (
        isinstance(runtime, bool)
        or not isinstance(runtime, (int, float))
        or not math.isfinite(float(runtime))
        or float(runtime) <= 0.0
    ):
        raise RuntimeError("Phase census receipt runtime is invalid.")

    protocol_descriptor = registered_descriptors["binary_phase_census_protocol"]
    if _exact_descriptor(summary.get("protocol"), label="summary protocol") != protocol_descriptor:
        raise RuntimeError("Summary protocol descriptor changed.")
    if _exact_descriptor(receipt.get("protocol"), label="receipt protocol") != protocol_descriptor:
        raise RuntimeError("Receipt protocol descriptor changed.")
    table_descriptor = registered_descriptors["binary_phase_census_table"]
    summary_descriptor = registered_descriptors["binary_phase_census_summary"]
    summary_artifacts = _mapping(summary, "artifacts", label="phase census summary")
    receipt_artifacts = _mapping(receipt, "artifacts", label="phase census receipt")
    if set(summary_artifacts) != {"complete_cell_table"} or set(receipt_artifacts) != {
        "complete_cell_table"
    }:
        raise RuntimeError("Phase census artifact inventory changed.")
    if (
        _exact_descriptor(summary_artifacts.get("complete_cell_table"), label="summary cell table")
        != table_descriptor
        or _exact_descriptor(
            receipt_artifacts.get("complete_cell_table"), label="receipt cell table"
        )
        != table_descriptor
    ):
        raise RuntimeError("Phase census cell-table descriptor changed.")
    if _exact_descriptor(receipt.get("summary"), label="receipt summary") != summary_descriptor:
        raise RuntimeError("Phase census summary descriptor changed in the receipt.")

    source = _mapping(config, "source", label="phase census config")
    if dict(_mapping(summary, "source_artifacts", label="phase census summary")) != dict(source):
        raise RuntimeError("Summary source descriptors differ from the frozen config.")
    if dict(_mapping(receipt, "sources", label="phase census receipt")) != dict(source):
        raise RuntimeError("Receipt source descriptors differ from the frozen config.")
    if (
        dict(_mapping(summary, "source_read_contract", label="phase census summary"))
        != _EXPECTED_SOURCE_READ_CONTRACT
    ):
        raise RuntimeError("Phase census source-read boundary changed.")
    if dict(_mapping(summary, "claim_boundary", label="phase census summary")) != dict(
        _mapping(config, "claim_boundary", label="phase census config")
    ):
        raise RuntimeError("Summary claim boundary differs from the frozen config.")
    if summary.get("cell_table_schema") != dataframe_schema(frame):
        raise RuntimeError("Summary cell-table schema differs from the complete CSV.")

    if summary.get("implementation_provenance") != receipt.get("implementation_provenance"):
        raise RuntimeError("Summary and receipt implementation provenance differ.")
    _require_implementation_provenance(
        summary,
        registered_descriptors=registered_descriptors,
        repo_root=repo_root,
        cache=cache,
        label="phase census summary",
    )
    summary_environment = _mapping(summary, "environment", label="phase census summary")
    receipt_environment = _mapping(receipt, "environment", label="phase census receipt")
    if dict(summary_environment) != dict(receipt_environment):
        raise RuntimeError("Summary and receipt environments differ.")
    if summary_environment.get("uv_lock_sha256") != _UV_LOCK_SHA256:
        raise RuntimeError("Phase census scientific lock hash changed.")
    _clean_git_state(summary.get("initial_git"), label="summary initial")
    _clean_git_state(receipt.get("initial_git"), label="receipt initial")
    _clean_git_state(receipt.get("final_git"), label="receipt final")
    if summary.get("artifact_commit_status") != (
        "pending_single_direct_child_commit_and_annotated_tag"
    ):
        raise RuntimeError("Historical pre-seal artifact status changed.")
    _require_no_side_effects(summary, label="phase census summary")
    _require_no_side_effects(receipt, label="phase census receipt")
    _require_result_contract(summary, frame)


def load_binary_phase_census_evidence(
    registered: Mapping[str, Path],
    identity: Mapping[str, Any],
    *,
    repo_root: Path,
) -> BinaryPhaseCensusEvidence:
    """Verify the active Git-native phase census and expose its complete table."""
    root = repo_root.resolve()
    _require_registered_paths(registered, repo_root=root)
    _require_identity_and_transport(identity, repo_root=root)
    registered_descriptors = _require_registered_blobs(registered, repo_root=root)
    cache: dict[tuple[str, int, str], Path] = {}

    config = _load_yaml_object(registered["binary_phase_census_config"], label="phase config")
    _validate_config(config)
    summary = _load_json_object(
        registered["binary_phase_census_summary"], label="phase census summary"
    )
    receipt = _load_json_object(
        registered["binary_phase_census_receipt"], label="phase census receipt"
    )
    frame = pd.read_csv(registered["binary_phase_census_table"])
    findings = _validate_cell_table(frame)
    _validate_payloads(
        summary,
        receipt,
        config,
        frame,
        registered_descriptors=registered_descriptors,
        repo_root=root,
        cache=cache,
    )
    return BinaryPhaseCensusEvidence(
        summary=summary,
        receipt=receipt,
        cell_table=frame,
        findings=findings,
    )


def binary_phase_census_publication_table(
    evidence: BinaryPhaseCensusEvidence,
) -> pd.DataFrame:
    """Return a defensive copy of the verified complete 200-cell table."""
    table = evidence.cell_table.copy()
    _validate_cell_table(table)
    return table


__all__ = [
    "BinaryPhaseCensusEvidence",
    "binary_phase_census_publication_table",
    "load_binary_phase_census_evidence",
]
