from __future__ import annotations

from scripts.search import run_conformal_search, run_portfolio_search


def test_retired_conformal_search_entrypoint_is_actionable(capsys) -> None:
    assert run_conformal_search.main([]) == 2

    captured = capsys.readouterr()
    assert "retired" in captured.err
    assert "run_conformal_reopen_search.py" in captured.err


def test_retired_portfolio_search_entrypoint_is_actionable(capsys) -> None:
    assert run_portfolio_search.main([]) == 2

    captured = capsys.readouterr()
    assert "retired" in captured.err
    assert "run_pool93_ijds_local_refinement.py" in captured.err
