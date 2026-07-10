from __future__ import annotations

from scripts.search.export_pool93_policy_aware_frontier import ROLE_ORDER, build_table


def test_build_table_orders_roles_and_uses_exact_threshold() -> None:
    rows = []
    for index, role in enumerate(reversed(ROLE_ORDER), start=1):
        rows.append(
            {
                "role": role,
                "run_label": "unit",
                "local_candidate_id": index,
                "family": "family",
                "risk_tolerance": 0.17,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.5,
                "uncertainty_aversion": 0.1,
                "return": 180_000.0 + index,
                "return_floor_surplus": 9_000.0,
                "Gamma_CP": 0.2,
                "Gamma_residual": 0.1,
                "V": 0.03,
                "endpoint_budget": 0.24,
                "endpoint_budget_upper": 0.24,
                "Markov_threshold": 0.34,
                "Markov_cap": 0.34,
                "alpha_pass": "8/8",
                "n_funded_mean": 300.0,
            }
        )

    table = build_table({"rows": rows})

    assert len(table) == len(ROLE_ORDER)
    assert table.iloc[0]["role"] == "Minimum Markov-threshold endpoint"
    assert table.iloc[-1]["role"] == "Max-return economic endpoint"
    assert table["Markov_threshold_alpha01"].eq(0.34).all()
    assert "Gamma_residual_alpha01" in table.columns
