from __future__ import annotations

import pandas as pd
import pytest

from scripts.search.build_pool93_point_baseline_audit import (
    _comparison_table,
    _format_comparison_tex,
)


def test_comparison_table_reports_return_cost_and_certificate_metrics() -> None:
    point = {
        "realized_return": 200.0,
        "expected_return_net_point": 210.0,
        "certificate": {
            "n_funded": 10,
            "weighted_outcome": 0.12,
            "weighted_miscoverage": 0.11,
            "gamma_cp": 0.50,
            "endpoint_budget": 0.60,
            "markov_loss_threshold": 0.70,
        },
    }
    selected = {
        "realized_return": 180.0,
        "expected_return_net_point": 170.0,
        "certificate": {
            "n_funded": 14,
            "weighted_outcome": 0.04,
            "weighted_miscoverage": 0.03,
            "gamma_cp": 0.16,
            "endpoint_budget": 0.25,
            "markov_loss_threshold": 0.35,
        },
    }

    table = _comparison_table(point, selected).set_index("policy")

    assert isinstance(table, pd.DataFrame)
    assert table.loc["Point-PD two-stage LP", "return_cost_vs_point_pct"] == pytest.approx(0.0)
    assert table.loc["Selected CRPTO", "return_cost_vs_point_pct"] == pytest.approx(10.0)
    assert table.loc["Selected CRPTO", "Markov_threshold_alpha01"] == pytest.approx(0.35)
    assert table.loc["Selected CRPTO", "weighted_default_rate"] == pytest.approx(0.04)

    tex = _format_comparison_tex(table.reset_index())
    assert "Policy & Realized return & Weighted default" in tex
    assert "Selected CRPTO & \\$180.00 & 0.040000 & 0.160000 & 0.250000 & 0.350000" in tex
    assert "expected\\_return\\_net\\_point" not in tex
