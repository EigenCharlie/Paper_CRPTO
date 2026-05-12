"""Operations Research: portfolio optimization, robust optimization, SPO+."""

from src.optimization.policy import PolicyMode, all_policy_modes, resolve_policy_mode
from src.optimization.tail_satisficing_objective import (
    SatisficingMargin,
    SatisficingThreshold,
    TailSatisficingObjectiveResult,
    entropic_oce,
    evaluate_satisficing_margins,
    funded_loss_rate,
    normalize_weights,
    score_tail_satisficing_objective,
    weighted_cvar,
    weighted_mean,
)

__all__ = [
    "PolicyMode",
    "SatisficingMargin",
    "SatisficingThreshold",
    "TailSatisficingObjectiveResult",
    "all_policy_modes",
    "entropic_oce",
    "evaluate_satisficing_margins",
    "funded_loss_rate",
    "normalize_weights",
    "resolve_policy_mode",
    "score_tail_satisficing_objective",
    "weighted_cvar",
    "weighted_mean",
]
