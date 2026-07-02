from __future__ import annotations

import pytest

from scripts.search.build_pool93_tail_risk_audit import (
    DEFAULT_ALLOCATION_PATH,
    DEFAULT_BODY_AUDIT_PATH,
    _load_allocation,
    _read_json,
    build_cluster_bound_table,
    build_tail_risk_table,
)


def _pool93_inputs():
    if not DEFAULT_ALLOCATION_PATH.is_file():
        pytest.skip("pool93 body allocation artifact is not present locally")
    return _load_allocation(DEFAULT_ALLOCATION_PATH), _read_json(DEFAULT_BODY_AUDIT_PATH)


def test_pool93_tail_repricing_matches_promoted_body_return() -> None:
    funded, body_audit = _pool93_inputs()
    table = build_tail_risk_table(funded, body_audit=body_audit, lgds=(0.35, 0.45, 0.60))
    baseline = table.loc[table["lgd"].eq(0.45)].iloc[0]

    assert baseline["funded_rows"] == 314
    assert baseline["total_allocated"] == pytest.approx(1_000_000.0)
    assert baseline["funded_set_repriced_return"] == pytest.approx(184_832.475845, rel=1e-9)
    assert baseline["weighted_default_rate"] == pytest.approx(0.03535, abs=1e-12)
    assert baseline["realized_cvar95_loss_rate"] > baseline["decision_time_cvar95_loss_rate"]
    assert baseline["alpha01_weighted_miscoverage_V"] == pytest.approx(0.03535, abs=1e-12)


def test_pool93_cluster_bounds_remain_looser_than_markov() -> None:
    funded, body_audit = _pool93_inputs()
    table = build_cluster_bound_table(funded, body_audit=body_audit, alpha=0.01, delta=0.10)

    assert set(table["cluster_type"]) == {"period", "grade_bucket", "period_grade", "score_vintage"}
    assert not bool(table["cluster_bound_tighter_than_markov"].any())
    assert table["markov_threshold"].nunique() == 1
    assert float(table["markov_threshold"].iloc[0]) == pytest.approx(0.1)
    period_grade = table.loc[table["cluster_type"].eq("period_grade")].iloc[0]
    assert period_grade["cluster_hoeffding_threshold"] == pytest.approx(0.281247, rel=1e-6)
    assert period_grade["sum_cluster_exposure_sq"] > period_grade["sum_w2_tightening_threshold"]
