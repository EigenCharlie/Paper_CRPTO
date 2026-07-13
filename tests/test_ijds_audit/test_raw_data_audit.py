"""Tests for the full-archive IJDS data-contract audit."""

from __future__ import annotations

from src.ijds_audit.raw_data_audit import classify_raw_column


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
