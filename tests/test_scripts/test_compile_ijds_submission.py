from __future__ import annotations

import hashlib
import json

from scripts.compile_ijds_submission import (
    OFFICIAL_TEMPLATE_FILES,
    STYLE_MANIFEST,
    LatexScan,
    _missing_template_files,
    _template_asset_drift,
    _windows_latexmk_script,
)


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
