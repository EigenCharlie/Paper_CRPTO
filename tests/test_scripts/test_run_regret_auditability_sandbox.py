from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.search.run_regret_auditability_sandbox as sandbox
from scripts.search.run_regret_auditability_sandbox import (
    FEATURE_PROFILES,
    MONOTONIC_POLICIES,
    PORTFOLIO_ALPHA_GRID,
    PhaseCommand,
    _pd_validation_policy,
    _pending_commands_for_group,
    _phase_command_groups,
    _rank_pd_candidate_rows,
    assert_safe_output_path,
    build_phase_commands,
    compute_auditability_score,
    compute_decision_regret,
    load_resume_manifest,
    materialize_feature_profiles,
    materialize_monotonic_policies,
)


def test_protected_path_rejection_blocks_frozen_outputs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"

    with pytest.raises(ValueError, match="protected CRPTO artifact"):
        assert_safe_output_path("models/pd_canonical.cbm", repo_root=repo_root)

    with pytest.raises(ValueError, match="protected CRPTO directory"):
        assert_safe_output_path(
            "data/processed/portfolio_bound_aware/rank1_candidate/frontier.parquet",
            repo_root=repo_root,
        )

    external = tmp_path / "outside" / "frontier.parquet"
    assert assert_safe_output_path(external, repo_root=repo_root) == external.resolve()


def test_monotonic_policy_materialization_matches_sandbox_lanes() -> None:
    policies = materialize_monotonic_policies()

    assert set(policies) == set(MONOTONIC_POLICIES)
    assert policies["canonical_4"] == {
        "installment": 1,
        "annual_inc": -1,
        "dti": 1,
        "loan_to_income": 1,
    }
    assert policies["affordability_rate_5"]["int_rate"] == 1
    assert policies["credit_history_7"]["delinq_severity"] == 1
    assert policies["credit_history_7"]["delinq_recency"] == -1
    assert policies["bureau_utilization_11"]["bc_util"] == 1
    assert policies["bureau_behavior_15"]["pct_tl_nvr_dlq"] == -1
    assert policies["inquiry_velocity_12"]["mths_since_recent_inq"] == -1


def test_feature_profiles_materialize_expected_lanes() -> None:
    profiles = materialize_feature_profiles()

    assert set(profiles) == set(FEATURE_PROFILES)
    assert profiles["core_stable"]["stable_core_enabled"] is True
    assert "WOE_FEATURES" in profiles["core_woe"]["groups"]
    assert "CHALLENGER_FEATURE_POOL_V2" in profiles["full_challenger"]["groups"]


def test_decision_regret_is_oracle_minus_policy_return() -> None:
    assert compute_decision_regret(1250.0, 1000.0) == 250.0
    assert compute_decision_regret(1000.0, 1250.0) == -250.0


def test_auditability_score_weights_all_checks() -> None:
    result = compute_auditability_score(
        {
            "coverage90": 0.91,
            "coverage95": 0.951,
            "min_group_coverage": 0.90,
            "critical_alerts": 0,
            "alpha01_exact_pass": True,
            "violation": 0.0,
            "weighted_miscoverage_V": 0.05,
            "alpha": 0.01,
            "monotonic_audit_pass": True,
            "reproducible_resume_manifest": True,
        }
    )

    assert result["score"] == 100
    assert all(result["checks"].values())


def test_auditability_score_penalizes_failed_guarantees() -> None:
    result = compute_auditability_score(
        {
            "coverage90": 0.89,
            "coverage95": 0.94,
            "min_group_coverage": 0.80,
            "critical_alerts": 1,
            "alpha01_exact_pass": False,
            "violation": 0.01,
            "weighted_miscoverage_V": 0.2,
            "alpha": 0.01,
            "monotonic_audit_pass": True,
            "reproducible_resume_manifest": True,
        }
    )

    assert result["score"] == 15
    assert result["checks"]["monotonic_audit_pass"]
    assert result["checks"]["reproducible_resume_manifest"]


def test_resume_manifest_loading_roundtrip(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sandbox_manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": "x", "phase": "plan"}))

    assert load_resume_manifest(manifest_path)["phase"] == "plan"
    assert load_resume_manifest(tmp_path / "missing.json") == {}


def _command(name: str, phase: str, output: Path) -> PhaseCommand:
    return PhaseCommand(
        name=name,
        phase=phase,
        command=["python", "-c", "pass"],
        outputs=[str(output)],
        checkpoint=str(output),
        env={},
        max_workers=1,
        cpu_threads=1,
    )


def test_phase_command_groups_keep_consecutive_phase_batches(tmp_path: Path) -> None:
    commands = [
        _command("a", "pd-smoke", tmp_path / "a"),
        _command("b", "pd-smoke", tmp_path / "b"),
        _command("c", "conformal", tmp_path / "c"),
        _command("d", "pd-smoke", tmp_path / "d"),
    ]

    groups = _phase_command_groups(commands)

    assert [[command.name for command in group] for group in groups] == [["a", "b"], ["c"], ["d"]]


def test_pending_commands_skip_completed_outputs_on_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed_output = tmp_path / "done.txt"
    completed_output.write_text("ok", encoding="utf-8")
    pending_output = tmp_path / "todo.txt"
    monkeypatch.setattr(sandbox, "_log_command_to_mlflow", lambda **_: None)

    pending, skipped = _pending_commands_for_group(
        artifact_root=tmp_path,
        log_path=tmp_path / "command_log.csv",
        group=[
            _command("done", "pd-smoke", completed_output),
            _command("todo", "pd-smoke", pending_output),
        ],
        resume=True,
    )

    assert skipped == 1
    assert [command.name for command in pending] == ["todo"]
    assert "skipped_completed" in (tmp_path / "command_log.csv").read_text(encoding="utf-8")


def test_pd_validation_policy_scales_by_phase() -> None:
    smoke_replay, smoke_walk_forward = _pd_validation_policy("pd-smoke")
    broad_replay, broad_walk_forward = _pd_validation_policy("pd-broad")
    refine_replay, refine_walk_forward = _pd_validation_policy("pd-refine")

    assert smoke_replay["top_k_trials"] == 1
    assert smoke_walk_forward is False
    assert broad_replay["seeds"] == [42, 52, 62]
    assert broad_walk_forward is True
    assert refine_replay["top_k_trials"] == 30
    assert refine_walk_forward is True


def test_pd_candidate_ranking_prefers_auc_then_calibration() -> None:
    ranked = _rank_pd_candidate_rows(
        [
            {"lane_id": "a", "auc_roc": 0.75, "brier_score": 0.11, "ece": 0.03},
            {"lane_id": "b", "auc_roc": 0.76, "brier_score": 0.13, "ece": 0.05},
            {"lane_id": "c", "auc_roc": 0.75, "brier_score": 0.10, "ece": 0.04},
        ]
    )

    assert [row["lane_id"] for row in ranked] == ["b", "c", "a"]
    assert [row["selection_rank"] for row in ranked] == [1, 2, 3]


def test_build_pd_smoke_commands_write_external_config_snapshots(tmp_path: Path) -> None:
    commands = build_phase_commands(
        artifact_root=tmp_path,
        run_tag="unit_sandbox",
        phase="pd-smoke",
        max_workers=3,
        cpu_threads=6,
    )

    expected_search_lanes = len(FEATURE_PROFILES) * len(MONOTONIC_POLICIES)
    assert len(commands) == expected_search_lanes + 1
    assert {command.phase for command in commands} == {"pd-smoke"}
    search_commands = [
        command for command in commands if command.lane_id != "incumbent__frozen_champion"
    ]
    assert len(search_commands) == expected_search_lanes
    assert all("--hpo_n_trials" in command.command for command in search_commands)
    assert all("12" in command.command for command in search_commands)
    assert {command.env["PIPELINE_RUN_TAG"] for command in commands} == {"unit_sandbox"}
    assert {command.env["CRPTO_RUN_TAG"] for command in commands} == {"unit_sandbox"}
    config_path = tmp_path / "configs" / "pd_core_stable__canonical_4_pd-smoke.yaml"
    assert config_path.exists()
    assert (tmp_path / "configs" / "feature_profiles" / "full_challenger_woe.pkl").exists()
    assert all(str(tmp_path) in output for command in commands for output in command.outputs)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["hpo"]["enqueue_trials"]
    assert config["sandbox_search"]["hpo_warm_start"]["sources"] == ["frozen_champion_pd_config"]


def test_build_portfolio_command_uses_external_output_dirs(tmp_path: Path) -> None:
    commands = build_phase_commands(
        artifact_root=tmp_path,
        run_tag="unit_sandbox",
        phase="portfolio",
        max_workers=4,
        cpu_threads=4,
    )

    assert len(commands) == 1
    command = commands[0]
    assert "--output-dir" in command.command
    assert "--model-dir" in command.command
    alpha_grid_index = command.command.index("--alpha-grid") + 1
    assert command.command[alpha_grid_index] == PORTFOLIO_ALPHA_GRID
    assert PORTFOLIO_ALPHA_GRID == "0.01,0.03,0.05,0.07,0.10,0.12,0.15,0.20"
    assert all(str(tmp_path) in output for output in command.outputs)


def test_build_conformal_command_accepts_model_override(tmp_path: Path) -> None:
    commands = build_phase_commands(
        artifact_root=tmp_path,
        run_tag="unit_sandbox",
        phase="conformal",
        max_workers=6,
        cpu_threads=1,
    )

    assert len(commands) == 1
    command = commands[0]
    assert "--artifact_root" in command.command
    assert "--model_override_path" in command.command
    assert "--calibrator_override_path" in command.command
    assert all(str(tmp_path) in output for output in command.outputs)
