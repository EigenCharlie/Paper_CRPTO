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
    "$179327.59",
    "0.039375",
    "0.036875",
    "0.176102",
    "0.088051",
    "0.258051",
    "0.294926",
    "0.574279",
    "196369.14",
    "8.678%",
    "7.9025",
)

ACTIVE_SURFACE_FORBIDDEN = (
    "four contributions",
    "crpto v2",
    "-10.56%",
    "markov cap",
    "0.345084",
    "50010",
    "27508",
    "capped_blended_uncertainty",
)

SURFACES = (
    SurfaceCheck(
        path=REPO / "README.md",
        required=(
            *COMMON_CLAIM_TOKENS,
            "claim ijds activo",
            "q=(p+u)/2",
            "grilla redonda 3x3",
        ),
        forbidden=("## champion congelado",),
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/README.md",
        required=(
            "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "latexmk",
            "official-template",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper/CRPTO_ijds.qmd",
        required=(
            *COMMON_CLAIM_TOKENS,
            "the paper makes three contributions",
            "retrospective lockbox replay",
            "matched point-pd",
            "q_i=(p_i+u_i)/2",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CRPTO_ijds_submission.tex",
        required=(
            *COMMON_CLAIM_TOKENS,
            "the paper makes three contributions",
            "retrospective lockbox replay",
            "matched point-pd",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper/supplement_ijds.qmd",
        required=(
            *COMMON_CLAIM_TOKENS,
            "a35. exact alpha replay",
            "a36. calibration policy selector",
            "a40. matched decision audit",
            "retrospective lockbox replay",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
        required=(
            "calibration-selected midpoint",
            "a40",
            "8.678%",
            "7.9025",
        ),
        forbidden=ACTIVE_SURFACE_FORBIDDEN,
    ),
    SurfaceCheck(
        path=REPO / "docs/research/active_claims_2026-07-04.md",
        required=(
            *COMMON_CLAIM_TOKENS,
            "nine round-number candidates",
            "retrospective lockbox replay",
            "retired headline claims",
        ),
        forbidden=("crpto v2", "markov cap", "+27.03%"),
    ),
    SurfaceCheck(
        path=REPO / "configs/crpto_publication_targets.yaml",
        required=(
            "exact 90% conformal replay",
            "q=(p+u)/2",
            "outside the submitted claim",
            "not acceptance criteria",
        ),
        forbidden=("crpto v2",),
    ),
)


def _normalize(text: str) -> str:
    """Normalize Markdown and LaTeX enough for robust token checks."""
    lowered = text.lower()
    replacements = {
        r"\$": "$",
        "{,}": ",",
        r"\_": "_",
        r"\mathrm": "",
        r"\gamma": "gamma",
        r"\alpha": "alpha",
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
