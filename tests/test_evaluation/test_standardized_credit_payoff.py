from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.standardized_credit_payoff import (
    expected_objective_coefficients,
    realized_standardized_payoff_bounds,
)


def test_expected_objective_coefficients_use_coherent_payoff() -> None:
    coefficients = expected_objective_coefficients(
        np.array([0.0, 1.0, 0.2]),
        np.array([0.1, 0.1, 0.2]),
        lgd=0.45,
    )

    np.testing.assert_allclose(coefficients, np.array([0.1, -0.45, 0.07]))


@pytest.mark.parametrize(
    ("probability", "rate", "lgd"),
    [
        (np.nan, 0.1, 0.45),
        (1.01, 0.1, 0.45),
        (0.1, np.inf, 0.45),
        (0.1, -0.01, 0.45),
        (0.1, 0.1, np.nan),
        (0.1, 0.1, 1.01),
    ],
)
def test_expected_objective_rejects_invalid_inputs(
    probability: float,
    rate: float,
    lgd: float,
) -> None:
    with pytest.raises(ValueError):
        expected_objective_coefficients(
            np.array([probability]),
            np.array([rate]),
            lgd=lgd,
        )


def test_realized_bounds_reject_infinite_outcomes_and_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="binary or NaN"):
        realized_standardized_payoff_bounds(
            np.array([np.inf]),
            np.array([0.1]),
            lgd=0.45,
        )
    with pytest.raises(ValueError, match="Contractual rates"):
        realized_standardized_payoff_bounds(
            np.array([0.0]),
            np.array([1.1]),
            lgd=0.45,
        )
    with pytest.raises(ValueError, match="LGD"):
        realized_standardized_payoff_bounds(
            np.array([0.0]),
            np.array([0.1]),
            lgd=-0.1,
        )
