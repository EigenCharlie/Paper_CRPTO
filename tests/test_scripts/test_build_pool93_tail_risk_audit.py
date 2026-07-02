from __future__ import annotations

import pytest

from scripts.search.build_pool93_tail_risk_audit import (
    DEFAULT_ALLOCATION_PATH,
    DEFAULT_BODY_AUDIT_PATH,
    _load_allocation,
    _read_json,
    build_bootstrap_table,
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


def test_pool93_bootstrap_table_is_fixed_allocation_diagnostic() -> None:
    funded, body_audit = _pool93_inputs()
    table = build_bootstrap_table(
        funded,
        body_audit=body_audit,
        n_draws=5000,
        seed=20260702,
        lgd=0.45,
    )
    metrics = {row["metric"]: row for row in table.to_dict(orient="records")}
    return_row = metrics["funded_set_repriced_return_lgd45"]
    v_row = metrics["weighted_miscoverage_V"]
    gamma_row = metrics["alpha01_gamma_cp"]

    assert return_row["observed"] == pytest.approx(184_832.475845, rel=1e-9)
    assert return_row["boot_p025"] == pytest.approx(167_963.197413, rel=1e-9)
    assert return_row["boot_p975"] == pytest.approx(198_650.467343, rel=1e-9)
    assert v_row["observed"] == pytest.approx(0.03535, abs=1e-12)
    assert v_row["boot_p975"] < 0.1
    assert gamma_row["boot_p975"] < 0.2
    assert table["note"].nunique() == 1
    assert "solver input uncertainty is not resampled" in str(table["note"].iloc[0])
