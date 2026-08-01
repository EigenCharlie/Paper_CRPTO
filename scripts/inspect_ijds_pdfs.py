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
PUBLICATION_TARGETS = ROOT / "configs" / "crpto_publication_targets.yaml"
OFFICIAL_PDF = ROOT / "paper" / "submission" / "CRPTO_ijds_submission.pdf"
OFFICIAL_TEX = ROOT / "paper" / "submission" / "CRPTO_ijds_submission.tex"
BODY_PDF = ROOT / "paper" / "CRPTO_ijds.pdf"
BODY_HTML = ROOT / "paper" / "CRPTO_ijds.html"
SUPPLEMENT_PDF = ROOT / "paper" / "supplement_ijds.pdf"
SUPPLEMENT_HTML = ROOT / "paper" / "supplement_ijds.html"
BODY_QMD = ROOT / "paper" / "CRPTO_ijds.qmd"
SUPPLEMENT_QMD = ROOT / "paper" / "supplement_ijds.qmd"
REFERENCES_BIB = ROOT / "paper" / "references.bib"
CSL_STYLE = ROOT / "paper" / "apa.csl"
HTML_STYLE = ROOT / "paper" / "ijds.css"
SUBMISSION_TEMPLATE = ROOT / "paper" / "submission" / "informs-pandoc-template.tex"
STYLE_MANIFEST = ROOT / "paper" / "submission" / "informs_style_assets.json"
TEX_BUILDER = ROOT / "scripts" / "build_ijds_submission_tex.py"
PDF_COMPILER = ROOT / "scripts" / "compile_ijds_submission.py"
PREVIEW_RENDERER = ROOT / "scripts" / "render_submission_pdf_previews.py"
INFORMATION_BOUNDARY_GENERATOR = ROOT / "scripts" / "generate_ijds_information_boundary_figure.py"
INFORMATION_BOUNDARY_FIGURES = tuple(
    ROOT / "reports" / "crpto" / "figures" / f"crpto_ijds_information_boundary.{suffix}"
    for suffix in ("pdf", "png")
)
BODY_FIGURES = (
    ROOT / "reports" / "crpto" / "figures" / "crpto_ijds_v4_fig1_coverage.png",
    ROOT / "reports" / "crpto" / "figures" / "crpto_ijds_v4_fig2_phase_transition.png",
    ROOT
    / "reports"
    / "crpto"
    / "figures"
    / "crpto_ijds_v4_fig4_common_panel_threshold_response.png",
    *INFORMATION_BOUNDARY_FIGURES,
)
SUPPLEMENT_FIGURES = (
    ROOT
    / "reports"
    / "crpto"
    / "figures"
    / "crpto_ijds_v4_figS1_common_panel_threshold_response_census.png",
    ROOT / "reports" / "crpto" / "figures" / "crpto_ijds_v4_fig3_envelopes.png",
)
INFORMS_STYLE_ASSETS = tuple(
    ROOT / "paper" / "submission" / name
    for name in ("informs4.cls", "informs2014.bst", "eqndefns-left.sty", "informs_Logo.pdf")
)
FRESHNESS_GRAPH = (
    *((figure, (INFORMATION_BOUNDARY_GENERATOR,)) for figure in INFORMATION_BOUNDARY_FIGURES),
    (BODY_HTML, (BODY_QMD, REFERENCES_BIB, CSL_STYLE, HTML_STYLE, *BODY_FIGURES)),
    (BODY_PDF, (BODY_HTML, PREVIEW_RENDERER)),
    (
        SUPPLEMENT_HTML,
        (
            SUPPLEMENT_QMD,
            REFERENCES_BIB,
            CSL_STYLE,
            HTML_STYLE,
            *SUPPLEMENT_FIGURES,
        ),
    ),
    (SUPPLEMENT_PDF, (SUPPLEMENT_HTML, PREVIEW_RENDERER)),
    (
        OFFICIAL_TEX,
        (BODY_QMD, REFERENCES_BIB, CSL_STYLE, SUBMISSION_TEMPLATE, TEX_BUILDER),
    ),
    (
        OFFICIAL_PDF,
        (
            OFFICIAL_TEX,
            REFERENCES_BIB,
            PDF_COMPILER,
            STYLE_MANIFEST,
            *INFORMS_STYLE_ASSETS,
            *BODY_FIGURES,
        ),
    ),
)
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


def normalized_word_stream(text: str) -> str:
    """Return a token-boundary-insensitive stream for source-to-PDF checks."""
    return "".join(re.findall(r"[A-Za-z0-9]+", text.casefold()))


def final_freeze_pre_reference_page_limit(
    path: Path = PUBLICATION_TARGETS,
) -> int:
    """Load the sole final-freeze pre-reference page limit from config."""
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid publication-target config: {_display_path(path)}")
    primary = cast(Mapping[str, object], payload).get("primary_target")
    if not isinstance(primary, Mapping):
        raise ValueError("Missing primary_target in publication-target config")
    constraints = cast(Mapping[str, object], primary).get("constraints")
    if not isinstance(constraints, Mapping):
        raise ValueError("Missing primary_target.constraints in publication-target config")
    limit = cast(Mapping[str, object], constraints).get("final_freeze_pre_reference_page_limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("final_freeze_pre_reference_page_limit must be a positive integer")
    return limit


def page_limit_failure(
    content_pages: int | None,
    *,
    enforce: bool,
    limit: int,
    document: str,
) -> str | None:
    """Return the opt-in final-freeze page failure, if any."""
    if not enforce or content_pages is None or content_pages <= limit:
        return None
    return f"{document}: {content_pages} pages before References exceeds {limit}"


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def freshness_failure(output: Path, inputs: tuple[Path, ...]) -> str | None:
    """Return a failure when an artifact predates a declared build input."""
    missing = [path for path in (output, *inputs) if not path.is_file()]
    if missing:
        names = ", ".join(_display_path(path) for path in missing)
        return f"missing freshness input or output: {names}"
    newest_input = max(inputs, key=lambda path: path.stat().st_mtime_ns)
    if output.stat().st_mtime_ns < newest_input.stat().st_mtime_ns:
        return f"{_display_path(output)} predates {_display_path(newest_input)}"
    return None


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
    delimiters = tuple(re.finditer(r"^---[ \t]*$", raw, flags=re.MULTILINE))
    if len(delimiters) < 2 or delimiters[0].start() != 0:
        raise ValueError(f"Missing YAML front matter in {path.relative_to(ROOT)}")
    front_matter = raw[delimiters[0].end() : delimiters[1].start()]
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


def build_report(*, enforce_page_limit: bool = False) -> dict[str, Any]:
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
    official_reader = PdfReader(OFFICIAL_PDF)
    official_front_text = "\n".join(
        (page.extract_text() or "") for page in official_reader.pages[:2]
    )
    abstract_matches_pdf = normalized_word_stream(abstract) in normalized_word_stream(
        official_front_text
    )
    content_pages = (
        official.reference_start_page - 1 if official.reference_start_page is not None else None
    )
    freeze_page_limit = final_freeze_pre_reference_page_limit()

    freshness_checks = tuple(
        freshness_failure(output, inputs) for output, inputs in FRESHNESS_GRAPH
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
    else:
        page_failure = page_limit_failure(
            content_pages,
            enforce=enforce_page_limit,
            limit=freeze_page_limit,
            document=official.path,
        )
        if page_failure is not None:
            failures.append(page_failure)
    if abstract_words > 300:
        failures.append(f"abstract has {abstract_words} words; IJDS maximum is 300")
    if not abstract_single_paragraph:
        failures.append("abstract is not one paragraph")
    if not abstract_matches_pdf:
        failures.append("official PDF abstract does not match the active QMD abstract")
    failures.extend(failure for failure in freshness_checks if failure is not None)

    return {
        "status": "pass" if not failures else "fail",
        "abstract_words": abstract_words,
        "abstract_single_paragraph": abstract_single_paragraph,
        "abstract_matches_official_pdf": abstract_matches_pdf,
        "official_pre_reference_pages": content_pages,
        "page_limit_enforced": enforce_page_limit,
        "final_freeze_pre_reference_page_limit": freeze_page_limit,
        "freshness_failures": [failure for failure in freshness_checks if failure is not None],
        "documents": [asdict(inspection) for inspection in inspections],
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the PDF audit and emit a compact JSON record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enforce-freeze-page-limit",
        action="store_true",
        help="Enable the deferred final-freeze pre-reference page-limit contract.",
    )
    args = parser.parse_args(argv)
    report = build_report(enforce_page_limit=args.enforce_freeze_page_limit)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
