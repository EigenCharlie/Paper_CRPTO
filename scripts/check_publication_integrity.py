"""Check active IJDS publication surfaces for claim and narrative drift."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SurfaceCheck:
    """Text surface and normalized tokens that must or must not appear."""

    path: Path
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


ACTIVE_NUMERIC_TOKENS = (
    "540,121",
    "0.854923",
    "0.879692",
    "0.020093",
    "0.046275",
    "0.008822",
    "0.029850",
)

COMPACT_V7_TOKENS = (
    "champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7",
    "$179,327.59",
    "276,869",
    "0.039375",
    "0.036875",
    "0.258051",
    "0.574279",
    "$196,369.14",
    "8.678%",
    "7.9025",
)

SURFACES = (
    SurfaceCheck(
        path=REPO / "README.md",
        required=(
            "claim ijds activo",
            "maturity-safe-locked-bounded-h1h2-v2",
            "q=0.75p+0.25u",
            "active_claims_2026-07-10.md",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/CRPTO_ijds.qmd",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "when marginal conformal coverage meets maturity-safe credit portfolio selection",
            "the paper makes four contributions",
            "standardized payoff",
            "not a confidence interval",
            "within-group optimizer selection",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CRPTO_ijds_submission.tex",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "when marginal conformal coverage meets maturity-safe credit portfolio selection",
            "the paper makes four contributions",
            "standardized payoff",
            "not a confidence interval",
            "within-group optimizer selection",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/supplement_ijds.qmd",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "proposition s1",
            "proposition s2",
            "proposition s3",
            "s1--s7",
            "historical diagnostics",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "status-independent",
            "sharp partial-identification bounds",
            "historical firewall",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "docs/research/active_claims_2026-07-10.md",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "active experiment",
            "selection-transport identity",
            "historical boundary",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "configs/crpto_publication_targets.yaml",
        required=(
            "reconstructed_active",
            "maturity-safe-locked-bounded-h1h2-v2",
            "q=0.75p+0.25u",
            "historical_not_active_evidence",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/README.md",
        required=(
            "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "latexmk",
            "16 pages",
            "active maturity-safe ijds handoff",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
)


def _normalize(text: str) -> str:
    """Normalize Markdown and LaTeX enough for robust token checks."""
    value = text.lower()
    replacements = {
        r"\$": "$",
        r"\%": "%",
        r"\_": "_",
        "{,}": ",",
        "{": "",
        "}": "",
        "`": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value)


def check_publication_integrity() -> list[str]:
    """Return active-manuscript integrity failures."""
    failures: list[str] = []
    for surface in SURFACES:
        if not surface.path.is_file():
            failures.append(f"{surface.path.relative_to(REPO)} is missing")
            continue
        text = _normalize(surface.path.read_text(encoding="utf-8"))
        required = tuple(_normalize(token) for token in surface.required)
        forbidden = tuple(_normalize(token) for token in surface.forbidden)
        missing = [token for token in required if token not in text]
        present = [token for token in forbidden if token in text]
        rel = surface.path.relative_to(REPO)
        failures.extend(f"{rel}: missing required token '{token}'" for token in missing)
        failures.extend(f"{rel}: compact-v7 token is active '{token}'" for token in present)
    return failures


def main() -> int:
    """CLI entry point."""
    failures = check_publication_integrity()
    if failures:
        for failure in failures:
            logger.error(failure)
        return 1
    logger.success("Active maturity-safe IJDS publication surfaces are synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
