from __future__ import annotations

import pandas as pd
import pytest

from src.data.outcome_observability import (
    audit_outcome_label_availability,
    build_outcome_label_availability,
    parse_last_payment_dates,
    terminal_outcome_from_status,
    validate_minimum_label_retention,
)


def test_terminal_protocol_leaves_default_and_other_states_unresolved() -> None:
    statuses = pd.Series(
        [
            "Fully Paid",
            "Does not meet the credit policy. Status:Fully Paid",
            "Charged Off",
            "Does not meet the credit policy. Status:Charged Off",
            "Default",
            "Current",
        ]
    )

    outcome = terminal_outcome_from_status(statuses)

    assert outcome.iloc[:4].tolist() == [0, 0, 1, 1]
    assert outcome.iloc[4:].isna().all()


def test_last_payment_months_parse_conservatively_to_month_end() -> None:
    parsed = parse_last_payment_dates(pd.Series(["Jan-2017", "2017-02-15", pd.NA]))

    assert parsed.iloc[0] == pd.Timestamp("2017-01-31")
    assert parsed.iloc[1] == pd.Timestamp("2017-02-15")
    assert pd.isna(parsed.iloc[2])


def test_label_availability_respects_missing_dates_cutoff_and_chargeoff_lag() -> None:
    statuses = pd.Series(["Fully Paid", "Charged Off", "Charged Off", "Default"])
    last_payments = pd.Series(["Jan-2017", "Jan-2017", pd.NA, "Jan-2017"])

    before_lag = build_outcome_label_availability(
        statuses,
        last_payments,
        cutoff="2017-07-30",
        charged_off_lag_months=6,
    )
    at_lag = build_outcome_label_availability(
        statuses,
        last_payments,
        cutoff="2017-07-31",
        charged_off_lag_months=6,
    )

    assert before_lag["label_available"].tolist() == [True, False, False, False]
    assert at_lag["label_available"].tolist() == [True, True, False, False]
    assert at_lag.loc[1, "label_available_at"] == pd.Timestamp("2017-07-31")


def test_block_audit_counts_retention_and_strict_99_percent_gate() -> None:
    passing = pd.DataFrame(
        {
            "design_split": ["conformal_fit"] * 101,
            "loan_status": ["Fully Paid"] * 100 + ["Current"],
            "last_pymnt_d": ["Jan-2012"] * 101,
        }
    )
    audit = audit_outcome_label_availability(passing, cutoff="2013-01-31")

    assert audit.loc[0, "total_rows"] == 101
    assert audit.loc[0, "label_available_rows"] == 100
    assert audit.loc[0, "unresolved_outcome_rows"] == 1
    assert audit.loc[0, "retention_rate"] == pytest.approx(100 / 101)
    validate_minimum_label_retention(audit, minimum_retention=0.99)

    boundary = audit.copy()
    boundary.loc[0, "retention_rate"] = 0.99
    with pytest.raises(RuntimeError, match=r"must exceed 99\.00%"):
        validate_minimum_label_retention(boundary, minimum_retention=0.99)
