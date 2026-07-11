from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.cashflow_payoff import (
    exposure_weighted_undiscounted_snapshot_cash_yield,
    exposure_weighted_undiscounted_snapshot_cash_yield_difference,
    observed_undiscounted_snapshot_cash_yield,
)


def test_cash_yield_is_loan_level_and_funded_exposure_weighted() -> None:
    principal = np.array([100.0, 300.0])
    payments = np.array([120.0, 270.0])

    np.testing.assert_allclose(
        observed_undiscounted_snapshot_cash_yield(principal, payments),
        np.array([0.20, -0.10]),
    )
    assert exposure_weighted_undiscounted_snapshot_cash_yield(principal, payments) == pytest.approx(
        -0.025
    )


def test_cash_yield_difference_is_portfolio_a_minus_b() -> None:
    difference = exposure_weighted_undiscounted_snapshot_cash_yield_difference(
        np.array([100.0]),
        np.array([110.0]),
        np.array([200.0]),
        np.array([190.0]),
    )

    assert difference == pytest.approx(0.15)


@pytest.mark.parametrize(
    ("principal", "payments"),
    [
        ([0.0], [1.0]),
        ([-1.0], [1.0]),
        ([np.inf], [1.0]),
        ([1.0], [-1.0]),
        ([1.0], [np.nan]),
    ],
)
def test_cash_yield_rejects_invalid_observed_cash_inputs(
    principal: list[float],
    payments: list[float],
) -> None:
    with pytest.raises(ValueError):
        observed_undiscounted_snapshot_cash_yield(
            np.asarray(principal),
            np.asarray(payments),
        )
