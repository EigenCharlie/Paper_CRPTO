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
    "0.068313",
    "0.034431",
    "0.056287",
    "0.027093",
    "0.046283",
    "295,967.17",
    "506,587.03",
    "7/9",
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

REVIEWER_SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
    REPO / "paper/submission/ANONYMOUS_REVIEW_ARCHIVE_README.md",
)

REVIEWER_FORBIDDEN_LITERALS = (
    "champion-reopen-",
    "protocol/ijds",
    "carlos alfredo vergara rojas",
    "cavr94",
    "eigencharlie",
)

REVIEWER_FORBIDDEN_PATTERNS = (
    ("full Git commit", re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)),
    ("SHA-256 fingerprint", re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)),
    ("DVC directory fingerprint", re.compile(r"\b[0-9a-f]{32}\.dir\b", re.IGNORECASE)),
)

SURFACES = (
    SurfaceCheck(
        path=REPO / "README.md",
        required=(
            "claim ijds activo",
            "maturity-safe-locked-bounded-h1h2-v2",
            "comparator-stringency-audit-v1",
            "q=0.75p+0.25u",
            "active_claims_2026-07-10.md",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/CRPTO_ijds.qmd",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "auditing comparator stringency in maturity-safe conformal credit portfolios",
            "the paper makes four contributions",
            "standardized payoff",
            "not a confidence interval",
            "within-group optimizer selection",
            "closest-work boundary",
            "identification and theory",
            "comparator non-invariance",
            "equal thresholds are not equal baselines",
            "post hoc",
            "managerial audit card",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CRPTO_ijds_submission.tex",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "auditing comparator stringency in maturity-safe conformal credit portfolios",
            "the paper makes four contributions",
            "standardized payoff",
            "not a confidence interval",
            "within-group optimizer selection",
            "closest-work boundary",
            "identification and theory",
            "comparator non-invariance",
            "equal thresholds are not equal baselines",
            "post hoc",
            "managerial audit card",
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
            "proposition s4",
            "cs1--cs3",
            "historical diagnostics",
            "reader map",
            "corollary s2.1",
            "threats to validity",
            "metadata-sanitized review archive",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "status-independent",
            "sharp partial-identification bounds",
            "comparator",
            "post hoc",
            "historical firewall",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "docs/research/active_claims_2026-07-10.md",
        required=(
            *ACTIVE_NUMERIC_TOKENS,
            "evidence hierarchy",
            "selection-transport identity",
            "comparator non-invariance",
            "historical boundary",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "configs/crpto_publication_targets.yaml",
        required=(
            "reconstructed_active",
            "maturity-safe-locked-bounded-h1h2-v2",
            "comparator-stringency-audit-v1",
            "q=0.75p+0.25u",
            "0.06831339893217318",
            "historical_not_active_evidence",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/README.md",
        required=(
            "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "latexmk",
            "active maturity-safe and comparator-aware ijds handoff",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
        required=(
            "540,121",
            "0.854923",
            "0.879692",
            "0.068313",
            "0.034431",
            "0.056287",
            "0.027093",
            "0.046283",
            "295,967.17",
            "506,587.03",
            "seven of nine",
            "before the first successful persisted execution",
            "select option 4",
            "openai codex",
            "gpt-5.6 sol",
            "accepts full responsibility",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md",
        required=(
            "effective march 5, 2025",
            "select option 4",
            "legitimate access",
            "historical consumer-credit records",
            "reproducibility report",
            "editor_only_reproducibility_crosswalk.md",
        ),
        forbidden=COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        path=REPO / "paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md",
        required=(
            "editor-only",
            "p1: maturity-safe parent",
            "c1: comparator-stringency audit",
            "protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2",
            "protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1",
            "neither sequence invokes or writes a manifest-protected historical stage",
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

    for path in REVIEWER_SURFACES:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        normalized = raw.lower()
        rel = path.relative_to(REPO)
        for token in REVIEWER_FORBIDDEN_LITERALS:
            if token in normalized:
                failures.append(f"{rel}: reviewer fingerprint is active '{token}'")
        for label, pattern in REVIEWER_FORBIDDEN_PATTERNS:
            if pattern.search(raw):
                failures.append(f"{rel}: reviewer surface contains {label}")
    return failures


def main() -> int:
    """CLI entry point."""
    failures = check_publication_integrity()
    if failures:
        for failure in failures:
            logger.error(failure)
        return 1
    logger.success("Active maturity-safe and comparator-aware IJDS surfaces are synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
