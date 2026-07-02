"""PD conformal interval builders."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.models.conformal._scores import (
    _compute_score_scale,
    _conformal_quantile,
    _resolve_score_scale_family,
)
from src.models.conformal_adapters import ProbabilityRegressor


def apply_probability_calibrator(calibrator: Any, scores: np.ndarray) -> np.ndarray:
    """Apply calibrator robustly across sklearn calibrator API variants."""
    scores = np.asarray(scores, dtype=float)
    if calibrator is None:
        return np.asarray(np.clip(scores, 0.0, 1.0), dtype=float)

    if hasattr(calibrator, "transform"):
        out = calibrator.transform(scores)
        return np.asarray(np.clip(np.asarray(out, dtype=float), 0.0, 1.0), dtype=float)

    if hasattr(calibrator, "predict_proba"):
        out = calibrator.predict_proba(scores.reshape(-1, 1))[:, 1]
        return np.asarray(np.clip(np.asarray(out, dtype=float), 0.0, 1.0), dtype=float)

    try:
        out = calibrator.predict(scores)
        out = np.asarray(out, dtype=float)
        if out.shape[0] != scores.shape[0]:
            out = np.asarray(calibrator.predict(scores.reshape(-1, 1)), dtype=float)
    except (ValueError, TypeError, IndexError):
        out = np.asarray(calibrator.predict(scores.reshape(-1, 1)), dtype=float)

    return np.asarray(np.clip(out, 0.0, 1.0), dtype=float)


def create_pd_intervals(
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    alpha: float = 0.1,
    calibrator: Any | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate global split-conformal PD intervals via MAPIE."""
    from mapie.regression import SplitConformalRegressor

    prob_reg = ProbabilityRegressor(classifier, calibrator=calibrator)
    mapie = SplitConformalRegressor(
        estimator=prob_reg,
        confidence_level=1 - alpha,
        prefit=True,
    )
    mapie.conformalize(X_cal, y_cal.astype(float))

    y_pred, y_intervals_raw = mapie.predict_interval(X_test)
    y_intervals = y_intervals_raw[:, :, 0]

    y_intervals = np.clip(y_intervals, 0, 1)
    y_pred = np.clip(y_pred, 0, 1)

    avg_width = float((y_intervals[:, 1] - y_intervals[:, 0]).mean())
    logger.info(
        f"Conformal PD intervals (global, alpha={alpha}): "
        f"avg_width={avg_width:.4f}, target_coverage={1 - alpha:.0%}"
    )
    return y_pred, y_intervals


def create_pd_intervals_mondrian(
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    group_cal: pd.Series,
    group_test: pd.Series,
    alpha: float = 0.1,
    min_group_size: int = 500,
    calibrator: Any | None = None,
    scaled_scores: bool = False,
    score_scale_family: str = "none",
    log_summary: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Create group-conditional split-conformal PD intervals."""
    y_cal_pred_raw = classifier.predict_proba(X_cal)[:, 1]
    y_test_pred_raw = classifier.predict_proba(X_test)[:, 1]
    y_cal_pred = apply_probability_calibrator(calibrator, y_cal_pred_raw)
    y_test_pred = apply_probability_calibrator(calibrator, y_test_pred_raw)

    return create_pd_intervals_mondrian_from_predictions(
        y_cal_pred=y_cal_pred,
        y_test_pred=y_test_pred,
        y_cal=y_cal,
        group_cal=group_cal,
        group_test=group_test,
        alpha=alpha,
        min_group_size=min_group_size,
        scaled_scores=scaled_scores,
        score_scale_family=score_scale_family,
        log_summary=log_summary,
    )


def create_pd_intervals_mondrian_from_predictions(
    *,
    y_cal_pred: np.ndarray,
    y_test_pred: np.ndarray,
    y_cal: pd.Series | np.ndarray,
    group_cal: pd.Series | np.ndarray,
    group_test: pd.Series | np.ndarray,
    alpha: float = 0.1,
    min_group_size: int = 500,
    scaled_scores: bool = False,
    score_scale_family: str = "none",
    log_summary: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Create group-conditional PD intervals from precomputed probabilities.

    The conformal reopen search evaluates many interval designs against the same
    model scores. This helper preserves the exact interval math used by
    ``create_pd_intervals_mondrian`` while avoiding repeated classifier
    inference inside each grid cell.
    """
    y_cal_pred = np.clip(np.asarray(y_cal_pred, dtype=float).reshape(-1), 0.0, 1.0)
    y_test_pred = np.clip(np.asarray(y_test_pred, dtype=float).reshape(-1), 0.0, 1.0)
    if len(y_cal_pred) != len(y_cal):
        raise ValueError(
            f"Calibration prediction length mismatch: pred={len(y_cal_pred)}, y={len(y_cal)}"
        )
    if len(y_test_pred) != len(group_test):
        raise ValueError(
            f"Test prediction length mismatch: pred={len(y_test_pred)}, groups={len(group_test)}"
        )

    y_cal_arr = np.asarray(y_cal, dtype=float)
    g_cal = pd.Series(group_cal).fillna("UNKNOWN").astype(str).to_numpy()
    g_test = pd.Series(group_test).fillna("UNKNOWN").astype(str).to_numpy()

    scores = np.abs(y_cal_arr - y_cal_pred)
    resolved_scale_family = _resolve_score_scale_family(
        scaled_scores=scaled_scores,
        score_scale_family=score_scale_family,
    )
    cal_scale = _compute_score_scale(y_cal_pred, resolved_scale_family)
    test_scale = _compute_score_scale(y_test_pred, resolved_scale_family)
    if resolved_scale_family != "none":
        scores = scores / cal_scale

    global_q = _conformal_quantile(scores, alpha)
    group_quantiles: dict[str, float] = {}
    group_cal_counts: dict[str, int] = {}
    fallback_groups: list[str] = []

    all_groups = sorted(set(g_cal).union(set(g_test)))
    for g in all_groups:
        mask = g_cal == g
        n_g = int(mask.sum())
        group_cal_counts[g] = n_g
        if n_g >= min_group_size:
            group_quantiles[g] = _conformal_quantile(scores[mask], alpha)
        else:
            group_quantiles[g] = global_q
            fallback_groups.append(g)

    radii = np.array([group_quantiles[str(g)] for g in g_test], dtype=float) * test_scale
    low = np.clip(y_test_pred - radii, 0.0, 1.0)
    high = np.clip(y_test_pred + radii, 0.0, 1.0)
    y_intervals = np.column_stack([low, high])

    diagnostics = {
        "alpha": alpha,
        "global_quantile": global_q,
        "group_quantiles": group_quantiles,
        "group_cal_counts": group_cal_counts,
        "fallback_groups": fallback_groups,
        "scaled_scores": bool(resolved_scale_family != "none"),
        "score_scale_family": resolved_scale_family,
        "min_group_size": min_group_size,
        "avg_width": float((high - low).mean()),
        "median_width": float(np.median(high - low)),
    }
    if log_summary:
        logger.info(
            "Conformal PD intervals (mondrian): "
            f"groups={len(all_groups)}, avg_width={diagnostics['avg_width']:.4f}, "
            f"fallback_groups={len(fallback_groups)}"
        )
    return y_test_pred, y_intervals, diagnostics


def conditional_coverage_by_group(
    y_true: np.ndarray,
    y_intervals: np.ndarray,
    groups: pd.Series | np.ndarray,
) -> pd.DataFrame:
    """Compute conditional coverage and width per segment."""
    g = pd.Series(groups).fillna("UNKNOWN").astype(str)
    y_true_arr = np.asarray(y_true, dtype=float)
    low = y_intervals[:, 0]
    high = y_intervals[:, 1]
    covered = (y_true_arr >= low) & (y_true_arr <= high)
    widths = high - low

    df = pd.DataFrame(
        {
            "group": g,
            "covered": covered.astype(float),
            "width": widths,
        }
    )
    out = (
        df.groupby("group", observed=True)
        .agg(
            n=("covered", "size"),
            coverage=("covered", "mean"),
            avg_width=("width", "mean"),
            median_width=("width", "median"),
        )
        .reset_index()
        .sort_values("group")
    )
    return out


def create_pd_intervals_venn_abers(
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate Venn-Abers multi-probability PD intervals."""
    y_cal_arr = np.asarray(y_cal.values if hasattr(y_cal, "values") else y_cal, dtype=int).reshape(
        -1
    )

    try:
        from mapie.calibration import VennAbersCalibrator

        va = VennAbersCalibrator(estimator=classifier, inductive=True, random_state=42)
        va.fit(
            X_cal,
            y_cal_arr,
            X_calib=X_cal,
            y_calib=y_cal_arr,
        )
        probs = va.predict_proba(X_test)
        p_low_raw = np.clip(np.asarray(probs[:, 0], dtype=float), 0.0, 1.0)
        p_high_raw = np.clip(np.asarray(probs[:, 1], dtype=float), 0.0, 1.0)
        p_low = np.minimum(p_low_raw, p_high_raw)
        p_high = np.maximum(p_low_raw, p_high_raw)
        y_pred_point = np.clip((p_low + p_high) / 2.0, 0.0, 1.0)
        avg_width = float((p_high - p_low).mean())
        logger.info(
            f"Venn-Abers PD intervals [MAPIE]: avg_width={avg_width:.4f}, n_test={len(X_test)}"
        )
        return y_pred_point, p_low, p_high

    except (ImportError, ValueError, TypeError, RuntimeError, AttributeError) as exc:
        logger.warning(
            f"MAPIE VennAbersCalibrator failed ({exc}) - falling back to venn_abers library."
        )

    from venn_abers import VennAbers

    p_cal_pos = np.asarray(classifier.predict_proba(X_cal)[:, 1], dtype=float).reshape(-1)
    p_cal = np.column_stack([1.0 - p_cal_pos, p_cal_pos])
    p_test_pos = np.asarray(classifier.predict_proba(X_test)[:, 1], dtype=float).reshape(-1)
    p_test = np.column_stack([1.0 - p_test_pos, p_test_pos])

    wrapped = VennAbers()
    wrapped.fit(p_cal, y_cal_arr)
    y_pred_binary, p_result = wrapped.predict_proba(p_test)
    p0 = np.clip(np.asarray(p_result[:, 0], dtype=float), 0.0, 1.0)
    p1 = np.clip(np.asarray(p_result[:, 1], dtype=float), 0.0, 1.0)

    p_low = np.minimum(p0, p1)
    p_high = np.maximum(p0, p1)
    y_pred_point = np.clip(np.asarray(y_pred_binary[:, 1], dtype=float), 0.0, 1.0)

    avg_width = float((p_high - p_low).mean())
    logger.info(
        f"Venn-Abers PD intervals [fallback]: avg_width={avg_width:.4f}, n_test={len(X_test)}"
    )
    return y_pred_point, p_low, p_high
