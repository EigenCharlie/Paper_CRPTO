from __future__ import annotations

import pandas as pd
import pytest

from src.data.make_dataset import initial_clean
from src.data.prepare_dataset import require_observed_binary_target


def _snapshot_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "loan_status": [
                "Fully Paid",
                "Does not meet the credit policy. Status:Fully Paid",
                "Charged Off",
                "Does not meet the credit policy. Status:Charged Off",
                "Default",
                "Current",
                "Late (31-120 days)",
            ],
            "loan_amnt": [1_000.0] * 7,
            "issue_d": ["Jan-2016"] * 7,
            "last_pymnt_d": ["Jan-2017"] * 7,
        }
    )


def test_initial_clean_retains_unresolved_candidate_universe() -> None:
    cleaned = initial_clean(_snapshot_fixture())

    assert len(cleaned) == 7
    assert cleaned["default_flag"].tolist()[:5] == [0, 0, 1, 1, 1]
    assert cleaned["default_flag"].iloc[5:].isna().all()
    assert cleaned["outcome_observed"].tolist() == [True] * 5 + [False, False]
    assert cleaned["lgd"].tolist()[:5] == [0.0, 0.0, 1.0, 1.0, 1.0]
    assert cleaned["lgd"].iloc[5:].isna().all()
    assert "last_pymnt_d" not in cleaned.columns


def test_legacy_resolved_filter_requires_explicit_opt_in() -> None:
    cleaned = initial_clean(_snapshot_fixture(), legacy_resolved_only=True)

    assert len(cleaned) == 5
    assert cleaned["default_flag"].notna().all()


def test_split_builder_refuses_implicit_status_filtering() -> None:
    frame = pd.DataFrame({"default_flag": pd.Series([0, 1, pd.NA], dtype="Int8")})

    with pytest.raises(RuntimeError, match="unresolved outcomes"):
        require_observed_binary_target(frame)


def test_split_builder_accepts_declared_binary_labels() -> None:
    require_observed_binary_target(pd.DataFrame({"default_flag": [0, 1, 0]}))
