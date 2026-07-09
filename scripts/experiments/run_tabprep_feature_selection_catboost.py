"""Run full-data CatBoost experiments with selected TabPrep features.

This runner is experimental-only. It reads frozen CRPTO feature splits, creates
TabPrep features once, ranks generated features using a prior selector model,
and trains several compact CatBoost challengers under isolated output roots.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostClassifier, Pool
from loguru import logger
from sklearn.metrics import roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.run_tabprep_challenger import (  # noqa: E402
    _apply_calibrator,
    _build_fairness_report,
    _case_dir,
    _combine_features,
    _model_params,
    _prediction_frame,
    _prepare_catboost_frame,
    _resolve_sample_rows,
    _sample_split,
    _select_calibrator,
    _validate_output_roots,
)
from src.evaluation.metrics import classification_metrics  # noqa: E402
from src.features.feature_config_io import load_feature_config  # noqa: E402
from src.features.feature_engineering import TARGET  # noqa: E402
from src.features.tabprep_challenger import (  # noqa: E402
    TabPrepChallengerTransformer,
    resolve_tabprep_categorical_features,
    resolve_tabprep_input_features,
    validate_no_forbidden_features,
)
from src.models.pd_model import temporal_train_val_split, train_catboost_default  # noqa: E402
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    atomic_write_pickle,
    write_runtime_checkpoint,
    write_runtime_status,
)

DEFAULT_CASES = [
    "core42",
    "core42_woe",
    "pool93_woe",
    "pool93_top50",
    "pool93_top100",
    "pool93_business80",
    "core42_business80",
]
STABLE_CORE_EXCLUDES = {"rev_utilization", "high_util_pct"}
BUSINESS_SOURCE_DENY_TOKENS = {"__is_missing"}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/experiments/tabprep_catboost_full.yaml",
        help="Base experiment config.",
    )
    parser.add_argument(
        "--run-tag",
        default="tabprep-feature-selection-2026-06-17",
        help="Isolated run tag for selected-feature experiments.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--tabprep-seed",
        type=int,
        default=None,
        help=(
            "Seed for TabPrep feature generation. Defaults to --seed; set to 42 "
            "when testing CatBoost seed stability on the same generated feature space."
        ),
    )
    parser.add_argument("--variant", default="balanced_1500")
    parser.add_argument(
        "--selector-model",
        default=(
            "models/experiments/tabprep/tabprep-catboost-full-2026-06-17/"
            "balanced_1500/seed_42/pd_tabprep_challenger.cbm"
        ),
        help="Previously trained all-feature TabPrep CatBoost model for ranking.",
    )
    parser.add_argument(
        "--cases",
        default=",".join(DEFAULT_CASES),
        help="Comma-separated cases to run.",
    )
    parser.add_argument(
        "--ranking-method",
        choices=["pvc", "shap_blend"],
        default="pvc",
        help="Feature ranking source: CatBoost PredictionValuesChange or blended PVC+SHAP ranks.",
    )
    parser.add_argument(
        "--shap-rows",
        type=int,
        default=30000,
        help="Maximum validation rows used for SHAP ranking when --ranking-method=shap_blend.",
    )
    parser.add_argument(
        "--calibration-method",
        default=None,
        help="Override calibration.method from config.",
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
    return parser.parse_args()


def main() -> None:
    """Run selected-feature CatBoost experiments."""
    args = parse_args()
    config = _load_config(Path(args.config))
    if args.calibration_method is not None:
        config.setdefault("calibration", {})["method"] = str(args.calibration_method)
    run_tag = str(args.run_tag)
    seed = int(args.seed)
    tabprep_seed = int(args.tabprep_seed if args.tabprep_seed is not None else args.seed)
    cases = [case.strip() for case in str(args.cases).split(",") if case.strip()]
    sample_rows = 0 if args.full_data else _resolve_sample_rows(config, args.sample_rows)
    started = time.perf_counter()
    runtime_paths = _runtime_paths(config, run_tag=run_tag, seed=seed)
    _write_runtime(
        runtime_paths=runtime_paths,
        phase="start",
        state="running",
        run_tag=run_tag,
        extra={
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "variant": str(args.variant),
            "cases": cases,
            "sample_rows": sample_rows,
        },
    )

    train = pd.read_parquet(config["data"]["train_path"])
    calibration = pd.read_parquet(config["data"]["calibration_path"])
    test = pd.read_parquet(config["data"]["test_path"])
    if sample_rows > 0:
        train = _sample_split(train, sample_rows=sample_rows, seed=seed)
        calibration = _sample_split(calibration, sample_rows=sample_rows, seed=seed)
        test = _sample_split(test, sample_rows=sample_rows, seed=seed)
    feature_config = load_feature_config(
        yaml_path=Path(config["data"]["feature_config_path"]),
        prefer="yaml",
    )

    pool_features = resolve_tabprep_input_features(
        train,
        feature_config=feature_config,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    validate_no_forbidden_features(
        pool_features,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    categorical_features = resolve_tabprep_categorical_features(
        pool_features,
        feature_config=feature_config,
    )
    train_columns = [str(column) for column in train.columns]
    core_features = _resolve_core_features(feature_config, train_columns)
    catboost_features = _resolve_catboost_features(feature_config, train_columns)
    woe_features = _resolve_woe_features(feature_config, train_columns)

    train_fit, train_val = temporal_train_val_split(
        train,
        val_fraction=float(config["validation"]["val_fraction"]),
        date_col=str(config["validation"]["date_col"]),
    )
    del train
    gc.collect()

    transformer = TabPrepChallengerTransformer(
        variant=str(args.variant),
        input_features=pool_features,
        categorical_features=categorical_features,
        target=TARGET,
        random_state=tabprep_seed,
        extra_blacklist=config["tabprep"].get("extra_blacklist", []),
    )
    logger.info("Fitting TabPrep {} once for selected-feature runs", args.variant)
    generated_train_fit = transformer.fit_transform(
        train_fit,
        train_fit[TARGET].astype(int),
        issue_dates=train_fit.get(str(config["validation"]["date_col"])),
    )
    generated_train_val = transformer.transform(train_val)
    generated_calibration = transformer.transform(calibration)
    generated_test = transformer.transform(test)

    generated_features = list(generated_train_fit.columns)
    manifest = transformer.feature_manifest()
    pool_ranking, ranking, ranking_diagnostics = _load_selector_rankings(
        selector_model_path=Path(args.selector_model),
        pool_features=pool_features,
        generated_features=generated_features,
        ranking_method=str(args.ranking_method),
        shap_rows=int(args.shap_rows),
        train_val=train_val,
        train_fit=train_fit,
        generated_train_val=generated_train_val,
        categorical_features=categorical_features,
    )
    business_ranking = _business_ranking(ranking, manifest)
    case_features = _build_case_features(
        cases=cases,
        core_features=core_features,
        catboost_features=catboost_features,
        pool_features=pool_features,
        pool_ranking=pool_ranking,
        woe_features=woe_features,
        generated_ranking=ranking,
        business_ranking=business_ranking,
    )
    _write_selection_manifest(
        config=config,
        run_tag=run_tag,
        seed=seed,
        tabprep_seed=tabprep_seed,
        cases=case_features,
        ranking=ranking,
        pool_ranking=pool_ranking,
        business_ranking=business_ranking,
        manifest=manifest,
        ranking_diagnostics=ranking_diagnostics,
    )
    _write_checkpoint(
        runtime_paths=runtime_paths,
        checkpoint_name="selection_manifest",
        payload={
            "run_tag": run_tag,
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "cases": list(case_features),
            "pool_ranking_count": len(pool_ranking),
            "generated_ranking_count": len(ranking),
            "business_ranking_count": len(business_ranking),
        },
    )

    results: list[dict[str, Any]] = []
    for case_name, feature_set in case_features.items():
        generated_subset = [feature for feature in feature_set if feature in generated_features]
        base_subset = [feature for feature in feature_set if feature not in generated_features]
        result = _run_selected_case(
            case_name=case_name,
            run_tag=run_tag,
            seed=seed,
            tabprep_seed=tabprep_seed,
            config=config,
            train_fit=train_fit,
            train_val=train_val,
            calibration=calibration,
            test=test,
            base_features=base_subset,
            categorical_features=categorical_features,
            generated_train_fit=generated_train_fit[generated_subset],
            generated_train_val=generated_train_val[generated_subset],
            generated_calibration=generated_calibration[generated_subset],
            generated_test=generated_test[generated_subset],
            transformer_summary=transformer.state_summary(),
            selection_sources={
                "core_features": core_features,
                "pool_features": pool_features,
                "woe_features": woe_features,
                "generated_features": generated_subset,
            },
        )
        results.append(result)
        _write_runtime(
            runtime_paths=runtime_paths,
            phase="case_complete",
            state="running",
            run_tag=run_tag,
            extra={
                "seed": seed,
                "tabprep_seed": tabprep_seed,
                "completed_cases": [row["case_name"] for row in results],
                "latest_case": case_name,
                "latest_auc": result.get("test_metrics", {}).get("auc_roc"),
                "best_auc": max(
                    float(row.get("test_metrics", {}).get("auc_roc", float("-inf")))
                    for row in results
                ),
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        gc.collect()

    summary_dir = _case_dir(
        Path(config["output"]["report_dir"]),
        run_tag=run_tag,
        case_name="summary",
        seed=seed,
    )
    atomic_write_json(
        summary_dir / "selected_feature_experiment_summary.json",
        {
            "run_tag": run_tag,
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "variant": str(args.variant),
            "elapsed_seconds": time.perf_counter() - started,
            "cases": list(case_features),
            "results": results,
        },
    )
    _write_checkpoint(
        runtime_paths=runtime_paths,
        checkpoint_name="summary",
        payload={
            "summary_path": str(summary_dir / "selected_feature_experiment_summary.json"),
            "results": results,
        },
    )
    _write_runtime(
        runtime_paths=runtime_paths,
        phase="complete",
        state="completed",
        run_tag=run_tag,
        extra={
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "elapsed_seconds": time.perf_counter() - started,
            "summary_path": str(summary_dir / "selected_feature_experiment_summary.json"),
            "completed_cases": [row["case_name"] for row in results],
        },
    )


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise TypeError(f"Config must be a mapping: {path}")
    config.setdefault("calibration", {})
    config["calibration"].setdefault("method", "auto")
    config["calibration"].setdefault("candidates", ["platt", "isotonic", "venn_abers"])
    _validate_output_roots(config["output"].values())
    return config


def _resolve_core_features(
    feature_config: Mapping[str, Any],
    columns: Sequence[str],
) -> list[str]:
    available = set(columns)
    return [
        str(feature)
        for feature in feature_config.get("CATBOOST_FEATURES", [])
        if feature in available and feature not in STABLE_CORE_EXCLUDES
    ]


def _resolve_catboost_features(
    feature_config: Mapping[str, Any],
    columns: Sequence[str],
) -> list[str]:
    available = set(columns)
    return [
        str(feature)
        for feature in feature_config.get("CATBOOST_FEATURES", [])
        if feature in available
    ]


def _resolve_woe_features(
    feature_config: Mapping[str, Any],
    columns: Sequence[str],
) -> list[str]:
    available = set(columns)
    return [
        str(feature) for feature in feature_config.get("WOE_FEATURES", []) if feature in available
    ]


def _load_selector_rankings(
    *,
    selector_model_path: Path,
    pool_features: Sequence[str],
    generated_features: Sequence[str],
    ranking_method: str,
    shap_rows: int,
    train_val: pd.DataFrame,
    train_fit: pd.DataFrame,
    generated_train_val: pd.DataFrame,
    categorical_features: Sequence[str],
) -> tuple[list[str], list[str], pd.DataFrame]:
    model = CatBoostClassifier()
    model.load_model(str(selector_model_path))
    feature_names = list(model.feature_names_)
    pvc_importances = model.get_feature_importance(type="PredictionValuesChange")
    scores = dict(zip(feature_names, [float(x) for x in pvc_importances], strict=False))
    if ranking_method == "shap_blend":
        shap_scores = _selector_shap_scores(
            model=model,
            pool_features=pool_features,
            generated_features=generated_features,
            train_val=train_val,
            generated_train_val=generated_train_val,
            categorical_features=categorical_features,
            max_rows=shap_rows,
        )
        scores = _blend_rank_scores(scores, shap_scores)

    generated = set(generated_features)
    generated_ranked = [
        feature
        for feature, score in sorted(
            scores.items(),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        if feature in generated and float(score) > 0.0
    ]
    pool_ranked, ranking_diagnostics = _rank_pool_features(
        pool_features=pool_features,
        selector_scores=scores,
        train_fit=train_fit,
        train_val=train_val,
        categorical_features=categorical_features,
    )
    missing = [feature for feature in generated_features if feature not in feature_names]
    if missing:
        logger.warning("Selector model is missing {} generated features", len(missing))
    pool_missing = [feature for feature in pool_features if feature not in feature_names]
    if pool_missing:
        logger.warning("Selector model is missing {} pool features", len(pool_missing))
    logger.info(
        "Loaded {} ranked pool features and {} ranked generated features from {} using {}",
        len(pool_ranked),
        len(generated_ranked),
        selector_model_path,
        ranking_method,
    )
    return pool_ranked, generated_ranked, ranking_diagnostics


def _rank_pool_features(
    *,
    pool_features: Sequence[str],
    selector_scores: Mapping[str, float],
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    categorical_features: Sequence[str],
) -> tuple[list[str], pd.DataFrame]:
    """Rank base pool features even when the selector model omits them.

    Earlier TabPrep selector runs could produce a strong generated-feature
    ranking while leaving ``pool_ranking`` empty.  The champion reopen cases
    need an explicit ranking for the 93-feature pool, so we blend selector PVC
    or SHAP importance with leakage-safe univariate diagnostics fitted on the
    train-fit slice and evaluated on the temporal validation slice.
    """
    pool = [feature for feature in dict.fromkeys(pool_features) if feature in train_val.columns]
    fallback = _pool_feature_diagnostics(
        pool_features=pool,
        train_fit=train_fit,
        train_val=train_val,
        categorical_features=categorical_features,
    )
    selector_norm = _minmax_by_feature(
        {feature: max(0.0, float(selector_scores.get(feature, 0.0))) for feature in pool}
    )
    fallback_norm = _minmax_by_feature(
        {row["feature"]: float(row["fallback_score"]) for row in fallback}
    )

    rows: list[dict[str, Any]] = []
    has_selector_signal = any(float(selector_scores.get(feature, 0.0)) > 0 for feature in pool)
    for row in fallback:
        feature = str(row["feature"])
        selector_component = float(selector_norm.get(feature, 0.0))
        fallback_component = float(fallback_norm.get(feature, 0.0))
        if has_selector_signal:
            blended = 0.65 * selector_component + 0.35 * fallback_component
            source = "selector_blend"
        else:
            blended = fallback_component
            source = "fallback_univariate"
        rows.append(
            {
                **row,
                "selector_score": float(selector_scores.get(feature, 0.0)),
                "selector_component": selector_component,
                "fallback_component": fallback_component,
                "ranking_score": blended,
                "ranking_source": source,
            }
        )

    diagnostics = pd.DataFrame(rows).sort_values(
        ["ranking_score", "selector_score", "fallback_score", "feature"],
        ascending=[False, False, False, True],
        kind="mergesort",
    )
    ranked = diagnostics.loc[diagnostics["ranking_score"] > 0, "feature"].astype(str).tolist()
    if not ranked:
        raise ValueError("Unable to rank any pool features for pooltop cases.")
    return ranked, diagnostics.reset_index(drop=True)


def _pool_feature_diagnostics(
    *,
    pool_features: Sequence[str],
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    categorical_features: Sequence[str],
) -> list[dict[str, Any]]:
    y_fit = train_fit[TARGET].astype(int)
    y_val = train_val[TARGET].astype(int)
    categorical = set(categorical_features)
    rows: list[dict[str, Any]] = []
    for feature in pool_features:
        if feature not in train_fit.columns or feature not in train_val.columns:
            continue
        if feature in categorical or train_fit[feature].dtype == "object":
            val_score = _encode_categorical_from_fit(
                train_fit[feature],
                y_fit,
                train_val[feature],
            )
            drift = _categorical_psi(train_fit[feature], train_val[feature])
            feature_type = "categorical"
        else:
            val_score = _numeric_validation_score(train_fit[feature], train_val[feature])
            drift = _numeric_psi(train_fit[feature], train_val[feature])
            feature_type = "numeric"
        score_values = pd.Series(val_score, index=train_val.index).astype(float)
        auc_strength = _safe_auc_strength(y_val, score_values)
        abs_corr = _safe_abs_corr(score_values, y_val)
        iv = _information_value(train_val[feature], y_val, categorical=feature in categorical)
        coverage = float(train_val[feature].notna().mean())
        fallback_score = (
            0.45 * auc_strength
            + 0.25 * np.sqrt(min(max(iv, 0.0), 1.0))
            + 0.20 * abs_corr
            + 0.10 * coverage
            - 0.15 * min(max(drift, 0.0), 1.0)
        )
        rows.append(
            {
                "feature": str(feature),
                "feature_type": feature_type,
                "auc_strength": float(auc_strength),
                "abs_corr": float(abs_corr),
                "iv": float(iv),
                "coverage": coverage,
                "psi_fit_to_val": float(drift),
                "fallback_score": float(max(fallback_score, 0.0)),
            }
        )
    return rows


def _numeric_validation_score(fit: pd.Series, val: pd.Series) -> pd.Series:
    fit_num = pd.to_numeric(fit, errors="coerce")
    val_num = pd.to_numeric(val, errors="coerce")
    fill = float(fit_num.median()) if fit_num.notna().any() else 0.0
    if not np.isfinite(fill):
        fill = 0.0
    return val_num.replace([np.inf, -np.inf], np.nan).fillna(fill)


def _encode_categorical_from_fit(
    fit: pd.Series,
    y_fit: pd.Series,
    val: pd.Series,
    *,
    smoothing: float = 20.0,
) -> pd.Series:
    global_mean = float(y_fit.mean())
    key_fit = fit.astype("string").fillna("__MISSING__")
    grouped = (
        pd.DataFrame({"key": key_fit, "target": y_fit.astype(float)})
        .groupby("key")["target"]
        .agg(["mean", "count"])
    )
    smoothed = (grouped["mean"] * grouped["count"] + global_mean * float(smoothing)) / (
        grouped["count"] + float(smoothing)
    )
    key_val = val.astype("string").fillna("__MISSING__")
    return key_val.map(smoothed.to_dict()).fillna(global_mean).astype(float)


def _safe_auc_strength(y_true: pd.Series, score: pd.Series) -> float:
    y = y_true.astype(int).to_numpy()
    values = pd.to_numeric(score, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if len(np.unique(y)) < 2 or int(values.nunique(dropna=True)) < 2:
        return 0.0
    fill = float(values.median()) if values.notna().any() else 0.0
    if not np.isfinite(fill):
        fill = 0.0
    auc = float(roc_auc_score(y, values.fillna(fill).to_numpy(dtype=float)))
    return float(max(auc, 1.0 - auc) * 2.0 - 1.0)


def _safe_abs_corr(score: pd.Series, y_true: pd.Series) -> float:
    values = pd.to_numeric(score, errors="coerce").replace([np.inf, -np.inf], np.nan)
    fill = float(values.median()) if values.notna().any() else 0.0
    if not np.isfinite(fill):
        fill = 0.0
    x = values.fillna(fill).to_numpy(dtype=float)
    y = y_true.astype(float).to_numpy()
    if np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        return 0.0
    corr = float(np.corrcoef(x, y)[0, 1])
    return float(abs(corr)) if np.isfinite(corr) else 0.0


def _information_value(series: pd.Series, y_true: pd.Series, *, categorical: bool) -> float:
    y = y_true.astype(int)
    if categorical:
        bins = series.astype("string").fillna("__MISSING__")
        top = set(bins.value_counts(dropna=False).head(30).index)
        bins = bins.where(bins.isin(top), "__OTHER__")
    else:
        numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
        if int(numeric.nunique(dropna=True)) < 2:
            return 0.0
        try:
            bins = pd.qcut(
                numeric.rank(method="first"), q=min(10, numeric.nunique()), duplicates="drop"
            )
        except ValueError:
            return 0.0
        bins = bins.astype("string").fillna("__MISSING__")
    frame = pd.DataFrame({"bin": bins, "target": y})
    grouped = frame.groupby("bin", observed=False)["target"].agg(["sum", "count"])
    bad = grouped["sum"].astype(float) + 0.5
    good = (grouped["count"] - grouped["sum"]).astype(float) + 0.5
    bad_dist = bad / bad.sum()
    good_dist = good / good.sum()
    iv = ((bad_dist - good_dist) * np.log(bad_dist / good_dist)).sum()
    return float(iv) if np.isfinite(iv) else 0.0


def _numeric_psi(fit: pd.Series, val: pd.Series) -> float:
    fit_num = pd.to_numeric(fit, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    val_num = pd.to_numeric(val, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(fit_num) < 10 or len(val_num) < 10 or int(fit_num.nunique()) < 2:
        return 0.0
    quantiles = np.linspace(0.0, 1.0, 11)
    edges = np.unique(np.nanquantile(fit_num.to_numpy(dtype=float), quantiles))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    expected, _ = np.histogram(fit_num, bins=edges)
    actual, _ = np.histogram(val_num, bins=edges)
    return _psi_from_counts(expected, actual)


def _categorical_psi(fit: pd.Series, val: pd.Series) -> float:
    fit_key = fit.astype("string").fillna("__MISSING__")
    val_key = val.astype("string").fillna("__MISSING__")
    top = set(fit_key.value_counts(dropna=False).head(30).index)
    fit_key = fit_key.where(fit_key.isin(top), "__OTHER__")
    val_key = val_key.where(val_key.isin(top), "__OTHER__")
    categories = sorted(set(fit_key.unique()) | set(val_key.unique()))
    expected = np.asarray([(fit_key == cat).sum() for cat in categories], dtype=float)
    actual = np.asarray([(val_key == cat).sum() for cat in categories], dtype=float)
    return _psi_from_counts(expected, actual)


def _psi_from_counts(expected: np.ndarray, actual: np.ndarray) -> float:
    eps = 1e-6
    expected_pct = np.clip(expected / max(float(expected.sum()), eps), eps, 1.0)
    actual_pct = np.clip(actual / max(float(actual.sum()), eps), eps, 1.0)
    psi = ((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)).sum()
    return float(psi) if np.isfinite(psi) else 0.0


def _minmax_by_feature(scores: Mapping[str, float]) -> dict[str, float]:
    clean = {feature: float(score) for feature, score in scores.items() if np.isfinite(score)}
    if not clean:
        return {}
    values = np.asarray(list(clean.values()), dtype=float)
    low = float(values.min())
    high = float(values.max())
    if high <= low:
        return {feature: 1.0 if score > 0 else 0.0 for feature, score in clean.items()}
    return {feature: (score - low) / (high - low) for feature, score in clean.items()}


def _selector_shap_scores(
    *,
    model: CatBoostClassifier,
    pool_features: Sequence[str],
    generated_features: Sequence[str],
    train_val: pd.DataFrame,
    generated_train_val: pd.DataFrame,
    categorical_features: Sequence[str],
    max_rows: int,
) -> dict[str, float]:
    selector_features = list(model.feature_names_)
    selected_generated = [feature for feature in generated_features if feature in selector_features]
    base_features = [feature for feature in pool_features if feature in selector_features]
    frame = _combine_features(train_val, base_features, generated_train_val[selected_generated])
    if max_rows > 0 and len(frame) > max_rows:
        frame = frame.sample(n=max_rows, random_state=42).sort_index()
    cat_features = [feature for feature in categorical_features if feature in selector_features]
    x_cb = _prepare_catboost_frame(frame, selector_features, cat_features)
    shap_pool = Pool(x_cb, cat_features=cat_features)
    shap_raw = model.get_feature_importance(type="ShapValues", data=shap_pool)
    shap_values = np.asarray(shap_raw[:, :-1], dtype=float)
    mean_abs = np.abs(shap_values).mean(axis=0)
    logger.info("Computed selector SHAP scores on {} rows", len(x_cb))
    return dict(zip(selector_features, [float(x) for x in mean_abs], strict=False))


def _blend_rank_scores(
    pvc_scores: Mapping[str, float],
    shap_scores: Mapping[str, float],
) -> dict[str, float]:
    features = sorted(set(pvc_scores) | set(shap_scores))
    pvc_rank = {
        feature: rank
        for rank, feature in enumerate(
            sorted(features, key=lambda f: float(pvc_scores.get(f, 0.0)), reverse=True),
            start=1,
        )
    }
    shap_rank = {
        feature: rank
        for rank, feature in enumerate(
            sorted(features, key=lambda f: float(shap_scores.get(f, 0.0)), reverse=True),
            start=1,
        )
    }
    return {
        feature: 1.0 / np.sqrt(float(pvc_rank[feature]) * float(shap_rank[feature]))
        for feature in features
    }


def _business_ranking(ranking: Sequence[str], manifest: pd.DataFrame) -> list[str]:
    if manifest.empty:
        return list(ranking)
    source_by_feature = dict(zip(manifest["feature"], manifest["source_features"], strict=False))
    generator_by_feature = dict(zip(manifest["feature"], manifest["generator"], strict=False))
    selected: list[str] = []
    for feature in ranking:
        sources = str(source_by_feature.get(feature, "")).split("|")
        if any(token in source for source in sources for token in BUSINESS_SOURCE_DENY_TOKENS):
            continue
        if str(generator_by_feature.get(feature, "")) == "rsfc" and len(sources) > 3:
            continue
        selected.append(feature)
    return selected


def _build_case_features(
    *,
    cases: Sequence[str],
    core_features: Sequence[str],
    catboost_features: Sequence[str],
    pool_features: Sequence[str],
    pool_ranking: Sequence[str],
    woe_features: Sequence[str],
    generated_ranking: Sequence[str],
    business_ranking: Sequence[str],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for case in cases:
        if case == "core42":
            features = list(core_features)
        elif case == "catboost44":
            features = list(catboost_features)
        elif case == "core42_woe":
            features = [*core_features, *woe_features]
        elif case == "pool93":
            features = list(pool_features)
        elif case == "pool93_woe":
            features = [*pool_features, *woe_features]
        elif case.startswith("pooltop") and "_tab" in case:
            x, y = _pool_tab_case_sizes(case, generated_token="_tab")
            features = [
                *_take_ranked(pool_ranking, x, case=case, label="pool"),
                *_take_ranked(generated_ranking, y, case=case, label="generated"),
            ]
        elif case.startswith("pooltop") and "_business" in case:
            x, y = _pool_tab_case_sizes(case, generated_token="_business")
            features = [
                *_take_ranked(pool_ranking, x, case=case, label="pool"),
                *_take_ranked(business_ranking, y, case=case, label="business generated"),
            ]
        elif case.startswith("pooltop") and case.endswith("_woe"):
            x = _case_k(case.removesuffix("_woe"), prefix="pooltop")
            features = [*_take_ranked(pool_ranking, x, case=case, label="pool"), *woe_features]
        elif case.startswith("pooltop"):
            x = _case_k(case, prefix="pooltop")
            features = list(_take_ranked(pool_ranking, x, case=case, label="pool"))
        elif case.startswith("pool93_top"):
            k = _case_k(case, prefix="pool93_top")
            features = [
                *pool_features,
                *_take_ranked(generated_ranking, k, case=case, label="generated"),
            ]
        elif case.startswith("pool93_woe_top"):
            k = _case_k(case, prefix="pool93_woe_top")
            features = [
                *pool_features,
                *woe_features,
                *_take_ranked(generated_ranking, k, case=case, label="generated"),
            ]
        elif case.startswith("pool93_business"):
            k = _case_k(case, prefix="pool93_business")
            features = [
                *pool_features,
                *_take_ranked(business_ranking, k, case=case, label="business generated"),
            ]
        elif case.startswith("core42_business"):
            k = _case_k(case, prefix="core42_business")
            features = [
                *core_features,
                *_take_ranked(business_ranking, k, case=case, label="business generated"),
            ]
        else:
            raise ValueError(f"Unknown feature-selection case: {case}")
        out[case] = list(dict.fromkeys(features))
    return out


def _pool_tab_case_sizes(case: str, *, generated_token: str) -> tuple[int, int]:
    pool_part, generated_part = case.split(generated_token, maxsplit=1)
    x = _case_k(pool_part, prefix="pooltop")
    y = int(generated_part)
    return x, y


def _case_k(case: str, *, prefix: str) -> int:
    raw = case.removeprefix(prefix)
    if not raw:
        raise ValueError(f"Case {case!r} requires a numeric suffix")
    return int(raw)


def _take_ranked(
    ranking: Sequence[str],
    k: int,
    *,
    case: str,
    label: str,
) -> list[str]:
    if k <= 0:
        return []
    if len(ranking) < k:
        raise ValueError(
            f"Case {case!r} requested top {k} {label} features, "
            f"but only {len(ranking)} ranked features are available."
        )
    return list(ranking[:k])


def _write_selection_manifest(
    *,
    config: Mapping[str, Any],
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    cases: Mapping[str, Sequence[str]],
    ranking: Sequence[str],
    pool_ranking: Sequence[str],
    business_ranking: Sequence[str],
    manifest: pd.DataFrame,
    ranking_diagnostics: pd.DataFrame,
) -> None:
    report_dir = _case_dir(
        Path(config["output"]["report_dir"]),
        run_tag=run_tag,
        case_name="selection_manifest",
        seed=seed,
    )
    atomic_write_json(
        report_dir / "selection_manifest.json",
        {
            "run_tag": run_tag,
            "seed": seed,
            "tabprep_seed": tabprep_seed,
            "cases": {name: list(features) for name, features in cases.items()},
            "pool_ranking_top200": list(pool_ranking[:200]),
            "generated_ranking_top200": list(ranking[:200]),
            "business_ranking_top200": list(business_ranking[:200]),
        },
    )
    atomic_write_parquet(manifest, report_dir / "generated_feature_manifest.parquet")
    if not ranking_diagnostics.empty:
        atomic_write_parquet(ranking_diagnostics, report_dir / "pool_ranking_diagnostics.parquet")


def _runtime_paths(config: Mapping[str, Any], *, run_tag: str, seed: int) -> dict[str, Path]:
    model_dir = _case_dir(
        Path(config["output"]["model_dir"]),
        run_tag=run_tag,
        case_name="runtime",
        seed=seed,
    )
    _validate_output_roots([model_dir])
    return {
        "status": model_dir / "runtime_status.json",
        "checkpoints": model_dir / "checkpoints",
    }


def _write_runtime(
    *,
    runtime_paths: Mapping[str, Path],
    phase: str,
    state: str,
    run_tag: str,
    extra: Mapping[str, Any] | None = None,
) -> None:
    write_runtime_status(
        "champion_reopen_feature_selection",
        phase=phase,
        state=state,
        run_tag=run_tag,
        status_path=runtime_paths["status"],
        extra=dict(extra or {}),
    )


def _write_checkpoint(
    *,
    runtime_paths: Mapping[str, Path],
    checkpoint_name: str,
    payload: Mapping[str, Any],
) -> None:
    write_runtime_checkpoint(
        "champion_reopen_feature_selection",
        checkpoint_name,
        dict(payload),
        checkpoint_dir=runtime_paths["checkpoints"],
    )


def _run_selected_case(
    *,
    case_name: str,
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    config: Mapping[str, Any],
    train_fit: pd.DataFrame,
    train_val: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    base_features: Sequence[str],
    categorical_features: Sequence[str],
    generated_train_fit: pd.DataFrame,
    generated_train_val: pd.DataFrame,
    generated_calibration: pd.DataFrame,
    generated_test: pd.DataFrame,
    transformer_summary: Mapping[str, Any],
    selection_sources: Mapping[str, Any],
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

    generated_features = list(generated_train_fit.columns)
    model_features = [*base_features, *generated_features]
    cat_features = [feature for feature in categorical_features if feature in model_features]

    x_train = _combine_features(train_fit, base_features, generated_train_fit)
    x_val = _combine_features(train_val, base_features, generated_train_val)
    x_cal = _combine_features(calibration, base_features, generated_calibration)
    x_test = _combine_features(test, base_features, generated_test)

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
    calibrator, calibration_report = _select_calibrator(
        method=str(config["calibration"]["method"]),
        candidates=[str(item) for item in config["calibration"]["candidates"]],
        y_cal=calibration[TARGET].astype(int).to_numpy(),
        raw_cal=raw_cal,
    )
    calibrated_test = np.asarray(_apply_calibrator(calibrator, raw_test), dtype=float)
    calibrated_cal = np.asarray(_apply_calibrator(calibrator, raw_cal), dtype=float)
    test_metrics = classification_metrics(test[TARGET].astype(int).to_numpy(), calibrated_test)
    cal_metrics = classification_metrics(
        calibration[TARGET].astype(int).to_numpy(),
        calibrated_cal,
    )
    fairness = _build_fairness_report(test, y_prob=calibrated_test, config=config)

    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "pd_selected_tabprep_challenger.cbm"
    calibrator_path = model_dir / "pd_selected_tabprep_calibrator.pkl"
    prediction_path = data_dir / "test_predictions.parquet"
    status_path = model_dir / "selected_feature_training_status.json"
    model.save_model(str(model_path))
    atomic_write_pickle(calibrator_path, calibrator)
    predictions = _prediction_frame(
        test,
        raw_prob=raw_test,
        calibrated_prob=calibrated_test,
        case_name=case_name,
        seed=seed,
    )
    atomic_write_parquet(predictions, prediction_path)
    if not fairness.empty:
        atomic_write_parquet(fairness, report_dir / "fairness_report.parquet")
    feature_importance = _feature_importance_frame(model)
    atomic_write_parquet(feature_importance, report_dir / "feature_importance.parquet")
    status = {
        "run_tag": run_tag,
        "case_name": case_name,
        "seed": seed,
        "tabprep_seed": tabprep_seed,
        "model_path": str(model_path),
        "calibrator_path": str(calibrator_path),
        "prediction_path": str(prediction_path),
        "n_base_features": len(base_features),
        "n_generated_features": len(generated_features),
        "n_model_features": len(model_features),
        "categorical_features": cat_features,
        "generated_features": generated_features,
        "training_metrics": train_metrics,
        "test_metrics": test_metrics,
        "calibration_metrics": cal_metrics,
        "calibration_selection": calibration_report,
        "selection_sources": selection_sources,
        "transformer_summary": transformer_summary,
    }
    atomic_write_json(status_path, status)
    logger.info(
        "{} seed {} done: test AUC={:.6f}, Brier={:.6f}, features={} generated={}",
        case_name,
        seed,
        test_metrics["auc_roc"],
        test_metrics["brier_score"],
        len(model_features),
        len(generated_features),
    )
    return status


def _feature_importance_frame(model: CatBoostClassifier) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": list(model.feature_names_),
            "importance": model.get_feature_importance(type="PredictionValuesChange"),
        }
    ).sort_values("importance", ascending=False, kind="mergesort")


if __name__ == "__main__":
    main()
