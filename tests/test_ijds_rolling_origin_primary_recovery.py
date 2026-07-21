from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ijds_audit.allocations import declared_menu_counts
from src.ijds_audit.config import load_v4_config
from src.ijds_audit.rolling_origin_recovery import (
    EXPECTED_CENSUS,
    EXPECTED_MONTHLY_CENSUS,
    FORBIDDEN_FULL_PRIMARY_ROWS,
    PRIMARY_PERIODS,
    PROTOCOL_TAG,
    RUN_TAG,
    SOURCE_FREEZE_SHA256,
    select_primary_origin_scores,
    validate_primary_horizon_identity,
)
from src.utils.isolated_experiment import sha256_file

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT / "configs" / "experiments" / "ijds_rolling_origin_primary_recovery_2026-07-21_v1.yaml"
)
PROTOCOL = (
    ROOT / "docs" / "research" / "ijds_rolling_origin_primary_recovery_protocol_2026-07-21.md"
)
SOURCE_FREEZE = (
    ROOT
    / "models"
    / "experiments"
    / "ijds_audit"
    / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    / "protocol_freeze.json"
)
SOURCE_SCORES = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "ijds_audit"
    / "ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    / "prediction"
    / "scores.parquet"
)


def test_recovery_config_locks_the_common_three_month_horizon() -> None:
    config = load_v4_config(CONFIG)
    assert config["run_tag"] == RUN_TAG
    assert config["protocol_tag"] == PROTOCOL_TAG
    assert config["design"]["primary_oot_start_month"] == "2016-04"
    assert config["design"]["primary_oot_end_month"] == "2016-06"
    assert config["design"]["censored_extension_start_month"] == "2016-07"
    assert config["design"]["censored_extension_end_month"] == "2016-09"
    assert config["rolling_origin"]["origin_year"] == 2016
    assert config["rolling_origin"]["common_primary_months"] == 3
    assert config["rolling_origin"]["outcome_based_origin_selection"] is False
    assert config["rolling_origin"]["pooled_origin_claims"] is False
    assert config.get("endpoint_reason_recovery") is None
    assert config["resume_outcome_free"]["source_freeze_sha256"] == SOURCE_FREEZE_SHA256
    assert declared_menu_counts(config) == (11, 3)


def test_protocol_predeclares_identity_reconciliation_and_claim_boundary() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for token in (
        "{2016-04, 2016-05, 2016-06}",
        "74,537",
        "74,443",
        "376,890",
        "15-month",
        "eight recovered 2016 upper endpoints",
        "not preregistration",
        "selected-set conformal validity",
    ):
        assert token in text


def test_horizon_identity_accepts_only_the_reconciled_three_month_object() -> None:
    validate_primary_horizon_identity(
        candidate_rows=EXPECTED_CENSUS[0], observed_periods=PRIMARY_PERIODS
    )


def test_horizon_identity_rejects_the_historical_full_primary_count() -> None:
    with pytest.raises(RuntimeError, match="376,890-row/15-month"):
        validate_primary_horizon_identity(
            candidate_rows=FORBIDDEN_FULL_PRIMARY_ROWS,
            observed_periods=PRIMARY_PERIODS,
        )


def test_horizon_identity_rejects_any_fifteen_month_period_set() -> None:
    periods = tuple(pd.period_range("2016-04", periods=15, freq="M").astype(str))
    with pytest.raises(RuntimeError, match="376,890-row/15-month"):
        validate_primary_horizon_identity(
            candidate_rows=EXPECTED_CENSUS[0], observed_periods=periods
        )


def test_horizon_identity_rejects_a_nearby_but_wrong_three_month_set() -> None:
    with pytest.raises(RuntimeError, match="recovery periods changed"):
        validate_primary_horizon_identity(
            candidate_rows=EXPECTED_CENSUS[0],
            observed_periods=("2016-05", "2016-06", "2016-07"),
        )


def test_horizon_identity_rejects_a_wrong_nonhistorical_count() -> None:
    with pytest.raises(RuntimeError, match="candidate census changed"):
        validate_primary_horizon_identity(
            candidate_rows=EXPECTED_CENSUS[0] - 1,
            observed_periods=PRIMARY_PERIODS,
        )


def test_frozen_v4_scores_reconcile_to_the_locked_primary_census() -> None:
    if not SOURCE_FREEZE.is_file() or not SOURCE_SCORES.is_file():
        pytest.skip("DVC-fetched V4-v1 artifacts are unavailable.")
    assert sha256_file(SOURCE_FREEZE) == SOURCE_FREEZE_SHA256
    scores = pd.read_parquet(
        SOURCE_SCORES,
        columns=["id", "issue_d", "design_split", "pd_catboost_platt"],
    )
    selected = select_primary_origin_scores(scores)
    periods = pd.to_datetime(selected["issue_d"]).dt.to_period("M").astype(str)
    assert tuple(sorted(periods.unique())) == PRIMARY_PERIODS
    assert len(selected) == EXPECTED_CENSUS[0]
    assert periods.value_counts().sort_index().to_dict() == {
        month: counts[0] for month, counts in EXPECTED_MONTHLY_CENSUS.items()
    }
    assert selected["id"].is_unique


def test_score_selector_rejects_outcome_bearing_input_before_filtering() -> None:
    scores = pd.DataFrame(
        {
            "id": ["1"],
            "issue_d": [pd.Timestamp("2016-04-01")],
            "design_split": ["primary_oot"],
            "pd_catboost_platt": [0.1],
            "snapshot_default": [0],
        }
    )
    with pytest.raises(RuntimeError, match="Outcome columns entered"):
        select_primary_origin_scores(scores)
