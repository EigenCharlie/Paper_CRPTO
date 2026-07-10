"""Validate conformal artifacts against explicit acceptance policy.

Usage:
    uv run python scripts/validate_conformal_policy.py --config configs/crpto_conformal_policy.yaml
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from loguru import logger

from src.utils.artifact_metadata import build_artifact_metadata, resolve_run_tag
from src.utils.baseline_registry import resolve_official_baseline_run_tag

try:
    from mapie.metrics.regression import regression_mwi_score as _imported_mapie_mwi_score

    _mapie_mwi_score: Any = _imported_mapie_mwi_score
    _MAPIE_MWI_AVAILABLE = True
except ImportError:
    _mapie_mwi_score = None
    _MAPIE_MWI_AVAILABLE = False

DEFAULT_POLICY_CONFIG = "configs/crpto_conformal_policy.yaml"


def _fallback_winkler_interval_score(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    alpha: float,
) -> np.ndarray:
    y_true = np.asarray(y_true, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    width = np.maximum(upper - lower, 0.0)
    below = np.maximum(lower - y_true, 0.0)
    above = np.maximum(y_true - upper, 0.0)
    penalty = (2.0 / max(float(alpha), 1e-12)) * (below + above)
    return width + penalty


_imported_winkler_interval_score: Any
try:
    from src.evaluation import backtesting as _backtesting

    _imported_winkler_interval_score = _backtesting.winkler_interval_score
except ImportError:
    _imported_winkler_interval_score = _fallback_winkler_interval_score

winkler_interval_score: Any = _imported_winkler_interval_score

SCHEMA_VERSION = "2026-06-07.1"
RETIRED_BACKTEST_CHECKS = (
    "kupiec_pvalue_90",
    "kupiec_pvalue_95",
    "christoffersen_pvalue_90",
    "christoffersen_pvalue_95",
)


def _check(
    metric_name: str, value: float, threshold: float, comparator: str, scope: str
) -> dict[str, object]:
    if comparator == ">=":
        passed = value >= threshold
    elif comparator == "<=":
        passed = value <= threshold
    else:
        raise ValueError(f"Unsupported comparator: {comparator}")
    return {
        "scope": scope,
        "metric": metric_name,
        "value": float(value),
        "threshold": float(threshold),
        "comparator": comparator,
        "passed": bool(passed),
    }


def _safe_float(value: object, default: float = float("nan")) -> float:
    try:
        if isinstance(value, int | float | str):
            return float(value)
        return default
    except (TypeError, ValueError):
        return default


def _compute_mapie_mwi_score(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    confidence_level: float,
) -> float:
    """Compute MAPIE MWI across current and legacy MAPIE metric signatures."""
    if _mapie_mwi_score is None:
        raise RuntimeError("MAPIE regression_mwi_score is not available.")
    y = np.asarray(y_true, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    y_pis = np.stack([lo, hi], axis=1)[:, :, np.newaxis]
    try:
        return float(_mapie_mwi_score(y, y_pis, confidence_level=confidence_level))
    except TypeError:
        alpha = 1.0 - confidence_level
        return float(np.mean(_mapie_mwi_score(y, lo, hi, alpha_=alpha)))


def _apply_artifact_namespace(
    cfg: dict[str, object],
    artifact_namespace: str | None,
) -> dict[str, object]:
    if not artifact_namespace:
        return cfg
    ns = str(artifact_namespace).strip().replace("/", "_")
    data_dir = Path("data/processed/conformal_gap") / ns
    models_dir = Path("models/conformal_gap") / ns
    updated = dict(cfg)
    artifacts = dict(cast(Mapping[str, Any], updated.get("artifacts", {}) or {}))
    output = dict(cast(Mapping[str, Any], updated.get("output", {}) or {}))
    artifacts["conformal_results_path"] = str(models_dir / "conformal_results_mondrian.pkl")
    artifacts["group_metrics_path"] = str(data_dir / "conformal_group_metrics_mondrian.parquet")
    artifacts["backtest_monthly_path"] = str(data_dir / "conformal_backtest_monthly.parquet")
    artifacts["backtest_alerts_path"] = str(data_dir / "conformal_backtest_alerts.parquet")
    artifacts["intervals_path"] = str(data_dir / "conformal_intervals_mondrian.parquet")
    output["policy_status_json"] = str(models_dir / "conformal_policy_status.json")
    output["policy_checks_parquet"] = str(data_dir / "conformal_policy_checks.parquet")
    updated["artifacts"] = artifacts
    updated["output"] = output
    return updated


def _load_yaml_dict(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return dict(cast(Mapping[str, Any], raw))


def _load_policy_config(
    *,
    config_path: str,
    sensitivity_config_path: str | None,
    artifact_namespace: str | None,
) -> dict[str, Any]:
    cfg = _load_yaml_dict(config_path)
    if sensitivity_config_path is not None:
        sens_cfg = _load_yaml_dict(sensitivity_config_path)
        if "policy_sensitivity" in sens_cfg:
            cfg["policy_sensitivity"] = sens_cfg["policy_sensitivity"]
            logger.info(
                f"Overriding policy_sensitivity from {sensitivity_config_path}: "
                f"{cfg['policy_sensitivity']}"
            )
    return _apply_artifact_namespace(cfg, artifact_namespace)


def _load_alerts(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame({"severity": pd.Series(dtype="object")})


def _interval_arrays(
    intervals_df: pd.DataFrame,
    *,
    lower_col: str,
    upper_col: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if {"y_true", lower_col, upper_col}.issubset(intervals_df.columns):
        y_true = pd.to_numeric(intervals_df["y_true"], errors="coerce").to_numpy(dtype=float)
        lower = pd.to_numeric(intervals_df[lower_col], errors="coerce").to_numpy(dtype=float)
        upper = pd.to_numeric(intervals_df[upper_col], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(y_true) & np.isfinite(lower) & np.isfinite(upper)
        return y_true[valid], lower[valid], upper[valid]
    empty = np.array([], dtype=float)
    return empty, empty, empty


def _mean_winkler(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    alpha: float,
) -> float:
    if not y_true.size:
        return float("inf")
    return float(np.mean(winkler_interval_score(y_true, lower, upper, alpha=alpha)))


def _violation_rate(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    if not y_true.size:
        return float("nan")
    return float(np.mean((y_true < lower) | (y_true > upper)))


def _mapie_mwi_cross_check(
    *,
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    winkler_score: float,
    confidence_level: float,
) -> float | None:
    if not (_MAPIE_MWI_AVAILABLE and y_true.size):
        return None
    try:
        mapie_score = _compute_mapie_mwi_score(
            y_true,
            lower,
            upper,
            confidence_level=confidence_level,
        )
        delta = abs(mapie_score - winkler_score)
        if delta > 0.01:
            logger.warning(
                f"MAPIE MWI ({mapie_score:.4f}) deviates from manual Winkler "
                f"({winkler_score:.4f}) by {delta:.4f} -- check score definition."
            )
        else:
            logger.info(f"MAPIE MWI cross-check OK: {mapie_score:.4f} ~= {winkler_score:.4f}")
        return mapie_score
    except Exception as exc:
        logger.warning(f"MAPIE MWI cross-check failed: {exc}")
        return None


def _evaluate_check_frame(frame: pd.DataFrame) -> dict[str, Any]:
    gate_pass = bool(frame["passed"].all())
    failing_material = frame.loc[~frame["passed"], "metric"].astype(str).tolist()
    methodological_status = (
        "not_needed_material_gate_pass" if gate_pass else "blocked_material_gate_failures"
    )
    return {
        "strict_overall_pass": gate_pass,
        "gate_overall_pass": gate_pass,
        "non_statistical_checks_pass": gate_pass,
        "diagnostic_statistical_pass": True,
        "failing_checks": failing_material,
        "failing_statistical_checks": [],
        "gate_failing_checks": failing_material,
        "failing_non_statistical_checks": failing_material,
        "diagnostic_failing_checks": [],
        "methodological_justification_pass": gate_pass,
        "methodological_justification_status": methodological_status,
    }


def _winkler_90_check(policy: dict[str, Any], metrics: dict[str, float]) -> dict[str, object]:
    max_winkler_90 = float(policy.get("max_winkler_90", float("inf")))
    enable_compensated = bool(policy.get("enable_compensated_winkler_90", False))
    compensated_threshold = float(policy.get("compensated_winkler_90_max", max_winkler_90))
    compensated_min_coverage = float(
        policy.get("compensated_min_coverage_90", policy["target_coverage_90_min"])
    )
    compensated_min_group_coverage = float(
        policy.get("compensated_min_group_coverage_90", policy["min_group_coverage_90_min"])
    )
    compensated_max_avg_width = float(
        policy.get("compensated_max_avg_width_90", policy["max_avg_width_90"])
    )

    raw_pass = bool(metrics["winkler_90"] <= max_winkler_90)
    compensated_pass = bool(
        enable_compensated
        and (not raw_pass)
        and metrics["winkler_90"] <= compensated_threshold
        and metrics["coverage_90"] >= compensated_min_coverage
        and metrics["min_group_coverage_90"] >= compensated_min_group_coverage
        and metrics["avg_width_90"] <= compensated_max_avg_width
        and metrics["critical_alerts"] <= float(policy["max_critical_alerts"])
    )
    policy_pass = bool(raw_pass or compensated_pass)
    policy_mode = "strict" if raw_pass else "compensated_band" if compensated_pass else "strict"
    check = _check("winkler_90", metrics["winkler_90"], max_winkler_90, "<=", "quality")
    check["passed"] = bool(policy_pass)
    check["policy_mode"] = str(policy_mode)
    check["raw_threshold"] = float(max_winkler_90)
    check["raw_passed"] = bool(raw_pass)
    check["compensated_band_enabled"] = bool(enable_compensated)
    check["compensated_threshold"] = float(compensated_threshold)
    check["compensated_passed"] = bool(compensated_pass)
    return check


def _policy_checks(policy: dict[str, Any], metrics: dict[str, float]) -> list[dict[str, object]]:
    return [
        _check(
            "coverage_90",
            metrics["coverage_90"],
            float(policy["target_coverage_90_min"]),
            ">=",
            "portfolio",
        ),
        _check(
            "coverage_95",
            metrics["coverage_95"],
            float(policy["target_coverage_95_min"]),
            ">=",
            "portfolio",
        ),
        _check(
            "min_group_coverage_90",
            metrics["min_group_coverage_90"],
            float(policy["min_group_coverage_90_min"]),
            ">=",
            "group",
        ),
        _check(
            "avg_width_90",
            metrics["avg_width_90"],
            float(policy["max_avg_width_90"]),
            "<=",
            "portfolio",
        ),
        _check(
            "critical_alerts",
            metrics["critical_alerts"],
            float(policy["max_critical_alerts"]),
            "<=",
            "monitoring",
        ),
        _check(
            "total_alerts",
            metrics["total_alerts"],
            float(policy["max_total_alerts"]),
            "<=",
            "monitoring",
        ),
        _check(
            "warning_alerts",
            metrics["warning_alerts"],
            float(policy["max_warning_alerts"]),
            "<=",
            "monitoring",
        ),
        _winkler_90_check(policy, metrics),
        _check(
            "winkler_95",
            metrics["winkler_95"],
            float(policy.get("max_winkler_95", float("inf"))),
            "<=",
            "quality",
        ),
    ]


def _latest_backtest_month(backtest_monthly: pd.DataFrame) -> object | None:
    if backtest_monthly.empty:
        return None
    return backtest_monthly.sort_values("month").iloc[-1]["month"]


def main(
    config_path: str = DEFAULT_POLICY_CONFIG,
    run_tag: str | None = None,
    sensitivity_config_path: str | None = None,
    artifact_namespace: str | None = None,
) -> None:
    cfg = _load_policy_config(
        config_path=config_path,
        sensitivity_config_path=sensitivity_config_path,
        artifact_namespace=artifact_namespace,
    )

    policy = dict(cast(Mapping[str, Any], cfg["policy"]))
    artifacts = dict(cast(Mapping[str, Any], cfg["artifacts"]))
    output = dict(cast(Mapping[str, Any], cfg["output"]))
    resolved_run_tag = resolve_run_tag(
        run_tag,
        fallback_candidates=[resolve_official_baseline_run_tag()],
        require_explicit=True,
    )

    with open(artifacts["conformal_results_path"], "rb") as results_handle:
        results = cast(dict[str, Any], pickle.load(results_handle))
    group_metrics = pd.read_parquet(artifacts["group_metrics_path"])
    backtest_monthly = pd.read_parquet(artifacts["backtest_monthly_path"])
    alerts_path = Path(artifacts["backtest_alerts_path"])
    alerts = _load_alerts(alerts_path)
    intervals_path = Path(
        artifacts.get("intervals_path", "data/processed/conformal_intervals_mondrian.parquet")
    )
    intervals_df = pd.read_parquet(intervals_path)
    lgd_ead_status_path = Path("models/conformal_lgd_ead_status.json")
    lgd_ead_status = (
        json.loads(lgd_ead_status_path.read_text(encoding="utf-8"))
        if lgd_ead_status_path.exists()
        else {"available": False, "reason": "missing_status_artifact"}
    )

    metrics_90 = results.get("metrics_90", {})
    metrics_95 = results.get("metrics_95", {})

    coverage_90 = float(metrics_90.get("empirical_coverage", 0.0))
    coverage_95 = float(metrics_95.get("empirical_coverage", 0.0))
    avg_width_90 = float(metrics_90.get("avg_interval_width", 999.0))
    min_group_coverage_90 = float(group_metrics.get("coverage_90", pd.Series([0.0])).min())
    critical_alerts = int((alerts.get("severity", pd.Series([], dtype=str)) == "critical").sum())
    warning_alerts = int((alerts.get("severity", pd.Series([], dtype=str)) == "warning").sum())
    total_alerts = len(alerts)

    y90, lo90, hi90 = _interval_arrays(intervals_df, lower_col="pd_low_90", upper_col="pd_high_90")
    y95, lo95, hi95 = _interval_arrays(intervals_df, lower_col="pd_low_95", upper_col="pd_high_95")
    winkler_90 = _mean_winkler(y90, lo90, hi90, alpha=0.10)
    winkler_95 = _mean_winkler(y95, lo95, hi95, alpha=0.05)
    mapie_mwi_90 = _mapie_mwi_cross_check(
        y_true=y90,
        lower=lo90,
        upper=hi90,
        winkler_score=winkler_90,
        confidence_level=0.90,
    )
    violation_rate_90 = _violation_rate(y90, lo90, hi90)
    violation_rate_95 = _violation_rate(y95, lo95, hi95)

    metrics = {
        "coverage_90": coverage_90,
        "coverage_95": coverage_95,
        "avg_width_90": avg_width_90,
        "min_group_coverage_90": min_group_coverage_90,
        "critical_alerts": float(critical_alerts),
        "warning_alerts": float(warning_alerts),
        "total_alerts": float(total_alerts),
        "winkler_90": winkler_90,
        "winkler_95": winkler_95,
    }
    checks = _policy_checks(policy, metrics)
    checks_df = pd.DataFrame(checks)
    winkler_90_check = next(check for check in checks if check["metric"] == "winkler_90")
    winkler_90_raw_pass = bool(winkler_90_check.get("raw_passed", False))
    winkler_90_policy_pass = bool(winkler_90_check.get("passed", False))
    winkler_90_policy_mode = str(winkler_90_check.get("policy_mode", "strict"))
    winkler_90_compensated_pass = bool(winkler_90_check.get("compensated_passed", False))
    compensated_winkler_90_max = _safe_float(winkler_90_check.get("compensated_threshold", np.nan))

    evaluation = _evaluate_check_frame(checks_df)
    strict_overall_pass = bool(evaluation["strict_overall_pass"])
    gate_overall_pass = bool(evaluation["gate_overall_pass"])
    non_statistical_checks_pass = bool(evaluation["non_statistical_checks_pass"])
    diagnostic_statistical_pass = bool(evaluation["diagnostic_statistical_pass"])
    failing_checks = list(evaluation["failing_checks"])
    failing_statistical_checks = list(evaluation["failing_statistical_checks"])
    gate_failing_checks = list(evaluation["gate_failing_checks"])
    failing_non_statistical_checks = list(evaluation["failing_non_statistical_checks"])
    diagnostic_failing_checks = list(evaluation["diagnostic_failing_checks"])
    methodological_justification_pass = bool(evaluation["methodological_justification_pass"])
    methodological_status = str(evaluation["methodological_justification_status"])
    overall_pass = gate_overall_pass

    latest_month = _latest_backtest_month(backtest_monthly)

    out_status = {
        "overall_pass": overall_pass,
        "gate_overall_pass": gate_overall_pass,
        "strict_overall_pass": strict_overall_pass,
        "non_statistical_checks_pass": non_statistical_checks_pass,
        "diagnostic_statistical_pass": diagnostic_statistical_pass,
        "methodological_justification_pass": methodological_justification_pass,
        "methodological_justification_status": methodological_status,
        "checks_passed": int(checks_df["passed"].sum()),
        "checks_total": len(checks_df),
        "gate_checks_passed": int(checks_df["passed"].sum()),
        "gate_checks_total": len(checks_df),
        "diagnostic_checks_passed": 0,
        "diagnostic_checks_total": 0,
        "failing_checks": failing_checks,
        "failing_statistical_checks": failing_statistical_checks,
        "gate_failing_checks": gate_failing_checks,
        "failing_non_statistical_checks": failing_non_statistical_checks,
        "diagnostic_failing_checks": diagnostic_failing_checks,
        "coverage_90": coverage_90,
        "coverage_95": coverage_95,
        "avg_width_90": avg_width_90,
        "min_group_coverage_90": min_group_coverage_90,
        "critical_alerts": critical_alerts,
        "warning_alerts": warning_alerts,
        "total_alerts": total_alerts,
        "winkler_90": winkler_90,
        "winkler_90_raw_pass": bool(winkler_90_raw_pass),
        "winkler_90_policy_pass": bool(winkler_90_policy_pass),
        "winkler_90_policy_mode": str(winkler_90_policy_mode),
        "winkler_90_compensated_pass": bool(winkler_90_compensated_pass),
        "winkler_90_compensated_threshold": float(compensated_winkler_90_max),
        "winkler_95": winkler_95,
        "mapie_mwi_90": mapie_mwi_90,
        "sample_size_context": {
            "n_total_90": int(y90.size),
            "n_total_95": int(y95.size),
            "violation_rate_90": violation_rate_90,
            "violation_rate_95": violation_rate_95,
            "nominal_alpha_90": 0.10,
            "nominal_alpha_95": 0.05,
        },
        "methodological_justification": {
            "allowed": True,
            "material_gate_definition": "coverage_width_group_alert_winkler_checks",
            "winkler_90_policy_mode": str(winkler_90_policy_mode),
            "winkler_90_raw_pass": bool(winkler_90_raw_pass),
            "winkler_90_compensated_pass": bool(winkler_90_compensated_pass),
            "winkler_90_compensated_threshold": float(compensated_winkler_90_max),
            "decision": bool(gate_overall_pass),
            "gate_overall_pass": bool(gate_overall_pass),
            "retired_backtest_checks": list(RETIRED_BACKTEST_CHECKS),
            "retirement_reason": (
                "Kupiec and Christoffersen p-value gates test exact nominal VaR-style "
                "coverage and create noisy rejections for conservative conformal intervals "
                "in the 276k OOT sample; IJDS promotion gates on material coverage, "
                "group coverage, width, alert, and Winkler checks instead."
            ),
        },
        "latest_backtest_month": str(latest_month) if latest_month is not None else None,
        "intervals_path": str(intervals_path),
        "artifact_namespace": artifact_namespace or "",
        "policy_config": config_path,
        "lgd_ead_conformal_status_path": str(lgd_ead_status_path),
        "lgd_ead_conformal_status": lgd_ead_status,
        **build_artifact_metadata(
            schema_version=SCHEMA_VERSION,
            run_tag=resolved_run_tag,
            require_explicit=True,
        ),
    }

    sensitivity_cfg = dict(cast(Mapping[str, Any], cfg.get("policy_sensitivity", {}) or {}))
    max_winkler_values = [
        float(x) for x in sensitivity_cfg.get("max_winkler_90_values", []) or [] if x is not None
    ]
    if max_winkler_values:
        sensitivity_rows: list[dict[str, object]] = []
        for threshold in max_winkler_values:
            checks_sens = checks_df.copy()
            mask = checks_sens["metric"].eq("winkler_90")
            checks_sens.loc[mask, "threshold"] = float(threshold)
            checks_sens.loc[mask, "passed"] = float(winkler_90) <= float(threshold)
            sens_eval = _evaluate_check_frame(checks_sens)
            sensitivity_rows.append(
                {
                    "max_winkler_90": float(threshold),
                    "strict_overall_pass": bool(sens_eval["strict_overall_pass"]),
                    "gate_overall_pass": bool(sens_eval["gate_overall_pass"]),
                    "non_statistical_checks_pass": bool(sens_eval["non_statistical_checks_pass"]),
                    "methodological_justification_pass": bool(
                        sens_eval["methodological_justification_pass"]
                    ),
                    "failing_non_statistical_checks": list(
                        sens_eval["failing_non_statistical_checks"]
                    ),
                    "failing_statistical_checks": [],
                }
            )
        out_status["policy_sensitivity"] = {
            "metric": "winkler_90",
            "results": sensitivity_rows,
        }

    checks_path = Path(output["policy_checks_parquet"])
    checks_path.parent.mkdir(parents=True, exist_ok=True)
    checks_df.to_parquet(checks_path, index=False)

    status_path = Path(output["policy_status_json"])
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(out_status, f, indent=2)
        f.write("\n")

    logger.info(f"Policy checks saved: {checks_path}")
    logger.info(f"Policy status saved: {status_path}")
    logger.info(
        "Conformal policy gate_pass="
        f"{gate_overall_pass} ({out_status['gate_checks_passed']}/"
        f"{out_status['gate_checks_total']}); strict_overall_pass={strict_overall_pass}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_POLICY_CONFIG)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument(
        "--sensitivity-config",
        default=None,
        help="Optional YAML with policy_sensitivity overrides (e.g. configs/conformal_policy_sensitivity.yaml)",
    )
    parser.add_argument("--artifact-namespace", default=None)
    args = parser.parse_args()
    main(
        args.config,
        run_tag=args.run_tag,
        sensitivity_config_path=args.sensitivity_config,
        artifact_namespace=args.artifact_namespace,
    )
