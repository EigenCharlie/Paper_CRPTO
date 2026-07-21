"""Static contracts for the active three-page Quarto companion."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.ijds_audit.publication_sources import load_source_registry

REPO = Path(__file__).resolve().parents[1]
BOOK = REPO / "book"


def _config() -> dict:
    return yaml.safe_load((BOOK / "_quarto.yml").read_text(encoding="utf-8"))


def _assert_local_file(path: str) -> None:
    candidate = (BOOK / path).resolve()
    assert candidate.is_file(), candidate


def test_active_companion_configuration_has_no_missing_local_dependencies() -> None:
    config = _config()
    chapters: list[str] = []
    for entry in config["book"]["chapters"]:
        if isinstance(entry, str):
            chapters.append(entry)
        else:
            chapters.extend(entry["chapters"])
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
