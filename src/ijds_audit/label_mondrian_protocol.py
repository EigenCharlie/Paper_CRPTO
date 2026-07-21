"""Isolated freeze and endpoint-evaluation runners for label-Mondrian sensitivity."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.label_mondrian import (
    evaluate_label_mondrian,
    fit_label_mondrian_thresholds,
)
from src.ijds_audit.protocol import configured_archive_outcomes, load_outcome_universe, load_recipes
from src.utils.artifact_descriptor import relative_artifact_descriptor, verified_artifact_path
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_git_tag,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
FREEZE_STATUS = "label_mondrian_thresholds_frozen_before_primary_oot_outcome_join"
FREEZE_RUN_TAG = "ijds-label-mondrian-freeze-2026-07-21-v1"
FREEZE_PROTOCOL_TAG = "protocol/ijds-label-mondrian-freeze-2026-07-21-v1"
EVALUATION_PHASE = "endpoint_evaluation_locked"
PENDING_TOKEN = "PENDING_AFTER_OUTCOME_FREE_FREEZE"


def load_label_mondrian_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Label-Mondrian config must be a mapping.")
    required = {"schema_version", "phase", "run_tag", "protocol_tag", "source", "design", "output"}
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Label-Mondrian config omits fields: {missing}.")
    return payload


def _verified(
    descriptor: Mapping[str, Any],
    *,
    repo_root: Path,
    label: str,
) -> Path:
    return verified_artifact_path(descriptor, repo_root=repo_root, label=label)


def _require_descriptor_equal(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor mismatched on {field}.")


def _design(config: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], int, float]:
    design = config["design"]
    learners = tuple(str(value) for value in design["learners"])
    windows = tuple(str(value) for value in design["window_ids"])
    groups = int(design["taxonomy_groups"])
    alpha = float(design["alpha"])
    if len(set(learners)) != len(learners) or len(set(windows)) != len(windows):
        raise ValueError("Label-Mondrian learner/window config contains duplicates.")
    expected_cells = int(design["expected_threshold_cells"])
    if expected_cells != len(learners) * len(windows) * groups * 2:
        raise ValueError("Configured label-Mondrian threshold census is inconsistent.")
    return learners, windows, groups, alpha


def freeze_label_mondrian(*, config_path: Path, repo_root: Path) -> Path:
    """Create the outcome-free F1 threshold freeze without loading the raw archive."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_label_mondrian_config(resolved_config)
    if config["phase"] != "evaluation_outcome_free_threshold_freeze":
        raise RuntimeError(
            "F1 config is not locked as an evaluation-outcome-free threshold freeze."
        )
    if config["run_tag"] != FREEZE_RUN_TAG or config["protocol_tag"] != FREEZE_PROTOCOL_TAG:
        raise RuntimeError("F1 run or protocol identity changed.")
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))

    source = config["source"]
    source_freeze_path = _verified(
        source["credit_control_freeze"],
        repo_root=root,
        label="credit-control outcome-free freeze",
    )
    source_freeze = json.loads(source_freeze_path.read_text(encoding="utf-8"))
    expected_source_identity = {
        "status": "credit_control_scores_frozen_before_primary_oot_outcome_join",
        "run_tag": "ijds-credit-risk-controls-2026-07-13-v1b",
        "protocol_tag": "protocol/ijds-credit-risk-controls-2026-07-13-v1b",
    }
    for field, expected in expected_source_identity.items():
        if source_freeze.get(field) != expected:
            raise RuntimeError(f"Credit-control source freeze changed {field}.")
    if source_freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("Credit-control source freeze reports primary-OOT outcome leakage.")
    frozen_artifacts = source_freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("Credit-control source freeze omits outcome-free artifacts.")
    source_paths: dict[str, Path] = {}
    for name in ("scores", "recipes", "fit_audit"):
        declared = source.get(name)
        internal = frozen_artifacts.get(name)
        if not isinstance(declared, Mapping) or not isinstance(internal, Mapping):
            raise TypeError(f"F1 source omits {name!r} descriptor.")
        _require_descriptor_equal(internal, declared, label=f"F1 {name}")
        source_paths[name] = _verified(declared, repo_root=root, label=f"F1 {name}")

    learners, windows, groups, alpha = _design(config)
    scores = pd.read_parquet(source_paths["scores"])
    fit_audit = pd.read_parquet(source_paths["fit_audit"])
    recipes = load_recipes(source_paths["recipes"])
    thresholds = fit_label_mondrian_thresholds(
        scores,
        fit_audit,
        recipes,
        learners=learners,
        window_ids=windows,
        taxonomy_groups=groups,
        alpha=alpha,
    )

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    thresholds_path = atomic_write_parquet(
        thresholds,
        outputs.data_dir / str(config["output"]["thresholds"]),
    )
    finite_thresholds = thresholds.loc[~thresholds["threshold_is_infinite"], "threshold"].to_numpy(
        dtype=float
    )
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": FREEZE_STATUS,
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_artifacts": {
            "credit_control_freeze": relative_artifact_descriptor(
                source_freeze_path, repo_root=root
            ),
            **{
                name: relative_artifact_descriptor(path, repo_root=root)
                for name, path in source_paths.items()
            },
        },
        "design": {
            "learners": list(learners),
            "window_ids": list(windows),
            "taxonomy_groups": groups,
            "labels": [0, 1],
            "alpha": alpha,
            "threshold_cells": int(len(thresholds)),
        },
        "threshold_census": {
            "finite_cells": int((~thresholds["threshold_is_infinite"]).sum()),
            "infinite_cells": int(thresholds["threshold_is_infinite"].sum()),
            "fit_rows_minimum": int(thresholds["fit_rows"].min()),
            "fit_rows_maximum": int(thresholds["fit_rows"].max()),
            "finite_threshold_minimum": (
                float(finite_thresholds.min()) if len(finite_thresholds) else None
            ),
            "finite_threshold_maximum": (
                float(finite_thresholds.max()) if len(finite_thresholds) else None
            ),
        },
        "information_contract": {
            "evaluation_outcomes_joined": False,
            "raw_archive_loaded": False,
            "primary_oot_outcome_columns_in_frozen_scores": [],
            "fit_labels_are_historical_conformal_fit_only": True,
            "threshold_table_contains_loan_ids": False,
            "threshold_table_contains_row_level_labels": False,
        },
        "method": {
            "rank": "ceil((n_gy + 1) * (1 - alpha))",
            "n_plus_one_threshold": "+infinity",
            "candidate_set": "{0: p <= q_g0} union {1: 1-p <= q_g1}",
        },
        "interpretation": dict(config["interpretation"]),
        "outcome_free_artifacts": {
            "thresholds": relative_artifact_descriptor(thresholds_path, repo_root=root)
        },
        "implementation_provenance": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("scripts/experiments/run_ijds_label_mondrian_freeze.py"),
                Path("src/ijds_audit/label_mondrian.py"),
                Path("src/ijds_audit/label_mondrian_protocol.py"),
                Path("src/ijds_audit/protocol.py"),
                Path("src/models/binary_conformal_guardrail.py"),
                Path("docs/research/ijds_label_mondrian_sensitivity_protocol_2026-07-21.md"),
            ],
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    freeze_path = atomic_write_json(
        outputs.model_dir / str(config["output"]["freeze"]),
        freeze,
    )
    atomic_write_json(
        outputs.model_dir / str(config["output"]["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "status": "complete_label_mondrian_threshold_freeze_execution_receipt",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return freeze_path


def require_locked_evaluation_source(config: Mapping[str, Any]) -> None:
    """Reject E1 until F1's descriptor and protocol commit are explicitly locked."""
    if config.get("phase") != EVALUATION_PHASE:
        raise RuntimeError(
            "E1 remains pending; lock the exact F1 freeze descriptor in a new clean tag first."
        )
    source = config.get("source")
    if not isinstance(source, Mapping):
        raise TypeError("E1 source must be a mapping.")
    descriptor = source.get("label_mondrian_freeze")
    receipt_descriptor = source.get("label_mondrian_freeze_receipt")
    if not isinstance(descriptor, Mapping) or not isinstance(receipt_descriptor, Mapping):
        raise TypeError("E1 source omits the F1 freeze or receipt descriptor.")
    commit = source.get("freeze_protocol_commit")
    if (
        descriptor.get("bytes") in (-1, None)
        or receipt_descriptor.get("bytes") in (-1, None)
        or not isinstance(descriptor.get("sha256"), str)
        or not isinstance(receipt_descriptor.get("sha256"), str)
        or PENDING_TOKEN in str(descriptor.get("sha256"))
        or PENDING_TOKEN in str(receipt_descriptor.get("sha256"))
        or not isinstance(commit, str)
        or PENDING_TOKEN in commit
    ):
        raise RuntimeError("E1 F1 descriptor or protocol commit is still pending.")


def _summary_ranges(evaluation: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    metrics = (
        "coverage_lower",
        "coverage_upper",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "coverage_y0_lower",
        "coverage_y0_upper",
        "coverage_y1_lower",
        "coverage_y1_upper",
        "coverage_gap_y0_minus_y1_lower",
        "coverage_gap_y0_minus_y1_upper",
        "average_set_size",
        "singleton_share",
        "set_empty_share",
        "set_zero_only_share",
        "set_one_only_share",
        "set_both_share",
    )
    for learner, frame in evaluation.groupby("learner", sort=False, observed=True):
        row: dict[str, Any] = {"learner": str(learner)}
        for metric in metrics:
            row[f"{metric}_min"] = float(frame[metric].min())
            row[f"{metric}_max"] = float(frame[metric].max())
        rows.append(row)
    return rows


def evaluate_frozen_label_mondrian(*, config_path: Path, repo_root: Path) -> Path:
    """Run E1 after an exact F1 descriptor has been locked in a second tag."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_label_mondrian_config(resolved_config)
    require_locked_evaluation_source(config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    source = config["source"]

    freeze_path = _verified(
        source["label_mondrian_freeze"],
        repo_root=root,
        label="locked label-Mondrian F1 freeze",
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze_receipt_path = _verified(
        source["label_mondrian_freeze_receipt"],
        repo_root=root,
        label="locked label-Mondrian F1 execution receipt",
    )
    freeze_receipt = json.loads(freeze_receipt_path.read_text(encoding="utf-8"))
    expected_freeze_identity = {
        "status": FREEZE_STATUS,
        "run_tag": FREEZE_RUN_TAG,
        "protocol_tag": str(source["freeze_protocol_tag"]),
        "protocol_commit": str(source["freeze_protocol_commit"]),
    }
    for field, expected in expected_freeze_identity.items():
        if freeze.get(field) != expected:
            raise RuntimeError(f"Locked F1 freeze changed {field}.")
    expected_receipt_identity = {
        "status": "complete_label_mondrian_threshold_freeze_execution_receipt",
        "run_tag": FREEZE_RUN_TAG,
        "protocol_tag": str(source["freeze_protocol_tag"]),
        "protocol_commit": str(source["freeze_protocol_commit"]),
    }
    for field, expected in expected_receipt_identity.items():
        if freeze_receipt.get(field) != expected:
            raise RuntimeError(f"Locked F1 execution receipt changed {field}.")
    receipt_freeze_descriptor = freeze_receipt.get("freeze")
    if not isinstance(receipt_freeze_descriptor, Mapping):
        raise TypeError("F1 execution receipt omits its freeze descriptor.")
    _require_descriptor_equal(
        receipt_freeze_descriptor,
        source["label_mondrian_freeze"],
        label="F1 receipt versus locked freeze",
    )
    resolved_freeze_tag = resolve_git_tag(root, str(source["freeze_protocol_tag"]))
    if resolved_freeze_tag != str(source["freeze_protocol_commit"]):
        raise RuntimeError("The locked F1 protocol tag no longer resolves to its declared commit.")
    information = freeze.get("information_contract")
    if (
        not isinstance(information, Mapping)
        or information.get("evaluation_outcomes_joined") is not False
    ):
        raise RuntimeError("F1 freeze does not prove evaluation-outcome isolation.")
    artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(artifacts, Mapping) or not isinstance(artifacts.get("thresholds"), Mapping):
        raise TypeError("F1 freeze omits its threshold artifact.")
    thresholds_path = _verified(
        artifacts["thresholds"],
        repo_root=root,
        label="locked label-Mondrian thresholds",
    )
    thresholds = pd.read_parquet(thresholds_path)

    source_artifacts = freeze.get("source_artifacts")
    if not isinstance(source_artifacts, Mapping):
        raise TypeError("F1 freeze omits its frozen source artifacts.")
    scores_path = _verified(source_artifacts["scores"], repo_root=root, label="F1 frozen scores")
    recipes_path = _verified(source_artifacts["recipes"], repo_root=root, label="F1 frozen recipes")
    scores = pd.read_parquet(scores_path)
    recipes = load_recipes(recipes_path)

    active_config_path = _verified(
        source["active_v5_config"], repo_root=root, label="active V5 config"
    )
    active_config = load_v4_config(active_config_path)
    credit_summary_path = _verified(
        source["credit_control_summary"], repo_root=root, label="active credit-control summary"
    )
    credit_summary = json.loads(credit_summary_path.read_text(encoding="utf-8"))
    if credit_summary.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("Active five-model evaluation is incomplete.")
    f1_source_artifacts = freeze.get("source_artifacts")
    if not isinstance(f1_source_artifacts, Mapping):
        raise TypeError("F1 freeze omits its source-artifact lineage.")
    credit_source_freeze = credit_summary.get("source_freeze")
    if not isinstance(credit_source_freeze, Mapping) or not isinstance(
        f1_source_artifacts.get("credit_control_freeze"), Mapping
    ):
        raise TypeError("Credit-control/F1 freeze lineage is incomplete.")
    _require_descriptor_equal(
        credit_source_freeze,
        f1_source_artifacts["credit_control_freeze"],
        label="credit-control summary versus F1 source freeze",
    )
    evaluation_artifacts = credit_summary.get("evaluation_artifacts")
    if not isinstance(evaluation_artifacts, Mapping) or not isinstance(
        evaluation_artifacts.get("temporal_coverage"), Mapping
    ):
        raise TypeError("Active five-model summary omits temporal coverage.")
    temporal_path = _verified(
        evaluation_artifacts["temporal_coverage"],
        repo_root=root,
        label="active marginal temporal coverage",
    )
    temporal_reference = pd.read_parquet(temporal_path)

    conformal_summary_path = _verified(
        source["conformal_set_summary"],
        repo_root=root,
        label="active conformal-set diagnostic summary",
    )
    conformal_summary = json.loads(conformal_summary_path.read_text(encoding="utf-8"))
    if conformal_summary.get("status") != "complete_retrospective_conformal_set_diagnostic":
        raise RuntimeError("Active conformal-set diagnostic is incomplete.")
    conformal_artifacts = conformal_summary.get("artifacts")
    if not isinstance(conformal_artifacts, Mapping) or not isinstance(
        conformal_artifacts.get("conformal_set_diagnostics"), Mapping
    ):
        raise TypeError("Active conformal-set summary omits its table.")
    conformal_sources = conformal_summary.get("source_artifacts")
    if not isinstance(conformal_sources, Mapping):
        raise TypeError("Active conformal-set summary omits source lineage.")
    conformal_path = _verified(
        conformal_artifacts["conformal_set_diagnostics"],
        repo_root=root,
        label="active conformal-set diagnostic table",
    )
    conformal_reference = pd.read_parquet(conformal_path)

    expected_conformal_sources: dict[str, Mapping[str, Any]] = {
        "active_v5_config": relative_artifact_descriptor(active_config_path, repo_root=root),
        "credit_control_summary": relative_artifact_descriptor(credit_summary_path, repo_root=root),
        "credit_control_freeze": f1_source_artifacts["credit_control_freeze"],
        "scores": f1_source_artifacts["scores"],
        "recipes": f1_source_artifacts["recipes"],
        "temporal_coverage": evaluation_artifacts["temporal_coverage"],
    }
    for name, expected_descriptor in expected_conformal_sources.items():
        observed_descriptor = conformal_sources.get(name)
        if not isinstance(observed_descriptor, Mapping):
            raise TypeError(f"Conformal-set lineage omits {name!r}.")
        _require_descriptor_equal(
            observed_descriptor,
            expected_descriptor,
            label=f"conformal-set lineage {name}",
        )

    raw_path = resolve_repo_input(active_config["source"]["raw_path"], repo_root=root)
    raw_descriptor = relative_artifact_descriptor(raw_path, repo_root=root)
    if raw_descriptor["sha256"] != source["raw_archive_sha256"]:
        raise RuntimeError("Predeclared raw archive digest changed.")
    conformal_raw = conformal_sources.get("raw_archive")
    if not isinstance(conformal_raw, Mapping):
        raise TypeError("Conformal-set lineage omits the raw archive.")
    _require_descriptor_equal(
        conformal_raw,
        raw_descriptor,
        label="conformal-set lineage raw archive",
    )
    universe = load_outcome_universe(active_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, active_config)

    learners, windows, groups, alpha = _design(config)
    if not thresholds["alpha"].eq(alpha).all():
        raise RuntimeError("F1 alpha changed before E1.")
    design = config["design"]
    evaluation, categories, strata, reconciliation = evaluate_label_mondrian(
        scores,
        outcomes,
        recipes,
        thresholds,
        conformal_reference,
        temporal_reference,
        learners=learners,
        window_ids=windows,
        role=str(design["role"]),
        taxonomy_groups=groups,
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
    )
    expected_categories = int(design["expected_target_category_cells"])
    if len(categories) != expected_categories:
        raise RuntimeError(
            f"Target category census changed: {len(categories)} != {expected_categories}."
        )
    expected_strata = int(design["expected_target_stratum_cells"])
    if len(strata) != expected_strata:
        raise RuntimeError(f"Target stratum census changed: {len(strata)} != {expected_strata}.")

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    evaluation_path = atomic_write_parquet(
        evaluation,
        outputs.data_dir / str(config["output"]["evaluation"]),
    )
    category_path = atomic_write_parquet(
        categories,
        outputs.data_dir / str(config["output"]["category_evaluation"]),
    )
    stratum_path = atomic_write_parquet(
        strata,
        outputs.data_dir / str(config["output"]["stratum_evaluation"]),
    )
    reconciliation_path = atomic_write_parquet(
        reconciliation,
        outputs.data_dir / str(config["output"]["baseline_reconciliation"]),
    )
    difference_columns = [
        column for column in reconciliation.columns if column.endswith("_difference")
    ]
    maximum_reconciliation_difference = float(
        np.abs(reconciliation[difference_columns].to_numpy(dtype=float)).max()
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_label_mondrian_evaluation",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_artifacts": {
            "label_mondrian_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "label_mondrian_freeze_receipt": relative_artifact_descriptor(
                freeze_receipt_path, repo_root=root
            ),
            "thresholds": relative_artifact_descriptor(thresholds_path, repo_root=root),
            "scores": relative_artifact_descriptor(scores_path, repo_root=root),
            "recipes": relative_artifact_descriptor(recipes_path, repo_root=root),
            "active_v5_config": relative_artifact_descriptor(active_config_path, repo_root=root),
            "credit_control_summary": relative_artifact_descriptor(
                credit_summary_path, repo_root=root
            ),
            "temporal_coverage": relative_artifact_descriptor(temporal_path, repo_root=root),
            "conformal_set_summary": relative_artifact_descriptor(
                conformal_summary_path, repo_root=root
            ),
            "conformal_set_diagnostics": relative_artifact_descriptor(
                conformal_path, repo_root=root
            ),
            "raw_archive": raw_descriptor,
        },
        "counts": {
            "learner_window_cells": int(len(evaluation)),
            "threshold_cells": int(len(thresholds)),
            "target_category_cells": int(len(categories)),
            "target_stratum_cells": int(len(strata)),
            "learners": len(learners),
            "windows_per_learner": len(windows),
            "score_strata": groups,
            "labels": 2,
            "candidate_rows": int(evaluation["candidate_rows"].iloc[0]),
            "resolved_rows": int(evaluation["resolved_rows"].iloc[0]),
            "unresolved_rows": int(evaluation["unresolved_rows"].iloc[0]),
        },
        "baseline_reconciliation": {
            "metrics_per_cell": len(difference_columns),
            "maximum_absolute_difference": maximum_reconciliation_difference,
            "absolute_and_relative_tolerance": 5.0e-14,
        },
        "identification": {
            "marginal_bounds": "loan-wise min/max over each unresolved binary outcome",
            "class_ratio_bounds": "sharp numerator-denominator ratios over class assignments",
            "class_gap_bounds": "sharp common-completion scan over all unresolved class counts",
            "sampling_confidence_interval": False,
            "missing_at_random_assumption": False,
        },
        "ranges": _summary_ranges(evaluation),
        "target_categories": {
            "coverage_upper_below_nominal_cells": int(
                categories["coverage_upper_below_nominal"].astype(bool).sum()
            ),
            "conditional_coverage_undefined_cells": int(
                (~categories["conditional_coverage_defined"].astype(bool)).sum()
            ),
            "identification_state_counts": {
                str(state): int(count)
                for state, count in categories["identification_state_at_nominal"]
                .value_counts(dropna=False)
                .items()
            },
            "baseline_identification_state_counts": {
                str(state): int(count)
                for state, count in categories["baseline_identification_state_at_nominal"]
                .value_counts(dropna=False)
                .items()
            },
            "coverage_label_lower_minimum": float(categories["coverage_label_lower"].min()),
            "coverage_label_upper_maximum": float(categories["coverage_label_upper"].max()),
            "resolved_label_rows_minimum": int(categories["resolved_label_rows"].min()),
            "resolved_label_rows_maximum": int(categories["resolved_label_rows"].max()),
            "all_400_categories_reported": len(categories) == expected_categories == 400,
            "inferential_multiplicity_applied": False,
            "sharp_endpoint_differences_reported": False,
        },
        "target_strata": {
            "conditional_gap_undefined_cells": int(
                (~strata["conditional_gap_defined"].astype(bool)).sum()
            ),
            "coverage_gap_lower_minimum": float(strata["coverage_gap_y0_minus_y1_lower"].min()),
            "coverage_gap_upper_maximum": float(strata["coverage_gap_y0_minus_y1_upper"].max()),
            "all_200_strata_reported": len(strata) == expected_strata == 200,
            "common_completion_used_within_each_stratum": True,
            "inferential_multiplicity_applied": False,
        },
        "interpretation": dict(config["interpretation"]),
        "artifacts": {
            "label_mondrian_diagnostics": relative_artifact_descriptor(
                evaluation_path, repo_root=root
            ),
            "label_mondrian_category_diagnostics": relative_artifact_descriptor(
                category_path, repo_root=root
            ),
            "label_mondrian_stratum_diagnostics": relative_artifact_descriptor(
                stratum_path, repo_root=root
            ),
            "marginal_baseline_reconciliation": relative_artifact_descriptor(
                reconciliation_path, repo_root=root
            ),
        },
        "implementation_provenance": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("scripts/experiments/run_ijds_label_mondrian_evaluation.py"),
                Path("src/ijds_audit/label_mondrian.py"),
                Path("src/ijds_audit/label_mondrian_protocol.py"),
                Path("src/ijds_audit/protocol.py"),
                Path("src/data/outcome_observability.py"),
                Path("src/models/binary_conformal_guardrail.py"),
                Path("docs/research/ijds_label_mondrian_sensitivity_protocol_2026-07-21.md"),
            ],
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(
        outputs.model_dir / str(config["output"]["summary"]),
        summary,
    )
    atomic_write_json(
        outputs.model_dir / str(config["output"]["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return summary_path


def parse_config_path(value: str | Path) -> Path:
    """Small typed adapter used by both command-line entry points."""
    return Path(value)


def declared_grid(config: Mapping[str, Any]) -> tuple[Sequence[str], Sequence[str], int, float]:
    """Expose the locked grid for lightweight config tests."""
    return _design(config)
