"""Tests for the full-archive IJDS data-contract audit."""

from __future__ import annotations

import pandas as pd

from src.ijds_audit.raw_data_audit import _feature_contract, classify_raw_column


def test_post_outcome_columns_are_never_model_eligible() -> None:
    role, reason = classify_raw_column("total_pymnt", active_required=["total_pymnt"])
    assert role == "post_outcome_or_servicing"
    assert "never eligible" in reason


def test_late_joint_application_fields_have_explicit_role() -> None:
    role, reason = classify_raw_column("sec_app_fico_range_low", active_required=[])
    assert role == "joint_application_origination"
    assert "introduced late" in reason


def test_active_origination_field_is_distinct_from_metadata() -> None:
    role, _ = classify_raw_column("fico_range_low", active_required=["fico_range_low"])
    assert role == "active_protocol_input"


def test_feature_contract_applies_threshold_and_declared_exceptions() -> None:
    coverage = pd.DataFrame(
        {
            "feature": ["ordinary", "nullable"] * 4,
            "cohort": [
                "pd_development",
                "pd_development",
                "probability_calibration",
                "probability_calibration",
                "conformal_fit",
                "conformal_fit",
                "primary_oot",
                "primary_oot",
            ],
            "coverage": [0.96, 0.30, 0.97, 0.35, 0.98, 0.40, 0.99, 0.50],
        }
    )
    rules = {
        "minimum_fitting_feature_coverage": 0.95,
        "late_feature_fitting_coverage": 0.50,
        "late_feature_primary_coverage": 0.80,
        "active_feature_coverage_exceptions": {
            "nullable": {
                "type": "structural",
                "missingness_semantics": "explicit sentinel",
                "requires_sensitivity": True,
            }
        },
    }
    contract = _feature_contract(
        coverage,
        columns=["ordinary", "nullable"],
        active_required=["ordinary", "nullable"],
        rules=rules,
    ).set_index("feature")
    assert contract.loc["ordinary", "decision"] == "eligible"
    assert contract.loc["nullable", "decision"] == "eligible_with_declared_coverage_exception"
    assert bool(contract.loc["nullable", "requires_sensitivity"])
