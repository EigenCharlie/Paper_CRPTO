"""Check active IJDS surfaces for numerical, narrative, and anonymity drift."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SurfaceCheck:
    """Required and forbidden normalized tokens for one publication surface."""

    path: Path
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


ACTIVE_NUMERIC_TOKENS = (
    "465,117",
    "0.900388",
    "0.900174",
    "0.854714",
    "0.879647",
    "0.845072",
    "0.870973",
    "7 of 9",
    "5 of 9",
    "180",
    "2,025",
    "27",
    "0.0600",
    "0.0825",
    "81",
    "62",
)

RETIRED_HEADLINE_TOKENS = (
    "0.854923",
    "0.879692",
    "0.900448",
    "0.068313",
    "295,967.17",
    "506,587.03",
    "selected guardrail",
    "development-matched point",
    "maturity-safe parent",
)

COMPACT_V7_TOKENS = (
    "$179,327.59",
    "276,869",
    "0.039375",
    "0.036875",
    "0.258051",
    "0.574279",
    "$196,369.14",
)

REVIEWER_SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
    REPO / "paper/submission/ANONYMOUS_REVIEW_ARCHIVE_README.md",
    REPO / "paper/submission/TITLE_PAGE_DRAFT.md",
    REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
)

ACTIVE_EDITORIAL_SURFACES = (
    REPO / "README.md",
    REPO / "CLAUDE.md",
    REPO / "AGENTS.md",
    REPO / "docs/SCOPE_AND_GOVERNANCE.md",
    REPO / "docs/refactor/ijds_tooling_decisions_2026-07-09.md",
    REPO / "docs/research/active_claims_2026-07-12.md",
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
    REPO / "paper/submission/ANONYMOUS_REVIEW_ARCHIVE_README.md",
    REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
    REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
    REPO / "paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md",
    REPO / "paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md",
    REPO / "paper/submission/README.md",
    REPO / "paper/submission/REPRODUCIBILITY_PACKAGE.md",
    REPO / "paper/submission/SCHOLARONE_FINAL_CHECKLIST.md",
    REPO / "paper/submission/TITLE_PAGE_DRAFT.md",
    REPO / "configs/crpto_publication_targets.yaml",
)

TITLE = "crpto: auditing temporal transport and comparator choice in conformal portfolios"

SURFACES = (
    SurfaceCheck(
        REPO / "paper/CRPTO_ijds.qmd",
        (
            TITLE,
            *ACTIVE_NUMERIC_TOKENS,
            "all nine policies are co-primary",
            "comparator scopes",
            "standardized payoff",
            "not a prospective trial",
            "present negative audit framing was formulated after observing that stop",
            "ethical and governance implications",
        ),
        RETIRED_HEADLINE_TOKENS + COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/supplement_ijds.qmd",
        (
            TITLE,
            *ACTIVE_NUMERIC_TOKENS,
            "all nine policies are co-primary",
            "outcome-free freezes",
            "audit interpretation in the paper was developed after observing that failure",
            "identity s1",
            "499,845",
            "500,019",
            "9.849--21.352 million",
            "active claim boundary",
        ),
        RETIRED_HEADLINE_TOKENS + COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        (
            TITLE,
            *ACTIVE_NUMERIC_TOKENS,
            "generated from paper/crpto_ijds.qmd",
            "comparator scopes",
            "present negative audit framing was formulated after observing that stop",
        ),
        RETIRED_HEADLINE_TOKENS + COMPACT_V7_TOKENS,
    ),
    SurfaceCheck(
        REPO / "docs/research/active_claims_2026-07-12.md",
        (
            "source of truth",
            "0.854714",
            "0.879647",
            "27/27",
            "180",
            "no policy winner",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
        (
            "0.854714",
            "0.879647",
            "27/27",
            "180",
            "all nine",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
        (
            TITLE,
            "0.854714",
            "0.879647",
            "27",
            "180",
            "present negative audit framing was developed after observing the stop",
            "openai codex",
            "accepts full responsibility",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/README.md",
        (
            "single editorial source",
            "build_ijds_submission_tex.py",
            "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "28 pages",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "configs/crpto_publication_targets.yaml",
        (
            "active_claims_2026-07-12.md",
            "ijds-fixed-taxonomy-c2-2026-07-11-v1",
            "ijds-fixed-taxonomy-c2-2026-07-11-v2",
            "0.854714",
            "0.879647",
            "post_result_audit_framing: true",
            "git_history_only",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
)

REVIEWER_FORBIDDEN_LITERALS = (
    "champion-reopen-",
    "protocol/ijds",
    "carlos alfredo vergara rojas",
    "cavr94",
    "eigencharlie",
    "c:\\users\\",
    "the authors thank the anonymous reviewers and editors",
)

REVIEWER_FORBIDDEN_PATTERNS = (
    ("full Git commit", re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)),
    ("SHA-256 fingerprint", re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)),
    ("DVC directory fingerprint", re.compile(r"\b[0-9a-f]{32}\.dir\b", re.IGNORECASE)),
)


def _normalize(text: str) -> str:
    value = text.lower()
    for old, new in {
        r"\$": "$",
        r"\%": "%",
        r"\_": "_",
        "{,}": ",",
        "{[}": "[",
        "{]}": "]",
        "{": "",
        "}": "",
        "`": "",
    }.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value)


def _check_surface_contracts() -> list[str]:
    failures: list[str] = []
    for surface in SURFACES:
        if not surface.path.is_file():
            failures.append(f"{surface.path.relative_to(REPO)} is missing")
            continue
        text = _normalize(surface.path.read_text(encoding="utf-8"))
        rel = surface.path.relative_to(REPO)
        failures.extend(
            f"{rel}: missing required token '{token}'"
            for token in surface.required
            if _normalize(token) not in text
        )
        failures.extend(
            f"{rel}: retired token present '{token}'"
            for token in surface.forbidden
            if _normalize(token) in text
        )
    return failures


def _check_retired_headlines() -> list[str]:
    failures: list[str] = []

    for path in ACTIVE_EDITORIAL_SURFACES:
        if not path.is_file():
            failures.append(f"{path.relative_to(REPO)} is missing")
            continue
        normalized = _normalize(path.read_text(encoding="utf-8"))
        for token in RETIRED_HEADLINE_TOKENS:
            if _normalize(token) in normalized:
                failures.append(f"{path.relative_to(REPO)}: retired headline token '{token}'")
    return failures


def _check_reviewer_anonymity() -> list[str]:
    failures: list[str] = []

    for path in REVIEWER_SURFACES:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        normalized = _normalize(raw)
        for literal in REVIEWER_FORBIDDEN_LITERALS:
            if literal in normalized:
                failures.append(f"{path.relative_to(REPO)}: reviewer identity token '{literal}'")
        for label, pattern in REVIEWER_FORBIDDEN_PATTERNS:
            if pattern.search(raw):
                failures.append(f"{path.relative_to(REPO)}: reviewer surface contains {label}")
    return failures


def _check_evidence_decision() -> list[str]:
    failures: list[str] = []

    evidence_path = REPO / "reports/crpto/ijds_fixed_taxonomy_c2_evidence.json"
    if evidence_path.is_file():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence["decision"]["policy_winner_allowed"] is not False:
            failures.append("active evidence unexpectedly allows a policy winner")
        if evidence["decision"].get("post_result_audit_framing") is not True:
            failures.append("active evidence no longer discloses post-result audit framing")
        if evidence["decision"].get("prespecified_negative_fallback") is not False:
            failures.append("active evidence misstates the audit as a prespecified fallback")
        if evidence["headline"]["comparator_multiverse_envelopes_indeterminate"] != 27:
            failures.append("active evidence no longer has 27 indeterminate envelopes")
    else:
        failures.append("active evidence manifest is missing")
    return failures


def check_publication_integrity() -> list[str]:
    """Return every active-paper synchronization or anonymity failure."""
    failures: list[str] = []
    failures.extend(_check_surface_contracts())
    failures.extend(_check_retired_headlines())
    failures.extend(_check_reviewer_anonymity())
    failures.extend(_check_evidence_decision())

    return failures


def main() -> int:
    failures = check_publication_integrity()
    if failures:
        for failure in failures:
            logger.error(failure)
        logger.error("Publication integrity failed with {} issue(s).", len(failures))
        return 1
    logger.info("Active IJDS publication surfaces are synchronized and anonymous.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
