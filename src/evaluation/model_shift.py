"""Interpretive helpers for structural shift and p-value semantics."""

from __future__ import annotations

from typing import Any


def interpret_model_shift(
    *,
    c2st_auc: float,
    c2st_materiality: str,
    score_psi: float,
    auc_delta: float,
    brier_increase: float,
    calibration_gap_delta: float,
    distribution_warning_ratio: float,
    score_psi_max: float,
    auc_delta_max: float,
    brier_increase_max: float,
    calibration_gap_delta_max: float,
) -> dict[str, Any]:
    """Distinguish structural shift from predictive degradation."""
    structural_level = _structural_shift_level(
        c2st_auc=c2st_auc,
        score_psi=score_psi,
        distribution_warning_ratio=distribution_warning_ratio,
        score_psi_max=score_psi_max,
    )
    predictive_level = _predictive_degradation_level(
        auc_delta=auc_delta,
        brier_increase=brier_increase,
        calibration_gap_delta=calibration_gap_delta,
        auc_delta_max=auc_delta_max,
        brier_increase_max=brier_increase_max,
        calibration_gap_delta_max=calibration_gap_delta_max,
    )
    shift_type = _shift_type(structural_level, predictive_level)

    return {
        "shift_type": shift_type,
        "structural_shift_level": structural_level,
        "predictive_degradation_level": predictive_level,
        "governance_posture": _governance_posture(shift_type, predictive_level),
        "c2st_materiality": str(c2st_materiality),
        "pvalue_interpretation": _pvalue_note(shift_type),
    }


def _structural_shift_level(
    *,
    c2st_auc: float,
    score_psi: float,
    distribution_warning_ratio: float,
    score_psi_max: float,
) -> str:
    if c2st_auc >= 0.70 or score_psi >= max(score_psi_max * 1.5, 0.20):
        return "severe"
    if c2st_auc >= 0.60 or score_psi >= score_psi_max:
        return "high"
    if c2st_auc >= 0.55 or score_psi >= max(score_psi_max * 0.7, 0.10):
        return "moderate"
    if c2st_auc >= 0.52 or distribution_warning_ratio > 0.05:
        return "low"
    return "none"


def _predictive_degradation_level(
    *,
    auc_delta: float,
    brier_increase: float,
    calibration_gap_delta: float,
    auc_delta_max: float,
    brier_increase_max: float,
    calibration_gap_delta_max: float,
) -> str:
    metrics = (
        (auc_delta, auc_delta_max),
        (brier_increase, brier_increase_max),
        (calibration_gap_delta, calibration_gap_delta_max),
    )
    if _any_metric_crosses(metrics, multiplier=1.5, strict=False):
        return "severe"
    if _any_metric_crosses(metrics, multiplier=1.0, strict=True):
        return "high"
    if _any_metric_crosses(metrics, multiplier=0.75, strict=False):
        return "moderate"
    if any(value > 0.0 for value, _ in metrics):
        return "low"
    return "none"


def _any_metric_crosses(
    metrics: tuple[tuple[float, float], ...],
    *,
    multiplier: float,
    strict: bool,
) -> bool:
    for value, limit in metrics:
        threshold = limit * multiplier
        crosses = value > threshold if strict else value >= threshold
        if crosses:
            return True
    return False


def _shift_type(structural_level: str, predictive_level: str) -> str:
    if structural_level != "none" and predictive_level in {"none", "low"}:
        return "structural_shift_only"
    if structural_level == "none" and predictive_level != "none":
        return "predictive_degradation"
    if structural_level != "none" and predictive_level != "none":
        return "mixed_shift"
    return "stable"


def _governance_posture(shift_type: str, predictive_level: str) -> str:
    if shift_type == "mixed_shift" or predictive_level in {"high", "severe"}:
        return "candidate_gate"
    if shift_type == "structural_shift_only":
        return "warning_only"
    return "monitor"


def _pvalue_note(shift_type: str) -> str:
    if shift_type == "structural_shift_only":
        return (
            "KS/CvM or C2ST detect structural population change without clear predictive degradation. "
            "Treat this as representativeness pressure and monitoring, not an automatic retraining gate."
        )
    if shift_type == "predictive_degradation":
        return (
            "Predictive degradation is visible even without strong structural shift. "
            "Operational metrics dominate p-value interpretation in this case."
        )
    if shift_type == "mixed_shift":
        return (
            "Both structural shift and predictive degradation are present. "
            "This combination deserves the strongest governance posture."
        )
    return (
        "Distribution p-values are informative, but they can trigger on small effects at large N; "
        "the governance posture should be anchored on materiality, predictive loss, and C2ST/score shift."
    )
