"""Run or verify the clean V3E marginal mean-score--outcome gap replay."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import re
import secrets
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[2]
PROJECT_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
if str(PROJECT_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(PROJECT_SITE_PACKAGES))

import dateutil  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow  # noqa: E402
import six  # noqa: E402
import tzdata  # noqa: E402
import yaml  # noqa: E402

from scripts.experiments.bootstrap_ijds_marginal_mean_score_outcome_gap_v3e import (  # noqa: E402
    GIT_EXECUTABLE,
    RUNTIME_MANIFEST_PATH as BOOTSTRAP_RUNTIME_MANIFEST_PATH,
    _git_environment,
    _load_runtime_manifest as load_bootstrap_runtime_manifest,
    derive_local_python_closure as derive_bootstrap_python_closure,
    git_command,
    require_loaded_module_origins,
    require_sealed_import_runtime,
)
from src.ijds_audit.marginal_mean_score_outcome_gap_v3e import (  # noqa: E402
    ENDPOINT_REASONS,
    ESTIMAND,
    ROLE,
    MarginalMeanScoreOutcomeGapV3EResult,
    build_row_level_endpoint,
    marginal_mean_score_outcome_gap_v3e,
    scan_primary_oot_raw_archive,
)
from src.utils.artifact_descriptor import (  # noqa: E402
    relative_artifact_descriptor,
    sha256_file,
)

_SEALED_AUTHORITY_BYTES = {
    Path(str(path)): bytes(payload)
    for path, payload in globals().get("_IJDS_V3E_SEALED_AUTHORITY_BYTES", {}).items()
}
_RUNNER_EXECUTED_FROM_SEALED_BYTES = bool(
    globals().get("_IJDS_V3E_RUNNER_EXECUTED_FROM_SEALED_BYTES", False)
)

DEFAULT_CONFIG_PATH = Path(
    "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3e.yaml"
)
PROTOCOL_PATH = Path(
    "docs/research/ijds_marginal_mean_score_outcome_gap_v3e_protocol_2026-07-26.md"
)
BOOTSTRAP_PATH = Path("scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3e.py")
RUNNER_PATH = Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3e.py")
RUNTIME_MANIFEST_PATH = Path(
    "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3e_runtime.json"
)
CALIBRE_GLOBAL_TEMPLATE_PATH = Path(
    "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3e_calibre_global.json"
)
RUN_TAG = "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e"
PROTOCOL_TAG = "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e"
ARTIFACT_TAG = "artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e"
SCHEMA_VERSION = "2026-07-26.3e"
ABORTED_V3D_PROTOCOL_COMMIT = "b51e0fbc25a941d9ea3b1e68c6c7ba5823b33ba5"
EXPECTED_V3E_PROTOCOL_DIFF_PATHS = tuple(
    sorted(
        (
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3e.yaml",
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3e_runtime.json",
            "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3e_calibre_global.json",
            "docs/research/ijds_marginal_mean_score_outcome_gap_v3e_protocol_2026-07-26.md",
            "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3e.py",
            "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3e.py",
            "src/ijds_audit/marginal_mean_score_outcome_gap_v3e.py",
            "tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3e.py",
            "tests/test_ijds_audit/test_marginal_mean_score_outcome_gap_v3e.py",
        )
    )
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
TRANSITIVE_PYTHON_PATHS = (
    Path("scripts/__init__.py"),
    Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3e.py"),
    Path("src/__init__.py"),
    Path("src/data/__init__.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/ijds_audit/__init__.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/geometry.py"),
    Path("src/ijds_audit/marginal_mean_score_outcome_gap_v3e.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/rhs_ranging.py"),
    Path("src/utils/__init__.py"),
    Path("src/utils/artifact_descriptor.py"),
)
HANDOFF_IMPORTED_PYTHON_PATHS = (
    BOOTSTRAP_PATH,
    Path("scripts/__init__.py"),
    Path("src/__init__.py"),
    Path("src/data/__init__.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/ijds_audit/__init__.py"),
    Path("src/ijds_audit/marginal_mean_score_outcome_gap_v3e.py"),
    Path("src/utils/__init__.py"),
    Path("src/utils/artifact_descriptor.py"),
)
BOOTSTRAP_PYTHON_PATHS = (BOOTSTRAP_PATH,)
NONPYTHON_AUTHORITY_PATHS = (
    DEFAULT_CONFIG_PATH,
    PROTOCOL_PATH,
    RUNTIME_MANIFEST_PATH,
    CALIBRE_GLOBAL_TEMPLATE_PATH,
    Path("tests/test_ijds_audit/test_marginal_mean_score_outcome_gap_v3e.py"),
    Path("tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3e.py"),
    Path(".gitignore"),
    Path(".gitattributes"),
    Path(".python-version"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
GIT_BOUND_SOURCE_KEYS = (
    "score_data_dvc_pointer",
    "score_model_dvc_pointer",
    "raw_dvc_pointer",
    "raw_audit_evidence",
    "raw_audit_config",
)
SOURCE_KEYS = {
    "credit_control_freeze",
    "scores",
    "score_data_dvc_pointer",
    "score_model_dvc_pointer",
    "raw_archive",
    "raw_dvc_pointer",
    "raw_audit_evidence",
    "raw_audit_config",
}
LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
SCORE_COLUMNS = {learner: f"pd_{learner}" for learner in LEARNERS}
ISSUE_MONTHS = tuple(pd.period_range("2016-04", "2017-06", freq="M").astype(str).tolist())
EXPECTED_COUNTS = {
    "expected_raw_rows": 2_925_493,
    "expected_candidates": 376_890,
    "expected_resolved": 364_814,
    "expected_unresolved": 12_076,
    "expected_resolved_y0": 307_842,
    "expected_resolved_y1": 56_972,
}
EXPECTED_CANDIDATE_ID_SHA256 = "72799b236a7e45d8746099adefba7da5683e8308959643d6ad341d3585e8fa74"
EXPECTED_REASON_CENSUS = {
    "charged_off_by_reconstructed_cutoff": {
        "candidate_rows": 56_972,
        "resolved_rows": 56_972,
        "unresolved_rows": 0,
    },
    "fully_paid_by_reconstructed_cutoff": {
        "candidate_rows": 307_842,
        "resolved_rows": 307_842,
        "unresolved_rows": 0,
    },
    "nonterminal_or_unresolved_status": {
        "candidate_rows": 11_551,
        "resolved_rows": 0,
        "unresolved_rows": 11_551,
    },
    "terminal_after_reconstructed_cutoff": {
        "candidate_rows": 47,
        "resolved_rows": 0,
        "unresolved_rows": 47,
    },
    "terminal_availability_date_missing": {
        "candidate_rows": 478,
        "resolved_rows": 0,
        "unresolved_rows": 478,
    },
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _require_revalidation_callback() -> Any:
    callback = globals().get("_IJDS_V3E_REVALIDATE_BOOTSTRAP_ATTESTATION")
    carrier = sys.modules.get("calibre.debug")
    code = getattr(callback, "__code__", None)
    if (
        not callable(callback)
        or carrier is None
        or getattr(callback, "__globals__", None) is not vars(carrier)
        or getattr(callback, "__name__", None) != "revalidate_bootstrap_attestation"
        or getattr(callback, "__qualname__", None) != "revalidate_bootstrap_attestation"
        or code is None
        or Path(str(getattr(code, "co_filename", ""))).resolve()
        != (ROOT / BOOTSTRAP_PATH).resolve()
    ):
        raise RuntimeError(
            "V3E terminal revalidation callback is not bound to the authenticated "
            "Calibre entrypoint carrier."
        )
    return callback


def _require_bootstrap_attestation(*, phase: str) -> dict[str, Any]:
    attestation = globals().get("_IJDS_V3E_BOOTSTRAP_ATTESTATION")
    if not isinstance(attestation, Mapping):
        raise RuntimeError("V3E scientific runner was invoked without the authenticated bootstrap.")
    if (
        attestation.get("schema_version") != "2026-07-26.3e-bootstrap-1"
        or attestation.get("phase") != phase
        or attestation.get("head_tag")
        != (
            PROTOCOL_TAG
            if phase in {"handoff-only", "pre-source-only", "compute"}
            else ARTIFACT_TAG
        )
        or not _RUNNER_EXECUTED_FROM_SEALED_BYTES
    ):
        raise RuntimeError("V3E bootstrap attestation identity changed.")
    expected_paths = {
        *BOOTSTRAP_PYTHON_PATHS,
        *TRANSITIVE_PYTHON_PATHS,
        *NONPYTHON_AUTHORITY_PATHS,
    }
    if set(_SEALED_AUTHORITY_BYTES) != expected_paths:
        raise RuntimeError("V3E sealed authority byte census is absent or incomplete.")
    source_files = attestation.get("authority", {}).get("source_files", {})
    for relative, payload in _SEALED_AUTHORITY_BYTES.items():
        expected = _descriptor_from_bytes(payload, relative_path=relative.as_posix())
        if source_files.get(relative.as_posix()) != expected:
            raise RuntimeError(f"V3E sealed authority descriptor changed: {relative}.")
    runner_payload = _SEALED_AUTHORITY_BYTES.get(
        Path("scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3e.py")
    )
    if (
        runner_payload is None
        or globals().get("_IJDS_V3E_RUNNER_EXECUTED_FROM_SEALED_BYTES") is not True
    ):
        raise RuntimeError("V3E runner did not execute from the authenticated runner payload.")
    _require_revalidation_callback()
    return dict(attestation)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse one explicit phase and the one canonical configuration path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("handoff-only", "pre-source-only", "compute", "verify-artifact"),
        required=True,
    )
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def _resolve_repo_file(path_like: str | Path, *, repo_root: Path) -> Path:
    root = repo_root.resolve()
    raw = Path(path_like)
    path = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Repository input escapes the repository: {path}.") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _resolve_locked_config_path(path: Path, *, repo_root: Path) -> Path:
    resolved = _resolve_repo_file(path, repo_root=repo_root)
    expected = (repo_root.resolve() / DEFAULT_CONFIG_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V3E accepts only the canonical config: {expected}.")
    return resolved


def _descriptor_from_bytes(data: bytes, *, relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _stable_file_bytes(path: Path) -> bytes:
    if path.is_symlink():
        raise RuntimeError(f"V3E file is symlinked: {path}.")
    resolved = path.resolve()
    if not resolved.is_file():
        raise RuntimeError(f"V3E file is missing or nonregular: {resolved}.")
    before = resolved.stat()
    with resolved.open("rb") as handle:
        handle_before = os.fstat(handle.fileno())
        payload = handle.read()
        handle_after = os.fstat(handle.fileno())
    after = resolved.stat()
    identities = {
        (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        for value in (before, handle_before, handle_after, after)
    }
    if len(identities) != 1 or len(payload) != after.st_size:
        raise RuntimeError(f"V3E file changed while read: {resolved}.")
    return payload


def _read_verified_bytes(
    descriptor: Mapping[str, Any], *, label: str, repo_root: Path
) -> tuple[Path, bytes]:
    if set(descriptor).difference({"path", "bytes", "sha256", "dvc_md5"}):
        raise RuntimeError(f"{label} descriptor has undeclared fields.")
    path = _resolve_repo_file(str(descriptor.get("path")), repo_root=repo_root)
    data = _stable_file_bytes(path)
    relative = path.relative_to(repo_root.resolve()).as_posix()
    actual = _descriptor_from_bytes(data, relative_path=relative)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"{label} mismatched on {field}.")
    return path, data


def _load_config(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    relative = resolved.relative_to(ROOT.resolve())
    data = _SEALED_AUTHORITY_BYTES.get(relative)
    if _SEALED_AUTHORITY_BYTES and data is None:
        raise RuntimeError("Canonical V3E config is absent from the sealed authority bytes.")
    if data is None:
        data = _stable_file_bytes(resolved)
    payload = yaml.safe_load(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V3E configuration must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_tag",
        "artifact_tag",
        "protocol_path",
        "estimand",
        "prior_lineage",
        "source",
        "source_identity",
        "design",
        "scientific_contract",
        "execution",
        "authority",
        "output",
        "reporting_contract",
        "stop_rules",
    }
    if set(payload) != required:
        raise RuntimeError("V3E top-level configuration fields changed.")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise RuntimeError("V3E schema version changed.")
    if payload["protocol_status"] != (
        "retrospectively_locked_runtime_lineage_recovery_before_v3e_execution"
    ):
        raise RuntimeError("V3E protocol status changed.")
    if (
        payload["run_tag"] != RUN_TAG
        or payload["protocol_tag"] != PROTOCOL_TAG
        or payload["artifact_tag"] != ARTIFACT_TAG
        or payload["protocol_path"] != PROTOCOL_PATH.as_posix()
        or payload["estimand"] != ESTIMAND
    ):
        raise RuntimeError("V3E run, tag, protocol, or estimand identity changed.")
    prior = payload["prior_lineage"]
    expected_prior = {
        "v2_run_tag": "ijds-marginal-mean-score-outcome-gap-2026-07-26-v2",
        "status": "quarantined_runtime_and_portability_lineage_not_a_scientific_refutation",
        "v2_outputs_are_inputs": False,
        "v2_result_signs_already_inspected": True,
        "v3_protocol_tag": "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3",
        "v3_protocol_commit": "934cdb2f2a9418625eddf0f9bc4cb771d2654696",
        "v3_status": "aborted_precompute_runtime_path_not_git_ignored",
        "v3_outcomes_read": False,
        "v3_outputs_exist": False,
        "v3_outputs_are_inputs": False,
        "v3a_protocol_tag": "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3a",
        "v3a_protocol_commit": "88f71852db9d740e54d290e378a070f0a43b8541",
        "v3a_status": "aborted_pre_science_calibre_e_entrypoint_sys_path_mismatch",
        "v3a_outcomes_read": False,
        "v3a_outputs_exist": False,
        "v3a_outputs_are_inputs": False,
        "v3b_protocol_tag": "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3b",
        "v3b_protocol_commit": "0a7b184d5d82748fb57d37c734268fc096259976",
        "v3b_status": "aborted_pre_science_calibre_e_entrypoint_carrier_not_attested",
        "v3b_outcomes_read": False,
        "v3b_outputs_exist": False,
        "v3b_outputs_are_inputs": False,
        "v3c_protocol_tag": "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3c",
        "v3c_protocol_commit": "d3ebcdd96087e1419a73961c947fea6e85c8a0e9",
        "v3c_status": "aborted_pre_outcome_runner_authority_census_handoff_mismatch",
        "v3c_scientific_modules_imported": True,
        "v3c_config_read": False,
        "v3c_source_data_read": False,
        "v3c_outcomes_read": False,
        "v3c_outputs_exist": False,
        "v3c_outputs_are_inputs": False,
        "v3d_protocol_tag": "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3d",
        "v3d_protocol_commit": "b51e0fbc25a941d9ea3b1e68c6c7ba5823b33ba5",
        "v3d_status": "aborted_pre_source_authority_config_duplicate",
        "v3d_scientific_modules_imported": True,
        "v3d_config_read": True,
        "v3d_git_bound_source_checks_started": False,
        "v3d_source_data_read": False,
        "v3d_outcomes_read": False,
        "v3d_outputs_exist": False,
        "v3d_outputs_are_inputs": False,
        "v3e_role": "clean_row_identified_runtime_and_lineage_replay",
    }
    if not isinstance(prior, Mapping) or dict(prior) != expected_prior:
        raise RuntimeError("V3E prior-lineage quarantine boundary changed.")
    source = payload["source"]
    if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
        raise RuntimeError("V3E source family changed.")
    for key, descriptor in source.items():
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"V3E source {key!r} is not a descriptor.")
        allowed = {"path", "bytes", "sha256", "dvc_md5"}
        if set(descriptor).difference(allowed) or not {"path", "bytes", "sha256"}.issubset(
            descriptor
        ):
            raise RuntimeError(f"V3E source descriptor fields changed for {key!r}.")
    source_identity = payload["source_identity"]
    expected_source_identity = {
        "credit_control_freeze_status": (
            "credit_control_scores_frozen_before_primary_oot_outcome_join"
        ),
        "credit_control_freeze_run_tag": "ijds-credit-risk-controls-2026-07-13-v1b",
        "credit_control_freeze_protocol_tag": ("protocol/ijds-credit-risk-controls-2026-07-13-v1b"),
        "credit_control_freeze_protocol_commit": ("1776cbf8b201ae5b92756e5ea397a403d6cc7c9f"),
        "credit_control_sampling": "none_all_eligible_rows",
        "credit_control_model_selection": "none_all_five_reported",
        "raw_audit_status": "complete_full_archive_data_contract_audit",
        "raw_audit_run_tag": "ijds-raw-data-contract-2026-07-14-v2",
        "raw_rows": 2_925_493,
        "raw_dvc_size": 1_773_470_505,
    }
    if (
        not isinstance(source_identity, Mapping)
        or dict(source_identity) != expected_source_identity
    ):
        raise RuntimeError("V3E source-identity lineage contract changed.")
    design = payload["design"]
    if not isinstance(design, Mapping):
        raise TypeError("V3E design must be a mapping.")
    if (
        design.get("role") != ROLE
        or design.get("term_months") != 36
        or design.get("primary_oot_start_month") != "2016-04"
        or design.get("primary_oot_end_month") != "2017-06"
        or design.get("endpoint_cutoff") != "2020-09-30"
        or design.get("charged_off_availability_lag_months") != 6
        or tuple(design.get("issue_months", ())) != ISSUE_MONTHS
        or tuple(design.get("learners", ())) != LEARNERS
        or dict(design.get("score_columns", {})) != SCORE_COLUMNS
        or tuple(design.get("endpoint_reason_census", {})) != ENDPOINT_REASONS
        or dict(design.get("endpoint_reason_census", {})) != EXPECTED_REASON_CENSUS
        or design.get("expected_candidate_id_sha256") != EXPECTED_CANDIDATE_ID_SHA256
        or design.get("expected_endpoint_row_sha256")
        != "04c4d182b1223dc1c92df0898d4cd25e0a44fedded46dc1f52af62ba3d9317b6"
        or design.get("hash_serialization")
        != {
            "identifier_order": "normalized_unique_ids_sorted_by_unicode_code_point",
            "identifier_record": (
                "utf8_bytes_prefixed_by_unsigned_64_bit_little_endian_byte_length"
            ),
            "endpoint_order": "rows_sorted_by_normalized_id",
            "endpoint_record": (
                "compact_utf8_json_array_id_role_period_reason_nullable_binary_outcome"
            ),
            "endpoint_record_prefix": "unsigned_64_bit_little_endian_json_byte_length",
            "identifier_literal_vector_sha256": (
                "81f6992fb47d559c793c87786fe34a258f8a816b741079c8301d1af281d54e0d"
            ),
            "endpoint_literal_vector_sha256": (
                "1e4d90031d9c00cabbb31dc16e591c3bcba0c7a2cbd1669f5778b37d091402c3"
            ),
        }
    ):
        raise RuntimeError("V3E scientific design changed.")
    for field, expected in EXPECTED_COUNTS.items():
        if design.get(field) != expected:
            raise RuntimeError(f"V3E count contract changed on {field}.")
    if tuple(design.get("raw_required_columns", ())) != (
        "id",
        "issue_d",
        "term",
        "loan_status",
        "last_pymnt_d",
    ):
        raise RuntimeError("V3E raw column allowlist changed.")
    science = payload["scientific_contract"]
    expected_science = {
        "formula_lower": (
            "mean_score - (resolved_defaults + unresolved_outcomes) / candidate_rows"
        ),
        "formula_upper": "mean_score - resolved_defaults / candidate_rows",
        "binary_completion_class": ("all_independent_zero_or_one_assignments_to_unresolved_rows"),
        "endpoints_jointly_attained": True,
        "exact_identified_set": "finite_grid_with_unresolved_count_plus_one_points",
        "joint_exact_identified_set": "shared_completion_finite_grid_not_cartesian_product",
        "joint_exact_identified_set_formula": (
            "mean_score_vector - ((resolved_defaults + k) / candidate_rows) * ones_5, "
            "k=0,...,unresolved_outcomes"
        ),
        "reported_interval_is_identified_set_hull": True,
        "complete_five_learner_census": True,
        "selection": "none",
        "result_sign_is_stop_condition": False,
    }
    if not isinstance(science, Mapping) or dict(science) != expected_science:
        raise RuntimeError("V3E scientific reporting contract changed.")
    reporting = payload["reporting_contract"]
    expected_reporting = {
        "complete_five_learner_census": True,
        "select_or_rank_learner": False,
        "result_sign_is_stop_condition": False,
        "binary_completion_bounds_are_sampling_intervals": False,
        "verified_point_in_time_snapshot_claim": False,
        "row_level_evaluation_outcomes_loaded": True,
        "row_level_evaluation_outcomes_persisted": False,
        "raw_membership_uses_outcome_status": False,
        "refit_recalibrate_or_optimize": False,
        "selected_or_funded_set_validity": False,
        "causal_or_prospective_interpretation": False,
        "active_before_dvc_verification": False,
    }
    if not isinstance(reporting, Mapping) or dict(reporting) != expected_reporting:
        raise RuntimeError("V3E interpretation boundary changed.")
    stop_rules = payload["stop_rules"]
    expected_stop_rules = {
        "stop_on_dirty_or_non_strict_tagged_head": True,
        "stop_on_noncanonical_config_or_git_blob_mismatch": True,
        "stop_on_runtime_launcher_argv_environment_or_lock_drift": True,
        "stop_on_transitive_authority_or_assert_statement_drift": True,
        "stop_on_source_nested_descriptor_or_source_seal_drift": True,
        "stop_on_raw_score_or_joined_candidate_id_drift": True,
        "stop_on_nonbijective_join_or_issue_month_mismatch": True,
        "stop_on_invalid_or_incomplete_score_census": True,
        "stop_on_endpoint_reason_or_total_drift": True,
        "stop_on_nonfinite_or_reversed_bound": True,
        "stop_on_preexisting_racing_escaping_or_extra_output": True,
        "stop_on_terminal_seal_or_dvc_pointer_mismatch": True,
        "stop_on_result_sign_or_ordering": False,
    }
    if not isinstance(stop_rules, Mapping) or dict(stop_rules) != expected_stop_rules:
        raise RuntimeError("V3E result-independent stop rule changed.")
    execution = payload["execution"]
    expected_bootstrap = {
        "path": BOOTSTRAP_PATH.as_posix(),
        "runtime_manifest": RUNTIME_MANIFEST_PATH.as_posix(),
        "attestation_schema": "2026-07-26.3e-bootstrap-1",
    }
    expected_packages = {
        "numpy": "2.4.6",
        "pandas": "3.0.3",
        "pyarrow": "25.0.0",
        "PyYAML": "6.0.3",
        "python-dateutil": "2.9.0.post0",
        "six": "1.17.0",
        "tzdata": "2026.3",
    }
    canonical_argv_prefix = [
        "C:/Program Files/Calibre2/calibre-debug.exe",
        "-e",
        BOOTSTRAP_PATH.as_posix(),
        "--",
        "--phase",
    ]
    expected_execution = {
        "launcher_kind": "stdlib_authenticated_calibre_bootstrap_then_scientific_runner",
        "bootstrap": expected_bootstrap,
        "executable": {
            "path": "C:/Program Files/Calibre2/calibre-debug.exe",
            "bytes": 32_368,
            "sha256": "f06cbc79c233457bf8bf1c3603981f685a727e7f68c1381c5e56c9cdb592d36b",
            "calibre_version": "7.2.0",
        },
        "python": {
            "implementation": "CPython",
            "version": "3.11.5",
            "optimize": 2,
            "debug": False,
            "assert_statements_permitted_in_scientific_closure": False,
        },
        "project_site_packages": ".venv/Lib/site-packages",
        "handoff_import_paths": [path.as_posix() for path in HANDOFF_IMPORTED_PYTHON_PATHS],
        "calibre_config_directory": (
            ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e-config"
        ),
        "calibre_cache_directory": (
            ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e-calibre-cache"
        ),
        "uv_lock_sha256": "6c862cbad9ab7e3a07dd2823c775127403093d6ad59a789ee227d827165e4733",
        "required_packages": expected_packages,
        "authorized_orig_argv": {
            phase_name: [
                *canonical_argv_prefix,
                phase_name,
                "--config",
                DEFAULT_CONFIG_PATH.as_posix(),
            ]
            for phase_name in (
                "attest-only",
                "handoff-only",
                "pre-source-only",
                "compute",
                "verify-artifact",
            )
        },
    }
    if not isinstance(execution, Mapping) or dict(execution) != expected_execution:
        raise RuntimeError("V3E authenticated bootstrap or package contract changed.")
    authority = payload["authority"]
    if (
        not isinstance(authority, Mapping)
        or tuple(map(Path, authority.get("bootstrap_python_paths", ()))) != BOOTSTRAP_PYTHON_PATHS
        or tuple(map(Path, authority.get("transitive_python_paths", ()))) != TRANSITIVE_PYTHON_PATHS
        or tuple(map(Path, authority.get("nonpython_authority_paths", ())))
        != NONPYTHON_AUTHORITY_PATHS
    ):
        raise RuntimeError("V3E transitive authority census changed.")
    output = payload["output"]
    expected_output = {
        "data_root": ALLOWED_DATA_ROOT.as_posix(),
        "model_root": ALLOWED_MODEL_ROOT.as_posix(),
        "table": "evaluation/marginal_mean_score_outcome_gap.parquet",
        "endpoint_reason_census": "evaluation/endpoint_reason_census.parquet",
        "monthly_endpoint_reason_census": ("evaluation/monthly_endpoint_reason_census.parquet"),
        "summary": "marginal_mean_score_outcome_gap_summary.json",
        "execution_receipt": "execution_receipt.json",
        "execution_seal": "execution_seal.json",
        "immutability": "exclusive_create_no_overwrite_no_retry_same_run_tag",
    }
    if not isinstance(output, Mapping):
        raise TypeError("V3E output contract must be a mapping.")
    for key, value in expected_output.items():
        if output.get(key) != value:
            raise RuntimeError(f"V3E output contract changed on {key}.")
    artifact = output.get("artifact_registration")
    expected_artifact_paths = [
        (
            "data/processed/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/evaluation/"
            "marginal_mean_score_outcome_gap.parquet"
        ),
        (
            "data/processed/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/evaluation/"
            "endpoint_reason_census.parquet"
        ),
        (
            "data/processed/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/evaluation/"
            "monthly_endpoint_reason_census.parquet"
        ),
        (
            "models/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/"
            "marginal_mean_score_outcome_gap_summary.json"
        ),
        (
            "models/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/execution_receipt.json"
        ),
        (
            "models/experiments/ijds_audit/"
            "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3e/execution_seal.json"
        ),
    ]
    if (
        not isinstance(artifact, Mapping)
        or artifact.get("performed_by_compute_phase") is not False
        or artifact.get("required_before_promotion") is not True
        or artifact.get("transport") != "git_force_tracked_direct_child_commit"
        or artifact.get("dvc_tracked") is not False
        or artifact.get("expected_files") != 6
        or artifact.get("max_total_bytes") != 5_000_000
        or artifact.get("expected_paths") != expected_artifact_paths
        or artifact.get("clean_clone_required_source_pointers")
        != [
            "data/raw/Loan_status_2007-2020Q3.csv.dvc",
            "data/processed/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b.dvc",
            "models/experiments/ijds_audit/ijds-credit-risk-controls-2026-07-13-v1b.dvc",
        ]
    ):
        raise RuntimeError("V3E Git-native artifact promotion boundary changed.")
    return payload


def _git(
    args: Sequence[str], *, repo_root: Path, binary: bool = False, check: bool = True
) -> bytes | str:
    return git_command(
        args,
        repo_root=repo_root,
        binary=binary,
        check=check,
    )


def _resolve_strict_tag(repo_root: Path, tag: str) -> str:
    value = str(tag)
    reference = f"refs/tags/{value}"
    if value.startswith(("-", "refs/")) or any(token in value for token in ("^", "~", ":")):
        raise RuntimeError(f"Tag is not an explicit safe tag name: {tag!r}.")
    valid = subprocess.run(
        [str(GIT_EXECUTABLE), "check-ref-format", reference],
        cwd=repo_root,
        env=_git_environment(),
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if valid.returncode != 0:
        raise RuntimeError(f"Tag is not a valid explicit ref: {tag!r}.")
    output = _git(
        ["rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}"],
        repo_root=repo_root,
    )
    commit = str(output).strip()
    if not HEX40.fullmatch(commit):
        raise RuntimeError(f"Tag {tag!r} did not resolve to a full commit.")
    return commit


def _git_snapshot(repo_root: Path) -> dict[str, Any]:
    commit = str(_git(["rev-parse", "HEAD"], repo_root=repo_root)).strip()
    if not HEX40.fullmatch(commit):
        raise RuntimeError("Git HEAD is unavailable or abbreviated.")
    status = _git(
        ["status", "--porcelain=v2", "-z", "--untracked-files=all"],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(status, bytes):
        raise TypeError("Git porcelain status was not captured as bytes.")
    return {
        "commit": commit,
        "porcelain_v2_sha256": hashlib.sha256(status).hexdigest(),
        "porcelain_v2_bytes": len(status),
        "clean": len(status) == 0,
    }


def _require_clean_tagged_head(repo_root: Path, tag: str) -> dict[str, Any]:
    snapshot = _git_snapshot(repo_root)
    if snapshot["clean"] is not True:
        raise RuntimeError("V3E requires an exactly clean tracked/index/untracked worktree.")
    tagged = _resolve_strict_tag(repo_root, tag)
    if snapshot["commit"] != tagged:
        raise RuntimeError(f"Explicit tag {tag!r} does not resolve exactly to HEAD.")
    return snapshot


def _require_ancestor(*, ancestor: str, descendant: str, repo_root: Path) -> None:
    process = subprocess.run(
        [str(GIT_EXECUTABLE), "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        env=_git_environment(),
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Commit {ancestor} is not an ancestor of {descendant}.")


def _require_v3e_protocol_parent(*, protocol_commit: str, repo_root: Path) -> None:
    parent_line = str(
        _git(["rev-list", "--parents", "-n", "1", protocol_commit], repo_root=repo_root)
    ).strip()
    if parent_line.split() != [protocol_commit, ABORTED_V3D_PROTOCOL_COMMIT]:
        raise RuntimeError("V3E protocol commit must be the direct child of aborted V3D.")
    raw = _git(
        ["diff", "--name-only", "-z", ABORTED_V3D_PROTOCOL_COMMIT, protocol_commit, "--"],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(raw, bytes):
        raise TypeError("V3E protocol diff was not captured as bytes.")
    observed = tuple(sorted(value.decode("utf-8") for value in raw.split(b"\0") if value))
    if observed != EXPECTED_V3E_PROTOCOL_DIFF_PATHS:
        raise RuntimeError("V3E protocol commit must contain exactly nine authorized paths.")


def _git_blob(repo_root: Path, *, commit: str, relative_path: str) -> bytes:
    if not HEX40.fullmatch(commit):
        raise RuntimeError("Git blob lookup requires a full commit hash.")
    listing = _git(["ls-tree", "-z", commit, "--", relative_path], repo_root=repo_root, binary=True)
    if not isinstance(listing, bytes):
        raise TypeError("Git tree listing did not return bytes.")
    records = [value for value in listing.split(b"\0") if value]
    if len(records) != 1 or b"\t" not in records[0]:
        raise RuntimeError(f"Git blob path is absent or ambiguous: {relative_path}.")
    header, listed_path = records[0].split(b"\t", 1)
    fields = header.decode("ascii").split()
    if listed_path.decode("utf-8") != relative_path or len(fields) != 3 or fields[1] != "blob":
        raise RuntimeError(f"Git tree entry changed: {relative_path}.")
    object_id = fields[2]
    if not HEX40.fullmatch(object_id):
        raise RuntimeError(f"Git blob ID is malformed: {relative_path}.")
    output = _git(["cat-file", "blob", object_id], repo_root=repo_root, binary=True)
    if not isinstance(output, bytes):
        raise TypeError("Git blob lookup did not return bytes.")
    return output


def require_working_file_matches_git(path: Path, *, commit: str, repo_root: Path) -> dict[str, Any]:
    """Require one working file to equal its exact blob at a full commit."""
    resolved = path.resolve()
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    descriptor = relative_artifact_descriptor(resolved, repo_root=repo_root)
    blob = _git_blob(repo_root, commit=commit, relative_path=relative)
    git_descriptor = _descriptor_from_bytes(blob, relative_path=relative)
    if descriptor != git_descriptor:
        raise RuntimeError(f"On-disk authority differs from Git blob: {relative}.")
    return descriptor


def _module_path(module_name: str, *, repo_root: Path) -> Path | None:
    if module_name != "src" and not module_name.startswith("src."):
        return None
    relative = Path(*module_name.split("."))
    module_file = repo_root / relative.with_suffix(".py")
    package_file = repo_root / relative / "__init__.py"
    if module_file.is_file():
        return module_file.relative_to(repo_root)
    if package_file.is_file():
        return package_file.relative_to(repo_root)
    raise RuntimeError(f"Local import cannot be resolved: {module_name}.")


def _package_initializers(path: Path, *, repo_root: Path) -> set[Path]:
    relative = path.relative_to(repo_root) if path.is_absolute() else path
    parts = relative.parts[:-1]
    initializers: set[Path] = set()
    for index in range(1, len(parts) + 1):
        candidate = Path(*parts[:index]) / "__init__.py"
        if (repo_root / candidate).is_file():
            initializers.add(candidate)
    return initializers


def derive_local_python_closure(*, repo_root: Path) -> tuple[Path, ...]:
    """Derive absolute/relative local imports and process every initializer."""
    return derive_bootstrap_python_closure(
        repo_root=repo_root,
        sealed_sources=_SEALED_AUTHORITY_BYTES or None,
    )


def _require_no_assert_statements(paths: Sequence[Path], *, repo_root: Path) -> None:
    violations: list[str] = []
    for relative in paths:
        data = _SEALED_AUTHORITY_BYTES.get(relative)
        if _SEALED_AUTHORITY_BYTES and data is None:
            raise RuntimeError(f"V3E AST source escaped sealed authority: {relative}.")
        source = (
            data.decode("utf-8")
            if data is not None
            else _stable_file_bytes(repo_root / relative).decode("utf-8")
        )
        tree = ast.parse(source, filename=relative.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                violations.append(f"{relative.as_posix()}:{node.lineno}")
    if violations:
        raise RuntimeError(f"Optimized V3E closure contains assert statements: {violations}.")


def _authority_provenance(
    *, config_path: Path, protocol_commit: str, repo_root: Path
) -> dict[str, Any]:
    derived = derive_local_python_closure(repo_root=repo_root)
    expected = tuple(sorted(TRANSITIVE_PYTHON_PATHS, key=lambda value: value.as_posix()))
    if derived != expected:
        raise RuntimeError(
            "V3E local import closure changed: "
            f"derived={[p.as_posix() for p in derived]}, "
            f"expected={[p.as_posix() for p in expected]}."
        )
    _require_no_assert_statements((*BOOTSTRAP_PYTHON_PATHS, *derived), repo_root=repo_root)
    config_relative = Path(config_path.relative_to(repo_root))
    if config_relative != DEFAULT_CONFIG_PATH or config_relative not in NONPYTHON_AUTHORITY_PATHS:
        raise RuntimeError("V3E locked config is absent from the non-Python authority census.")
    relative_paths = (
        *BOOTSTRAP_PYTHON_PATHS,
        *TRANSITIVE_PYTHON_PATHS,
        *NONPYTHON_AUTHORITY_PATHS,
    )
    if len(relative_paths) != 25 or len(relative_paths) != len(set(relative_paths)):
        raise RuntimeError("V3E authority paths are not the exact unique 25-path census.")
    descriptors: dict[str, dict[str, Any]] = {}
    for relative in relative_paths:
        path = repo_root / relative
        sealed = _SEALED_AUTHORITY_BYTES.get(relative)
        if sealed is None:
            raise RuntimeError(f"V3E provenance path escaped sealed authority: {relative}.")
        disk = _stable_file_bytes(path)
        blob = _git_blob(repo_root, commit=protocol_commit, relative_path=relative.as_posix())
        if disk != sealed or blob != sealed:
            raise RuntimeError(f"V3E sealed, working, and Git bytes disagree: {relative}.")
        descriptor = _descriptor_from_bytes(sealed, relative_path=relative.as_posix())
        descriptors[relative.as_posix()] = descriptor
    return {
        "hash_algorithm": "sha256",
        "protocol_commit": protocol_commit,
        "bootstrap_python_paths": [value.as_posix() for value in BOOTSTRAP_PYTHON_PATHS],
        "transitive_python_paths": [value.as_posix() for value in derived],
        "source_files": descriptors,
        "assert_statements": 0,
        "executed_from_sealed_git_bytes": True,
    }


def _normalize_windows_path(value: str | Path) -> str:
    return Path(value).resolve().as_posix().casefold()


def _runtime_observation(config: Mapping[str, Any], *, phase: str) -> dict[str, Any]:
    bootstrap_attestation = _require_bootstrap_attestation(phase=phase)
    if not _RUNNER_EXECUTED_FROM_SEALED_BYTES:
        raise RuntimeError("V3E runner execution did not originate in sealed bytes.")
    execution = config["execution"]
    executable_spec = execution["executable"]
    executable = Path(sys.executable).resolve()
    executable_actual = {
        "path": executable.as_posix(),
        "bytes": int(executable.stat().st_size),
        "sha256": sha256_file(executable),
    }
    expected_executable = {
        "path": str(executable_spec["path"]),
        "bytes": int(executable_spec["bytes"]),
        "sha256": str(executable_spec["sha256"]),
    }
    actual_executable_path = str(executable_actual["path"])
    expected_executable_path = str(expected_executable["path"])
    if (
        _normalize_windows_path(actual_executable_path)
        != _normalize_windows_path(expected_executable_path)
        or executable_actual["bytes"] != expected_executable["bytes"]
        or executable_actual["sha256"] != expected_executable["sha256"]
    ):
        raise RuntimeError("V3E executable path, bytes, or SHA-256 changed.")
    try:
        from calibre.constants import (  # type: ignore[import-not-found]
            __version__ as calibre_version,
        )
    except ImportError as exc:
        raise RuntimeError("V3E did not start inside the declared Calibre runtime.") from exc
    if calibre_version != str(executable_spec["calibre_version"]):
        raise RuntimeError("V3E Calibre version changed.")

    orig_argv = [str(value) for value in getattr(sys, "orig_argv", ())]
    expected_argv = [str(value) for value in execution["authorized_orig_argv"][phase]]
    if len(orig_argv) != len(expected_argv):
        raise RuntimeError(f"V3E orig_argv length changed: {orig_argv}.")
    if (
        _normalize_windows_path(orig_argv[0]) != _normalize_windows_path(expected_argv[0])
        or orig_argv[1:] != expected_argv[1:]
    ):
        raise RuntimeError(f"V3E was not launched with the authorized argv: {orig_argv}.")

    python_spec = execution["python"]
    observed_python_version = platform.python_version()
    if (
        platform.python_implementation() != python_spec["implementation"]
        or observed_python_version != python_spec["version"]
        or sys.flags.optimize != python_spec["optimize"]
        or bool(__debug__) is not bool(python_spec["debug"])
    ):
        raise RuntimeError("V3E Python implementation, version, or optimize flags changed.")
    site_packages = (ROOT / str(execution["project_site_packages"])).resolve()
    if site_packages != PROJECT_SITE_PACKAGES.resolve() or not site_packages.is_dir():
        raise RuntimeError("V3E project site-packages path changed or is missing.")
    config_directory_raw = os.environ.get("CALIBRE_CONFIG_DIRECTORY")
    if not config_directory_raw:
        raise RuntimeError("CALIBRE_CONFIG_DIRECTORY is required by the V3E runtime.")
    config_directory = Path(config_directory_raw).resolve()
    expected_config_directory = (ROOT / str(execution["calibre_config_directory"])).resolve()
    if config_directory != expected_config_directory or not config_directory.is_dir():
        raise RuntimeError("V3E Calibre configuration directory changed or is missing.")
    cache_directory_raw = os.environ.get("CALIBRE_CACHE_DIRECTORY")
    if not cache_directory_raw:
        raise RuntimeError("CALIBRE_CACHE_DIRECTORY is required by the V3E runtime.")
    cache_directory = Path(cache_directory_raw).resolve()
    expected_cache_directory = (ROOT / str(execution["calibre_cache_directory"])).resolve()
    if cache_directory != expected_cache_directory or not cache_directory.is_dir():
        raise RuntimeError("V3E Calibre cache directory changed or is missing.")
    lock_path = ROOT / "uv.lock"
    if sha256_file(lock_path) != execution["uv_lock_sha256"]:
        raise RuntimeError("V3E uv.lock changed.")

    required_packages = execution["required_packages"]
    observed_packages = {name: importlib.metadata.version(name) for name in required_packages}
    if observed_packages != dict(required_packages):
        raise RuntimeError(
            f"V3E imported package versions changed: {observed_packages} != {required_packages}."
        )
    module_paths = {
        "dateutil": Path(dateutil.__file__).resolve().as_posix(),
        "numpy": Path(np.__file__).resolve().as_posix(),
        "pandas": Path(pd.__file__).resolve().as_posix(),
        "pyarrow": Path(pyarrow.__file__).resolve().as_posix(),
        "PyYAML": Path(yaml.__file__).resolve().as_posix(),
        "six": Path(six.__file__).resolve().as_posix(),
        "tzdata": Path(tzdata.__file__).resolve().as_posix(),
    }
    site_prefix = site_packages.as_posix().casefold() + "/"
    if any(not path.casefold().startswith(site_prefix) for path in module_paths.values()):
        raise RuntimeError("A V3E scientific package was not imported from project site-packages.")
    runtime_manifest_bytes = _SEALED_AUTHORITY_BYTES.get(BOOTSTRAP_RUNTIME_MANIFEST_PATH)
    if runtime_manifest_bytes is None:
        raise RuntimeError("V3E runtime manifest is absent from sealed authority bytes.")
    runtime_manifest = load_bootstrap_runtime_manifest(
        repo_root=ROOT, sealed_bytes=runtime_manifest_bytes
    )
    expected_modules = {
        "dateutil": runtime_manifest["module_paths"]["dateutil"],
        "numpy": runtime_manifest["module_paths"]["numpy"],
        "pandas": runtime_manifest["module_paths"]["pandas"],
        "pyarrow": runtime_manifest["module_paths"]["pyarrow"],
        "PyYAML": runtime_manifest["module_paths"]["yaml"],
        "six": runtime_manifest["module_paths"]["six"],
        "tzdata": runtime_manifest["module_paths"]["tzdata"],
    }
    expected_module_paths = {
        name: (ROOT / relative).resolve().as_posix() for name, relative in expected_modules.items()
    }
    if module_paths != expected_module_paths:
        raise RuntimeError(
            f"V3E scientific module paths changed: {module_paths} != {expected_module_paths}."
        )
    local_modules = {
        "src.data.outcome_observability": ROOT / "src/data/outcome_observability.py",
        "src.ijds_audit.marginal_mean_score_outcome_gap_v3e": (
            ROOT / "src/ijds_audit/marginal_mean_score_outcome_gap_v3e.py"
        ),
        "src.utils.artifact_descriptor": ROOT / "src/utils/artifact_descriptor.py",
    }
    local_module_paths: dict[str, str] = {}
    for name, expected_path in local_modules.items():
        module = sys.modules.get(name)
        observed_file = Path(str(getattr(module, "__file__", ""))).resolve()
        if module is None or observed_file != expected_path.resolve():
            raise RuntimeError(f"V3E local module {name!r} was shadowed: {observed_file}.")
        cached = getattr(module, "__cached__", None)
        if cached and Path(str(cached)).exists():
            raise RuntimeError(f"V3E local module {name!r} executed existing bytecode: {cached}.")
        local_module_paths[name] = observed_file.as_posix()
    expected_sys_path = [ROOT.resolve().as_posix(), site_packages.resolve().as_posix()]
    observed_sys_path = [Path(value).resolve().as_posix() for value in sys.path]
    if observed_sys_path != expected_sys_path:
        raise RuntimeError(f"V3E scientific sys.path changed: {observed_sys_path}.")
    sealed_import_runtime = require_sealed_import_runtime(_SEALED_AUTHORITY_BYTES, repo_root=ROOT)
    carrier_globals = getattr(_require_revalidation_callback(), "__globals__", None)
    if not isinstance(carrier_globals, dict):
        raise RuntimeError("V3E carrier-bound callback globals are unavailable.")
    require_loaded_module_origins(
        runtime_manifest,
        _SEALED_AUTHORITY_BYTES,
        entrypoint_globals=carrier_globals,
        repo_root=ROOT,
    )
    return {
        "launcher_kind": execution["launcher_kind"],
        "executable": executable_actual,
        "calibre_version": calibre_version,
        "orig_argv": orig_argv,
        "sys_argv": [str(value) for value in sys.argv],
        "python": {
            "implementation": platform.python_implementation(),
            "version": observed_python_version,
            "full_version": sys.version,
            "optimize": sys.flags.optimize,
            "debug": bool(__debug__),
        },
        "platform": platform.platform(),
        "project_site_packages": site_packages.relative_to(ROOT).as_posix(),
        "calibre_config_directory": config_directory.relative_to(ROOT).as_posix(),
        "calibre_cache_directory": cache_directory.relative_to(ROOT).as_posix(),
        "packages": observed_packages,
        "module_paths": {
            name: Path(path).relative_to(ROOT).as_posix() for name, path in module_paths.items()
        },
        "local_module_paths": {
            name: Path(path).relative_to(ROOT).as_posix()
            for name, path in local_module_paths.items()
        },
        "runner_executed_from_sealed_bytes": True,
        "sealed_import_runtime": sealed_import_runtime,
        "native_module_policy": {
            "all_loaded_extensions_within_sealed_inventories": True,
            "calibre_native_directory": runtime_manifest["calibre"]["native_directory"],
            "venv_distribution_composites": runtime_manifest["distributions"],
        },
        "scientific_sys_path": [".", execution["project_site_packages"]],
        "uv_lock_sha256": sha256_file(lock_path),
        "pythonoptimize_environment": os.environ.get("PYTHONOPTIMIZE"),
        "bootstrap_attestation": bootstrap_attestation,
    }


def _md5_file(path: Path, *, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _hash_open_handle(handle: BinaryIO, *, block_size: int = 8 * 1024 * 1024) -> dict[str, Any]:
    sha_digest = hashlib.sha256()
    md5_digest = hashlib.md5(usedforsecurity=False)
    handle.seek(0)
    size = 0
    while block := handle.read(block_size):
        size += len(block)
        sha_digest.update(block)
        md5_digest.update(block)
    handle.seek(0)
    return {"bytes": size, "sha256": sha_digest.hexdigest(), "dvc_md5": md5_digest.hexdigest()}


def _single_dvc_out(data: bytes, *, label: str) -> dict[str, Any]:
    payload = yaml.safe_load(data.decode("utf-8"))
    if not isinstance(payload, Mapping) or set(payload) != {"outs"}:
        raise RuntimeError(f"{label} DVC pointer schema changed.")
    outs = payload["outs"]
    if not isinstance(outs, list) or len(outs) != 1 or not isinstance(outs[0], Mapping):
        raise RuntimeError(f"{label} DVC pointer must contain exactly one out.")
    out = dict(outs[0])
    md5 = str(out.get("md5", ""))
    directory = md5.endswith(".dir")
    expected_fields = {"md5", "size", "hash", "path"}
    if directory:
        expected_fields.add("nfiles")
    if set(out) != expected_fields:
        raise RuntimeError(f"{label} DVC out fields changed: {sorted(out)}.")
    digest = md5[:-4] if directory else md5
    relative = Path(str(out.get("path", "")))
    if (
        not re.fullmatch(r"[0-9a-f]{32}", digest)
        or out.get("hash") != "md5"
        or isinstance(out.get("size"), bool)
        or not isinstance(out.get("size"), int)
        or int(out["size"]) < 0
        or relative.is_absolute()
        or str(relative) in {"", ".", ".."}
        or ".." in relative.parts
    ):
        raise RuntimeError(f"{label} DVC out types or values changed.")
    if directory and (
        isinstance(out.get("nfiles"), bool)
        or not isinstance(out.get("nfiles"), int)
        or int(out["nfiles"]) < 0
    ):
        raise RuntimeError(f"{label} DVC directory file count changed type or sign.")
    return out


def _require_same_descriptor(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor changed on {field}.")


def _source_seal(
    config: Mapping[str, Any], *, repo_root: Path, return_bytes: bool = False
) -> tuple[dict[str, Any], dict[str, bytes]]:
    source = config["source"]
    descriptors: dict[str, dict[str, Any]] = {}
    captured: dict[str, bytes] = {}
    for key, specification in source.items():
        if key == "raw_archive":
            path = _resolve_repo_file(str(specification["path"]), repo_root=repo_root)
            actual = relative_artifact_descriptor(path, repo_root=repo_root)
            _require_same_descriptor(actual, specification, label="Raw archive")
            raw_md5 = _md5_file(path)
            if raw_md5 != specification["dvc_md5"]:
                raise RuntimeError("Raw archive DVC MD5 changed.")
            descriptors[key] = {**actual, "dvc_md5": raw_md5}
            continue
        path, data = _read_verified_bytes(
            specification, label=f"V3E source {key}", repo_root=repo_root
        )
        descriptors[key] = _descriptor_from_bytes(
            data, relative_path=path.relative_to(repo_root).as_posix()
        )
        if return_bytes:
            captured[key] = data
    canonical = json.dumps(
        descriptors, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return (
        {
            "hash_algorithm": "sha256",
            "artifacts": descriptors,
            "composite_sha256": hashlib.sha256(canonical).hexdigest(),
        },
        captured,
    )


def _validate_source_lineage(
    config: Mapping[str, Any],
    *,
    captured: Mapping[str, bytes],
    evaluation_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    source = config["source"]
    identity = config["source_identity"]
    freeze = json.loads(captured["credit_control_freeze"].decode("utf-8"))
    expected_freeze_identity = {
        "status": identity["credit_control_freeze_status"],
        "run_tag": identity["credit_control_freeze_run_tag"],
        "protocol_tag": identity["credit_control_freeze_protocol_tag"],
        "protocol_commit": identity["credit_control_freeze_protocol_commit"],
    }
    for field, expected in expected_freeze_identity.items():
        if freeze.get(field) != expected:
            raise RuntimeError(f"Credit-control freeze identity changed on {field}.")
    source_commit = str(identity["credit_control_freeze_protocol_commit"])
    if (
        _resolve_strict_tag(repo_root, str(identity["credit_control_freeze_protocol_tag"]))
        != source_commit
    ):
        raise RuntimeError("Credit-control source tag no longer resolves to its pinned commit.")
    _require_ancestor(ancestor=source_commit, descendant=evaluation_commit, repo_root=repo_root)
    if (
        freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []
        or freeze.get("sampling") != identity["credit_control_sampling"]
        or freeze.get("model_selection") != identity["credit_control_model_selection"]
        or tuple(freeze.get("co_primary_learners", ())) != LEARNERS
    ):
        raise RuntimeError("Credit-control outcome-free or no-selection contract changed.")
    artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(artifacts, Mapping) or not isinstance(artifacts.get("scores"), Mapping):
        raise RuntimeError("Credit-control freeze omits its score descriptor.")
    _require_same_descriptor(artifacts["scores"], source["scores"], label="Freeze-to-scores")
    inventory = freeze.get("source_inventory")
    retained = inventory.get("retained_rows_by_split") if isinstance(inventory, Mapping) else None
    if (
        not isinstance(retained, Mapping)
        or retained.get(ROLE) != EXPECTED_COUNTS["expected_candidates"]
    ):
        raise RuntimeError("Credit-control primary OOT source census changed.")

    raw_audit = json.loads(captured["raw_audit_evidence"].decode("utf-8"))
    if (
        raw_audit.get("status") != identity["raw_audit_status"]
        or raw_audit.get("run_tag") != identity["raw_audit_run_tag"]
        or raw_audit.get("results", {}).get("raw_rows") != identity["raw_rows"]
    ):
        raise RuntimeError("Raw-audit identity or row census changed.")
    _require_same_descriptor(
        raw_audit.get("raw_source", {}), source["raw_archive"], label="Raw-audit-to-archive"
    )
    if raw_audit.get("raw_source", {}).get("dvc_md5") != source["raw_archive"]["dvc_md5"]:
        raise RuntimeError("Raw-audit DVC MD5 changed.")
    _require_same_descriptor(
        raw_audit.get("config", {}), source["raw_audit_config"], label="Raw-audit-to-config"
    )

    raw_pointer = _single_dvc_out(captured["raw_dvc_pointer"], label="Raw archive")
    if (
        raw_pointer.get("md5") != source["raw_archive"]["dvc_md5"]
        or raw_pointer.get("size") != source["raw_archive"]["bytes"]
        or raw_pointer.get("path") != Path(source["raw_archive"]["path"]).name
        or raw_pointer.get("hash") != "md5"
    ):
        raise RuntimeError("Raw DVC pointer no longer describes the hash-pinned archive.")
    score_data_pointer = _single_dvc_out(captured["score_data_dvc_pointer"], label="Score data")
    score_model_pointer = _single_dvc_out(captured["score_model_dvc_pointer"], label="Score model")
    score_dvc_directories: dict[str, dict[str, Any]] = {}
    for label, pointer in (
        ("data", score_data_pointer),
        ("model", score_model_pointer),
    ):
        if (
            pointer.get("path") != identity["credit_control_freeze_run_tag"]
            or not str(pointer.get("md5", "")).endswith(".dir")
            or pointer.get("hash") != "md5"
        ):
            raise RuntimeError(f"Credit-control {label} DVC pointer changed.")
        pointer_key = f"score_{label}_dvc_pointer"
        pointer_path = _resolve_repo_file(str(source[pointer_key]["path"]), repo_root=repo_root)
        directory = (pointer_path.parent / str(pointer["path"])).resolve()
        observed_directory = _dvc_directory_descriptor(directory)
        for field in ("md5", "size", "nfiles", "hash"):
            if pointer.get(field) != observed_directory[field]:
                raise RuntimeError(f"Credit-control {label} DVC directory changed on {field}.")
        score_dvc_directories[label] = {
            "directory": directory.relative_to(repo_root).as_posix(),
            **observed_directory,
        }
    score_path = _resolve_repo_file(str(source["scores"]["path"]), repo_root=repo_root)
    freeze_path = _resolve_repo_file(
        str(source["credit_control_freeze"]["path"]), repo_root=repo_root
    )
    data_directory = repo_root / score_dvc_directories["data"]["directory"]
    model_directory = repo_root / score_dvc_directories["model"]["directory"]
    try:
        score_path.relative_to(data_directory.resolve())
        freeze_path.relative_to(model_directory.resolve())
    except ValueError as exc:
        raise RuntimeError(
            "Credit-control score or freeze escaped its verified DVC directory."
        ) from exc
    return {
        "credit_control_freeze_identity": expected_freeze_identity,
        "credit_control_tag_and_ancestry": True,
        "freeze_to_scores_descriptor": True,
        "freeze_primary_oot_census": int(retained[ROLE]),
        "raw_audit_to_archive_descriptor": True,
        "raw_audit_to_config_descriptor": True,
        "raw_dvc_pointer_to_archive": True,
        "credit_control_dvc_pointers": True,
        "credit_control_dvc_directories": score_dvc_directories,
        "score_and_freeze_inside_verified_dvc_directories": True,
    }


def _require_git_bound_sources(config: Mapping[str, Any], *, commit: str, repo_root: Path) -> None:
    for key in GIT_BOUND_SOURCE_KEYS:
        descriptor = config["source"][key]
        relative = str(descriptor["path"])
        blob = _git_blob(repo_root, commit=commit, relative_path=relative)
        observed = _descriptor_from_bytes(blob, relative_path=relative)
        _require_same_descriptor(observed, descriptor, label=f"Git-bound source {key}")


def _load_scientific_sources(
    config: Mapping[str, Any], *, protocol_commit: str, repo_root: Path
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    initial_seal, captured = _source_seal(config, repo_root=repo_root, return_bytes=True)
    lineage = _validate_source_lineage(
        config,
        captured=captured,
        evaluation_commit=protocol_commit,
        repo_root=repo_root,
    )
    score_columns = ["id", "issue_d", "design_split", *SCORE_COLUMNS.values()]
    scores = pd.read_parquet(io.BytesIO(captured["scores"]))
    if tuple(str(value) for value in scores.columns) != tuple(score_columns):
        raise RuntimeError("Frozen score Parquet schema changed or acquired undeclared columns.")

    raw_spec = config["source"]["raw_archive"]
    raw_path = _resolve_repo_file(str(raw_spec["path"]), repo_root=repo_root)
    design = config["design"]
    with raw_path.open("rb") as handle:
        raw_handle_before = _hash_open_handle(handle)
        expected_raw_handle = {
            "bytes": int(raw_spec["bytes"]),
            "sha256": str(raw_spec["sha256"]),
            "dvc_md5": str(raw_spec["dvc_md5"]),
        }
        if raw_handle_before != expected_raw_handle:
            raise RuntimeError("Opened raw archive does not equal its locked descriptor.")
        scan = scan_primary_oot_raw_archive(
            handle,
            required_columns=design["raw_required_columns"],
            csv_chunksize=int(design["csv_chunksize"]),
            term_months=int(design["term_months"]),
            start_month=str(design["primary_oot_start_month"]),
            end_month=str(design["primary_oot_end_month"]),
            expected_raw_rows=int(design["expected_raw_rows"]),
            expected_candidates=int(design["expected_candidates"]),
            expected_issue_months=design["issue_months"],
            expected_candidate_ids=scores.loc[scores["design_split"].astype(str).eq(ROLE), "id"],
        )
        raw_handle_after = _hash_open_handle(handle)
    if raw_handle_after != raw_handle_before:
        raise RuntimeError("Raw archive changed while its target rows were scanned.")
    if scan.audit["candidate_id_sha256"] != EXPECTED_CANDIDATE_ID_SHA256:
        raise RuntimeError("Raw target ID hash changed before the outcome join.")
    endpoint = build_row_level_endpoint(
        scan.frame,
        cutoff=str(design["endpoint_cutoff"]),
        charged_off_lag_months=int(design["charged_off_availability_lag_months"]),
    )
    return scores, endpoint, initial_seal, {"lineage": lineage, "raw_scan": scan.audit}


def _run_directory(*, repo_root: Path, configured_root: str, allowed_root: Path) -> Path:
    root = repo_root.resolve()
    configured = (root / configured_root).resolve()
    allowed = (root / allowed_root).resolve()
    if configured != allowed:
        raise RuntimeError("V3E output root left its exact allowlist.")
    candidate = (allowed / RUN_TAG).resolve()
    relative = candidate.relative_to(allowed)
    if len(relative.parts) != 1 or relative.name != RUN_TAG:
        raise RuntimeError("V3E output must be one direct run-tag child.")
    return candidate


def _contained_target(base: Path, relative_value: Any, *, suffix: str) -> Path:
    relative = Path(str(relative_value))
    if relative.is_absolute() or str(relative) in {"", ".", ".."}:
        raise RuntimeError(f"Unsafe V3E output path: {relative_value!r}.")
    target = (base / relative).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as exc:
        raise RuntimeError(f"V3E output escapes its run directory: {target}.") from exc
    if target.suffix.casefold() != suffix.casefold():
        raise RuntimeError(f"V3E output {target} must use {suffix}.")
    return target


def output_targets(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[Path, Path, dict[str, Path]]:
    output = config["output"]
    data_dir = _run_directory(
        repo_root=repo_root,
        configured_root=str(output["data_root"]),
        allowed_root=ALLOWED_DATA_ROOT,
    )
    model_dir = _run_directory(
        repo_root=repo_root,
        configured_root=str(output["model_root"]),
        allowed_root=ALLOWED_MODEL_ROOT,
    )
    targets = {
        "table": _contained_target(data_dir, output["table"], suffix=".parquet"),
        "endpoint_reason_census": _contained_target(
            data_dir, output["endpoint_reason_census"], suffix=".parquet"
        ),
        "monthly_endpoint_reason_census": _contained_target(
            data_dir, output["monthly_endpoint_reason_census"], suffix=".parquet"
        ),
        "summary": _contained_target(model_dir, output["summary"], suffix=".json"),
        "execution_receipt": _contained_target(
            model_dir, output["execution_receipt"], suffix=".json"
        ),
        "execution_seal": _contained_target(model_dir, output["execution_seal"], suffix=".json"),
    }
    rendered = [str(path).casefold() for path in targets.values()]
    if len(rendered) != len(set(rendered)):
        raise RuntimeError("V3E output paths alias one another.")
    expected_paths = sorted(
        str(value) for value in output["artifact_registration"]["expected_paths"]
    )
    actual_paths = sorted(
        path.relative_to(repo_root.resolve()).as_posix() for path in targets.values()
    )
    if actual_paths != expected_paths:
        raise RuntimeError("V3E Git-native artifact path census changed.")
    return data_dir, model_dir, targets


def _preflight_outputs(config: Mapping[str, Any], *, repo_root: Path) -> None:
    data_dir, model_dir, targets = output_targets(config, repo_root=repo_root)
    occupied = [path for path in (data_dir, model_dir) if path.exists()]
    if occupied:
        raise FileExistsError(f"V3E run path is occupied: {occupied}.")
    if any(path.exists() for path in targets.values()):
        raise FileExistsError("A V3E output target already exists.")


def _exclusive_link_promote(temporary: Path, target: Path) -> Path:
    if target.exists():
        temporary.unlink(missing_ok=True)
        raise FileExistsError(f"Immutable V3E target already exists: {target}.")
    try:
        os.link(temporary, target)
    except FileExistsError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    temporary.unlink()
    return target


def _exclusive_write_bytes(target: Path, payload: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return _exclusive_link_promote(temporary, target)


def _exclusive_write_json(target: Path, payload: Mapping[str, Any]) -> Path:
    data = (
        json.dumps(
            dict(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return _exclusive_write_bytes(target, data)


def _exclusive_write_parquet(target: Path, frame: pd.DataFrame) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}")
    with temporary.open("xb") as handle:
        frame.to_parquet(handle, index=False)
        handle.flush()
        os.fsync(handle.fileno())
    return _exclusive_link_promote(temporary, target)


def _inventory(root: Path) -> tuple[str, ...]:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"V3E output root is missing or symlinked: {root}.")
    for directory in [root, *[path for path in root.rglob("*") if path.is_dir()]]:
        if directory.is_symlink():
            raise RuntimeError(f"V3E output contains a symlinked directory: {directory}.")
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"V3E output contains a symlink: {path}.")
        if path.is_file():
            files.append(path.relative_to(root).as_posix())
    return tuple(sorted(files))


def _expected_inventories(config: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    output = config["output"]
    return (
        tuple(
            sorted(
                (
                    str(output["table"]),
                    str(output["endpoint_reason_census"]),
                    str(output["monthly_endpoint_reason_census"]),
                )
            )
        ),
        tuple(
            sorted(
                (
                    str(output["summary"]),
                    str(output["execution_receipt"]),
                    str(output["execution_seal"]),
                )
            )
        ),
    )


def _require_output_inventory(config: Mapping[str, Any], *, repo_root: Path) -> None:
    data_dir, model_dir, _targets = output_targets(config, repo_root=repo_root)
    expected_data, expected_model = _expected_inventories(config)
    observed_data = _inventory(data_dir)
    observed_model = _inventory(model_dir)
    if observed_data != expected_data or observed_model != expected_model:
        raise RuntimeError(
            "V3E output inventory changed: "
            f"data={observed_data}/{expected_data}, model={observed_model}/{expected_model}."
        )


def _scientific_result(
    config: Mapping[str, Any], scores: pd.DataFrame, endpoint: pd.DataFrame
) -> MarginalMeanScoreOutcomeGapV3EResult:
    design = config["design"]
    return marginal_mean_score_outcome_gap_v3e(
        scores,
        endpoint,
        learners=design["learners"],
        score_columns=design["score_columns"],
        role=str(design["role"]),
        expected_issue_months=design["issue_months"],
        expected_candidate_id_sha256=str(design["expected_candidate_id_sha256"]),
        expected_endpoint_row_sha256=str(design["expected_endpoint_row_sha256"]),
        expected_reason_census=design["endpoint_reason_census"],
        expected_monthly_reason_candidate_rows=design["monthly_reason_candidate_rows"],
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )


def _authority_snapshot(
    config: Mapping[str, Any],
    *,
    config_path: Path,
    phase: str,
    tag: str,
    protocol_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    git = _require_clean_tagged_head(repo_root, tag)
    authority = _authority_provenance(
        config_path=config_path,
        protocol_commit=protocol_commit,
        repo_root=repo_root,
    )
    _require_git_bound_sources(config, commit=protocol_commit, repo_root=repo_root)
    runtime = _runtime_observation(config, phase=phase)
    return {"git": git, "implementation": authority, "runtime": runtime}


def _require_same_authority(
    expected: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    config_path: Path,
    phase: str,
    tag: str,
    protocol_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    observed = _authority_snapshot(
        config,
        config_path=config_path,
        phase=phase,
        tag=tag,
        protocol_commit=protocol_commit,
        repo_root=repo_root,
    )
    if observed != dict(expected):
        raise RuntimeError("V3E Git, implementation, or runtime authority drifted.")
    return observed


def _table_schema(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
    }


def _scientific_summary_payload(
    config: Mapping[str, Any],
    *,
    result: MarginalMeanScoreOutcomeGapV3EResult,
    source_seal: Mapping[str, Any],
    source_audit: Mapping[str, Any],
    protocol_commit: str,
    artifact_descriptors: Mapping[str, Any],
) -> dict[str, Any]:
    table = result.table
    lower = "marginal_mean_score_outcome_gap_lower"
    upper = "marginal_mean_score_outcome_gap_upper"
    design = config["design"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "complete_clean_tagged_v3e_pending_git_artifact_commit",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "artifact_tag_required_before_promotion": ARTIFACT_TAG,
        "estimand": ESTIMAND,
        "candidate_identity": result.join_audit,
        "endpoint_row_sha256": result.endpoint_row_sha256,
        "issue_months": list(result.issue_months),
        "endpoint": {
            "cutoff": design["endpoint_cutoff"],
            "charged_off_availability_lag_months": design["charged_off_availability_lag_months"],
            "resolved_rows": design["expected_resolved"],
            "resolved_nondefaults": design["expected_resolved_y0"],
            "resolved_defaults": design["expected_resolved_y1"],
            "unresolved_rows": design["expected_unresolved"],
            "reason_census": result.endpoint_reason_census.to_dict(orient="records"),
        },
        "identification": {
            "lower_formula": config["scientific_contract"]["formula_lower"],
            "upper_formula": config["scientific_contract"]["formula_upper"],
            "completion_class": config["scientific_contract"]["binary_completion_class"],
            "sharp_binary_completions": True,
            "joint_endpoint_attainment": True,
            "exact_identified_set": "finite_grid_with_unresolved_count_plus_one_points",
            "joint_exact_identified_set": ("shared_completion_finite_grid_not_cartesian_product"),
            "joint_exact_identified_set_formula": config["scientific_contract"][
                "joint_exact_identified_set_formula"
            ],
            "identified_grid_points": int(table["identified_grid_points"].iloc[0]),
            "identified_grid_step": float(table["identified_grid_step"].iloc[0]),
            "reported_interval_is_identified_set_hull": True,
            "sampling_interval": False,
        },
        "results": {
            "learners": int(len(table)),
            "learner_order": table["learner"].astype(str).tolist(),
            "outcome_mean_identification_interval": [
                float(table["outcome_mean_lower"].iloc[0]),
                float(table["outcome_mean_upper"].iloc[0]),
            ],
            "identification_width": float(table["identification_width"].iloc[0]),
            "mean_score_range": [
                float(table["mean_score"].min()),
                float(table["mean_score"].max()),
            ],
            "gap_lower_range": [float(table[lower].min()), float(table[lower].max())],
            "gap_upper_range": [float(table[upper].min()), float(table[upper].max())],
            "all_results_reported_without_sign_condition": True,
        },
        "source_audit": dict(source_audit),
        "source_seal": dict(source_seal),
        "schemas": {
            "marginal_mean_score_outcome_gap": _table_schema(result.table),
            "endpoint_reason_census": _table_schema(result.endpoint_reason_census),
            "monthly_endpoint_reason_census": _table_schema(result.monthly_endpoint_reason_census),
        },
        "artifacts": dict(artifact_descriptors),
        "reporting_contract": dict(config["reporting_contract"]),
        "git_artifact_commit_performed": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def _write_compute_outputs(
    config: Mapping[str, Any],
    *,
    config_path: Path,
    result: MarginalMeanScoreOutcomeGapV3EResult,
    source_seal: Mapping[str, Any],
    source_audit: Mapping[str, Any],
    initial_authority: Mapping[str, Any],
    started_at: str,
    started_counter: float,
    repo_root: Path,
) -> Path:
    data_dir, model_dir, targets = output_targets(config, repo_root=repo_root)
    data_dir.mkdir(parents=False, exist_ok=False)
    model_dir.mkdir(parents=False, exist_ok=False)
    table_path = _exclusive_write_parquet(targets["table"], result.table)
    endpoint_path = _exclusive_write_parquet(
        targets["endpoint_reason_census"], result.endpoint_reason_census
    )
    monthly_path = _exclusive_write_parquet(
        targets["monthly_endpoint_reason_census"], result.monthly_endpoint_reason_census
    )
    pd.testing.assert_frame_equal(
        pd.read_parquet(table_path), result.table, check_dtype=True, check_exact=True
    )
    pd.testing.assert_frame_equal(
        pd.read_parquet(endpoint_path),
        result.endpoint_reason_census,
        check_dtype=True,
        check_exact=True,
    )
    pd.testing.assert_frame_equal(
        pd.read_parquet(monthly_path),
        result.monthly_endpoint_reason_census,
        check_dtype=True,
        check_exact=True,
    )
    artifact_paths = {
        "marginal_mean_score_outcome_gap": table_path,
        "endpoint_reason_census": endpoint_path,
        "monthly_endpoint_reason_census": monthly_path,
    }
    artifact_descriptors = {
        key: relative_artifact_descriptor(path, repo_root=repo_root)
        for key, path in artifact_paths.items()
    }
    summary = _scientific_summary_payload(
        config,
        result=result,
        source_seal=source_seal,
        source_audit=source_audit,
        protocol_commit=str(initial_authority["git"]["commit"]),
        artifact_descriptors=artifact_descriptors,
    )
    summary_path = _exclusive_write_json(targets["summary"], summary)
    summary_descriptor = relative_artifact_descriptor(summary_path, repo_root=repo_root)
    preterminal_source_seal, _ = _source_seal(config, repo_root=repo_root)
    if preterminal_source_seal != dict(source_seal):
        raise RuntimeError("V3E sources drifted before the terminal receipt and seal.")
    preterminal_authority = _require_same_authority(
        initial_authority,
        config,
        config_path=config_path,
        phase="compute",
        tag=PROTOCOL_TAG,
        protocol_commit=str(initial_authority["git"]["commit"]),
        repo_root=repo_root,
    )
    final_git = preterminal_authority["git"]
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete_clean_tagged_v3e_receipt_pending_git_artifact_commit",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": initial_authority["git"]["commit"],
        "artifact_tag_required_before_promotion": ARTIFACT_TAG,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "initial_git": initial_authority["git"],
        "preterminal_git": final_git,
        "implementation_provenance": initial_authority["implementation"],
        "runtime": initial_authority["runtime"],
        "initial_source_seal": dict(source_seal),
        "preterminal_source_seal": preterminal_source_seal,
        "summary": summary_descriptor,
        "artifacts": artifact_descriptors,
        "preterminal_implementation_provenance": preterminal_authority["implementation"],
        "preterminal_runtime": preterminal_authority["runtime"],
        "git_artifact_commit": {
            "performed": False,
            "required_before_promotion": True,
            "transport": "git_force_tracked_direct_child_commit",
            "dvc_tracked": False,
            "expected_paths": config["output"]["artifact_registration"]["expected_paths"],
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    receipt_path = _exclusive_write_json(targets["execution_receipt"], receipt)
    receipt_descriptor = relative_artifact_descriptor(receipt_path, repo_root=repo_root)
    final_source_seal, _ = _source_seal(config, repo_root=repo_root)
    if final_source_seal != dict(source_seal):
        raise RuntimeError("V3E sources drifted before the terminal success marker.")
    final_authority = _require_same_authority(
        initial_authority,
        config,
        config_path=config_path,
        phase="compute",
        tag=PROTOCOL_TAG,
        protocol_commit=str(initial_authority["git"]["commit"]),
        repo_root=repo_root,
    )
    final_bootstrap = _require_revalidation_callback()(
        _require_bootstrap_attestation(phase="compute"),
        sealed_authority_bytes=_SEALED_AUTHORITY_BYTES,
        repo_root=repo_root,
    )
    expected_data, expected_model = _expected_inventories(config)
    preseal_model = tuple(
        value for value in expected_model if value != config["output"]["execution_seal"]
    )
    if _inventory(data_dir) != expected_data or _inventory(model_dir) != preseal_model:
        raise RuntimeError("V3E pre-seal output inventory is incomplete or contains extras.")
    seal = {
        "schema_version": SCHEMA_VERSION,
        "status": "terminal_v3e_seal_pending_git_artifact_commit",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": initial_authority["git"]["commit"],
        "artifact_tag_required_before_promotion": ARTIFACT_TAG,
        "summary": summary_descriptor,
        "execution_receipt": receipt_descriptor,
        "artifacts": artifact_descriptors,
        "expected_data_inventory": list(_expected_inventories(config)[0]),
        "expected_model_inventory": list(_expected_inventories(config)[1]),
        "source_composite_sha256": source_seal["composite_sha256"],
        "preterminal_source_composite_sha256": preterminal_source_seal["composite_sha256"],
        "final_source_seal": final_source_seal,
        "implementation_provenance": initial_authority["implementation"],
        "runtime": initial_authority["runtime"],
        "final_implementation_provenance": final_authority["implementation"],
        "final_runtime": final_authority["runtime"],
        "final_bootstrap_attestation": final_bootstrap,
        "initial_git": initial_authority["git"],
        "preterminal_git": final_git,
        "final_git": final_authority["git"],
        "git_artifact_commit_performed": False,
        "active_evidence_authorized": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    seal_path = _exclusive_write_json(targets["execution_seal"], seal)
    _require_output_inventory(config, repo_root=repo_root)
    validate_execution_seal(config, repo_root=repo_root)
    validate_aggregate_only_artifacts(config, repo_root=repo_root)
    return seal_path


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _authenticated_seal_context(config: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    """Recompute the exact authority that a valid historical compute seal must contain."""
    root = repo_root.resolve()
    current_bootstrap = _require_bootstrap_attestation(
        phase=str(globals().get("_IJDS_V3E_BOOTSTRAP_ATTESTATION", {}).get("phase", ""))
    )
    phase = str(current_bootstrap["phase"])
    current_tag = PROTOCOL_TAG if phase == "compute" else ARTIFACT_TAG
    current_git = _require_clean_tagged_head(root, current_tag)
    if current_bootstrap.get("head") != current_git:
        raise RuntimeError("Current bootstrap and Git state disagree during seal validation.")
    protocol_commit = _resolve_strict_tag(root, PROTOCOL_TAG)
    _require_v3e_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    if current_bootstrap.get("protocol_commit") != protocol_commit:
        raise RuntimeError("Current bootstrap and protocol tag disagree during seal validation.")
    implementation = _authority_provenance(
        config_path=(root / DEFAULT_CONFIG_PATH).resolve(),
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    _require_git_bound_sources(config, commit=protocol_commit, repo_root=root)
    current_runtime = _runtime_observation(config, phase=phase)
    terminal_bootstrap = _require_revalidation_callback()(
        current_bootstrap,
        sealed_authority_bytes=_SEALED_AUTHORITY_BYTES,
        repo_root=root,
    )
    protocol_git = {
        "commit": protocol_commit,
        "porcelain_v2_sha256": hashlib.sha256(b"").hexdigest(),
        "porcelain_v2_bytes": 0,
        "clean": True,
    }
    compute_bootstrap = _json_copy(current_bootstrap)
    compute_bootstrap["phase"] = "compute"
    compute_bootstrap["head_tag"] = PROTOCOL_TAG
    compute_bootstrap["head"] = protocol_git
    compute_bootstrap["orig_argv"] = list(config["execution"]["authorized_orig_argv"]["compute"])
    compute_terminal_bootstrap = _json_copy(terminal_bootstrap)
    compute_terminal_bootstrap["phase"] = "compute"
    compute_terminal_bootstrap["head_tag"] = PROTOCOL_TAG
    compute_terminal_bootstrap["head"] = protocol_git
    compute_terminal_bootstrap["orig_argv"] = list(
        config["execution"]["authorized_orig_argv"]["compute"]
    )
    compute_runtime = _json_copy(current_runtime)
    compute_runtime["orig_argv"] = list(config["execution"]["authorized_orig_argv"]["compute"])
    compute_runtime["sys_argv"] = [
        RUNNER_PATH.as_posix(),
        "--phase",
        "compute",
        "--config",
        DEFAULT_CONFIG_PATH.as_posix(),
    ]
    compute_runtime["bootstrap_attestation"] = compute_bootstrap
    return {
        "protocol_commit": protocol_commit,
        "protocol_git": protocol_git,
        "implementation_provenance": implementation,
        "compute_runtime": compute_runtime,
        "compute_bootstrap_attestation": compute_terminal_bootstrap,
    }


def validate_execution_seal(config: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    """Rehash all immutable outputs against the terminal execution seal."""
    _data, _model, targets = output_targets(config, repo_root=repo_root)
    _require_output_inventory(config, repo_root=repo_root)
    seal = json.loads(targets["execution_seal"].read_text(encoding="utf-8"))
    expected_seal_keys = {
        "schema_version",
        "status",
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "artifact_tag_required_before_promotion",
        "summary",
        "execution_receipt",
        "artifacts",
        "expected_data_inventory",
        "expected_model_inventory",
        "source_composite_sha256",
        "preterminal_source_composite_sha256",
        "final_source_seal",
        "implementation_provenance",
        "runtime",
        "final_implementation_provenance",
        "final_runtime",
        "final_bootstrap_attestation",
        "initial_git",
        "preterminal_git",
        "final_git",
        "git_artifact_commit_performed",
        "active_evidence_authorized",
        "protected_stages_run",
        "protected_artifacts_written",
    }
    if (
        set(seal) != expected_seal_keys
        or seal.get("schema_version") != SCHEMA_VERSION
        or seal.get("status") != "terminal_v3e_seal_pending_git_artifact_commit"
        or seal.get("run_tag") != RUN_TAG
        or seal.get("protocol_tag") != PROTOCOL_TAG
        or seal.get("artifact_tag_required_before_promotion") != ARTIFACT_TAG
        or not HEX40.fullmatch(str(seal.get("protocol_commit", "")))
        or seal.get("git_artifact_commit_performed") is not False
        or seal.get("active_evidence_authorized") is not False
        or seal.get("protected_stages_run") != []
        or seal.get("protected_artifacts_written") != []
        or seal.get("expected_data_inventory") != list(_expected_inventories(config)[0])
        or seal.get("expected_model_inventory") != list(_expected_inventories(config)[1])
    ):
        raise RuntimeError("V3E execution seal identity or pending status changed.")
    expected = {
        "summary": relative_artifact_descriptor(targets["summary"], repo_root=repo_root),
        "execution_receipt": relative_artifact_descriptor(
            targets["execution_receipt"], repo_root=repo_root
        ),
        "artifacts": {
            "marginal_mean_score_outcome_gap": relative_artifact_descriptor(
                targets["table"], repo_root=repo_root
            ),
            "endpoint_reason_census": relative_artifact_descriptor(
                targets["endpoint_reason_census"], repo_root=repo_root
            ),
            "monthly_endpoint_reason_census": relative_artifact_descriptor(
                targets["monthly_endpoint_reason_census"], repo_root=repo_root
            ),
        },
    }
    for key, value in expected.items():
        if seal.get(key) != value:
            raise RuntimeError(f"V3E terminal seal no longer binds {key}.")
    summary = json.loads(targets["summary"].read_text(encoding="utf-8"))
    receipt = json.loads(targets["execution_receipt"].read_text(encoding="utf-8"))
    authenticated = _authenticated_seal_context(config, repo_root=repo_root)
    expected_summary_keys = {
        "schema_version",
        "status",
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "artifact_tag_required_before_promotion",
        "estimand",
        "candidate_identity",
        "endpoint_row_sha256",
        "issue_months",
        "endpoint",
        "identification",
        "results",
        "source_audit",
        "source_seal",
        "schemas",
        "artifacts",
        "reporting_contract",
        "git_artifact_commit_performed",
        "protected_stages_run",
        "protected_artifacts_written",
    }
    expected_receipt_keys = {
        "schema_version",
        "status",
        "run_tag",
        "protocol_tag",
        "protocol_commit",
        "artifact_tag_required_before_promotion",
        "started_at_utc",
        "completed_at_utc",
        "runtime_seconds",
        "initial_git",
        "preterminal_git",
        "implementation_provenance",
        "runtime",
        "initial_source_seal",
        "preterminal_source_seal",
        "summary",
        "artifacts",
        "preterminal_implementation_provenance",
        "preterminal_runtime",
        "git_artifact_commit",
        "protected_stages_run",
        "protected_artifacts_written",
    }
    if (
        set(summary) != expected_summary_keys
        or set(receipt) != expected_receipt_keys
        or summary.get("schema_version") != SCHEMA_VERSION
        or summary.get("status") != "complete_clean_tagged_v3e_pending_git_artifact_commit"
        or summary.get("run_tag") != RUN_TAG
        or summary.get("protocol_tag") != PROTOCOL_TAG
        or summary.get("protocol_commit") != seal.get("protocol_commit")
        or summary.get("artifact_tag_required_before_promotion") != ARTIFACT_TAG
        or summary.get("estimand") != ESTIMAND
        or summary.get("artifacts") != expected["artifacts"]
        or summary.get("source_seal", {}).get("composite_sha256")
        != seal.get("source_composite_sha256")
        or summary.get("git_artifact_commit_performed") is not False
        or summary.get("protected_stages_run") != []
        or summary.get("protected_artifacts_written") != []
        or receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("status") != "complete_clean_tagged_v3e_receipt_pending_git_artifact_commit"
        or receipt.get("run_tag") != RUN_TAG
        or receipt.get("protocol_tag") != PROTOCOL_TAG
        or receipt.get("protocol_commit") != seal.get("protocol_commit")
        or receipt.get("artifact_tag_required_before_promotion") != ARTIFACT_TAG
        or receipt.get("summary") != expected["summary"]
        or receipt.get("artifacts") != expected["artifacts"]
        or receipt.get("initial_git") != seal.get("initial_git")
        or receipt.get("preterminal_git") != seal.get("preterminal_git")
        or receipt.get("implementation_provenance") != seal.get("implementation_provenance")
        or receipt.get("runtime") != seal.get("runtime")
        or receipt.get("preterminal_implementation_provenance")
        != seal.get("final_implementation_provenance")
        or receipt.get("preterminal_runtime") != seal.get("final_runtime")
        or receipt.get("initial_source_seal", {}).get("composite_sha256")
        != seal.get("source_composite_sha256")
        or receipt.get("preterminal_source_seal", {}).get("composite_sha256")
        != seal.get("preterminal_source_composite_sha256")
        or seal.get("final_source_seal", {}).get("composite_sha256")
        != seal.get("source_composite_sha256")
        or seal.get("initial_git") != seal.get("preterminal_git")
        or seal.get("initial_git") != seal.get("final_git")
        or seal.get("implementation_provenance") != seal.get("final_implementation_provenance")
        or seal.get("runtime") != seal.get("final_runtime")
        or seal.get("final_bootstrap_attestation", {}).get("schema_version")
        != "2026-07-26.3e-bootstrap-1"
        or receipt.get("git_artifact_commit", {}).get("performed") is not False
        or receipt.get("git_artifact_commit", {}).get("required_before_promotion") is not True
        or receipt.get("git_artifact_commit", {}).get("transport")
        != "git_force_tracked_direct_child_commit"
        or receipt.get("git_artifact_commit", {}).get("dvc_tracked") is not False
        or receipt.get("git_artifact_commit", {}).get("expected_paths")
        != config["output"]["artifact_registration"]["expected_paths"]
        or receipt.get("protected_stages_run") != []
        or receipt.get("protected_artifacts_written") != []
        or seal.get("protocol_commit") != authenticated["protocol_commit"]
        or summary.get("protocol_commit") != authenticated["protocol_commit"]
        or receipt.get("protocol_commit") != authenticated["protocol_commit"]
        or seal.get("initial_git") != authenticated["protocol_git"]
        or seal.get("preterminal_git") != authenticated["protocol_git"]
        or seal.get("final_git") != authenticated["protocol_git"]
        or receipt.get("initial_git") != authenticated["protocol_git"]
        or receipt.get("preterminal_git") != authenticated["protocol_git"]
        or seal.get("implementation_provenance") != authenticated["implementation_provenance"]
        or seal.get("final_implementation_provenance") != authenticated["implementation_provenance"]
        or receipt.get("implementation_provenance") != authenticated["implementation_provenance"]
        or receipt.get("preterminal_implementation_provenance")
        != authenticated["implementation_provenance"]
        or seal.get("runtime") != authenticated["compute_runtime"]
        or seal.get("final_runtime") != authenticated["compute_runtime"]
        or receipt.get("runtime") != authenticated["compute_runtime"]
        or receipt.get("preterminal_runtime") != authenticated["compute_runtime"]
        or seal.get("final_bootstrap_attestation") != authenticated["compute_bootstrap_attestation"]
    ):
        raise RuntimeError("V3E summary or receipt disagrees with the terminal seal.")
    return seal


def validate_recomputed_scientific_outputs(
    config: Mapping[str, Any],
    *,
    result: MarginalMeanScoreOutcomeGapV3EResult,
    source_seal: Mapping[str, Any],
    source_audit: Mapping[str, Any],
    protocol_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Recompute every deterministic scientific output instead of trusting a reseal."""
    _data, _model, targets = output_targets(config, repo_root=repo_root)
    observed_frames = {
        "marginal_mean_score_outcome_gap": pd.read_parquet(targets["table"]),
        "endpoint_reason_census": pd.read_parquet(targets["endpoint_reason_census"]),
        "monthly_endpoint_reason_census": pd.read_parquet(
            targets["monthly_endpoint_reason_census"]
        ),
    }
    expected_frames = {
        "marginal_mean_score_outcome_gap": result.table,
        "endpoint_reason_census": result.endpoint_reason_census,
        "monthly_endpoint_reason_census": result.monthly_endpoint_reason_census,
    }
    for name, expected_frame in expected_frames.items():
        try:
            pd.testing.assert_frame_equal(
                observed_frames[name], expected_frame, check_dtype=True, check_exact=True
            )
        except AssertionError as exc:
            raise RuntimeError(f"V3E sealed Parquet {name!r} differs from recomputation.") from exc
    artifact_descriptors = {
        "marginal_mean_score_outcome_gap": relative_artifact_descriptor(
            targets["table"], repo_root=repo_root
        ),
        "endpoint_reason_census": relative_artifact_descriptor(
            targets["endpoint_reason_census"], repo_root=repo_root
        ),
        "monthly_endpoint_reason_census": relative_artifact_descriptor(
            targets["monthly_endpoint_reason_census"], repo_root=repo_root
        ),
    }
    expected_summary = _scientific_summary_payload(
        config,
        result=result,
        source_seal=source_seal,
        source_audit=source_audit,
        protocol_commit=protocol_commit,
        artifact_descriptors=artifact_descriptors,
    )
    observed_summary = json.loads(targets["summary"].read_text(encoding="utf-8"))
    if observed_summary != expected_summary:
        raise RuntimeError("V3E scientific summary differs from complete recomputation.")
    seal = validate_execution_seal(config, repo_root=repo_root)
    if seal.get("source_composite_sha256") != source_seal["composite_sha256"]:
        raise RuntimeError("V3E terminal seal does not bind the recomputed source seal.")
    return {
        "parquets_exactly_recomputed": list(expected_frames),
        "summary_exactly_recomputed": True,
        "source_composite_sha256": source_seal["composite_sha256"],
        "endpoint_row_sha256": result.endpoint_row_sha256,
    }


def _dvc_directory_descriptor(directory: Path) -> dict[str, Any]:
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError(f"DVC directory is missing or symlinked: {directory}.")
    entries: list[dict[str, str]] = []
    file_records: list[dict[str, str | int]] = []
    size = 0
    for path in sorted(directory.rglob("*"), key=lambda value: value.as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"DVC directory contains a symlink: {path}.")
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        path_before = path.stat()
        with path.open("rb") as handle:
            handle_before = os.fstat(handle.fileno())
            hashes = _hash_open_handle(handle)
            handle_after = os.fstat(handle.fileno())
        path_after = path.stat()
        identity_before = (
            path_before.st_dev,
            path_before.st_ino,
            path_before.st_size,
            path_before.st_mtime_ns,
            path_before.st_ctime_ns,
        )
        identity_handle_before = (
            handle_before.st_dev,
            handle_before.st_ino,
            handle_before.st_size,
            handle_before.st_mtime_ns,
            handle_before.st_ctime_ns,
        )
        identity_handle_after = (
            handle_after.st_dev,
            handle_after.st_ino,
            handle_after.st_size,
            handle_after.st_mtime_ns,
            handle_after.st_ctime_ns,
        )
        identity_after = (
            path_after.st_dev,
            path_after.st_ino,
            path_after.st_size,
            path_after.st_mtime_ns,
            path_after.st_ctime_ns,
        )
        if not (
            identity_before == identity_handle_before == identity_handle_after == identity_after
        ):
            raise RuntimeError(f"DVC file changed while it was hashed: {path}.")
        digest = str(hashes["dvc_md5"])
        if int(hashes["bytes"]) != path_after.st_size:
            raise RuntimeError(f"DVC file size changed while it was hashed: {path}.")
        entries.append({"md5": digest, "relpath": relative})
        file_records.append(
            {
                "relpath": relative,
                "bytes": int(hashes["bytes"]),
                "sha256": str(hashes["sha256"]),
                "md5": digest,
            }
        )
        size += int(hashes["bytes"])
    payload = json.dumps(entries).encode("utf-8")
    directory_md5 = hashlib.md5(payload, usedforsecurity=False).hexdigest() + ".dir"
    file_payload = json.dumps(file_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "md5": directory_md5,
        "size": size,
        "nfiles": len(entries),
        "hash": "md5",
        "file_inventory_sha256": hashlib.sha256(file_payload).hexdigest(),
    }


def _artifact_diff_paths(
    *, protocol_commit: str, artifact_commit: str, repo_root: Path
) -> tuple[str, ...]:
    output = _git(
        ["diff", "--name-only", "-z", protocol_commit, artifact_commit, "--"],
        repo_root=repo_root,
        binary=True,
    )
    if not isinstance(output, bytes):
        raise TypeError("Artifact Git diff was not captured as bytes.")
    return tuple(sorted(value.decode("utf-8") for value in output.split(b"\0") if value))


def _require_direct_child_artifact_commit(
    *, protocol_commit: str, artifact_commit: str, repo_root: Path
) -> None:
    parent_line = str(
        _git(["rev-list", "--parents", "-n", "1", artifact_commit], repo_root=repo_root)
    ).strip()
    if parent_line.split() != [artifact_commit, protocol_commit]:
        raise RuntimeError(
            "V3E artifact commit must be the direct single-parent child of the protocol commit."
        )


def _git_bound_artifact_descriptors(
    targets: Mapping[str, Path], *, artifact_commit: str, repo_root: Path
) -> dict[str, dict[str, Any]]:
    """Bind every small aggregate artifact to its exact artifact-commit Git blob."""
    descriptors: dict[str, dict[str, Any]] = {}
    for name, path in targets.items():
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"V3E Git-native artifact is missing or symlinked: {path}.")
        relative = path.relative_to(repo_root.resolve()).as_posix()
        before = path.stat()
        with path.open("rb") as handle:
            handle_before = os.fstat(handle.fileno())
            payload = handle.read()
            handle_after = os.fstat(handle.fileno())
        after = path.stat()
        identities = {
            (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )
            for value in (before, handle_before, handle_after, after)
        }
        if len(identities) != 1 or len(payload) != after.st_size:
            raise RuntimeError(f"V3E Git-native artifact changed while read: {relative}.")
        blob = _git_blob(repo_root, commit=artifact_commit, relative_path=relative)
        if payload != blob:
            raise RuntimeError(f"V3E artifact differs from its artifact-tag Git blob: {relative}.")
        descriptors[name] = _descriptor_from_bytes(payload, relative_path=relative)
    return descriptors


def validate_aggregate_only_artifacts(
    config: Mapping[str, Any], *, repo_root: Path
) -> dict[str, Any]:
    """Reject row-level payloads or personal-path metadata in Git-native outputs."""
    _data, _model, targets = output_targets(config, repo_root=repo_root)
    frames = {
        "table": pd.read_parquet(targets["table"]),
        "endpoint_reason_census": pd.read_parquet(targets["endpoint_reason_census"]),
        "monthly_endpoint_reason_census": pd.read_parquet(
            targets["monthly_endpoint_reason_census"]
        ),
    }
    expected_rows = {"table": 5, "endpoint_reason_census": 5, "monthly_endpoint_reason_census": 75}
    forbidden_columns = {
        "id",
        "loan_id",
        "member_id",
        "loan_status",
        "last_pymnt_d",
        "snapshot_default",
    }
    for name, frame in frames.items():
        if len(frame) != expected_rows[name]:
            raise RuntimeError(f"V3E Git-native {name} row census is not aggregate-only.")
        leaked = forbidden_columns.intersection(str(value).casefold() for value in frame.columns)
        if leaked:
            raise RuntimeError(
                f"V3E Git-native {name} exposes row-level columns: {sorted(leaked)}."
            )
    json_targets = (targets["summary"], targets["execution_receipt"], targets["execution_seal"])
    forbidden_keys = {
        "database_path",
        "installation_uuid",
        "loan_id",
        "member_id",
        "row_ids",
        "userprofile",
        "username",
    }
    for path in json_targets:
        payload = json.loads(path.read_text(encoding="utf-8"))
        pending: list[Any] = [payload]
        while pending:
            value = pending.pop()
            if isinstance(value, Mapping):
                keys = {str(key).casefold() for key in value}
                if keys.intersection(forbidden_keys):
                    raise RuntimeError(
                        f"V3E Git-native JSON exposes personal or row-level keys: {path}."
                    )
                pending.extend(value.values())
            elif isinstance(value, list):
                if len(value) > 1_000:
                    raise RuntimeError(f"V3E Git-native JSON contains a row-scale list: {path}.")
                pending.extend(value)
            elif isinstance(value, str):
                normalized = value.replace("\\", "/").casefold()
                if "c:/users/" in normalized or normalized.startswith("/home/"):
                    raise RuntimeError(
                        f"V3E Git-native JSON exposes a personal filesystem path: {path}."
                    )
    total_bytes = sum(path.stat().st_size for path in targets.values())
    maximum = int(config["output"]["artifact_registration"]["max_total_bytes"])
    if total_bytes > maximum:
        raise RuntimeError(
            f"V3E Git-native artifacts exceed the aggregate size cap: {total_bytes}."
        )
    return {
        "parquet_rows": {name: int(len(frame)) for name, frame in frames.items()},
        "row_level_columns": [],
        "personal_paths": [],
        "total_bytes": total_bytes,
        "max_total_bytes": maximum,
    }


def _expected_handoff_local_modules() -> list[str]:
    names = {"calibre.debug"}
    for relative in HANDOFF_IMPORTED_PYTHON_PATHS:
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        names.add(".".join(parts))
    return sorted(names)


def _require_exact_handoff_local_modules(terminal: Mapping[str, Any]) -> list[str]:
    module_origins = terminal.get("terminal_module_origins", {})
    loaded_local = (
        list(module_origins.get("loaded_local_modules", []))
        if isinstance(module_origins, Mapping)
        else []
    )
    expected_loaded_local = _expected_handoff_local_modules()
    if loaded_local != expected_loaded_local:
        raise RuntimeError(
            "V3E handoff did not load exactly the complete expected sealed local closure: "
            f"{loaded_local} != {expected_loaded_local}."
        )
    return loaded_local


def run_handoff_only(*, config_path: Path, repo_root: Path = ROOT) -> dict[str, Any]:
    """Exercise the real sealed runner handoff without opening scientific sources."""
    bootstrap_attestation = _require_bootstrap_attestation(phase="handoff-only")
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    initial_git = _require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_commit = str(initial_git["commit"])
    _require_v3e_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    if (
        bootstrap_attestation.get("protocol_commit") != protocol_commit
        or bootstrap_attestation.get("head") != initial_git
    ):
        raise RuntimeError("V3E handoff bootstrap and scientific Git attestations disagree.")
    data_dir, model_dir, targets = output_targets(config, repo_root=root)
    before = {path for path in (data_dir, model_dir, *targets.values()) if path.exists()}
    if before:
        raise FileExistsError(f"V3E handoff found occupied output paths: {sorted(before)}.")
    terminal = _require_revalidation_callback()(
        bootstrap_attestation,
        sealed_authority_bytes=_SEALED_AUTHORITY_BYTES,
        repo_root=root,
    )
    after = {path for path in (data_dir, model_dir, *targets.values()) if path.exists()}
    if after:
        raise RuntimeError(f"V3E handoff created an output path: {sorted(after)}.")
    loaded_local = _require_exact_handoff_local_modules(terminal)
    return {
        "status": "complete_pre_outcome_runner_handoff_attestation",
        "schema_version": SCHEMA_VERSION,
        "phase": "handoff-only",
        "protocol_commit": protocol_commit,
        "head_tag": PROTOCOL_TAG,
        "authority_files": len(_SEALED_AUTHORITY_BYTES),
        "config_loaded_from_sealed_bytes": DEFAULT_CONFIG_PATH in _SEALED_AUTHORITY_BYTES,
        "loaded_local_modules": loaded_local,
        "loaded_local_modules_exact": True,
        "output_targets_absent": True,
        "terminal_revalidated": terminal.get("terminal_revalidated") is True,
    }


def run_pre_source_only(*, config_path: Path, repo_root: Path = ROOT) -> dict[str, Any]:
    """Execute the complete compute prefix and stop before the first source-data access."""
    bootstrap_attestation = _require_bootstrap_attestation(phase="pre-source-only")
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    initial_git = _require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_commit = str(initial_git["commit"])
    _require_v3e_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    if (
        bootstrap_attestation.get("protocol_commit") != protocol_commit
        or bootstrap_attestation.get("head") != initial_git
    ):
        raise RuntimeError("V3E pre-source bootstrap and scientific Git attestations disagree.")
    authority_snapshot = _authority_snapshot(
        config,
        config_path=resolved_config,
        phase="pre-source-only",
        tag=PROTOCOL_TAG,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    _preflight_outputs(config, repo_root=root)
    terminal = _require_revalidation_callback()(
        bootstrap_attestation,
        sealed_authority_bytes=_SEALED_AUTHORITY_BYTES,
        repo_root=root,
    )
    loaded_local = _require_exact_handoff_local_modules(terminal)
    implementation = authority_snapshot.get("implementation", {})
    source_files = (
        implementation.get("source_files", {}) if isinstance(implementation, Mapping) else {}
    )
    if len(source_files) != 25:
        raise RuntimeError("V3E pre-source authority snapshot is not exactly 25 files.")
    return {
        "status": "complete_pre_source_authority_snapshot_attestation",
        "schema_version": SCHEMA_VERSION,
        "phase": "pre-source-only",
        "protocol_commit": protocol_commit,
        "head_tag": PROTOCOL_TAG,
        "authority_files": len(_SEALED_AUTHORITY_BYTES),
        "authority_snapshot_files": len(source_files),
        "git_bound_source_checks_complete": True,
        "loaded_local_modules": loaded_local,
        "loaded_local_modules_exact": True,
        "next_compute_operation": "_load_scientific_sources",
        "output_preflight_complete": True,
        "runtime_observation_complete": True,
        "terminal_revalidated": terminal.get("terminal_revalidated") is True,
    }


def run_compute(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute V3E only from its clean explicit protocol tag."""
    bootstrap_attestation = _require_bootstrap_attestation(phase="compute")
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    initial_git = _require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_commit = str(initial_git["commit"])
    _require_v3e_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    if (
        bootstrap_attestation.get("protocol_commit") != protocol_commit
        or bootstrap_attestation.get("head") != initial_git
    ):
        raise RuntimeError("V3E compute bootstrap and scientific Git attestations disagree.")
    initial_authority = _authority_snapshot(
        config,
        config_path=resolved_config,
        phase="compute",
        tag=PROTOCOL_TAG,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    _preflight_outputs(config, repo_root=root)
    scores, endpoint, initial_source_seal, source_audit = _load_scientific_sources(
        config, protocol_commit=protocol_commit, repo_root=root
    )
    result = _scientific_result(config, scores, endpoint)
    preoutput_source_seal, _ = _source_seal(config, repo_root=root)
    if preoutput_source_seal != initial_source_seal:
        raise RuntimeError("V3E sources drifted before output creation.")
    _require_same_authority(
        initial_authority,
        config,
        config_path=resolved_config,
        phase="compute",
        tag=PROTOCOL_TAG,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    _preflight_outputs(config, repo_root=root)
    seal_path = _write_compute_outputs(
        config,
        config_path=resolved_config,
        result=result,
        source_seal=initial_source_seal,
        source_audit=source_audit,
        initial_authority=initial_authority,
        started_at=started_at,
        started_counter=started_counter,
        repo_root=root,
    )
    return seal_path


def run_verify_artifact(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Recompute the six Git-native aggregates at the direct-child artifact tag."""
    bootstrap_attestation = _require_bootstrap_attestation(phase="verify-artifact")
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    artifact_git = _require_clean_tagged_head(root, ARTIFACT_TAG)
    artifact_commit = str(artifact_git["commit"])
    if bootstrap_attestation.get("head") != artifact_git:
        raise RuntimeError("V3E artifact bootstrap and scientific Git attestations disagree.")
    protocol_commit = _resolve_strict_tag(root, PROTOCOL_TAG)
    _require_v3e_protocol_parent(protocol_commit=protocol_commit, repo_root=root)
    if bootstrap_attestation.get("protocol_commit") != protocol_commit:
        raise RuntimeError("V3E artifact bootstrap and protocol commit disagree.")
    _require_ancestor(ancestor=protocol_commit, descendant=artifact_commit, repo_root=root)
    _require_direct_child_artifact_commit(
        protocol_commit=protocol_commit,
        artifact_commit=artifact_commit,
        repo_root=root,
    )
    initial_authority = _authority_snapshot(
        config,
        config_path=resolved_config,
        phase="verify-artifact",
        tag=ARTIFACT_TAG,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    if initial_authority["git"] != artifact_git:
        raise RuntimeError("V3E initial authority disagrees with the artifact tag.")
    _data_dir, model_dir, targets = output_targets(config, repo_root=root)
    expected_diff = tuple(
        sorted(str(value) for value in config["output"]["artifact_registration"]["expected_paths"])
    )
    observed_diff = _artifact_diff_paths(
        protocol_commit=protocol_commit,
        artifact_commit=artifact_commit,
        repo_root=root,
    )
    if observed_diff != expected_diff:
        raise RuntimeError(
            f"Artifact commit does not contain exactly six outputs: {observed_diff}."
        )
    initial_artifacts = _git_bound_artifact_descriptors(
        targets, artifact_commit=artifact_commit, repo_root=root
    )
    aggregate_audit = validate_aggregate_only_artifacts(config, repo_root=root)
    if aggregate_audit["row_level_columns"] or aggregate_audit["personal_paths"]:
        raise RuntimeError("V3E Git-native aggregate privacy audit failed.")
    scores, endpoint, source_seal, source_audit = _load_scientific_sources(
        config, protocol_commit=protocol_commit, repo_root=root
    )
    result = _scientific_result(config, scores, endpoint)
    recomputation = validate_recomputed_scientific_outputs(
        config,
        result=result,
        source_seal=source_seal,
        source_audit=source_audit,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    if recomputation["endpoint_row_sha256"] != result.endpoint_row_sha256:
        raise RuntimeError("V3E artifact endpoint recomputation changed internally.")
    final_source_seal, _ = _source_seal(config, repo_root=root)
    if final_source_seal != source_seal:
        raise RuntimeError("V3E sources drifted during read-only DVC recomputation.")
    _require_same_authority(
        initial_authority,
        config,
        config_path=resolved_config,
        phase="verify-artifact",
        tag=ARTIFACT_TAG,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    _require_revalidation_callback()(
        bootstrap_attestation,
        sealed_authority_bytes=_SEALED_AUTHORITY_BYTES,
        repo_root=root,
    )
    validate_recomputed_scientific_outputs(
        config,
        result=result,
        source_seal=source_seal,
        source_audit=source_audit,
        protocol_commit=protocol_commit,
        repo_root=root,
    )
    final_artifacts = _git_bound_artifact_descriptors(
        targets, artifact_commit=artifact_commit, repo_root=root
    )
    if final_artifacts != initial_artifacts or _git_snapshot(root) != artifact_git:
        raise RuntimeError("Git-native artifact bytes or Git state drifted during verification.")
    return (model_dir / str(config["output"]["execution_seal"])).resolve()


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.phase == "handoff-only":
        print(
            json.dumps(
                run_handoff_only(config_path=args.config),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    if args.phase == "pre-source-only":
        print(
            json.dumps(
                run_pre_source_only(config_path=args.config),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    if args.phase == "compute":
        path = run_compute(config_path=args.config)
    else:
        path = run_verify_artifact(config_path=args.config)
    print(path)


if __name__ == "__main__":
    main()
