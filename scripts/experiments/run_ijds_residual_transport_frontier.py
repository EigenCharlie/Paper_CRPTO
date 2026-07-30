"""Run the clean tagged finite-archive residual-transport frontier V1."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.ijds_audit.residual_transport_frontier import build_residual_transport_frontier
from src.utils.artifact_descriptor import relative_artifact_descriptor, sha256_file
from src.utils.isolated_experiment import (
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path(
    "configs/experiments/ijds_residual_transport_frontier_2026-07-29_v1.yaml"
)
PROTOCOL_PATH = Path("docs/research/ijds_residual_transport_frontier_v1_protocol_2026-07-29.md")
RUN_TAG = "ijds-residual-transport-frontier-2026-07-29-v1"
PROTOCOL_TAG = "protocol/ijds-residual-transport-frontier-2026-07-29-v1"
ARTIFACT_TAG = "artifacts/ijds-residual-transport-frontier-2026-07-29-v1"
PROTOCOL_STATUS = (
    "retrospectively_locked_after_archive_and_prior_transport_inspection_before_v1_execution"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_residual_transport_frontier.py"),
    Path("src/ijds_audit/residual_transport_frontier.py"),
    Path("src/ijds_audit/common_panel_threshold_response.py"),
    Path("src/ijds_audit/grid_contracts.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/evaluation.py"),
    Path("src/data/outcome_observability.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/artifact_descriptor.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("uv.lock"),
    PROTOCOL_PATH,
)
SOURCE_KEYS = {
    "active_v5_config",
    "active_v4_config",
    "active_v3_config",
    "active_v2_config",
    "active_v1_config",
    "fixed_taxonomy_config",
    "credit_control_summary",
    "temporal_coverage",
    "credit_control_freeze",
    "scores",
    "recipes",
    "residual_fit_audit",
    "raw_archive",
    "exchangeability_summary",
    "exchangeability_strata",
}
OUTPUT_SUFFIXES = {
    "monthly_table": ".csv",
    "pooled_table": ".csv",
    "summary": ".json",
    "execution_receipt": ".json",
}


def _portable_environment(repo_root: Path) -> dict[str, Any]:
    """Bind the interpreter bytes without serializing a machine-specific path."""
    payload = dict(environment_provenance(repo_root))
    executable = Path(str(payload.pop("executable")))
    if not executable.is_file():
        raise FileNotFoundError(executable)
    payload["executable"] = {
        "basename": executable.name,
        "bytes": int(executable.stat().st_size),
        "sha256": sha256_file(executable),
    }
    payload["absolute_paths_recorded"] = False
    return payload


STOP_RULE_KEYS = {
    "stop_on_dirty_or_untagged_head",
    "stop_on_source_or_nested_descriptor_mismatch",
    "stop_on_protected_read_path_escape",
    "stop_on_preexisting_output_path",
    "stop_on_unsafe_output_basename",
    "stop_on_incomplete_or_duplicate_grid",
    "stop_on_monthly_cell_without_resolved_target_rows",
    "stop_on_candidate_or_endpoint_census_drift",
    "stop_on_fit_order_statistic_or_recipe_drift",
    "stop_on_target_score_edge_or_assignment_drift",
    "stop_on_v5_q_or_coverage_reconciliation_failure",
    "stop_on_directional_ks_or_completion_order_failure",
    "stop_on_monthly_to_pooled_count_reconciliation_failure",
    "stop_on_implementation_drift",
}
LEARNERS = (
    "catboost_platt",
    "numeric_logistic_platt",
    "catboost_monotonic_platt",
    "woe_scorecard_platform_platt",
    "woe_scorecard_borrower_platt",
)
WINDOWS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
ISSUE_MONTHS = tuple(str(value) for value in pd.period_range("2016-04", "2017-06", freq="M"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_locked_config_path(path: Path, *, repo_root: Path) -> Path:
    resolved = resolve_repo_input(path, repo_root=repo_root)
    expected = (repo_root.resolve() / DEFAULT_CONFIG_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V1 accepts only the canonical tracked config: {expected}.")
    return resolved


def _canonical_descriptor_path(descriptor: Mapping[str, Any], *, label: str) -> Path:
    raw = descriptor.get("path")
    if not isinstance(raw, str) or not raw:
        raise TypeError(f"{label} descriptor omits a path.")
    path = Path(raw)
    if (
        path.is_absolute()
        or path.drive
        or path.root
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{label} descriptor path is unsafe: {raw!r}.")
    if path.as_posix() != raw:
        raise ValueError(f"{label} descriptor path is not canonical: {raw!r}.")
    return path


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Residual-transport config must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_tag",
        "protocol_path",
        "artifact_transport",
        "source",
        "design",
        "output",
        "interpretation",
        "stop_rules",
    }
    if set(payload) != required:
        raise RuntimeError("Residual-transport top-level config fields changed.")
    if payload["schema_version"] != "2026-07-29.1":
        raise RuntimeError("Residual-transport schema version changed.")
    if payload["protocol_status"] != PROTOCOL_STATUS:
        raise RuntimeError("Residual-transport protocol status changed.")
    if payload["run_tag"] != RUN_TAG or payload["protocol_tag"] != PROTOCOL_TAG:
        raise RuntimeError("Residual-transport run or protocol identity changed.")
    if payload["protocol_path"] != PROTOCOL_PATH.as_posix():
        raise RuntimeError("Residual-transport protocol path changed.")

    source = payload["source"]
    if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
        raise RuntimeError("Residual-transport source family changed.")
    for name, descriptor in source.items():
        if not isinstance(descriptor, Mapping) or set(descriptor) != {
            "path",
            "bytes",
            "sha256",
        }:
            raise RuntimeError(f"Source descriptor fields changed for {name!r}.")
        _canonical_descriptor_path(descriptor, label=str(name))
        if (
            isinstance(descriptor["bytes"], bool)
            or not isinstance(descriptor["bytes"], int)
            or descriptor["bytes"] < 1
        ):
            raise RuntimeError(f"Source byte count is invalid for {name!r}.")
        digest = descriptor["sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(value not in "0123456789abcdef" for value in digest)
        ):
            raise RuntimeError(f"Source SHA-256 is invalid for {name!r}.")

    design = payload["design"]
    if not isinstance(design, Mapping):
        raise TypeError("Residual-transport design must be a mapping.")
    expected_design = {
        "nominal_miscoverage": 0.10,
        "taxonomy_groups": 5,
        "role": "primary_oot",
        "expected_monthly_rows": 3000,
        "expected_pooled_rows": 200,
        "expected_candidates": 376890,
        "expected_resolved": 364814,
        "expected_unresolved": 12076,
        "expected_resolved_y0": 307842,
        "expected_resolved_y1": 56972,
    }
    expected_design_keys = {*expected_design, "issue_months", "learners", "window_ids"}
    if set(design) != expected_design_keys:
        raise RuntimeError("Residual-transport design fields changed.")
    for field, expected in expected_design.items():
        if design[field] != expected:
            raise RuntimeError(f"Residual-transport design field {field!r} changed.")
    if tuple(str(value) for value in design["learners"]) != LEARNERS:
        raise RuntimeError("Residual-transport learner order changed.")
    if tuple(str(value) for value in design["window_ids"]) != WINDOWS:
        raise RuntimeError("Residual-transport window order changed.")
    if tuple(str(value) for value in design["issue_months"]) != ISSUE_MONTHS:
        raise RuntimeError("Residual-transport issue-month domain changed.")

    expected_interpretation = {
        "retrospective_after_archive_and_prior_transport_inspection": True,
        "exhaustive_deterministic_full_census": True,
        "preregistered": False,
        "confirmatory": False,
        "directional_ks_is_descriptive_only": True,
        "directional_ks_uses_exact_integer_cross_products": True,
        "no_p_values_or_multiplicity_claim": True,
        "no_exchangeability_test": True,
        "no_temporal_validity_transfer": True,
        "no_selected_or_funded_set_validity": True,
        "no_causal_or_prospective_claim": True,
        "no_ranking_or_selection": True,
        "no_two_origin_sensitivity": True,
        "unresolved_binary_completion_extrema_are_cellwise_sharp": True,
        "directional_discrepancy_comparison_requires_strict_sharp_range_separation": True,
        "directional_discrepancy_ties_are_not_robustly_ordered": True,
        "no_interior_attainability_claim": True,
        "pooled_q_reconciles_active_v5_and_exchangeability_lineage": True,
        "protected_sources_are_read_only": True,
        "protected_read_root_is_materialization_only": True,
    }
    if payload["interpretation"] != expected_interpretation:
        raise RuntimeError("Residual-transport interpretation boundary changed.")
    stop_rules = payload["stop_rules"]
    if (
        not isinstance(stop_rules, Mapping)
        or set(stop_rules) != STOP_RULE_KEYS
        or not all(value is True for value in stop_rules.values())
    ):
        raise RuntimeError("Residual-transport fail-closed stop rules changed.")
    _validate_output_names(payload)
    _validate_artifact_transport(payload)
    return payload


def _validate_output_names(config: Mapping[str, Any]) -> dict[str, str]:
    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("Residual-transport output contract must be a mapping.")
    expected = {"data_root", "model_root", "immutability", *OUTPUT_SUFFIXES}
    if set(output) != expected:
        raise RuntimeError("Residual-transport output fields changed.")
    if output["immutability"] != "hard_no_overwrite_choose_fresh_run_tag":
        raise RuntimeError("Residual-transport output immutability changed.")
    names: dict[str, str] = {}
    for key, suffix in OUTPUT_SUFFIXES.items():
        rendered = str(output[key])
        candidate = Path(rendered)
        if (
            candidate.name != rendered
            or rendered in {"", ".", ".."}
            or candidate.suffix.lower() != suffix
        ):
            raise ValueError(f"Residual-transport output {key!r} is not a safe {suffix} basename.")
        names[key] = rendered
    folded = [value.casefold() for value in names.values()]
    if len(folded) != len(set(folded)):
        raise ValueError("Residual-transport output basenames alias case-insensitively.")
    return names


def _validate_artifact_transport(config: Mapping[str, Any]) -> dict[str, Any]:
    transport = config.get("artifact_transport")
    expected_fields = {
        "artifact_tag",
        "artifact_commit_relationship",
        "exact_tracked_paths",
        "pending_at_runner_exit",
        "dvc_required",
    }
    if not isinstance(transport, Mapping) or set(transport) != expected_fields:
        raise RuntimeError("Residual-transport artifact-transport contract changed.")

    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("Residual-transport output contract must be a mapping.")
    if Path(str(output["data_root"])) != ALLOWED_DATA_ROOT or Path(
        str(output["model_root"])
    ) != ALLOWED_MODEL_ROOT:
        raise RuntimeError("Residual-transport output roots changed.")
    _validate_output_names(config)
    data_prefix = ALLOWED_DATA_ROOT / RUN_TAG
    model_prefix = ALLOWED_MODEL_ROOT / RUN_TAG
    nominal_targets = _output_targets(
        config,
        OutputPaths(data_dir=data_prefix, model_dir=model_prefix),
    )
    if set(nominal_targets) != set(OUTPUT_SUFFIXES):
        raise RuntimeError("Residual-transport output-key mapping changed.")
    expected_paths = [nominal_targets[key].as_posix() for key in OUTPUT_SUFFIXES]
    actual_paths = transport["exact_tracked_paths"]
    if not isinstance(actual_paths, list):
        raise TypeError("Residual-transport exact tracked paths must be a list.")
    for index, raw in enumerate(actual_paths):
        if not isinstance(raw, str):
            raise TypeError("Residual-transport exact tracked paths must be strings.")
        _canonical_descriptor_path({"path": raw}, label=f"artifact_transport[{index}]")
    if len({raw.casefold() for raw in actual_paths}) != len(actual_paths):
        raise RuntimeError("Residual-transport exact tracked paths alias case-insensitively.")
    if (
        transport["artifact_tag"] != ARTIFACT_TAG
        or transport["artifact_commit_relationship"]
        != "single_direct_child_of_protocol_commit"
        or actual_paths != expected_paths
        or transport["pending_at_runner_exit"] is not True
        or transport["dvc_required"] is not False
    ):
        raise RuntimeError("Residual-transport artifact-transport identity changed.")
    return {
        "artifact_tag": ARTIFACT_TAG,
        "artifact_commit_relationship": "single_direct_child_of_protocol_commit",
        "exact_tracked_paths": expected_paths,
        "pending_at_runner_exit": True,
        "dvc_required": False,
    }


def _output_targets(config: Mapping[str, Any], paths: OutputPaths) -> dict[str, Path]:
    names = _validate_output_names(config)
    return {
        "monthly_table": paths.data_dir / names["monthly_table"],
        "pooled_table": paths.data_dir / names["pooled_table"],
        "summary": paths.model_dir / names["summary"],
        "execution_receipt": paths.model_dir / names["execution_receipt"],
    }


def _preflight_output_paths(config: Mapping[str, Any], *, repo_root: Path) -> None:
    output = config["output"]
    paths = OutputPaths(
        data_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=output["data_root"],
            allowed_relative_root=ALLOWED_DATA_ROOT,
            run_tag=RUN_TAG,
        ),
        model_dir=resolve_isolated_run_dir(
            repo_root=repo_root,
            configured_root=output["model_root"],
            allowed_relative_root=ALLOWED_MODEL_ROOT,
            run_tag=RUN_TAG,
        ),
    )
    existing = [path for path in (paths.data_dir, paths.model_dir) if path.exists()]
    if existing:
        raise FileExistsError(f"Residual-transport output directories already exist: {existing}.")
    _output_targets(config, paths)


def _candidate_matches(
    path: Path,
    descriptor: Mapping[str, Any],
) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, "missing"
    if int(path.stat().st_size) != int(descriptor["bytes"]):
        return False, "bytes"
    if sha256_file(path) != descriptor["sha256"]:
        return False, "sha256"
    return True, None


def _verified_source(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
    protected_read_root: Path | None,
    label: str,
) -> tuple[Path, str]:
    relative = _canonical_descriptor_path(descriptor, label=label)
    root = repo_root.resolve()
    repo_candidate = (root / relative).resolve()
    repo_candidate.relative_to(root)
    candidates: list[tuple[Path, str]] = [(repo_candidate, "repository")]
    if protected_read_root is not None:
        protected_root = protected_read_root.resolve()
        protected_candidate = (protected_root / relative).resolve()
        try:
            protected_candidate.relative_to(protected_root)
        except ValueError as exc:
            raise ValueError(f"{label} escaped --protected-read-root.") from exc
        if protected_candidate != repo_candidate:
            candidates.append((protected_candidate, "protected_read_root"))

    failures: list[str] = []
    for candidate, materialization in candidates:
        matches, mismatch = _candidate_matches(candidate, descriptor)
        if matches:
            return candidate, materialization
        failures.append(f"{materialization}:{mismatch}")
    rendered = ", ".join(failures)
    if all(value.endswith(":missing") for value in failures):
        raise FileNotFoundError(f"{label} source is not materialized ({rendered}).")
    raise RuntimeError(f"{label} source descriptor mismatch ({rendered}).")


def _require_same_descriptor(actual: Any, expected: Mapping[str, Any], *, label: str) -> None:
    if not isinstance(actual, Mapping):
        raise TypeError(f"{label} nested descriptor is missing.")
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeError(f"{label} nested descriptor changed on {field}.")


def _load_verified_sources(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    protected_read_root: Path | None,
) -> tuple[
    dict[str, Path],
    dict[str, str],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    source = config["source"]
    verified = {
        name: _verified_source(
            descriptor,
            repo_root=repo_root,
            protected_read_root=protected_read_root,
            label=name,
        )
        for name, descriptor in source.items()
    }
    paths = {name: value[0] for name, value in verified.items()}
    materialization = {name: value[1] for name, value in verified.items()}

    config_chain = (
        ("active_v5_config", "active_v4_config"),
        ("active_v4_config", "active_v3_config"),
        ("active_v3_config", "active_v2_config"),
        ("active_v2_config", "active_v1_config"),
        ("active_v1_config", "fixed_taxonomy_config"),
    )
    for child_name, parent_name in config_chain:
        child = yaml.safe_load(paths[child_name].read_text(encoding="utf-8"))
        if not isinstance(child, Mapping):
            raise TypeError(f"Configuration-chain member {child_name!r} is not a mapping.")
        expected_parent = Path(str(source[parent_name]["path"])).name
        if child.get("extends") != expected_parent:
            raise RuntimeError(
                f"Configuration-chain edge {child_name!r} -> {parent_name!r} changed."
            )

    active_config = load_v4_config(paths["active_v5_config"])
    configured_raw = Path(str(active_config["source"]["raw_path"]))
    if configured_raw.as_posix() != str(source["raw_archive"]["path"]):
        raise RuntimeError("The active endpoint config changed its raw archive path.")

    credit = json.loads(paths["credit_control_summary"].read_text(encoding="utf-8"))
    if credit.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The source five-learner evaluation is incomplete.")
    _require_same_descriptor(
        credit.get("source_freeze"), source["credit_control_freeze"], label="Evaluation-to-freeze"
    )
    evaluation_artifacts = credit.get("evaluation_artifacts")
    if not isinstance(evaluation_artifacts, Mapping):
        raise TypeError("The source evaluation omits its artifact mapping.")
    _require_same_descriptor(
        evaluation_artifacts.get("temporal_coverage"),
        source["temporal_coverage"],
        label="Evaluation-to-temporal-coverage",
    )

    freeze = json.loads(paths["credit_control_freeze"].read_text(encoding="utf-8"))
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The source five-learner outcome-free freeze is incomplete.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("The frozen score artifact reports outcome leakage.")
    frozen_artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("The source freeze omits outcome-free artifacts.")
    for configured_name, frozen_name in (
        ("scores", "scores"),
        ("recipes", "recipes"),
        ("residual_fit_audit", "fit_audit"),
    ):
        _require_same_descriptor(
            frozen_artifacts.get(frozen_name),
            source[configured_name],
            label=f"Freeze-to-{configured_name}",
        )

    exchange = json.loads(paths["exchangeability_summary"].read_text(encoding="utf-8"))
    if exchange.get("status") != "complete_retrospective_exchangeability_transport_test":
        raise RuntimeError("The source exchangeability replay is incomplete.")
    exchange_sources = exchange.get("source_artifacts")
    if not isinstance(exchange_sources, Mapping):
        raise TypeError("The source exchangeability summary omits its sources.")
    for name in (
        "active_v5_config",
        "credit_control_summary",
        "temporal_coverage",
        "credit_control_freeze",
        "scores",
        "recipes",
        "raw_archive",
    ):
        _require_same_descriptor(
            exchange_sources.get(name), source[name], label=f"Exchangeability-to-{name}"
        )
    exchange_artifacts = exchange.get("artifacts")
    if not isinstance(exchange_artifacts, Mapping):
        raise TypeError("The source exchangeability summary omits its artifacts.")
    _require_same_descriptor(
        exchange_artifacts.get("stratum_tests"),
        source["exchangeability_strata"],
        label="Exchangeability-to-strata",
    )
    return paths, materialization, active_config, credit, freeze, exchange


def _reconcile_temporal_reference(
    temporal: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    learners: Sequence[str],
    windows: Sequence[str],
    role: str,
    taxonomy_groups: int,
    tolerance: float = 1.0e-12,
) -> dict[str, Any]:
    keys = ["learner", "window_id", "taxonomy_groups", "conformal_group", "role"]
    columns = [
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "score_min",
        "score_max",
        "fit_residual_quantile",
        "fit_score_min",
        "fit_score_max",
    ]
    required = set(keys + columns)
    for label, frame in (("temporal", temporal), ("exchangeability", reference)):
        if missing := required.difference(frame.columns):
            raise ValueError(f"{label} reference omits fields: {sorted(missing)}")
    mask = (
        temporal["learner"].isin(learners)
        & temporal["window_id"].isin(windows)
        & temporal["role"].eq(role)
        & temporal["taxonomy_groups"].eq(taxonomy_groups)
        & temporal["conformal_group"].between(0, taxonomy_groups - 1)
    )
    left = temporal.loc[mask, keys + columns].copy()
    right_mask = (
        reference["learner"].isin(learners)
        & reference["window_id"].isin(windows)
        & reference["role"].eq(role)
        & reference["taxonomy_groups"].eq(taxonomy_groups)
        & reference["conformal_group"].between(0, taxonomy_groups - 1)
    )
    right = reference.loc[right_mask, keys + columns].copy()
    expected_rows = len(learners) * len(windows) * taxonomy_groups
    for label, frame in (("temporal", left), ("exchangeability", right)):
        if len(frame) != expected_rows or frame.duplicated(keys).any():
            raise RuntimeError(f"{label} reference grid changed.")
    left = left.sort_values(keys, kind="stable").reset_index(drop=True)
    right = right.sort_values(keys, kind="stable").reset_index(drop=True)
    if not left[keys].equals(right[keys]):
        raise RuntimeError("Temporal and exchangeability reference keys differ.")
    integer_columns = ["candidate_rows", "resolved_rows", "unresolved_rows"]
    for column in integer_columns:
        left_values = pd.to_numeric(left[column], errors="raise").to_numpy(dtype=float)
        right_values = pd.to_numeric(right[column], errors="raise").to_numpy(dtype=float)
        if not np.array_equal(left_values, right_values):
            raise RuntimeError(f"Temporal reference integer field {column!r} changed.")
    maximum_differences: dict[str, float] = {}
    for column in set(columns).difference(integer_columns):
        left_values = pd.to_numeric(left[column], errors="raise").to_numpy(dtype=float)
        right_values = pd.to_numeric(right[column], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
            raise RuntimeError(f"Temporal reference field {column!r} is nonfinite.")
        maximum = float(np.max(np.abs(left_values - right_values)))
        if maximum > tolerance:
            raise RuntimeError(
                f"Temporal and exchangeability field {column!r} differ by {maximum!r}."
            )
        maximum_differences[column] = maximum
    return {
        "rows": expected_rows,
        "key_grid_exact": True,
        "integer_fields_exact": True,
        "floating_tolerance": tolerance,
        "maximum_absolute_differences": dict(sorted(maximum_differences.items())),
    }


def _configured_descriptors(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(name): {
            "path": str(descriptor["path"]),
            "bytes": int(descriptor["bytes"]),
            "sha256": str(descriptor["sha256"]),
        }
        for name, descriptor in config["source"].items()
    }


def _protected_reads(
    source_descriptors: Mapping[str, Mapping[str, Any]],
    materialization: Mapping[str, str],
) -> list[dict[str, Any]]:
    names = [name for name in SOURCE_KEYS if materialization[name] == "protected_read_root"]
    if "raw_archive" not in names:
        names.append("raw_archive")
    reads: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in sorted(names):
        descriptor = dict(source_descriptors[name])
        path = str(descriptor["path"])
        if path not in seen:
            reads.append(descriptor)
            seen.add(path)
    return reads


def _reverify_sources_and_git_before_write(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    protected_read_root: Path | None,
    expected_paths: Mapping[str, Path],
    expected_materialization: Mapping[str, str],
    expected_git: Mapping[str, Any],
) -> None:
    """Repeat every source/lineage and Git gate immediately before output creation."""
    paths_end, materialization_end, *_ = _load_verified_sources(
        config,
        repo_root=repo_root,
        protected_read_root=protected_read_root,
    )
    if dict(paths_end) != dict(expected_paths):
        raise RuntimeError("Residual-transport source paths changed during execution.")
    if dict(materialization_end) != dict(expected_materialization):
        raise RuntimeError("Residual-transport source materialization changed during execution.")
    if git_provenance(repo_root) != dict(expected_git):
        raise RuntimeError("Residual-transport Git state changed during execution.")


def run(
    *,
    config_path: Path,
    repo_root: Path = ROOT,
    protected_read_root: Path | None = None,
) -> Path:
    """Execute V1 from one clean tagged commit without protected writes."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = _resolve_locked_config_path(config_path, repo_root=root)
    config = _load_config(resolved_config)
    _preflight_output_paths(config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, PROTOCOL_TAG)
    protocol_path = resolve_repo_input(PROTOCOL_PATH, repo_root=root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)

    source_paths, materialization, active_config, _credit, _freeze, _exchange = (
        _load_verified_sources(
            config,
            repo_root=root,
            protected_read_root=protected_read_root,
        )
    )
    design = config["design"]
    temporal = pd.read_parquet(source_paths["temporal_coverage"])
    reference = pd.read_parquet(source_paths["exchangeability_strata"])
    temporal_reconciliation = _reconcile_temporal_reference(
        temporal,
        reference,
        learners=LEARNERS,
        windows=WINDOWS,
        role=str(design["role"]),
        taxonomy_groups=int(design["taxonomy_groups"]),
    )
    scores = pd.read_parquet(source_paths["scores"])
    recipes = load_recipes(source_paths["recipes"])
    fit_audit = pd.read_parquet(
        source_paths["residual_fit_audit"],
        columns=[
            "id",
            "issue_d",
            "learner",
            "window_id",
            "taxonomy_groups",
            "conformal_group",
            "pd_point",
            "conformal_lower",
            "conformal_upper",
            "terminal_default",
            "covered",
        ],
        filters=[("taxonomy_groups", "==", int(design["taxonomy_groups"]))],
    )
    universe = load_outcome_universe(active_config, raw_path=source_paths["raw_archive"])
    outcomes = configured_archive_outcomes(universe, active_config)
    monthly, pooled, module_summary = build_residual_transport_frontier(
        scores,
        outcomes,
        recipes,
        reference,
        fit_audit=fit_audit,
        learners=LEARNERS,
        window_ids=WINDOWS,
        role=str(design["role"]),
        taxonomy_groups=int(design["taxonomy_groups"]),
        expected_issue_months=ISSUE_MONTHS,
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    if len(monthly) != int(design["expected_monthly_rows"]) or len(pooled) != int(
        design["expected_pooled_rows"]
    ):
        raise RuntimeError("Residual-transport output row census changed.")
    if not pooled["v5_q_and_coverage_reconciled"].all():
        raise RuntimeError("Pooled V5/q reconciliation marker changed.")

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Residual-transport implementation changed during execution.")
    _reverify_sources_and_git_before_write(
        config,
        repo_root=root,
        protected_read_root=protected_read_root,
        expected_paths=source_paths,
        expected_materialization=materialization,
        expected_git=initial_git,
    )
    output_paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, output_paths)
    monthly_path = write_csv_atomic(monthly, targets["monthly_table"])
    pooled_path = write_csv_atomic(pooled, targets["pooled_table"])
    source_descriptors = _configured_descriptors(config)
    artifacts = {
        "monthly_residual_transport_frontier": relative_artifact_descriptor(
            monthly_path, repo_root=root
        ),
        "pooled_residual_transport_frontier": relative_artifact_descriptor(
            pooled_path, repo_root=root
        ),
    }
    protected_reads = _protected_reads(source_descriptors, materialization)
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_calculation_pending_git_artifact_commit_v1",
        "activation_status": "candidate_only_no_active_claim",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "scope": "five_learners_by_eight_windows_by_five_strata_by_fifteen_months_plus_pooled",
        "source_artifacts": source_descriptors,
        "source_materialization": {
            "protected_read_root_supplied": protected_read_root is not None,
            "roles": dict(sorted(materialization.items())),
            "absolute_materialization_paths_recorded": False,
        },
        "nested_source_reconciliation": {
            "active_config_to_raw_archive": True,
            "complete_six_file_active_config_chain_hash_bound": True,
            "evaluation_to_freeze": True,
            "evaluation_to_temporal_coverage": True,
            "freeze_to_scores_recipes_and_fit_audit": True,
            "exchangeability_to_upstream_sources_and_strata": True,
            "temporal_coverage_to_exchangeability_strata": temporal_reconciliation,
        },
        "census": {
            "candidate_rows": int(design["expected_candidates"]),
            "resolved_rows": int(design["expected_resolved"]),
            "resolved_nondefaults": int(design["expected_resolved_y0"]),
            "resolved_defaults": int(design["expected_resolved_y1"]),
            "unresolved_rows": int(design["expected_unresolved"]),
            "learners": len(LEARNERS),
            "calibration_windows": len(WINDOWS),
            "score_strata": int(design["taxonomy_groups"]),
            "issue_months": len(ISSUE_MONTHS),
            "monthly_rows": len(monthly),
            "pooled_rows": len(pooled),
            "full_census_reported_without_selection": True,
        },
        "module_audit": module_summary,
        "identities": {
            "resolved_directional_ks_on_union_grid": True,
            "directional_ks_uses_exact_integer_cross_products": True,
            "unresolved_completion_extrema_are_cellwise_sharp": True,
            "directional_discrepancy_comparison_requires_strict_sharp_range_separation": True,
            "directional_discrepancy_ties_are_not_robustly_ordered": True,
            "interior_attainability_claimed": False,
            "pooled_q_counts_and_coverage_reconcile_v5": True,
            "monthly_q_counts_sum_to_pooled": True,
            "p_values_computed": False,
        },
        "descriptive_ranges": {
            "monthly_resolved_calibration_minus_target_ks": [
                float(monthly["resolved_calibration_minus_target_ks"].min()),
                float(monthly["resolved_calibration_minus_target_ks"].max()),
            ],
            "monthly_resolved_target_minus_calibration_ks": [
                float(monthly["resolved_target_minus_calibration_ks"].min()),
                float(monthly["resolved_target_minus_calibration_ks"].max()),
            ],
            "monthly_calibration_minus_target_ks_extrema": [
                float(monthly["calibration_minus_target_ks_min"].min()),
                float(monthly["calibration_minus_target_ks_max"].max()),
            ],
            "monthly_target_minus_calibration_ks_extrema": [
                float(monthly["target_minus_calibration_ks_min"].min()),
                float(monthly["target_minus_calibration_ks_max"].max()),
            ],
            "pooled_resolved_calibration_minus_target_ks": [
                float(pooled["resolved_calibration_minus_target_ks"].min()),
                float(pooled["resolved_calibration_minus_target_ks"].max()),
            ],
            "pooled_resolved_target_minus_calibration_ks": [
                float(pooled["resolved_target_minus_calibration_ks"].min()),
                float(pooled["resolved_target_minus_calibration_ks"].max()),
            ],
            "monthly_sharp_directional_discrepancy_counts": {
                str(key): int(value)
                for key, value in monthly["sharp_directional_discrepancy_comparison"]
                .value_counts(dropna=False)
                .sort_index()
                .items()
            },
            "pooled_sharp_directional_discrepancy_counts": {
                str(key): int(value)
                for key, value in pooled["sharp_directional_discrepancy_comparison"]
                .value_counts(dropna=False)
                .sort_index()
                .items()
            },
        },
        "interpretation": dict(config["interpretation"]),
        "stop_rules": dict(config["stop_rules"]),
        "monthly_schema": dataframe_schema(monthly),
        "pooled_schema": dataframe_schema(pooled),
        "artifacts": artifacts,
        "artifact_transport": _validate_artifact_transport(config),
        "implementation_provenance": implementation_start,
        "environment": _portable_environment(root),
        "initial_git": initial_git,
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(targets["summary"], summary)
    summary_descriptor = relative_artifact_descriptor(summary_path, repo_root=root)
    final_git = git_provenance(root)
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_calculation_pending_git_artifact_commit",
        "activation_status": "candidate_only_no_active_claim",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "implementation_provenance": implementation_start,
        "sources": source_descriptors,
        "source_materialization": summary["source_materialization"],
        "summary": summary_descriptor,
        "artifacts": artifacts,
        "artifact_transport": _validate_artifact_transport(config),
        "initial_git": initial_git,
        "final_git": final_git,
        "environment": _portable_environment(root),
        "protected_stages_run": [],
        "protected_artifacts_read": protected_reads,
        "protected_artifacts_written": [],
    }
    atomic_write_json(targets["execution_receipt"], receipt)
    return summary_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--protected-read-root",
        type=Path,
        default=None,
        help="Optional read-only materialization root for exact locked source descriptors.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(
        run(
            config_path=args.config,
            repo_root=args.repo_root,
            protected_read_root=args.protected_read_root,
        )
    )


if __name__ == "__main__":
    main()
