"""Run isolated TabPrep-inspired PD challengers for CRPTO.

This script never writes canonical champion artifacts. All models, predictions,
feature manifests and audit files are forced under experiment-only directories.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from scripts.train_pd_model import _apply_calibrator, _prepare_catboost_frame
from src.evaluation.fairness import fairness_report
from src.evaluation.metrics import classification_metrics
from src.features.feature_config_io import load_feature_config, save_feature_config
from src.features.feature_engineering import TARGET
from src.features.tabprep_challenger import (
    TabPrepChallengerTransformer,
    resolve_tabprep_categorical_features,
    resolve_tabprep_input_features,
    validate_no_forbidden_features,
)
from src.models.pd_model import (
    resolve_monotonic_constraints,
    temporal_train_val_split,
    train_catboost_default,
)
from src.models.venn_abers import VennAbersScoreCalibrator
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet, atomic_write_pickle

PROTECTED_PATHS = {
    Path("models/pd_canonical.cbm"),
    Path("models/pd_canonical_calibrator.pkl"),
    Path("models/final_project_promotion.json"),
    Path("models/conformal_policy_status.json"),
    Path("data/processed/conformal_intervals_mondrian.parquet"),
    Path("EXTRACTION_MANIFEST.json"),
}
PROTECTED_PREFIXES = {
    Path(
        "data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734"
    ),
}
ALLOWED_OUTPUT_PREFIXES = {
    Path("data/processed/experiments"),
    Path("models/experiments"),
    Path("reports/crpto/experiments"),
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/experiments/tabprep_challenger.yaml",
        help="Path to the isolated TabPrep challenger YAML config.",
    )
    parser.add_argument(
        "--variant",
        default=None,
        help="Variant to run: safe_500, balanced_1500, full_3000, or all.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional single seed override. Defaults to the config seed list.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=None,
        help="Optional sample rows per split for smoke runs. Use 0 with --full-data.",
    )
    parser.add_argument(
        "--full-data",
        action="store_true",
        help="Disable sampling even when the config has sample_rows set.",
    )
    parser.add_argument(
        "--persist-transformed",
        action="store_true",
        help="Persist transformed train/validation/calibration/test matrices.",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the no-generated-features baseline control.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the configured TabPrep challenger experiment."""
    args = parse_args()
    config = _load_config(Path(args.config))
    run_tag = str(config.get("run_tag", "tabprep-challenger-2026-06-16"))
    variants = _resolve_variants(config, args.variant)
    seeds = [int(args.seed)] if args.seed is not None else [int(seed) for seed in config["seeds"]]
    sample_rows = 0 if args.full_data else _resolve_sample_rows(config, args.sample_rows)
    persist_transformed = bool(
        args.persist_transformed or config["tabprep"].get("persist_transformed")
    )

    splits = _load_splits(config)
    if sample_rows > 0:
        splits = {
            name: _sample_split(frame, sample_rows=sample_rows, seed=seeds[0])
            for name, frame in splits.items()
        }

    feature_config = _load_feature_config(config)
    base_features = resolve_tabprep_input_features(
        splits["train"],
        feature_config=feature_config,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    validate_no_forbidden_features(
        base_features,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    categorical_features = resolve_tabprep_categorical_features(
        base_features,
        feature_config=feature_config,
    )

    train_fit, train_val = temporal_train_val_split(
        splits["train"],
        val_fraction=float(config["validation"]["val_fraction"]),
        date_col=str(config["validation"]["date_col"]),
    )

    summary: dict[str, Any] = {
        "run_tag": run_tag,
        "sample_rows": sample_rows,
        "variants": variants,
        "seeds": seeds,
        "base_feature_count": len(base_features),
        "categorical_feature_count": len(categorical_features),
        "results": [],
    }

    if not args.skip_baseline:
        for seed in seeds:
            summary["results"].append(
                _run_model_case(
                    case_name="baseline_control",
                    run_tag=run_tag,
                    seed=seed,
                    config=config,
                    train_fit=train_fit,
                    train_val=train_val,
                    calibration=splits["calibration"],
                    test=splits["test"],
                    features=base_features,
                    categorical_features=categorical_features,
                    generated_train_fit=None,
                    generated_train_val=None,
                    generated_calibration=None,
                    generated_test=None,
                    transformer=None,
                    persist_transformed=persist_transformed,
                )
            )

    for variant in variants:
        for seed in seeds:
            transformer = TabPrepChallengerTransformer(
                variant=variant,
                input_features=base_features,
                categorical_features=categorical_features,
                target=TARGET,
                random_state=seed,
                extra_blacklist=config["tabprep"].get("extra_blacklist", []),
            )
            generated_train_fit = transformer.fit_transform(
                train_fit,
                train_fit[TARGET].astype(int),
                issue_dates=train_fit.get(str(config["validation"]["date_col"])),
            )
            generated_train_val = transformer.transform(train_val)
            generated_calibration = transformer.transform(splits["calibration"])
            generated_test = transformer.transform(splits["test"])
            case_result = _run_model_case(
                case_name=variant,
                run_tag=run_tag,
                seed=seed,
                config=config,
                train_fit=train_fit,
                train_val=train_val,
                calibration=splits["calibration"],
                test=splits["test"],
                features=base_features,
                categorical_features=categorical_features,
                generated_train_fit=generated_train_fit,
                generated_train_val=generated_train_val,
                generated_calibration=generated_calibration,
                generated_test=generated_test,
                transformer=transformer,
                persist_transformed=persist_transformed,
            )
            summary["results"].append(case_result)

    output_dir = _case_dir(
        Path(config["output"]["report_dir"]),
        run_tag=run_tag,
        case_name="summary",
        seed=seeds[0],
    )
    atomic_write_json(output_dir / "tabprep_challenger_summary.json", summary)
    logger.info("Wrote TabPrep challenger summary to {}", output_dir)


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise TypeError(f"Config must be a mapping: {path}")
    config.setdefault("run_tag", "tabprep-challenger-2026-06-16")
    config.setdefault("seeds", [42, 52, 62])
    config.setdefault("sample_rows", 0)
    config.setdefault("tabprep", {})
    config.setdefault("validation", {})
    config.setdefault("calibration", {})
    config.setdefault("output", {})
    config["tabprep"].setdefault("variants", ["safe_500", "balanced_1500", "full_3000"])
    config["tabprep"].setdefault("extra_blacklist", [])
    config["tabprep"].setdefault("persist_transformed", False)
    config["tabprep"].setdefault("suspicious_auc_threshold", 0.90)
    config["validation"].setdefault("val_fraction", 0.15)
    config["validation"].setdefault("date_col", "issue_d")
    config["calibration"].setdefault("method", "auto")
    config["calibration"].setdefault("candidates", ["platt", "isotonic", "venn_abers"])
    config["output"].setdefault("data_dir", "data/processed/experiments/tabprep")
    config["output"].setdefault("model_dir", "models/experiments/tabprep")
    config["output"].setdefault("report_dir", "reports/crpto/experiments/tabprep")
    config.setdefault("model", {})
    config["model"].setdefault("params", {})
    _validate_output_roots(config["output"].values())
    return config


def _resolve_variants(config: Mapping[str, Any], variant_override: str | None) -> list[str]:
    if variant_override and variant_override != "all":
        return [variant_override]
    return [str(variant) for variant in config["tabprep"]["variants"]]


def _resolve_sample_rows(config: Mapping[str, Any], cli_value: int | None) -> int:
    if cli_value is not None:
        return max(0, int(cli_value))
    return max(0, int(config.get("sample_rows", 0)))


def _load_splits(config: Mapping[str, Any]) -> dict[str, pd.DataFrame]:
    data_cfg = config["data"]
    return {
        "train": pd.read_parquet(data_cfg["train_path"]),
        "calibration": pd.read_parquet(data_cfg["calibration_path"]),
        "test": pd.read_parquet(data_cfg["test_path"]),
    }


def _load_feature_config(config: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(config["data"].get("feature_config_path", "data/processed/feature_config.yml"))
    return load_feature_config(yaml_path=path, prefer="yaml")


def _sample_split(frame: pd.DataFrame, *, sample_rows: int, seed: int) -> pd.DataFrame:
    if sample_rows <= 0 or len(frame) <= sample_rows:
        return frame.reset_index(drop=True)
    sampled = frame.sample(n=sample_rows, random_state=seed)
    if "issue_d" in sampled.columns:
        sampled = sampled.sort_values("issue_d", kind="mergesort")
    return sampled.reset_index(drop=True)


def _run_model_case(
    *,
    case_name: str,
    run_tag: str,
    seed: int,
    config: Mapping[str, Any],
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    features: Sequence[str],
    categorical_features: Sequence[str],
    generated_train_fit: pd.DataFrame | None,
    generated_train_val: pd.DataFrame | None,
    generated_calibration: pd.DataFrame | None,
    generated_test: pd.DataFrame | None,
    transformer: TabPrepChallengerTransformer | None,
    persist_transformed: bool,
) -> dict[str, Any]:
    model_dir = _case_dir(
        Path(config["output"]["model_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    data_dir = _case_dir(
        Path(config["output"]["data_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    report_dir = _case_dir(
        Path(config["output"]["report_dir"]), run_tag=run_tag, case_name=case_name, seed=seed
    )
    _validate_output_roots([model_dir, data_dir, report_dir])

    generated_features = (
        list(generated_train_fit.columns) if generated_train_fit is not None else []
    )
    model_features = [*features, *generated_features]
    cat_features = [feature for feature in categorical_features if feature in model_features]

    x_train = _combine_features(train_fit, features, generated_train_fit)
    x_val = _combine_features(train_val, features, generated_train_val)
    x_cal = _combine_features(calibration, features, generated_calibration)
    x_test = _combine_features(test, features, generated_test)

    x_train_cb = _prepare_catboost_frame(x_train, model_features, cat_features)
    x_val_cb = _prepare_catboost_frame(x_val, model_features, cat_features)
    x_cal_cb = _prepare_catboost_frame(x_cal, model_features, cat_features)
    x_test_cb = _prepare_catboost_frame(x_test, model_features, cat_features)

    params = _model_params(config, model_features=model_features, seed=seed)
    model, train_metrics = train_catboost_default(
        x_train_cb,
        train_fit[TARGET].astype(int),
        x_val_cb,
        train_val[TARGET].astype(int),
        X_test=x_test_cb,
        y_test=test[TARGET].astype(int),
        cat_features=cat_features,
        params=params,
    )

    raw_cal = model.predict_proba(x_cal_cb)[:, 1]
    raw_test = model.predict_proba(x_test_cb)[:, 1]
    selected_calibrator, calibration_report = _select_calibrator(
        method=str(config["calibration"]["method"]),
        candidates=[str(item) for item in config["calibration"]["candidates"]],
        y_cal=calibration[TARGET].astype(int).to_numpy(),
        raw_cal=raw_cal,
    )
    calibrated_test = _apply_calibrator(selected_calibrator, raw_test)
    calibrated_cal = _apply_calibrator(selected_calibrator, raw_cal)

    test_metrics = classification_metrics(
        test[TARGET].astype(int).to_numpy(),
        np.asarray(calibrated_test, dtype=float),
    )
    cal_metrics = classification_metrics(
        calibration[TARGET].astype(int).to_numpy(),
        np.asarray(calibrated_cal, dtype=float),
    )
    fairness = _build_fairness_report(
        test,
        y_prob=np.asarray(calibrated_test, dtype=float),
        config=config,
    )
    audit = _build_audit_report(
        case_name=case_name,
        train_generated=generated_train_fit,
        test_generated=generated_test,
        y_train=train_fit[TARGET].astype(int),
        model=model,
        x_test=x_test_cb,
        y_test=test[TARGET].astype(int),
        cat_features=cat_features,
        config=config,
    )

    model_path = model_dir / "pd_tabprep_challenger.cbm"
    calibrator_path = model_dir / "pd_tabprep_calibrator.pkl"
    transformer_path = model_dir / "tabprep_transformer.pkl"
    prediction_path = data_dir / "test_predictions.parquet"
    status_path = model_dir / "tabprep_training_status.json"

    _assert_isolated_output(model_path)
    _assert_isolated_output(calibrator_path)
    _assert_isolated_output(transformer_path)
    _assert_isolated_output(prediction_path)
    _assert_isolated_output(status_path)

    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))
    atomic_write_pickle(calibrator_path, selected_calibrator)
    if transformer is not None:
        atomic_write_pickle(transformer_path, transformer)
        manifest = transformer.feature_manifest()
        atomic_write_parquet(manifest, report_dir / "generated_feature_manifest.parquet")
        atomic_write_json(
            report_dir / "tabprep_transformer_summary.json", transformer.state_summary()
        )
        _write_experiment_feature_config(
            report_dir / "feature_config.yml",
            base_features=features,
            generated_features=generated_features,
            categorical_features=cat_features,
        )

    predictions = _prediction_frame(
        test,
        raw_prob=raw_test,
        calibrated_prob=np.asarray(calibrated_test, dtype=float),
        case_name=case_name,
        seed=seed,
    )
    atomic_write_parquet(predictions, prediction_path)
    if not fairness.empty:
        atomic_write_parquet(fairness, report_dir / "fairness_report.parquet")
    atomic_write_json(report_dir / "audit_report.json", audit)

    if persist_transformed:
        _persist_transformed_frames(
            data_dir=data_dir,
            train_fit=x_train_cb,
            train_val=x_val_cb,
            calibration=x_cal_cb,
            test=x_test_cb,
        )

    status = {
        "run_tag": run_tag,
        "case_name": case_name,
        "seed": seed,
        "model_path": str(model_path),
        "calibrator_path": str(calibrator_path),
        "transformer_path": str(transformer_path) if transformer is not None else None,
        "prediction_path": str(prediction_path),
        "n_base_features": len(features),
        "n_generated_features": len(generated_features),
        "n_model_features": len(model_features),
        "categorical_features": cat_features,
        "training_metrics": train_metrics,
        "test_metrics": test_metrics,
        "calibration_metrics": cal_metrics,
        "calibration_selection": calibration_report,
        "audit_path": str(report_dir / "audit_report.json"),
    }
    atomic_write_json(status_path, status)
    logger.info(
        "{} seed {} done: test AUC={:.4f}, Brier={:.4f}, generated_features={}",
        case_name,
        seed,
        test_metrics["auc_roc"],
        test_metrics["brier_score"],
        len(generated_features),
    )
    return status


def _combine_features(
    frame: pd.DataFrame,
    base_features: Sequence[str],
    generated: pd.DataFrame | None,
) -> pd.DataFrame:
    base = frame[[feature for feature in base_features if feature in frame.columns]].copy()
    base = base.reset_index(drop=True)
    if generated is None:
        return base
    return pd.concat([base, generated.reset_index(drop=True)], axis=1)


def _model_params(
    config: Mapping[str, Any],
    *,
    model_features: Sequence[str],
    seed: int,
) -> dict[str, Any]:
    params = dict(config["model"].get("params", {}) or {})
    raw_constraints = params.pop("monotone_constraints", None)
    constraint_map = _parse_monotone_constraints(raw_constraints)
    constraint_map.update(config.get("tabprep", {}).get("monotonic_constraints", {}) or {})
    constraints = resolve_monotonic_constraints(
        list(model_features),
        constraints_config={str(key): int(value) for key, value in constraint_map.items()},
    )
    if constraints is not None:
        params["monotone_constraints"] = f"({constraints})"
    feature_weights = params.get("feature_weights")
    if isinstance(feature_weights, dict):
        weights_by_feature = {str(feature): float(weight) for feature, weight in feature_weights.items()}
        if any(feature in weights_by_feature for feature in model_features):
            params["feature_weights"] = [
                weights_by_feature.get(str(feature), 1.0) for feature in model_features
            ]
        else:
            params.pop("feature_weights", None)
    params["random_seed"] = int(seed)
    params["allow_writing_files"] = False
    params.setdefault("verbose", 100)
    return params


def _parse_monotone_constraints(raw: Any) -> dict[str, int]:
    if isinstance(raw, dict):
        return {str(key): int(value) for key, value in raw.items()}
    if not isinstance(raw, str) or not raw.strip():
        return {}
    parsed: dict[str, int] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        feature, value = part.split(":", 1)
        parsed[feature.strip()] = int(value.strip())
    return parsed


def _select_calibrator(
    *,
    method: str,
    candidates: Sequence[str],
    y_cal: np.ndarray,
    raw_cal: np.ndarray,
) -> tuple[Any, dict[str, Any]]:
    method = method.lower()
    if method != "auto":
        return _fit_calibrator(method, y_cal, raw_cal), {
            "selected_method": method,
            "reason": "fixed",
        }
    if len(y_cal) < 50 or len(np.unique(y_cal)) < 2:
        model = _fit_calibrator("platt", y_cal, raw_cal)
        return model, {"selected_method": "platt", "reason": "small_calibration_split"}

    split = max(10, int(round(len(y_cal) * 0.70)))
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            fitted = _fit_calibrator(candidate, y_cal[:split], raw_cal[:split])
            pred = _apply_calibrator(fitted, raw_cal[split:])
            rows.append(
                {
                    "method": candidate,
                    "brier_score": float(brier_score_loss(y_cal[split:], pred)),
                    "log_loss": float(log_loss(y_cal[split:], pred)),
                    "auc_roc": float(roc_auc_score(y_cal[split:], pred)),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive diagnostic path
            rows.append({"method": candidate, "error": str(exc)})
    feasible = [row for row in rows if "error" not in row]
    if not feasible:
        model = _fit_calibrator("platt", y_cal, raw_cal)
        return model, {
            "selected_method": "platt",
            "reason": "all_candidates_failed",
            "candidate_reports": rows,
        }
    feasible.sort(key=lambda row: (row["brier_score"], row["log_loss"], -row["auc_roc"]))
    selected = str(feasible[0]["method"])
    return _fit_calibrator(selected, y_cal, raw_cal), {
        "selected_method": selected,
        "reason": "holdout_brier_logloss_auc",
        "candidate_reports": rows,
    }


def _fit_calibrator(method: str, y_true: np.ndarray, raw_prob: np.ndarray) -> Any:
    method = method.lower()
    if method == "platt":
        model = LogisticRegression(max_iter=1000)
        model.fit(raw_prob.reshape(-1, 1), y_true)
        return model
    if method == "isotonic":
        model = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
        model.fit(raw_prob, y_true)
        return model
    if method == "venn_abers":
        model = VennAbersScoreCalibrator()
        model.fit(raw_prob, y_true)
        return model
    if method == "beta":
        from src.models.calibration import calibrate_beta

        return calibrate_beta(y_true, raw_prob)
    if method == "temperature":
        from src.models.calibration import TemperatureScalingCalibrator

        return TemperatureScalingCalibrator().fit(raw_prob, y_true)
    if method == "quadratic_logit":
        from src.models.calibration import QuadraticLogitCalibrator

        return QuadraticLogitCalibrator().fit(raw_prob, y_true)
    raise ValueError(f"Unsupported calibration method: {method}")


def _prediction_frame(
    frame: pd.DataFrame,
    *,
    raw_prob: np.ndarray,
    calibrated_prob: np.ndarray,
    case_name: str,
    seed: int,
) -> pd.DataFrame:
    cols = [col for col in ["id", "issue_d", TARGET] if col in frame.columns]
    out = frame[cols].copy()
    out["pd_raw"] = raw_prob
    out["pd_calibrated"] = calibrated_prob
    out["case_name"] = case_name
    out["seed"] = int(seed)
    return out


def _build_fairness_report(
    test: pd.DataFrame,
    *,
    y_prob: np.ndarray,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    columns = config.get("evaluation", {}).get(
        "fairness_columns",
        ["grade", "sub_grade", "term", "purpose", "home_ownership"],
    )
    groups = {col: test[col].astype(str).to_numpy() for col in columns if col in test.columns}
    if not groups:
        return pd.DataFrame()
    return fairness_report(
        y_true=test[TARGET].astype(int).to_numpy(),
        y_pred_proba=y_prob,
        groups_dict=groups,
        threshold=float(config.get("evaluation", {}).get("fairness_threshold", 0.50)),
    )


def _build_audit_report(
    *,
    case_name: str,
    train_generated: pd.DataFrame | None,
    test_generated: pd.DataFrame | None,
    y_train: pd.Series,
    model: Any,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    cat_features: Sequence[str],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    suspicious_threshold = float(config.get("tabprep", {}).get("suspicious_auc_threshold", 0.90))
    report: dict[str, Any] = {
        "case_name": case_name,
        "suspicious_auc_threshold": suspicious_threshold,
        "suspicious_single_feature_auc": [],
        "generated_feature_drift": [],
        "top_feature_importance": [],
    }
    if train_generated is not None and test_generated is not None:
        report["suspicious_single_feature_auc"] = _single_feature_auc_audit(
            train_generated,
            y_train,
            threshold=suspicious_threshold,
        )
        report["generated_feature_drift"] = _generated_drift_audit(train_generated, test_generated)
    try:
        from catboost import Pool

        importance = model.get_feature_importance(
            Pool(x_test, y_test.astype(int), cat_features=list(cat_features)),
            prettified=True,
        )
        if isinstance(importance, pd.DataFrame):
            report["top_feature_importance"] = importance.head(50).to_dict(orient="records")
    except Exception as exc:  # pragma: no cover - non-critical audit path
        report["feature_importance_error"] = str(exc)
    return report


def _single_feature_auc_audit(
    generated: pd.DataFrame,
    y: pd.Series,
    *,
    threshold: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    y_values = y.astype(int).to_numpy()
    if len(np.unique(y_values)) < 2:
        return rows
    for feature in generated.columns:
        values = pd.to_numeric(generated[feature], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        fill = values.median()
        if not np.isfinite(fill):
            fill = 0.0
        values = values.fillna(float(fill)).to_numpy(dtype=float)
        if len(np.unique(values)) < 2:
            continue
        auc = float(roc_auc_score(y_values, values))
        directional_auc = max(auc, 1.0 - auc)
        if directional_auc >= threshold:
            rows.append({"feature": feature, "auc": directional_auc})
    rows.sort(key=lambda row: -float(row["auc"]))
    return rows


def _generated_drift_audit(
    train_generated: pd.DataFrame, test_generated: pd.DataFrame
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in train_generated.columns:
        train_values = pd.to_numeric(train_generated[feature], errors="coerce")
        test_values = pd.to_numeric(test_generated[feature], errors="coerce")
        rows.append(
            {
                "feature": feature,
                "coverage_train": float(train_values.notna().mean()),
                "coverage_test": float(test_values.notna().mean()),
                "mean_train": float(train_values.mean()) if train_values.notna().any() else None,
                "mean_test": float(test_values.mean()) if test_values.notna().any() else None,
                "std_train": float(train_values.std()) if train_values.notna().any() else None,
                "std_test": float(test_values.std()) if test_values.notna().any() else None,
            }
        )
    return rows


def _write_experiment_feature_config(
    path: Path,
    *,
    base_features: Sequence[str],
    generated_features: Sequence[str],
    categorical_features: Sequence[str],
) -> None:
    cfg = {
        "CATBOOST_FEATURES": [*base_features, *generated_features],
        "CATEGORICAL_FEATURES": list(categorical_features),
        "TABPREP_BASE_FEATURES": list(base_features),
        "TABPREP_GENERATED_FEATURES": list(generated_features),
        "schema_version": "tabprep-challenger-2026-06-16",
    }
    _assert_isolated_output(path)
    save_feature_config(cfg, yaml_path=path)


def _persist_transformed_frames(
    *,
    data_dir: Path,
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    for name, frame in {
        "train_fit_tabprep.parquet": train_fit,
        "train_val_tabprep.parquet": train_val,
        "calibration_tabprep.parquet": calibration,
        "test_tabprep.parquet": test,
    }.items():
        path = data_dir / name
        _assert_isolated_output(path)
        atomic_write_parquet(frame, path)


def _case_dir(root: Path, *, run_tag: str, case_name: str, seed: int) -> Path:
    return root / run_tag / case_name / f"seed_{seed}"


def _validate_output_roots(paths: Iterable[Any]) -> None:
    for raw_path in paths:
        _assert_isolated_output(Path(raw_path))


def _assert_isolated_output(path: Path) -> None:
    normalized = _normalize_repo_path(path)
    if normalized in PROTECTED_PATHS:
        raise ValueError(f"Refusing to write protected CRPTO artifact: {path}")
    if any(_is_relative_to(normalized, protected) for protected in PROTECTED_PREFIXES):
        raise ValueError(f"Refusing to write below protected CRPTO artifact directory: {path}")
    if not any(_is_relative_to(normalized, allowed) for allowed in ALLOWED_OUTPUT_PREFIXES):
        raise ValueError(
            "TabPrep challenger outputs must stay under "
            f"{sorted(str(root) for root in ALLOWED_OUTPUT_PREFIXES)}; got {path}"
        )


def _normalize_repo_path(path: Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        try:
            return Path(path.relative_to(Path.cwd()).as_posix())
        except ValueError:
            return path
    return Path(path.as_posix())


def _is_relative_to(path: Path | str, parent: Path) -> bool:
    try:
        Path(path).relative_to(parent)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()
