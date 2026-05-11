"""CRPTO — Conformal Robust Predict-Then-Optimize.

The package is named after the paper's core thesis: combine conformal
prediction with robust portfolio optimization. CRPTO is applied to credit
risk (Lending Club data) but the acronym itself refers to the
methodological pair, not to the domain.

Public API for the standalone Paper_CRPTO research pipeline. This top-level
``crpto`` package re-exports the most useful entry points from the internal
``src.*`` layout so external notebooks, the Quarto book and downstream
scripts can write::

    from crpto import PolicyMode, load_pipeline_state, make_study

instead of dipping into ``src.optimization.policy`` etc.

The underlying modules under ``src/`` remain the source of truth. This
package is a thin re-export layer — adding new public symbols here is the
recommended way to surface them to API consumers without leaking the
``src.`` prefix.
"""

from __future__ import annotations

# Feature config IO
from src.features.feature_config_io import (
    load_feature_config,
    pickle_to_yaml,
    save_feature_config,
)

# Conformal diagnostics (cheap, no model state)
from src.models.conformal_diagnostics import (
    summarize_prediction_sets,
    validate_coverage,
)

# Calibration
from src.models.venn_abers import VennAbersScoreCalibrator

# Optimization
from src.optimization.policy import (
    PolicyMode,
    all_policy_modes,
    resolve_policy_mode,
)

# MLflow helpers
from src.utils.mlflow_tracing import (
    PAPER_RUN_TAG,
    paper_run,
    register_parquet_dataset,
    set_paper_tags,
    trace,
)

# Optuna helpers
from src.utils.optuna_storage import make_storage, make_study

# Pipeline state aggregator
from src.utils.pipeline_state import (
    PipelineState,
    load_pipeline_state,
    write_pipeline_state,
)

__version__ = "0.1.0"

__all__ = [
    "PAPER_RUN_TAG",
    "PipelineState",
    "PolicyMode",
    "VennAbersScoreCalibrator",
    "__version__",
    "all_policy_modes",
    "load_feature_config",
    "load_pipeline_state",
    "make_storage",
    "make_study",
    "paper_run",
    "pickle_to_yaml",
    "register_parquet_dataset",
    "resolve_policy_mode",
    "save_feature_config",
    "set_paper_tags",
    "summarize_prediction_sets",
    "trace",
    "validate_coverage",
    "write_pipeline_state",
]
