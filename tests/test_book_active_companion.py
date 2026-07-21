"""Static contracts for the active three-page Quarto companion."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.ijds_audit.publication_sources import load_source_registry

REPO = Path(__file__).resolve().parents[1]
BOOK = REPO / "book"
ACTIVE_CHAPTERS = (
    "chapters/06-blueprint-manuscrito.qmd",
    "chapters/06b-guia-editorial-claims.qmd",
)
HISTORICAL_MARKER = "<!-- crpto-companion-status: retired-historical-source -->"
SPANISH_ESTIMAND_BOUNDARY = (
    "cobertura de $Y$ binario observado",
    "PD latente individual",
    "ECL",
    "SICR",
    "expected loss",
    "policy seleccionada",
)
ENGLISH_ESTIMAND_BOUNDARY = (
    "Coverage of observed binary $Y$",
    "latent individual PD",
    "ECL",
    "SICR",
    "expected loss",
    "selected allocation policy",
)


def _config() -> dict:
    return yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))


def _assert_local_file(path: str) -> None:
    candidate = (BOOK / path).resolve()
    assert candidate.is_file(), candidate


def _registered_pages(config: dict) -> list[str]:
    pages: list[str] = []
    for entry in config["book"]["chapters"]:
        if isinstance(entry, str):
            pages.append(entry)
        else:
            pages.extend(entry["chapters"])
    return pages


def test_active_companion_configuration_has_no_missing_local_dependencies() -> None:
    config = _config()
    chapters = _registered_pages(config)
    assert chapters == [
        "index.qmd",
        "chapters/06-blueprint-manuscrito.qmd",
        "chapters/06b-guia-editorial-claims.qmd",
        "references.qmd",
    ]

    local_dependencies = [
        *chapters,
        config["bibliography"],
        config["csl"],
        config["book"]["favicon"],
        config["book"]["sidebar"]["logo"],
        config["format"]["html"]["include-after-body"],
        config["format"]["pdf"]["include-in-header"],
    ]
    for dependency in local_dependencies:
        _assert_local_file(dependency)

    index = (BOOK / "index.qmd").read_text(encoding="utf-8")
    for include in re.findall(r"\{\{<\s+include\s+([^\s>]+)\s*>}}", index):
        _assert_local_file(include)


def test_every_unregistered_chapter_is_marked_as_historical_source() -> None:
    registered = set(_registered_pages(_config()))
    active_chapters = {BOOK / path for path in ACTIVE_CHAPTERS}
    assert active_chapters == {
        path
        for path in (BOOK / "chapters").glob("*.qmd")
        if path.relative_to(BOOK).as_posix() in registered
    }

    inactive_chapters = sorted(set((BOOK / "chapters").glob("*.qmd")) - active_chapters)
    assert inactive_chapters
    contract = (BOOK / "chapters/README.md").read_text(encoding="utf-8")
    for path in inactive_chapters:
        text = path.read_text(encoding="utf-8")
        assert text.count(HISTORICAL_MARKER) == 1, path
        assert path.name in contract, path

    for path in active_chapters:
        assert HISTORICAL_MARKER not in path.read_text(encoding="utf-8"), path


def test_active_surfaces_state_the_observed_outcome_estimand_boundary() -> None:
    for path in (
        BOOK / "index.qmd",
        BOOK / "chapters/06-blueprint-manuscrito.qmd",
        BOOK / "chapters/06b-guia-editorial-claims.qmd",
    ):
        text = path.read_text(encoding="utf-8")
        for phrase in SPANISH_ESTIMAND_BOUNDARY:
            assert phrase in text, (path, phrase)

    body = (REPO / "paper/CRPTO_ijds.qmd").read_text(encoding="utf-8")
    for phrase in ENGLISH_ESTIMAND_BOUNDARY:
        assert phrase in body, phrase


def test_active_companion_matches_supplement_and_registry_structure() -> None:
    index = (BOOK / "index.qmd").read_text(encoding="utf-8")
    blueprint = (BOOK / "chapters/06-blueprint-manuscrito.qmd").read_text(encoding="utf-8")
    guide = (BOOK / "chapters/06b-guia-editorial-claims.qmd").read_text(encoding="utf-8")
    supplement = (REPO / "paper/supplement_ijds.qmd").read_text(encoding="utf-8")
    registry = load_source_registry(
        REPO / "configs/ijds_active_evidence_sources.yaml",
        repo_root=REPO,
    )

    appendix_letters = re.findall(r"^# Appendix ([A-Z]):", supplement, flags=re.MULTILINE)
    assert appendix_letters == list("ABCDEFGH")
    assert "Apéndices A--H" in index
    assert "Paquetes A--H" in blueprint
    assert "A--I" not in index + blueprint
    assert "| Simulation | Supplement |" not in guide

    for registry_key in (
        "lineages.credit_controls.evaluation",
        "sources.credit_summary",
        "lineages.binary_geometry.{outcome_free,evaluation}",
        "sources.v4_summary",
        "lineages.two_ruler.{outcome_free,evaluation}",
        "sources.two_ruler_manifest",
    ):
        assert registry_key in blueprint

    assert registry["lineages"]["credit_controls"]["evaluation"]
    assert registry["lineages"]["binary_geometry"]["outcome_free"]
    assert registry["lineages"]["binary_geometry"]["evaluation"]
    assert registry["lineages"]["two_ruler"]["outcome_free"]
    assert registry["lineages"]["two_ruler"]["evaluation"]
    assert registry["sources"]["credit_summary"]
    assert registry["sources"]["v4_summary"]
    assert registry["sources"]["two_ruler_manifest"]
