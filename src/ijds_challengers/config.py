"""Strict configuration contract for the normalized/objective frontier."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


def _exact_floats(values: Any, expected: list[float], *, label: str) -> None:
    if [float(value) for value in values] != expected:
        raise ValueError(f"The locked {label} changed.")


def _require_true(mapping: Any, names: set[str], *, label: str) -> None:
    if not isinstance(mapping, dict) or any(mapping.get(name) is not True for name in names):
        raise ValueError(f"Every {label} must remain enabled.")


def _validate_frontier(frontier: Any) -> None:
    if not isinstance(frontier, dict):
        raise TypeError("frontier must be a mapping.")
    _exact_floats(frontier["gamma_grid"], [0.0, 0.25, 0.5, 0.75, 1.0], label="gamma path")
    _exact_floats(frontier["coordinate_grid"], [0.25, 0.5, 0.75], label="coordinate grid")
    _exact_floats(frontier["endpoint_contrast"], [1.0, 0.0], label="endpoint contrast")
    if frontier["rulers"] != {
        "primary": "objective_matched",
        "secondary": "normalized_score",
    }:
        raise ValueError("The declared frontier ruler hierarchy changed.")
    if frontier["roles"] != ["policy_development", "primary_oot"]:
        raise ValueError("The outcome-free frontier roles changed.")
    if (int(frontier["expected_development_months"]), int(frontier["expected_primary_months"])) != (
        11,
        15,
    ) or int(frontier["expected_windows"]) != 8:
        raise ValueError("The locked window or month census changed.")


def _validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise TypeError("source_ingest must be a mapping.")
    if source["allowed_raw_columns"] != ["id", "loan_amnt", "int_rate", "purpose"]:
        raise ValueError("The outcome-free raw-column allowlist changed.")
    forbidden = tuple(str(token).casefold() for token in source["forbidden_tokens"])
    if any(
        token in str(column).casefold()
        for column in source["allowed_raw_columns"]
        for token in forbidden
    ):
        raise ValueError("The raw-column allowlist contains an outcome-like name.")


def _validate_solver(solver: Any) -> None:
    if not isinstance(solver, dict):
        raise TypeError("solver must be a mapping.")
    if solver["primary"] != "highspy_exact_budget_simplex" or int(solver["threads"]) != 1:
        raise ValueError("The deterministic primary solver contract changed.")
    validation = solver["independent_validation"]
    if validation["solver"] != "ortools_glop" or validation["periods"] != [
        "2016-04",
        "2016-11",
        "2017-06",
    ]:
        raise ValueError("The independent solver validation contract changed.")
    positive = (
        solver["allocation_tolerance"],
        solver["budget_residual_tolerance_dollars"],
        solver["order_exposure_distance_tolerance"],
        solver["order_objective_tolerance_dollars"],
        solver["endpoint_pair_degeneracy_tolerance"],
        validation["objective_rate_tolerance"],
        validation["weighted_score_tolerance"],
    )
    if any(float(value) <= 0.0 for value in positive):
        raise ValueError("Every numerical solver tolerance must be positive.")


def load_frontier_config(path: Path) -> dict[str, Any]:
    """Load and validate the locked outcome-free V1 challenger config."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Frontier config must be a YAML mapping.")
    required = {
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "parent",
        "source_ingest",
        "frontier",
        "solver",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Frontier config is missing sections: {missing}.")
    if payload["protocol_status"] != "locked_outcome_free_frontier_before_execution":
        raise ValueError("Frontier protocol is not locked for outcome-free execution.")
    _validate_frontier(payload["frontier"])
    _validate_source(payload["source_ingest"])
    _validate_solver(payload["solver"])
    boundary = payload["claim_boundary"]
    if boundary.get("outcome_columns_passed") != []:
        raise ValueError("The V1 frontier cannot accept outcome columns.")
    required_true = {
        "no_policy_selection",
        "no_policy_winner",
        "no_conformal_guarantee_repair",
        "no_equal_true_risk_claim",
        "no_equal_shadow_price_claim",
        "no_causal_claim",
        "no_submission_freeze",
    }
    _require_true(boundary, required_true, label="V1 frontier claim boundary")
    _require_true(
        payload["stop_rules"],
        {
            "stop_on_incomplete_cell",
            "stop_on_score_range_failure",
            "stop_on_objective_range_failure",
            "stop_on_objective_optimum_tie",
            "stop_on_order_sensitivity",
            "stop_on_independent_solver_mismatch",
            "stop_before_outcomes_if_endpoint_allocations_all_identical",
        },
        label="V1 frontier stop rule",
    )
    if payload["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Frontier outputs must remain immutable.")
    return cast(dict[str, Any], payload)
