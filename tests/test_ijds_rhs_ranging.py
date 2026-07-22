from __future__ import annotations

from typing import Any, cast

import highspy
import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.portfolio import PointPortfolioSession
from src.ijds_audit.rhs_ranging import interpret_upper_only_rhs_ranging


def _synthetic_session() -> PointPortfolioSession:
    frame = pd.DataFrame(
        {
            "loan_amnt": [60.0, 50.0, 40.0, 30.0],
            "purpose": ["a", "a", "b", "b"],
        }
    )
    return PointPortfolioSession(
        frame,
        point_score=np.array([0.03, 0.07, 0.10, 0.14]),
        objective_rate=np.array([0.01, 0.03, 0.06, 0.10]),
        budget=100.0,
        purpose_cap=0.6,
    )


def test_upper_status_uses_raw_ranging_as_effective_rhs_range() -> None:
    interpreted = interpret_upper_only_rhs_ranging(
        row_status=highspy.HighsBasisStatus.kUpper,
        row_value=8.0,
        row_dual=-2.0,
        raw_bound_down=7.0,
        raw_bound_up=8.4,
        domain_upper=100.0,
        basic_dual_tolerance=1.0e-12,
    )

    assert interpreted.basis_status == "kUpper"
    assert interpreted.raw_activity_lower == 7.0
    assert interpreted.raw_activity_upper == 8.4
    assert interpreted.effective_rhs_lower == 7.0
    assert interpreted.effective_rhs_upper == 8.4


def test_basic_status_preserves_raw_activity_but_extends_effective_rhs_to_domain() -> None:
    interpreted = interpret_upper_only_rhs_ranging(
        row_status=highspy.HighsBasisStatus.kBasic,
        row_value=10.0,
        row_dual=0.0,
        raw_bound_down=8.4,
        raw_bound_up=10.0,
        domain_upper=100.0,
        basic_dual_tolerance=1.0e-12,
    )

    assert interpreted.basis_status == "kBasic"
    assert interpreted.raw_activity_lower == 8.4
    assert interpreted.raw_activity_upper == 10.0
    assert interpreted.effective_rhs_lower == 10.0
    assert interpreted.effective_rhs_upper == 100.0


@pytest.mark.parametrize(
    "status",
    [
        highspy.HighsBasisStatus.kLower,
        highspy.HighsBasisStatus.kZero,
        highspy.HighsBasisStatus.kNonbasic,
        cast(Any, "kUpper"),
    ],
)
def test_unsupported_upper_only_row_statuses_fail_closed(status: Any) -> None:
    with pytest.raises(RuntimeError, match="expected kUpper or kBasic"):
        interpret_upper_only_rhs_ranging(
            row_status=status,
            row_value=10.0,
            row_dual=0.0,
            raw_bound_down=8.4,
            raw_bound_up=10.0,
            domain_upper=100.0,
            basic_dual_tolerance=1.0e-12,
        )


def test_basic_status_with_nonzero_dual_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="requires a zero dual certificate"):
        interpret_upper_only_rhs_ranging(
            row_status=highspy.HighsBasisStatus.kBasic,
            row_value=10.0,
            row_dual=1.1e-12,
            raw_bound_down=8.4,
            raw_bound_up=10.0,
            domain_upper=100.0,
            basic_dual_tolerance=1.0e-12,
        )


def test_synthetic_active_upper_row_retains_raw_effective_semantics() -> None:
    solution = _synthetic_session().solve(0.08)

    assert solution.risk_row_basis_status == "kUpper"
    assert solution.weighted_point_score == pytest.approx(0.08)
    assert solution.basis_cap_lower == pytest.approx(solution.basis_activity_lower)
    assert solution.basis_cap_upper == pytest.approx(solution.basis_activity_upper)
    assert solution.basis_cap_lower <= 0.08 <= solution.basis_cap_upper


def test_synthetic_slack_basic_row_uses_activity_to_domain_effective_range() -> None:
    solution = _synthetic_session().solve(1.0)

    assert solution.risk_row_basis_status == "kBasic"
    assert solution.weighted_point_score == pytest.approx(0.10)
    assert solution.basis_activity_lower == pytest.approx(0.084)
    assert solution.basis_activity_upper == pytest.approx(0.10)
    assert solution.basis_cap_lower == pytest.approx(solution.weighted_point_score)
    assert solution.basis_cap_upper == pytest.approx(1.0)
    assert solution.basis_activity_upper < solution.basis_cap_upper
