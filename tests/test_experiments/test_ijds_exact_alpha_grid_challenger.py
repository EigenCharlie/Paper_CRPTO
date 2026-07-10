from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.experiments.run_ijds_exact_alpha_grid_challenger import (
    _base_grid_frame,
    _replay_differences,
)
from src.models.conformal_alpha_grid import ExactAlphaIntervals


def _result() -> ExactAlphaIntervals:
    return ExactAlphaIntervals(
        target_alpha=0.10,
        used_alpha=0.095,
        point=np.array([0.2, 0.4]),
        low=np.array([0.0, 0.1]),
        high=np.array([0.5, 0.8]),
        partition_labels=pd.Series(["a", "b"]),
        partition_metadata={},
        diagnostics={},
    )


def test_base_grid_keeps_only_traceability_columns() -> None:
    source = pd.DataFrame(
        {
            "_row_number": [0],
            "id": ["x"],
            "y_true": [0.0],
            "grade": ["A"],
            "pd_high_90": [0.5],
        }
    )

    assert _base_grid_frame(source).columns.tolist() == [
        "_row_number",
        "id",
        "y_true",
        "grade",
    ]


def test_reference_replay_reports_exact_match() -> None:
    source = pd.DataFrame(
        {
            "y_pred": [0.2, 0.4],
            "pd_low_90": [0.0, 0.1],
            "pd_high_90": [0.5, 0.8],
        }
    )

    assert _replay_differences(_result(), source) == {
        "point_max_abs": 0.0,
        "low_max_abs": 0.0,
        "high_max_abs": 0.0,
    }
