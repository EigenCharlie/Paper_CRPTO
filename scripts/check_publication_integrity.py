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


TITLE = "crpto: auditing binary conformal geometry and portfolio comparators"

RETIRED_HEADLINE_TOKENS = (
    "0.854714",
    "0.879647",
    "0.845072",
    "0.870973",
    "7 of 9",
    "5 of 9",
    "2,025",
    "selected guardrail",
    "development-matched point",
    "maturity-safe parent",
    "all nine policies are co-primary",
    "$179,327.59",
    "0.039375",
    "0.036875",
    "0.258051",
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
    REPO / "CLAUDE.md",
    REPO / "AGENTS.md",
    REPO / "docs/SCOPE_AND_GOVERNANCE.md",
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

COMMON_ACTIVE_TOKENS = (
    "376,890",
    "11,551",
    "6,240",
    "5,603.66",
    "155,937.27",
    "44 loan-month positions",
    "eight",
    "0.1017",
    "0.0971",
    "0.8884",
    "0.1118",
    "3,067",
    "216",
    "72",
    "selected-set",
)

SURFACES = (
    SurfaceCheck(
        REPO / "paper/CRPTO_ijds.qmd",
        (
            TITLE,
            *COMMON_ACTIVE_TOKENS,
            "0.8957",
            "1,080",
            "two outcome-free rulers",
            "not 48 replications",
            "objective-matched",
            "normalized-score",
            "standardized payoff",
            "not a prospective trial",
            "ethical and governance implications",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/supplement_ijds.qmd",
        (
            TITLE,
            *COMMON_ACTIVE_TOKENS,
            "365,339",
            "5,001,617",
            "1,080",
            "19,200",
            "not eight independent confirmations",
            "coordinate one",
            "binary phase transition",
            "active conclusion is deliberately narrow",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        (
            TITLE,
            *COMMON_ACTIVE_TOKENS,
            "generated from paper/crpto_ijds.qmd",
            "0.8957",
            "1,080",
            "objective-matched",
            "normalized-score",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "docs/research/active_claims_2026-07-12.md",
        (
            "source of truth",
            "0.838531",
            "0.895654",
            "8.33e-17",
            "216",
            "155,937.27",
            "no gamma, ruler, coordinate, or policy winner",
            "no policy winner",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/CLAIM_AUDIT_MATRIX.md",
        ("0.838531", "0.895654", "3,067", "216", "two-ruler"),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
        (
            TITLE,
            "376,890",
            "0.8970",
            "0.1017",
            "0.0971",
            "216",
            "5,603.66",
            "openai codex",
            "accepts full responsibility",
        ),
        RETIRED_HEADLINE_TOKENS,
    ),
    SurfaceCheck(
        REPO / "configs/crpto_publication_targets.yaml",
        (
            "active_claims_2026-07-12.md",
            "ijds-binary-geometry-frontier-v4-2026-07-12-v1",
            "ijds-binary-geometry-frontier-v4-2026-07-12-v2",
            "ijds-normalized-objective-frontier-2026-07-13-v1c",
            "ijds-normalized-objective-frontier-2026-07-13-v2",
            "0.838531",
            "0.895654",
            "policy_winner_allowed: false",
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
        failures.extend(
            f"{path.relative_to(REPO)}: retired headline token '{token}'"
            for token in RETIRED_HEADLINE_TOKENS
            if _normalize(token) in normalized
        )
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
    path = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
    if not path.is_file():
        return ["active evidence manifest is missing"]
    evidence = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    boundary = evidence["claim_boundary"]
    if boundary["policy_winner"] is not False:
        failures.append("active evidence unexpectedly allows a policy winner")
    if boundary["confirmatory"] is not False or boundary["prospective"] is not False:
        failures.append("active evidence misstates its retrospective boundary")
    if not evidence["coverage"]["catboost_all_eight_upper_below_nominal"]:
        failures.append("CatBoost coverage no longer fails in all eight windows")
    if not evidence["coverage"]["logistic_all_eight_upper_below_nominal"]:
        failures.append("logistic coverage no longer fails in all eight windows")
    if not evidence["portfolio"]["broad_stress_all_envelopes_cross_zero"]:
        failures.append("broad comparator support no longer crosses zero everywhere")
    if evidence["simulation"]["portfolio_claim_allowed"] is not False:
        failures.append("degenerate simulation unexpectedly allows a portfolio claim")
    challenger = evidence.get("decision_challenger", {})
    if challenger.get("scope") != "finite_two_ruler_three_interior_coordinate_diagnostic":
        failures.append("two-ruler finite diagnostic is missing")
    if challenger.get("continuous_frontier_claim") is not False:
        failures.append("two-ruler evidence unexpectedly claims a continuous frontier")
    if challenger.get("tracks_are_independent_replications") is not False:
        failures.append("two-ruler tracks are incorrectly treated as replications")
    interpretation = challenger.get("interpretation", {})
    for field in ("preferred_gamma", "preferred_ruler", "preferred_coordinate", "policy_winner"):
        if interpretation.get(field) is not None:
            failures.append(f"two-ruler evidence unexpectedly selects {field}")
    return failures


def check_publication_integrity() -> list[str]:
    """Return every active-paper synchronization or anonymity failure."""
    return [
        *_check_surface_contracts(),
        *_check_retired_headlines(),
        *_check_reviewer_anonymity(),
        *_check_evidence_decision(),
    ]


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
