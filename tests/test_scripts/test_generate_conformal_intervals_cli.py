from __future__ import annotations

import pytest

from scripts.generate_conformal_intervals import (
    _parse_bool_tuple,
    _parse_float_tuple,
    _parse_int_tuple,
    _parse_str_tuple,
    _resolve_tuning_grid,
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


def test_resolve_tuning_grid_normalizes_candidates() -> None:
    grid = _resolve_tuning_grid(
        partition="grade",
        partition_candidates=(" grade ", "grade", "score_bin"),
        partition_probability_sources=(" RAW ", "calibrated", "raw"),
        n_score_bins_candidates=(0, 5, 5),
        fallback_modes=(" Grade_Then_Global ", "global", "global"),
        score_scale_families=(" None ", "bernoulli_sqrt", "none"),
        scaled_scores_options=(True, False),
    )

    assert grid.partition_candidates == ("grade", "score_bin")
    assert grid.partition_probability_sources == ("raw", "calibrated")
    assert grid.n_score_bins_candidates == (5, 5)
    assert grid.fallback_modes == ("grade_then_global", "global")
    assert grid.score_scale_families == ("none", "bernoulli_sqrt")
    assert grid.scaled_scores_options == (True, False)


def test_resolve_tuning_grid_uses_current_defaults_for_empty_inputs() -> None:
    grid = _resolve_tuning_grid(
        partition="",
        partition_candidates=None,
        partition_probability_sources=(),
        n_score_bins_candidates=(0,),
        fallback_modes=(),
        score_scale_families=(),
        scaled_scores_options=(),
    )

    assert grid.partition_candidates == ("grade",)
    assert grid.partition_probability_sources == ("raw",)
    assert grid.n_score_bins_candidates == (10,)
    assert grid.fallback_modes == ("grade_then_global",)
    assert grid.score_scale_families == ("none",)
    assert grid.scaled_scores_options == ()
