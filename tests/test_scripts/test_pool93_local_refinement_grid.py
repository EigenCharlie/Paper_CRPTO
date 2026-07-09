from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from scripts.search.run_pool93_ijds_local_refinement import (
    DEFAULT_ALPHA_GRID,
    _build_parser,
    _claim_summary,
    _generate_candidate_grid,
    _manifest_payload,
    _pending_refinement_tasks,
    _resolve_paths,
)
from src.optimization.certificate_semantics import IJDS_DECLARED_ALPHA_GRID

EXPECTED_PROFILE_FINGERPRINTS = {
    "stage1": (1236, "4f4fa9791ad71b3901f0af5aa55ff616426700e3245e6d5fd4cd5e923086f6ad"),
    "expanded": (7463, "a0bb03c5ee6491b2f9e1032e50c12c8aae6937a84206a989889acbb4212d371a"),
    "claim_expanded": (
        3659,
        "8345545b20e93985462a84e92bf503417911386ab1aaf0194a657aab64d8d329",
    ),
    "claim_micro": (2949, "1e4083c8b8e200c5689566a06da1e18591a11b219b13ffea5c65d575dfb796bc"),
    "claim_micro_ext": (
        4407,
        "3cc8a45b2ca0fde9a2f12cd6229b94cc7bf0119e3eeb7e742d6ce2f7bf601d08",
    ),
    "claim_bound_closure": (
        1653,
        "8d8ef58d92049809406049ff22b81831a9607c0203a2c401fb026826f2a9acee",
    ),
    "claim_bound_floor_closure": (
        2343,
        "9cb18594d1ec323cab23ffcdb4c96e481b2fb0798a18c4df73b796737e6b72c5",
    ),
    "claim_bound_terminal": (
        37068,
        "6d75ef0b7c083f9f60dfc834a50cb5da10873223dffe340665ef130e6c4c88ac",
    ),
}


def test_pool93_default_alpha_grid_uses_shared_certificate_semantics() -> None:
    assert list(IJDS_DECLARED_ALPHA_GRID) == DEFAULT_ALPHA_GRID


def _synthetic_anchor_rows() -> pd.DataFrame:
    base_fields = {
        "tail_focus_quantile": 1.0,
        "min_budget_utilization": 0.0,
        "pd_cap_slack_penalty": 0.0,
    }
    return pd.DataFrame(
        [
            {
                **base_fields,
                "candidate_rank": 96,
                "risk_tolerance": 0.156,
                "policy_mode": "tail_blended_uncertainty",
                "gamma": 0.46,
                "uncertainty_aversion": 0.125,
                "delta_cap_quantile": 1.0,
            },
            {
                **base_fields,
                "candidate_rank": 219,
                "risk_tolerance": 0.171,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.45,
                "uncertainty_aversion": 0.1,
                "delta_cap_quantile": 1.0,
            },
            {
                **base_fields,
                "candidate_rank": 223,
                "risk_tolerance": 0.173,
                "policy_mode": "capped_blended_uncertainty",
                "gamma": 0.40,
                "uncertainty_aversion": 0.1,
                "delta_cap_quantile": 0.95,
            },
        ]
    )


def _semantic_fingerprint(frame: pd.DataFrame) -> str:
    blob = "\n".join(frame["semantic_policy_key"].astype(str)).encode()
    return hashlib.sha256(blob).hexdigest()


@pytest.mark.parametrize("profile", EXPECTED_PROFILE_FINGERPRINTS)
def test_pool93_local_refinement_grid_is_stable_by_profile(profile: str) -> None:
    expected_rows, expected_sha = EXPECTED_PROFILE_FINGERPRINTS[profile]

    candidates = _generate_candidate_grid(
        _synthetic_anchor_rows(),
        profile=profile,
        solver_backend="highspy",
    )

    assert len(candidates) == expected_rows
    assert _semantic_fingerprint(candidates) == expected_sha
    assert candidates["local_candidate_id"].tolist() == list(range(1, expected_rows + 1))
    assert candidates["semantic_policy_key"].is_unique


def test_pool93_local_refinement_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="profile must be one of"):
        _generate_candidate_grid(
            _synthetic_anchor_rows(),
            profile="broad_new_search",
            solver_backend="highspy",
        )


def test_pool93_manifest_paths_and_pending_tasks_are_coherent(tmp_path) -> None:
    args = _build_parser().parse_args(
        [
            "--run-tag",
            "unit/run",
            "--output-dir",
            str(tmp_path / "out"),
            "--model-dir",
            str(tmp_path / "model"),
            "--source-bound-eval",
            str(tmp_path / "source.parquet"),
            "--source-selection",
            str(tmp_path / "selection.json"),
        ]
    )
    paths = _resolve_paths(args, run_tag="unit_run")
    candidates = pd.DataFrame({"local_candidate_id": [1, 2]})

    pending = _pending_refinement_tasks(
        candidates=candidates,
        alpha_grid=[0.01, 0.03],
        completed_keys={(1, 0.01)},
    )
    manifest = _manifest_payload(
        args=args,
        paths=paths,
        run_tag="unit_run",
        source_bound_eval=tmp_path / "source.parquet",
        source_selection=tmp_path / "selection.json",
        conformal_intervals_path="data/processed/conformal.parquet",
        anchor_ranks=[96, 219, 223],
        alpha_grid=[0.01, 0.03],
    )

    assert [(row["local_candidate_id"], alpha) for row, alpha in pending] == [
        (1, 0.03),
        (2, 0.01),
        (2, 0.03),
    ]
    assert manifest["candidates_path"] == str(paths.candidates_path)
    assert manifest["claim_summary_path"] == str(paths.claim_summary_path)
    assert manifest["run_tag"] == "unit_run"


def test_claim_summary_exposes_finite_grid_and_balanced_claim() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "claim_rank": 1,
                "local_candidate_id": 1,
                "local_family": "endpoint",
                "anchor_rank": 96,
                "source_reason": "max_return",
                "risk_tolerance": 0.18,
                "policy_mode": "tail_blended_uncertainty",
                "gamma": 0.40,
                "delta_cap_quantile": 1.0,
                "tail_focus_quantile": 1.0,
                "uncertainty_aversion": 0.05,
                "alpha01_realized_total_return": 190000.0,
                "alpha01_gamma_cp": 0.20,
                "alpha01_weighted_miscoverage_V": 0.05,
                "alpha01_weighted_pd_true": 0.11,
                "alpha01_empirical_coverage_funded": 0.92,
                "alpha01_exact_pass": True,
                "all_alpha_pass": True,
                "alpha_exact_pass_count": 2,
                "alpha_exact_check_count": 2,
                "alpha_mean_gamma_cp": 0.18,
                "alpha_mean_weighted_miscoverage_V": 0.04,
                "n_funded_mean": 50,
                "allocator_backends": "highspy",
            },
            {
                "claim_rank": 2,
                "local_candidate_id": 2,
                "local_family": "body",
                "anchor_rank": 219,
                "source_reason": "balanced",
                "risk_tolerance": 0.17,
                "policy_mode": "capped_blended_uncertainty",
                "gamma": 0.55,
                "delta_cap_quantile": 0.975,
                "tail_focus_quantile": 1.0,
                "uncertainty_aversion": 0.05,
                "alpha01_realized_total_return": 185000.0,
                "alpha01_gamma_cp": 0.10,
                "alpha01_weighted_miscoverage_V": 0.03,
                "alpha01_weighted_pd_true": 0.10,
                "alpha01_empirical_coverage_funded": 0.94,
                "alpha01_exact_pass": True,
                "all_alpha_pass": True,
                "alpha_exact_pass_count": 2,
                "alpha_exact_check_count": 2,
                "alpha_mean_gamma_cp": 0.11,
                "alpha_mean_weighted_miscoverage_V": 0.03,
                "n_funded_mean": 48,
                "allocator_backends": "highspy",
            },
            {
                "claim_rank": 3,
                "local_candidate_id": 3,
                "local_family": "failed",
                "anchor_rank": 223,
                "source_reason": "not_all_alpha",
                "risk_tolerance": 0.16,
                "policy_mode": "blended_uncertainty",
                "gamma": 0.60,
                "delta_cap_quantile": 1.0,
                "tail_focus_quantile": 1.0,
                "uncertainty_aversion": 0.10,
                "alpha01_realized_total_return": 200000.0,
                "alpha01_gamma_cp": 0.09,
                "alpha01_weighted_miscoverage_V": 0.02,
                "alpha01_weighted_pd_true": 0.09,
                "alpha01_empirical_coverage_funded": 0.95,
                "alpha01_exact_pass": True,
                "all_alpha_pass": False,
                "alpha_exact_pass_count": 1,
                "alpha_exact_check_count": 2,
                "alpha_mean_gamma_cp": 0.10,
                "alpha_mean_weighted_miscoverage_V": 0.02,
                "n_funded_mean": 45,
                "allocator_backends": "highspy",
            },
        ]
    )
    bound_eval = pd.DataFrame(
        {
            "alpha": [0.01, 0.01, 0.03],
            "all_bounds_hold": [True, False, True],
            "violation": [0.0, 0.02, 0.0],
            "gamma_cp": [0.1, 0.2, 0.15],
            "weighted_miscoverage_V": [0.03, 0.05, 0.04],
        }
    )

    summary = _claim_summary(leaderboard, bound_eval, alpha_grid=[0.03, 0.01, 0.01])

    assert summary["finite_grid_policy"]["alpha_grid"] == [0.01, 0.03]
    assert summary["n_policies"] == 3
    assert summary["n_all_alpha_passers"] == 2
    assert summary["n_all_alpha_passers_above_return_floor"] == 2
    assert summary["max_return_claim"]["local_candidate_id"] == 1
    assert summary["best_gamma_cp_return_floor_claim"]["local_candidate_id"] == 2
    assert summary["best_weighted_miscoverage_return_floor_claim"]["local_candidate_id"] == 2
    assert summary["balanced_return_bound_claim"]["local_candidate_id"] == 2
    assert summary["by_family"]["failed"]["n_all_alpha_passers"] == 0
    assert summary["by_alpha"]["0.01"]["n_checks"] == 2
