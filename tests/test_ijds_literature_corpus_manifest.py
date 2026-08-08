from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_ijds_bibliography_views import parse_bibtex_entries
from scripts.build_ijds_literature_corpus_manifest import (
    MIN_AUTO_MATCH_MARGIN,
    MIN_AUTO_MATCH_SCORE,
    build_manifest,
)

MANIFEST = Path("configs/ijds_literature_corpus_manifest.json")
MASTER_BIBLIOGRAPHY = Path("paper/references.bib")

EXPECTED_STATUS_COUNTS = {
    "companion": 1,
    "current": 144,
    "legacy": 6,
    "quarantined": 4,
    "superseded": 4,
    "watchlist": 6,
}

EXPECTED_VERSIONED_OBJECTS = {
    "zhou2025credo": {
        "version": "arXiv:2505.13243v3 / ICLR 2026",
        "pages": 41,
        "sha256": "251468168063809ac3b60fc3d3ac129cbf4e6827dcfd452c202dd1ea6a77ddb8",
        "source_url": "https://arxiv.org/abs/2505.13243v3",
    },
    "cpc2026": {
        "version": "arXiv:2603.02196v3 / ICML 2026",
        "pages": 48,
        "sha256": "1a83540c5a770be71b81a4402e42042ac21fcd6100aa0cd21d40171c1a02c28d",
        "source_url": "https://arxiv.org/abs/2603.02196v3",
    },
    "fannjiang2022feedback": {
        "version": "arXiv:2202.03613v5 / PNAS 2022",
        "pages": 38,
        "sha256": "1aa9096f151423e1c101c217179c2595f435ebc749123ef52a17d3e99117c4f8",
        "source_url": "https://arxiv.org/abs/2202.03613v5",
    },
    "stanton2023feedback": {
        "version": "AISTATS 2023 / PMLR 206",
        "pages": 28,
        "sha256": "32d573387f0bc1c1c39f36b30df0fdbba049ea5c718240fa9335743414637fba",
        "source_url": "https://proceedings.mlr.press/v206/stanton23a.html",
    },
    "prinster2024feedback": {
        "version": "ICML 2024 / PMLR 235",
        "pages": 33,
        "sha256": "48e98b614dae0646de30dc28ab4fca9831770ca114e4d37f5cae0dc5cb8e11f8",
        "source_url": "https://proceedings.mlr.press/v235/prinster24a.html",
    },
    "chen2026polyhedral_conformal_ro": {
        "version": "arXiv:2605.08506v2",
        "pages": 32,
        "sha256": "4e7f1a3e4e007a77a816adb563e06f9b15d1ddfcff2ee837d75d6b0624d0f278",
        "source_url": "https://arxiv.org/abs/2605.08506v2",
    },
    "wang2026optimal_decision_prediction_sets": {
        "version": "arXiv:2602.00989v3",
        "pages": 24,
        "sha256": "f3d1f24d4889aca52f25d0d2d86d228be1ae205a78cf7060e3f1d771c5c8bb66",
        "source_url": "https://arxiv.org/abs/2602.00989v3",
    },
    "cortesgomez2025utility": {
        "version": "ICLR 2025",
        "pages": 21,
        "sha256": "4f0984da23129e30aca12b18da24ffe9ff409a9e6a9484c37d30e955595d556c",
        "source_url": "https://openreview.net/forum?id=iOMnn1hSBO",
    },
    "joshi2026risk_controlled_postprocessing": {
        "version": "arXiv:2605.06479v1",
        "pages": 38,
        "sha256": "1412672dee77ca804e3d9e611ea8af41555fbce1be34657f7d2b707a9bd650b6",
        "source_url": "https://arxiv.org/abs/2605.06479v1",
    },
}

EXPECTED_LEGACY_FILENAMES = {
    "Deprez et al 2026 - Network Analytics for Anti-money Laundering.pdf",
    "Fuk Nagaev 1971 - Probability Inequalities for Sums of Independent Random Variables.pdf",
    "Hand Henley 1997 - Statistical Classification Methods in Consumer Credit Scoring.pdf",
    "Izbicki Shimizu Stern 2022 - CD-split and HPD-split.pdf",
    "Lei et al 2018 - Distribution-Free Predictive Inference for Regression.pdf",
    "Shafer Vovk 2008 - A Tutorial on Conformal Prediction.pdf",
}

EXPECTED_MANUALLY_ADJUDICATED_KEYS = {
    "aldirawi2026nonmonotone_crc",
    "angelopoulos2024risk",
    "bao2025croms",
    "barber2021limits",
    "cresswell2024",
    "donti2017",
    "farinhas2024nonexchangeable_crc",
    "gazin2025informative",
    "gibbs2024online",
    "guo2026lpas",
    "liu2021riskbounds",
    "ovalle2025cmicl",
    "patel2024",
    "xu2024profit_risk_credit",
    "ziliaskopoulos2026dva",
}


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_repository_literature_manifest_is_current_and_complete() -> None:
    payload = _manifest()
    pdfs = list(Path("Papers_tesis").rglob("*.pdf"))

    assert build_manifest(check=True)
    assert payload["summary"] == {
        "active_metadata_only_keys": ["holm1979", "manski2003partial", "platt2000", "vovk2005"],
        "bibliography_corpus_status_counts": {"current": 144, "metadata-only": 52},
        "bibliography_entries": 196,
        "citation_state_counts": {"active": 102, "reserve": 94},
        "object_status_counts": EXPECTED_STATUS_COUNTS,
        "pdf_bytes": 340_545_318,
        "pdf_objects": 165,
        "pdf_pages": 5_900,
        "unique_sha256": 165,
    }
    assert len(pdfs) == 165
    assert payload["validation"] == {
        "all_active_keys_current_or_explicit_metadata_only": True,
        "all_hashes_unique": True,
        "all_keyed_current_objects_unique": True,
        "all_object_paths_unique": True,
        "all_pdf_objects_in_manifest": True,
        "all_pdfs_parse_strictly": True,
        "missing_citation_keys": [],
        "no_encrypted_pdfs": True,
        "stale_object_overrides": [],
    }
    assert payload["scope"]["protected_extraction_manifest_modified"] is False


def test_promoted_and_pinned_objects_have_exact_versions_hashes_and_sources() -> None:
    objects = {
        item["bibtex_key"]: item
        for item in _manifest()["objects"]
        if item["bibtex_key"] in EXPECTED_VERSIONED_OBJECTS
    }

    assert set(objects) == set(EXPECTED_VERSIONED_OBJECTS)
    for key, expected in EXPECTED_VERSIONED_OBJECTS.items():
        item = objects[key]
        assert item["status"] == "current"
        assert {field: item[field] for field in expected} == expected
        assert Path(item["path"]).is_file()


def test_unkeyed_legacy_objects_are_explicitly_resolved() -> None:
    legacy = [item for item in _manifest()["objects"] if item["status"] == "legacy"]

    assert len(legacy) == 6
    assert {Path(item["path"]).name for item in legacy} == EXPECTED_LEGACY_FILENAMES
    assert all(item["bibtex_key"] is None for item in legacy)
    assert all("not used by the IJDS manuscript" in item["note"] for item in legacy)


def test_automatic_matches_clear_the_score_and_runner_up_margin_gates() -> None:
    objects = _manifest()["objects"]
    automatic = [item for item in objects if item["match_method"] == "title-author"]
    manually_adjudicated = {
        item["bibtex_key"]
        for item in objects
        if item["match_method"] == "explicit"
        and item["bibtex_key"] in EXPECTED_MANUALLY_ADJUDICATED_KEYS
    }

    assert manually_adjudicated == EXPECTED_MANUALLY_ADJUDICATED_KEYS
    assert all(item["match_score"] >= MIN_AUTO_MATCH_SCORE for item in automatic)
    assert all(item["match_margin"] >= MIN_AUTO_MATCH_MARGIN for item in automatic)


def test_master_bibliography_contains_the_five_coordinated_keys_and_pinned_urls() -> None:
    entries = {
        entry.key: entry.text
        for entry in parse_bibtex_entries(MASTER_BIBLIOGRAPHY.read_text(encoding="utf-8"))
    }

    assert {
        "zhou2025credo",
        "fannjiang2022feedback",
        "stanton2023feedback",
        "prinster2024feedback",
        "cpc2026",
    }.issubset(entries)
    assert "https://openreview.net/forum?id=xRjOrcj08o" in entries["zhou2025credo"]
    assert "https://arxiv.org/abs/2605.08506v2" in entries["chen2026polyhedral_conformal_ro"]
    assert (
        "https://arxiv.org/abs/2602.00989v3" in entries["wang2026optimal_decision_prediction_sets"]
    )
    assert "https://openreview.net/forum?id=iOMnn1hSBO" in entries["cortesgomez2025utility"]
    assert (
        "https://arxiv.org/abs/2605.06479v1"
        in entries["joshi2026risk_controlled_postprocessing"]
    )
