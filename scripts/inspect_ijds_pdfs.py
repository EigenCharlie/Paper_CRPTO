"""Audit generated IJDS PDFs for page, layout, anonymity, and abstract contracts."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from pypdf import PdfReader

from scripts.check_publication_integrity import (
    REVIEWER_FORBIDDEN_LITERALS,
    REVIEWER_FORBIDDEN_PATTERNS,
)

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PDF = ROOT / "paper" / "submission" / "CRPTO_ijds_submission.pdf"
BODY_PDF = ROOT / "paper" / "CRPTO_ijds.pdf"
SUPPLEMENT_PDF = ROOT / "paper" / "supplement_ijds.pdf"
BODY_QMD = ROOT / "paper" / "CRPTO_ijds.qmd"
LETTER_POINTS = (612.0, 792.0)
BLANK_PAGE_MIN_ALNUM = 20


@dataclass(frozen=True)
class PdfInspection:
    """Compact machine-readable inspection of one reviewer-facing PDF."""

    path: str
    pages: int
    page_sizes_points: tuple[str, ...]
    non_letter_pages: tuple[int, ...]
    blank_pages: tuple[int, ...]
    identity_hits: tuple[str, ...]
    fingerprint_hits: tuple[str, ...]
    reference_start_page: int | None


def word_count(text: str) -> int:
    """Count human-readable word tokens in an abstract."""
    return len(re.findall(r"\b[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*\b", text))


def is_letter_size(width: float, height: float, *, tolerance: float = 1.0) -> bool:
    """Return whether a page is US Letter in portrait or landscape orientation."""
    expected = (LETTER_POINTS, tuple(reversed(LETTER_POINTS)))
    return any(
        abs(width - target_width) <= tolerance and abs(height - target_height) <= tolerance
        for target_width, target_height in expected
    )


def find_reference_start_page(page_texts: list[str]) -> int | None:
    """Return the one-based page containing the standalone References heading."""
    heading = re.compile(r"(?:^|\n)\s*references\s*(?:\n|$)", re.IGNORECASE)
    for page_number, text in enumerate(page_texts, start=1):
        if heading.search(text):
            return page_number
    return None


def _load_abstract(path: Path = BODY_QMD) -> str:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"Missing YAML front matter in {path.relative_to(ROOT)}")
    front_matter = raw.split("---", maxsplit=2)[1]
    payload: object = yaml.safe_load(front_matter)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Missing abstract in {path.relative_to(ROOT)}")
    abstract = cast(Mapping[str, object], payload).get("abstract")
    if not isinstance(abstract, str):
        raise ValueError(f"Missing abstract in {path.relative_to(ROOT)}")
    return abstract.strip()


def _page_size(page: Any) -> tuple[float, float]:
    return float(page.mediabox.width), float(page.mediabox.height)


def inspect_pdf(path: Path, *, detect_references: bool = False) -> PdfInspection:
    """Inspect one generated PDF without persisting extracted manuscript text."""
    if not path.is_file():
        raise FileNotFoundError(path)
    reader = PdfReader(path)
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    sizes = [_page_size(page) for page in reader.pages]
    metadata = " ".join(str(value) for value in (reader.metadata or {}).values())
    searchable = "\n".join([metadata, *page_texts])
    normalized = searchable.lower()

    identity_hits = tuple(
        sorted(literal for literal in REVIEWER_FORBIDDEN_LITERALS if literal in normalized)
    )
    fingerprint_hits = tuple(
        label for label, pattern in REVIEWER_FORBIDDEN_PATTERNS if pattern.search(searchable)
    )
    blank_pages = tuple(
        page_number
        for page_number, text in enumerate(page_texts, start=1)
        if len(re.sub(r"[^A-Za-z0-9]", "", text)) < BLANK_PAGE_MIN_ALNUM
    )
    non_letter_pages = tuple(
        page_number
        for page_number, (width, height) in enumerate(sizes, start=1)
        if not is_letter_size(width, height)
    )
    unique_sizes = tuple(sorted({f"{width:.2f}x{height:.2f}" for width, height in sizes}))
    return PdfInspection(
        path=path.relative_to(ROOT).as_posix(),
        pages=len(reader.pages),
        page_sizes_points=unique_sizes,
        non_letter_pages=non_letter_pages,
        blank_pages=blank_pages,
        identity_hits=identity_hits,
        fingerprint_hits=fingerprint_hits,
        reference_start_page=find_reference_start_page(page_texts) if detect_references else None,
    )


def build_report() -> dict[str, Any]:
    """Build the full reviewer-facing PDF audit report."""
    inspections = (
        inspect_pdf(OFFICIAL_PDF, detect_references=True),
        inspect_pdf(BODY_PDF),
        inspect_pdf(SUPPLEMENT_PDF),
    )
    official = inspections[0]
    abstract = _load_abstract()
    abstract_words = word_count(abstract)
    abstract_single_paragraph = re.search(r"\n\s*\n", abstract) is None
    content_pages = (
        official.reference_start_page - 1 if official.reference_start_page is not None else None
    )

    failures: list[str] = []
    for inspection in inspections:
        if inspection.non_letter_pages:
            failures.append(f"{inspection.path}: non-Letter pages {inspection.non_letter_pages}")
        if inspection.blank_pages:
            failures.append(f"{inspection.path}: blank pages {inspection.blank_pages}")
        if inspection.identity_hits:
            failures.append(f"{inspection.path}: identity tokens {inspection.identity_hits}")
        if inspection.fingerprint_hits:
            failures.append(f"{inspection.path}: fingerprints {inspection.fingerprint_hits}")
    if official.reference_start_page is None:
        failures.append(f"{official.path}: References heading not found")
    elif content_pages is not None and content_pages > 25:
        failures.append(f"{official.path}: {content_pages} pages before References exceeds 25")
    if abstract_words > 300:
        failures.append(f"abstract has {abstract_words} words; IJDS maximum is 300")
    if not abstract_single_paragraph:
        failures.append("abstract is not one paragraph")

    return {
        "status": "pass" if not failures else "fail",
        "abstract_words": abstract_words,
        "abstract_single_paragraph": abstract_single_paragraph,
        "official_pre_reference_pages": content_pages,
        "documents": [asdict(inspection) for inspection in inspections],
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the PDF audit and emit a compact JSON record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
