"""Run fairness audit across multiple protected attributes.

Computes demographic parity, equalized odds, and disparate impact
for each attribute defined in the fairness policy config.
Supports policy `outcome_mode`:
- `default`: fairness over predicted default events.
- `approval`: fairness over favorable credit decision (approved loans).

Usage:
    uv run python scripts/run_fairness_audit.py
    uv run python scripts/run_fairness_audit.py --config configs/fairness_policy.yaml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    equalized_odds_difference,
    selection_rate,
)
from loguru import logger
from sklearn.metrics import accuracy_score

from src.evaluation.fairness import (
    build_intersectional_groups,
    fairness_report_from_binary,
    fairness_threshold_frontier,
)
from src.utils.artifact_metadata import build_artifact_metadata, resolve_run_tag
from src.utils.threshold_semantics import write_threshold_semantics

SCHEMA_VERSION = "2026-03-06.1"
SHAP_STATUS_PATH = Path("models/shap_fairness_status.json")
SHAP_SAMPLE_SIZE = 10_000


def _as_float(value: Any) -> float:
    """Convert scalar config/data values to float with a narrow error surface."""
    return float(value)


def _load_config(config_path: str) -> dict:
    """Load fairness policy YAML config."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def _build_groups_dict(
    df: pd.DataFrame,
    attributes: list[dict],
) -> dict[str, np.ndarray]:
    """Build groups dict from config attribute definitions."""
    groups_dict: dict[str, np.ndarray] = {}

    for attr in attributes:
        name = attr["name"]
        col = attr["column"]

        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in data, skipping attribute '{name}'")
            continue

        if attr.get("binning") == "quartile":
            groups_dict[name] = (
                pd.qcut(df[col], q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
                .astype(str)
                .values
            )
        else:
            groups_dict[name] = df[col].astype(str).values

    return groups_dict


def _resolve_prediction_threshold(cfg: dict, policy: dict) -> tuple[float, str]:
    """Resolve prediction threshold from artifact when configured."""
    fallback_threshold = float(policy.get("prediction_threshold", 0.5))
    threshold_cfg = cfg.get("threshold_policy", {}) or {}
    if not bool(threshold_cfg.get("use_artifact", True)):
        return fallback_threshold, "policy_default"

    artifact_path = Path(threshold_cfg.get("artifact_path", "models/decision_threshold.json"))
    if not artifact_path.exists():
        return fallback_threshold, "policy_default_missing_artifact"

    key = str(threshold_cfg.get("selected_threshold_key", "selected_threshold"))
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        resolved = float(payload.get(key, fallback_threshold))
        return resolved, "artifact"
    except Exception:
        return fallback_threshold, "policy_default_artifact_error"


def _resolve_outcome_mode(policy: dict) -> str:
    raw = str(policy.get("outcome_mode", "default")).strip().lower()
    if raw in {"approval", "approve", "good", "non_default"}:
        return "approval"
    return "default"


def _resolve_frontier_thresholds(primary_threshold: float, cfg: dict) -> list[float]:
    frontier_cfg = cfg.get("threshold_frontier", {}) or {}
    if not bool(frontier_cfg.get("enabled", True)):
        return [float(primary_threshold)]

    explicit = frontier_cfg.get("thresholds", []) or []
    if explicit:
        values = [float(x) for x in explicit]
    else:
        radius = float(frontier_cfg.get("window_radius", 0.10))
        step = float(frontier_cfg.get("step", 0.05))
        low = max(0.01, float(primary_threshold) - radius)
        high = min(0.99, float(primary_threshold) + radius)
        values = np.arange(low, high + step * 0.5, step).tolist()
        values.append(float(primary_threshold))
    clipped = [min(max(float(x), 0.01), 0.99) for x in values]
    return sorted({round(x, 4) for x in clipped})


def _decision_policy_cfg(cfg: dict) -> dict:
    return cfg.get("decision_policy", {}) or {}


def _select_threshold_from_frontier(
    frontier: pd.DataFrame,
    *,
    y_pred_proba_eval: np.ndarray,
) -> dict[str, float | int]:
    if frontier.empty:
        return {
            "selected_threshold": 0.5,
            "n_passed": 0,
            "worst_eo_gap": 1.0,
            "approval_rate": 0.0,
        }

    rows: list[dict[str, float | int]] = []
    for threshold, grp in frontier.groupby("threshold", observed=True):
        threshold_value = _as_float(threshold)
        rows.append(
            {
                "threshold": threshold_value,
                "n_passed": int(grp["passed_all"].sum()),
                "worst_eo_gap": float(grp["eo_gap"].max()),
                "approval_rate": float(
                    (np.asarray(y_pred_proba_eval, dtype=float) >= threshold_value).mean()
                ),
            }
        )

    ranking = pd.DataFrame(rows).sort_values(
        ["n_passed", "worst_eo_gap", "approval_rate"],
        ascending=[False, True, False],
    )
    selected = ranking.iloc[0].to_dict()
    selected["selected_threshold"] = float(selected["threshold"])
    return selected


def _load_decision_policy_artifact(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _apply_decision_policy(
    *,
    y_pred_proba: np.ndarray,
    groups_all: dict[str, np.ndarray],
    decision_policy: dict,
    default_threshold: float,
) -> np.ndarray:
    y_pred_proba = np.asarray(y_pred_proba, dtype=float)
    thresholds = np.full(len(y_pred_proba), float(default_threshold), dtype=float)
    overrides = decision_policy.get("overrides", []) if isinstance(decision_policy, dict) else []
    if not isinstance(overrides, list):
        overrides = []

    for override in overrides:
        if not isinstance(override, dict):
            continue
        attribute = str(override.get("attribute", "")).strip()
        group = str(override.get("group", "")).strip()
        threshold = float(override.get("threshold", default_threshold))
        labels = groups_all.get(attribute)
        if labels is None:
            continue
        mask = pd.Series(labels).astype(str).eq(group).to_numpy()
        thresholds[mask] = threshold

    return (y_pred_proba >= thresholds).astype(float)


def _model_feature_names(model: Any) -> list[str]:
    return list(getattr(model, "feature_names_", None) or [])


def _available_features(feature_names: list[str], data: pd.DataFrame) -> list[str]:
    return [feature for feature in feature_names if feature in data.columns]


def _sample_shap_frame(
    frame: pd.DataFrame,
    *,
    shap_sample_size: int,
    random_state: int,
) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(random_state)
    n_rows = len(frame)
    if n_rows > shap_sample_size:
        sample_idx = np.sort(rng.choice(n_rows, size=shap_sample_size, replace=False))
    else:
        sample_idx = np.arange(n_rows)
    return frame.iloc[sample_idx].reset_index(drop=True), sample_idx


def _cat_features_from_model(model: Any, frame: pd.DataFrame) -> list[str]:
    try:
        feature_names = _model_feature_names(model)
        cat_idx = model.get_cat_feature_indices()
        return [
            feature_names[idx]
            for idx in cat_idx
            if idx < len(feature_names) and feature_names[idx] in frame.columns
        ]
    except Exception:
        return []


def _text_categorical_columns(frame: pd.DataFrame, known_cats: set[str]) -> list[str]:
    detected: list[str] = []
    for col in frame.columns:
        if col in known_cats or pd.api.types.is_numeric_dtype(frame[col]):
            continue
        probe = frame[col].dropna().head(5)
        if probe.empty:
            continue
        try:
            pd.to_numeric(probe, errors="raise")
        except (ValueError, TypeError):
            detected.append(str(col))
            known_cats.add(str(col))
    return detected


def _catboost_cat_feature_names(model: Any, frame: pd.DataFrame) -> list[str]:
    cat_names = _cat_features_from_model(model, frame)
    cat_set = set(cat_names)
    cat_names.extend(_text_categorical_columns(frame, cat_set))
    return cat_names


def _prepare_catboost_shap_frame(frame: pd.DataFrame, cat_feature_names: list[str]) -> pd.DataFrame:
    out = frame.copy()
    cat_set = set(cat_feature_names)
    for col in list(out.columns):
        if not out[col].isna().any():
            continue
        if col in cat_set:
            out[col] = out[col].astype(object).fillna("missing").astype(str)
        elif pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].fillna(0.0)
    return out


def _catboost_shap_matrix(
    model: Any, frame: pd.DataFrame, cat_feature_names: list[str]
) -> np.ndarray:
    from catboost import Pool as CatPool

    pool = CatPool(frame, cat_features=cat_feature_names or None)
    shap_raw = model.get_feature_importance(pool, type="ShapValues")
    return np.abs(np.asarray(shap_raw[:, :-1], dtype=float))


def _top_shap_features(
    mean_abs_shap: np.ndarray,
    feature_names: list[str],
    *,
    limit: int,
) -> list[dict[str, object]]:
    top_idx = np.argsort(mean_abs_shap)[::-1][:limit]
    return [
        {"feature": feature_names[idx], "mean_abs_shap": float(mean_abs_shap[idx])}
        for idx in top_idx
    ]


def _pairwise_shap_diffs(
    group_shap: dict[str, np.ndarray],
    feature_names: list[str],
    *,
    limit: int,
) -> list[dict[str, object]]:
    pairwise_diffs: list[dict[str, object]] = []
    groups_with_shap = list(group_shap.keys())
    for i, group_a in enumerate(groups_with_shap):
        for group_b in groups_with_shap[i + 1 :]:
            diff = np.abs(group_shap[group_a] - group_shap[group_b])
            top_idx = np.argsort(diff)[::-1][:limit]
            pairwise_diffs.append(
                {
                    "group_a": group_a,
                    "group_b": group_b,
                    "top_driving_features": [
                        {
                            "feature": feature_names[idx],
                            "shap_diff": float(diff[idx]),
                        }
                        for idx in top_idx
                    ],
                }
            )
    return pairwise_diffs


def _attribute_shap_result(
    *,
    attribute: str,
    labels: np.ndarray,
    sample_idx: np.ndarray,
    shap_matrix: np.ndarray,
    feature_names: list[str],
    min_group_size: int = 10,
) -> dict[str, object]:
    group_labels = pd.Series(labels).iloc[sample_idx].reset_index(drop=True).astype(str)
    unique_groups = sorted(group_labels.unique())
    group_shap: dict[str, np.ndarray] = {}
    group_top5: dict[str, list[dict[str, object]]] = {}

    for group in unique_groups:
        mask = group_labels.eq(group).to_numpy()
        if mask.sum() < min_group_size:
            continue
        mean_abs_shap = shap_matrix[mask].mean(axis=0)
        group_shap[str(group)] = mean_abs_shap
        group_top5[str(group)] = _top_shap_features(mean_abs_shap, feature_names, limit=5)

    groups_with_shap = list(group_shap.keys())
    return {
        "attribute": attribute,
        "groups_analyzed": groups_with_shap,
        "top5_per_group": group_top5,
        "pairwise_feature_diffs": _pairwise_shap_diffs(
            group_shap,
            feature_names,
            limit=3,
        ),
    }


def _shap_attribute_results(
    groups_dict: dict[str, np.ndarray],
    *,
    sample_idx: np.ndarray,
    shap_matrix: np.ndarray,
    feature_names: list[str],
) -> list[dict[str, object]]:
    attribute_results: list[dict[str, object]] = []
    for attribute, labels in groups_dict.items():
        if "__x__" in attribute:
            continue
        result = _attribute_shap_result(
            attribute=attribute,
            labels=labels,
            sample_idx=sample_idx,
            shap_matrix=shap_matrix,
            feature_names=feature_names,
        )
        attribute_results.append(result)
        groups_analyzed = result.get("groups_analyzed", [])
        n_groups = len(groups_analyzed) if isinstance(groups_analyzed, list) else 0
        logger.info(f"SHAP per-group: {attribute} ({n_groups} groups)")
    return attribute_results


def _shap_result_payload(
    *,
    model_path: Path,
    sample_size: int,
    n_features: int,
    attribute_results: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_path": str(model_path),
        "shap_sample_size": sample_size,
        "n_features": n_features,
        "attributes": attribute_results,
        "interpretation": (
            "For each protected attribute, top-5 features by mean |SHAP| per group. "
            "Pairwise diffs show which features drive SHAP disparities between groups. "
            "Features like dti/loan_amnt are legitimate credit risk factors; "
            "home_ownership may proxy for race in US ECOA context."
        ),
    }


def _compute_shap_per_group(
    data: pd.DataFrame,
    groups_dict: dict[str, np.ndarray],
    model_path: str | Path = "models/pd_canonical.cbm",
    shap_sample_size: int = SHAP_SAMPLE_SIZE,
    random_state: int = 42,
) -> dict[str, object] | None:
    """Compute per-group SHAP analysis to identify which features drive disparities.

    For each protected attribute, computes mean |SHAP| per group and the
    top-5 features per group. Also computes pairwise group differences
    |mean_SHAP_A - mean_SHAP_B| to identify the features responsible for
    any observed fairness gaps.

    Args:
        data: Test feature DataFrame (test_fe.parquet, n=276K rows).
        groups_dict: Base attribute groups from fairness audit.
        model_path: Path to the trained CatBoost model (.cbm).
        shap_sample_size: Max rows to use for SHAP (performance cap).
        random_state: Random seed for sampling.

    Returns:
        Dict with per-attribute SHAP analysis, or None on failure.
    """
    try:
        from catboost import CatBoostClassifier
    except ImportError as e:
        logger.warning(f"SHAP per-group analysis skipped — missing dependency: {e}")
        return None

    model_path = Path(model_path)
    if not model_path.exists():
        logger.warning(f"SHAP per-group analysis skipped — model not found: {model_path}")
        return None

    try:
        model = CatBoostClassifier()
        model.load_model(str(model_path))
        feature_names = _model_feature_names(model)
    except Exception as e:
        logger.warning(f"SHAP per-group analysis skipped — model load error: {e}")
        return None

    available_features = _available_features(feature_names, data)
    if not available_features:
        logger.warning("SHAP per-group analysis skipped — no model features found in test data")
        return None

    x_sample, sample_idx = _sample_shap_frame(
        data[available_features].copy(),
        shap_sample_size=shap_sample_size,
        random_state=random_state,
    )

    logger.info(
        f"Computing SHAP values on {len(x_sample):,} rows, {len(available_features)} features"
    )
    try:
        # Use CatBoost's native SHAP via Pool + get_feature_importance — avoids the shap
        # library's cat/NaN handling issues entirely.  model.get_cat_feature_indices() works
        # on .cbm-loaded models without needing the sklearn feature_names_ attribute.
        cat_feature_names = _catboost_cat_feature_names(model, x_sample)
        x_sample = _prepare_catboost_shap_frame(x_sample, cat_feature_names)
        shap_matrix = _catboost_shap_matrix(model, x_sample, cat_feature_names)
    except Exception as e:
        logger.warning(f"SHAP per-group analysis skipped — SHAP computation error: {e}")
        return None

    attribute_results = _shap_attribute_results(
        groups_dict,
        sample_idx=sample_idx,
        shap_matrix=shap_matrix,
        feature_names=available_features,
    )
    return _shap_result_payload(
        model_path=model_path,
        sample_size=len(x_sample),
        n_features=len(available_features),
        attribute_results=attribute_results,
    )


def _bootstrap_base_indices(
    n_rows: int,
    *,
    bootstrap_max_rows: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if bootstrap_max_rows > 0 and n_rows > bootstrap_max_rows:
        return np.sort(rng.choice(n_rows, size=bootstrap_max_rows, replace=False))
    return np.arange(n_rows)


def _fairlearn_group_rows(
    *,
    attribute: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: pd.Series,
) -> list[dict[str, object]]:
    metric_frame = MetricFrame(
        metrics={"selection_rate": selection_rate, "accuracy": accuracy_score},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
    )
    by_group = metric_frame.by_group.reset_index()
    by_group.columns = ["group", *[str(col) for col in by_group.columns[1:]]]
    rows = by_group.to_dict(orient="records")
    for row in rows:
        row["attribute"] = attribute
    return rows


def _bootstrap_fairlearn_gaps(
    *,
    boot_sensitive_base: pd.Series,
    boot_true_base: np.ndarray,
    boot_pred_base: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> tuple[list[float], list[float]]:
    dpd_boot: list[float] = []
    eo_boot: list[float] = []
    for _ in range(max(n_boot, 0)):
        idx = rng.integers(0, len(boot_true_base), len(boot_true_base))
        boot_sensitive = boot_sensitive_base.iloc[idx]
        boot_true = boot_true_base[idx]
        boot_pred = boot_pred_base[idx]
        dpd_boot.append(
            float(
                demographic_parity_difference(
                    y_true=boot_true,
                    y_pred=boot_pred,
                    sensitive_features=boot_sensitive,
                )
            )
        )
        eo_boot.append(
            float(
                equalized_odds_difference(
                    y_true=boot_true,
                    y_pred=boot_pred,
                    sensitive_features=boot_sensitive,
                )
            )
        )
    return dpd_boot, eo_boot


def _fairlearn_summary_row(
    *,
    attribute: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: pd.Series,
    bootstrap_idx: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> dict[str, object]:
    dpd = float(
        demographic_parity_difference(
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=sensitive,
        )
    )
    eo = float(
        equalized_odds_difference(
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=sensitive,
        )
    )
    dpd_boot, eo_boot = _bootstrap_fairlearn_gaps(
        boot_sensitive_base=sensitive.iloc[bootstrap_idx].reset_index(drop=True),
        boot_true_base=y_true[bootstrap_idx],
        boot_pred_base=y_pred[bootstrap_idx],
        rng=rng,
        n_boot=n_boot,
    )
    return {
        "attribute": attribute,
        "demographic_parity_difference": dpd,
        "equalized_odds_difference": eo,
        "dpd_ci_low": float(np.quantile(dpd_boot, 0.025)) if dpd_boot else None,
        "dpd_ci_high": float(np.quantile(dpd_boot, 0.975)) if dpd_boot else None,
        "eo_ci_low": float(np.quantile(eo_boot, 0.025)) if eo_boot else None,
        "eo_ci_high": float(np.quantile(eo_boot, 0.975)) if eo_boot else None,
    }


def _fairlearn_sidecar_rows(
    *,
    groups_all: dict[str, np.ndarray],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    bootstrap_idx: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    group_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for attribute, labels in groups_all.items():
        sensitive = pd.Series(labels).astype(str).reset_index(drop=True)
        group_rows.extend(
            _fairlearn_group_rows(
                attribute=attribute,
                y_true=y_true,
                y_pred=y_pred,
                sensitive=sensitive,
            )
        )
        summary_rows.append(
            _fairlearn_summary_row(
                attribute=attribute,
                y_true=y_true,
                y_pred=y_pred,
                sensitive=sensitive,
                bootstrap_idx=bootstrap_idx,
                rng=rng,
                n_boot=n_boot,
            )
        )
    return group_rows, summary_rows


def _write_fairlearn_sidecar(
    *,
    sidecar_cfg: dict,
    groups_all: dict[str, np.ndarray],
    y_true_eval: np.ndarray,
    y_pred_binary: np.ndarray,
    status_path: Path,
    primary_threshold: float,
    outcome_mode: str,
    resolved_run_tag: str,
) -> None:
    rng = np.random.default_rng(int(sidecar_cfg.get("bootstrap_random_state", 42)))
    n_boot = int(sidecar_cfg.get("bootstrap_samples", 200))
    bootstrap_max_rows = int(sidecar_cfg.get("bootstrap_max_rows", 50_000))
    y_true_arr = np.asarray(y_true_eval, dtype=float)
    y_pred_arr = np.asarray(y_pred_binary, dtype=float)
    bootstrap_idx = _bootstrap_base_indices(
        len(y_true_arr),
        bootstrap_max_rows=bootstrap_max_rows,
        rng=rng,
    )
    group_rows, summary_rows = _fairlearn_sidecar_rows(
        groups_all=groups_all,
        y_true=y_true_arr,
        y_pred=y_pred_arr,
        bootstrap_idx=bootstrap_idx,
        rng=rng,
        n_boot=n_boot,
    )

    sidecar_path = Path(sidecar_cfg.get("status_json", "models/fairlearn_fairness_status.json"))
    group_metrics_path = Path(
        sidecar_cfg.get("group_metrics_parquet", "data/processed/fairlearn_group_metrics.parquet")
    )
    group_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(group_rows).to_parquet(group_metrics_path, index=False)
    sidecar_payload = {
        "primary_status_path": str(status_path),
        "group_metrics_path": str(group_metrics_path),
        "n_attributes": len(summary_rows),
        "attributes": summary_rows,
        "bootstrap_samples": n_boot,
        "bootstrap_rows_used": len(bootstrap_idx),
        "bootstrap_max_rows": bootstrap_max_rows,
        "prediction_threshold": float(primary_threshold),
        "outcome_mode": outcome_mode,
        **build_artifact_metadata(
            schema_version=f"{SCHEMA_VERSION}-fairlearn",
            run_tag=resolved_run_tag,
            require_explicit=True,
        ),
    }
    sidecar_path.write_text(json.dumps(sidecar_payload, indent=2, default=str), encoding="utf-8")
    logger.info(f"Saved fairlearn sidecar status: {sidecar_path}")


def _with_attribute_type(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["attribute_type"] = np.where(
        out["attribute"].astype(str).str.contains("__x__"),
        "intersectional",
        "base",
    )
    return out


def _primary_frontier(frontier: pd.DataFrame, primary_threshold: float) -> pd.DataFrame:
    if frontier.empty:
        return pd.DataFrame()
    return frontier.loc[np.isclose(frontier["threshold"].astype(float), primary_threshold)]


def _worst_primary_attribute(primary_frontier: pd.DataFrame) -> str:
    if primary_frontier.empty:
        return ""
    return str(
        primary_frontier.sort_values(
            by=["passed_all", "eo_gap", "dpd", "dir"],
            ascending=[True, False, False, True],
        ).iloc[0]["attribute"]
    )


def _decision_override_count(decision_policy: Any) -> int:
    overrides = decision_policy.get("overrides", []) if isinstance(decision_policy, dict) else []
    return len(overrides) if isinstance(overrides, list) else 0


def _decision_global_threshold(decision_policy: Any, primary_threshold: float) -> float:
    if isinstance(decision_policy, dict):
        return _as_float(decision_policy.get("global_threshold", primary_threshold))
    return float(primary_threshold)


def _fairness_status_payload(
    *,
    report: pd.DataFrame,
    frontier: pd.DataFrame,
    frontier_path: Path,
    frontier_thresholds: list[float],
    primary_threshold: float,
    threshold_source: str,
    outcome_mode: str,
    policy: dict,
    decision_policy: Any,
    decision_policy_path: Path,
    config_path: str,
    resolved_run_tag: str,
) -> dict[str, object]:
    primary_frontier = _primary_frontier(frontier, primary_threshold)
    return {
        "overall_pass": bool(report["passed_all"].all()),
        "n_attributes": len(report),
        "n_base_attributes": int(
            (report.get("attribute_type", pd.Series(dtype=str)) == "base").sum()
        ),
        "n_intersectional_attributes": int(
            (report.get("attribute_type", pd.Series(dtype=str)) == "intersectional").sum()
        ),
        "n_passed": int(report["passed_all"].sum()),
        "attributes": report.to_dict(orient="records"),
        "prediction_threshold": float(primary_threshold),
        "primary_threshold": float(primary_threshold),
        "prediction_threshold_source": threshold_source,
        "outcome_mode": outcome_mode,
        "thresholds": {
            "dpd": policy["dpd_threshold"],
            "eo_gap": policy["eo_gap_threshold"],
            "dir": policy["dir_threshold"],
        },
        "threshold_frontier": {
            "path": str(frontier_path),
            "thresholds": frontier_thresholds,
            "worst_primary_attribute": _worst_primary_attribute(primary_frontier),
            "selected_threshold": float(primary_threshold),
            "all_primary_pass": bool(
                primary_frontier.get("passed_all", pd.Series(dtype=bool)).all()
            )
            if not primary_frontier.empty
            else True,
        },
        "decision_policy": {
            "path": str(decision_policy_path),
            "global_threshold": float(primary_threshold),
            "n_overrides": _decision_override_count(decision_policy),
        },
        "policy_config": str(config_path),
        **build_artifact_metadata(
            schema_version=SCHEMA_VERSION,
            run_tag=resolved_run_tag,
            require_explicit=True,
        ),
    }


def _write_json_payload(path: Path, payload: dict[str, object], *, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info(f"Saved {label}: {path}")


def _write_shap_status(
    *,
    shap_result: dict[str, object] | None,
    resolved_run_tag: str,
    primary_threshold: float,
    outcome_mode: str,
    path: Path = SHAP_STATUS_PATH,
) -> None:
    if shap_result is None:
        return
    shap_result["generated_at_utc"] = str(
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )
    shap_result["run_tag"] = resolved_run_tag
    shap_result["prediction_threshold"] = float(primary_threshold)
    shap_result["outcome_mode"] = outcome_mode
    _write_json_payload(path, shap_result, label="SHAP per-group fairness analysis")


def main(config_path: str = "configs/fairness_policy.yaml", run_tag: str | None = None) -> None:
    """Run the fairness audit pipeline."""
    cfg = _load_config(config_path)
    policy = cfg["policy"]
    artifacts = cfg["artifacts"]
    output = cfg["output"]

    # Load test predictions and test data
    pred_path = Path(artifacts["test_predictions_path"])
    data_path = Path(artifacts["test_data_path"])

    if not pred_path.exists():
        raise FileNotFoundError(f"Missing test predictions: {pred_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Missing test data: {data_path}")

    preds = pd.read_parquet(pred_path)
    data = pd.read_parquet(data_path)

    # Extract y_true and y_pred_proba
    y_true_col = "default_flag"
    y_proba_col = "y_pred_proba" if "y_pred_proba" in preds.columns else "pd_calibrated"

    if y_true_col not in data.columns:
        raise KeyError(f"Missing target column '{y_true_col}' in test data")
    if y_proba_col not in preds.columns:
        raise KeyError(
            f"Missing probability column in predictions. Available: {list(preds.columns)}"
        )

    # Align lengths (both should be OOT test set)
    n = min(len(preds), len(data))
    y_true = data[y_true_col].values[:n]
    y_proba = preds[y_proba_col].values[:n]

    logger.info(f"Loaded {n} observations for fairness audit")

    # Build groups from attributes config
    groups_dict = _build_groups_dict(data.iloc[:n], cfg["attributes"])

    if not groups_dict:
        logger.error("No valid attributes found for fairness audit")
        return

    threshold, threshold_source = _resolve_prediction_threshold(cfg, policy)
    outcome_mode = _resolve_outcome_mode(policy)
    if outcome_mode == "approval":
        # Fairness in credit decisions should be audited on favorable outcome (approval).
        y_true_eval = 1.0 - y_true
        y_proba_eval = 1.0 - y_proba
    else:
        y_true_eval = y_true
        y_proba_eval = y_proba
    resolved_run_tag = resolve_run_tag(run_tag, require_explicit=True)

    intersectional_cfg = cfg.get("intersectional", {}) or {}
    intersectional_groups = (
        build_intersectional_groups(
            groups_dict,
            max_order=int(intersectional_cfg.get("max_order", 2)),
            min_group_size=int(intersectional_cfg.get("min_group_size", 300)),
        )
        if bool(intersectional_cfg.get("enabled", True))
        else {}
    )
    groups_all = dict(groups_dict)
    groups_all.update(intersectional_groups)

    frontier_thresholds = _resolve_frontier_thresholds(float(threshold), cfg)
    frontier = fairness_threshold_frontier(
        y_true=y_true_eval,
        y_pred_proba=y_proba_eval,
        groups_dict=groups_all,
        thresholds=frontier_thresholds,
        primary_threshold=float(threshold),
        dpd_threshold=policy["dpd_threshold"],
        eo_gap_threshold=policy["eo_gap_threshold"],
        dir_threshold=policy["dir_threshold"],
    )
    frontier = _with_attribute_type(frontier)
    frontier_path = Path(
        output.get("frontier_parquet", "data/processed/fairness_threshold_frontier.parquet")
    )
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier.to_parquet(frontier_path, index=False)
    logger.info(f"Saved fairness threshold frontier: {frontier_path}")

    decision_policy_cfg = _decision_policy_cfg(cfg)
    decision_policy_path = Path(
        decision_policy_cfg.get("artifact_path", "models/fairness_decision_policy.json")
    )
    auto_select = bool(decision_policy_cfg.get("auto_select", False))
    decision_policy = _load_decision_policy_artifact(decision_policy_path)
    selected_threshold_info = _select_threshold_from_frontier(
        frontier, y_pred_proba_eval=y_proba_eval
    )
    primary_threshold = float(
        selected_threshold_info.get("selected_threshold", float(threshold))
        if auto_select
        else float(threshold)
    )

    if auto_select:
        decision_policy = {
            "global_threshold": primary_threshold,
            "overrides": decision_policy.get("overrides", [])
            if isinstance(decision_policy, dict)
            else [],
            "selection": {
                "source": "fairness_frontier_auto_select",
                "n_passed": int(selected_threshold_info.get("n_passed", 0)),
                "worst_eo_gap": float(selected_threshold_info.get("worst_eo_gap", 0.0)),
                "approval_rate": float(selected_threshold_info.get("approval_rate", 0.0)),
            },
            **build_artifact_metadata(
                schema_version=SCHEMA_VERSION,
                run_tag=resolved_run_tag,
                require_explicit=True,
            ),
        }
        decision_policy_path.parent.mkdir(parents=True, exist_ok=True)
        decision_policy_path.write_text(
            json.dumps(decision_policy, indent=2, default=str),
            encoding="utf-8",
        )
        threshold_source = "decision_policy_artifact_auto_selected"
    elif decision_policy:
        primary_threshold = float(decision_policy.get("global_threshold", threshold))
        threshold_source = "decision_policy_artifact"

    y_pred_binary = _apply_decision_policy(
        y_pred_proba=y_proba_eval,
        groups_all=groups_all,
        decision_policy=decision_policy,
        default_threshold=primary_threshold,
    )
    report = fairness_report_from_binary(
        y_true=y_true_eval,
        y_pred_binary=y_pred_binary,
        groups_dict=groups_all,
        dpd_threshold=policy["dpd_threshold"],
        eo_gap_threshold=policy["eo_gap_threshold"],
        dir_threshold=policy["dir_threshold"],
    )
    report = _with_attribute_type(report)

    audit_path = Path(output["audit_parquet"])
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_parquet(audit_path, index=False)
    logger.info(f"Saved fairness audit: {audit_path}")

    status = _fairness_status_payload(
        report=report,
        frontier=frontier,
        frontier_path=frontier_path,
        frontier_thresholds=frontier_thresholds,
        primary_threshold=float(primary_threshold),
        threshold_source=threshold_source,
        outcome_mode=outcome_mode,
        policy=policy,
        decision_policy=decision_policy,
        decision_policy_path=decision_policy_path,
        config_path=config_path,
        resolved_run_tag=resolved_run_tag,
    )

    status_path = Path(output["status_json"])
    _write_json_payload(status_path, status, label="fairness status")

    sidecar_cfg = cfg.get("fairlearn_sidecar", {}) or {}
    if bool(sidecar_cfg.get("enabled", True)):
        _write_fairlearn_sidecar(
            sidecar_cfg=sidecar_cfg,
            groups_all=groups_all,
            y_true_eval=y_true_eval,
            y_pred_binary=y_pred_binary,
            status_path=status_path,
            primary_threshold=float(primary_threshold),
            outcome_mode=outcome_mode,
            resolved_run_tag=resolved_run_tag,
        )

    _write_shap_status(
        shap_result=_compute_shap_per_group(
            data=data.iloc[:n],
            groups_dict=groups_dict,
        ),
        resolved_run_tag=resolved_run_tag,
        primary_threshold=float(primary_threshold),
        outcome_mode=outcome_mode,
    )

    write_threshold_semantics(
        fairness_primary_threshold=float(primary_threshold),
        decision_policy_global_threshold=_decision_global_threshold(
            decision_policy,
            float(primary_threshold),
        ),
        source_artifacts={
            "fairness_status": str(status_path),
            "fairness_decision_policy": str(decision_policy_path),
            "fairness_frontier": str(frontier_path),
        },
        run_tag=resolved_run_tag,
        extra={
            "fairness_threshold_source": threshold_source,
            "outcome_mode": outcome_mode,
        },
        path=output.get("threshold_semantics_json", "models/threshold_semantics.json"),
    )

    overall_pass = bool(status["overall_pass"])
    pass_label = "PASS" if overall_pass else "FAIL"
    logger.info(
        f"Fairness audit: {pass_label} ({status['n_passed']}/{status['n_attributes']} attributes)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fairness audit")
    parser.add_argument("--config", default="configs/fairness_policy.yaml")
    parser.add_argument("--run-tag", default=None)
    args = parser.parse_args()
    main(config_path=args.config, run_tag=args.run_tag)
