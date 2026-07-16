"""Small dataframe contracts for paper-facing evidence grids."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype
from pandas.testing import assert_frame_equal


def require_exact_grid(
    frame: pd.DataFrame,
    *,
    domains: Mapping[str, Sequence[Any]],
    label: str,
) -> None:
    """Require exactly one row for every declared Cartesian key."""
    keys = tuple(domains)
    missing_columns = sorted(set(keys).difference(frame.columns))
    if missing_columns:
        raise KeyError(f"{label} is missing grid keys: {missing_columns}.")
    if bool(frame.duplicated(list(keys)).any()):
        raise RuntimeError(f"{label} contains duplicate grid keys.")
    actual = set(frame.loc[:, list(keys)].itertuples(index=False, name=None))
    expected = set(product(*(domains[key] for key in keys)))
    if actual != expected:
        missing = sorted(expected.difference(actual), key=repr)[:5]
        extra = sorted(actual.difference(expected), key=repr)[:5]
        raise RuntimeError(f"{label} grid changed; missing={missing}, extra={extra}.")


def require_finite(frame: pd.DataFrame, columns: Sequence[str], *, label: str) -> None:
    """Reject missing, nonnumeric, NaN, or infinite paper-facing values."""
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise KeyError(f"{label} is missing numeric columns: {missing}.")
    values = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce").to_numpy()
    if not bool(np.isfinite(values).all()):
        raise RuntimeError(f"{label} contains nonfinite numeric evidence.")


def require_unique_row(
    frame: pd.DataFrame,
    *,
    key: Mapping[str, Any],
    label: str,
) -> pd.Series:
    """Return the single row matching named keys, independent of row order."""
    missing = sorted(set(key).difference(frame.columns))
    if missing:
        raise KeyError(f"{label} is missing lookup keys: {missing}.")
    mask = pd.Series(True, index=frame.index)
    for column, value in key.items():
        mask &= frame[column].eq(value)
    rows = frame.loc[mask]
    if len(rows) != 1:
        raise RuntimeError(f"{label} requires one row for {dict(key)}, found {len(rows)}.")
    return rows.iloc[0]


def require_unique_value(frame: pd.DataFrame, column: str, *, label: str) -> Any:
    """Return one nonmissing value only when it is constant over the frame."""
    if column not in frame:
        raise KeyError(f"{label} is missing column {column!r}.")
    values = frame[column].drop_duplicates()
    if len(values) != 1 or bool(values.isna().any()):
        raise RuntimeError(f"{label} has no unique nonmissing {column!r} value.")
    return values.iloc[0]


def require_exact_frame(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    *,
    keys: Sequence[str],
    label: str,
    float_atol: float = 0.0,
    float_rtol: float = 0.0,
    allowed_expected_extra_columns: Sequence[str] = (),
) -> None:
    """Require exact frames, optionally allowing declared float roundoff only."""
    if (
        not np.isfinite(float_atol)
        or not np.isfinite(float_rtol)
        or float_atol < 0.0
        or float_rtol < 0.0
        or float_atol > 1.0e-12
        or float_rtol > 1.0e-12
    ):
        raise ValueError("Frame float tolerances must be finite and at most 1e-12.")
    actual_columns = set(actual.columns)
    expected_columns = set(expected.columns)
    actual_only = actual_columns.difference(expected_columns)
    expected_only = expected_columns.difference(actual_columns)
    allowed_extras = set(allowed_expected_extra_columns)
    if actual_only or expected_only.difference(allowed_extras):
        raise RuntimeError(f"{label} columns differ from the active reference.")
    columns = [column for column in expected.columns if column in actual_columns]
    actual_sorted = (
        actual.loc[:, columns].sort_values(list(keys), kind="stable").reset_index(drop=True)
    )
    expected_sorted = (
        expected.loc[:, columns].sort_values(list(keys), kind="stable").reset_index(drop=True)
    )
    exact_columns = [
        column
        for column in columns
        if column in keys or not is_float_dtype(expected_sorted[column].dtype)
    ]
    float_columns = [column for column in columns if column not in exact_columns]
    try:
        if exact_columns:
            assert_frame_equal(
                actual_sorted.loc[:, exact_columns],
                expected_sorted.loc[:, exact_columns],
                check_exact=True,
                check_dtype=True,
                check_like=False,
            )
        if float_columns:
            assert_frame_equal(
                actual_sorted.loc[:, float_columns],
                expected_sorted.loc[:, float_columns],
                check_exact=float_atol == 0.0 and float_rtol == 0.0,
                check_dtype=True,
                check_like=False,
                atol=float_atol,
                rtol=float_rtol,
            )
    except AssertionError as error:
        raise RuntimeError(f"{label} does not reconcile exactly to active evidence.") from error
