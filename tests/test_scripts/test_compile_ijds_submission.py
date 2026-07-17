from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import scripts.compile_ijds_submission as submission_compiler
from scripts.compile_ijds_submission import (
    JOB_NAME,
    OFFICIAL_TEMPLATE_FILES,
    STYLE_MANIFEST,
    LatexScan,
    _missing_template_files,
    _template_asset_drift,
    _windows_latexmk_script,
    main,
    scan_submission_logs,
)


def _write_clean_submission_outputs(directory: Path, *, pages: str = "27") -> None:
    (directory / f"{JOB_NAME}.pdf").write_bytes(b"%PDF-1.7\n")
    (directory / f"{JOB_NAME}.blg").write_text("This is BibTeX\n", encoding="utf-8")
    (directory / f"{JOB_NAME}.log").write_text(
        f"Output written on {JOB_NAME}.pdf ({pages} pages, 12345 bytes).\n",
        encoding="utf-8",
    )


def test_latex_scan_ok_property_flags_clean_build() -> None:
    scan = LatexScan(pages=27, blg_warnings=(), log_failures=())

    assert scan.ok


def test_latex_scan_ok_property_rejects_warnings_or_log_failures() -> None:
    assert not LatexScan(pages=27, blg_warnings=("Warning--empty journal",), log_failures=()).ok
    assert not LatexScan(pages=27, blg_warnings=(), log_failures=("undefined references",)).ok


def test_latex_scan_ok_property_requires_outputs_and_positive_page_count() -> None:
    assert not LatexScan(pages=None, blg_warnings=(), log_failures=()).ok
    assert not LatexScan(pages=0, blg_warnings=(), log_failures=()).ok
    assert not LatexScan(
        pages=27,
        blg_warnings=(),
        log_failures=(),
        artifact_failures=("missing PDF",),
    ).ok


@pytest.mark.parametrize(
    ("suffix", "failure"),
    [
        ("pdf", "missing PDF"),
        ("log", "missing LaTeX log"),
        ("blg", "missing BibTeX log"),
    ],
)
def test_scan_rejects_each_missing_required_output(
    tmp_path: Path,
    suffix: str,
    failure: str,
) -> None:
    _write_clean_submission_outputs(tmp_path)
    (tmp_path / f"{JOB_NAME}.{suffix}").unlink()

    scan = scan_submission_logs(tmp_path)

    assert not scan.ok
    assert any(item.startswith(failure) for item in scan.artifact_failures)


@pytest.mark.parametrize(
    ("suffix", "failure"),
    [
        ("pdf", "empty PDF"),
        ("log", "empty LaTeX log"),
        ("blg", "empty BibTeX log"),
    ],
)
def test_scan_rejects_each_empty_required_output(
    tmp_path: Path,
    suffix: str,
    failure: str,
) -> None:
    _write_clean_submission_outputs(tmp_path)
    (tmp_path / f"{JOB_NAME}.{suffix}").write_bytes(b"")

    scan = scan_submission_logs(tmp_path)

    assert not scan.ok
    assert any(item.startswith(failure) for item in scan.artifact_failures)


def test_scan_rejects_unparseable_page_count(tmp_path: Path) -> None:
    _write_clean_submission_outputs(tmp_path, pages="unknown")

    scan = scan_submission_logs(tmp_path)

    assert scan.pages is None
    assert not scan.ok


def test_scan_rejects_nonpositive_page_count(tmp_path: Path) -> None:
    _write_clean_submission_outputs(tmp_path, pages="0")

    scan = scan_submission_logs(tmp_path)

    assert scan.pages == 0
    assert not scan.ok


def test_scan_accepts_complete_clean_outputs(tmp_path: Path) -> None:
    _write_clean_submission_outputs(tmp_path)

    scan = scan_submission_logs(tmp_path)

    assert scan.ok


def test_windows_latexmk_script_finds_tinytex_payload(tmp_path) -> None:
    wrapper = tmp_path / "TinyTeX" / "bin" / "windows" / "latexmk.exe"
    script = tmp_path / "TinyTeX" / "texmf-dist" / "scripts" / "latexmk" / "latexmk.pl"
    wrapper.parent.mkdir(parents=True)
    wrapper.touch()
    script.parent.mkdir(parents=True)
    script.touch()

    assert _windows_latexmk_script(wrapper) == script


def test_missing_template_files_reports_only_absent_assets(tmp_path) -> None:
    for name in OFFICIAL_TEMPLATE_FILES[:2]:
        (tmp_path / name).touch()

    assert _missing_template_files(tmp_path) == OFFICIAL_TEMPLATE_FILES[2:]


def test_style_manifest_tracks_the_complete_publisher_asset_set() -> None:
    payload = json.loads(STYLE_MANIFEST.read_text(encoding="utf-8"))

    assert set(payload["assets"]) == set(OFFICIAL_TEMPLATE_FILES)
    assert payload["informs4_class_version"] == "2024/06/03 v1.02"


def test_style_manifest_detects_tampered_publisher_asset(tmp_path) -> None:
    assets = {}
    for name in OFFICIAL_TEMPLATE_FILES:
        content = f"reviewed {name}\n".encode()
        (tmp_path / name).write_bytes(content)
        assets[name] = {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    (tmp_path / STYLE_MANIFEST.name).write_text(
        json.dumps({"assets": assets}),
        encoding="utf-8",
    )

    assert _template_asset_drift(tmp_path) == ()
    (tmp_path / OFFICIAL_TEMPLATE_FILES[0]).write_bytes(b"tampered")

    assert _template_asset_drift(tmp_path) == (OFFICIAL_TEMPLATE_FILES[0],)


def test_official_template_starts_references_on_a_new_page() -> None:
    template = STYLE_MANIFEST.parent / "informs-pandoc-template.tex"

    assert "\\clearpage\n\\bibliographystyle" in template.read_text(encoding="utf-8")


def test_scan_only_rejects_redundant_skip_render() -> None:
    with pytest.raises(SystemExit) as error:
        main(["--scan-only", "--skip-render"])

    assert error.value.code == 2


def test_scan_only_fails_when_required_outputs_are_missing(tmp_path: Path, monkeypatch) -> None:
    _write_clean_submission_outputs(tmp_path)
    (tmp_path / f"{JOB_NAME}.pdf").unlink()
    monkeypatch.setattr(submission_compiler, "SUBMISSION_DIR", tmp_path)

    assert main(["--scan-only"]) == 1


def test_post_compile_validation_fails_when_page_count_is_unparseable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_clean_submission_outputs(tmp_path, pages="unknown")
    monkeypatch.setattr(submission_compiler, "SUBMISSION_DIR", tmp_path)
    monkeypatch.setattr(submission_compiler, "compile_submission", lambda **_: 0)

    assert main([]) == 1
