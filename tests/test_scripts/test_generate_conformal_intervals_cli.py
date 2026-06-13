from __future__ import annotations

import pytest

from scripts.generate_conformal_intervals import (
    _parse_bool_tuple,
    _parse_float_tuple,
    _parse_int_tuple,
    _parse_str_tuple,
)


def test_conformal_cli_tuple_parsers_strip_and_cast_values() -> None:
    assert _parse_float_tuple("0.1, 0.05") == (0.1, 0.05)
    assert _parse_int_tuple("5, 10") == (5, 10)
    assert _parse_bool_tuple("true,false,1,0,yes,no,y,n") == (
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    )
    assert _parse_str_tuple("raw, calibrated ") == ("raw", "calibrated")


@pytest.mark.parametrize(
    "parser",
    [_parse_float_tuple, _parse_int_tuple, _parse_bool_tuple, _parse_str_tuple],
)
def test_conformal_cli_tuple_parsers_reject_empty_lists(parser) -> None:
    with pytest.raises(ValueError, match="Expected at least one"):
        parser(" , ")
