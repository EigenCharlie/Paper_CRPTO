"""Two-phase orchestration for the IJDS credit-risk learner controls."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ijds_audit.config import load_credit_control_config
from src.ijds_audit.credit_controls import (
    ScorecardFit,
    feature_variation_audit,
    fit_monotonic_catboost_control,
    fit_woe_scorecard_control,
    score_psi_audit,
    scorecard_feature_psi_audit,
)
from src.ijds_audit.evaluation import build_archive_outcomes, temporal_coverage_audit
from src.ijds_audit.prediction import (
    LearnerScores,
    fit_logistic_control,
    fit_primary_scores,
    fit_window_recipes,
    fixed_taxonomy_edges,
    prepare_data,
)
from src.ijds_audit.protocol import (
    load_outcome_universe,
    load_recipes,
    outcome_free_geometry,
    recipe_payload,
    score_frame,
    verified_freeze_artifact_paths,
)
from src.models.maturity_safe_pd import classification_metrics
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    save_catboost_model_atomic,
)
from src.utils.pipeline_runtime import (
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
)

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
OUTCOME_COLUMNS = frozenset(
    {
        "loan_status",
        "snapshot_default",
        "snapshot_resolution",
        "terminal_default",
        "label_available",
        "label_available_at",
        "total_pymnt",
    }
)


def _implementation(config_path: Path, repo_root: Path) -> dict[str, Any]:
    config = load_credit_control_config(config_path)
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_credit_risk_controls.py"),
            Path("src/ijds_audit/config.py"),
            Path("src/ijds_audit/prediction.py"),
            Path("src/ijds_audit/credit_controls.py"),
            Path("src/ijds_audit/credit_control_protocol.py"),
            Path("src/ijds_audit/evaluation.py"),
            Path("src/ijds_audit/protocol.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/features/feature_engineering.py"),
            Path("src/models/binary_conformal_guardrail.py"),
            Path("src/models/maturity_safe_pd.py"),
            *[Path(value) for value in config.get("protocol_lineage_files", [])],
        ],
    )


def _align_active_reference(
    *,
    data: Any,
    learners: tuple[LearnerScores, LearnerScores],
    config: dict[str, Any],
    repo_root: Path,
) -> tuple[tuple[LearnerScores, LearnerScores], dict[str, Any]]:
    reference_spec = config["credit_risk_controls"]["active_score_reference"]
    reference_path = resolve_repo_input(reference_spec["path"], repo_root=repo_root)
    descriptor = relative_artifact_descriptor(reference_path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if descriptor[field] != reference_spec[field]:
            raise RuntimeError(f"Active V4 score reference mismatch for {field}.")
    reference = pd.read_parquet(reference_path)
    identity = pd.DataFrame(
        {
            "id": data.universe["id"].astype("string"),
            "design_split": data.universe["design_split"].astype("string"),
            "row_order": np.arange(len(data.universe), dtype=np.int64),
        }
    )
    aligned = identity.merge(
        reference,
        on=["id", "design_split"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_reference"),
    ).sort_values("row_order", kind="stable")
    missing_reference = bool(aligned.filter(like="pd_").isna().to_numpy().any())
    if len(aligned) != len(identity) or missing_reference:
        raise RuntimeError("The active V4 score reference does not align to the design universe.")

    groups = [int(value) for value in config["conformal"]["diagnostic_group_counts"]]
    calibration_mask = data.universe["design_split"].eq("probability_calibration").to_numpy()
    tolerance = float(reference_spec["numerical_tolerance"])
    replacements: list[LearnerScores] = []
    audit: dict[str, Any] = {"reference": descriptor, "tolerance": tolerance, "learners": {}}
    for learner in learners:
        column = f"pd_{learner.name}"
        expected = aligned[column].to_numpy(dtype=float)
        absolute = np.abs(learner.probabilities - expected)
        maximum = float(np.max(absolute))
        if maximum > tolerance:
            raise RuntimeError(
                f"Refit {learner.name} differs from active V4 scores by {maximum:.3e}."
            )
        metrics = dict(learner.metrics)
        metrics["active_reference_max_abs_difference"] = maximum
        replacements.append(
            replace(
                learner,
                probabilities=expected,
                taxonomy_edges=fixed_taxonomy_edges(expected[calibration_mask], groups),
                metrics=metrics,
            )
        )
        audit["learners"][learner.name] = {
            "max_abs_difference": maximum,
            "rows": int(len(expected)),
            "within_tolerance": True,
        }
    return (replacements[0], replacements[1]), audit


def _scorecard_artifacts(scorecards: tuple[ScorecardFit, ...]) -> dict[str, pd.DataFrame]:
    return {
        "woe_summary": pd.concat([item.summary for item in scorecards], ignore_index=True),
        "woe_coefficients": pd.concat(
            [item.coefficients for item in scorecards], ignore_index=True
        ),
        "woe_binning_table": pd.concat(
            [item.binning_table for item in scorecards], ignore_index=True
        ),
    }


def freeze_credit_controls(*, config_path: Path, repo_root: Path) -> Path:
    """Fit and hash all learner scores and residual recipes before OOT outcomes."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_credit_control_config(resolved_config)
    if config.get("resume_credit_control_freeze"):
        raise ValueError("The evaluation config cannot create a new credit-control freeze.")
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    data = prepare_data(config, raw_path=raw_path)
    primary = fit_primary_scores(data, config)
    logistic = fit_logistic_control(data, config)
    (primary, logistic), reference_audit = _align_active_reference(
        data=data,
        learners=(primary, logistic),
        config=config,
        repo_root=root,
    )
    monotonic = fit_monotonic_catboost_control(data, config)
    platform = fit_woe_scorecard_control(data, config, specification="platform")
    borrower = fit_woe_scorecard_control(data, config, specification="borrower")
    scorecards = (platform, borrower)
    learners = (primary, logistic, monotonic, platform.scores, borrower.scores)
    expected = tuple(str(value) for value in config["credit_risk_controls"]["co_primary_models"])
    if tuple(learner.name for learner in learners) != expected:
        raise RuntimeError("Fitted learner order differs from the closed protocol family.")

    windows = {learner.name: fit_window_recipes(data, learner, config) for learner in learners}
    scores = score_frame(data, learners)
    forbidden = sorted(OUTCOME_COLUMNS.intersection(scores.columns))
    if forbidden:
        raise RuntimeError(f"Outcome columns entered the frozen score artifact: {forbidden}.")
    fit_audit = pd.concat(
        [window.fit_audit for learner in windows.values() for window in learner.values()],
        ignore_index=True,
    )
    feature_audit = feature_variation_audit(data)
    score_psi = score_psi_audit(
        data,
        learners,
        bins=int(config["credit_risk_controls"]["score_psi_bins"]),
    )
    scorecard_psi = pd.concat(
        [scorecard_feature_psi_audit(data, item.model) for item in scorecards],
        ignore_index=True,
    )
    scorecard_frames = _scorecard_artifacts(scorecards)
    artifact_files = {
        "scores": atomic_write_parquet(scores, paths.data_dir / "prediction/scores.parquet"),
        "recipes": atomic_write_json(
            paths.model_dir / "prediction/residual_recipes.json",
            recipe_payload(windows),
        ),
        "fit_audit": atomic_write_parquet(
            fit_audit,
            paths.data_dir / "prediction/residual_fit_audit.parquet",
        ),
        "outcome_free_geometry": atomic_write_parquet(
            outcome_free_geometry(scores, windows),
            paths.data_dir / "prediction/outcome_free_geometry.parquet",
        ),
        "feature_variation": atomic_write_parquet(
            feature_audit,
            paths.data_dir / "diagnostics/active_feature_variation.parquet",
        ),
        "score_psi": atomic_write_parquet(
            score_psi,
            paths.data_dir / "diagnostics/score_psi.parquet",
        ),
        "scorecard_feature_psi": atomic_write_parquet(
            scorecard_psi,
            paths.data_dir / "diagnostics/scorecard_feature_psi.parquet",
        ),
        **{
            name: atomic_write_parquet(
                frame,
                paths.data_dir / f"diagnostics/{name}.parquet",
            )
            for name, frame in scorecard_frames.items()
        },
    }
    model_files = {
        "catboost": save_catboost_model_atomic(
            primary.model,
            paths.model_dir / "prediction/catboost_seed42.cbm",
        ),
        "catboost_platt": atomic_write_pickle(
            paths.model_dir / "prediction/catboost_platt.pkl",
            primary.calibrator,
        ),
        "numeric_logistic": atomic_write_pickle(
            paths.model_dir / "prediction/numeric_logistic.pkl",
            logistic.model,
        ),
        "numeric_logistic_platt": atomic_write_pickle(
            paths.model_dir / "prediction/numeric_logistic_platt.pkl",
            logistic.calibrator,
        ),
        "catboost_monotonic": save_catboost_model_atomic(
            monotonic.model,
            paths.model_dir / "prediction/catboost_monotonic_seed42.cbm",
        ),
        "catboost_monotonic_platt": atomic_write_pickle(
            paths.model_dir / "prediction/catboost_monotonic_platt.pkl",
            monotonic.calibrator,
        ),
        "woe_scorecard_platform": atomic_write_pickle(
            paths.model_dir / "prediction/woe_scorecard_platform.pkl",
            platform.model,
        ),
        "woe_scorecard_platform_platt": atomic_write_pickle(
            paths.model_dir / "prediction/woe_scorecard_platform_platt.pkl",
            platform.scores.calibrator,
        ),
        "woe_scorecard_borrower": atomic_write_pickle(
            paths.model_dir / "prediction/woe_scorecard_borrower.pkl",
            borrower.model,
        ),
        "woe_scorecard_borrower_platt": atomic_write_pickle(
            paths.model_dir / "prediction/woe_scorecard_borrower_platt.pkl",
            borrower.scores.calibrator,
        ),
    }
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": "credit_control_scores_frozen_before_primary_oot_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "source_inventory": data.source_inventory,
        "active_reference_reproduction": reference_audit,
        "learner_metrics": {learner.name: learner.metrics for learner in learners},
        "co_primary_learners": list(expected),
        "model_selection": "none_all_five_reported",
        "window_selection": "none_all_eight_reported",
        "portfolio_optimization": False,
        "sampling": "none_all_eligible_rows",
        "primary_oot_outcome_columns_in_frozen_scores": [],
        "implementation_provenance": _implementation(resolved_config, root),
        "environment": environment_provenance(root),
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifact_files.items()
        },
        "model_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in model_files.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze)


def _prediction_metrics(scores: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    joined = scores.merge(
        outcomes[["id", "snapshot_default"]],
        on="id",
        how="left",
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    roles = (
        "pd_development",
        "probability_calibration",
        "conformal_fit",
        "policy_development",
        "primary_oot",
        "censored_extension",
    )
    for column in [value for value in scores.columns if value.startswith("pd_")]:
        learner = column.removeprefix("pd_")
        for role in roles:
            frame = joined.loc[joined["design_split"].eq(role)]
            labels = pd.to_numeric(frame["snapshot_default"], errors="coerce")
            observed = labels.notna()
            if not bool(observed.any()):
                raise RuntimeError(f"No resolved outcomes for {learner}/{role}.")
            values = labels.loc[observed].astype(int).to_numpy()
            probability = frame.loc[observed, column].to_numpy(dtype=float)
            metrics = classification_metrics(values, probability)
            rows.append(
                {
                    "learner": learner,
                    "role": role,
                    "candidate_rows": int(len(frame)),
                    "resolved_rows": int(observed.sum()),
                    "unresolved_rows": int((~observed).sum()),
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def _evaluation_summary(
    *,
    config: dict[str, Any],
    coverage: pd.DataFrame,
    prediction: pd.DataFrame,
) -> dict[str, Any]:
    canonical = coverage.loc[
        coverage["role"].eq("primary_oot")
        & coverage["taxonomy_groups"].eq(5)
        & coverage["conformal_group"].eq(-1)
    ]
    primary_prediction = prediction.loc[prediction["role"].eq("primary_oot")].set_index("learner")
    learners: dict[str, Any] = {}
    for learner in config["credit_risk_controls"]["co_primary_models"]:
        cells = canonical.loc[canonical["learner"].eq(learner)]
        if len(cells) != 8:
            raise RuntimeError(f"Expected eight canonical OOT cells for {learner}.")
        row = primary_prediction.loc[learner]
        learners[str(learner)] = {
            "primary_oot_roc_auc": float(row["roc_auc"]),
            "primary_oot_brier": float(row["brier"]),
            "primary_oot_log_loss": float(row["log_loss"]),
            "primary_oot_default_rate": float(row["default_rate"]),
            "canonical_coverage_lower_min": float(cells["coverage_lower"].min()),
            "canonical_coverage_lower_max": float(cells["coverage_lower"].max()),
            "canonical_coverage_upper_min": float(cells["coverage_upper"].min()),
            "canonical_coverage_upper_max": float(cells["coverage_upper"].max()),
            "windows_with_upper_below_target": int(
                (cells["coverage_upper"] < 1.0 - float(config["conformal"]["alpha"])).sum()
            ),
        }
    platform = learners["woe_scorecard_platform_platt"]
    borrower = learners["woe_scorecard_borrower_platt"]
    active = learners["catboost_platt"]
    monotonic = learners["catboost_monotonic_platt"]
    return {
        "schema_version": str(config["schema_version"]),
        "status": "complete_no_model_selection_credit_risk_control_evaluation",
        "run_tag": str(config["run_tag"]),
        "co_primary_learners": learners,
        "declared_diagnostics": {
            "platform_minus_borrower_oot_auc": float(
                platform["primary_oot_roc_auc"] - borrower["primary_oot_roc_auc"]
            ),
            "platform_minus_borrower_oot_brier": float(
                platform["primary_oot_brier"] - borrower["primary_oot_brier"]
            ),
            "monotonic_minus_active_oot_auc": float(
                monotonic["primary_oot_roc_auc"] - active["primary_oot_roc_auc"]
            ),
            "monotonic_minus_active_oot_brier": float(
                monotonic["primary_oot_brier"] - active["primary_oot_brier"]
            ),
        },
        "interpretation": {
            "model_or_feature_selected_from_oot": False,
            "portfolio_claim_authorized": False,
            "scorecard_superiority_claim_authorized": False,
            "universal_transport_claim_authorized": False,
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }


def evaluate_credit_controls(*, config_path: Path, repo_root: Path) -> Path:
    """Verify the V1 score freeze and evaluate all five controls once."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_credit_control_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    resume = config.get("resume_credit_control_freeze")
    if not resume:
        raise ValueError("Evaluation requires resume_credit_control_freeze.")
    source_model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=str(resume["source_run_tag"]),
    )
    source_freeze_path = source_model_dir / "protocol_freeze.json"
    source_descriptor = relative_artifact_descriptor(source_freeze_path, repo_root=root)
    if source_descriptor["sha256"] != str(resume["source_freeze_sha256"]):
        raise RuntimeError("Imported credit-control freeze SHA-256 mismatch.")
    freeze = json.loads(source_freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": "credit_control_scores_frozen_before_primary_oot_outcome_join",
        "run_tag": str(resume["source_run_tag"]),
        "protocol_tag": str(resume["source_protocol_tag"]),
        "protocol_commit": str(resume["source_protocol_commit"]),
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise RuntimeError(f"Imported credit-control freeze mismatch for {field}.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("Imported credit-control freeze reports OOT outcome leakage.")
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=root)
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    raw_path = resolve_repo_input(config["source"]["raw_path"], repo_root=root)
    universe = load_outcome_universe(config, raw_path=raw_path)
    outcomes = build_archive_outcomes(universe)
    scores = pd.read_parquet(artifacts["scores"])
    recipes = load_recipes(artifacts["recipes"])
    fit_audit = pd.read_parquet(artifacts["fit_audit"])
    coverage = temporal_coverage_audit(scores, outcomes, recipes, fit_audit)
    prediction = _prediction_metrics(scores, outcomes)
    output_files = {
        "temporal_coverage": atomic_write_parquet(
            coverage,
            paths.data_dir / "evaluation/temporal_coverage.parquet",
        ),
        "prediction_metrics": atomic_write_parquet(
            prediction,
            paths.data_dir / "evaluation/prediction_metrics.parquet",
        ),
    }
    summary = _evaluation_summary(config=config, coverage=coverage, prediction=prediction)
    summary["source_freeze"] = source_descriptor
    summary["source_protocol"] = expected
    summary["evaluation_artifacts"] = {
        name: relative_artifact_descriptor(path, repo_root=root)
        for name, path in output_files.items()
    }
    summary["implementation_provenance"] = _implementation(resolved_config, root)
    summary["environment"] = environment_provenance(root)
    summary_path = atomic_write_json(
        paths.model_dir / str(config["output"]["deterministic_summary"]),
        summary,
    )
    receipt = {
        "schema_version": str(config["schema_version"]),
        "status": "credit_risk_control_evaluation_complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "summary": relative_artifact_descriptor(summary_path, repo_root=root),
        "source_freeze": source_descriptor,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    atomic_write_json(paths.model_dir / str(config["output"]["execution_receipt"]), receipt)
    return summary_path
