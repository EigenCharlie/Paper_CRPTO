from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.experiments import run_ijds_fixed_taxonomy_c2 as protocol
from src.optimization.policy_selection import LinearPolicyCandidate


def test_protocol_removes_champion_selection_and_locks_closed_sensitivities() -> None:
    config = protocol.load_config(protocol.DEFAULT_CONFIG_PATH)

    assert config["policy"]["outcome_based_selection"] is False
    assert config["analysis"]["all_nine_policies_primary"] is True
    assert config["model"]["sensitivity_seeds"] == [40, 41, 42, 43, 44]
    assert config["policy"]["purpose_cap_sensitivity"] == [0.2, 0.25, 0.3, 1.0]
    assert config["conformal"]["taxonomy_source"].startswith("2011_")
    assert config["comparators"]["primary"].startswith("contemporaneous_outcome_free")
    assert config["simulation"]["enabled"] is True
    assert len(protocol._policy_candidates(config)) == 9


def test_terminal_resolution_keeps_nonterminal_rows_right_censored() -> None:
    outcome = pd.Series([0, 1, pd.NA], dtype="Int8")

    assert protocol._terminal_resolution(outcome).tolist() == [
        "fully_paid",
        "charged_off",
        "right_censored",
    ]


def test_c2_family_derives_exact_outcome_free_point_moment(
    monkeypatch,
) -> None:
    config = protocol.load_config(protocol.DEFAULT_CONFIG_PATH)
    candidate = LinearPolicyCandidate("linear-001", 0.17, 0.25, 0.0)
    monkeypatch.setattr(protocol, "_policy_candidates", lambda _config: [candidate])
    panel = pd.DataFrame(
        {
            "id": ["a", "b"],
            "issue_d": pd.to_datetime(["2016-04-01", "2016-04-01"]),
            "design_split": ["primary_oot", "primary_oot"],
            "pd_point": [0.1, 0.2],
        }
    )

    def fake_solve(
        month: pd.DataFrame,
        policy: LinearPolicyCandidate,
        *,
        robust: bool,
        role: str,
        period: str,
        policy_label: str,
        config,
    ) -> tuple[dict[str, object], pd.DataFrame]:
        del month, config
        allocation = pd.DataFrame(
            {
                "id": ["a", "b"],
                "exposure": [50.0, 50.0],
                "pd_point": [0.1, 0.2],
                "role": [role, role],
                "period": [period, period],
                "policy_label": [policy_label, policy_label],
                "candidate_id": [policy.candidate_id, policy.candidate_id],
            }
        )
        return (
            {
                "role": role,
                "period": period,
                "policy_label": policy_label,
                "robust_guardrail": robust,
            },
            allocation,
        )

    monkeypatch.setattr(protocol, "solve_outcome_free_allocation", fake_solve)

    bundle = protocol._solve_guardrail_family(
        panel,
        config=config,
        role="primary_oot",
        seed=42,
        purpose_cap=0.25,
        lgd=0.45,
        include_multiverse=False,
    )

    assert bundle.records["comparator_rule"].tolist() == [
        "guardrail",
        "c2_contemporaneous",
    ]
    assert bundle.records["c2_target_point_risk"].tolist() == [0.15, 0.15]
    assert bundle.records["c2_match_residual"].abs().max() < 1e-12
    assert "snapshot_default" not in bundle.allocations.columns
    assert "loan_status" not in bundle.allocations.columns


def test_default_config_path_is_repository_relative() -> None:
    assert (
        Path(protocol.ROOT) / ("configs/experiments/ijds_fixed_taxonomy_c2_2026-07-11.yaml")
        == protocol.DEFAULT_CONFIG_PATH
    )
