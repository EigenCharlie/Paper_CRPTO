"""Check active IJDS surfaces for evidence, narrative, and anonymity drift."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from loguru import logger

from src.ijds_audit.claim_ledger import materialize_claim_ledger
from src.ijds_audit.publication_generation import publication_implementation_descriptors
from src.ijds_audit.publication_sources import (
    load_verified_or_sealed_source_registry,
    load_verified_source_registry,
)
from src.utils.artifact_descriptor import verified_artifact_path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
SOURCE_REGISTRY_PATH = REPO / "configs/ijds_active_evidence_sources.yaml"
PUBLICATION_TARGETS_PATH = REPO / "configs/crpto_publication_targets.yaml"
CLAIM_LEDGER_PATH = REPO / "configs/ijds_claim_ledger.yaml"

EXPECTED_REGISTRY_SCHEMA = "2026-08-01.1"
EXPECTED_DVC_POINTERS = 53
EXPECTED_CSV_TABLES = 45
SEALED_PARENT_COMMIT = "6e9086ed57492325787498d912b3f5f3e03458bf"
SEALED_PARENT_MANIFEST_PATH = "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json"
SEALED_PARENT_REGISTRY_PATH = "configs/ijds_active_evidence_sources.yaml"
SEALED_PARENT_MANIFEST_BYTES = 3_500_642
SEALED_PARENT_MANIFEST_SHA256 = "02122d92270425540fba930de574e3b8abc940cc667b3a34f32f5504e21bb5e4"
EXPECTED_INCREMENTAL_MISSING_DVC_SOURCES = 33

EXPECTED_SCIENTIFIC_GIT_LINEAGES = (
    "lineages.diagnostics.binary_phase_census",
    "lineages.diagnostics.common_panel_threshold_response",
    "lineages.diagnostics.decision_catalog_transport",
    "lineages.diagnostics.dual_coefficient_binary_set_native",
    "lineages.diagnostics.funded_selection_estimands",
    "lineages.diagnostics.marginal_score_outcome_gap",
    "lineages.diagnostics.residual_transport_frontier",
    "lineages.diagnostics.score_equivalence_complete_hull",
    "lineages.diagnostics.set_native_binary_robust_counterpart",
    "lineages.diagnostics.set_preserving_embedding",
    "sensitivities.calibrator_family",
)


@dataclass(frozen=True)
class SurfaceCheck:
    path: Path
    required: tuple[str, ...]


@dataclass(frozen=True)
class SourceRegistryVerification:
    """Verified active registry, including a narrowly sealed incremental state."""

    registry: dict[str, Any]
    registered: dict[str, Path]
    missing_dvc_sources: tuple[str, ...]
    mode: str


def _sealed_parent_manifest(*, repo_root: Path = REPO) -> Mapping[str, Any]:
    """Return the byte-pinned parent manifest used by the incremental bridge."""
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SEALED_PARENT_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("The sealed publication parent is not an ancestor of HEAD.")
    blob = subprocess.run(
        [
            "git",
            "cat-file",
            "blob",
            f"{SEALED_PARENT_COMMIT}:{SEALED_PARENT_MANIFEST_PATH}",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if blob.returncode != 0:
        raise RuntimeError("The sealed parent publication manifest Git blob is absent.")
    actual_bytes = len(blob.stdout)
    actual_sha256 = hashlib.sha256(blob.stdout).hexdigest()
    if (
        actual_bytes != SEALED_PARENT_MANIFEST_BYTES
        or actual_sha256 != SEALED_PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError(
            "The sealed parent publication manifest differs from its exact byte/hash pin."
        )
    payload = json.loads(blob.stdout)
    if not isinstance(payload, Mapping) or payload.get("schema_version") != "2026-07-31.1":
        raise RuntimeError("The sealed parent publication manifest has an invalid schema.")
    return payload


def _load_integrity_source_registry(
    registry_path: Path = SOURCE_REGISTRY_PATH,
    *,
    repo_root: Path = REPO,
) -> SourceRegistryVerification:
    """Use strict verification unless only the sealed 33-source DVC gap remains."""
    try:
        registry, registered = load_verified_source_registry(
            registry_path,
            repo_root=repo_root,
        )
    except FileNotFoundError as missing_error:
        _sealed_parent_manifest(repo_root=repo_root)
        registry, registered, missing = load_verified_or_sealed_source_registry(
            registry_path,
            repo_root=repo_root,
            sealed_parent_commit=SEALED_PARENT_COMMIT,
            sealed_parent_registry_path=SEALED_PARENT_REGISTRY_PATH,
        )
        if len(missing) != EXPECTED_INCREMENTAL_MISSING_DVC_SOURCES:
            raise RuntimeError(
                "Incremental publication verification requires exactly "
                f"{EXPECTED_INCREMENTAL_MISSING_DVC_SOURCES} absent DVC sources; "
                f"found {len(missing)}."
            ) from missing_error
        return SourceRegistryVerification(
            registry=registry,
            registered=registered,
            missing_dvc_sources=missing,
            mode="sealed_incremental",
        )
    return SourceRegistryVerification(
        registry=registry,
        registered=registered,
        missing_dvc_sources=(),
        mode="full",
    )


def _scientific_git_lineages(registry: Mapping[str, Any]) -> tuple[str, ...]:
    """Derive conceptual Git-native scientific lineages from registry contracts."""

    discovered: set[str] = set()
    lineages = registry.get("lineages")
    sensitivities = registry.get("sensitivities")
    if not isinstance(lineages, Mapping) or not isinstance(sensitivities, Mapping):
        raise TypeError("Active registry omits lineage or sensitivity mappings.")
    diagnostics = lineages.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        raise TypeError("Active registry omits diagnostic lineages.")

    for name, raw_identity in diagnostics.items():
        if not isinstance(raw_identity, Mapping):
            raise TypeError(f"Diagnostic lineage {name!r} is malformed.")
        stages = (
            raw_identity,
            *[value for value in raw_identity.values() if isinstance(value, Mapping)],
        )
        if any("artifact_tag" in stage or "source_artifact_tag" in stage for stage in stages):
            discovered.add(f"lineages.diagnostics.{name}")

    for name, raw_identity in sensitivities.items():
        if not isinstance(raw_identity, Mapping):
            raise TypeError(f"Sensitivity lineage {name!r} is malformed.")
        stages = (
            raw_identity,
            *[value for value in raw_identity.values() if isinstance(value, Mapping)],
        )
        if any("artifact_tag" in stage or "source_artifact_tag" in stage for stage in stages):
            discovered.add(f"sensitivities.{name}")

    return tuple(sorted(discovered))


TITLE = (
    "auditing binary conformal prediction in credit allocation: exact geometry, "
    "temporal-transport diagnostics, and comparator dependence"
)

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
            "finite-archive shortfall",
            "only primary CatBoost enters optimization",
            "score-Mondrian",
            "retrospective Label-Mondrian sensitivity",
            "model-implied plug-in objective",
            "status-indexed standardized payoff proxy",
            "sharp common-outcome bounds",
            "objective-matched",
            "normalized-score",
            "crosses zero",
            "not a prospective trial",
            "ethical and governance implications",
            "exact combined-rank",
            "label-mondrian",
            "individual-age",
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
            "only the primary CatBoost enters optimization",
            "active recipe is score-Mondrian",
            "label-Mondrian sensitivity",
            "model-implied plug-in objective",
            "status-indexed standardized payoff proxy",
            "sharp common-outcome bounds",
            "exact combined-rank",
            "label-mondrian",
            "individual-age",
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
            "individual-age",
        ),
    ),
    SurfaceCheck(
        REPO / "docs/research/active_claims_2026-07-14.md",
        (
            "sole claim registry",
            "0.842485",
            "0.897726",
            "12,076",
            "no path-end contrast has a universal status-indexed outcome ordering",
            "31/40",
            "0.879120",
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
            "run_ijds_rolling_origin_individual_age_followup.py",
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


def _check_calibrator_publication_payload() -> list[str]:
    """Fail closed on the complete, nonselective calibrator-family publication."""
    evidence = _evidence()
    calibrator = evidence.get("sensitivity", {}).get("calibrator_family", {})
    if not isinstance(calibrator, Mapping):
        return ["calibrator-family publication payload is missing"]
    fit_rows = calibrator.get("method_fit_rows")
    cell_rows = calibrator.get("cell_rows")
    pairwise_rows = calibrator.get("pairwise_rows")
    if (
        not isinstance(fit_rows, list)
        or not isinstance(cell_rows, list)
        or not isinstance(pairwise_rows, list)
        or any(not isinstance(row, Mapping) for row in (*fit_rows, *cell_rows, *pairwise_rows))
    ):
        return ["calibrator-family publication rows are malformed"]

    overall = [row for row in cell_rows if row.get("conformal_group") == -1]
    exact_boolean_flags = all(
        row.get("coverage_upper_below_nominal") in {True, False} for row in overall
    )
    below = sum(row.get("coverage_upper_below_nominal") is True for row in overall)
    at_or_above = sum(row.get("coverage_upper_below_nominal") is False for row in overall)
    methods = ("platt", "isotonic", "beta", "venn_abers")
    method_census = {
        method: {
            "upper_below_nominal": sum(
                row.get("coverage_upper_below_nominal") is True
                for row in overall
                if row.get("method") == method
            ),
            "upper_at_or_above_nominal": sum(
                row.get("coverage_upper_below_nominal") is False
                for row in overall
                if row.get("method") == method
            ),
        }
        for method in methods
    }
    expected_method_census = {
        "platt": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "isotonic": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
        "beta": {"upper_below_nominal": 8, "upper_at_or_above_nominal": 0},
        "venn_abers": {"upper_below_nominal": 1, "upper_at_or_above_nominal": 7},
    }
    method_summaries = {
        method: {
            "upper_below_nominal": method_census[method]["upper_below_nominal"],
            "coverage_lower_min": min(
                float(row["coverage_lower"]) for row in overall if row["method"] == method
            ),
            "coverage_upper_max": max(
                float(row["coverage_upper"]) for row in overall if row["method"] == method
            ),
            "coverage_resolved_min": min(
                float(row["coverage_resolved"]) for row in overall if row["method"] == method
            ),
            "coverage_resolved_max": max(
                float(row["coverage_resolved"]) for row in overall if row["method"] == method
            ),
            "average_set_size_min": min(
                float(row["average_set_size"]) for row in overall if row["method"] == method
            ),
            "average_set_size_max": max(
                float(row["average_set_size"]) for row in overall if row["method"] == method
            ),
        }
        for method in methods
    }

    pairwise_overall = [row for row in pairwise_rows if row["conformal_group"] == -1]
    pairwise_summaries: dict[str, dict[str, int | float | bool]] = {}
    for method_a in methods:
        for method_b in methods:
            if method_a == method_b:
                continue
            direct = [
                row
                for row in pairwise_overall
                if row["method_a"] == method_a and row["method_b"] == method_b
            ]
            if direct:
                lower = [float(row["coverage_difference_lower"]) for row in direct]
                upper = [float(row["coverage_difference_upper"]) for row in direct]
            else:
                reverse = [
                    row
                    for row in pairwise_overall
                    if row["method_a"] == method_b and row["method_b"] == method_a
                ]
                lower = [-float(row["coverage_difference_upper"]) for row in reverse]
                upper = [-float(row["coverage_difference_lower"]) for row in reverse]
                direct = reverse
            pairwise_summaries[f"{method_a}_minus_{method_b}"] = {
                "rows": len(direct),
                "lower_min": min(lower),
                "upper_max": max(upper),
                "all_bounds_strictly_positive": all(
                    lower_value > 0.0 and upper_value > 0.0
                    for lower_value, upper_value in zip(lower, upper, strict=True)
                ),
            }

    equality_columns = (
        "rows",
        "candidate_rows",
        "resolved_rows",
        "unresolved_rows",
        "coverage_resolved",
        "coverage_lower",
        "coverage_upper",
        "coverage_resolved_y0",
        "coverage_resolved_y1",
        "average_set_size",
        "singleton_share",
        "set_empty_count",
        "set_empty_share",
        "set_zero_only_count",
        "set_zero_only_share",
        "set_one_only_count",
        "set_one_only_share",
        "set_both_count",
        "set_both_share",
        "lower_positive_share",
        "upper_saturated_share",
    )
    indexed_cells = {
        (row["method"], row["window_id"], row["conformal_group"]): row for row in cell_rows
    }
    platt_keys = [
        (row["window_id"], row["conformal_group"]) for row in cell_rows if row["method"] == "platt"
    ]
    platt_beta_equal_cells = sum(
        all(
            indexed_cells[("platt", window_id, group)][column]
            == indexed_cells[("beta", window_id, group)][column]
            for column in equality_columns
        )
        for window_id, group in platt_keys
    )
    platt_overall = {row["window_id"]: row for row in overall if row["method"] == "platt"}
    alternative_set_geometry = {
        method: {
            "rows": len(rows),
            "zero_empty_set_cells": sum(int(row["set_empty_count"]) == 0 for row in rows),
            "two_label_count_greater_than_platt_cells": sum(
                int(row["set_both_count"])
                > int(platt_overall[str(row["window_id"])]["set_both_count"])
                for row in rows
            ),
        }
        for method in ("isotonic", "venn_abers")
        for rows in [[row for row in overall if row["method"] == method]]
    }
    derived_state = (
        "all_32_overall_upper_below_nominal"
        if len(overall) == 32 and below == 32
        else "uniform_closed_family_shortfall_not_established"
    )
    expected_counts = {
        "methods": 4,
        "windows": 8,
        "scopes_per_method_window": 6,
        "evaluation_cells": 192,
        "overall_cells": 32,
        "pairwise_cells": 288,
        "candidate_rows": 376890,
        "resolved_rows": 364814,
        "unresolved_rows": 12076,
        "resolved_y0": 307842,
        "resolved_y1": 56972,
    }
    findings = calibrator.get("findings")
    interpretation = calibrator.get("interpretation", {})
    artifacts = evidence.get("paper_artifacts", {})
    expected_artifacts = {
        "table/calibrator_fit_diagnostics": (
            "reports/crpto/tables/crpto_ijds_v4_tableS2C_calibrator_fit_diagnostics.csv"
        ),
        "table/calibrator_sensitivity_cells": (
            "reports/crpto/tables/crpto_ijds_v4_tableS6O_calibrator_sensitivity_cells.csv"
        ),
        "table/calibrator_pairwise_shared_completion": (
            "reports/crpto/tables/crpto_ijds_v4_tableS6P_calibrator_pairwise_shared_completion.csv"
        ),
    }
    forbidden_columns = ("allocation", "portfolio", "objective", "net_return")
    checks = (
        (
            calibrator.get("counts") != expected_counts
            or len(fit_rows) != 4
            or len(cell_rows) != 192
            or len(pairwise_rows) != 288,
            "calibrator-family 4/192/288 publication census changed",
        ),
        (
            len(overall) != 32
            or not exact_boolean_flags
            or below != 18
            or at_or_above != 14
            or method_census != expected_method_census,
            "calibrator-family pooled 18/14 result census changed",
        ),
        (
            calibrator.get("result_state") != derived_state
            or derived_state != "uniform_closed_family_shortfall_not_established",
            "calibrator-family published result state is not derived from the 32 pooled rows",
        ),
        (
            calibrator.get("overall_cells_with_coverage_upper_below_nominal") != below
            or calibrator.get("overall_cells_with_coverage_upper_at_or_above_nominal")
            != at_or_above
            or calibrator.get("overall_result_census_by_method") != method_census,
            "calibrator-family published result summaries disagree with their rows",
        ),
        (
            not isinstance(findings, Mapping)
            or findings.get("overall_method_summaries") != method_summaries
            or findings.get("pairwise_overall_summaries") != pairwise_summaries
            or findings.get("platt_beta_aggregate_equality_cells") != platt_beta_equal_cells
            or platt_beta_equal_cells != 48
            or findings.get("alternative_overall_set_geometry_census") != alternative_set_geometry
            or alternative_set_geometry
            != {
                "isotonic": {
                    "rows": 8,
                    "zero_empty_set_cells": 8,
                    "two_label_count_greater_than_platt_cells": 8,
                },
                "venn_abers": {
                    "rows": 8,
                    "zero_empty_set_cells": 8,
                    "two_label_count_greater_than_platt_cells": 8,
                },
            },
            "calibrator-family derived method, pairwise, or set-geometry findings "
            "disagree with their rows",
        ),
        (
            any(row.get("shared_loanwise_completion") is not True for row in pairwise_rows),
            "calibrator pairwise rows no longer use shared loanwise completion",
        ),
        (
            not isinstance(interpretation, Mapping)
            or interpretation.get("learner_calibrator_window_or_result_selected") is not False
            or interpretation.get("calibrator_winner") is not None
            or interpretation.get("selected_calibrator") is not None
            or interpretation.get("portfolio_score_changed") is not False
            or interpretation.get("portfolio_optimization") is not False
            or interpretation.get("portfolio_optimization_run") is not False
            or interpretation.get("pre_existing_platt_score_remains_primary_portfolio_score")
            is not True
            or interpretation.get("alternative_calibrator_maps_propagated_to_portfolio")
            is not False
            or interpretation.get(
                "uniform_shortfall_not_established_is_not_true_coverage_dependence"
            )
            is not True
            or interpretation.get("temporal_transport_established") is not False
            or interpretation.get("prospective_transport_established") is not False
            or interpretation.get(
                "venn_abers_multiprobability_guarantee_transported_to_scalarization"
            )
            is not False,
            "calibrator-family selection, Venn, or portfolio boundary changed",
        ),
        (
            not isinstance(artifacts, Mapping)
            or any(
                not isinstance(artifacts.get(name), Mapping) or artifacts[name].get("path") != path
                for name, path in expected_artifacts.items()
            ),
            "calibrator-family paper artifact descriptors are missing or misbound",
        ),
        (
            any(
                token in str(column).lower()
                for row in (*fit_rows, *cell_rows, *pairwise_rows)
                for column in row
                for token in forbidden_columns
            ),
            "calibrator-family publication rows leaked a portfolio field",
        ),
    )
    return [message for failed, message in checks if failed]


def _check_decision_representation_payload() -> list[str]:
    """Fail closed on the two complete decision-representation censuses."""
    evidence = _evidence()
    score = evidence.get("score_equivalence_complete_hull", {})
    set_native = evidence.get("set_native_binary_robust_counterpart", {})
    if not isinstance(score, Mapping) or not isinstance(set_native, Mapping):
        return ["decision-representation publication payload is missing"]

    expected_score_rows = [
        {
            "family": "v1d_embedding",
            "cell_group": "theta_zero_self",
            "cells": 1040,
            "equivalent_cells": 1040,
            "without_complete_hull_certificate": 0,
        },
        {
            "family": "v1d_embedding",
            "cell_group": "theta_positive_gamma_zero",
            "cells": 832,
            "equivalent_cells": 832,
            "without_complete_hull_certificate": 0,
        },
        {
            "family": "v1d_embedding",
            "cell_group": "theta_positive_gamma_positive",
            "cells": 3328,
            "equivalent_cells": 0,
            "without_complete_hull_certificate": 3328,
        },
        {
            "family": "closed_calibrator_q_gamma",
            "cell_group": "gamma_zero",
            "cells": 1248,
            "equivalent_cells": 0,
            "without_complete_hull_certificate": 1248,
        },
        {
            "family": "closed_calibrator_q_gamma",
            "cell_group": "gamma_positive",
            "cells": 4992,
            "equivalent_cells": 0,
            "without_complete_hull_certificate": 4992,
        },
    ]
    score_interpretation = score.get("interpretation", {})
    score_checks = (
        score.get("complete_census_verified") is True
        and score.get("complete_hulls") == 26
        and score.get("v1d_cells") == 5200
        and score.get("v1d_identity_equivalent_cells") == 1872
        and score.get("v1d_substantive_without_certificate") == 3328
        and score.get("calibrator_cells_without_certificate") == 6240
        and score.get("rows") == expected_score_rows
    )
    score_boundary = (
        isinstance(score_interpretation, Mapping)
        and score_interpretation.get("complete_candidate_menu_not_funded_support") is True
        and score_interpretation.get("outcome_free") is True
        and score_interpretation.get("optimization_run") is False
        and score_interpretation.get("failed_certificate_means_fixed_cell_allocation_change")
        is False
        and score_interpretation.get("common_solver_output_means_equal_optimal_faces") is False
        and score_interpretation.get("calibrator_common_objective_established") is False
        and score_interpretation.get("selected_embedding_or_calibrator") is False
        and score_interpretation.get("selected_or_funded_set_validity_claimed") is False
    )

    direction_rows = set_native.get("direction_rows")
    if not isinstance(direction_rows, list) or any(
        not isinstance(row, Mapping) for row in direction_rows
    ):
        return ["set-native direction rows are malformed"]
    metrics = (
        "standardized_payoff",
        "funded_default",
        "funded_binary_miscoverage",
    )
    monthly_totals = {
        metric: [
            sum(int(row[field]) for row in direction_rows if row.get("metric") == metric)
            for field in ("monthly_positive", "monthly_negative", "monthly_includes_zero")
        ]
        for metric in metrics
    }
    pooled_totals = {
        metric: [
            sum(int(row[field]) for row in direction_rows if row.get("metric") == metric)
            for field in ("pooled_positive", "pooled_negative", "pooled_includes_zero")
        ]
        for metric in metrics
    }
    expected_monthly_totals = {
        "standardized_payoff": [5840, 9853, 2307],
        "funded_default": [13992, 2462, 1546],
        "funded_binary_miscoverage": [11947, 4355, 1698],
    }
    expected_pooled_totals = {
        "standardized_payoff": [15, 1065, 120],
        "funded_default": [1196, 0, 4],
        "funded_binary_miscoverage": [1009, 120, 71],
    }
    set_interpretation = set_native.get("interpretation", {})
    set_census = (
        set_native.get("complete_census_verified") is True
        and set_native.get("phase_a_cells") == 1248
        and set_native.get("primary_cells") == 720
        and set_native.get("taxonomy_rows") == 208
        and set_native.get("solver_audit_rows") == 1248
        and set_native.get("funded_rows") == 126686
        and set_native.get("evaluated_robust_cells") == 720
        and set_native.get("monthly_contrasts") == 18000
        and set_native.get("pooled_contrasts") == 1200
        and len(direction_rows) == 75
        and all(row.get("monthly_cells") == 720 for row in direction_rows)
        and all(row.get("pooled_cells") == 48 for row in direction_rows)
        and monthly_totals == expected_monthly_totals
        and pooled_totals == expected_pooled_totals
        and set_native.get("monthly_sign_totals") == expected_monthly_totals
        and set_native.get("pooled_sign_totals") == expected_pooled_totals
        and set_native.get("sign_order") == ["positive", "negative", "includes_zero"]
    )
    set_boundary = (
        isinstance(set_interpretation, Mapping)
        and set_interpretation.get("set_native_score_uses_exact_binary_worst_label") is True
        and set_interpretation.get("empty_set_is_declared_fail_closed_convention") is True
        and set_interpretation.get("cartesian_product_joint_coverage_guarantee_established")
        is False
        and set_interpretation.get("probabilistic_robustness_claimed") is False
        and set_interpretation.get("conformal_validity_repair_claimed") is False
        and set_interpretation.get("selected_result_or_policy") is False
        and set_interpretation.get("causal_or_prospective_claimed") is False
        and set_interpretation.get("independent_replications_or_p_value_claimed") is False
        and set_native.get("selected_result") is None
        and set_native.get("policy_winner") is None
    )

    artifacts = evidence.get("paper_artifacts", {})
    expected_artifacts = {
        "table/score_equivalence_complete_hull": (
            "reports/crpto/tables/crpto_ijds_v4_tableS9M_score_equivalence_complete_hull.csv"
        ),
        "table/set_native_robust_minus_embedding": (
            "reports/crpto/tables/crpto_ijds_v4_tableS9N_set_native_robust_minus_embedding.csv"
        ),
    }
    artifact_binding = isinstance(artifacts, Mapping) and all(
        isinstance(artifacts.get(name), Mapping) and artifacts[name].get("path") == path
        for name, path in expected_artifacts.items()
    )
    checks = (
        (not score_checks, "complete-hull score-equivalence census changed"),
        (not score_boundary, "score-equivalence interpretation boundary changed"),
        (not set_census, "set-native robust-minus-embedding census changed"),
        (not set_boundary, "set-native interpretation boundary changed"),
        (not artifact_binding, "decision-representation publication tables are misbound"),
    )
    return [message for failed, message in checks if failed]


def _binary_phase_rows_are_complete(rows: object) -> bool:
    """Validate the exact 5-by-8-by-5 cell grid and its row-level gates."""
    if not isinstance(rows, list) or len(rows) != 200:
        return False
    forbidden_tokens = (
        "target",
        "outcome",
        "coverage",
        "selected",
        "selection",
        "optim",
        "allocation",
        "funded",
        "policy",
        "endpoint",
        "resolved",
        "unresolved",
    )
    keys: list[tuple[str, str, int]] = []
    for raw_row in rows:
        if not isinstance(raw_row, Mapping):
            return False
        row = cast(Mapping[str, Any], raw_row)
        learner = row.get("learner")
        window = row.get("window_id")
        group = row.get("conformal_group")
        if not isinstance(learner, str) or not isinstance(window, str):
            return False
        if not isinstance(group, int) or isinstance(group, bool) or group not in range(5):
            return False
        keys.append((learner, window, group))
        if any(token in str(column).lower() for column in row for token in forbidden_tokens):
            return False
        integer_fields = (
            "fit_rows",
            "fit_defaults",
            "fit_nondefaults",
            "finite_sample_rank",
            "boundary_count",
            "boundary_closed_form",
            "phase_margin",
            "recomputed_residual_below_threshold",
            "recomputed_residual_equal_threshold",
            "recomputed_residual_above_threshold",
            "frozen_residual_below_threshold",
            "frozen_residual_equal_threshold",
            "frozen_residual_above_threshold",
            "count_nondefault_score_below_half",
            "count_default_score_above_half",
        )
        if any(
            not isinstance(row.get(field), int) or isinstance(row.get(field), bool)
            for field in integer_fields
        ):
            return False
        fit_rows = int(row["fit_rows"])
        fit_defaults = int(row["fit_defaults"])
        fit_nondefaults = int(row["fit_nondefaults"])
        rank = int(row["finite_sample_rank"])
        below = int(row["recomputed_residual_below_threshold"])
        equal = int(row["recomputed_residual_equal_threshold"])
        above = int(row["recomputed_residual_above_threshold"])
        boolean_fields = (
            "threshold_below_half",
            "exact_half_criterion_expected",
            "exact_half_criterion_observed",
            "max_score_below_half_condition",
            "phase_margin_half_check_applicable",
            "no_interleaving_condition",
            "phase_margin_source_check_applicable",
        )
        if any(type(row.get(field)) is not bool for field in boolean_fields):
            return False
        threshold = row.get("recomputed_threshold")
        score_max = row.get("recomputed_score_max")
        score_max_nondefault = row.get("fit_score_max_nondefault")
        score_max_default = row.get("fit_score_max_default")
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in (threshold, score_max, score_max_nondefault, score_max_default)
        ):
            return False
        threshold_value = float(cast(int | float, threshold))
        score_max_value = float(cast(int | float, score_max))
        score_max_nondefault_value = float(cast(int | float, score_max_nondefault))
        score_max_default_value = float(cast(int | float, score_max_default))
        expected_half_criterion = (
            int(row["count_nondefault_score_below_half"])
            + int(row["count_default_score_above_half"])
            >= rank
        )
        if (
            row.get("taxonomy_groups") != 5
            or row.get("alpha") != 0.1
            or fit_defaults <= 0
            or fit_nondefaults <= 0
            or fit_defaults + fit_nondefaults != fit_rows
            or not (0 < rank <= fit_rows)
            or row.get("boundary_count") != fit_rows - rank
            or row.get("boundary_count") != (fit_rows + 1) // 10 - 1
            or row.get("boundary_closed_form") != row.get("boundary_count")
            or row.get("phase_margin") != fit_defaults - int(row["boundary_count"])
            or below + equal + above != fit_rows
            or not (below < rank <= below + equal)
            or row.get("frozen_fit_rows") != fit_rows
            or row.get("frozen_finite_sample_rank") != rank
            or row.get("frozen_threshold") != row.get("recomputed_threshold")
            or row.get("threshold_gap") != 0.0
            or row.get("frozen_residual_below_threshold") != below
            or row.get("frozen_residual_equal_threshold") != equal
            or row.get("frozen_residual_above_threshold") != above
            or row.get("frozen_score_min") != row.get("recomputed_score_min")
            or row.get("frozen_score_max") != score_max
            or row.get("threshold_below_half") is not (threshold_value < 0.5)
            or row.get("exact_half_criterion_expected") is not expected_half_criterion
            or row.get("exact_half_criterion_expected")
            is not row.get("exact_half_criterion_observed")
            or row.get("exact_half_criterion_observed") is not row.get("threshold_below_half")
            or row.get("max_score_below_half_condition") is not (score_max_value < 0.5)
            or row.get("phase_margin_half_check_applicable")
            is not row.get("max_score_below_half_condition")
            or row.get("no_interleaving_condition")
            is not (score_max_nondefault_value + score_max_default_value < 1.0)
            or row.get("phase_margin_source_check_applicable")
            is not row.get("no_interleaving_condition")
        ):
            return False
        required_true = (
            "both_classes_nonempty",
            "exact_half_criterion_pass",
            "phase_margin_half_check_pass",
            "phase_margin_source_check_pass",
            "boundary_identity_reconciles",
            "rows_reconcile",
            "rank_reconciles",
            "threshold_reconciles",
            "tie_counts_reconcile",
            "score_extrema_reconcile",
            "rank_bracket_reconciles",
            "cell_reconciles",
        )
        if any(row.get(field) is not True for field in required_true):
            return False
        applicable = row.get("phase_margin_source_check_applicable") is True
        expected_branch = (
            "nondefault_mirror"
            if applicable and int(row["phase_margin"]) <= 0
            else "default_mirror"
            if applicable
            else "condition_not_met"
        )
        if (
            row.get("expected_threshold_source_branch") != expected_branch
            or row.get("threshold_source_branch") != expected_branch
        ):
            return False

    learners = {learner for learner, _, _ in keys}
    windows = {window for _, window, _ in keys}
    expected_keys = {
        (learner, window, group) for learner in learners for window in windows for group in range(5)
    }
    return len(learners) == 5 and len(windows) == 8 and set(keys) == expected_keys


def _check_sealed_extension_payload(
    evidence_payload: Mapping[str, Any] | None = None,
    registry_payload: Mapping[str, Any] | None = None,
) -> list[str]:
    """Fail closed on the sealed phase-census and dual-coefficient extension."""
    evidence = evidence_payload if evidence_payload is not None else _evidence()
    if registry_payload is None:
        raw_registry = yaml.safe_load(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw_registry, Mapping):
            return ["sealed-extension source registry is malformed"]
        registry = cast(Mapping[str, Any], raw_registry)
    else:
        registry = registry_payload
    diagnostics = registry.get("lineages", {}).get("diagnostics", {})
    if not isinstance(diagnostics, Mapping):
        return ["sealed-extension diagnostic registry is missing"]
    phase_identity = diagnostics.get("binary_phase_census", {})
    dual_identity = diagnostics.get("dual_coefficient_binary_set_native", {})
    phase = evidence.get("binary_phase_census", {})
    dual = evidence.get("dual_coefficient_binary_set_native", {})
    if not all(
        isinstance(payload, Mapping) for payload in (phase_identity, dual_identity, phase, dual)
    ):
        return ["sealed phase-census or dual-coefficient payload is missing"]
    phase_identity = cast(Mapping[str, Any], phase_identity)
    dual_identity = cast(Mapping[str, Any], dual_identity)
    phase = cast(Mapping[str, Any], phase)
    dual = cast(Mapping[str, Any], dual)

    expected_phase_groups = [
        {
            "conformal_group": group,
            "cells": 40,
            "threshold_below_half": threshold_count,
            "phase_margin_nonpositive": threshold_count,
            "half_condition_applicable": half_applicable,
            "half_condition_inapplicable": 40 - half_applicable,
            "half_condition_failed_when_applicable": 0,
            "source_condition_applicable": source_applicable,
            "source_condition_inapplicable": 40 - source_applicable,
            "source_condition_failed_when_applicable": 0,
            "exact_half_failures": 0,
            "reconciliation_failures": 0,
        }
        for group, threshold_count, half_applicable, source_applicable in (
            (0, 40, 40, 40),
            (1, 40, 40, 40),
            (2, 7, 40, 40),
            (3, 0, 40, 40),
            (4, 0, 24, 28),
        )
    ]
    expected_phase_global = {
        "threshold_below_half": 87,
        "phase_margin_nonpositive": 87,
        "half_condition_applicable": 184,
        "half_condition_inapplicable": 16,
        "half_condition_failed_when_applicable": 0,
        "source_condition_applicable": 188,
        "source_condition_inapplicable": 12,
        "source_condition_failed_when_applicable": 0,
        "exact_half_failures": 0,
        "reconciliation_failures": 0,
    }
    phase_registry_identity = all(
        phase.get(field) == phase_identity.get(field)
        for field in (
            "run_tag",
            "protocol_tag",
            "protocol_commit",
            "artifact_tag",
            "artifact_commit",
        )
    )
    phase_census = (
        phase.get("scope") == "five_learners_by_eight_windows_by_five_frozen_score_strata"
        and phase.get("complete_census_verified") is True
        and phase.get("cells") == 200
        and phase.get("learner_count") == 5
        and phase.get("window_count") == 8
        and phase.get("conformal_group_count") == 5
        and phase.get("cells_per_conformal_group") == 40
        and phase.get("ordered_conformal_groups") == expected_phase_groups
        and phase.get("global") == expected_phase_global
        and _binary_phase_rows_are_complete(phase.get("rows"))
    )
    phase_interpretation = phase.get("interpretation", {})
    phase_boundary = (
        phase.get("retrospective") is True
        and phase.get("confirmatory") is False
        and phase.get("learner_window_breakdown_emitted") is False
        and phase.get("forbidden_columns") == []
        and isinstance(phase_interpretation, Mapping)
        and phase_interpretation.get("retrospective_complete_calibration_grid") is True
        and phase_interpretation.get("target_or_evaluation_endpoint_read") is False
        and phase_interpretation.get("all_strata_reported_without_selection") is True
        and phase_interpretation.get("condition_inapplicability_is_not_failure") is True
        and phase_interpretation.get("universal_phase_law_claimed") is False
        and phase_interpretation.get("coverage_transport_or_validity_claimed") is False
        and phase_interpretation.get("optimization_or_funded_policy_claimed") is False
        and phase_interpretation.get("causal_or_prospective_claimed") is False
    )

    dual_protocol = dual.get("protocol", {})
    dual_registry_identity = (
        dual.get("run_tag") == dual_identity.get("run_tag")
        and isinstance(dual_protocol, Mapping)
        and dual_protocol.get("tag") == dual_identity.get("protocol_tag")
        and dual_protocol.get("commit") == dual_identity.get("protocol_commit")
        and dual_protocol.get("tag_object") == "d4e1c400a5a0a2be3ad83661a3a796741b2f3363"
        and dual.get("artifact_tag") == dual_identity.get("artifact_tag")
        and dual.get("artifact_commit") == dual_identity.get("artifact_commit")
    )
    expected_role_rows = [
        {
            "role": "policy_development",
            "menu_certificates": 88,
            "windows": 8,
            "months_per_window": 11,
            "all_conditions_certified": True,
            "all_maximin_optimizers_singleton_zero": True,
            "continuous_cap_frontier_collapses": True,
            "cap_domain_lower": 0.0,
            "cap_domain_upper": 1.0,
            "new_optimizations": 0,
            "optimizer_unique_certified": False,
            "validity_claim_established": False,
        },
        {
            "role": "primary_oot",
            "menu_certificates": 120,
            "windows": 8,
            "months_per_window": 15,
            "all_conditions_certified": True,
            "all_maximin_optimizers_singleton_zero": True,
            "continuous_cap_frontier_collapses": True,
            "cap_domain_lower": 0.0,
            "cap_domain_upper": 1.0,
            "new_optimizations": 0,
            "optimizer_unique_certified": False,
            "validity_claim_established": False,
        },
    ]
    dual_census = (
        dual.get("scope")
        == "complete_outcome_free_dual_set_native_risk_and_maximin_payoff_certificate_census_"
        "over_all_frozen_primary_catboost_platt_menus"
        and dual.get("complete_certificate_census_verified") is True
        and dual.get("menu_certificates") == 208
        and dual.get("role_menu_certificates") == {"policy_development": 88, "primary_oot": 120}
        and dual.get("new_optimizations") == 0
        and dual.get("all_conditions_certified") is True
        and dual.get("all_maximin_optimizers_singleton_zero") is True
        and dual.get("continuous_cap_frontier_collapses") is True
        and dual.get("cap_domain") == [0.0, 1.0]
        and dual.get("conditional_on_inherited_constraint_and_payoff_contract") is True
        and dual.get("role_rows") == expected_role_rows
    )
    dual_interpretation = dual.get("interpretation", {})
    dual_boundary = (
        dual.get("raw_archive_read") is False
        and dual.get("outcome_columns_passed") == []
        and dual.get("selected_result") is None
        and dual.get("policy_winner") is None
        and dual.get("optimizer_unique_certified") is False
        and dual.get("conformal_validity_repair") is False
        and dual.get("joint_cartesian_product_coverage_established") is False
        and dual.get("probabilistic_robustness_guarantee") is False
        and dual.get("funded_or_selected_set_validity") is False
        and dual.get("causal_or_prospective_claim") is False
        and isinstance(dual_interpretation, Mapping)
        and dual_interpretation.get("conditional_substitution_theorem") is True
        and dual_interpretation.get("both_risk_and_payoff_coefficients_are_set_native") is True
        and dual_interpretation.get("empty_set_is_declared_fail_closed_convention") is True
        and dual_interpretation.get("continuous_cap_domain_certified") == [0.0, 1.0]
        and dual_interpretation.get("new_optimization_run") is False
        and dual_interpretation.get("true_zero_default_risk_claimed") is False
        and dual_interpretation.get("cartesian_product_joint_coverage_guarantee_established")
        is False
        and dual_interpretation.get("probabilistic_robustness_claimed") is False
        and dual_interpretation.get("conformal_validity_repair_claimed") is False
        and dual_interpretation.get("optimizer_uniqueness_claimed") is False
        and dual_interpretation.get("selected_result_or_policy") is False
        and dual_interpretation.get("outcome_causal_or_prospective_claimed") is False
    )

    artifacts = evidence.get("paper_artifacts", {})
    artifact_binding = isinstance(artifacts, Mapping) and all(
        isinstance(artifacts.get(name), Mapping) and artifacts[name].get("path") == path
        for name, path in {
            "table/binary_phase_census": (
                "reports/crpto/tables/crpto_ijds_v4_tableS6I_binary_phase_census.csv"
            ),
            "table/dual_coefficient_binary_set_native": (
                "reports/crpto/tables/crpto_ijds_v4_tableS9O_dual_coefficient_binary_set_native.csv"
            ),
        }.items()
    )
    checks = (
        (not phase_registry_identity, "binary-phase identity differs from the registry"),
        (not phase_census, "binary-phase 200-cell census or exact checks changed"),
        (not phase_boundary, "binary-phase interpretation boundary changed"),
        (not dual_registry_identity, "dual-coefficient identity differs from the registry"),
        (not dual_census, "dual-coefficient 208/88/120/0 certificate census changed"),
        (not dual_boundary, "dual-coefficient interpretation boundary changed"),
        (not artifact_binding, "sealed-extension publication tables are misbound"),
    )
    return [message for failed, message in checks if failed]


def _check_evidence_decision() -> list[str]:
    evidence = _evidence()
    boundary = evidence["claim_boundary"]
    lag = evidence["binary_phase_transition"]["label_lag_sensitivity"]
    support = evidence["portfolio"]["policy_support_rhs_semantics"]
    challenger = evidence["decision_challenger"]
    interpretation = challenger["interpretation"]
    endpoint = evidence.get("sensitivity", {}).get("evaluation_endpoint_availability", {})
    missingness = evidence.get("sensitivity", {}).get("missingness_encoding", {})
    rolling = evidence.get("sensitivity", {}).get("rolling_origin", {})
    conformal_set = evidence.get("conformal_set_diagnostics", {})
    exact = evidence.get("exchangeability_transport_test", {})
    label_mondrian = evidence.get("sensitivity", {}).get("label_mondrian", {})
    controls = evidence.get("credit_risk_controls", {})
    common_panel = evidence.get("common_panel_threshold_response", {})

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
            controls.get("all_five_all_eight_upper_below_nominal") is not True,
            "five-model coverage result no longer holds",
        ),
        (
            controls.get("learners_reported")
            != [
                "catboost_platt",
                "numeric_logistic_platt",
                "catboost_monotonic_platt",
                "woe_scorecard_platform_platt",
                "woe_scorecard_borrower_platt",
            ]
            or controls.get("portfolio_learner") != "catboost_platt"
            or controls.get("controls_enter_portfolio_optimization") is not False
            or controls.get("model_or_feature_selected_from_oot") is not False,
            "five coverage-control learners or the CatBoost-only LP role changed",
        ),
        (
            common_panel.get("full_census_and_identities_verified") is not True
            or common_panel.get("stratum_rows") != 175
            or common_panel.get("learner_rows") != 35
            or common_panel.get("stratum_sharp_sign_census")
            != {"negative": 122, "exactly_zero": 5, "positive": 48}
            or common_panel.get("learner_transition_sharp_sign_census")
            != {"negative": 31, "exactly_zero": 0, "positive": 4}
            or common_panel.get("interpretation", {}).get("sharpness_is_cellwise") is not True
            or common_panel.get("interpretation", {}).get(
                "joint_attainability_of_all_cell_endpoints_claimed"
            )
            is not False
            or common_panel.get("interpretation", {}).get(
                "stratum_sign_census_is_substantive_discovery"
            )
            is not False,
            "common-panel threshold response or its cellwise boundary changed",
        ),
        (
            challenger.get("primary_ruler") != "objective_matched"
            or challenger.get("secondary_ruler") != "normalized_score"
            or challenger.get("continuous_frontier_claim") is not False,
            "two-ruler hierarchy or finite-grid boundary changed",
        ),
        (
            evidence["portfolio"]["registered_cap_values_all_envelopes_include_zero"] is not True,
            "broad comparator support no longer crosses zero everywhere",
        ),
        (
            lag["w7_to_w8_threshold_crossing_at_all_admissible_lags"] is not True,
            "phase crossing no longer survives all admissible reporting lags",
        ),
        (
            support["rhs_support_coverage_gate_passed"] is not True
            or support["covered_periods"] != 15
            or support["registered_gap_seed_solves"] != 196
            or support["strictly_interior_gap_seed_solves"] != 196
            or support["status_aware_seed_cap_containment_passes"] != 196
            or support["recomputed_target_gap_coverage_passes"] != 196
            or support["absolute_gap_tolerance"] != 1.0e-10,
            "bounded numerical RHS support coverage no longer holds",
        ),
        (
            support["zero_tolerance_positive_seams"] != 465
            or support["positive_gaps_at_1e_15"] != 0
            or support["maximum_zero_tolerance_seam_width"] > 1.0e-15,
            "machine-precision RHS seam census changed",
        ),
        (
            support["freeze_reconciliation_rows"] != 7_297
            or support["freeze_reconciliation_passes"] != 7_297
            or support["freeze_reconciliation_gate_passed"] is not True
            or support["all_basis_dual_feasibility_contracts_passed"] is not True
            or support["corrected_lateral_gate_passed"] is not True,
            "policy-support bridge, basis, or lateral contract changed",
        ),
        (
            support["strict_numerical_uniqueness_gate_passed"] is not False
            or support["rhs_coverage_recovered_without_uniqueness_promotion"] is not True,
            "RHS coverage is no longer coupled to the blocked uniqueness promotion",
        ),
        (
            any(
                support[field] is not False
                for field in (
                    "exact_symbolic_optimal_face_claim_active",
                    "exact_nonuniqueness_claim_active",
                    "allocation_continuity_claim_active",
                    "continuous_outcome_envelope_claim_active",
                    "epsilon_mobility_is_exact_nonuniqueness_evidence",
                )
            ),
            "policy-support evidence promotes a forbidden exact or continuous inference",
        ),
        (
            support["v2_warning_rows"] != 13
            or support["v3a_gap_seed_warning_rows"] != 1
            or not (0.0 < support["maximum_coordinate_exposure_mobility_dollars"] < 1.0),
            "scale-aware policy-support warning census changed",
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
            or rolling.get("individual_followup_months_after_issue_month_end") != 39
            or rolling.get("exact_calendar_month_age_matched") is not True
            or rolling.get("exact_day_level_age_matched") is not False
            or rolling.get("cutoff_by_issue_period")
            != {
                "2016-04": "2019-07-31",
                "2016-05": "2019-08-31",
                "2016-06": "2019-09-30",
                "2017-04": "2020-07-31",
                "2017-05": "2020-08-31",
                "2017-06": "2020-09-30",
            }
            or rolling.get("primary_2016_census")
            != {"candidate_rows": 74537, "resolved_rows": 73934, "unresolved_rows": 603}
            or rolling.get("rolling_2017_census")
            != {"candidate_rows": 77105, "resolved_rows": 66037, "unresolved_rows": 11068}
            or rolling.get("coarser_equal_quarter_followup_retained_as_provenance")
            != {
                "run_tag": "ijds-rolling-origin-equal-followup-2026-07-21-v1",
                "protocol_tag": "protocol/ijds-rolling-origin-equal-followup-2026-07-21-v1",
                "all_sixteen_upper_below_nominal": True,
                "approximate_followup_months_by_issue_month": {
                    "April": 41,
                    "May": 40,
                    "June": 39,
                },
            }
            or rolling.get("unequal_followup_runs_retained_as_provenance")
            != {
                "rolling_2017_run_tag": "ijds-rolling-origin-2017-2026-07-15-v4",
                "primary_2016_recovery_run_tag": (
                    "ijds-rolling-origin-primary-recovery-2026-07-21-v1"
                ),
            }
            or len(rolling.get("monthly_endpoint_census", [])) != 6
            or {
                (row.get("period"), row.get("individual_evaluation_cutoff"))
                for row in rolling.get("monthly_endpoint_census", [])
            }
            != set(rolling.get("cutoff_by_issue_period", {}).items())
            or any(
                sum(
                    int(row.get(field, -1))
                    for field in (
                        "charged_off_by_reconstructed_cutoff",
                        "fully_paid_by_reconstructed_cutoff",
                        "nonterminal_or_unresolved_status",
                        "terminal_after_reconstructed_cutoff",
                        "terminal_availability_date_missing",
                    )
                )
                != row.get("candidate_rows")
                for row in rolling.get("monthly_endpoint_census", [])
            )
            or any(
                row.get("candidate_rows") == 376890
                for row in rolling.get("rows", [])
                if row.get("origin_id") == "primary_2016"
            ),
            "two-origin coverage comparison no longer uses individual-age 39-month follow-up",
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
            or conformal_set.get("interpretation", {}).get("label_mondrian_method") is not False
            or conformal_set.get("interpretation", {}).get("selected_set_guarantee") is not False
            or conformal_set.get("interpretation", {}).get("funded_set_guarantee") is not False
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
            or label_mondrian.get("interpretation", {}).get("retrospective_sensitivity") is not True
            or label_mondrian.get("interpretation", {}).get("learner_or_window_selected")
            is not False
            or label_mondrian.get("interpretation", {}).get("label_conditional_transport_guarantee")
            is not False
            or label_mondrian.get("interpretation", {}).get("selected_set_guarantee") is not False
            or label_mondrian.get("interpretation", {}).get("funded_set_guarantee") is not False
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


def _paper_artifact_failures(
    artifacts: object,
    *,
    repo_root: Path = REPO,
) -> list[str]:
    """Verify every paper-facing descriptor against the bytes on disk."""
    if not isinstance(artifacts, Mapping):
        return ["paper evidence manifest omits its artifact descriptor mapping"]
    failures: list[str] = []
    seen_paths: dict[str, str] = {}
    for name, raw_descriptor in artifacts.items():
        label = f"paper artifact {name}"
        if not isinstance(name, str) or not isinstance(raw_descriptor, Mapping):
            failures.append(f"{label} has an invalid descriptor")
            continue
        descriptor = cast(Mapping[str, Any], raw_descriptor)
        raw_path = descriptor.get("path")
        if isinstance(raw_path, str):
            if previous := seen_paths.get(raw_path):
                failures.append(f"{label} duplicates the path bound by {previous}")
            else:
                seen_paths[raw_path] = name
        try:
            verified_artifact_path(descriptor, repo_root=repo_root, label=label)
        except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
            failures.append(f"{label} failed verification: {error}")
    return failures


def _check_lineage_sync() -> list[str]:
    """Verify identities and DVC pointers against the single source registry."""
    failures: list[str] = []
    try:
        verification = _load_integrity_source_registry()
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        return [f"active source registry failed verification: {error}"]
    registry = verification.registry
    evidence = _evidence()
    targets = yaml.safe_load(PUBLICATION_TARGETS_PATH.read_text(encoding="utf-8"))
    contract = targets.get("active_scientific_contract", {}) if isinstance(targets, dict) else {}
    expected_registry_path = SOURCE_REGISTRY_PATH.relative_to(REPO).as_posix()
    expected_source_registry = {
        "schema_version": str(registry["schema_version"]),
        "status": str(registry["status"]),
        "sources": sorted(registry["sources"]),
    }
    scientific_git_lineages = _scientific_git_lineages(registry)
    checks = (
        (
            str(registry.get("schema_version")) != EXPECTED_REGISTRY_SCHEMA,
            f"active source registry schema is not {EXPECTED_REGISTRY_SCHEMA}",
        ),
        (
            evidence.get("schema_version") != EXPECTED_REGISTRY_SCHEMA,
            f"paper evidence manifest schema is not {EXPECTED_REGISTRY_SCHEMA}",
        ),
        (
            len(registry.get("dvc_pointers", [])) != EXPECTED_DVC_POINTERS,
            f"active source registry does not contain exactly {EXPECTED_DVC_POINTERS} DVC pointers",
        ),
        (
            scientific_git_lineages != EXPECTED_SCIENTIFIC_GIT_LINEAGES,
            "active source registry does not contain exactly the eleven declared "
            "scientific Git-native lineages",
        ),
        (
            len(
                [
                    descriptor
                    for descriptor in evidence.get("paper_artifacts", {}).values()
                    if str(descriptor.get("path", "")).endswith(".csv")
                ]
            )
            != EXPECTED_CSV_TABLES,
            f"paper evidence manifest does not contain exactly {EXPECTED_CSV_TABLES} CSV tables",
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
    calibrator_registry = registry["sensitivities"]["calibrator_family"]
    calibrator_evidence = evidence.get("sensitivity", {}).get("calibrator_family", {})
    failures.extend(
        _identity_mismatches(
            calibrator_evidence,
            calibrator_registry["evaluation"],
            label="calibrator-family evaluation",
        )
    )
    if (
        calibrator_evidence.get("outcome_free_lineage") != calibrator_registry["outcome_free"]
        or calibrator_evidence.get("evaluation_lineage") != calibrator_registry["evaluation"]
    ):
        failures.append(
            "calibrator-family outcome-free or evaluation lineage differs from registry"
        )
    exact_registry = registry["lineages"]["diagnostics"]["exchangeability_transport_test"]
    failures.extend(
        _identity_mismatches(
            evidence.get("exchangeability_transport_test", {}),
            exact_registry,
            label="exact exchangeability diagnostic",
        )
    )
    rolling_registry = registry["sensitivities"]["rolling_origin_individual_age_followup"]
    failures.extend(
        _identity_mismatches(
            evidence.get("sensitivity", {}).get("rolling_origin", {}),
            rolling_registry,
            label="individual-age follow-up sensitivity",
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
    failures.extend(_paper_artifact_failures(evidence.get("paper_artifacts")))
    failures.extend(
        f"active DVC pointer is missing: {pointer}"
        for pointer in registry["dvc_pointers"]
        if not (REPO / pointer).is_file()
    )
    return failures


def _check_inventory_count_sync() -> list[str]:
    """Keep manually written capsule counts tied to the machine registries."""
    registry = _load_integrity_source_registry().registry
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    dvc_count = len(registry["dvc_pointers"])
    csv_count = sum(
        str(descriptor.get("path", "")).endswith(".csv")
        for descriptor in evidence["paper_artifacts"].values()
    )
    dvc_surfaces = (
        REPO / ".codex/skills/crpto/SKILL.md",
        REPO / "CLAUDE.md",
        REPO / "README.md",
        REPO / "docs/security/SECRETS_AND_REMOTES.md",
        REPO / "paper/CRPTO_ijds.qmd",
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        REPO / "paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md",
        REPO / "paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md",
        REPO / "paper/submission/README.md",
        REPO / "paper/submission/REPRODUCIBILITY_PACKAGE.md",
        REPO / "paper/submission/SCHOLARONE_FINAL_CHECKLIST.md",
    )
    # The manuscript surfaces state the same count as "tables" rather than "CSV",
    # so they are scanned with the widened pattern below. Omitting them let a
    # stale table count reach the generated TeX.
    csv_surfaces = (
        REPO / ".codex/skills/crpto/SKILL.md",
        REPO / "paper/CRPTO_ijds.qmd",
        REPO / "paper/supplement_ijds.qmd",
        REPO / "paper/submission/CRPTO_ijds_submission.tex",
        REPO / "paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md",
        REPO / "paper/submission/EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md",
        REPO / "paper/submission/README.md",
        REPO / "paper/submission/REPRODUCIBILITY_PACKAGE.md",
        REPO / "paper/submission/SCHOLARONE_FINAL_CHECKLIST.md",
    )
    failures: list[str] = []
    dvc_pattern = re.compile(rf"\b{dvc_count}\s+(?:registered\s+)?dvc\s+pointers?\b", re.IGNORECASE)
    for path in dvc_surfaces:
        normalized = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        if dvc_pattern.search(normalized) is None:
            failures.append(
                f"manual DVC inventory count is stale in {path.relative_to(REPO).as_posix()}"
            )
    csv_pattern = re.compile(
        rf"\b{csv_count}\s+(?:(?:paper-facing|aggregate|publication)\s+)*(?:csv\b|tables\b)",
        re.IGNORECASE,
    )
    for path in csv_surfaces:
        normalized = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        if csv_pattern.search(normalized) is None:
            failures.append(
                f"manual CSV inventory count is stale in {path.relative_to(REPO).as_posix()}"
            )
    return failures


def _guarded_check(label: str, check: Callable[[], list[str]]) -> list[str]:
    """Fail closed with an actionable message instead of aborting the full audit."""
    try:
        return check()
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        return [f"{label} failed closed: {error}"]


def check_publication_integrity() -> list[str]:
    checks = (
        ("surface contracts", _check_surface_contracts),
        ("numeric synchronization", _check_numeric_sync),
        ("endpoint-reason partition", _check_endpoint_reason_partition),
        ("retired-claim scan", _check_retired_claims),
        ("reviewer anonymity", _check_reviewer_anonymity),
        ("evidence decision contract", _check_evidence_decision),
        ("calibrator-family publication contract", _check_calibrator_publication_payload),
        ("decision-representation publication contract", _check_decision_representation_payload),
        ("sealed-extension publication contract", _check_sealed_extension_payload),
        ("claim ledger", _check_claim_ledger),
        ("lineage synchronization", _check_lineage_sync),
        ("inventory-count synchronization", _check_inventory_count_sync),
    )
    return [failure for label, check in checks for failure in _guarded_check(label, check)]


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
