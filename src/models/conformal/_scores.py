"""Score-space helpers shared by conformal interval builders."""

from __future__ import annotations

import numpy as np


def _conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """Finite-sample conformal quantile with ``higher`` interpolation."""
    scores = np.asarray(scores, dtype=float)
    if scores.size == 0:
        return 0.0
    n = scores.size
    q_level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(scores, q_level, method="higher"))


def _resolve_score_scale_family(*, scaled_scores: bool, score_scale_family: str | None) -> str:
    family = str(score_scale_family or "").strip().lower()
    if family in {"", "auto"}:
        family = "bernoulli_sqrt" if scaled_scores else "none"
    valid = {
        "none",
        "bernoulli_sqrt",
        "bernoulli_sqrt_clipped_0.02",
        "bernoulli_sqrt_clipped_0.05",
    }
    if family not in valid:
        raise ValueError(f"Unsupported score_scale_family: {score_scale_family}")
    return family


def _compute_score_scale(y_prob: np.ndarray, score_scale_family: str) -> np.ndarray:
    y_prob_arr = np.clip(np.asarray(y_prob, dtype=float), 1e-6, 1.0 - 1e-6)
    if score_scale_family == "none":
        return np.ones_like(y_prob_arr)
    if score_scale_family == "bernoulli_sqrt":
        return np.asarray(np.sqrt(np.clip(y_prob_arr * (1.0 - y_prob_arr), 1e-6, None)))
    if score_scale_family == "bernoulli_sqrt_clipped_0.02":
        clipped = np.clip(y_prob_arr, 0.02, 0.98)
        return np.asarray(np.sqrt(np.clip(clipped * (1.0 - clipped), 1e-6, None)))
    if score_scale_family == "bernoulli_sqrt_clipped_0.05":
        clipped = np.clip(y_prob_arr, 0.05, 0.95)
        return np.asarray(np.sqrt(np.clip(clipped * (1.0 - clipped), 1e-6, None)))
    raise ValueError(f"Unsupported score_scale_family: {score_scale_family}")
