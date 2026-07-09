from __future__ import annotations

from scripts.compile_ijds_submission import LatexScan


def test_latex_scan_ok_property_flags_clean_build() -> None:
    scan = LatexScan(pages=27, blg_warnings=(), log_failures=())

    assert scan.ok


def test_latex_scan_ok_property_rejects_warnings_or_log_failures() -> None:
    assert not LatexScan(pages=27, blg_warnings=("Warning--empty journal",), log_failures=()).ok
    assert not LatexScan(pages=27, blg_warnings=(), log_failures=("undefined references",)).ok
