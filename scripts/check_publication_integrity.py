"""Check active IJDS manuscript surfaces for claim and narrative drift."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SurfaceCheck:
    """Text surface and tokens that must or must not appear after normalization."""

    path: Path
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


COMMON_CLAIM_TOKENS = (
    "$184832.48",
    "0.035350",
    "0.162616",
    "0.073584",
    "0.245084",
    "50010",
    "27508",
    "8/8",
)

MAIN_SURFACE_REQUIRED = (
    *COMMON_CLAIM_TOKENS,
    "0.345084",
    "0.697056",
    "196369.14",
    "5.875%",
    "8.305",
    "43.55",
    "decision certificate",
    "single-submission boundary",
)

ACTIVE_SURFACE_FORBIDDEN = (
    "five contributions",
    "crpto v2",
    "future work rather than",
    "signed price is favorable",
    "wins expected return",
    "-10.56%",
    "markov cap",
    "0.510753",
    "173314.04",
    "zero deterministic violation",
    "zero exact violation",
)

SURFACES = (
    SurfaceCheck(
        path=REPO / "README.md",
        required=(
            *COMMON_CLAIM_TOKENS,
            "0.345084",
            "claim ijds activo",
            "upstream congelado",
            "no como el claim activo",
        ),
        forbidden=("## champion congelado",),
    ),
    SurfaceCheck(
        path=REPO / "paper" / "submission" / "README.md",
        required=(
            "28-page official-template pdf",
            "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "latexmk",
            "body remains inside the ijds 25-page",
        ),
        forbidden=(
            "26-page official pdf",
            "26 pages total",
            "27-page official-template pdf",
            "27 pages total",
        ),
    ),
    SurfaceCheck(
        path=REPO / "paper" / "CRPTO_ijds.qmd",
        required=(
            *MAIN_SURFACE_REQUIRED,
            "the paper makes four contributions",
            "one auditable post-hoc decision certificate",
            "matched point-pd baseline",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper" / "submission" / "CRPTO_ijds_submission.tex",
        required=(
            *MAIN_SURFACE_REQUIRED,
            "the paper makes four contributions",
            "one auditable post-hoc decision certificate",
            "matched point-pd baseline",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper" / "supplement_ijds.qmd",
        required=(
            *COMMON_CLAIM_TOKENS,
            "decision certificate",
            "single-submission boundary",
            "outside the submitted claim",
            "10423",
            "2866",
            "matched point-pd decision audit (a40)",
        ),
        forbidden=("crpto v2", "future work only", "markov cap", "0.510753"),
    ),
    SurfaceCheck(
        path=REPO / "paper" / "submission" / "CLAIM_AUDIT_MATRIX.md",
        required=(
            "exclude the historical lending club -10.56% field",
            "a40 reports a matched lending club cost of 5.875%",
            "gamma_cp = gamma_int + gamma_res",
        ),
        forbidden=("lending club price -10.56%", "+27.03%", "markov cap"),
    ),
    SurfaceCheck(
        path=REPO / "book" / "chapters" / "30-replicacion-multidataset.qmd",
        required=(
            "lending club no entra en esa serie",
            "la auditoría point-pd corregida en tau=0.1715 es a40",
            "frontera policy-aware a35",
            "5.875%",
        ),
        forbidden=(
            "lending club es la excepción informativa",
            "la robustez nunca es económicamente catastrófica",
            "+27.03%",
        ),
    ),
    SurfaceCheck(
        path=REPO / "scripts" / "generate_crpto_figures.py",
        required=("stored nonrobust baseline was not a point-only comparator",),
        forbidden=("lc_price", "sits below zero", "robustness adds value"),
    ),
    SurfaceCheck(
        path=REPO / "docs" / "research" / "active_claims_2026-07-04.md",
        required=(
            *COMMON_CLAIM_TOKENS,
            "0.345083866",
            "decision certificate",
            "outside the submitted claim",
            "baseline semantics boundary",
            "point-pd allocation earns $196369.14",
            "maximum understatement was 0.241324",
        ),
        forbidden=("crpto v2", "future protocols", "markov cap", "+27.03%"),
    ),
    SurfaceCheck(
        path=REPO / "configs" / "crpto_publication_targets.yaml",
        required=("outside the submitted claim", "not acceptance criteria"),
        forbidden=("future work and are not acceptance criteria", "crpto v2"),
    ),
)


def _normalize(text: str) -> str:
    """Normalize Markdown/LaTeX enough for robust manuscript-token checks."""
    lowered = text.lower()
    replacements = {
        "\\$": "$",
        "{,}": ",",
        "\\_": "_",
        "\\mathrm": "",
        "\\gamma": "gamma",
        "\\alpha": "alpha",
        "\\": "",
        "{": "",
        "}": "",
        "`": "",
        ",": "",
    }
    for old, new in replacements.items():
        lowered = lowered.replace(old, new)
    lowered = lowered.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", lowered)


def _read_normalized(path: Path) -> str:
    return _normalize(path.read_text(encoding="utf-8"))


def check_publication_integrity() -> list[str]:
    """Return active-manuscript integrity failures."""
    failures: list[str] = []
    for surface in SURFACES:
        if not surface.path.is_file():
            failures.append(f"{surface.path.relative_to(REPO)} is missing")
            continue
        text = _read_normalized(surface.path)
        missing = [token for token in surface.required if token not in text]
        present_forbidden = [token for token in surface.forbidden if token in text]
        rel = surface.path.relative_to(REPO)
        failures.extend(f"{rel}: missing required token '{token}'" for token in missing)
        failures.extend(
            f"{rel}: forbidden token still present '{token}'" for token in present_forbidden
        )
    return failures


def main() -> int:
    """CLI entry point."""
    failures = check_publication_integrity()
    if failures:
        for failure in failures:
            logger.error(failure)
        return 1
    logger.success("Active IJDS publication surfaces are claim-synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
