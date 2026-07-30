from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from src.ijds_audit.funded_selection_estimand import (
    _coalesced_union,
    build_funded_selection_estimand_audit,
)

PERIODS = ("2016-04", "2016-05")


def _set_bounds(kind: str) -> tuple[float, float]:
    return {
        "empty": (0.4, 0.6),
        "full": (0.0, 1.0),
        "zero": (0.0, 0.4),
        "one": (0.6, 1.0),
    }[kind]


def _miss_bounds(outcome: float, lower: float, upper: float) -> tuple[float, float]:
    misses = [float(not (lower <= label <= upper)) for label in (0.0, 1.0)]
    if np.isfinite(outcome):
        miss = misses[int(outcome)]
        return miss, miss
    return min(misses), max(misses)


def _synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specifications = [
        # period, gamma, candidate, id, continuous, rounded, set, outcome
        ("2016-04", 0.0, "g0", "A", 30.0, 25.0, "zero", np.nan),
        ("2016-04", 0.0, "g0", "B", 65.0, 50.0, "zero", 1.0),
        ("2016-04", 0.0, "g0", "G", 5.0, None, "empty", 0.0),
        ("2016-05", 0.0, "g0", "D", 30.0, 25.0, "full", np.nan),
        ("2016-05", 0.0, "g0", "E", 70.0, 50.0, "empty", 0.0),
        ("2016-04", 1.0, "g1", "A", 50.0, 50.0, "zero", np.nan),
        ("2016-04", 1.0, "g1", "C", 50.0, 50.0, "one", 0.0),
        ("2016-05", 1.0, "g1", "D", 50.0, 50.0, "full", np.nan),
        ("2016-05", 1.0, "g1", "F", 50.0, 50.0, "empty", np.nan),
    ]
    rounded_rows = []
    parent_rows = []
    joined_rows = []
    for period, gamma, candidate, loan_id, continuous, rounded, kind, outcome in specifications:
        lower, upper = _set_bounds(kind)
        miss_lower, miss_upper = _miss_bounds(outcome, lower, upper)
        base = {
            "id": loan_id,
            "issue_d": pd.Timestamp(f"{period}-01"),
            "design_split": "primary_oot",
            "pd_point": 0.20,
            "loan_amnt": 100.0,
            "purpose": "debt_consolidation",
            "contractual_rate": 0.12,
            "window_id": "w1",
            "role": "primary_oot",
            "period": period,
            "candidate_id": candidate,
            "policy_label": candidate,
            "comparator_rule": "objective_matched",
            "paired_policy_id": candidate,
            "frontier_ruler": "objective_matched",
            "frontier_coordinate": 0.25,
            "frontier_cap": 0.30,
            "objective_target": np.nan,
            "gamma": gamma,
            "pd_effective": 0.20,
            "expected_payoff_rate": 0.10,
            "conformal_lower": lower,
            "conformal_upper": upper,
        }
        parent_rows.append(
            {
                **base,
                "allocation_fraction": continuous / 100.0,
                "exposure": continuous,
                "weight": continuous / 100.0,
                "expected_payoff_contribution": continuous * 0.10,
            }
        )
        if rounded is not None:
            rounded_rows.append(
                {
                    **base,
                    "exposure": rounded,
                    "source_exposure": continuous,
                }
            )
        joined_rows.append(
            {
                **base,
                "allocation_fraction": continuous / 100.0,
                "exposure": continuous,
                "weight": continuous / 100.0,
                "expected_payoff_contribution": continuous * 0.10,
                "snapshot_default": outcome,
                "snapshot_resolution": (
                    "fully_paid_by_reconstructed_cutoff"
                    if outcome == 0.0
                    else (
                        "charged_off_by_reconstructed_cutoff"
                        if outcome == 1.0
                        else "nonterminal_or_unresolved_status"
                    )
                ),
                "miscoverage_lower": miss_lower,
                "miscoverage_upper": miss_upper,
            }
        )
    registered = pd.DataFrame(
        [
            {
                "window_id": "w1",
                "candidate_id": "g0",
                "frontier_ruler": "objective_matched",
                "frontier_coordinate": 0.25,
                "gamma": 0.0,
                "periods": 2,
                "role": "primary_oot",
                "contrast": "rounded_lot_minus_continuous",
                "policy_a": "rounded_lot",
                "policy_b": "continuous",
                "policy_a_normalization_capital": 200.0,
                "policy_b_normalization_capital": 200.0,
                "weighted_miscoverage_difference_lower": -0.225,
                "weighted_miscoverage_difference_upper": -0.2,
            },
            {
                "window_id": "w1",
                "candidate_id": "g1",
                "frontier_ruler": "objective_matched",
                "frontier_coordinate": 0.25,
                "gamma": 1.0,
                "periods": 2,
                "role": "primary_oot",
                "contrast": "rounded_lot_minus_continuous",
                "policy_a": "rounded_lot",
                "policy_b": "continuous",
                "policy_a_normalization_capital": 200.0,
                "policy_b_normalization_capital": 200.0,
                "weighted_miscoverage_difference_lower": 0.0,
                "weighted_miscoverage_difference_upper": 0.0,
            },
        ]
    )
    return (
        pd.DataFrame(rounded_rows),
        pd.DataFrame(parent_rows),
        pd.DataFrame(joined_rows),
        registered,
    )


def _build():
    rounded, parent, joined, registered = _synthetic_inputs()
    return build_funded_selection_estimand_audit(
        rounded,
        parent,
        joined,
        registered,
        periods=PERIODS,
        lot_size_usd=25.0,
        committed_budget_usd=100.0,
    )


def test_three_estimands_are_explicit_and_pooled_before_division() -> None:
    tables = _build()
    assert len(tables.monthly_bounds) == 4
    assert len(tables.track_bounds) == 2
    assert len(tables.monthly_gamma_contrasts) == 2
    assert len(tables.track_gamma_contrasts) == 1
    assert len(tables.support_and_fixed_capital_reconciliation) == 2

    gamma_zero = tables.track_bounds.loc[tables.track_bounds["gamma"].eq(0.0)].iloc[0]
    assert gamma_zero["selected_positions"] == 4
    assert gamma_zero["periods"] == 2
    assert gamma_zero["funded_dollars"] == pytest.approx(150.0)
    assert gamma_zero["committed_capital_usd"] == pytest.approx(200.0)
    assert gamma_zero["count_selected_fcp_lower"] == pytest.approx(0.5)
    assert gamma_zero["count_selected_fcp_upper"] == pytest.approx(0.75)
    assert gamma_zero["invested_dollar_selected_fcp_lower"] == pytest.approx(2.0 / 3.0)
    assert gamma_zero["invested_dollar_selected_fcp_upper"] == pytest.approx(5.0 / 6.0)
    assert gamma_zero["fixed_capital_decision_fcp_lower"] == pytest.approx(0.5)
    assert gamma_zero["fixed_capital_decision_fcp_upper"] == pytest.approx(0.625)
    assert "dollar_fcp_lower" not in tables.track_bounds


def test_count_vs_dollar_differences_use_one_shared_completion() -> None:
    gamma_zero = _build().track_bounds.query("gamma == 0.0").iloc[0]
    assert gamma_zero["count_selected_minus_invested_dollar_selected_fcp_lower"] == pytest.approx(
        -1.0 / 6.0
    )
    assert gamma_zero["count_selected_minus_invested_dollar_selected_fcp_upper"] == pytest.approx(
        -1.0 / 12.0
    )
    assert gamma_zero["count_selected_minus_fixed_capital_decision_fcp_lower"] == pytest.approx(0.0)
    assert gamma_zero["count_selected_minus_fixed_capital_decision_fcp_upper"] == pytest.approx(
        0.125
    )


def test_gamma_contrasts_are_sharp_under_shared_loan_labels() -> None:
    contrast = _build().track_gamma_contrasts.iloc[0]
    assert contrast["gamma1_minus_gamma0_count_selected_fcp_lower"] == pytest.approx(0.0)
    assert contrast["gamma1_minus_gamma0_count_selected_fcp_upper"] == pytest.approx(0.0)
    assert contrast["gamma1_minus_gamma0_invested_dollar_selected_fcp_lower"] == pytest.approx(
        -1.0 / 6.0
    )
    assert contrast["gamma1_minus_gamma0_invested_dollar_selected_fcp_upper"] == pytest.approx(
        -1.0 / 12.0
    )
    assert contrast["gamma1_minus_gamma0_fixed_capital_decision_fcp_lower"] == pytest.approx(0.0)
    assert contrast["gamma1_minus_gamma0_fixed_capital_decision_fcp_upper"] == pytest.approx(0.125)

    # Exhaustively verify the three unresolved loans; this is independent of
    # separately extremizing policy-level intervals.
    observed = []
    for label_a, _label_d, _label_f in itertools.product((0, 1), repeat=3):
        count_g0 = (label_a + 1 + 0 + 1) / 4
        count_g1 = (label_a + 1 + 0 + 1) / 4
        observed.append(count_g1 - count_g0)
    assert min(observed) == pytest.approx(contrast["gamma1_minus_gamma0_count_selected_fcp_lower"])
    assert max(observed) == pytest.approx(contrast["gamma1_minus_gamma0_count_selected_fcp_upper"])


def test_fixed_capital_recomputation_reconciles_to_registered_v3() -> None:
    reconciliation = _build().support_and_fixed_capital_reconciliation
    assert reconciliation["exact_within_locked_tolerance"].all()
    assert reconciliation["lower_absolute_difference"].max() <= 1.0e-12
    assert reconciliation["upper_absolute_difference"].max() <= 1.0e-12


def test_fixed_capital_v3_mismatch_fails_closed() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    registered.loc[0, "weighted_miscoverage_difference_lower"] += 1.0e-5
    with pytest.raises(RuntimeError, match="does not reconcile to V3"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_non_lot_exposure_fails_closed() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    rounded.loc[0, "exposure"] = 26.0
    with pytest.raises(RuntimeError, match="lot multiples"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_subtolerance_non_lot_exposure_fails_closed() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    rounded.loc[0, "exposure"] += 5.0e-11
    with pytest.raises(RuntimeError, match="exact lot multiples"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_even_tiny_endpoint_reversal_fails_closed() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    replacement = rounded.loc[0, "conformal_upper"] + 1.0e-15
    key = rounded.loc[0, ["id", "window_id", "role", "period", "candidate_id"]]
    rounded.loc[0, "conformal_lower"] = replacement
    for frame in (parent, joined):
        mask = np.ones(len(frame), dtype=bool)
        for column, value in key.items():
            mask &= frame[column].eq(value).to_numpy(dtype=bool)
        frame.loc[mask, "conformal_lower"] = replacement
    with pytest.raises(RuntimeError, match="reversed endpoints"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_rowwise_miscoverage_must_reconcile() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    joined.loc[0, "miscoverage_upper"] = 0.0
    with pytest.raises(RuntimeError, match="does not reconcile"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_subtolerance_rowwise_miscoverage_drift_fails_closed() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    joined.loc[0, "miscoverage_lower"] += 5.0e-13
    with pytest.raises(RuntimeError, match="does not reconcile"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


@pytest.mark.parametrize("invalid", ["not-a-label", np.inf, -np.inf, 0.5])
def test_nonmissing_outcomes_must_be_finite_binary(invalid: object) -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    joined["snapshot_default"] = joined["snapshot_default"].astype(object)
    joined.loc[0, "snapshot_default"] = invalid
    joined.loc[0, "snapshot_resolution"] = "nonterminal_or_unresolved_status"
    with pytest.raises(ValueError, match="finite and binary"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_endpoint_reason_must_match_binary_outcome() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    resolved_index = joined["snapshot_default"].eq(0.0).idxmax()
    joined.loc[resolved_index, "snapshot_resolution"] = "charged_off_by_reconstructed_cutoff"
    with pytest.raises(RuntimeError, match="disagrees with its outcome"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_parent_and_outcome_join_support_must_match_exactly() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    joined.loc[0, "exposure"] += 1.0
    with pytest.raises(RuntimeError, match="disagree on 'exposure'"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


@pytest.mark.parametrize(
    ("column", "replacement"), [("policy_label", "changed"), ("frontier_cap", 0.31)]
)
def test_parent_and_outcome_join_policy_metadata_must_match_exactly(
    column: str, replacement: object
) -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    joined.loc[0, column] = replacement
    with pytest.raises(RuntimeError, match=f"disagree on '{column}'"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_rounded_support_binary_endpoint_drift_fails_exactly() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    zero_endpoint = rounded["conformal_lower"].eq(0.0).idxmax()
    rounded.loc[zero_endpoint, "conformal_lower"] = 5.0e-13
    with pytest.raises(RuntimeError, match="V3 parent and rounded support disagree"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_removed_parent_position_must_floor_to_zero() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    removed = parent["id"].eq("G")
    parent.loc[removed, "exposure"] = 30.0
    joined.loc[joined["id"].eq("G"), "exposure"] = 30.0
    with pytest.raises(RuntimeError, match="does not floor to zero"):
        build_funded_selection_estimand_audit(
            rounded,
            parent,
            joined,
            registered,
            periods=PERIODS,
            committed_budget_usd=100.0,
        )


def test_v3_rounding_tolerance_preserves_near_lot_boundary() -> None:
    rounded, parent, joined, registered = _synthetic_inputs()
    target = rounded["id"].eq("A") & rounded["candidate_id"].eq("g1")
    rounded.loc[target, "source_exposure"] = 49.99999999999999
    parent_target = parent["id"].eq("A") & parent["candidate_id"].eq("g1")
    joined_target = joined["id"].eq("A") & joined["candidate_id"].eq("g1")
    parent.loc[parent_target, "exposure"] = 49.99999999999999
    joined.loc[joined_target, "exposure"] = 49.99999999999999
    tables = build_funded_selection_estimand_audit(
        rounded,
        parent,
        joined,
        registered,
        periods=PERIODS,
        committed_budget_usd=100.0,
    )
    assert len(tables.support_and_fixed_capital_reconciliation) == 2


def test_shared_loan_endpoint_drift_is_rejected_without_tolerance() -> None:
    base = {
        "id": "A",
        "period": "2016-04",
        "funded_exposure": 25.0,
        "snapshot_default": np.nan,
        "outcome_resolved": False,
        "miss_zero": 0.0,
        "miss_one": 1.0,
        "conformal_lower": 0.0,
        "conformal_upper": 0.5,
    }
    left = pd.DataFrame([base])
    right = pd.DataFrame([{**base, "conformal_lower": 5.0e-13}])
    with pytest.raises(RuntimeError, match="shared-loan conformal endpoints"):
        _coalesced_union(left, right)
