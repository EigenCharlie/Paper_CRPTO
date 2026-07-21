"""Check active IJDS surfaces for evidence, narrative, and anonymity drift."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
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


TITLE = "crpto: an identification audit of binary conformal credit portfolio optimization"

REVIEWER_SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
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
            "exact combined-rank",
            "label-mondrian",
            "equal-follow-up",
            "39-month",
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
            "exact combined-rank",
            "label-mondrian",
            "equal-follow-up",
            "39-month",
        ),
    ),
    SurfaceCheck(
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        (
            TITLE,
            "generated from paper/crpto_ijds.qmd",
            "objective-matched",
            "normalized-score",
            "exact combined-rank",
            "label-mondrian",
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
            "31/40",
            "0.877685",
        ),
    ),
    SurfaceCheck(
        REPO / "configs/crpto_publication_targets.yaml",
        (
            "active_claims_2026-07-14.md",
            "lineage_and_dvc_authority",
            "configs/ijds_active_evidence_sources.yaml",
            "policy_winner_allowed: false",
            "run_ijds_exchangeability_transport_test.py",
            "run_ijds_rolling_origin_equal_followup.py",
            "run_ijds_label_mondrian_freeze.py",
            "run_ijds_label_mondrian_evaluation.py",
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
    boundary = evidence["claim_boundary"]
    lag = evidence["binary_phase_transition"]["label_lag_sensitivity"]
    tie = evidence["portfolio"]["evaluated_point_cap_solver_stability"]
    challenger = evidence["decision_challenger"]
    interpretation = challenger["interpretation"]
    endpoint = evidence.get("sensitivity", {}).get("evaluation_endpoint_availability", {})
    missingness = evidence.get("sensitivity", {}).get("missingness_encoding", {})
    rolling = evidence.get("sensitivity", {}).get("rolling_origin", {})
    conformal_set = evidence.get("conformal_set_diagnostics", {})
    exact = evidence.get("exchangeability_transport_test", {})
    label_mondrian = evidence.get("sensitivity", {}).get("label_mondrian", {})

    checks = [
        *(
            (boundary[field] is not False, f"active evidence unexpectedly allows {field}")
            for field in ("policy_winner", "confirmatory", "prospective", "causal")
        ),
        (
            evidence["design"]["archive_is_verified_point_in_time_snapshot"] is not False,
            "active evidence misstates the archive as a point-in-time snapshot",
        ),
        (
            evidence["credit_risk_controls"]["all_five_all_eight_upper_below_nominal"] is not True,
            "five-model coverage result no longer holds",
        ),
        (
            evidence["portfolio"]["broad_stress_all_envelopes_cross_zero"] is not True,
            "broad comparator support no longer crosses zero everywhere",
        ),
        (
            lag["w7_to_w8_threshold_crossing_at_all_admissible_lags"] is not True,
            "phase crossing no longer survives all admissible reporting lags",
        ),
        (
            tie["near_zero_bases"] != 0 or tie["tie_sensitive_rows"] != 0,
            "evaluated point-cap solver stability no longer holds",
        ),
        *(
            (
                interpretation[field] is not None,
                f"two-ruler evidence unexpectedly selects {field}",
            )
            for field in (
                "preferred_gamma",
                "preferred_ruler",
                "preferred_coordinate",
                "policy_winner",
            )
        ),
        (
            evidence["evaluation_endpoint"].get("reason_census_partitions_primary_candidates")
            is not True,
            "endpoint reasons no longer partition the primary candidate census",
        ),
        (
            endpoint.get("six_month_endpoint_reconciles_to_active_evaluation") is not True,
            "endpoint sensitivity no longer reconciles to the active evaluation",
        ),
        (
            endpoint.get("endpoint_or_result_selected") is not False,
            "endpoint sensitivity unexpectedly selects an endpoint or result",
        ),
        (
            endpoint.get("fit_label_lag_crossed_factorially") is not False,
            "separate timing sensitivities are incorrectly reported as factorial",
        ),
        (
            missingness.get("all_three_all_eight_upper_below_nominal") is not True,
            "missingness-encoding coverage recurrence no longer holds",
        ),
        (
            missingness.get("model_or_encoding_selected") is not False,
            "missingness sensitivity unexpectedly selects a model or encoding",
        ),
        (
            rolling.get("all_sixteen_upper_below_nominal") is not True,
            "two-origin coverage recurrence no longer holds",
        ),
        (
            rolling.get("primary_2016_periods") != ["2016-04", "2016-05", "2016-06"]
            or rolling.get("rolling_2017_periods") != ["2017-04", "2017-05", "2017-06"]
            or rolling.get("common_followup_months_after_issue_quarter_end") != 39
            or rolling.get("approximate_followup_months_by_issue_month")
            != {"April": 41, "May": 40, "June": 39}
            or rolling.get("exact_loan_level_age_matched") is not False
            or rolling.get("evaluation_cutoffs")
            != {"primary_2016": "2019-09-30", "rolling_2017": "2020-09-30"}
            or rolling.get("primary_2016_census")
            != {"candidate_rows": 74537, "resolved_rows": 74120, "unresolved_rows": 417}
            or rolling.get("rolling_2017_census")
            != {"candidate_rows": 77105, "resolved_rows": 66091, "unresolved_rows": 11014}
            or rolling.get("unequal_followup_runs_retained_as_provenance")
            != {
                "rolling_2017_run_tag": "ijds-rolling-origin-2017-2026-07-15-v4",
                "primary_2016_recovery_run_tag": (
                    "ijds-rolling-origin-primary-recovery-2026-07-21-v1"
                ),
            }
            or any(
                row.get("candidate_rows") == 376890
                for row in rolling.get("rows", [])
                if row.get("origin_id") == "primary_2016"
            ),
            "two-origin coverage comparison no longer uses cutoffs 39 months after quarter end",
        ),
        (
            rolling.get("independent_replication_claim_authorized") is not False,
            "second origin is incorrectly reported as an independent replication",
        ),
        (
            conformal_set.get("learner_window_cells") != 40
            or conformal_set.get("all_forty_resolved_y0_coverage_above_y1") is not True
            or conformal_set.get("interpretation", {}).get("label_conditional_guarantee")
            is not False
            or conformal_set.get("interpretation", {}).get(
                "all_candidate_label_conditional_coverage_estimated"
            )
            is not False
            or conformal_set.get("interpretation", {}).get("fairness_or_equalized_coverage_claim")
            is not False,
            "complete conformal-set diagnostic or its claim boundary changed",
        ),
        (
            exact.get("thirty_one_of_forty_meet_locked_nominal_thresholds") is not True
            or exact.get("cells_meeting_locked_nominal_thresholds") != 31
            or exact.get("cells_not_meeting_locked_nominal_thresholds") != 9
            or len(exact.get("cell_rows", [])) != 40
            or len(exact.get("stratum_rows", [])) != 200
            or exact.get("multiplicity", {}).get("stratum_flags_control_global_200_test_fwer")
            is not False
            or exact.get("multiplicity", {}).get("post_selection_fwer_control_claimed") is not False
            or exact.get("rank_null", {}).get(
                "stronger_than_single_future_point_split_conformal_condition"
            )
            is not True
            or exact.get("interpretation", {}).get("preregistered") is not False
            or exact.get("interpretation", {}).get("confirmatory") is not False
            or exact.get("interpretation", {}).get("nonflag_establishes_exchangeability")
            is not False
            or exact.get("interpretation", {}).get("flag_identifies_cause_of_shift") is not False,
            "joint-block rank reference or its post-inspection boundary changed",
        ),
        (
            label_mondrian.get("counts")
            != {
                "learner_window_cells": 40,
                "threshold_cells": 400,
                "target_category_cells": 400,
                "target_stratum_cells": 200,
                "learners": 5,
                "windows_per_learner": 8,
                "score_strata": 5,
                "labels": 2,
                "candidate_rows": 376890,
                "resolved_rows": 364814,
                "unresolved_rows": 12076,
            }
            or label_mondrian.get("learner_window_states")
            != {
                "robust_shortfall": 27,
                "robust_at_or_above_nominal": 1,
                "crosses_nominal": 12,
            }
            or label_mondrian.get("category_states")
            != {
                "crosses_nominal": 185,
                "robust_shortfall": 109,
                "robust_at_or_above_nominal": 106,
            }
            or label_mondrian.get("mixed_category_identification_states") is not True
            or label_mondrian.get("all_forty_aggregate_class_gap_bounds_cross_zero") is not True
            or label_mondrian.get("interpretation", {}).get("label_conditional_transport_guarantee")
            is not False
            or label_mondrian.get("interpretation", {}).get("fairness_claim") is not False,
            "label-Mondrian sensitivity or its interpretation boundary changed",
        ),
    ]
    failures = [message for failed, message in checks if failed]
    quarter = next(
        row
        for row in challenger["rows"]
        if row["ruler"] == "objective_matched" and row["coordinate"] == 0.25
    )
    failures.extend(
        f"objective-matched .25 unexpectedly changed: {field}"
        for field in (
            "payoff_direction_pattern",
            "default_direction_pattern",
            "miscoverage_direction_pattern",
        )
        if quarter[field] != "crosses_zero:8"
    )
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


def _identity_mismatches(
    actual: Mapping[str, object],
    expected: Mapping[str, object],
    *,
    label: str,
) -> list[str]:
    return [
        f"{label} {field} differs from the registry"
        for field in ("run_tag", "protocol_tag", "protocol_commit")
        if actual.get(field) != expected.get(field)
    ]


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
    expected_source_registry = {
        "schema_version": str(registry["schema_version"]),
        "status": str(registry["status"]),
        "sources": sorted(registered),
    }
    checks = (
        (
            str(registry.get("schema_version")) != "2026-07-21.2",
            "active source registry schema is not 2026-07-21.2",
        ),
        (
            len(registry.get("dvc_pointers", [])) != 45,
            "active source registry does not contain exactly 45 DVC pointers",
        ),
        (
            len(
                [
                    descriptor
                    for descriptor in evidence.get("paper_artifacts", {}).values()
                    if str(descriptor.get("path", "")).endswith(".csv")
                ]
            )
            != 25,
            "paper evidence manifest does not contain exactly 25 CSV tables",
        ),
        (
            contract.get("source_registry") != expected_registry_path,
            "publication target does not consume the active source registry",
        ),
        (
            contract.get("lineage_and_dvc_authority") != expected_registry_path,
            "publication target duplicates or omits lineage/DVC authority",
        ),
        (
            evidence.get("lineages") != registry["lineages"],
            "evidence manifest lineages differ from the active source registry",
        ),
        (
            evidence.get("sensitivities") != registry.get("sensitivities"),
            "evidence manifest sensitivities differ from the active source registry",
        ),
        (
            evidence.get("source_registry") != expected_source_registry,
            "evidence manifest source-registry identity changed",
        ),
    )
    failures.extend(message for failed, message in checks if failed)

    binary = registry["lineages"]["binary_geometry"]["evaluation"]
    failures.extend(_identity_mismatches(evidence, binary, label="active binary evidence"))
    two_ruler = registry["lineages"]["two_ruler"]["evaluation"]
    challenger = evidence.get("decision_challenger", {})
    failures.extend(_identity_mismatches(challenger, two_ruler, label="two-ruler"))
    endpoint = registry["sensitivities"]["endpoint_availability"]
    endpoint_evidence = evidence.get("sensitivity", {}).get("evaluation_endpoint_availability", {})
    failures.extend(_identity_mismatches(endpoint_evidence, endpoint, label="endpoint sensitivity"))
    exact_registry = registry["lineages"]["diagnostics"]["exchangeability_transport_test"]
    failures.extend(
        _identity_mismatches(
            evidence.get("exchangeability_transport_test", {}),
            exact_registry,
            label="exact exchangeability diagnostic",
        )
    )
    rolling_registry = registry["sensitivities"]["rolling_origin_equal_followup"]
    failures.extend(
        _identity_mismatches(
            evidence.get("sensitivity", {}).get("rolling_origin", {}),
            rolling_registry,
            label="equal-follow-up sensitivity",
        )
    )
    label_registry = registry["sensitivities"]["label_mondrian"]
    label_evidence = evidence.get("sensitivity", {}).get("label_mondrian", {})
    failures.extend(
        _identity_mismatches(
            label_evidence,
            label_registry["evaluation"],
            label="label-Mondrian evaluation",
        )
    )
    if label_evidence.get("freeze_run_tag") != label_registry["outcome_free"].get("run_tag"):
        failures.append("label-Mondrian outcome-free freeze differs from the registry")
    expected_descriptors = publication_implementation_descriptors(REPO)
    evidence_sources = evidence.get("source_artifacts", {})
    failures.extend(
        f"evidence manifest does not bind the current {name}"
        for name, descriptor in expected_descriptors.items()
        if evidence_sources.get(name) != descriptor
    )
    failures.extend(
        f"active DVC pointer is missing: {pointer}"
        for pointer in registry["dvc_pointers"]
        if not (REPO / pointer).is_file()
    )
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
