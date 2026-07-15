"""Protocol-locked sensitivity to two active missing-value conventions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.credit_controls import credit_prediction_metrics
from src.ijds_audit.evaluation import endpoint_resolution_audit, temporal_coverage_audit
from src.ijds_audit.prediction import (
    PreparedData,
    fit_primary_scores,
    fit_window_recipes,
    prepare_data,
)
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
    recipe_payload,
    verified_freeze_artifact_paths,
)
from src.utils.isolated_experiment import (
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_isolated_run_dir,
    resolve_repo_input,
    save_catboost_model_atomic,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet, atomic_write_pickle

ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
SPECIFICATION_IDS = (
    "catboost_platt",
    "catboost_missing_indicators_platt",
    "catboost_native_missing_platt",
)


def load_missingness_config(path: Path, *, repo_root: Path) -> dict[str, Any]:
    """Load and validate the closed missingness-sensitivity contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Missingness protocol must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "base_config",
        "protocol_document",
        "source_freeze",
        "specifications",
        "evaluation",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise KeyError(f"Missingness protocol is missing sections: {missing}.")
    if payload["protocol_status"] != "locked_outcome_free_then_evaluate_missingness_sensitivity":
        raise ValueError("Unexpected missingness protocol status.")
    specifications = payload["specifications"]
    if not isinstance(specifications, list):
        raise TypeError("Missingness specifications must be a list.")
    if tuple(str(item["id"]) for item in specifications) != SPECIFICATION_IDS:
        raise ValueError("The complete missingness specification family changed.")
    expected_encodings = (
        "active_sentinel_convention",
        "active_mappings_plus_explicit_missing_indicators",
        "native_numeric_nan_without_active_mapped_features",
    )
    if tuple(str(item["encoding"]) for item in specifications) != expected_encodings:
        raise ValueError("The missingness encoding family changed.")
    evaluation = payload["evaluation"]
    expected_evaluation = {
        "role": "primary_oot",
        "expected_candidates": 376890,
        "expected_windows": 8,
        "taxonomy_groups": 5,
        "aggregate_stratum": -1,
        "nominal_coverage": 0.90,
        "no_model_selection": True,
        "no_window_selection": True,
        "no_portfolio_optimization": True,
    }
    if evaluation != expected_evaluation:
        raise ValueError("The missingness evaluation contract changed.")
    if payload["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Missingness outputs must be immutable.")
    source = payload["source_freeze"]
    if not isinstance(source, Mapping) or str(source.get("sha256", "")) != (
        "c2b3dc2d18c9fed80708682d5a0369c80c89643e2d28024418522d954ebe667c"
    ):
        raise ValueError("The active V4-v1 source freeze changed.")
    base_path = resolve_repo_input(str(payload["base_config"]), repo_root=repo_root)
    load_v4_config(base_path)
    return payload


def _base_config(config: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    return load_v4_config(resolve_repo_input(str(config["base_config"]), repo_root=repo_root))


def build_missingness_variant(data: PreparedData, *, variant: str) -> PreparedData:
    """Construct one declared feature matrix without changing the row universe."""
    features = data.features.copy()
    numeric = list(data.numeric_features)
    if variant == "explicit_indicators":
        features["delinq_recency_missing"] = (
            pd.to_numeric(data.universe["mths_since_last_delinq"], errors="coerce")
            .isna()
            .astype("int8")
        )
        features["bankruptcy_count_missing"] = (
            pd.to_numeric(data.universe["pub_rec_bankruptcies"], errors="coerce")
            .isna()
            .astype("int8")
        )
        numeric.extend(["delinq_recency_missing", "bankruptcy_count_missing"])
    elif variant == "native_missing":
        features = features.drop(columns=["delinq_recency", "has_bankruptcy"])
        numeric = [name for name in numeric if name not in {"delinq_recency", "has_bankruptcy"}]
        features["delinq_recency_native"] = pd.to_numeric(
            data.universe["mths_since_last_delinq"], errors="coerce"
        )
        features["bankruptcy_count_native"] = pd.to_numeric(
            data.universe["pub_rec_bankruptcies"], errors="coerce"
        )
        numeric.extend(["delinq_recency_native", "bankruptcy_count_native"])
    else:
        raise ValueError(f"Unknown missingness variant: {variant!r}.")
    if len(numeric) != len(set(numeric)):
        raise RuntimeError("Missingness variant contains duplicate numeric features.")
    if not features.index.equals(data.features.index):
        raise RuntimeError("Missingness variant changed the row index.")
    return replace(data, features=features, numeric_features=tuple(numeric))


def _verified_source_freeze(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Any], dict[str, Path]]:
    source = config["source_freeze"]
    path = resolve_repo_input(str(source["path"]), repo_root=repo_root)
    descriptor = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if descriptor[field] != source[field]:
            raise RuntimeError(f"Missingness source freeze mismatch for {field}.")
    freeze = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
        "run_tag": str(source["run_tag"]),
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": str(source["protocol_commit"]),
    }
    if any(freeze.get(field) != value for field, value in expected.items()):
        raise RuntimeError("Missingness source freeze identity changed.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("Missingness source freeze reports outcome leakage.")
    return freeze, verified_freeze_artifact_paths(freeze, repo_root=repo_root)


def _missingness_census(data: PreparedData) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role, frame in data.universe.groupby("design_split", observed=True, sort=True):
        for feature in ("mths_since_last_delinq", "pub_rec_bankruptcies"):
            missing = pd.to_numeric(frame[feature], errors="coerce").isna()
            rows.append(
                {
                    "role": str(role),
                    "feature": feature,
                    "rows": int(len(frame)),
                    "missing_rows": int(missing.sum()),
                    "missing_share": float(missing.mean()),
                }
            )
    return pd.DataFrame(rows)


def _implementation(
    config_path: Path,
    config: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    return implementation_provenance(
        config_path=config_path,
        repo_root=repo_root,
        relative_paths=[
            Path("scripts/experiments/run_ijds_missingness_sensitivity.py"),
            Path("src/ijds_audit/missingness_sensitivity.py"),
            Path("src/ijds_audit/evaluation.py"),
            Path("src/ijds_audit/prediction.py"),
            Path("src/ijds_audit/protocol.py"),
            Path("src/data/outcome_observability.py"),
            Path("src/features/feature_engineering.py"),
            Path("docs/research/ijds_missingness_sensitivity_protocol_2026-07-15.md"),
            *[Path(value) for value in config.get("implementation_lineage_files", [])],
        ],
    )


def freeze_missingness_sensitivity(*, config_path: Path, repo_root: Path) -> Path:
    """Freeze baseline and two alternative score/recipe specifications."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_missingness_config(resolved_config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    source_freeze, source_artifacts = _verified_source_freeze(config, repo_root=root)
    parent = _base_config(config, repo_root=root)
    paths = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    raw_path = resolve_repo_input(str(parent["source"]["raw_path"]), repo_root=root)
    data = prepare_data(parent, raw_path=raw_path)

    source_scores = pd.read_parquet(source_artifacts["scores"])
    identity = pd.DataFrame(
        {
            "id": data.universe["id"].astype("string"),
            "issue_d": data.universe["issue_d"],
            "design_split": data.universe["design_split"].astype("string"),
        }
    )
    baseline = identity.merge(
        source_scores[["id", "design_split", "pd_catboost_platt"]],
        on=["id", "design_split"],
        how="left",
        validate="one_to_one",
    )
    if len(baseline) != len(identity) or bool(baseline["pd_catboost_platt"].isna().any()):
        raise RuntimeError("The frozen baseline score does not align to the active universe.")

    indicator_data = build_missingness_variant(data, variant="explicit_indicators")
    native_data = build_missingness_variant(data, variant="native_missing")
    indicator = replace(
        fit_primary_scores(indicator_data, parent),
        name="catboost_missing_indicators_platt",
    )
    native = replace(
        fit_primary_scores(native_data, parent),
        name="catboost_native_missing_platt",
    )
    alternative_windows = {
        indicator.name: fit_window_recipes(indicator_data, indicator, parent),
        native.name: fit_window_recipes(native_data, native, parent),
    }
    baseline_recipes = json.loads(source_artifacts["recipes"].read_text(encoding="utf-8"))
    combined_recipes = {
        "catboost_platt": baseline_recipes["catboost_platt"],
        **recipe_payload(alternative_windows),
    }
    source_fit = pd.read_parquet(source_artifacts["fit_audit"])
    fit_audit = pd.concat(
        [
            source_fit.loc[source_fit["learner"].eq("catboost_platt")],
            *[
                window.fit_audit
                for learner_windows in alternative_windows.values()
                for window in learner_windows.values()
            ],
        ],
        ignore_index=True,
    )
    scores = baseline.assign(
        pd_catboost_missing_indicators_platt=indicator.probabilities,
        pd_catboost_native_missing_platt=native.probabilities,
    )
    census = _missingness_census(data)
    artifacts = {
        "scores": atomic_write_parquet(scores, paths.data_dir / "prediction/scores.parquet"),
        "recipes": atomic_write_json(
            paths.model_dir / "prediction/residual_recipes.json", combined_recipes
        ),
        "fit_audit": atomic_write_parquet(
            fit_audit, paths.data_dir / "prediction/residual_fit_audit.parquet"
        ),
        "missingness_census": atomic_write_parquet(
            census, paths.data_dir / "data/missingness_census.parquet"
        ),
    }
    model_artifacts = {
        "catboost_missing_indicators": relative_artifact_descriptor(
            save_catboost_model_atomic(
                indicator.model, paths.model_dir / "prediction/catboost_missing_indicators.cbm"
            ),
            repo_root=root,
        ),
        "catboost_missing_indicators_platt": relative_artifact_descriptor(
            atomic_write_pickle(
                paths.model_dir / "prediction/catboost_missing_indicators_platt.pkl",
                indicator.calibrator,
            ),
            repo_root=root,
        ),
        "catboost_native_missing": relative_artifact_descriptor(
            save_catboost_model_atomic(
                native.model, paths.model_dir / "prediction/catboost_native_missing.cbm"
            ),
            repo_root=root,
        ),
        "catboost_native_missing_platt": relative_artifact_descriptor(
            atomic_write_pickle(
                paths.model_dir / "prediction/catboost_native_missing_platt.pkl",
                native.calibrator,
            ),
            repo_root=root,
        ),
    }
    freeze = {
        "schema_version": str(config["schema_version"]),
        "status": "missingness_scores_frozen_before_primary_oot_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "specifications": list(config["specifications"]),
        "source_freeze": dict(config["source_freeze"]),
        "source_outcome_free_status": str(source_freeze["status"]),
        "primary_oot_outcome_columns_in_frozen_scores": [],
        "outcome_free_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in artifacts.items()
        },
        "model_artifacts": model_artifacts,
        "implementation_provenance": _implementation(resolved_config, config, repo_root=root),
        "environment": environment_provenance(root),
        "git": git_provenance(root),
        "selection": {"model": None, "encoding": None, "window": None},
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    return atomic_write_json(paths.model_dir / "protocol_freeze.json", freeze)


def _prediction_metrics(scores: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    primary_scores = scores.loc[scores["design_split"].eq("primary_oot")].copy()
    primary_outcomes = outcomes.loc[outcomes["role"].eq("primary_oot"), ["id", "snapshot_default"]]
    joined = primary_scores.merge(primary_outcomes, on="id", how="outer", validate="one_to_one")
    if len(joined) != 376890 or bool(joined["design_split"].isna().any()):
        raise RuntimeError("Missingness prediction outcome census changed.")
    observed = joined["snapshot_default"].notna()
    labels = joined.loc[observed, "snapshot_default"].astype(int).to_numpy()
    rows: list[dict[str, Any]] = []
    for learner in SPECIFICATION_IDS:
        metrics = credit_prediction_metrics(
            labels,
            joined.loc[observed, f"pd_{learner}"].to_numpy(dtype=float),
        )
        rows.append(
            {
                "learner": learner,
                "candidate_rows": int(len(joined)),
                "resolved_rows": int(observed.sum()),
                "unresolved_rows": int((~observed).sum()),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def evaluate_missingness_sensitivity(*, config_path: Path, repo_root: Path) -> Path:
    """Join the corrected endpoint once and report the complete specification family."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = load_missingness_config(resolved_config, repo_root=root)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))
    parent = _base_config(config, repo_root=root)
    model_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["model_root"]),
        allowed_relative_root=ALLOWED_MODEL_ROOT,
        run_tag=str(config["run_tag"]),
    )
    data_dir = resolve_isolated_run_dir(
        repo_root=root,
        configured_root=str(config["output"]["data_root"]),
        allowed_relative_root=ALLOWED_DATA_ROOT,
        run_tag=str(config["run_tag"]),
    )
    freeze_path = model_dir / "protocol_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = {
        "status": "missingness_scores_frozen_before_primary_oot_outcome_join",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    if any(freeze.get(field) != value for field, value in expected.items()):
        raise RuntimeError("Missingness freeze identity changed before evaluation.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("Missingness freeze reports OOT outcome leakage.")
    if (data_dir / "evaluation").exists():
        raise FileExistsError("Missingness evaluation already exists.")
    artifacts = verified_freeze_artifact_paths(freeze, repo_root=root)
    raw_path = resolve_repo_input(str(parent["source"]["raw_path"]), repo_root=root)
    universe = load_outcome_universe(parent, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, parent)
    scores = pd.read_parquet(artifacts["scores"])
    recipes = load_recipes(artifacts["recipes"])
    fit_audit = pd.read_parquet(artifacts["fit_audit"])
    coverage = temporal_coverage_audit(
        scores,
        outcomes,
        recipes,
        fit_audit,
        roles=("primary_oot",),
        taxonomy_group_counts=(5,),
        strata=(-1,),
    )
    prediction = _prediction_metrics(scores, outcomes)
    endpoint_audit = endpoint_resolution_audit(outcomes, roles=("primary_oot",))
    if len(coverage) != 24 or coverage["learner"].nunique() != 3:
        raise RuntimeError("Missingness coverage grid is incomplete.")
    summaries: list[dict[str, Any]] = []
    nominal = float(config["evaluation"]["nominal_coverage"])
    for learner, frame in coverage.groupby("learner", observed=True, sort=True):
        if len(frame) != int(config["evaluation"]["expected_windows"]):
            raise RuntimeError(f"Missingness coverage is incomplete for {learner}.")
        summaries.append(
            {
                "learner": str(learner),
                "coverage_lower_min": float(frame["coverage_lower"].min()),
                "coverage_upper_max": float(frame["coverage_upper"].max()),
                "windows_with_upper_below_nominal": int(frame["coverage_upper"].lt(nominal).sum()),
                "all_windows_upper_below_nominal": bool(frame["coverage_upper"].lt(nominal).all()),
            }
        )
    output_files = {
        "temporal_coverage": atomic_write_parquet(
            coverage, data_dir / "evaluation/temporal_coverage.parquet"
        ),
        "prediction_metrics": atomic_write_parquet(
            prediction, data_dir / "evaluation/prediction_metrics.parquet"
        ),
        "endpoint_resolution_audit": atomic_write_parquet(
            endpoint_audit, data_dir / "evaluation/endpoint_resolution_audit.parquet"
        ),
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_no_selection_missingness_sensitivity",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "specifications": list(config["specifications"]),
        "coverage": summaries,
        "prediction_metrics": prediction.to_dict(orient="records"),
        "endpoint_resolution_audit": endpoint_audit.to_dict(orient="records"),
        "interpretation": {
            "model_or_encoding_selected": False,
            "portfolio_claim_authorized": False,
            "missing_at_random_claim_authorized": False,
            "robustness_scope": "three_declared_missingness_encodings_only",
        },
        "source_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
        "evaluation_artifacts": {
            name: relative_artifact_descriptor(path, repo_root=root)
            for name, path in output_files.items()
        },
        "implementation_provenance": _implementation(resolved_config, config, repo_root=root),
        "environment": environment_provenance(root),
        "git": git_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(
        model_dir / str(config["output"]["deterministic_summary"]), summary
    )
    atomic_write_json(
        model_dir / str(config["output"]["execution_receipt"]),
        {
            "status": summary["status"],
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return summary_path
