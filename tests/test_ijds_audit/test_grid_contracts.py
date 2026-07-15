"""Mutation tests for paper-facing Cartesian evidence contracts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.grid_contracts import (
    require_exact_grid,
    require_finite,
    require_unique_row,
    require_unique_value,
)


def _grid() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "learner": ["a", "a", "b", "b"],
            "window": [1, 2, 1, 2],
            "value": [0.1, 0.2, 0.3, 0.4],
            "constant": [7, 7, 7, 7],
        }
    )


def test_exact_grid_is_order_invariant_and_keyed() -> None:
    frame = _grid().sample(frac=1.0, random_state=7)

    require_exact_grid(
        frame,
        domains={"learner": ("a", "b"), "window": (1, 2)},
        label="test grid",
    )
    row = require_unique_row(frame, key={"learner": "b", "window": 2}, label="test row")
    assert row["value"] == pytest.approx(0.4)
    assert require_unique_value(frame, "constant", label="test constant") == 7


def test_exact_grid_rejects_duplicate_replacing_missing_key() -> None:
    mutated = pd.concat([_grid().iloc[:-1], _grid().iloc[[0]]], ignore_index=True)

    with pytest.raises(RuntimeError, match="duplicate grid keys"):
        require_exact_grid(
            mutated,
            domains={"learner": ("a", "b"), "window": (1, 2)},
            label="test grid",
        )


def test_exact_grid_rejects_missing_or_extra_key() -> None:
    with pytest.raises(RuntimeError, match="grid changed"):
        require_exact_grid(
            _grid().iloc[:-1],
            domains={"learner": ("a", "b"), "window": (1, 2)},
            label="test grid",
        )

    extra = pd.concat(
        [_grid(), pd.DataFrame({"learner": ["c"], "window": [1], "value": [0.5]})],
        ignore_index=True,
    )
    with pytest.raises(RuntimeError, match="grid changed"):
        require_exact_grid(
            extra,
            domains={"learner": ("a", "b"), "window": (1, 2)},
            label="test grid",
        )


def test_finite_and_unique_value_contracts_reject_silent_corruption() -> None:
    nonfinite = _grid()
    nonfinite.loc[1, "value"] = np.inf
    with pytest.raises(RuntimeError, match="nonfinite"):
        require_finite(nonfinite, ("value",), label="test values")

    nonconstant = _grid()
    nonconstant.loc[1, "constant"] = 8
    with pytest.raises(RuntimeError, match="no unique"):
        require_unique_value(nonconstant, "constant", label="test constant")
