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
    "current": 151,
    "legacy": 6,
    "quarantined": 3,
    "superseded": 5,
    "watchlist": 5,
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
    "podkopaev2021labelshift": {
        "version": "UAI 2021 / PMLR 161:844--853",
        "pages": 10,
        "sha256": "76c4e956fff514c23546d8c5145f7331cdf4caddf458078fa59cefb9f91074ac",
        "source_url": "https://proceedings.mlr.press/v161/podkopaev21a.html",
    },
    "ramos2026transported_beta": {
        "version": "arXiv:2605.19024v1",
        "pages": 33,
        "sha256": "f4563aae0258ed80cf26155cee07f0c8476d2ba9261fc7738847030e20cbe577",
        "source_url": "https://arxiv.org/abs/2605.19024v1",
    },
    "xu2026selective_crc": {
        "version": "arXiv:2512.12844v2",
        "pages": 25,
        "sha256": "e5531ca84122c8fb5e56e9c0a2fe2b98521b69ca092f587eea9825a33e39d1f5",
        "source_url": "https://arxiv.org/abs/2512.12844v2",
    },
    "zhou2026audited_cp": {
        "version": "arXiv:2606.14909v1",
        "pages": 59,
        "sha256": "498e13b5b90e53335f18bc2a5757293d1c316302d7fba841e4808c5c7fdd00ea",
        "source_url": "https://arxiv.org/abs/2606.14909v1",
    },
    "liang2026model_selection_conformal": {
        "version": "arXiv:2408.07066v4 / JASA 2026 online first",
        "pages": 47,
        "sha256": "7e707e0afd0a680076d468717c1e7ae4032ce17160115265c93634c26bc4f071",
        "source_url": "https://arxiv.org/abs/2408.07066v4",
    },
    "yang2025selection_aggregation_conformal": {
        "version": "arXiv:2104.13871v3 / JASA 2025",
        "pages": 74,
        "sha256": "e0f7c8246de481ba35e46b13f06ba175ae22c2737404b53f00824d1bd7acca6d",
        "source_url": "https://arxiv.org/abs/2104.13871v3",
    },
    "zhu2026action_conditional_risk_averse": {
        "version": "arXiv:2606.05551v2",
        "pages": 38,
        "sha256": "9b72a0361912b770223980d21390712e8c016272e53b983cf8adbf8cea8a519e",
        "source_url": "https://arxiv.org/abs/2606.05551v2",
    },
    "hegazy2025valid_selection_conformal_sets": {
        "version": "NeurIPS 2025 proceedings / DOI 10.52202/085713-5812",
        "pages": 32,
        "sha256": "e4c1d3841477d5bdb9c2b01fb396c582dde8a024bb8d07eab857229ae5acc6f6",
        "source_url": "https://proceedings.neurips.cc/paper_files/paper/2025/hash/ff9386992bb2b9cee1dddf0bd5f328de-Abstract-Conference.html",
    },
    "bao2025croms": {
        "version": "arXiv:2507.04716v2",
        "pages": 104,
        "sha256": "7692f5ade58b6ec5926f6e18fb4a3fb3e8efe419e3edd7878a794dd1842317ea",
        "source_url": "https://arxiv.org/abs/2507.04716v2",
    },
    "yeh2026": {
        "version": "arXiv:2409.20534v2 / TMLR December 2025",
        "pages": 29,
        "sha256": "4c71398a763e94b75f39d1f99665e57b5a48711b90f3524c20df3735df20a736",
        "source_url": "https://arxiv.org/abs/2409.20534v2",
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
    "podkopaev2021labelshift",
    "ramos2026transported_beta",
    "xu2024profit_risk_credit",
    "xu2026selective_crc",
    "ziliaskopoulos2026dva",
    "zhou2026audited_cp",
}


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_repository_literature_manifest_is_current_and_complete() -> None:
    payload = _manifest()
    pdfs = list(Path("Papers_tesis").rglob("*.pdf"))

    assert build_manifest(check=True)
    assert payload["summary"] == {
        "active_metadata_only_keys": ["holm1979", "manski2003partial", "platt2000", "vovk2005"],
        "bibliography_corpus_status_counts": {"current": 151, "metadata-only": 56},
        "bibliography_entries": 207,
        "citation_state_counts": {"active": 110, "reserve": 97},
        "object_status_counts": EXPECTED_STATUS_COUNTS,
        "pdf_bytes": 346_669_707,
        "pdf_objects": 171,
        "pdf_pages": 6_121,
        "unique_sha256": 171,
    }
    assert len(pdfs) == 171
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
        if item["status"] == "current" and item["bibtex_key"] in EXPECTED_VERSIONED_OBJECTS
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


def test_master_bibliography_contains_coordinated_keys_and_pinned_urls() -> None:
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
        "podkopaev2021labelshift",
        "ramos2026transported_beta",
        "xu2026selective_crc",
        "zhou2026audited_cp",
        "long2026cp_wdro",
        "farzaneh2026oce_risk_control",
        "braun2026conditional_coverage_diagnostics",
        "wasserstein_regularized_cp_2025",
    }.issubset(entries)
    assert "https://openreview.net/forum?id=xRjOrcj08o" in entries["zhou2025credo"]
    assert "https://arxiv.org/abs/2605.08506v2" in entries["chen2026polyhedral_conformal_ro"]
    assert (
        "https://arxiv.org/abs/2602.00989v3" in entries["wang2026optimal_decision_prediction_sets"]
    )
    assert "https://openreview.net/forum?id=iOMnn1hSBO" in entries["cortesgomez2025utility"]
    assert (
        "https://proceedings.mlr.press/v161/podkopaev21a.html" in entries["podkopaev2021labelshift"]
    )
    assert "https://arxiv.org/abs/2605.19024v1" in entries["ramos2026transported_beta"]
    assert "https://arxiv.org/abs/2512.12844v2" in entries["xu2026selective_crc"]
    assert "https://arxiv.org/abs/2606.14909v1" in entries["zhou2026audited_cp"]
    assert (
        "https://arxiv.org/abs/2605.06479v1" in entries["joshi2026risk_controlled_postprocessing"]
    )
    assert "10.1080/01621459.2026.2663588" in entries["liang2026model_selection_conformal"]
    assert "10.1080/01621459.2024.2344700" in entries["yang2025selection_aggregation_conformal"]
    assert "https://arxiv.org/abs/2606.05551v2" in entries["zhu2026action_conditional_risk_averse"]
    assert "10.52202/085713-5812" in entries["hegazy2025valid_selection_conformal_sets"]
    assert "https://arxiv.org/abs/2507.04716v2" in entries["bao2025croms"]
    assert "https://openreview.net/forum?id=yM8qkT0f9H" in entries["yeh2026"]


def test_hegazy_arxiv_v1_is_retained_as_superseded_provenance() -> None:
    objects = [
        item
        for item in _manifest()["objects"]
        if item["bibtex_key"] == "hegazy2025valid_selection_conformal_sets"
    ]

    assert {(item["status"], item["version"]) for item in objects} == {
        ("current", "NeurIPS 2025 proceedings / DOI 10.52202/085713-5812"),
        ("superseded", "arXiv:2506.20173v1"),
    }
    old = next(item for item in objects if item["status"] == "superseded")
    assert old["pages"] == 31
    assert old["sha256"] == "f77dc2b614ee8fbfd6f4c9f886645294b781f9a5771f39ae0065ab66a788a605"
