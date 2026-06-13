"""Classification conformal sets and Mondrian partition helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.models.conformal._scores import _conformal_quantile
from src.models.conformal.pd_intervals import apply_probability_calibrator
from src.models.conformal_adapters import PrefitCalibratedClassifierAdapter


def create_classification_sets(
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    alpha: float = 0.1,
    method: str = "lac",
    calibrator: Any | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate conformal prediction sets for classification."""
    method_key = str(method or "lac").strip().lower()
    if method_key == "margin":
        y_pred, y_sets = _create_margin_classification_sets(
            classifier=classifier,
            X_cal=X_cal,
            y_cal=y_cal,
            X_test=X_test,
            alpha=alpha,
            calibrator=calibrator,
        )
    else:
        from mapie.classification import SplitConformalClassifier

        adapted = PrefitCalibratedClassifierAdapter(
            classifier,
            calibrator=calibrator,
            n_features_in=X_cal.shape[1],
        )
        mapie = SplitConformalClassifier(
            estimator=adapted,
            confidence_level=1 - alpha,
            conformity_score=method_key,
            prefit=True,
        )
        mapie.conformalize(X_cal, y_cal)

        y_pred = mapie.predict(X_test)
        _, y_sets_raw = mapie.predict_set(X_test)
        y_sets = np.asarray(y_sets_raw[:, :, 0], dtype=int)

    singleton_rate = (y_sets.sum(axis=1) == 1).mean()
    logger.info(
        f"Conformal sets (alpha={alpha}, method={method_key}): singleton_rate={singleton_rate:.2%}"
    )
    return y_pred, y_sets


def _create_margin_classification_sets(
    *,
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    alpha: float,
    calibrator: Any | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Binary margin-style conformal sets over calibrated probabilities."""
    p_cal = apply_probability_calibrator(calibrator, classifier.predict_proba(X_cal)[:, 1])
    p_test = apply_probability_calibrator(calibrator, classifier.predict_proba(X_test)[:, 1])
    y_cal_arr = np.asarray(y_cal, dtype=int).reshape(-1)

    p_true = np.where(y_cal_arr == 1, p_cal, 1.0 - p_cal)
    nonconformity = 2.0 * (1.0 - p_true)
    q_alpha = _conformal_quantile(nonconformity, alpha)

    include_pos = (2.0 * (1.0 - p_test)) <= q_alpha
    include_neg = (2.0 * p_test) <= q_alpha
    y_sets = np.column_stack([include_neg.astype(int), include_pos.astype(int)])
    y_pred = (p_test >= 0.5).astype(int)
    return y_pred, y_sets


def create_classification_sets_mondrian(
    classifier: Any,
    X_cal: pd.DataFrame,
    y_cal: pd.Series,
    X_test: pd.DataFrame,
    group_cal: pd.Series,
    group_test: pd.Series,
    alpha: float = 0.1,
    method: str = "lac",
    min_group_size: int = 500,
    calibrator: Any | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Generate group-conditional conformal prediction sets for binary classification."""
    g_cal = pd.Series(group_cal).fillna("UNKNOWN").astype(str).reset_index(drop=True)
    g_test = pd.Series(group_test).fillna("UNKNOWN").astype(str).reset_index(drop=True)
    all_groups = sorted(set(g_cal).union(set(g_test)))
    group_counts = {group: int((g_cal == group).sum()) for group in all_groups}
    fallback_groups: list[str] = []

    global_pred, global_sets = create_classification_sets(
        classifier=classifier,
        X_cal=X_cal,
        y_cal=y_cal,
        X_test=X_test,
        alpha=alpha,
        method=method,
        calibrator=calibrator,
    )
    y_pred = np.asarray(global_pred, dtype=int).copy()
    y_sets = np.asarray(global_sets, dtype=int).copy()

    for group in all_groups:
        cal_mask = g_cal == group
        test_mask = g_test == group
        if not test_mask.any():
            continue
        if int(cal_mask.sum()) < int(min_group_size):
            fallback_groups.append(group)
            continue
        group_pred, group_sets = create_classification_sets(
            classifier=classifier,
            X_cal=X_cal.loc[cal_mask].reset_index(drop=True),
            y_cal=y_cal.loc[cal_mask].reset_index(drop=True),
            X_test=X_test.loc[test_mask].reset_index(drop=True),
            alpha=alpha,
            method=method,
            calibrator=calibrator,
        )
        y_pred[np.asarray(test_mask)] = np.asarray(group_pred, dtype=int)
        y_sets[np.asarray(test_mask)] = np.asarray(group_sets, dtype=int)

    diagnostics = {
        "alpha": float(alpha),
        "method": str(method),
        "min_group_size": int(min_group_size),
        "group_cal_counts": group_counts,
        "fallback_groups": sorted(set(fallback_groups)),
    }
    return y_pred, y_sets, diagnostics


def build_mondrian_partition_labels(
    *,
    y_prob_cal: np.ndarray,
    y_prob_eval: np.ndarray,
    partition: str,
    base_groups_cal: pd.Series | np.ndarray | None = None,
    base_groups_eval: pd.Series | np.ndarray | None = None,
    n_score_bins: int = 10,
    min_group_size: int = 500,
    fallback_mode: str = "grade_then_global",
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    """Build partition labels for Mondrian-style calibration."""
    partition_key = str(partition).strip().lower()
    if partition_key in {"grade", "group", "default"}:
        if base_groups_cal is None or base_groups_eval is None:
            raise ValueError("grade partition requires base group labels for calibration/eval.")
        g_cal = pd.Series(base_groups_cal).fillna("UNKNOWN").astype(str).reset_index(drop=True)
        g_eval = pd.Series(base_groups_eval).fillna("UNKNOWN").astype(str).reset_index(drop=True)
        return (
            g_cal,
            g_eval,
            {
                "partition": "grade",
                "score_band_count": 0,
                "fallback_groups": [],
            },
        )

    cal_scores = pd.Series(np.asarray(y_prob_cal, dtype=float).reshape(-1)).clip(0.0, 1.0)
    eval_scores = pd.Series(np.asarray(y_prob_eval, dtype=float).reshape(-1)).clip(0.0, 1.0)
    rank_source = cal_scores.rank(method="first")
    n_bins_effective = int(max(1, min(int(n_score_bins), int(rank_source.nunique()))))
    if n_bins_effective <= 1:
        cal_band = pd.Series(["score_q0"] * len(cal_scores), dtype="string")
        eval_band = pd.Series(["score_q0"] * len(eval_scores), dtype="string")
        edges = np.array([0.0, 1.0], dtype=float)
    else:
        quantiles = np.linspace(0.0, 1.0, n_bins_effective + 1)
        edges = np.unique(np.quantile(cal_scores.to_numpy(dtype=float), quantiles))
        if len(edges) <= 2:
            cal_band = pd.Series(["score_q0"] * len(cal_scores), dtype="string")
            eval_band = pd.Series(["score_q0"] * len(eval_scores), dtype="string")
        else:
            labels = [f"score_q{i:02d}" for i in range(len(edges) - 1)]
            cal_band = pd.cut(
                cal_scores,
                bins=edges,
                labels=labels,
                include_lowest=True,
                duplicates="drop",
            ).astype("string")
            eval_band = pd.cut(
                eval_scores,
                bins=edges,
                labels=labels,
                include_lowest=True,
                duplicates="drop",
            ).astype("string")
            cal_band = cal_band.fillna(labels[0])
            eval_band = eval_band.fillna(labels[0])

    if partition_key in {"score_decile_mondrian", "score_decile", "scoreband"}:
        return (
            cal_band.astype(str).reset_index(drop=True),
            eval_band.astype(str).reset_index(drop=True),
            {
                "partition": "score_decile_mondrian",
                "score_band_count": int(cal_band.nunique()),
                "score_band_edges": [float(x) for x in np.asarray(edges, dtype=float)],
                "fallback_groups": [],
                "fallback_mode": "score_only",
            },
        )

    if partition_key not in {"grade_x_scoreband_mondrian", "grade_scoreband", "hybrid"}:
        raise ValueError(f"Unsupported partition mode: {partition}")

    if base_groups_cal is None or base_groups_eval is None:
        raise ValueError("grade_x_scoreband_mondrian requires base group labels.")

    grade_cal = pd.Series(base_groups_cal).fillna("UNKNOWN").astype(str).reset_index(drop=True)
    grade_eval = pd.Series(base_groups_eval).fillna("UNKNOWN").astype(str).reset_index(drop=True)
    hybrid_cal = (grade_cal + "|" + cal_band.astype(str)).reset_index(drop=True)
    hybrid_eval = (grade_eval + "|" + eval_band.astype(str)).reset_index(drop=True)

    counts = hybrid_cal.value_counts(dropna=False).to_dict()
    grade_counts = grade_cal.value_counts(dropna=False).to_dict()
    fallback_groups: list[str] = []
    fallback_mode_key = str(fallback_mode or "grade_then_global").strip().lower()
    if fallback_mode_key not in {"grade_then_global", "global_only"}:
        raise ValueError(f"Unsupported fallback_mode: {fallback_mode}")

    def _resolve_label(label: str, base_grade: str) -> str:
        n_label = int(counts.get(label, 0))
        if n_label >= int(min_group_size):
            return label
        fallback_groups.append(label)
        if fallback_mode_key == "grade_then_global" and int(grade_counts.get(base_grade, 0)) >= int(
            min_group_size
        ):
            return base_grade
        return "GLOBAL"

    resolved_cal = pd.Series(
        [
            _resolve_label(str(label), str(grade))
            for label, grade in zip(hybrid_cal, grade_cal, strict=False)
        ],
        dtype="string",
    )
    resolved_eval = pd.Series(
        [
            _resolve_label(str(label), str(grade))
            for label, grade in zip(hybrid_eval, grade_eval, strict=False)
        ],
        dtype="string",
    )
    return (
        resolved_cal.astype(str).reset_index(drop=True),
        resolved_eval.astype(str).reset_index(drop=True),
        {
            "partition": "grade_x_scoreband_mondrian",
            "score_band_count": int(cal_band.nunique()),
            "score_band_edges": [float(x) for x in np.asarray(edges, dtype=float)],
            "fallback_groups": sorted(set(fallback_groups)),
            "hybrid_group_count_cal": int(hybrid_cal.nunique()),
            "resolved_group_count_cal": int(resolved_cal.nunique()),
            "fallback_mode": fallback_mode_key,
        },
    )


def create_cross_conformal_score_intervals(
    y_cal: pd.Series | np.ndarray,
    y_prob_cal: np.ndarray,
    y_prob_test: np.ndarray,
    *,
    alpha: float = 0.1,
    method: str = "plus",
    cv: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Run a lightweight cross conformal benchmark on raw score space."""
    from mapie.regression import CrossConformalRegressor
    from sklearn.linear_model import LinearRegression

    y_cal_arr = np.asarray(y_cal, dtype=float).reshape(-1)
    X_cal = np.asarray(y_prob_cal, dtype=float).reshape(-1, 1)
    X_test = np.asarray(y_prob_test, dtype=float).reshape(-1, 1)

    regressor = CrossConformalRegressor(
        estimator=LinearRegression(),
        confidence_level=1 - alpha,
        method=method,
        cv=cv,
    )
    regressor.fit_conformalize(X_cal, y_cal_arr)
    y_pred, y_intervals_raw = regressor.predict_interval(X_test)
    y_pred_arr = np.clip(np.asarray(y_pred, dtype=float).reshape(-1), 0.0, 1.0)
    y_intervals = np.asarray(y_intervals_raw[:, :, 0], dtype=float)
    y_intervals = np.clip(y_intervals, 0.0, 1.0)
    return y_pred_arr, y_intervals
