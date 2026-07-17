from __future__ import annotations

from scripts.inspect_ijds_pdfs import (
    BODY_QMD,
    _load_abstract,
    find_reference_start_page,
    is_letter_size,
    word_count,
)


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
