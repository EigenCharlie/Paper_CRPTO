"""Small dataframe contracts for paper-facing evidence grids."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
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
) -> None:
    """Require value-, dtype-, column-, and key-exact dataframe equality."""
    if set(actual.columns) != set(expected.columns):
        raise RuntimeError(f"{label} columns differ from the active reference.")
    columns = list(expected.columns)
    actual_sorted = (
        actual.loc[:, columns].sort_values(list(keys), kind="stable").reset_index(drop=True)
    )
    expected_sorted = (
        expected.loc[:, columns].sort_values(list(keys), kind="stable").reset_index(drop=True)
    )
    try:
        assert_frame_equal(
            actual_sorted,
            expected_sorted,
            check_exact=True,
            check_dtype=True,
            check_like=False,
        )
    except AssertionError as error:
        raise RuntimeError(f"{label} does not reconcile exactly to active evidence.") from error
