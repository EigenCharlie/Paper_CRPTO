"""Status-aware interpretation of HiGHS ranging for upper-only rows."""

from __future__ import annotations

import math
from dataclasses import dataclass

import highspy


@dataclass(frozen=True)
class UpperOnlyRhsRange:
    """Raw row-activity ranging and the effective upper-RHS interval.

    HiGHS reports ``row_bound_dn`` and ``row_bound_up`` for the current
    basis.  For an upper-only row at its upper bound, those values are the
    effective RHS range.  When the row is basic (and therefore slack), they
    instead describe the row-activity range of the current basis: any upper
    RHS from the current activity through the declared domain upper bound
    leaves that slack row feasible.
    """

    basis_status: str
    raw_activity_lower: float
    raw_activity_upper: float
    effective_rhs_lower: float
    effective_rhs_upper: float


def interpret_upper_only_rhs_ranging(
    *,
    row_status: highspy.HighsBasisStatus,
    row_value: float,
    row_dual: float,
    raw_bound_down: float,
    raw_bound_up: float,
    domain_upper: float,
    basic_dual_tolerance: float,
) -> UpperOnlyRhsRange:
    """Interpret one HiGHS range record for a row with only an upper bound.

    Unsupported basis statuses fail closed.  In particular, treating a basic
    (slack) row's raw activity range as an RHS interval would incorrectly
    exclude every looser cap above the current activity.
    """

    activity = float(row_value)
    dual = float(row_dual)
    raw_lower = float(raw_bound_down)
    raw_upper = float(raw_bound_up)
    upper = float(domain_upper)
    dual_tolerance = float(basic_dual_tolerance)
    if not all(math.isfinite(value) for value in (activity, dual, upper, dual_tolerance)):
        raise ValueError("row_value, row_dual, domain_upper, and tolerance must be finite.")
    if dual_tolerance < 0.0:
        raise ValueError("basic_dual_tolerance cannot be negative.")
    if math.isnan(raw_lower) or math.isnan(raw_upper) or raw_lower > raw_upper:
        raise ValueError("HiGHS returned an invalid raw row-activity range.")

    if row_status == highspy.HighsBasisStatus.kUpper:
        effective_lower = raw_lower
        effective_upper = raw_upper
    elif row_status == highspy.HighsBasisStatus.kBasic:
        if activity > upper:
            raise ValueError("A basic upper-only row has activity above the RHS domain.")
        if abs(dual) > dual_tolerance:
            raise RuntimeError(
                "A basic upper-only row requires a zero dual certificate before "
                "its feasible RHS ray can be treated as optimal."
            )
        effective_lower = activity
        effective_upper = upper
    else:
        raise RuntimeError(
            "Unsupported basis status for an upper-only RHS row: "
            f"{row_status!r}; expected kUpper or kBasic."
        )

    if effective_lower > effective_upper:
        raise ValueError("The effective upper-only RHS range is reversed.")
    return UpperOnlyRhsRange(
        basis_status=row_status.name,
        raw_activity_lower=raw_lower,
        raw_activity_upper=raw_upper,
        effective_rhs_lower=effective_lower,
        effective_rhs_upper=effective_upper,
    )
