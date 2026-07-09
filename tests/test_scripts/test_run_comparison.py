from __future__ import annotations

from scripts.run_comparison import _collect_status_metadata, _gate_ab_no_regression


def _ab_status(control: float, robust: float, **extra: object) -> dict[str, object]:
    return {
        "metrics_a": {"total_return": control},
        "metrics_b": {"total_return": robust},
        **extra,
    }


def _status(run_tag: str) -> dict[str, str]:
    return {
        "schema_version": "test.1",
        "generated_at_utc": "2026-07-08T20:00:00+00:00",
        "run_tag": run_tag,
    }


def test_collect_status_metadata_passes_when_core_statuses_match() -> None:
    cur = {
        "dvc_metrics_meta": _status("run-a"),
        "pipeline_summary": _status("run-a"),
        "conformal_status": _status("run-a"),
        "fairness_status": _status("run-a"),
        "governance_status": _status("run-a"),
        "ab_simulation_status": _status("run-a"),
    }

    metadata = _collect_status_metadata(cur, expected_run_tag="run-a")

    assert metadata["passed"] is True
    assert metadata["all_have_metadata"] is True
    assert metadata["run_tags_observed"] == ["run-a"]
    assert metadata["mismatched_run_tag_artifacts"] == []
    assert len(metadata["critical_artifacts"]) == 6


def test_collect_status_metadata_allows_causal_insights_only_mismatch() -> None:
    cur = {
        "dvc_metrics_meta": _status("run-a"),
        "pipeline_summary": _status("run-a"),
        "conformal_status": _status("run-a"),
        "fairness_status": _status("run-a"),
        "governance_status": _status("run-a"),
        "ab_simulation_status": _status("run-a"),
        "causal_effect_status": _status("older-causal-run"),
    }

    metadata = _collect_status_metadata(cur, expected_run_tag="run-a")

    assert metadata["passed"] is True
    assert metadata["run_tag_matches_expected"] is False
    assert metadata["run_tag_matches_expected_operational"] is True
    assert metadata["causal_only_mismatch"] is True
    assert metadata["non_causal_mismatched_run_tag_artifacts"] == []


def test_gate_ab_no_regression_passes_when_current_self_gate_passes() -> None:
    base = {"ab_simulation_status": _ab_status(100.0, 120.0)}
    cur = {
        "ab_simulation_status": _ab_status(
            101.0,
            119.0,
            no_regression={
                "passed": True,
                "diff_total_return": 18.0,
                "tolerance_total_return": 5.0,
            },
            comparison={"p_value": 0.12, "significant": False},
            n_candidates_used=50,
        )
    }

    gate = _gate_ab_no_regression(base, cur)

    assert gate.name == "ab_no_regression"
    assert gate.passed is True
    assert gate.details["checks"]["self_no_regression_ok"] is True
    assert gate.details["warnings"]["control_vs_baseline_warning"] is False
    assert gate.details["diagnostics"]["gate_mode"] == "no_regression"


def test_gate_ab_no_regression_allows_selective_ambiguity_cross_gate() -> None:
    base = {"ab_simulation_status": _ab_status(100.0, 120.0)}
    cur = {
        "ab_simulation_status": _ab_status(
            100.0,
            80.0,
            decision_scenario="selective_ambiguity_defer",
            no_regression={"passed": False, "diff_total_return": -20.0},
            cross_scenario_gate={"passed": True},
        )
    }

    gate = _gate_ab_no_regression(base, cur)

    assert gate.passed is True
    assert gate.details["checks"]["self_no_regression_ok"] is True
    assert gate.details["checks"]["cross_scenario_gate_ok"] is True
    assert gate.details["warnings"]["robust_vs_baseline_warning"] is True
