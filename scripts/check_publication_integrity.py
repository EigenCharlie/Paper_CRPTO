"""Check active IJDS surfaces for evidence, narrative, and anonymity drift."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from loguru import logger

from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.publication_generation import publication_implementation_descriptors
from src.ijds_audit.publication_sources import load_verified_source_registry

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
SOURCE_REGISTRY_PATH = REPO / "configs/ijds_active_evidence_sources.yaml"
PUBLICATION_TARGETS_PATH = REPO / "configs/crpto_publication_targets.yaml"
CLAIM_LEDGER_PATH = REPO / "configs/ijds_claim_ledger.yaml"


@dataclass(frozen=True)
class SurfaceCheck:
    path: Path
    required: tuple[str, ...]


TITLE = "crpto: auditing binary conformal geometry and portfolio comparators"

REVIEWER_SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
    REPO / "paper/submission/ANONYMOUS_REVIEW_ARCHIVE_README.md",
    REPO / "paper/submission/TITLE_PAGE_DRAFT.md",
    REPO / "paper/submission/COVER_LETTER_AND_DISCLOSURE.md",
)

ACTIVE_EDITORIAL_SURFACES = (
    REPO / ".codex/skills/crpto/SKILL.md",
    REPO / "CLAUDE.md",
    REPO / "AGENTS.md",
    REPO / "CONTRIBUTING.md",
    REPO / "docs/ACADEMIC_CONTEXT.md",
    REPO / "docs/SCOPE_AND_GOVERNANCE.md",
    REPO / "docs/research/active_claims_2026-07-14.md",
    REPO / "paper/README.md",
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

RETIRED_CLAIM_TOKENS = (
    "0.838531",
    "0.895654",
    "0.896973",
    "favorable at .25",
    "favorable at 0.25",
    "5,603.66 higher",
    "small favorable",
    "borrower-only",
    "calibration-in-the-large",
    "september 2020 administrative snapshot",
    "four independent controls",
    "ijds-binary-geometry-frontier-v4-2026-07-12-v2",
    "ijds-normalized-objective-frontier-2026-07-13-v2",
    "ijds-credit-risk-controls-2026-07-13-v2b",
    "active_claims_2026-07-12.md",
)

SURFACES = (
    SurfaceCheck(
        REPO / "paper/CRPTO_ijds.qmd",
        (
            TITLE,
            "reconstructed",
            "not a verified point-in-time snapshot",
            "two rulers constructed without policy-development or OOT evaluation outcomes",
            "objective-matched",
            "normalized-score",
            "crosses zero",
            "not a prospective trial",
            "ethical and governance implications",
        ),
    ),
    SurfaceCheck(
        REPO / "paper/supplement_ijds.qmd",
        (
            TITLE,
            "reconstructed",
            "label-lag sensitivity",
            "not independent replications",
            "coordinate one",
            "missingness-encoding sensitivity",
            "second temporal origin",
        ),
    ),
    SurfaceCheck(
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        (
            TITLE,
            "generated from paper/crpto_ijds.qmd",
            "objective-matched",
            "normalized-score",
        ),
    ),
    SurfaceCheck(
        REPO / "docs/research/active_claims_2026-07-14.md",
        (
            "sole claim registry",
            "0.842485",
            "0.897726",
            "12,076",
            "no endpoint has a universal status-indexed outcome ordering",
        ),
    ),
    SurfaceCheck(
        REPO / "configs/crpto_publication_targets.yaml",
        (
            "active_claims_2026-07-14.md",
            "lineage_and_dvc_authority",
            "configs/ijds_active_evidence_sources.yaml",
            "policy_winner_allowed: false",
        ),
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


def _evidence() -> dict:
    payload: object = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{EVIDENCE_PATH} must contain a JSON object")
    return payload


def _check_surface_contracts() -> list[str]:
    failures: list[str] = []
    for surface in SURFACES:
        if not surface.path.is_file():
            failures.append(f"{surface.path.relative_to(REPO)} is missing")
            continue
        text = _normalize(surface.path.read_text(encoding="utf-8"))
        failures.extend(
            f"{surface.path.relative_to(REPO)}: missing required token '{token}'"
            for token in surface.required
            if _normalize(token) not in text
        )
    return failures


def _check_numeric_sync() -> list[str]:
    evidence = _evidence()
    design = evidence["design"]
    expected = (
        f"{design['primary_oot_candidates']:,}",
        f"{design['primary_oot_resolved']:,}",
        f"{design['primary_oot_unresolved']:,}",
    )
    failures: list[str] = []
    for path in (
        REPO / "paper/CRPTO_ijds.qmd",
        REPO / "paper/supplement_ijds.qmd",
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
    ):
        text = _normalize(path.read_text(encoding="utf-8"))
        failures.extend(
            f"{path.relative_to(REPO)}: missing evidence census '{token}'"
            for token in expected
            if _normalize(token) not in text
        )
    return failures


def _check_endpoint_reason_partition() -> list[str]:
    """Require the active reason census wherever the endpoint is reported."""
    required = ("307,842", "56,972", "11,551", "47", "478", "364,814", "12,076")
    failures: list[str] = []
    for path in (
        REPO / "paper/CRPTO_ijds.qmd",
        REPO / "paper/supplement_ijds.qmd",
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        REPO / "docs/research/active_claims_2026-07-14.md",
    ):
        text = _normalize(path.read_text(encoding="utf-8"))
        failures.extend(
            f"{path.relative_to(REPO)}: incomplete endpoint-reason partition '{token}'"
            for token in required
            if token not in text
        )
    return failures


def _check_retired_claims() -> list[str]:
    failures: list[str] = []
    for path in ACTIVE_EDITORIAL_SURFACES:
        if not path.is_file():
            failures.append(f"{path.relative_to(REPO)} is missing")
            continue
        text = _normalize(path.read_text(encoding="utf-8"))
        failures.extend(
            f"{path.relative_to(REPO)}: retired claim token '{token}'"
            for token in RETIRED_CLAIM_TOKENS
            if _normalize(token) in text
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
    evidence = _evidence()
    failures: list[str] = []
    boundary = evidence["claim_boundary"]
    for field in ("policy_winner", "confirmatory", "prospective", "causal"):
        if boundary[field] is not False:
            failures.append(f"active evidence unexpectedly allows {field}")
    if evidence["design"]["archive_is_verified_point_in_time_snapshot"] is not False:
        failures.append("active evidence misstates the archive as a point-in-time snapshot")
    if not evidence["credit_risk_controls"]["all_five_all_eight_upper_below_nominal"]:
        failures.append("five-model coverage result no longer holds")
    if not evidence["portfolio"]["broad_stress_all_envelopes_cross_zero"]:
        failures.append("broad comparator support no longer crosses zero everywhere")
    lag = evidence["binary_phase_transition"]["label_lag_sensitivity"]
    if not lag["w7_to_w8_threshold_crossing_at_all_admissible_lags"]:
        failures.append("phase crossing no longer survives all admissible reporting lags")
    tie = evidence["portfolio"]["evaluated_point_cap_solver_stability"]
    if tie["near_zero_bases"] != 0 or tie["tie_sensitive_rows"] != 0:
        failures.append("evaluated point-cap solver stability no longer holds")
    challenger = evidence["decision_challenger"]
    interpretation = challenger["interpretation"]
    for field in ("preferred_gamma", "preferred_ruler", "preferred_coordinate", "policy_winner"):
        if interpretation[field] is not None:
            failures.append(f"two-ruler evidence unexpectedly selects {field}")
    quarter = next(
        row
        for row in challenger["rows"]
        if row["ruler"] == "objective_matched" and row["coordinate"] == 0.25
    )
    for field in (
        "payoff_direction_pattern",
        "default_direction_pattern",
        "miscoverage_direction_pattern",
    ):
        if quarter[field] != "crosses_zero:8":
            failures.append(f"objective-matched .25 unexpectedly changed: {field}")
    if (
        evidence["evaluation_endpoint"].get("reason_census_partitions_primary_candidates")
        is not True
    ):
        failures.append("endpoint reasons no longer partition the primary candidate census")
    endpoint = evidence.get("sensitivity", {}).get("evaluation_endpoint_availability", {})
    if endpoint.get("six_month_endpoint_reconciles_to_active_evaluation") is not True:
        failures.append("endpoint sensitivity no longer reconciles to the active evaluation")
    if endpoint.get("endpoint_or_result_selected") is not False:
        failures.append("endpoint sensitivity unexpectedly selects an endpoint or result")
    if endpoint.get("fit_label_lag_crossed_factorially") is not False:
        failures.append("separate timing sensitivities are incorrectly reported as factorial")
    missingness = evidence.get("sensitivity", {}).get("missingness_encoding", {})
    if missingness.get("all_three_all_eight_upper_below_nominal") is not True:
        failures.append("missingness-encoding coverage recurrence no longer holds")
    if missingness.get("model_or_encoding_selected") is not False:
        failures.append("missingness sensitivity unexpectedly selects a model or encoding")
    rolling = evidence.get("sensitivity", {}).get("rolling_origin", {})
    if rolling.get("all_sixteen_upper_below_nominal") is not True:
        failures.append("two-origin coverage recurrence no longer holds")
    if rolling.get("independent_replication_claim_authorized") is not False:
        failures.append("second origin is incorrectly reported as an independent replication")
    return failures


def _check_claim_ledger() -> list[str]:
    """Require every active qualitative claim to resolve and appear only where allowed."""
    evidence = _evidence()
    try:
        expected = materialize_claim_ledger(
            CLAIM_LEDGER_PATH,
            evidence=evidence,
            repo_root=REPO,
        )
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        return [f"active claim ledger failed verification: {error}"]
    if evidence.get("claim_ledger") != expected:
        return ["evidence manifest claim ledger differs from the executable contract"]
    return []


def _check_lineage_sync() -> list[str]:
    """Verify identities and DVC pointers against the single source registry."""
    failures: list[str] = []
    try:
        registry, registered = load_verified_source_registry(
            SOURCE_REGISTRY_PATH,
            repo_root=REPO,
        )
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        return [f"active source registry failed verification: {error}"]
    evidence = _evidence()
    targets = yaml.safe_load(PUBLICATION_TARGETS_PATH.read_text(encoding="utf-8"))
    contract = targets.get("active_scientific_contract", {}) if isinstance(targets, dict) else {}
    expected_registry_path = SOURCE_REGISTRY_PATH.relative_to(REPO).as_posix()
    if contract.get("source_registry") != expected_registry_path:
        failures.append("publication target does not consume the active source registry")
    if contract.get("lineage_and_dvc_authority") != expected_registry_path:
        failures.append("publication target duplicates or omits lineage/DVC authority")
    if evidence.get("lineages") != registry["lineages"]:
        failures.append("evidence manifest lineages differ from the active source registry")
    if evidence.get("sensitivities") != registry.get("sensitivities"):
        failures.append("evidence manifest sensitivities differ from the active source registry")
    expected_source_registry = {
        "schema_version": str(registry["schema_version"]),
        "status": str(registry["status"]),
        "sources": sorted(registered),
    }
    if evidence.get("source_registry") != expected_source_registry:
        failures.append("evidence manifest source-registry identity changed")
    binary = registry["lineages"]["binary_geometry"]["evaluation"]
    for field in ("run_tag", "protocol_tag", "protocol_commit"):
        if evidence.get(field) != binary[field]:
            failures.append(f"active binary evidence {field} differs from the registry")
    two_ruler = registry["lineages"]["two_ruler"]["evaluation"]
    challenger = evidence.get("decision_challenger", {})
    for field in ("run_tag", "protocol_tag", "protocol_commit"):
        if challenger.get(field) != two_ruler[field]:
            failures.append(f"two-ruler {field} differs from the registry")
    endpoint = registry["sensitivities"]["endpoint_availability"]
    endpoint_evidence = evidence.get("sensitivity", {}).get("evaluation_endpoint_availability", {})
    for field in ("run_tag", "protocol_tag", "protocol_commit"):
        if endpoint_evidence.get(field) != endpoint[field]:
            failures.append(f"endpoint sensitivity {field} differs from the registry")
    expected_descriptors = publication_implementation_descriptors(REPO)
    evidence_sources = evidence.get("source_artifacts", {})
    for name, descriptor in expected_descriptors.items():
        if evidence_sources.get(name) != descriptor:
            failures.append(f"evidence manifest does not bind the current {name}")
    for pointer in registry["dvc_pointers"]:
        if not (REPO / pointer).is_file():
            failures.append(f"active DVC pointer is missing: {pointer}")
    return failures


def check_publication_integrity() -> list[str]:
    return [
        *_check_surface_contracts(),
        *_check_numeric_sync(),
        *_check_endpoint_reason_partition(),
        *_check_retired_claims(),
        *_check_reviewer_anonymity(),
        *_check_evidence_decision(),
        *_check_claim_ledger(),
        *_check_lineage_sync(),
    ]


def main() -> int:
    failures = check_publication_integrity()
    if failures:
        for failure in failures:
            logger.error(failure)
        return 1
    logger.info("Active IJDS publication integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
