"""Run the contained post-freeze S2B, breakeven, and minimum-stratum replay."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.postfreeze_derived_diagnostics import (
    all_candidate_calibration_bias_table,
    minimum_reference_stratum_effect_table,
    range_summary,
    resolved_coverage_breakeven_table,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import (
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    resolve_repo_input,
    write_csv_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_postfreeze_derived_diagnostics_v1.py"),
    Path("src/ijds_audit/postfreeze_derived_diagnostics.py"),
    Path("docs/research/ijds_postfreeze_derived_diagnostics_v1_protocol_2026-07-26.md"),
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Post-freeze derived-diagnostic config must be a mapping.")
    required = {"schema_version", "run_tag", "protocol_path", "source", "design", "output"}
    if missing := required.difference(payload):
        raise ValueError(f"Derived-diagnostic config omits fields: {sorted(missing)}")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=root)
    actual = relative_artifact_descriptor(path, repo_root=root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"Derived-diagnostic source mismatched on {field}: {path}.")
    return path


def _require_same_descriptor(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor changed on {field}.")


def _endpoint_table(v4_summary: Mapping[str, Any]) -> pd.DataFrame:
    rows = v4_summary.get("endpoint_resolution_audit")
    if not isinstance(rows, list):
        raise TypeError("The active V5 summary omits endpoint-reason rows.")
    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("The active V5 endpoint-reason table is empty.")
    return table


def run(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute all three complete deterministic diagnostics."""
    started_at = _utc_now()
    started_counter = time.perf_counter()
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_path = resolve_repo_input(str(config["protocol_path"]), repo_root=root)
    implementation_start = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    initial_git = git_provenance(root)

    source = config["source"]
    paths_by_name = {name: _verified_path(value, root=root) for name, value in source.items()}
    freeze = json.loads(paths_by_name["credit_control_freeze"].read_text(encoding="utf-8"))
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The source outcome-free score freeze is incomplete.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("The outcome-free score freeze reports primary-OOT outcome columns.")
    frozen_scores = freeze.get("outcome_free_artifacts", {}).get("scores")
    if not isinstance(frozen_scores, Mapping):
        raise TypeError("The source freeze omits its score descriptor.")
    _require_same_descriptor(frozen_scores, source["scores"], label="Outcome-free scores")

    conformal_summary = json.loads(
        paths_by_name["conformal_set_summary"].read_text(encoding="utf-8")
    )
    if conformal_summary.get("status") != "complete_retrospective_conformal_set_diagnostic":
        raise RuntimeError("The source conformal-set diagnostic is incomplete.")
    conformal_descriptor = conformal_summary.get("artifacts", {}).get(
        "conformal_set_diagnostics"
    )
    if not isinstance(conformal_descriptor, Mapping):
        raise TypeError("The conformal-set summary omits its table descriptor.")
    _require_same_descriptor(
        conformal_descriptor,
        source["conformal_set_diagnostics"],
        label="Conformal-set diagnostic table",
    )

    exchange_summary = json.loads(
        paths_by_name["exchangeability_summary"].read_text(encoding="utf-8")
    )
    if exchange_summary.get("status") != "complete_retrospective_exchangeability_transport_test":
        raise RuntimeError("The source joint-block diagnostic is incomplete.")
    exchange_artifacts = exchange_summary.get("artifacts")
    if not isinstance(exchange_artifacts, Mapping):
        raise TypeError("The joint-block summary omits artifacts.")
    for artifact_name, config_name in (
        ("stratum_tests", "exchangeability_strata"),
        ("learner_window_cells", "exchangeability_cells"),
    ):
        descriptor = exchange_artifacts.get(artifact_name)
        if not isinstance(descriptor, Mapping):
            raise TypeError(f"The joint-block summary omits {artifact_name!r}.")
        _require_same_descriptor(descriptor, source[config_name], label=artifact_name)

    design = config["design"]
    learners = tuple(str(value) for value in design["learners"])
    window_ids = tuple(str(value) for value in design["window_ids"])
    if (len(learners), len(window_ids), int(design["taxonomy_groups"])) != (5, 8, 5):
        raise RuntimeError("The declared five-by-eight-by-five grid changed.")
    score_columns = {str(key): str(value) for key, value in design["score_columns"].items()}
    if set(score_columns) != set(learners):
        raise RuntimeError("The declared score-column learner census changed.")

    scores = pd.read_parquet(paths_by_name["scores"])
    v4_summary = json.loads(paths_by_name["v4_summary"].read_text(encoding="utf-8"))
    calibration = all_candidate_calibration_bias_table(
        scores,
        _endpoint_table(v4_summary),
        score_columns=score_columns,
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
        expected_unresolved=int(design["expected_unresolved"]),
    )
    conformal_sets = pd.read_parquet(paths_by_name["conformal_set_diagnostics"])
    breakeven = resolved_coverage_breakeven_table(
        conformal_sets,
        learners=learners,
        window_ids=window_ids,
        alpha=float(design["alpha"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    strata = pd.read_parquet(paths_by_name["exchangeability_strata"])
    cells = pd.read_parquet(paths_by_name["exchangeability_cells"])
    minimum_effect = minimum_reference_stratum_effect_table(
        strata,
        cells,
        learners=learners,
        window_ids=window_ids,
        taxonomy_groups=int(design["taxonomy_groups"]),
        expected_holm_flags=int(design["expected_holm_flags"]),
    )

    implementation_end = implementation_provenance(
        config_path=resolved_config,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Derived-diagnostic implementation changed during execution.")

    output_paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    output = config["output"]
    calibration_path = write_csv_atomic(
        calibration, output_paths.data_dir / str(output["calibration_bias"])
    )
    breakeven_path = write_csv_atomic(
        breakeven, output_paths.data_dir / str(output["breakeven"])
    )
    effect_path = write_csv_atomic(
        minimum_effect, output_paths.data_dir / str(output["minimum_stratum_effect"])
    )
    artifact_descriptors = {
        "all_candidate_calibration_bias": relative_artifact_descriptor(
            calibration_path, repo_root=root
        ),
        "resolved_coverage_breakeven": relative_artifact_descriptor(
            breakeven_path, repo_root=root
        ),
        "minimum_reference_stratum_effect": relative_artifact_descriptor(
            effect_path, repo_root=root
        ),
    }
    source_descriptors = {
        name: relative_artifact_descriptor(path, repo_root=root)
        for name, path in paths_by_name.items()
    }
    flagged = minimum_effect["meets_locked_nominal_holm_threshold"].astype(bool)
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_hash_bound_post_protocol_derived_diagnostics_v1_replay",
        "run_tag": str(config["run_tag"]),
        "protocol_commit_available_at_execution": False,
        "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
        "source_artifacts": source_descriptors,
        "results": {
            "all_candidate_calibration_bias": {
                "learners": int(len(calibration)),
                "default_prevalence_bound": [
                    float(calibration["default_prevalence_lower"].iloc[0]),
                    float(calibration["default_prevalence_upper"].iloc[0]),
                ],
                "mean_score_minus_outcome_lower_range": [
                    float(calibration["mean_score_minus_outcome_lower"].min()),
                    float(calibration["mean_score_minus_outcome_lower"].max()),
                ],
                "mean_score_minus_outcome_upper_range": [
                    float(calibration["mean_score_minus_outcome_upper"].min()),
                    float(calibration["mean_score_minus_outcome_upper"].max()),
                ],
                "all_upper_endpoints_below_zero": bool(
                    calibration["mean_score_minus_outcome_upper"].lt(0.0).all()
                ),
            },
            "resolved_coverage_breakeven": {
                "cells": int(len(breakeven)),
                "mixture_identity_max_abs_residual": float(
                    breakeven["mixture_identity_abs_residual"].max()
                ),
                "resolved_prevalence": float(breakeven["resolved_prevalence"].iloc[0]),
                "breakeven_prevalence_range": [
                    float(breakeven["breakeven_prevalence"].min()),
                    float(breakeven["breakeven_prevalence"].max()),
                ],
                "relative_prevalence_reduction_to_nominal_range": [
                    float(breakeven["relative_prevalence_reduction_to_nominal"].min()),
                    float(breakeven["relative_prevalence_reduction_to_nominal"].max()),
                ],
                "resolved_prevalence_exceeds_breakeven_in_every_cell": bool(
                    breakeven["resolved_prevalence"].gt(
                        breakeven["breakeven_prevalence"]
                    ).all()
                ),
            },
            "minimum_reference_stratum_effect": {
                "selection_role": "post_inspection_p_value_selected_descriptive_magnitude",
                "not_a_new_test_family": True,
                "flagged_cells": range_summary(
                    minimum_effect.loc[flagged, "minimum_reference_excess_miss_rate_pp"]
                ),
                "nonflagged_cells": range_summary(
                    minimum_effect.loc[
                        ~flagged, "minimum_reference_excess_miss_rate_pp"
                    ]
                ),
            },
        },
        "schemas": {
            "all_candidate_calibration_bias": dataframe_schema(calibration),
            "resolved_coverage_breakeven": dataframe_schema(breakeven),
            "minimum_reference_stratum_effect": dataframe_schema(minimum_effect),
        },
        "artifacts": artifact_descriptors,
        "claim_boundary": dict(config["claim_boundary"]),
        "implementation_provenance": implementation_start,
        "environment": environment_provenance(root),
        "initial_git": initial_git,
        "protected_stages_run": [],
        "protected_artifacts_read": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(output_paths.model_dir / str(output["summary"]), summary)
    final_git = git_provenance(root)
    atomic_write_json(
        output_paths.model_dir / str(output["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": "complete_hash_bound_uncommitted_protocol_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "started_at_utc": started_at,
            "completed_at_utc": _utc_now(),
            "runtime_seconds": float(time.perf_counter() - started_counter),
            "protocol_commit_available_at_execution": False,
            "protocol": relative_artifact_descriptor(protocol_path, repo_root=root),
            "implementation_provenance": implementation_start,
            "sources": source_descriptors,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "artifacts": artifact_descriptors,
            "initial_git": initial_git,
            "final_git": final_git,
            "environment": environment_provenance(root),
            "promotion_boundary": (
                "Hash-bound retrospective replay. A clean tagged promotion requires "
                "a new run tag and fresh replay; no protocol commit is asserted here."
            ),
            "protected_stages_run": [],
            "protected_artifacts_read": [],
            "protected_artifacts_written": [],
        },
    )
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
