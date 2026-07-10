from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts.search import run_conformal_reopen_search as reopen
from scripts.search.run_conformal_reopen_search import (
    Phase1ConfirmationResult,
    _maybe_apply_phase2,
    _phase1_from_resume,
    _phase2_metric_blocked,
    _phase2_run_reason,
    _phase2_top_designs,
    _rank_phase2_candidates,
    _run_phase1_oot_confirmation,
    _run_phase2_search,
)


def _design(*, partition: str, alpha: float, width: float, rank: int) -> dict[str, object]:
    return {
        "partition": partition,
        "partition_probability_source": "calibrated",
        "n_score_bins": 10,
        "fallback_mode": "grade_then_global",
        "alpha_used_90": alpha,
        "alpha_used_95": 0.05,
        "score_scale_family": "bernoulli_sqrt",
        "min_group_size": 500,
        "calibration_fraction": 0.50,
        "avg_width_90": width,
        "selection_rank": rank,
    }


def test_phase2_top_designs_prefers_phase1_oot_confirmed_candidates() -> None:
    inner = pd.DataFrame(
        [
            _design(partition="score_decile_mondrian", alpha=0.085, width=0.79, rank=1),
            _design(partition="grade", alpha=0.095, width=0.77, rank=2),
        ]
    )
    oot = pd.DataFrame(
        [
            _design(partition="grade_x_scoreband_mondrian", alpha=0.075, width=0.78, rank=1),
        ]
    )

    top, source = _phase2_top_designs(
        aggregated=inner,
        phase1_candidates_frame=oot,
        top_k=2,
    )

    assert source == "phase1_oot_confirmed"
    assert top.iloc[0]["partition"] == "grade_x_scoreband_mondrian"
    assert set(top["phase2_design_source"]) == {"phase1_oot_confirmed"}


def test_phase2_top_designs_falls_back_to_inner_when_oot_empty() -> None:
    inner = pd.DataFrame(
        [
            _design(partition="score_decile_mondrian", alpha=0.085, width=0.79, rank=1),
        ]
    )

    top, source = _phase2_top_designs(
        aggregated=inner,
        phase1_candidates_frame=pd.DataFrame(),
        top_k=2,
    )

    assert source == "phase1_inner_aggregate"
    assert top.iloc[0]["partition"] == "score_decile_mondrian"
    assert set(top["phase2_design_source"]) == {"phase1_inner_aggregate"}


def _passing_policy(*, width: float = 0.42) -> dict[str, object]:
    return {
        "overall_pass": True,
        "strict_overall_pass": True,
        "methodological_justification_pass": True,
        "coverage_90": 0.90,
        "avg_width_90": width,
        "min_group_coverage_90": 0.89,
        "warning_alerts": 0,
        "total_alerts": 0,
    }


def test_phase1_resume_result_preserves_source_paths_and_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aggregate = pd.DataFrame(
        [
            _design(partition="grade", alpha=0.10, width=0.40, rank=1),
            _design(partition="score_decile_mondrian", alpha=0.09, width=0.41, rank=2),
        ]
    )
    source_paths = {
        "inner_aggregate": tmp_path / "source_aggregate.parquet",
        "inner_search": tmp_path / "source_inner.parquet",
    }
    aggregate.to_parquet(source_paths["inner_aggregate"], index=False)

    shortlist = aggregate.head(1).copy()

    def fake_paths(_run_tag: str) -> dict[str, Path]:
        return source_paths

    def fake_shortlist(
        *, source_run_tag: str, top_k_inner: int
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        assert source_run_tag == "source-run"
        assert top_k_inner == 1
        return shortlist, {"source": "source-run"}

    monkeypatch.setattr(reopen, "_reopen_artifact_paths", fake_paths)
    monkeypatch.setattr(reopen, "_build_resume_shortlist", fake_shortlist)

    result = _phase1_from_resume(
        resume_from_run_tag="source-run",
        top_k_inner=1,
        output_paths={"phase1_shortlist": tmp_path / "shortlist.parquet"},
    )

    assert result.aggregate_path == str(source_paths["inner_aggregate"])
    assert result.inner_search_path == str(source_paths["inner_search"])
    assert result.inner_search_winner["partition"] == "grade"
    assert result.resume_meta == {"source": "source-run"}
    assert (tmp_path / "shortlist.parquet").exists()


def test_phase1_oot_confirmation_writes_ranked_candidate_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shortlist = pd.DataFrame(
        [
            _design(partition="grade", alpha=0.10, width=0.50, rank=1),
            _design(partition="score_decile_mondrian", alpha=0.09, width=0.42, rank=2),
        ]
    )

    def fake_run_candidate(**kwargs: Any) -> dict[str, object]:
        rank = int(kwargs["rank"])
        return {
            "namespace": f"candidate-{rank}",
            "policy_status": _passing_policy(width=0.50 if rank == 1 else 0.42),
            "set_status": {"summary": {"set_coverage": 0.91, "singleton_rate": 0.73}},
            "selection_status": {"promotion_pass": rank == 2, "selected_variant": "variant"},
        }

    monkeypatch.setattr(reopen, "_run_phase1_oot_candidate", fake_run_candidate)

    result = _run_phase1_oot_confirmation(
        run_tag="test-run",
        env={},
        shortlist=shortlist,
        output_paths={"phase1_final_candidates": tmp_path / "phase1_final.parquet"},
        alpha_candidates_95=[0.05],
        partition_candidates=["grade"],
        partition_probability_sources=["calibrated"],
        n_score_bins_candidates=[10],
        fallback_modes=["grade_then_global"],
        score_scale_families=["none"],
        calibration_fractions=[1.0],
        sidecar_cfg={},
        validation_cfg={},
    )

    assert result.best_namespace == "candidate-2"
    assert result.final_namespace == "candidate-2"
    assert result.final_decision == "promotable_for_followup"
    assert result.frame.iloc[0]["avg_width_90"] == 0.42
    assert (tmp_path / "phase1_final.parquet").exists()


def test_maybe_apply_phase2_respects_phase1_only() -> None:
    phase1 = Phase1ConfirmationResult(
        candidates=[],
        frame=pd.DataFrame([{"namespace": "phase1"}]),
        best_namespace="phase1",
        final_policy=_passing_policy(),
        final_sets={"summary": {"set_coverage": 0.91}},
        final_decision="promotable_for_followup",
        final_namespace="phase1",
    )

    result = _maybe_apply_phase2(
        run_tag="run",
        upstream_run_tag="upstream",
        env={},
        aggregated=pd.DataFrame(),
        phase1=phase1,
        phase1_only=True,
        force_phase2=True,
        alpha_candidates_95=[],
        tuning_holdout_ratios=[],
        inner_random_states=[],
        partition_candidates=[],
        partition_probability_sources=[],
        n_score_bins_candidates=[],
        fallback_modes=[],
        score_scale_families=[],
        calibration_fractions=[],
        phase2_cfg={"enabled": True},
        sidecar_cfg={},
        validation_cfg={},
    )

    assert result.final_namespace == "phase1"
    assert result.final_decision == "promotable_for_followup"
    assert result.phase2_summary is None
    assert _phase2_run_reason(force_phase2=True, phase2_always_evaluate=True) == "forced"


def test_phase2_metric_gate_and_ranking_are_explicit() -> None:
    assert _phase2_metric_blocked(
        calibration_metrics={"ece": 0.12, "brier_score": 0.21},
        baseline_metrics={"ece": 0.10, "brier_score": 0.20},
        max_metric_degradation={"ece": 0.01, "brier_score": 0.02},
    )
    assert not _phase2_metric_blocked(
        calibration_metrics={"ece": 0.105},
        baseline_metrics={"ece": 0.10},
        max_metric_degradation={"ece": 0.01},
    )

    ranked = _rank_phase2_candidates(
        pd.DataFrame(
            [
                {
                    "artifact_namespace": "wide",
                    "calibrator_method": "platt",
                    "holdout_coverage": 0.91,
                    "holdout_width": 0.30,
                    "calibrator_ece": 0.01,
                    "calibrator_adaptive_ece": 0.01,
                    "calibrator_brier": 0.10,
                    "calibrator_phi_brier": 0.20,
                    "selection_rank": 1,
                },
                {
                    "artifact_namespace": "centered",
                    "calibrator_method": "isotonic",
                    "holdout_coverage": 0.90,
                    "holdout_width": 0.50,
                    "calibrator_ece": 0.02,
                    "calibrator_adaptive_ece": 0.02,
                    "calibrator_brier": 0.10,
                    "calibrator_phi_brier": 0.10,
                    "selection_rank": 2,
                },
            ]
        )
    )

    assert ranked.iloc[0]["artifact_namespace"] == "centered"


def _phase2_paths(tmp_path: Path) -> dict[str, Path]:
    data_dir = tmp_path / "data"
    models_dir = tmp_path / "models"
    data_dir.mkdir()
    models_dir.mkdir()
    return {
        "data_dir": data_dir,
        "models_dir": models_dir,
        "phase2_search": data_dir / "phase2.parquet",
        "phase2_progress": models_dir / "phase2_progress.json",
    }


def test_run_phase2_search_records_metric_gate_skip(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    paths = _phase2_paths(tmp_path)
    aggregate = pd.DataFrame([_design(partition="grade", alpha=0.10, width=0.40, rank=1)])

    def fake_fit_calibrator(
        *, method: str, output_path: Path, upstream_run_tag: str
    ) -> tuple[str, dict[str, float]]:
        del output_path, upstream_run_tag
        if method == "venn_abers":
            return method, {"ece": 0.10}
        return method, {"ece": 0.20}

    monkeypatch.setattr(reopen, "_reopen_artifact_paths", lambda _run_tag: paths)
    monkeypatch.setattr(reopen, "_fit_calibrator", fake_fit_calibrator)

    decision, policy, sets, summary = _run_phase2_search(
        run_tag="phase2-skip",
        upstream_run_tag="upstream",
        env={},
        aggregated=aggregate,
        phase1_candidates_frame=pd.DataFrame(),
        alpha_candidates_95=[0.05],
        tuning_holdout_ratios=[0.2],
        inner_random_states=[42],
        partition_candidates=["grade"],
        partition_probability_sources=["calibrated"],
        n_score_bins_candidates=[10],
        fallback_modes=["grade_then_global"],
        score_scale_families=["none"],
        calibration_fractions=[1.0],
        phase2_cfg={"calibrators": ["platt"], "max_metric_degradation": {"ece": 0.01}},
        sidecar_cfg={},
        validation_cfg={},
    )

    progress = json.loads(paths["phase2_progress"].read_text(encoding="utf-8"))
    assert decision == "policy_review_candidate"
    assert policy == {}
    assert sets == {}
    assert summary is not None
    assert summary["status"] == "no_noninferior_calibrator_candidate"
    assert progress["skipped"][0]["reason"] == "metric_degradation_gate"
    assert paths["phase2_search"].exists()


def test_run_phase2_search_ranks_and_confirms_best_candidate(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    paths = _phase2_paths(tmp_path)
    aggregate = pd.DataFrame(
        [
            _design(partition="grade", alpha=0.10, width=0.50, rank=1),
            _design(partition="score_decile_mondrian", alpha=0.09, width=0.42, rank=2),
        ]
    )

    def fake_fit_calibrator(
        *, method: str, output_path: Path, upstream_run_tag: str
    ) -> tuple[str, dict[str, float]]:
        del output_path, upstream_run_tag
        return method, {"ece": 0.02, "adaptive_ece": 0.03, "brier_score": 0.10}

    def fake_resolve_run_paths(namespace: str) -> dict[str, Path]:
        return {"results": tmp_path / f"{namespace}.pkl"}

    def fake_load_pickle(path: Path) -> dict[str, dict[str, float]]:
        if "rank-2" in path.name:
            return {"metrics_90": {"empirical_coverage": 0.90, "avg_interval_width": 0.44}}
        return {"metrics_90": {"empirical_coverage": 0.88, "avg_interval_width": 0.30}}

    def fake_final_candidate(**kwargs: Any) -> dict[str, object]:
        assert kwargs["phase_prefix"] == "phase2"
        assert kwargs["design"]["selection_rank"] == 2
        assert str(kwargs["calibrator_override_path"]).endswith("platt.pkl")
        return {
            "namespace": "phase2-final",
            "policy_status": _passing_policy(width=0.44),
            "set_status": {"summary": {"set_coverage": 0.91}},
        }

    monkeypatch.setattr(reopen, "_reopen_artifact_paths", lambda _run_tag: paths)
    monkeypatch.setattr(reopen, "_fit_calibrator", fake_fit_calibrator)
    monkeypatch.setattr(reopen, "_run_python", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(reopen, "_resolve_run_paths", fake_resolve_run_paths)
    monkeypatch.setattr(reopen, "_load_pickle", fake_load_pickle)
    monkeypatch.setattr(reopen, "_run_phase1_oot_candidate", fake_final_candidate)

    decision, policy, sets, summary = _run_phase2_search(
        run_tag="phase2-success",
        upstream_run_tag="upstream",
        env={},
        aggregated=aggregate,
        phase1_candidates_frame=pd.DataFrame(),
        alpha_candidates_95=[0.05],
        tuning_holdout_ratios=[0.2],
        inner_random_states=[42],
        partition_candidates=["grade"],
        partition_probability_sources=["calibrated"],
        n_score_bins_candidates=[10],
        fallback_modes=["grade_then_global"],
        score_scale_families=["none"],
        calibration_fractions=[1.0],
        phase2_cfg={"calibrators": ["platt"], "max_metric_degradation": {}},
        sidecar_cfg={},
        validation_cfg={},
    )

    phase2_search = pd.read_parquet(paths["phase2_search"])
    assert decision == "promotable_for_followup"
    assert policy["avg_width_90"] == 0.44
    assert sets["summary"]["set_coverage"] == 0.91
    assert summary is not None
    assert summary["final_namespace"] == "phase2-final"
    assert summary["best_candidate"]["selection_rank"] == 2
    assert phase2_search.iloc[0]["selection_rank"] == 2
