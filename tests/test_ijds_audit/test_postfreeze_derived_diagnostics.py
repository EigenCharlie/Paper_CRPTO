from __future__ import annotations

import pandas as pd
import pytest

from src.ijds_audit.postfreeze_derived_diagnostics import (
    all_candidate_calibration_bias_table,
    minimum_reference_stratum_effect_table,
    resolved_coverage_breakeven_table,
)


def test_all_candidate_calibration_bounds_are_sharp_and_complete():
    scores = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "design_split": ["primary_oot"] * 4 + ["conformal_fit"],
            "pd_a": [0.05, 0.10, 0.15, 0.20, 0.99],
            "pd_b": [0.02, 0.08, 0.12, 0.18, 0.99],
        }
    )
    endpoint = pd.DataFrame(
        {
            "role": ["primary_oot"] * 5,
            "snapshot_resolution": [
                "charged_off_by_reconstructed_cutoff",
                "fully_paid_by_reconstructed_cutoff",
                "nonterminal_or_unresolved_status",
                "terminal_after_reconstructed_cutoff",
                "terminal_availability_date_missing",
            ],
            "candidate_rows": [1, 2, 1, 0, 0],
            "resolved_rows": [1, 2, 0, 0, 0],
            "unresolved_rows": [0, 0, 1, 0, 0],
        }
    )
    result = all_candidate_calibration_bias_table(
        scores,
        endpoint,
        score_columns={"a": "pd_a", "b": "pd_b"},
        expected_candidates=4,
        expected_resolved_y1=1,
        expected_unresolved=1,
    ).set_index("learner")
    assert result.loc["a", "mean_score"] == pytest.approx(0.125)
    assert result.loc["a", "mean_score_minus_outcome_lower"] == pytest.approx(-0.375)
    assert result.loc["a", "mean_score_minus_outcome_upper"] == pytest.approx(-0.125)
    assert result["mean_score_minus_outcome_upper"].lt(0.0).all()


def _breakeven_rows() -> pd.DataFrame:
    rows = []
    prevalence = 20 / 100
    for learner in ("a", "b"):
        for window in ("w1", "w2"):
            c0 = 0.98 if learner == "a" else 0.97
            c1 = 0.30 if window == "w1" else 0.35
            rows.append(
                {
                    "learner": learner,
                    "window_id": window,
                    "resolved_y0_rows": 80,
                    "resolved_y1_rows": 20,
                    "coverage_resolved_y0": c0,
                    "coverage_resolved_y1": c1,
                    "coverage_resolved": (1.0 - prevalence) * c0 + prevalence * c1,
                }
            )
    return pd.DataFrame(rows)


def test_resolved_breakeven_reconciles_every_cell():
    result = resolved_coverage_breakeven_table(
        _breakeven_rows(),
        learners=("a", "b"),
        window_ids=("w1", "w2"),
        alpha=0.10,
        expected_resolved_y0=80,
        expected_resolved_y1=20,
    )
    assert len(result) == 4
    assert result["mixture_identity_abs_residual"].max() == pytest.approx(0.0)
    assert result["breakeven_prevalence"].between(0.0, 1.0).all()


def test_resolved_breakeven_fails_on_a_drifted_mixture():
    table = _breakeven_rows()
    table.loc[0, "coverage_resolved"] += 1.0e-4
    with pytest.raises(RuntimeError, match="mixture identity"):
        resolved_coverage_breakeven_table(
            table,
            learners=("a", "b"),
            window_ids=("w1", "w2"),
            alpha=0.10,
            expected_resolved_y0=80,
            expected_resolved_y1=20,
        )


def test_minimum_reference_effect_uses_declared_tie_break():
    strata = pd.DataFrame(
        {
            "learner": ["a", "a", "a", "a"],
            "window_id": ["w1", "w1", "w2", "w2"],
            "conformal_group": [0, 1, 0, 1],
            "exact_log_p_value": [-2.0, -2.0, -3.0, -1.0],
            "miss_rate_min": [0.15, 0.20, 0.18, 0.16],
            "null_expected_miss_rate": [0.10, 0.10, 0.10, 0.10],
        }
    )
    cells = pd.DataFrame(
        {
            "learner": ["a", "a"],
            "window_id": ["w1", "w2"],
            "holm_reject_exchangeability_null": [False, True],
        }
    )
    result = minimum_reference_stratum_effect_table(
        strata,
        cells,
        learners=("a",),
        window_ids=("w1", "w2"),
        taxonomy_groups=2,
        expected_holm_flags=1,
    ).set_index("window_id")
    assert result.loc["w1", "minimum_reference_score_stratum"] == 1
    assert result.loc["w1", "minimum_reference_excess_miss_rate_pp"] == pytest.approx(5.0)
    assert result.loc["w2", "minimum_reference_score_stratum"] == 1
    assert result.loc["w2", "minimum_reference_excess_miss_rate_pp"] == pytest.approx(8.0)
