"""CLI contracts for versioned IJDS protocol entrypoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from scripts.experiments import (
    run_ijds_binary_geometry_frontier_v4 as binary_geometry,
    run_ijds_credit_risk_controls as credit_controls,
    run_ijds_normalized_objective_frontier_v2 as two_ruler,
    run_ijds_raw_data_audit as raw_data_audit,
)


@pytest.mark.parametrize(
    ("parser", "argv"),
    [
        (binary_geometry.parse_args, ["evaluate"]),
        (credit_controls.parse_args, ["evaluate"]),
        (two_ruler.parse_args, []),
        (raw_data_audit.parse_args, []),
    ],
)
def test_versioned_protocol_entrypoints_require_explicit_config(
    parser: Callable[[Sequence[str] | None], object],
    argv: list[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        parser(argv)

    assert error.value.code == 2
