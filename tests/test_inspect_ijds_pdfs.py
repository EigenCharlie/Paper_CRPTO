from __future__ import annotations

import os
import re
from pathlib import Path

import scripts.inspect_ijds_pdfs as inspector
from scripts.inspect_ijds_pdfs import (
    BODY_FIGURES,
    BODY_QMD,
    FRESHNESS_GRAPH,
    INFORMS_STYLE_ASSETS,
    PDF_COMPILER,
    PREVIEW_RENDERER,
    STYLE_MANIFEST,
    SUBMISSION_TEMPLATE,
    SUPPLEMENT_FIGURES,
    SUPPLEMENT_QMD,
    TEX_BUILDER,
    _load_abstract,
    final_freeze_pre_reference_page_limit,
    find_reference_start_page,
    freshness_failure,
    is_letter_size,
    normalized_word_stream,
    page_limit_failure,
    word_count,
)


def test_freshness_graph_includes_figures_builders_and_publisher_assets() -> None:
    graph = {output: set(inputs) for output, inputs in FRESHNESS_GRAPH}
    assert all(path.is_file() for path in (*BODY_FIGURES, *SUPPLEMENT_FIGURES))
    assert {path.name for path in INFORMS_STYLE_ASSETS} == {
        "informs4.cls",
        "informs2014.bst",
        "eqndefns-left.sty",
        "informs_Logo.pdf",
    }
    assert all(
        path.is_file() for path in (TEX_BUILDER, PDF_COMPILER, PREVIEW_RENDERER, STYLE_MANIFEST)
    )
    all_inputs = set().union(*graph.values())
    assert {*BODY_FIGURES, *SUPPLEMENT_FIGURES}.issubset(all_inputs)
    assert {TEX_BUILDER, PDF_COMPILER, PREVIEW_RENDERER, STYLE_MANIFEST}.issubset(all_inputs)


def test_every_local_qmd_png_is_in_the_freshness_graph() -> None:
    graph_inputs = {path.resolve() for _, inputs in FRESHNESS_GRAPH for path in inputs}
    for qmd in (BODY_QMD, SUPPLEMENT_QMD):
        references = re.findall(r"\]\(([^)]+\.png)\)", qmd.read_text(encoding="utf-8"))
        resolved = {(qmd.parent / Path(reference)).resolve() for reference in references}
        assert resolved.issubset(graph_inputs)


def test_submission_template_starts_references_on_a_new_page() -> None:
    template = SUBMISSION_TEMPLATE.read_text(encoding="utf-8")

    assert re.search(r"\\clearpage\s+\\bibliographystyle", template)


def test_reference_heading_detection_is_one_based_and_standalone() -> None:
    texts = ["Introduction\nReferences to prior work", "Results", "References\nA. Author"]

    assert find_reference_start_page(texts) == 3


def test_letter_size_accepts_both_orientations_only() -> None:
    assert is_letter_size(612.0, 792.0)
    assert is_letter_size(792.0, 612.0)
    assert not is_letter_size(595.0, 842.0)


def test_active_abstract_satisfies_ijds_length_and_paragraph_contract() -> None:
    abstract = _load_abstract(BODY_QMD)

    assert word_count(abstract) <= 300
    assert "\n\n" not in abstract


def test_normalized_word_stream_ignores_layout_and_punctuation() -> None:
    assert normalized_word_stream("Beta--Binomial\n90%-target") == "betabinomial90target"


def test_freshness_check_rejects_an_artifact_older_than_its_input(tmp_path) -> None:
    source = tmp_path / "source.qmd"
    output = tmp_path / "output.pdf"
    output.write_bytes(b"old")
    source.write_text("new", encoding="utf-8")
    os.utime(output, ns=(1_000_000_000, 1_000_000_000))
    os.utime(source, ns=(2_000_000_000, 2_000_000_000))

    assert freshness_failure(output, (source,)) is not None

    os.utime(output, ns=(3_000_000_000, 3_000_000_000))
    assert freshness_failure(output, (source,)) is None


def test_page_limit_is_opt_in_until_final_freeze(monkeypatch, capsys) -> None:
    calls: list[bool] = []

    def fake_report(*, enforce_page_limit: bool = False) -> dict[str, object]:
        calls.append(enforce_page_limit)
        return {"status": "pass"}

    monkeypatch.setattr(inspector, "build_report", fake_report)

    assert inspector.main([]) == 0
    assert inspector.main(["--enforce-freeze-page-limit"]) == 0
    assert calls == [False, True]
    capsys.readouterr()


def test_freeze_page_limit_is_loaded_from_the_publication_contract() -> None:
    assert final_freeze_pre_reference_page_limit() == 25


def test_page_limit_behavior_is_deferred_and_boundary_exact() -> None:
    document = "paper/submission/CRPTO_ijds_submission.pdf"

    assert page_limit_failure(26, enforce=False, limit=25, document=document) is None
    assert page_limit_failure(25, enforce=True, limit=25, document=document) is None
    assert page_limit_failure(24, enforce=True, limit=25, document=document) is None
    assert page_limit_failure(None, enforce=True, limit=25, document=document) is None
    assert page_limit_failure(26, enforce=True, limit=25, document=document) == (
        f"{document}: 26 pages before References exceeds 25"
    )
