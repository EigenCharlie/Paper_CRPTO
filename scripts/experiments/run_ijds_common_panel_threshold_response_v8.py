"""Run the clean tagged V8 common-panel threshold-response census."""

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

from src.ijds_audit.common_panel_threshold_response import (
    build_common_panel_threshold_response,
)
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
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
    "configs/experiments/ijds_common_panel_threshold_response_2026-07-26_v8.yaml"
)
PROTOCOL_PATH = Path("docs/research/ijds_common_panel_threshold_response_v8_protocol_2026-07-26.md")
RUN_TAG = "ijds-common-panel-threshold-response-2026-07-26-v8"
PROTOCOL_TAG = "protocol/ijds-common-panel-threshold-response-2026-07-26-v8"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_common_panel_threshold_response_v8.py"),
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
    "stratum_table": ".csv",
    "learner_table": ".csv",
    "summary": ".json",
    "execution_receipt": ".json",
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_locked_config_path(path: Path, *, repo_root: Path) -> Path:
    resolved = resolve_repo_input(path, repo_root=repo_root)
    expected = (repo_root.resolve() / DEFAULT_CONFIG_PATH).resolve()
    if resolved != expected:
        raise RuntimeError(f"V8 accepts only the canonical tracked config: {expected}.")
    return resolved


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V8 common-panel config must be a mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "run_tag",
        "protocol_tag",
        "protocol_path",
        "source",
        "design",
        "output",
        "interpretation",
        "stop_rules",
    }
    if missing := required.difference(payload):
        raise ValueError(f"V8 config omits fields: {sorted(missing)}")
    if payload["schema_version"] != "2026-07-26.2":
        raise RuntimeError("V8 config schema changed.")
    if payload["protocol_status"] != (
        "retrospectively_locked_after_v7_provenance_audit_before_v8_execution"
    ):
        raise RuntimeError("V8 protocol status changed.")
    if payload["run_tag"] != RUN_TAG or payload["protocol_tag"] != PROTOCOL_TAG:
        raise RuntimeError("V8 run or protocol identity changed.")
    if payload["protocol_path"] != PROTOCOL_PATH.as_posix():
        raise RuntimeError("V8 protocol path changed.")
    source = payload["source"]
    if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
        raise RuntimeError("V8 source family changed.")
    for name, descriptor in source.items():
        if not isinstance(descriptor, Mapping) or set(descriptor) != {
            "path",
            "bytes",
            "sha256",
        }:
            raise RuntimeError(f"V8 source descriptor changed for {name!r}.")

    design = payload["design"]
    learners = tuple(str(value) for value in design.get("learners", ()))
    windows = tuple(str(value) for value in design.get("window_ids", ()))
    if len(learners) != 5 or len(set(learners)) != 5:
        raise RuntimeError("V8 must declare exactly five distinct learners.")
    if len(windows) != 8 or len(set(windows)) != 8:
        raise RuntimeError("V8 must declare exactly eight distinct windows.")
    expected_design = {
        "nominal_miscoverage": 0.10,
        "taxonomy_groups": 5,
        "role": "primary_oot",
        "expected_stratum_pairs": 175,
        "expected_learner_pairs": 35,
        "expected_candidates": 376890,
        "expected_resolved": 364814,
        "expected_unresolved": 12076,
        "expected_resolved_y0": 307842,
        "expected_resolved_y1": 56972,
    }
    for key, expected in expected_design.items():
        if design.get(key) != expected:
            raise RuntimeError(f"V8 design field {key!r} changed.")
    issue_months = tuple(str(value) for value in design.get("issue_months", ()))
    if len(issue_months) != 15 or len(set(issue_months)) != 15:
        raise RuntimeError("V8 primary issue-month census changed.")
    illustration = design.get("disclosed_illustration")
    if not isinstance(illustration, Mapping) or set(illustration) != {
        "learner",
        "conformal_group",
        "from_window",
        "to_window",
    }:
        raise RuntimeError("V8 disclosed-illustration identity changed.")
    if (
        illustration["learner"] != "catboost_platt"
        or illustration["conformal_group"] != 2
        or illustration["from_window"] != windows[-2]
        or illustration["to_window"] != windows[-1]
    ):
        raise RuntimeError("V8 disclosed W7--W8 illustration changed.")

    interpretation = payload["interpretation"]
    required_true = {
        "retrospective_after_archive_and_v6_inspection",
        "v7_outputs_already_inspected",
        "exhaustive_deterministic_replay",
        "common_fixed_target_panel",
        "unresolved_outcomes_use_one_shared_completion",
        "no_separate_interval_endpoint_subtraction",
        "no_slope_continuity_or_regression",
        "no_ranking_or_selection",
        "no_exchangeability_test",
        "no_temporal_validity_transfer",
        "no_selected_or_funded_set_validity",
        "no_causal_or_prospective_claim",
        "protected_raw_archive_read_only",
        "cellwise_sign_is_monotonicity_consistency_check",
        "sharpness_is_cellwise_not_joint",
    }
    required_false = {"preregistered", "confirmatory"}
    if any(interpretation.get(key) is not True for key in required_true) or any(
        interpretation.get(key) is not False for key in required_false
    ):
        raise RuntimeError("V8 interpretation boundary changed.")
    stop_rules = payload["stop_rules"]
    if (
        not isinstance(stop_rules, Mapping)
        or not stop_rules
        or not all(value is True for value in stop_rules.values())
    ):
        raise RuntimeError("V8 fail-closed stop rules changed.")
    _validate_output_names(payload)
    return payload


def _validate_output_names(config: Mapping[str, Any]) -> dict[str, str]:
    output = config.get("output")
    if not isinstance(output, Mapping):
        raise TypeError("V8 output contract must be a mapping.")
    expected_keys = {
        "data_root",
        "model_root",
        "immutability",
        *OUTPUT_SUFFIXES,
    }
    if set(output) != expected_keys:
        raise RuntimeError("V8 output contract fields changed.")
    if output["immutability"] != "hard_no_overwrite_choose_fresh_run_tag":
        raise RuntimeError("V8 output immutability contract changed.")
    names: dict[str, str] = {}
    for key, suffix in OUTPUT_SUFFIXES.items():
        rendered = str(output[key])
        candidate = Path(rendered)
        if (
            candidate.name != rendered
            or rendered in {"", ".", ".."}
            or candidate.suffix.lower() != suffix
        ):
            raise ValueError(f"V8 output {key!r} is not a safe {suffix} basename.")
        names[key] = rendered
    folded = [value.casefold() for value in names.values()]
    if len(folded) != len(set(folded)):
        raise ValueError("V8 output basenames alias case-insensitively.")
    return names


def _output_targets(config: Mapping[str, Any], paths: OutputPaths) -> dict[str, Path]:
    names = _validate_output_names(config)
    return {
        "stratum_table": paths.data_dir / names["stratum_table"],
        "learner_table": paths.data_dir / names["learner_table"],
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
        raise FileExistsError(f"V8 output directories already exist: {existing}.")
    _output_targets(config, paths)


def _verified_path(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"V8 source mismatched on {field}: {path}.")
    return path


def _require_same_descriptor(actual: Any, expected: Mapping[str, Any], *, label: str) -> None:
    if not isinstance(actual, Mapping):
        raise TypeError(f"{label} nested descriptor is missing.")
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeError(f"{label} nested descriptor changed on {field}.")


def _load_verified_sources(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[
    dict[str, Path],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    source = config["source"]
    paths = {
        name: _verified_path(descriptor, repo_root=repo_root) for name, descriptor in source.items()
    }
    active_config = load_v4_config(paths["active_v5_config"])
    configured_raw = resolve_repo_input(active_config["source"]["raw_path"], repo_root=repo_root)
    if configured_raw != paths["raw_archive"]:
        raise RuntimeError("The active endpoint config changed its raw archive.")

    credit = json.loads(paths["credit_control_summary"].read_text(encoding="utf-8"))
    if credit.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The source five-learner evaluation is incomplete.")
    _require_same_descriptor(
        credit.get("source_freeze"),
        source["credit_control_freeze"],
        label="Evaluation-to-freeze",
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
    return paths, active_config, credit, freeze, exchange


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
    right = reference.loc[:, keys + columns].copy()
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
    max_abs_differences: dict[str, float] = {}
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
        max_abs_differences[column] = maximum
    return {
        "rows": expected_rows,
        "key_grid_exact": True,
        "integer_fields_exact": True,
        "floating_tolerance": tolerance,
        "maximum_absolute_differences": dict(sorted(max_abs_differences.items())),
    }


def _json_record(row: pd.Series) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in row.items():
        if pd.isna(value):
            record[str(key)] = None
        elif isinstance(value, (np.bool_, bool)):
            record[str(key)] = bool(value)
        elif isinstance(value, (np.integer, int)):
            record[str(key)] = int(value)
        elif isinstance(value, (np.floating, float)):
            record[str(key)] = float(value)
        else:
            record[str(key)] = str(value)
    return record


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the exhaustive V8 replay from one clean tagged commit."""
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

    source_paths, active_config, _credit, _freeze, _exchange = _load_verified_sources(
        config, repo_root=root
    )
    design = config["design"]
    learners = tuple(str(value) for value in design["learners"])
    windows = tuple(str(value) for value in design["window_ids"])
    taxonomy_groups = int(design["taxonomy_groups"])
    temporal = pd.read_parquet(source_paths["temporal_coverage"])
    reference = pd.read_parquet(source_paths["exchangeability_strata"])
    temporal_reconciliation = _reconcile_temporal_reference(
        temporal,
        reference,
        learners=learners,
        windows=windows,
        role=str(design["role"]),
        taxonomy_groups=taxonomy_groups,
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
        filters=[("taxonomy_groups", "==", taxonomy_groups)],
    )
    universe = load_outcome_universe(active_config, raw_path=source_paths["raw_archive"])
    outcomes = configured_archive_outcomes(universe, active_config)
    strata, pooled, module_summary = build_common_panel_threshold_response(
        scores,
        outcomes,
        recipes,
        reference,
        fit_audit=fit_audit,
        learners=learners,
        window_ids=windows,
        role=str(design["role"]),
        taxonomy_groups=taxonomy_groups,
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    if len(strata) != int(design["expected_stratum_pairs"]) or len(pooled) != int(
        design["expected_learner_pairs"]
    ):
        raise RuntimeError("V8 complete adjacent-pair census changed.")
    if not (
        strata["resolved_delta_numerator"].eq(
            strata["threshold_sign"]
            * (strata["resolved_y0_crossed_rows"] + strata["resolved_y1_crossed_rows"])
        )
    ).all():
        raise RuntimeError("V8 exact resolved crossed-band identity changed.")
    if (
        not (strata["delta_upper_numerator"] - strata["delta_lower_numerator"])
        .eq(strata["delta_width_numerator"])
        .all()
    ):
        raise RuntimeError("V8 sharp completion-width identity changed.")

    illustration = design["disclosed_illustration"]
    selected = strata.loc[
        strata["learner"].eq(str(illustration["learner"]))
        & strata["conformal_group"].eq(int(illustration["conformal_group"]))
        & strata["window_from"].eq(str(illustration["from_window"]))
        & strata["window_to"].eq(str(illustration["to_window"]))
    ]
    if len(selected) != 1:
        raise RuntimeError("The disclosed W7--W8 illustration is absent or duplicated.")

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("V8 implementation changed during execution.")
    output_paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    targets = _output_targets(config, output_paths)
    strata_path = write_csv_atomic(strata, targets["stratum_table"])
    pooled_path = write_csv_atomic(pooled, targets["learner_table"])
    source_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=root)
        for name, path in source_paths.items()
    }
    artifact_descriptors = {
        "adjacent_stratum_threshold_response": relative_artifact_descriptor(
            strata_path, repo_root=root
        ),
        "adjacent_learner_threshold_response": relative_artifact_descriptor(
            pooled_path, repo_root=root
        ),
    }
    protected_reads = [source_descriptors["raw_archive"]]
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_clean_tagged_common_panel_threshold_response_v8",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "scope": "five_learners_by_five_score_strata_by_seven_adjacent_transitions",
        "source_artifacts": source_descriptors,
        "nested_source_reconciliation": {
            "active_config_to_raw_archive": True,
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
            "learners": len(learners),
            "score_strata": taxonomy_groups,
            "calibration_windows": len(windows),
            "adjacent_transitions": len(windows) - 1,
            "stratum_rows": len(strata),
            "learner_rows": len(pooled),
            "full_census_reported_without_selection": True,
        },
        "module_audit": module_summary,
        "identities": {
            "resolved_signed_crossed_band_integer_identity_all_rows": True,
            "sharp_shared_completion_bounds_all_rows": True,
            "sharp_width_integer_identity_all_rows": True,
            "learner_aggregates_sum_integer_numerators_before_division": True,
            "separately_extremized_coverage_intervals_subtracted": False,
        },
        "results": {
            "resolved_delta_rate_range": [
                float(strata["resolved_delta_rate"].min()),
                float(strata["resolved_delta_rate"].max()),
            ],
            "all_candidate_delta_lower_range": [
                float(strata["delta_lower"].min()),
                float(strata["delta_lower"].max()),
            ],
            "all_candidate_delta_upper_range": [
                float(strata["delta_upper"].min()),
                float(strata["delta_upper"].max()),
            ],
            "threshold_increase_rows": int(strata["threshold_sign"].eq(1).sum()),
            "threshold_equal_rows": int(strata["threshold_sign"].eq(0).sum()),
            "threshold_decrease_rows": int(strata["threshold_sign"].eq(-1).sum()),
            "disclosed_w7_w8_catboost_stratum_2": _json_record(selected.iloc[0]),
            "disclosed_pair_role": (
                "previously_inspected_illustration_not_winner_extreme_or_inferential_test"
            ),
        },
        "interpretation": dict(config["interpretation"]),
        "stop_rules": dict(config["stop_rules"]),
        "stratum_schema": dataframe_schema(strata),
        "learner_schema": dataframe_schema(pooled),
        "artifacts": artifact_descriptors,
        "implementation_provenance": implementation_start,
        "environment": environment_provenance(root),
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
        "status": "complete_clean_tagged_common_panel_threshold_response_v8_receipt",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": protocol_commit,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "implementation_provenance": implementation_start,
        "sources": source_descriptors,
        "summary": summary_descriptor,
        "artifacts": artifact_descriptors,
        "initial_git": initial_git,
        "final_git": final_git,
        "environment": environment_provenance(root),
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
