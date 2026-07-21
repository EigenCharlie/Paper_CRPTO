from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.ijds_audit.conformal_set_diagnostics import (
    build_conformal_set_diagnostics,
    conformal_set_diagnostic_ranges,
)
from src.models.binary_conformal_guardrail import BinaryOutcomeConformalRecipe

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_conformal_set_diagnostics_2026-07-21_v1.yaml"


def _fixture_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scores = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d"],
            "issue_d": pd.to_datetime(["2016-04-01"] * 4),
            "design_split": ["primary_oot"] * 4,
            "pd_test": [0.1, 0.4, 0.6, 0.9],
        }
    )
    outcomes = pd.DataFrame({"id": ["a", "b", "c", "d"], "snapshot_default": [0.0, 0.0, 1.0, 1.0]})
    reference = pd.DataFrame(
        {
            "learner": ["test"],
            "window_id": ["w1"],
            "taxonomy_groups": [1],
            "role": ["primary_oot"],
            "conformal_group": [-1],
            "candidate_rows": [4],
            "resolved_rows": [4],
            "unresolved_rows": [0],
            "coverage_resolved": [0.5],
            "mean_width": [0.35],
            "set_empty_share": [0.5],
            "set_zero_only_share": [0.25],
            "set_one_only_share": [0.25],
            "set_both_share": [0.0],
        }
    )
    return scores, outcomes, reference


def _recipe() -> BinaryOutcomeConformalRecipe:
    return BinaryOutcomeConformalRecipe(
        alpha=0.1,
        requested_groups=1,
        bin_edges=(0.0, 1.0),
        residual_quantiles=(0.2,),
        group_counts=(10,),
        finite_sample_ranks=(10,),
        raw_finite_sample_ranks=(10,),
    )


def test_binary_set_diagnostics_reconcile_set_and_coverage_identities() -> None:
    scores, outcomes, reference = _fixture_frames()
    result = build_conformal_set_diagnostics(
        scores,
        outcomes,
        {"test": {"w1": {1: _recipe()}}},
        reference,
        learners=("test",),
        window_ids=("w1",),
        role="primary_oot",
        taxonomy_groups=1,
        expected_issue_months=("2016-04",),
        expected_candidates=4,
        expected_resolved=4,
        expected_unresolved=0,
        expected_resolved_y0=2,
        expected_resolved_y1=2,
    )
    row = result.iloc[0]
    assert row["coverage_resolved_y0"] == pytest.approx(0.5)
    assert row["coverage_resolved_y1"] == pytest.approx(0.5)
    assert row["average_set_size"] == pytest.approx(0.5)
    assert row["singleton_share"] == pytest.approx(0.5)
    assert row["set_empty_share"] == pytest.approx(0.5)
    assert row["singleton_share"] == pytest.approx(
        row["set_zero_only_share"] + row["set_one_only_share"]
    )
    assert row["average_set_size"] == pytest.approx(
        1.0 - row["set_empty_share"] + row["set_both_share"]
    )
    assert row["coverage_resolved"] == pytest.approx(
        (
            row["resolved_y0_rows"] * row["coverage_resolved_y0"]
            + row["resolved_y1_rows"] * row["coverage_resolved_y1"]
        )
        / row["resolved_rows"]
    )
    ranges = conformal_set_diagnostic_ranges(result)
    assert ranges == [
        {
            "learner": "test",
            "coverage_resolved_y0_min": 0.5,
            "coverage_resolved_y0_max": 0.5,
            "coverage_resolved_y1_min": 0.5,
            "coverage_resolved_y1_max": 0.5,
            "average_set_size_min": 0.5,
            "average_set_size_max": 0.5,
            "singleton_share_min": 0.5,
            "singleton_share_max": 0.5,
            "set_empty_share_min": 0.5,
            "set_empty_share_max": 0.5,
            "set_both_share_min": 0.0,
            "set_both_share_max": 0.0,
        }
    ]


def test_binary_set_diagnostics_reject_an_incomplete_issue_horizon() -> None:
    scores, outcomes, reference = _fixture_frames()
    with pytest.raises(RuntimeError, match="issue-month set changed"):
        build_conformal_set_diagnostics(
            scores,
            outcomes,
            {"test": {"w1": {1: _recipe()}}},
            reference,
            learners=("test",),
            window_ids=("w1",),
            role="primary_oot",
            taxonomy_groups=1,
            expected_issue_months=("2016-04", "2016-05"),
            expected_candidates=4,
            expected_resolved=4,
            expected_unresolved=0,
            expected_resolved_y0=2,
            expected_resolved_y1=2,
        )


def test_binary_set_diagnostics_reject_missing_endpoint_id_even_if_treated_unresolved() -> None:
    scores, outcomes, reference = _fixture_frames()
    with pytest.raises(RuntimeError, match="Endpoint alignment is incomplete"):
        build_conformal_set_diagnostics(
            scores,
            outcomes.iloc[:-1],
            {"test": {"w1": {1: _recipe()}}},
            reference,
            learners=("test",),
            window_ids=("w1",),
            role="primary_oot",
            taxonomy_groups=1,
            expected_issue_months=("2016-04",),
            expected_candidates=4,
            expected_resolved=3,
            expected_unresolved=1,
            expected_resolved_y0=2,
            expected_resolved_y1=1,
        )


def test_conformal_set_diagnostic_config_locks_the_complete_grid() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["protocol_tag"] == "protocol/ijds-conformal-set-diagnostics-2026-07-21-v1"
    assert len(config["design"]["learners"]) == 5
    assert len(config["design"]["window_ids"]) == 8
    assert config["design"]["issue_months"] == [
        str(period) for period in pd.period_range("2016-04", "2017-06", freq="M")
    ]
    assert config["design"]["expected_candidates"] == 376890
    assert config["source"]["raw_archive_sha256"] == (
        "5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f"
    )
    assert config["interpretation"] == {
        "learner_or_window_selected": False,
        "label_conditional_guarantee": False,
        "selected_set_guarantee": False,
        "funded_set_guarantee": False,
        "latent_pd_interval": False,
    }
