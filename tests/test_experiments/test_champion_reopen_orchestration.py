from __future__ import annotations

from scripts.experiments.run_champion_claim_max_downstream import (
    _is_paper_facing_case,
    _portfolio_command,
    _select_downstream_candidates,
)
from scripts.experiments.run_champion_reopen import _build_commands


def _config() -> dict[str, object]:
    return {
        "run_tag": "unit",
        "seeds": [42, 52],
        "output": {
            "report_dir": "reports/crpto/experiments/champion_reopen",
            "model_dir": "models/experiments/champion_reopen",
        },
        "champion_reopen": {
            "selector_model": "models/experiments/tabprep/selector.cbm",
            "ranking_method": "pvc",
            "shap_rows": 123,
            "smoke_sample_rows": 1000,
            "smoke_cases": ["core42", "pooltop42_tab20"],
            "feature_search_cases": ["pool93_top90"],
            "seed_replay_cases": ["pool93_top90", "pool93_business80"],
        },
        "calibration": {"candidates": ["platt", "temperature"]},
    }


def test_smoke_commands_are_sampled_and_checkpointed() -> None:
    commands = _build_commands(
        config=_config(),
        stage="smoke",
        run_tag="unit-run",
        sample_rows_override=None,
    )

    assert len(commands) == 1
    command = commands[0]
    assert "--sample-rows" in command.command
    assert "1000" in command.command
    assert command.expected_output.endswith("selected_feature_experiment_summary.json")
    assert "reports/run_logs/champion_reopen" in command.log_path.replace("\\", "/")


def test_seed_replay_uses_fixed_tabprep_seed_for_catboost_seed_stability() -> None:
    commands = _build_commands(
        config=_config(),
        stage="seed_replay",
        run_tag="unit-run",
        sample_rows_override=None,
    )

    assert len(commands) == 2
    for command in commands:
        tabprep_idx = command.command.index("--tabprep-seed")
        assert command.command[tabprep_idx + 1] == "42"
        assert "--full-data" in command.command


def test_claim_max_downstream_keeps_mandatory_and_paper_facing_cases() -> None:
    candidates = [
        {"case_name": "opaque_rank1", "paper_facing": False, "claim_pd_score": 9.0},
        {"case_name": "opaque_rank2", "paper_facing": False, "claim_pd_score": 8.0},
        {"case_name": "pool93_woe", "paper_facing": True, "claim_pd_score": 7.0},
        {"case_name": "pool93", "paper_facing": True, "claim_pd_score": 6.0},
        {"case_name": "pool93_business80", "paper_facing": True, "claim_pd_score": 5.0},
    ]

    selected, policy = _select_downstream_candidates(
        candidates,
        top_k=2,
        mandatory_cases=["pool93"],
        paper_facing_top_k=2,
    )

    assert [row["case_name"] for row in selected] == [
        "opaque_rank1",
        "opaque_rank2",
        "pool93_woe",
        "pool93",
    ]
    assert policy["missing_mandatory_cases"] == []
    assert "mandatory_case" in selected[3]["selection_reasons"]
    assert "paper_facing_top_k" in selected[2]["selection_reasons"]


def test_claim_max_downstream_can_skip_dedicated_pool93_lane() -> None:
    candidates = [
        {"case_name": "pool93_woe", "paper_facing": True, "claim_pd_score": 7.0},
        {"case_name": "pool93", "paper_facing": True, "claim_pd_score": 6.0},
        {"case_name": "pool93_business80", "paper_facing": True, "claim_pd_score": 5.0},
    ]

    selected, policy = _select_downstream_candidates(
        candidates,
        top_k=2,
        mandatory_cases=["pool93"],
        paper_facing_top_k=3,
        skip_cases=["pool93"],
    )

    assert [row["case_name"] for row in selected] == ["pool93_woe", "pool93_business80"]
    assert policy["skip_cases"] == ["pool93"]
    assert policy["missing_mandatory_cases"] == []


def test_claim_max_paper_facing_case_detection_includes_pool93_family() -> None:
    assert _is_paper_facing_case("pool93")
    assert _is_paper_facing_case("pool93_woe")
    assert _is_paper_facing_case("pool93_business80")
    assert _is_paper_facing_case("pooltop72_business80")
    assert not _is_paper_facing_case("pooltop72_tab60")


def test_portfolio_command_separates_proxy_and_exact_sampling(tmp_path) -> None:
    command = _portfolio_command(
        portfolio_profile={
            "candidate_policy_families": ["blended_uncertainty"],
            "execution": {
                "solver_backend": "cuopt",
                "exact_solver_backend": "highs",
                "frontier_only": True,
            },
            "frontier": {
                "proxy_candidates_per_conformal_finalist": 100000,
                "exact_max_candidates": 0,
                "exact_random_states": "42,52,62",
                "exact_checkpoint_every": 25,
                "exact_threads": 8,
                "exact_rerank_top_k": 60,
            },
            "grids": {
                "risk_grid": "0.16",
                "gamma_grid": "0.45",
                "aversion_grid": "0",
                "delta_cap_grid": "1.0",
                "tail_focus_grid": "1.0",
                "alpha_grid": "0.01",
                "random_states": "42",
                "budget_profiles": "free",
            },
            "incumbent_region": {
                "risk_neighbors": "0.16",
                "gamma_neighbors": "0.45",
                "policy_modes": "blended_uncertainty",
            },
        },
        conformal_intervals_path=tmp_path / "intervals.parquet",
        run_label="unit",
        output_dir=tmp_path / "out",
        model_dir=tmp_path / "model",
    )

    assert command[command.index("--max-candidates") + 1] == "100000"
    assert command[command.index("--exact-max-candidates") + 1] == "0"
    assert command[command.index("--exact-random-states") + 1] == "42,52,62"
    assert command[command.index("--exact-checkpoint-every") + 1] == "25"
    assert command[command.index("--exact-threads") + 1] == "8"
    assert command[command.index("--budget-profiles") + 1] == "free"
    assert "--frontier-only" in command
