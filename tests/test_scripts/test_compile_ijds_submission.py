from __future__ import annotations

from scripts.compile_ijds_submission import LatexScan, _windows_latexmk_script


def test_latex_scan_ok_property_flags_clean_build() -> None:
    scan = LatexScan(pages=27, blg_warnings=(), log_failures=())

    assert scan.ok


def test_latex_scan_ok_property_rejects_warnings_or_log_failures() -> None:
    assert not LatexScan(pages=27, blg_warnings=("Warning--empty journal",), log_failures=()).ok
    assert not LatexScan(pages=27, blg_warnings=(), log_failures=("undefined references",)).ok


def test_windows_latexmk_script_finds_tinytex_payload(tmp_path) -> None:
    wrapper = tmp_path / "TinyTeX" / "bin" / "windows" / "latexmk.exe"
    script = tmp_path / "TinyTeX" / "texmf-dist" / "scripts" / "latexmk" / "latexmk.pl"
    wrapper.parent.mkdir(parents=True)
    wrapper.touch()
    script.parent.mkdir(parents=True)
    script.touch()

    assert _windows_latexmk_script(wrapper) == script
