"""Strict configuration contract for the post-freeze frontier evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

EXPECTED_FREEZE_SHA256 = "7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185"


def load_v2_config(path: Path) -> dict[str, Any]:
    """Load and validate the locked V2 outcome-evaluation config."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V2 config must be a YAML mapping.")
    required = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "source_frontier",
        "parent",
        "evaluation",
        "metrics",
        "outcomes",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"V2 config is missing sections: {missing}.")
    if payload["protocol_status"] != "locked_post_freeze_outcome_evaluation":
        raise ValueError("V2 protocol is not locked for post-freeze evaluation.")
    _validate_source_frontier(payload["source_frontier"])
    _validate_evaluation(payload["evaluation"])
    _validate_metrics(payload["metrics"])
    _require_true(
        payload["outcomes"],
        {"no_outcome_refit", "no_outcome_resolve", "no_outcome_selection"},
        label="outcome boundary",
    )
    _require_true(
        payload["claim_boundary"],
        {
            "no_policy_selection",
            "no_window_selection",
            "no_ruler_selection",
            "no_coordinate_selection",
            "no_gamma_selection",
            "no_policy_winner",
            "no_causal_claim",
            "no_conformal_guarantee_repair",
            "no_selected_set_validity",
            "no_submission_freeze",
        },
        label="V2 claim boundary",
    )
    _require_true(
        payload["stop_rules"],
        {
            "stop_on_v1c_freeze_mismatch",
            "stop_on_artifact_descriptor_mismatch",
            "stop_on_outcome_alignment_failure",
            "stop_on_incomplete_portfolio_evaluation",
            "stop_on_incomplete_contrast_census",
            "stop_on_nonbinary_observed_outcome",
            "retain_all_predeclared_results",
        },
        label="V2 stop rule",
    )
    if payload["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("V2 outputs must remain immutable.")
    return cast(dict[str, Any], payload)


def _validate_source_frontier(source: Any) -> None:
    if not isinstance(source, dict):
        raise TypeError("source_frontier must be a mapping.")
    expected = {
        "run_tag": "ijds-normalized-objective-frontier-2026-07-13-v1c",
        "protocol_tag": "protocol/ijds-normalized-objective-frontier-2026-07-13-v1c",
        "protocol_commit": "46f4df915d38eb5a6cc144484c6e6fe56d8ed397",
        "status": "outcome_free_frontiers_frozen_before_archive_outcome_join",
    }
    if any(source.get(field) != value for field, value in expected.items()):
        raise ValueError("The locked V1c source identity changed.")
    descriptor = source.get("freeze")
    if not isinstance(descriptor, dict) or descriptor != {
        "path": (
            "models/experiments/ijds_audit/"
            "ijds-normalized-objective-frontier-2026-07-13-v1c/protocol_freeze.json"
        ),
        "bytes": 15192,
        "sha256": EXPECTED_FREEZE_SHA256,
    }:
        raise ValueError("The locked V1c freeze descriptor changed.")


def _validate_evaluation(evaluation: Any) -> None:
    if not isinstance(evaluation, dict):
        raise TypeError("evaluation must be a mapping.")
    exact = {
        "evaluated_roles": ["policy_development", "primary_oot"],
        "primary_contrast_role": "primary_oot",
        "endpoint_contrast": [1.0, 0.0],
        "rulers": ["objective_matched", "normalized_score"],
        "coordinates": [0.25, 0.5, 0.75],
        "expected_solve_records": 6240,
        "expected_funded_rows": 622455,
        "expected_window_contrasts": 48,
        "expected_monthly_contrasts": 720,
        "expected_metric_directions": 144,
        "expected_windows": 8,
        "expected_primary_months": 15,
        "expected_candidate_counts": {
            "policy_development": 94885,
            "primary_oot": 376890,
        },
        "outcome_join": "single_validated_join_after_hash_verified_v1c_freeze",
        "unresolved_outcomes": "sharp_common_loanwise_assignment_on_funded_union",
    }
    if evaluation != exact:
        raise ValueError("The complete V2 evaluation census changed.")


def _validate_metrics(metrics: Any) -> None:
    expected_columns = {
        "standardized_payoff": (
            "realized_payoff_difference_lower",
            "realized_payoff_difference_upper",
            1.0e-4,
        ),
        "funded_default": (
            "weighted_default_difference_lower",
            "weighted_default_difference_upper",
            1.0e-10,
        ),
        "funded_binary_miscoverage": (
            "weighted_miscoverage_difference_lower",
            "weighted_miscoverage_difference_upper",
            1.0e-10,
        ),
    }
    if not isinstance(metrics, dict) or set(metrics) != set(expected_columns):
        raise ValueError("The V2 metric family changed.")
    for metric, (lower, upper, tolerance) in expected_columns.items():
        spec = metrics[metric]
        if spec.get("lower") != lower or spec.get("upper") != upper:
            raise ValueError(f"The {metric} bound columns changed.")
        if float(spec.get("direction_tolerance")) != tolerance:
            raise ValueError(f"The {metric} direction tolerance changed.")


def _require_true(mapping: Any, names: set[str], *, label: str) -> None:
    if not isinstance(mapping, dict) or any(mapping.get(name) is not True for name in names):
        raise ValueError(f"Every {label} must remain enabled.")
