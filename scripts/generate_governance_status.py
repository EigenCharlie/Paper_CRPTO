"""Generate governance drift status for MRM gating.

Builds per-feature drift diagnostics (PSI, KS, CvM) and multivariate C2ST,
then emits:
- data/processed/drift_monitoring.parquet
- models/governance_status.json

Usage:
    uv run python scripts/generate_governance_status.py --config configs/mrm_policy.yaml
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostClassifier, Pool
from loguru import logger
from sklearn.metrics import brier_score_loss, roc_auc_score

from scripts.train_pd_model import _apply_training_regime
from src.evaluation.backtesting import (
    classifier_two_sample_test,
    drift_monitoring_report,
    population_stability_index,
)
from src.evaluation.explainability import dominant_reason_match_rate, rank_overlap_ratio
from src.evaluation.model_shift import interpret_model_shift
from src.models.pd_contract import load_contract, resolve_calibrator_path, resolve_model_path
from src.utils.artifact_metadata import build_artifact_metadata, resolve_run_tag
from src.utils.baseline_registry import resolve_official_baseline_run_tag
from src.utils.io_utils import load_pickle_compat, read_split_with_fe_fallback
from src.utils.threshold_semantics import load_threshold_semantics, resolve_operational_threshold

SCHEMA_VERSION = "2026-03-06.1"


@dataclass(frozen=True)
class GovernanceThresholds:
    psi_threshold: float
    ks_pvalue_min: float
    cvm_pvalue_min: float
    c2st_auc_max: float
    max_feature_breach_ratio: float
    c2st_max_rows: int
    score_psi_max: float
    auc_delta_max: float
    brier_increase_max: float
    calibration_gap_delta_max: float
    performance_max_rows: int
    min_rank_overlap_top10: float
    max_explanation_shap_psi: float
    min_reason_code_stability: float
    explanation_min_rows_per_slice: int
    psi_bins: int
    random_state: int


@dataclass(frozen=True)
class GovernanceOutputPaths:
    drift_path: Path
    status_path: Path
    explanation_drift_path: Path
    fairness_status_path: Path
    fairness_frontier_path: Path
    challenger_report_path: Path
    model_shift_status_path: Path


def _load_cfg(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_feature_contract() -> list[str]:
    contract_path = Path("models/pd_model_contract.json")
    if not contract_path.exists():
        return []
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    features = contract.get("feature_names", [])
    if not isinstance(features, list):
        return []
    return [str(f) for f in features]


def _load_training_record() -> dict[str, Any]:
    path = Path("models/pd_training_record.pkl")
    if not path.exists():
        return {}
    try:
        payload = load_pickle_compat(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sample_frame(df: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df.copy()
    return df.sample(n=max_rows, random_state=random_state).copy()


def _load_calibrator() -> Any | None:
    path = resolve_calibrator_path()
    if path is None or not path.exists():
        return None
    try:
        return load_pickle_compat(path)
    except Exception:
        return None


def _apply_calibrator(calibrator: Any | None, y_prob_raw: np.ndarray) -> np.ndarray:
    if calibrator is None:
        return y_prob_raw.astype(float)
    if hasattr(calibrator, "predict_proba"):
        calibrated = calibrator.predict_proba(y_prob_raw.reshape(-1, 1))
        if calibrated.ndim == 2 and calibrated.shape[1] >= 2:
            return calibrated[:, 1].astype(float)
    if hasattr(calibrator, "predict"):
        calibrated = calibrator.predict(y_prob_raw)
        return np.asarray(calibrated, dtype=float)
    return y_prob_raw.astype(float)


def _prepare_model_frame(
    df: pd.DataFrame,
    *,
    features: list[str],
    categorical_features: list[str],
) -> pd.DataFrame:
    X = df.reindex(columns=features).copy()
    inferred_cat = [
        col
        for col in X.columns
        if col in categorical_features or not pd.api.types.is_numeric_dtype(X[col])
    ]
    for col in inferred_cat:
        if col in X.columns:
            X[col] = X[col].astype(str).fillna("missing")
    return X


def _score_and_performance_report(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    random_state: int,
    max_rows_per_split: int,
    psi_bins: int,
) -> dict[str, float]:
    contract = load_contract()
    if not contract:
        return {}

    feature_names = [str(f) for f in contract.get("feature_names", [])]
    categorical_features = [str(f) for f in contract.get("categorical_features", [])]
    if not feature_names:
        return {}

    model = CatBoostClassifier()
    model.load_model(resolve_model_path().as_posix())
    calibrator = _load_calibrator()

    train_eval = _sample_frame(train_df, max_rows=max_rows_per_split, random_state=random_state)
    test_eval = _sample_frame(test_df, max_rows=max_rows_per_split, random_state=random_state)

    X_train = _prepare_model_frame(
        train_eval,
        features=feature_names,
        categorical_features=categorical_features,
    )
    X_test = _prepare_model_frame(
        test_eval,
        features=feature_names,
        categorical_features=categorical_features,
    )
    y_train = (
        pd.to_numeric(train_eval["default_flag"], errors="coerce").fillna(0).astype(int).to_numpy()
    )
    y_test = (
        pd.to_numeric(test_eval["default_flag"], errors="coerce").fillna(0).astype(int).to_numpy()
    )

    cat_cols = [
        col
        for col in X_train.columns
        if col in categorical_features or not pd.api.types.is_numeric_dtype(X_train[col])
    ]
    train_pool = Pool(X_train, cat_features=cat_cols)
    test_pool = Pool(X_test, cat_features=cat_cols)

    train_raw = model.predict_proba(train_pool)[:, 1]
    test_raw = model.predict_proba(test_pool)[:, 1]
    train_score = _apply_calibrator(calibrator, train_raw)
    test_score = _apply_calibrator(calibrator, test_raw)

    train_auc = float(roc_auc_score(y_train, train_score))
    test_auc = float(roc_auc_score(y_test, test_score))
    train_brier = float(brier_score_loss(y_train, train_score))
    test_brier = float(brier_score_loss(y_test, test_score))
    train_cal_gap = float(abs(float(np.mean(train_score)) - float(np.mean(y_train))))
    test_cal_gap = float(abs(float(np.mean(test_score)) - float(np.mean(y_test))))
    score_psi = float(
        population_stability_index(
            np.asarray(train_score, dtype=float),
            np.asarray(test_score, dtype=float),
            n_bins=psi_bins,
        )
    )
    return {
        "score_psi": score_psi,
        "auc_train_reference": train_auc,
        "auc_test_oot": test_auc,
        "auc_delta_train_to_test": float(max(train_auc - test_auc, 0.0)),
        "brier_train_reference": train_brier,
        "brier_test_oot": test_brier,
        "brier_increase_train_to_test": float(max(test_brier - train_brier, 0.0)),
        "calibration_gap_train_reference": train_cal_gap,
        "calibration_gap_test_oot": test_cal_gap,
        "calibration_gap_delta": float(max(test_cal_gap - train_cal_gap, 0.0)),
        "train_eval_rows": len(train_eval),
        "test_eval_rows": len(test_eval),
    }


def _resolve_numeric_features(train_df: pd.DataFrame, test_df: pd.DataFrame) -> list[str]:
    contract_features = _load_feature_contract()
    common = [f for f in contract_features if f in train_df.columns and f in test_df.columns]

    numeric = []
    for f in common:
        if pd.api.types.is_numeric_dtype(train_df[f]) or pd.api.types.is_numeric_dtype(test_df[f]):
            numeric.append(f)

    if numeric:
        return numeric

    # Fallback: numeric intersection from both frames.
    train_num = set(train_df.select_dtypes(include=["number"]).columns)
    test_num = set(test_df.select_dtypes(include=["number"]).columns)
    fallback = sorted(train_num.intersection(test_num))
    return [c for c in fallback if c != "default_flag"][:80]


def _safe_mean(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    return float(series.mean())


def _safe_float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


def _resolve_primary_threshold() -> float:
    semantics = load_threshold_semantics()
    if semantics:
        return resolve_operational_threshold(semantics, default=0.5)
    fairness_status_path = Path("models/fairness_audit_status.json")
    if fairness_status_path.exists():
        try:
            payload = json.loads(fairness_status_path.read_text(encoding="utf-8"))
            return float(payload.get("primary_threshold", payload.get("prediction_threshold", 0.5)))
        except Exception:
            pass
    decision_threshold_path = Path("models/decision_threshold.json")
    if decision_threshold_path.exists():
        try:
            payload = json.loads(decision_threshold_path.read_text(encoding="utf-8"))
            return float(payload.get("selected_threshold", 0.5))
        except Exception:
            pass
    return 0.5


def _explanation_feature_columns(shap_raw: pd.DataFrame) -> list[str]:
    return [c.replace("shap_", "") for c in shap_raw.columns if c.startswith("shap_")]


def _recent_comparison_periods(
    shap_raw: pd.DataFrame,
    periods: list[str],
    *,
    min_rows_per_slice: int,
) -> tuple[list[str], pd.DataFrame] | None:
    comparison_periods: list[str] = []
    for period in reversed(periods):
        comparison_periods.insert(0, period)
        comparison_df = shap_raw.loc[
            shap_raw["issue_quarter"].astype(str).isin(comparison_periods)
        ].copy()
        if len(comparison_df) >= min_rows_per_slice:
            return comparison_periods, comparison_df
    return None


def _explanation_segment_pairs(
    shap_raw: pd.DataFrame,
    reference_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    *,
    min_rows_per_slice: int,
) -> list[tuple[str, str, pd.DataFrame, pd.DataFrame]]:
    segment_pairs: list[tuple[str, str, pd.DataFrame, pd.DataFrame]] = [
        ("overall", "all", reference_df, comparison_df)
    ]
    if "grade" not in shap_raw.columns:
        return segment_pairs
    for grade in sorted(shap_raw["grade"].dropna().astype(str).unique().tolist()):
        ref_seg = reference_df.loc[reference_df["grade"].astype(str) == grade].copy()
        cmp_seg = comparison_df.loc[comparison_df["grade"].astype(str) == grade].copy()
        if len(ref_seg) < min_rows_per_slice or len(cmp_seg) < min_rows_per_slice:
            continue
        segment_pairs.append(("grade", grade, ref_seg, cmp_seg))
    return segment_pairs


def _rank_shap_features(segment: pd.DataFrame, feature_cols: list[str]) -> list[str]:
    return sorted(
        feature_cols,
        key=lambda feature: segment[f"shap_{feature}"].abs().mean(),
        reverse=True,
    )


def _shap_psi_details(
    ref_seg: pd.DataFrame,
    cmp_seg: pd.DataFrame,
    *,
    focus_features: list[str],
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for feature in focus_features:
        col = f"shap_{feature}"
        if col not in ref_seg.columns or col not in cmp_seg.columns:
            continue
        psi = population_stability_index(
            pd.to_numeric(ref_seg[col], errors="coerce").dropna().to_numpy(dtype=float),
            pd.to_numeric(cmp_seg[col], errors="coerce").dropna().to_numpy(dtype=float),
            n_bins=8,
        )
        rows.append({"feature": feature, "psi": float(psi)})
    return rows


def _explanation_drift_row(
    *,
    segment_type: str,
    segment: str,
    ref_seg: pd.DataFrame,
    cmp_seg: pd.DataFrame,
    feature_cols: list[str],
    periods: list[str],
    comparison_periods: list[str],
    comparison_period_label: str,
    primary_threshold: float,
    min_rank_overlap_top10: float,
    max_shap_psi: float,
    min_reason_code_stability: float,
    min_rows_per_slice: int,
    pd_col: str,
) -> dict[str, Any]:
    ref_ranking = _rank_shap_features(ref_seg, feature_cols)
    cmp_ranking = _rank_shap_features(cmp_seg, feature_cols)
    overlap = rank_overlap_ratio(ref_ranking, cmp_ranking, top_k=10)
    focus_features = list(dict.fromkeys(ref_ranking[:5] + cmp_ranking[:5]))[:5]
    shap_psis = _shap_psi_details(ref_seg, cmp_seg, focus_features=focus_features)
    max_feature_psi = max((float(row["psi"]) for row in shap_psis), default=0.0)
    avg_feature_psi = float(np.mean([float(row["psi"]) for row in shap_psis])) if shap_psis else 0.0
    reason_match_rate, reason_details = dominant_reason_match_rate(
        ref_seg,
        cmp_seg,
        ref_ranking[:10],
        pd_col=pd_col,
        threshold=primary_threshold,
        min_rows_per_band=max(15, int(min_rows_per_slice / 4)),
    )
    pass_rank = bool(overlap >= min_rank_overlap_top10)
    pass_dist = bool(max_feature_psi <= max_shap_psi)
    pass_reason = bool(reason_match_rate >= min_reason_code_stability)
    return {
        "segment_type": segment_type,
        "segment": segment,
        "reference_period": "|".join([p for p in periods if p not in comparison_periods]),
        "comparison_period": comparison_period_label,
        "reference_n": len(ref_seg),
        "comparison_n": len(cmp_seg),
        "rank_overlap_top10": float(overlap),
        "avg_shap_psi_top5": float(avg_feature_psi),
        "max_shap_psi_top5": float(max_feature_psi),
        "reason_code_match_rate": float(reason_match_rate),
        "pass_rank_overlap": pass_rank,
        "pass_distribution_shift": pass_dist,
        "pass_reason_code_stability": pass_reason,
        "passed_all": bool(pass_rank and pass_dist and pass_reason),
        "feature_psi_details": json.dumps(shap_psis, default=str),
        "reason_code_details": json.dumps(reason_details, default=str),
    }


def _build_explanation_drift_report(
    shap_raw: pd.DataFrame,
    *,
    primary_threshold: float,
    min_rank_overlap_top10: float,
    max_shap_psi: float,
    min_reason_code_stability: float,
    min_rows_per_slice: int,
) -> pd.DataFrame:
    feature_cols = _explanation_feature_columns(shap_raw)
    if shap_raw.empty or not feature_cols or "issue_quarter" not in shap_raw.columns:
        return pd.DataFrame()

    periods = sorted(
        [
            p
            for p in shap_raw["issue_quarter"].astype(str).dropna().unique().tolist()
            if p != "unknown"
        ]
    )
    if len(periods) < 2:
        return pd.DataFrame()

    comparison_slice = _recent_comparison_periods(
        shap_raw,
        periods,
        min_rows_per_slice=min_rows_per_slice,
    )
    if comparison_slice is None:
        return pd.DataFrame()
    comparison_periods, comparison_df = comparison_slice

    reference_df = shap_raw.loc[
        ~shap_raw["issue_quarter"].astype(str).isin(comparison_periods)
    ].copy()
    if len(reference_df) < min_rows_per_slice or len(comparison_df) < min_rows_per_slice:
        return pd.DataFrame()
    comparison_period_label = "|".join(comparison_periods)

    segment_pairs = _explanation_segment_pairs(
        shap_raw,
        reference_df,
        comparison_df,
        min_rows_per_slice=min_rows_per_slice,
    )
    pd_col = "pd_calibrated" if "pd_calibrated" in shap_raw.columns else "score_raw"
    rows: list[dict[str, Any]] = []
    for segment_type, segment, ref_seg, cmp_seg in segment_pairs:
        rows.append(
            _explanation_drift_row(
                segment_type=segment_type,
                segment=segment,
                ref_seg=ref_seg,
                cmp_seg=cmp_seg,
                feature_cols=feature_cols,
                periods=periods,
                comparison_periods=comparison_periods,
                comparison_period_label=comparison_period_label,
                primary_threshold=primary_threshold,
                min_rank_overlap_top10=min_rank_overlap_top10,
                max_shap_psi=max_shap_psi,
                min_reason_code_stability=min_reason_code_stability,
                min_rows_per_slice=min_rows_per_slice,
                pd_col=pd_col,
            )
        )
    return pd.DataFrame(rows)


def _resolve_thresholds(
    triggers: dict[str, Any],
    checks: dict[str, Any],
) -> GovernanceThresholds:
    return GovernanceThresholds(
        psi_threshold=float(triggers.get("psi_threshold", 0.25)),
        ks_pvalue_min=float(checks.get("ks_pvalue_min", 0.01)),
        cvm_pvalue_min=float(checks.get("cvm_pvalue_min", 0.01)),
        c2st_auc_max=float(checks.get("c2st_auc_max", 0.60)),
        max_feature_breach_ratio=float(checks.get("max_feature_breach_ratio", 0.15)),
        c2st_max_rows=int(checks.get("c2st_max_rows_per_split", 50_000)),
        score_psi_max=float(checks.get("score_psi_max", 0.15)),
        auc_delta_max=float(checks.get("auc_delta_max", 0.05)),
        brier_increase_max=float(checks.get("brier_increase_max", 0.02)),
        calibration_gap_delta_max=float(checks.get("calibration_gap_delta_max", 0.02)),
        performance_max_rows=int(checks.get("performance_max_rows_per_split", 100_000)),
        min_rank_overlap_top10=float(checks.get("explanation_rank_overlap_top10_min", 0.60)),
        max_explanation_shap_psi=float(checks.get("explanation_shap_psi_max", 0.25)),
        min_reason_code_stability=float(checks.get("reason_code_stability_min", 0.55)),
        explanation_min_rows_per_slice=int(checks.get("explanation_min_rows_per_slice", 80)),
        psi_bins=int(checks.get("psi_bins", 10)),
        random_state=int(checks.get("random_state", 42)),
    )


def _output_path(outputs: dict[str, Any], key: str, default: str) -> Path:
    value = outputs.get(key, default)
    return Path(str(default if value is None else value))


def _resolve_output_paths(outputs: dict[str, Any]) -> GovernanceOutputPaths:
    return GovernanceOutputPaths(
        drift_path=_output_path(
            outputs,
            "drift_monitoring_path",
            "data/processed/drift_monitoring.parquet",
        ),
        status_path=_output_path(
            outputs,
            "governance_status_path",
            "models/governance_status.json",
        ),
        explanation_drift_path=_output_path(
            outputs,
            "explanation_drift_path",
            "data/processed/explanation_drift.parquet",
        ),
        fairness_status_path=_output_path(
            outputs,
            "fairness_status_path",
            "models/fairness_audit_status.json",
        ),
        fairness_frontier_path=_output_path(
            outputs,
            "fairness_frontier_path",
            "data/processed/fairness_threshold_frontier.parquet",
        ),
        challenger_report_path=_output_path(
            outputs,
            "challenger_promotion_report_path",
            "models/challenger_promotion_report.json",
        ),
        model_shift_status_path=_output_path(
            outputs,
            "model_shift_status_path",
            "models/model_shift_status.json",
        ),
    )


def _load_governance_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df = read_split_with_fe_fallback("data/processed/train_fe.parquet")
    test_df = read_split_with_fe_fallback("data/processed/test_fe.parquet")
    training_record = _load_training_record()
    regime_cfg = training_record.get("training_regime", {}) if training_record else {}
    if isinstance(regime_cfg, dict) and regime_cfg:
        train_df, regime_meta = _apply_training_regime(train_df, regime_cfg, date_col="issue_d")
        logger.info(
            "Applied PD training regime to governance reference population: mode={} rows={}",
            regime_meta.get("mode", regime_cfg.get("mode", "standard")),
            len(train_df),
        )
    return train_df, test_df


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_explanation_drift_if_available(thresholds: GovernanceThresholds) -> pd.DataFrame:
    shap_raw_path = Path("data/processed/shap_raw_top20.parquet")
    if not shap_raw_path.exists():
        return pd.DataFrame()
    return _build_explanation_drift_report(
        pd.read_parquet(shap_raw_path),
        primary_threshold=_resolve_primary_threshold(),
        min_rank_overlap_top10=thresholds.min_rank_overlap_top10,
        max_shap_psi=thresholds.max_explanation_shap_psi,
        min_reason_code_stability=thresholds.min_reason_code_stability,
        min_rows_per_slice=thresholds.explanation_min_rows_per_slice,
    )


def _drift_breach_metrics(
    drift_df: pd.DataFrame,
    c2st: dict[str, Any],
    performance_report: dict[str, float],
    thresholds: GovernanceThresholds,
) -> dict[str, Any]:
    n_features = len(drift_df)
    psi_breaches = (
        int((~drift_df.get("pass_psi", pd.Series(dtype=bool))).sum()) if n_features else 0
    )
    ks_breaches = int((~drift_df.get("pass_ks", pd.Series(dtype=bool))).sum()) if n_features else 0
    cvm_breaches = (
        int((~drift_df.get("pass_cvm", pd.Series(dtype=bool))).sum()) if n_features else 0
    )
    feature_breach_ratio = float(psi_breaches / max(n_features, 1))
    distribution_warning_ratio = float((ks_breaches + cvm_breaches) / max(n_features * 2, 1))
    score_psi = float(performance_report.get("score_psi", 0.0))
    auc_delta = float(performance_report.get("auc_delta_train_to_test", 0.0))
    brier_increase = float(performance_report.get("brier_increase_train_to_test", 0.0))
    calibration_gap_delta = float(performance_report.get("calibration_gap_delta", 0.0))
    pass_psi = bool(
        (float(drift_df["psi"].max()) if n_features else 0.0) <= thresholds.psi_threshold
    )
    pass_breach_ratio = bool(feature_breach_ratio <= thresholds.max_feature_breach_ratio)
    pass_score_psi = bool(score_psi <= thresholds.score_psi_max)
    pass_auc_delta = bool(auc_delta <= thresholds.auc_delta_max)
    pass_brier_increase = bool(brier_increase <= thresholds.brier_increase_max)
    pass_calibration_gap_delta = bool(calibration_gap_delta <= thresholds.calibration_gap_delta_max)
    return {
        "n_features": n_features,
        "psi_breaches": psi_breaches,
        "ks_breaches": ks_breaches,
        "cvm_breaches": cvm_breaches,
        "feature_breach_ratio": feature_breach_ratio,
        "distribution_warning_ratio": distribution_warning_ratio,
        "max_psi": float(drift_df["psi"].max()) if n_features else 0.0,
        "mean_psi": _safe_mean(drift_df["psi"]) if n_features else 0.0,
        "min_ks_pvalue": float(drift_df["ks_pvalue"].min()) if n_features else 1.0,
        "min_cvm_pvalue": float(drift_df["cvm_pvalue"].min()) if n_features else 1.0,
        "c2st_auc": _safe_float_value(c2st["c2st_auc"]),
        "c2st_materiality": str(c2st.get("materiality", "none")),
        "c2st_effective_driver_count": _safe_int_value(c2st.get("effective_driver_count", 0)),
        "c2st_top_drivers": _safe_list_value(c2st.get("top_drivers", [])),
        "c2st_rows_used": _safe_int_value(c2st.get("n_rows", 0)),
        "score_psi": score_psi,
        "auc_delta": auc_delta,
        "brier_increase": brier_increase,
        "calibration_gap_delta": calibration_gap_delta,
        "pass_psi": pass_psi,
        "pass_breach_ratio": pass_breach_ratio,
        "pass_score_psi": pass_score_psi,
        "pass_auc_delta": pass_auc_delta,
        "pass_brier_increase": pass_brier_increase,
        "pass_calibration_gap_delta": pass_calibration_gap_delta,
        "pass_predictive_drift": bool(
            pass_psi
            and pass_breach_ratio
            and pass_score_psi
            and pass_auc_delta
            and pass_brier_increase
            and pass_calibration_gap_delta
        ),
        "pass_c2st": bool(_safe_float_value(c2st["c2st_auc"]) <= thresholds.c2st_auc_max),
        "performance_report": performance_report,
    }


def _interpret_governance_shift(
    metrics: dict[str, Any],
    thresholds: GovernanceThresholds,
) -> dict[str, Any]:
    return interpret_model_shift(
        c2st_auc=float(metrics["c2st_auc"]),
        c2st_materiality=str(metrics["c2st_materiality"]),
        score_psi=float(metrics["score_psi"]),
        auc_delta=float(metrics["auc_delta"]),
        brier_increase=float(metrics["brier_increase"]),
        calibration_gap_delta=float(metrics["calibration_gap_delta"]),
        distribution_warning_ratio=float(metrics["distribution_warning_ratio"]),
        score_psi_max=thresholds.score_psi_max,
        auc_delta_max=thresholds.auc_delta_max,
        brier_increase_max=thresholds.brier_increase_max,
        calibration_gap_delta_max=thresholds.calibration_gap_delta_max,
    )


def _explanation_passes(explanation_drift: pd.DataFrame) -> dict[str, bool]:
    explainability_pass = bool(
        (not explanation_drift.empty) and explanation_drift["passed_all"].astype(bool).all()
    )
    reason_code_stability_pass = bool(
        (not explanation_drift.empty)
        and explanation_drift["pass_reason_code_stability"].astype(bool).all()
    )
    return {
        "explainability_pass": explainability_pass,
        "reason_code_stability_pass": reason_code_stability_pass,
    }


def _series_min_or_zero(df: pd.DataFrame, column: str) -> float:
    return float(df[column].min()) if not df.empty else 0.0


def _series_max_or_zero(df: pd.DataFrame, column: str) -> float:
    return float(df[column].max()) if not df.empty else 0.0


def _top_explanation_breaches(explanation_drift: pd.DataFrame) -> list[dict[str, Any]]:
    if explanation_drift.empty:
        return []
    return (
        explanation_drift.sort_values(
            ["passed_all", "max_shap_psi_top5", "rank_overlap_top10"],
            ascending=[True, False, True],
        )
        .head(10)
        .to_dict(orient="records")
    )


def _fairness_primary_threshold(fairness_status: dict[str, Any]) -> float:
    if not fairness_status:
        return 0.5
    return _safe_float_value(
        fairness_status.get("primary_threshold", fairness_status.get("prediction_threshold", 0.5))
    )


def _warning_flags(
    metrics: dict[str, Any],
    explanation_checks: dict[str, bool],
) -> dict[str, bool]:
    return {
        "warn_c2st": bool(not metrics["pass_c2st"]),
        "warn_distribution_tests": bool(metrics["ks_breaches"] > 0 or metrics["cvm_breaches"] > 0),
        "warn_explainability": bool(not explanation_checks["explainability_pass"]),
        "warn_reason_code_stability": bool(not explanation_checks["reason_code_stability_pass"]),
    }


def _build_governance_status(
    *,
    config_path: str,
    resolved_run_tag: str,
    paths: GovernanceOutputPaths,
    thresholds: GovernanceThresholds,
    drift_df: pd.DataFrame,
    explanation_drift: pd.DataFrame,
    fairness_status: dict[str, Any],
    challenger_report: dict[str, Any],
    metrics: dict[str, Any],
    model_shift: dict[str, Any],
) -> dict[str, Any]:
    fairness_pass = bool(fairness_status.get("overall_pass", False))
    challenger_promotable = bool(challenger_report.get("challenger_promotable", False))
    explanation_checks = _explanation_passes(explanation_drift)
    warning_flags = _warning_flags(metrics, explanation_checks)
    overall_pass = bool(metrics["pass_predictive_drift"] and fairness_pass)
    top_breaches = drift_df.head(10).to_dict(orient="records") if int(metrics["n_features"]) else []
    primary_threshold = _fairness_primary_threshold(fairness_status)

    return {
        "overall_pass": overall_pass,
        "checks": {
            "pass_psi": bool(metrics["pass_psi"]),
            "pass_breach_ratio": bool(metrics["pass_breach_ratio"]),
            "pass_score_psi": bool(metrics["pass_score_psi"]),
            "pass_auc_delta": bool(metrics["pass_auc_delta"]),
            "pass_brier_increase": bool(metrics["pass_brier_increase"]),
            "pass_calibration_gap_delta": bool(metrics["pass_calibration_gap_delta"]),
            "pass_predictive_drift": bool(metrics["pass_predictive_drift"]),
            "pass_fairness": fairness_pass,
            "pass_c2st": bool(metrics["pass_c2st"]),
            "pass_explainability": explanation_checks["explainability_pass"],
            "pass_reason_code_stability": explanation_checks["reason_code_stability_pass"],
            **warning_flags,
        },
        "thresholds": {
            "psi_threshold": thresholds.psi_threshold,
            "ks_pvalue_min": thresholds.ks_pvalue_min,
            "cvm_pvalue_min": thresholds.cvm_pvalue_min,
            "c2st_auc_max": thresholds.c2st_auc_max,
            "max_feature_breach_ratio": thresholds.max_feature_breach_ratio,
            "score_psi_max": thresholds.score_psi_max,
            "auc_delta_max": thresholds.auc_delta_max,
            "brier_increase_max": thresholds.brier_increase_max,
            "calibration_gap_delta_max": thresholds.calibration_gap_delta_max,
            "explanation_rank_overlap_top10_min": thresholds.min_rank_overlap_top10,
            "explanation_shap_psi_max": thresholds.max_explanation_shap_psi,
            "reason_code_stability_min": thresholds.min_reason_code_stability,
        },
        "summary": {
            "n_features": int(metrics["n_features"]),
            "max_psi": float(metrics["max_psi"]),
            "mean_psi": float(metrics["mean_psi"]),
            "min_ks_pvalue": float(metrics["min_ks_pvalue"]),
            "min_cvm_pvalue": float(metrics["min_cvm_pvalue"]),
            "c2st_auc": float(metrics["c2st_auc"]),
            "psi_breaches": int(metrics["psi_breaches"]),
            "ks_breaches": int(metrics["ks_breaches"]),
            "cvm_breaches": int(metrics["cvm_breaches"]),
            "feature_breach_ratio": float(metrics["feature_breach_ratio"]),
            "distribution_warning_ratio": float(metrics["distribution_warning_ratio"]),
            "c2st_rows_used": int(metrics["c2st_rows_used"]),
            "c2st_materiality": str(metrics["c2st_materiality"]),
            "c2st_effective_driver_count": int(metrics["c2st_effective_driver_count"]),
            **metrics["performance_report"],
            "n_explanation_segments": len(explanation_drift),
            "min_rank_overlap_top10": _series_min_or_zero(explanation_drift, "rank_overlap_top10"),
            "max_explanation_shap_psi": _series_max_or_zero(explanation_drift, "max_shap_psi_top5"),
            "min_reason_code_stability": _series_min_or_zero(
                explanation_drift, "reason_code_match_rate"
            ),
            "fairness_overall_pass": fairness_pass,
            "fairness_primary_threshold": primary_threshold,
            "challenger_promotable": challenger_promotable,
            "model_shift_type": str(model_shift["shift_type"]),
            "governance_posture": str(model_shift["governance_posture"]),
        },
        "warnings": warning_flags,
        "c2st": {
            "auc": float(metrics["c2st_auc"]),
            "materiality": str(metrics["c2st_materiality"]),
            "effective_driver_count": int(metrics["c2st_effective_driver_count"]),
            "top_drivers": metrics["c2st_top_drivers"],
        },
        "model_shift": model_shift,
        "artifacts": {
            "drift_monitoring_path": str(paths.drift_path),
            "explanation_drift_path": str(paths.explanation_drift_path),
            "fairness_status_path": str(paths.fairness_status_path),
            "fairness_frontier_path": str(paths.fairness_frontier_path),
            "challenger_promotion_report_path": str(paths.challenger_report_path),
            "model_shift_status_path": str(paths.model_shift_status_path),
        },
        "top_drift_features": top_breaches,
        "top_explanation_breaches": _top_explanation_breaches(explanation_drift),
        "primary_threshold": primary_threshold,
        "explainability_pass": explanation_checks["explainability_pass"],
        "explanation_drift_pass": explanation_checks["explainability_pass"],
        "reason_code_stability_pass": explanation_checks["reason_code_stability_pass"],
        "challenger_promotable": challenger_promotable,
        "policy_config": config_path,
        **build_artifact_metadata(
            schema_version=SCHEMA_VERSION,
            run_tag=resolved_run_tag,
            require_explicit=True,
        ),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_model_shift_status(
    *,
    path: Path,
    status_path: Path,
    model_shift: dict[str, Any],
    resolved_run_tag: str,
) -> None:
    _write_json(
        path,
        {
            "diagnostic_only": True,
            "overall_pass": bool(model_shift["governance_posture"] != "candidate_gate"),
            "summary": model_shift,
            "artifacts": {"governance_status_path": str(status_path)},
            **build_artifact_metadata(
                schema_version=SCHEMA_VERSION,
                run_tag=resolved_run_tag,
                require_explicit=True,
            ),
        },
    )


def _log_governance_outputs(
    *,
    paths: GovernanceOutputPaths,
    status: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    logger.info("Saved drift monitoring: {}", paths.drift_path)
    logger.info("Saved governance status: {}", paths.status_path)
    logger.info("Saved model-shift interpretation: {}", paths.model_shift_status_path)
    logger.info(
        "Governance checks pass={} (max_psi={:.4f}, score_psi={:.4f}, auc_delta={:.4f}, brier_increase={:.4f}, c2st_auc={:.4f})",
        status["overall_pass"],
        metrics["max_psi"],
        metrics["score_psi"],
        metrics["auc_delta"],
        metrics["brier_increase"],
        metrics["c2st_auc"],
    )


def main(config_path: str = "configs/mrm_policy.yaml", run_tag: str | None = None) -> None:
    cfg = _load_cfg(config_path)
    semantics = load_threshold_semantics()
    resolved_run_tag = resolve_run_tag(
        run_tag,
        fallback_candidates=[semantics.get("run_tag"), resolve_official_baseline_run_tag()],
        require_explicit=True,
    )

    triggers = cfg.get("retraining_triggers", {})
    checks = cfg.get("governance_checks", {})
    outputs = cfg.get("governance_output", {})
    thresholds = _resolve_thresholds(triggers, checks)
    paths = _resolve_output_paths(outputs)

    train_df, test_df = _load_governance_frames()

    features = _resolve_numeric_features(train_df, test_df)
    if not features:
        raise ValueError("No numeric features available for governance drift checks.")

    logger.info("Governance drift checks on {} numeric features", len(features))

    drift_df = drift_monitoring_report(
        train_df=train_df,
        test_df=test_df,
        features=features,
        psi_threshold=thresholds.psi_threshold,
        ks_pvalue_threshold=thresholds.ks_pvalue_min,
        cvm_pvalue_threshold=thresholds.cvm_pvalue_min,
        n_bins=thresholds.psi_bins,
    )

    c2st = classifier_two_sample_test(
        train_df=train_df,
        test_df=test_df,
        features=features,
        max_rows_per_split=thresholds.c2st_max_rows,
        random_state=thresholds.random_state,
    )
    performance_report = _score_and_performance_report(
        train_df,
        test_df,
        random_state=thresholds.random_state,
        max_rows_per_split=thresholds.performance_max_rows,
        psi_bins=thresholds.psi_bins,
    )
    metrics = _drift_breach_metrics(drift_df, c2st, performance_report, thresholds)
    model_shift = _interpret_governance_shift(metrics, thresholds)

    _write_parquet(drift_df, paths.drift_path)
    explanation_drift = _build_explanation_drift_if_available(thresholds)
    _write_parquet(explanation_drift, paths.explanation_drift_path)

    fairness_status = _load_json_dict(paths.fairness_status_path)
    challenger_report = _load_json_dict(paths.challenger_report_path)
    status = _build_governance_status(
        config_path=config_path,
        resolved_run_tag=resolved_run_tag,
        paths=paths,
        thresholds=thresholds,
        drift_df=drift_df,
        explanation_drift=explanation_drift,
        fairness_status=fairness_status,
        challenger_report=challenger_report,
        metrics=metrics,
        model_shift=model_shift,
    )
    _write_json(paths.status_path, status)
    _write_model_shift_status(
        path=paths.model_shift_status_path,
        status_path=paths.status_path,
        model_shift=model_shift,
        resolved_run_tag=resolved_run_tag,
    )
    _log_governance_outputs(paths=paths, status=status, metrics=metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate governance drift status")
    parser.add_argument("--config", default="configs/mrm_policy.yaml")
    parser.add_argument("--run-tag", default=None)
    args = parser.parse_args()
    main(config_path=args.config, run_tag=args.run_tag)
