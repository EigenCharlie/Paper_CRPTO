"""Shared semantics for the paper-facing funded-set decision certificate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

IJDS_DECLARED_ALPHA_GRID: tuple[float, ...] = (
    0.01,
    0.03,
    0.05,
    0.07,
    0.10,
    0.12,
    0.15,
    0.20,
)
IJDS_DECLARED_ALPHA_GRID_CSV = ",".join(f"{alpha:.2f}" for alpha in IJDS_DECLARED_ALPHA_GRID)


@dataclass(frozen=True)
class FundedCertificateMetrics:
    """Exact funded-set metrics and their policy-aware upper bounds.

    ``endpoint_budget`` and ``markov_loss_threshold`` are exact for the supplied
    funded weights. ``endpoint_budget_upper`` and ``markov_loss_cap`` additionally
    use the declared effective-PD constraint and its optional solver slack.
    """

    alpha: float
    risk_tolerance: float
    n_funded: int
    weighted_outcome: float
    weighted_miscoverage: float
    weighted_coverage: float
    empirical_coverage_funded: float
    weighted_pd_point: float
    weighted_pd_effective: float
    endpoint_budget: float
    gamma_cp: float
    gamma_internalized: float
    gamma_residual: float
    effective_constraint_slack: float
    effective_constraint_excess: float
    realized_risk_tolerance_excess: float
    sqrt_alpha: float
    endpoint_budget_upper: float
    markov_loss_threshold: float
    markov_loss_cap: float


def _one_dimensional_float_array(values: np.ndarray, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape={array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values.")
    return array


def _validate_probability_array(values: np.ndarray, *, name: str) -> None:
    tolerance = 1e-10
    if np.any(values < -tolerance) or np.any(values > 1.0 + tolerance):
        raise ValueError(f"{name} must stay on the [0, 1] probability scale.")


def compute_funded_certificate_metrics(
    weights: np.ndarray,
    outcomes: np.ndarray,
    pd_point: np.ndarray,
    pd_high: np.ndarray,
    pd_effective: np.ndarray,
    *,
    alpha: float,
    risk_tolerance: float,
    pd_cap_slack: float = 0.0,
    funded_tolerance: float = 1e-8,
) -> FundedCertificateMetrics:
    """Compute the exact and policy-aware funded-set certificate.

    The effective PD vector may come from any policy family. This is important
    for capped and tail-focused policies, where the linear-blend shortcut
    ``(1 - gamma) * Gamma_CP`` is not generally the residual endpoint premium.
    """
    arrays = {
        "weights": _one_dimensional_float_array(weights, name="weights"),
        "outcomes": _one_dimensional_float_array(outcomes, name="outcomes"),
        "pd_point": _one_dimensional_float_array(pd_point, name="pd_point"),
        "pd_high": _one_dimensional_float_array(pd_high, name="pd_high"),
        "pd_effective": _one_dimensional_float_array(pd_effective, name="pd_effective"),
    }
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1:
        shapes = {name: values.shape for name, values in arrays.items()}
        raise ValueError(f"Certificate arrays must have the same length: {shapes}")

    weights_arr = arrays["weights"]
    outcomes_arr = arrays["outcomes"]
    point_arr = arrays["pd_point"]
    high_arr = arrays["pd_high"]
    effective_arr = arrays["pd_effective"]
    if np.any(weights_arr < 0.0):
        raise ValueError("weights must be nonnegative.")
    weight_sum = float(weights_arr.sum())
    if not np.isclose(weight_sum, 1.0, rtol=0.0, atol=1e-8):
        raise ValueError(f"weights must sum to one, got {weight_sum:.12g}")

    for name, values in (
        ("outcomes", outcomes_arr),
        ("pd_point", point_arr),
        ("pd_high", high_arr),
        ("pd_effective", effective_arr),
    ):
        _validate_probability_array(values, name=name)
    order_tolerance = 1e-10
    if np.any(high_arr + order_tolerance < point_arr):
        raise ValueError("pd_high must be at least pd_point for every row.")
    if np.any(effective_arr + order_tolerance < point_arr) or np.any(
        effective_arr > high_arr + order_tolerance
    ):
        raise ValueError("pd_effective must lie between pd_point and pd_high.")

    alpha_value = float(alpha)
    if not 0.0 < alpha_value < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha_value}")
    tolerance_value = float(risk_tolerance)
    if not 0.0 <= tolerance_value <= 1.0:
        raise ValueError(f"risk_tolerance must lie in [0, 1], got {tolerance_value}")
    cap_slack = float(pd_cap_slack)
    if not np.isfinite(cap_slack) or cap_slack < 0.0:
        raise ValueError(f"pd_cap_slack must be finite and nonnegative, got {cap_slack}")

    funded = weights_arr > float(funded_tolerance)
    miscoverage = outcomes_arr > high_arr
    weighted_outcome = float(weights_arr @ outcomes_arr)
    weighted_miscoverage = float(weights_arr @ miscoverage.astype(float))
    weighted_point = float(weights_arr @ point_arr)
    weighted_effective = float(weights_arr @ effective_arr)
    endpoint_budget = float(weights_arr @ high_arr)
    gamma_cp = float(weights_arr @ np.clip(high_arr - point_arr, 0.0, 1.0))
    gamma_internalized = float(weights_arr @ np.clip(effective_arr - point_arr, 0.0, 1.0))
    gamma_residual = float(weights_arr @ np.clip(high_arr - effective_arr, 0.0, 1.0))
    if not np.isclose(
        gamma_cp,
        gamma_internalized + gamma_residual,
        rtol=0.0,
        atol=1e-9,
    ):
        raise ValueError("Conformal-premium decomposition is not internally consistent.")

    effective_cap = tolerance_value + cap_slack
    effective_constraint_slack = max(0.0, effective_cap - weighted_effective)
    effective_constraint_excess = max(0.0, weighted_effective - effective_cap)
    endpoint_budget_upper = effective_cap + gamma_residual
    sqrt_alpha = float(np.sqrt(alpha_value))
    empirical_coverage = float(1.0 - miscoverage[funded].mean()) if funded.any() else float("nan")

    return FundedCertificateMetrics(
        alpha=alpha_value,
        risk_tolerance=tolerance_value,
        n_funded=int(funded.sum()),
        weighted_outcome=weighted_outcome,
        weighted_miscoverage=weighted_miscoverage,
        weighted_coverage=1.0 - weighted_miscoverage,
        empirical_coverage_funded=empirical_coverage,
        weighted_pd_point=weighted_point,
        weighted_pd_effective=weighted_effective,
        endpoint_budget=endpoint_budget,
        gamma_cp=gamma_cp,
        gamma_internalized=gamma_internalized,
        gamma_residual=gamma_residual,
        effective_constraint_slack=effective_constraint_slack,
        effective_constraint_excess=effective_constraint_excess,
        realized_risk_tolerance_excess=max(0.0, weighted_outcome - tolerance_value),
        sqrt_alpha=sqrt_alpha,
        endpoint_budget_upper=endpoint_budget_upper,
        markov_loss_threshold=endpoint_budget + sqrt_alpha,
        markov_loss_cap=endpoint_budget_upper + sqrt_alpha,
    )


def add_policy_aware_bound_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add exact and policy-aware bound columns to alpha-grid evaluation rows.

    Historical pool93 evaluations already store the sufficient statistics for
    this decomposition. Rehydrating the bounds from those columns corrects
    capped/tail policy semantics without re-solving any portfolio.
    """
    required = {
        "alpha",
        "weighted_pd_high",
        "weighted_pd_constraint_used",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Bound-evaluation frame is missing required columns: {missing}")
    tolerance_column = "risk_tolerance" if "risk_tolerance" in frame.columns else "tau"
    if tolerance_column not in frame.columns:
        raise ValueError("Bound-evaluation frame requires risk_tolerance or tau.")

    work = frame.copy()
    if "realized_risk_tolerance_excess" not in work.columns and "violation" in work.columns:
        work["realized_risk_tolerance_excess"] = pd.to_numeric(
            work["violation"], errors="raise"
        ).astype(float)
    if (
        "empirical_risk_excess_leq_alpha" not in work.columns
        and "bound_a_expected_violation_leq_alpha" in work.columns
    ):
        work["empirical_risk_excess_leq_alpha"] = work[
            "bound_a_expected_violation_leq_alpha"
        ].astype(bool)
    alpha = pd.to_numeric(work["alpha"], errors="raise").astype(float)
    endpoint = pd.to_numeric(work["weighted_pd_high"], errors="raise").astype(float)
    effective = pd.to_numeric(work["weighted_pd_constraint_used"], errors="raise").astype(float)
    tolerance = pd.to_numeric(work[tolerance_column], errors="raise").astype(float)
    slack = (
        pd.to_numeric(work["pd_cap_slack"], errors="raise").astype(float)
        if "pd_cap_slack" in work.columns
        else pd.Series(0.0, index=work.index, dtype=float)
    )
    numeric = pd.concat(
        {
            "alpha": alpha,
            "endpoint": endpoint,
            "effective": effective,
            "tolerance": tolerance,
            "slack": slack,
        },
        axis=1,
    )
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Bound-evaluation frame contains non-finite certificate inputs.")
    if (alpha <= 0.0).any() or (alpha >= 1.0).any():
        raise ValueError("Bound-evaluation alpha values must lie in (0, 1).")
    if (slack < 0.0).any():
        raise ValueError("Bound-evaluation pd_cap_slack must be nonnegative.")

    residual = endpoint - effective
    if (residual < -1e-9).any():
        raise ValueError("weighted_pd_high must be at least weighted_pd_constraint_used.")
    residual = residual.clip(lower=0.0)
    effective_cap = tolerance + slack
    sqrt_alpha = np.sqrt(alpha)
    work["gamma_residual"] = residual
    if "weighted_pd_point" in work.columns:
        point = pd.to_numeric(work["weighted_pd_point"], errors="raise").astype(float)
        work["gamma_internalized"] = (effective - point).clip(lower=0.0)
    elif "gamma_cp" in work.columns:
        gamma_cp = pd.to_numeric(work["gamma_cp"], errors="raise").astype(float)
        work["gamma_internalized"] = (gamma_cp - residual).clip(lower=0.0)
    work["effective_constraint_slack"] = (effective_cap - effective).clip(lower=0.0)
    work["effective_constraint_excess"] = (effective - effective_cap).clip(lower=0.0)
    work["endpoint_budget"] = endpoint
    work["endpoint_budget_upper"] = effective_cap + residual
    work["markov_loss_threshold"] = endpoint + sqrt_alpha
    work["markov_loss_cap"] = work["endpoint_budget_upper"] + sqrt_alpha
    return work
