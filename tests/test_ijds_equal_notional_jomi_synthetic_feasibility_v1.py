"""Protocol, numerical, and transport tests for the sealed synthetic JOMI study."""

from __future__ import annotations

import math
import os
import time
from collections.abc import Mapping
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import scripts.experiments.run_ijds_equal_notional_jomi_synthetic_feasibility_v1 as runner

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT / "configs/experiments/ijds_equal_notional_jomi_synthetic_feasibility_2026-08-08_v1.yaml"
)


class _RecordingObserver:
    def __init__(self) -> None:
        self.completed: list[int] = []

    def emit(
        self,
        completed_units: int,
        *,
        phase: str,
        detail: dict[str, Any] | None = None,
        force: bool = False,
    ) -> None:
        del phase, detail, force
        self.completed.append(completed_units)


def _canonical_config() -> dict[str, Any]:
    return runner._load_config(CONFIG)


def _small_design() -> dict[str, Any]:
    design = {
        **runner.EXPECTED_DESIGN_SCALARS,
        "rng_streams": list(runner.EXPECTED_RNG_STREAMS),
        "primary_dgp": dict(runner.EXPECTED_DGP),
    }
    design.update(
        {
            "alpha": 0.20,
            "repetitions": 4,
            "train_size": 2_000,
            "design_size": 1_000,
            "calibration_size": 200,
            "test_size": 60,
            "selected_k": 10,
            "allocation_per_selected_unit": 0.10,
        }
    )
    return design


def _staged_bytes(tmp_path: Path) -> dict[str, Path]:
    staging = tmp_path / "external-staging"
    staging.mkdir()
    staged: dict[str, Path] = {}
    for index, filename in enumerate(
        (*runner.DATA_FILENAMES, runner.SUMMARY_FILENAME, runner.RECEIPT_FILENAME)
    ):
        path = staging / filename
        path.write_bytes(f"sealed-{index}-{filename}\n".encode())
        staged[filename] = path
    return staged


def test_canonical_config_is_exact_and_claim_boundary_is_synthetic_only() -> None:
    config = _canonical_config()

    runner._require_fixed_contract(config)
    assert config["design"]["rng_streams"] == runner.EXPECTED_RNG_STREAMS
    assert config["interpretation"] == {
        "synthetic_only": True,
        "active_empirical_evidence": False,
        "lendingclub_validity_claimed": False,
        "temporal_transport_claimed": False,
        "fractional_lp_validity_claimed": False,
        "joint_label_coverage_claimed": False,
        "prospective_confirmation_claimed": False,
        "permitted_claims": [
            "theorem_to_code_reconciliation_under_enumerated_top_k_cases",
            "exact_equal_notional_count_and_dollar_fcp_identity",
            ("beta_binomial_reference_size_finite_threshold_corollary_under_iid_continuous_scores"),
            "monte_carlo_behavior_under_the_single_locked_synthetic_iid_dgp",
        ],
    }
    drifted = deepcopy(config)
    drifted["stop_rules"]["stop_on_primary_reference_size_below_resolution"] = False
    with pytest.raises(RuntimeError, match="stop rule"):
        runner._require_fixed_contract(drifted)


def test_rng_roles_are_reproducible_distinct_and_never_reused() -> None:
    design = _small_design()
    fixed_a, replicated_a = runner._spawn_locked_rng_streams(design)
    fixed_b, replicated_b = runner._spawn_locked_rng_streams(design)

    fixed_draws_a = {name: float(generator.random()) for name, generator in fixed_a.items()}
    fixed_draws_b = {name: float(generator.random()) for name, generator in fixed_b.items()}
    assert fixed_draws_a == fixed_draws_b
    assert len(set(fixed_draws_a.values())) == len(fixed_draws_a)
    assert set(replicated_a) == set(runner.REPLICATION_RNG_STREAMS)
    assert all(len(streams) == design["repetitions"] for streams in replicated_a.values())
    first_a = {
        name: float(np.random.default_rng(streams[0]).random())
        for name, streams in replicated_a.items()
    }
    first_b = {
        name: float(np.random.default_rng(replicated_b[name][0]).random()) for name in replicated_b
    }
    assert first_a == first_b
    assert len(set(first_a.values())) == len(first_a)


def test_count_and_dollar_fcp_are_computed_on_independent_paths() -> None:
    count, dollar = runner._count_and_dollar_fcp_from_allocations(
        (1, 0),
        (0.5, 0.5),
        budget=1.0,
    )
    assert count == dollar == Fraction(1, 2)

    count, dollar = runner._count_and_dollar_fcp_from_allocations(
        (1, 0),
        (0.75, 0.25),
        budget=1.0,
    )
    assert count == Fraction(1, 2)
    assert dollar == Fraction(3, 4)
    with pytest.raises(RuntimeError, match="sum exactly"):
        runner._count_and_dollar_fcp_from_allocations(
            (1, 0),
            (0.4, 0.4),
            budget=1.0,
        )


def test_analytic_frontier_matches_the_closed_primary_cell() -> None:
    frame = runner._build_analytic_reference_frontier(_canonical_config())

    assert len(frame) == 18
    primary = frame.loc[
        frame["row_type"].eq("declared_frontier_cell")
        & frame["calibration_size"].eq(5_000)
        & frame["test_size"].eq(2_000)
        & frame["selected_k"].eq(100)
    ].iloc[0]
    expected_mean = 5_000 * 101 / 2_001
    expected_variance = 5_000 * 101 * 1_900 * 7_001 / (2_001**2 * 2_002)
    assert primary["mean_reference_size"] == pytest.approx(expected_mean)
    assert primary["variance_reference_size"] == pytest.approx(expected_variance)
    assert primary["resolution_size"] == 9
    assert primary["resolution_probability"] == 1.0
    assert primary["resolution_probability_saturated_at_one"]
    assert primary["failure_probability_below_resolution"] == pytest.approx(
        5.273399938929985e-46,
        rel=1.0e-12,
    )
    assert primary["log_failure_probability_below_resolution"] == pytest.approx(
        -104.25623897349035,
        rel=1.0e-12,
    )
    large_menu = frame.loc[
        frame["row_type"].eq("declared_frontier_cell")
        & frame["calibration_size"].eq(5_000)
        & frame["test_size"].eq(6_011)
        & frame["selected_k"].eq(100)
    ].iloc[0]
    assert large_menu["resolution_probability_saturated_at_one"]
    assert large_menu["failure_probability_below_resolution"] == pytest.approx(
        1.5532497216323095e-18,
        rel=1.0e-12,
    )
    minimum_rows = frame.loc[frame["row_type"].eq("minimum_calibration_search")]
    assert len(minimum_rows) == 10
    assert minimum_rows["minimum_search_succeeded"].all()


def test_scale_fixtures_are_outcome_free_complete_and_do_not_reuse_primary_stop() -> None:
    frame = runner._build_scale_fixtures(_canonical_config())

    assert len(frame) == 30
    assert set(frame["test_size"]) == {6_011, 10_000, 28_106}
    assert frame["selected_size"].eq(100).all()
    assert frame["outcome_rows_read"].eq(0).all()
    assert frame["repeat_invariant"].all()
    assert frame["reference_size"].ge(0).all()
    assert (
        frame["finite_threshold_possible"]
        .eq(frame["reference_size"].ge(frame["resolution_size"]))
        .all()
    )


def test_oracle_census_uses_canonical_rank_interleavings_and_both_labels() -> None:
    frame = runner._build_oracle_reconciliation(_canonical_config())

    exhaustive = frame.loc[frame["fixture_kind"].eq("exhaustive_rank_interleaving")]
    assert len(exhaustive) == 126 * 1 * 2 + 462 * 2 * 2 + 495 * 2 * 2
    assert set(frame["candidate_label"]) == {0, 1}
    assert (
        frame[
            [
                "shortcut_equals_oracle",
                "calibration_permutation_invariant",
                "test_permutation_equivariant",
                "visible_id_reversal_invariant",
                "repeat_invariant",
            ]
        ]
        .to_numpy(dtype=bool)
        .all()
    )


def test_small_primary_run_is_complete_deterministic_and_equal_notional() -> None:
    design = _small_design()
    fixed, replicated = runner._spawn_locked_rng_streams(design)
    model = runner._fit_frozen_model(
        train_feature_rng=fixed["training_features"],
        train_label_rng=fixed["training_labels"],
        design_feature_rng=fixed["design_features"],
        design_label_rng=fixed["design_labels"],
        design=design,
    )
    observer = _RecordingObserver()
    replications, focal, summary = runner._run_primary_replications(
        design=design,
        model=model,
        replication_seed_streams=replicated,
        observer=observer,  # type: ignore[arg-type]
        heartbeat=None,
        run_started=time.perf_counter(),
        wall_deadline_seconds=60.0,
    )

    assert len(replications) == design["repetitions"]
    assert len(focal) == design["repetitions"] * design["selected_k"]
    assert observer.completed == [1, 2, 3, 4]
    assert replications["jomi_count_fcp"].equals(replications["jomi_dollar_fcp"])
    assert replications["vanilla_count_fcp"].equals(replications["vanilla_dollar_fcp"])
    assert focal.groupby("replication_id")["allocation"].sum().eq(1.0).all()
    assert focal["jomi_set_size"].between(0, 2).all()
    assert focal["vanilla_set_size"].between(0, 2).all()
    assert summary["one_sided_999_hoeffding_lower_bound"] <= design["alpha"]


def test_runtime_directory_must_be_fresh_external_and_have_reserved_space(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "runtime"
    config = _canonical_config()

    run_directory = runner._prepare_runtime_directory(
        external,
        repo_root=repo,
        config=config,
    )
    assert run_directory == external / runner.EXPECTED_RUN_TAG
    with pytest.raises(FileExistsError, match="already exists"):
        runner._prepare_runtime_directory(external, repo_root=repo, config=config)
    with pytest.raises(ValueError, match="outside"):
        runner._prepare_runtime_directory(
            repo / "runtime",
            repo_root=repo,
            config=config,
        )


def test_official_materialization_is_transactional_and_hash_preserving(
    tmp_path: Path,
) -> None:
    staged = _staged_bytes(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    written = runner._materialize_staged_outputs(
        staged,
        config=_canonical_config(),
        repo_root=repo,
    )

    assert set(written) == set(staged)
    assert all(written[name].read_bytes() == staged[name].read_bytes() for name in staged)
    assert not list(repo.rglob(".jomi-txn-*"))


def test_transaction_rolls_back_if_second_directory_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staged = _staged_bytes(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    final_model = repo / runner.ALLOWED_MODEL_ROOT / runner.EXPECTED_RUN_TAG
    original_replace = os.replace
    failed = False

    def fail_model_directory_promotion(
        source: str | os.PathLike[str], target: str | os.PathLike[str]
    ) -> None:
        nonlocal failed
        source_path = Path(source)
        target_path = Path(target)
        if source_path.is_dir() and target_path == final_model and not failed:
            failed = True
            raise OSError("injected model-directory promotion failure")
        original_replace(source, target)

    monkeypatch.setattr(runner.os, "replace", fail_model_directory_promotion)
    with pytest.raises(OSError, match="injected"):
        runner._materialize_staged_outputs(
            staged,
            config=_canonical_config(),
            repo_root=repo,
        )

    assert failed is True
    assert not (repo / runner.ALLOWED_DATA_ROOT / runner.EXPECTED_RUN_TAG).exists()
    assert not final_model.exists()
    assert not list(repo.rglob(".jomi-txn-*"))


def test_transaction_rolls_back_if_post_promotion_seal_fails(tmp_path: Path) -> None:
    staged = _staged_bytes(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()

    def fail_seal(_written: Mapping[str, Path]) -> None:
        raise RuntimeError("injected observer seal failure")

    with pytest.raises(RuntimeError, match="observer seal"):
        runner._materialize_staged_outputs(
            staged,
            config=_canonical_config(),
            repo_root=repo,
            on_promoted=fail_seal,
        )

    assert not (repo / runner.ALLOWED_DATA_ROOT / runner.EXPECTED_RUN_TAG).exists()
    assert not (repo / runner.ALLOWED_MODEL_ROOT / runner.EXPECTED_RUN_TAG).exists()
    assert not list(repo.rglob(".jomi-txn-*"))


def test_clean_annotated_tag_gate_precedes_runtime_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_opened = False

    def fail_clean_gate(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("clean annotated tag gate")

    def mark_runtime(*_args: Any, **_kwargs: Any) -> Path:
        nonlocal runtime_opened
        runtime_opened = True
        raise AssertionError("runtime must remain unopened")

    monkeypatch.setattr(runner, "_require_clean_annotated_head", fail_clean_gate)
    monkeypatch.setattr(runner, "_prepare_runtime_directory", mark_runtime)
    with pytest.raises(RuntimeError, match="clean annotated"):
        runner.run(config_path=CONFIG, repo_root=ROOT, runtime_root=Path("D:/CRPTO/runtime"))
    assert runtime_opened is False


def test_crc_ltt_and_reoptimization_controls_retain_their_claim_boundaries() -> None:
    config = _canonical_config()
    crc_ltt = runner._build_crc_ltt_feasibility(config)
    counterexample = runner._build_monotonicity_counterexample()

    crc = crc_ltt.loc[crc_ltt["study"].eq("finite_grid_nonmonotone_crc_design_only")]
    assert not crc.empty
    assert crc["loss_lower_bound"].eq(0.0).all()
    assert crc["loss_upper_bound"].eq(1.0).all()
    assert crc["risk_bound_mode"].eq("expected_risk_bound_no_delta_parameter").all()
    assert crc["nominal_tail_probability"].eq("not_applicable").all()
    assert crc["per_policy_tail_probability"].eq("not_applicable").all()
    assert crc["pointwise_zero_loss_terminal_required"].all()
    assert crc["required_contexts"].min() >= 129
    assert runner._crc_excess(10, 200, loss_bound=2.0) == pytest.approx(
        2.0 * runner._crc_excess(10, 200, loss_bound=1.0)
    )
    ltt = crc_ltt.loc[crc_ltt["study"].eq("ltt_optimistic_bounded_loss_design_only")]
    assert not ltt.empty
    assert ltt["risk_bound_mode"].eq("single_policy_tail_bound").all()
    assert ltt["nominal_tail_probability"].eq("0.1").all()
    assert set(ltt["per_policy_tail_probability"]) == {"0.01", "0.1"}
    assert counterexample.groupby("loan_id")["unit_miss"].nunique().eq(1).all()
    assert counterexample.groupby("lambda_index")["allocation"].sum().eq(1.0).all()
    assert counterexample.groupby("lambda_index")["portfolio_loss"].first().to_dict() == {
        0: 0.0,
        1: 1.0,
    }
    assert (
        counterexample["portfolio_loss_contribution"]
        .eq(counterexample["allocation"] * counterexample["unit_miss"])
        .all()
    )
    sets = counterexample.pivot(index="loan_id", columns="lambda_index", values="prediction_set")
    assert sets.loc["A", 0] == "{0}"
    assert sets.loc["A", 1] == "{0,1}"


def test_hoeffding_warning_radius_is_only_a_coarse_bug_detector() -> None:
    radius = math.sqrt(math.log(1_000.0) / (2.0 * 2_000.0))
    assert radius == pytest.approx(0.041556, abs=1.0e-6)
    assert 0.10 + radius == pytest.approx(0.141556, abs=1.0e-6)
