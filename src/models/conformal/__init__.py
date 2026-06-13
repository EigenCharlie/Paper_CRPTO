"""Public facade for conformal prediction utilities.

The implementation lives in focused submodules, but the stable public import
path remains ``src.models.conformal`` for scripts, tests, and old pickles.
"""

from __future__ import annotations

from src.models.conformal._scores import (
    _compute_score_scale,
    _conformal_quantile,
    _resolve_score_scale_family,
)
from src.models.conformal.classification import (
    build_mondrian_partition_labels,
    create_classification_sets,
    create_classification_sets_mondrian,
    create_cross_conformal_score_intervals,
)
from src.models.conformal.pd_intervals import (
    apply_probability_calibrator,
    conditional_coverage_by_group,
    create_pd_intervals,
    create_pd_intervals_mondrian,
    create_pd_intervals_venn_abers,
)
from src.models.conformal.regression import (
    create_regression_intervals,
    create_residual_intervals,
)
from src.models.conformal_adapters import (
    PrefitCalibratedClassifierAdapter,
    PrefitClassifierAdapter,
    ProbabilityRegressor,
)
from src.models.conformal_diagnostics import (
    summarize_prediction_sets,
    validate_coverage,
)

__all__ = [
    "PrefitCalibratedClassifierAdapter",
    "PrefitClassifierAdapter",
    "ProbabilityRegressor",
    "_compute_score_scale",
    "_conformal_quantile",
    "_resolve_score_scale_family",
    "apply_probability_calibrator",
    "build_mondrian_partition_labels",
    "conditional_coverage_by_group",
    "create_classification_sets",
    "create_classification_sets_mondrian",
    "create_cross_conformal_score_intervals",
    "create_pd_intervals",
    "create_pd_intervals_mondrian",
    "create_pd_intervals_venn_abers",
    "create_regression_intervals",
    "create_residual_intervals",
    "summarize_prediction_sets",
    "validate_coverage",
]
