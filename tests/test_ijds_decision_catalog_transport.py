from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.experiments.run_ijds_decision_catalog_transport_v1 as runner
from src.ijds_audit.decision_catalog_transport import (
    METRICS,
    DecisionCatalogSpec,
    build_decision_catalog_transport,
    exact_binary_set_types,
    finite_sample_rank,
    validate_decision_alignment,
    validate_outcome_free_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> tuple[pd.DataFrame, pd.DataFrame, DecisionCatalogSpec]:
    calibration_periods = ("d1", "d2")
    target_periods = ("t1", "t2")
    windows = ("w1", "w2")
    rulers = ("objective",)
    coordinates = (0.25,)
    gammas = (0.0, 1.0)
    blocks = [
        *(("development", period) for period in calibration_periods),
        *(("target", period) for period in target_periods),
    ]
    loan_specs = (
        # id, exposure, p, rate, lower, upper, outcome by role
        ("resolved_zero_set", 500.0, 0.20, 0.10, 0.0, 0.6),
        ("resolved_empty_set", 200.0, 0.30, 0.15, 0.2, 0.8),
        ("resolved_full_set", 200.0, 0.40, 0.20, 0.0, 1.0),
        ("unresolved_zero_set", 100.0, 0.10, 0.12, 0.0, 0.7),
    )
    rows: list[dict[str, object]] = []
    joined_rows: list[dict[str, object]] = []
    for role, period in blocks:
        for window in windows:
            for gamma in gammas:
                candidate_id = f"{role}-{period}-{window}-{gamma}"
                for loan_id, exposure, point, rate, lower, upper in loan_specs:
                    expected_rate = (1.0 - point) * rate - point * 0.45
                    record: dict[str, object] = {
                        "id": f"{period}-{loan_id}",
                        "issue_d": pd.Timestamp("2013-01-01"),
                        "design_split": role,
                        "pd_point": point,
                        "loan_amnt": exposure,
                        "purpose": "fixture",
                        "contractual_rate": rate,
                        "conformal_lower": lower,
                        "conformal_upper": upper,
                        "allocation_fraction": 1.0,
                        "exposure": exposure,
                        "weight": exposure / 1000.0,
                        "pd_effective": point,
                        "expected_payoff_rate": expected_rate,
                        "expected_payoff_contribution": exposure * expected_rate,
                        "window_id": window,
                        "role": role,
                        "period": period,
                        "policy_label": f"gamma_{gamma}",
                        "candidate_id": candidate_id,
                        "comparator_rule": "fixture",
                        "paired_policy_id": candidate_id,
                        "frontier_ruler": "objective",
                        "frontier_coordinate": 0.25,
                        "frontier_cap": 0.2,
                        "objective_target": 1.0,
                        "gamma": gamma,
                    }
                    rows.append(record)
                    endpoint = dict(record)
                    if loan_id == "unresolved_zero_set":
                        endpoint["snapshot_default"] = pd.NA
                        endpoint["snapshot_resolution"] = "nonterminal_or_unresolved_status"
                    else:
                        endpoint["snapshot_default"] = int(
                            role == "target" and loan_id == "resolved_zero_set"
                        )
                        endpoint["snapshot_resolution"] = (
                            "charged_off_by_reconstructed_cutoff"
                            if endpoint["snapshot_default"] == 1
                            else "fully_paid_by_reconstructed_cutoff"
                        )
                    joined_rows.append(endpoint)
    outcome_free = pd.DataFrame(rows)
    joined = pd.DataFrame(joined_rows)
    joined["snapshot_default"] = joined["snapshot_default"].astype("Int8")
    spec = DecisionCatalogSpec(
        budget=1000.0,
        budget_tolerance=1.0e-9,
        lgd=0.45,
        nominal_miscoverage=0.10,
        alpha=0.50,
        numeric_tolerance=1.0e-12,
        payoff_contribution_tolerance=1.0e-8,
        calibration_role="development",
        target_role="target",
        calibration_periods=calibration_periods,
        target_periods=target_periods,
        window_ids=windows,
        rulers=rulers,
        coordinates=coordinates,
        gamma_grid=gammas,
        expected_rank=2,
        expected_policies_per_block=4,
        expected_policy_rows=16,
        expected_allocation_rows=64,
        expected_set_type_counts={
            "empty": 16,
            "zero_only": 32,
            "one_only": 0,
            "both": 16,
        },
    )
    return outcome_free, joined, spec


def test_exact_endpoint_membership_does_not_round_near_zero() -> None:
    labels = exact_binary_set_types(
        pd.Series([0.0, 0.2, 1.0e-15, 0.0]),
        pd.Series([0.8, 0.8, 1.0, 1.0]),
    )

    assert labels.tolist() == ["zero_only", "empty", "one_only", "both"]


def test_complete_synthetic_catalog_has_exact_shared_completion_bounds() -> None:
    outcome_free, joined, spec = _fixture()

    result = build_decision_catalog_transport(outcome_free, joined, spec=spec)

    assert len(result.policy_score_bounds) == 16 * 3
    assert len(result.block_score_bounds) == 4 * 3
    assert len(result.calibration_thresholds) == 3
    assert len(result.target_classification) == 2 * 3
    assert set(result.policy_score_bounds["metric"]) == set(METRICS)
    assert result.target_classification["classification"].eq("definitely_exceeds").all()
    assert result.target_classification["exceeds_all_development_upper"].all()
    assert result.summary["ordering_reference"] == {
        "reported": False,
        "reason": (
            "one_over_choose_26_11_applies_to_one_prespecified_scalar_ranking_not_the_"
            "postinspection_intersection_of_three_metric_rankings"
        ),
        "p_value_reported": False,
    }

    policy = result.policy_score_bounds.loc[
        result.policy_score_bounds["role"].eq("target")
        & result.policy_score_bounds["period"].eq("t1")
        & result.policy_score_bounds["window_id"].eq("w1")
        & result.policy_score_bounds["gamma"].eq(0.0)
    ].set_index("metric")
    assert policy.loc["default_gap", "score_lower"] == pytest.approx(0.25)
    assert policy.loc["default_gap", "score_upper"] == pytest.approx(0.35)
    assert policy.loc["miscoverage_excess", "score_lower"] == pytest.approx(0.60)
    assert policy.loc["miscoverage_excess", "score_upper"] == pytest.approx(0.70)

    # Exhaust the one shared unresolved outcome.  The extrema equal the stored
    # all-zero/all-one endpoints for every metric, including the catalog max.
    for completion, endpoint in ((0, "lower"), (1, "upper")):
        completed = joined.copy()
        unresolved = completed["snapshot_default"].isna()
        completed.loc[unresolved, "snapshot_default"] = completion
        completed.loc[unresolved, "snapshot_resolution"] = (
            "charged_off_by_reconstructed_cutoff"
            if completion == 1
            else "fully_paid_by_reconstructed_cutoff"
        )
        completed["snapshot_default"] = completed["snapshot_default"].astype("Int8")
        completed_result = build_decision_catalog_transport(
            outcome_free,
            completed,
            spec=spec,
        )
        completed_policy = completed_result.policy_score_bounds.loc[
            completed_result.policy_score_bounds["role"].eq("target")
            & completed_result.policy_score_bounds["period"].eq("t1")
            & completed_result.policy_score_bounds["window_id"].eq("w1")
            & completed_result.policy_score_bounds["gamma"].eq(0.0)
        ].set_index("metric")
        for metric in METRICS:
            assert completed_policy.loc[metric, "score_lower"] == pytest.approx(
                policy.loc[metric, f"score_{endpoint}"]
            )
            assert completed_policy.loc[metric, "score_upper"] == pytest.approx(
                policy.loc[metric, f"score_{endpoint}"]
            )


def test_joint_three_metric_ordering_probability_is_never_reported() -> None:
    outcome_free, joined, spec = _fixture()
    target_default = joined["role"].eq("target") & joined["id"].str.endswith("resolved_zero_set")
    joined.loc[target_default, "snapshot_default"] = 0
    joined.loc[target_default, "snapshot_resolution"] = "fully_paid_by_reconstructed_cutoff"

    result = build_decision_catalog_transport(outcome_free, joined, spec=spec)
    reference = result.summary["ordering_reference"]
    assert reference["reported"] is False
    assert reference["p_value_reported"] is False


def test_alignment_is_keyed_and_row_order_invariant() -> None:
    outcome_free, joined, spec = _fixture()
    shuffled = joined.sample(frac=1.0, random_state=19).reset_index(drop=True)

    order = validate_decision_alignment(
        outcome_free,
        shuffled,
        numeric_tolerance=spec.numeric_tolerance,
    )
    result = build_decision_catalog_transport(outcome_free, shuffled, spec=spec)

    assert len(np.unique(order)) == len(joined)
    assert len(result.policy_score_bounds) == 48


def test_alignment_rejects_changed_frozen_decision() -> None:
    outcome_free, joined, spec = _fixture()
    joined.loc[0, "exposure"] += 1.0

    with pytest.raises(RuntimeError, match="exposure"):
        validate_decision_alignment(
            outcome_free,
            joined,
            numeric_tolerance=spec.numeric_tolerance,
        )


def test_repeated_loan_must_have_one_shared_endpoint_state() -> None:
    outcome_free, joined, spec = _fixture()
    repeated = joined["id"].eq("d1-resolved_zero_set")
    changed = joined.index[repeated][0]
    joined.loc[changed, "snapshot_default"] = 1
    joined.loc[changed, "snapshot_resolution"] = "charged_off_by_reconstructed_cutoff"

    with pytest.raises(RuntimeError, match="shared endpoint"):
        build_decision_catalog_transport(outcome_free, joined, spec=spec)


def test_outcome_free_leakage_fails_closed() -> None:
    outcome_free, _joined, spec = _fixture()
    outcome_free["snapshot_default"] = 0

    with pytest.raises(ValueError, match="leak"):
        validate_outcome_free_catalog(outcome_free, spec=spec)


@pytest.mark.parametrize(
    ("outcome", "resolution", "message"),
    [
        ("not-a-number", "fully_paid_by_reconstructed_cutoff", "not numeric"),
        (pd.NA, "fully_paid_by_reconstructed_cutoff", "disagrees"),
        (0, "charged_off_by_reconstructed_cutoff", "disagrees"),
        (1, "nonterminal_or_unresolved_status", "unresolved"),
        (pd.NA, "unknown_resolution", "taxonomy changed"),
    ],
)
def test_endpoint_value_and_resolution_taxonomy_fail_closed(
    outcome: object,
    resolution: str,
    message: str,
) -> None:
    outcome_free, joined, spec = _fixture()
    if isinstance(outcome, str):
        joined["snapshot_default"] = joined["snapshot_default"].astype(object)
    joined.loc[0, "snapshot_default"] = outcome
    joined.loc[0, "snapshot_resolution"] = resolution

    with pytest.raises((RuntimeError, ValueError), match=message):
        build_decision_catalog_transport(outcome_free, joined, spec=spec)


def test_one_only_set_fails_monotonicity_gate() -> None:
    outcome_free, _joined, spec = _fixture()
    outcome_free.loc[0, ["conformal_lower", "conformal_upper"]] = [0.2, 1.0]
    altered_counts = dict(spec.expected_set_type_counts)
    altered_counts["zero_only"] -= 1
    altered_counts["one_only"] += 1

    with pytest.raises(RuntimeError, match=r"\{1\}-only"):
        validate_outcome_free_catalog(
            outcome_free,
            spec=replace(spec, expected_set_type_counts=altered_counts),
        )


@pytest.mark.parametrize("failure", ["missing_cell", "duplicate_id", "budget"])
def test_catalog_integrity_failures_stop(failure: str) -> None:
    outcome_free, _joined, spec = _fixture()
    if failure == "missing_cell":
        mask = (
            outcome_free["role"].eq("development")
            & outcome_free["period"].eq("d1")
            & outcome_free["window_id"].eq("w1")
            & outcome_free["gamma"].eq(0.0)
        )
        changed = outcome_free.loc[~mask].copy()
        expected = replace(
            spec,
            expected_allocation_rows=len(changed),
            expected_set_type_counts={
                key: int(
                    (
                        exact_binary_set_types(
                            changed["conformal_lower"], changed["conformal_upper"]
                        )
                        == key
                    ).sum()
                )
                for key in spec.expected_set_type_counts
            },
        )
        message = "catalog"
    elif failure == "duplicate_id":
        changed = pd.concat([outcome_free, outcome_free.iloc[[0]]], ignore_index=True)
        counts = dict(spec.expected_set_type_counts)
        counts["zero_only"] += 1
        expected = replace(
            spec,
            expected_allocation_rows=len(changed),
            expected_set_type_counts=counts,
        )
        message = "duplicate"
    else:
        changed = outcome_free.copy()
        changed.loc[0, "exposure"] += 1.0
        expected = spec
        message = "budget"

    with pytest.raises(RuntimeError, match=message):
        validate_outcome_free_catalog(changed, spec=expected)


def test_rank_and_three_way_boundary_conventions() -> None:
    assert finite_sample_rank(11, alpha=0.10) == 11
    with pytest.raises(ValueError, match="positive integer"):
        finite_sample_rank(0, alpha=0.10)


def test_canonical_config_is_locked_and_explicit() -> None:
    config = runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH)

    assert config["protocol_tag"] == runner.PROTOCOL_TAG
    assert config["design"]["expected_policy_metric_rows"] == 18_720
    assert config["design"]["expected_rank"] == 11
    assert config["post_inspection_disclosure"]["preregistered"] is False
    assert config["claim_boundary"]["active_claim"] is False


def test_artifact_transport_contract_is_exact_relative_and_git_native() -> None:
    config = runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH)
    transport = runner._validate_artifact_transport(config)

    assert transport["artifact_tag"] == runner.ARTIFACT_TAG
    assert transport["artifact_commit_relationship"] == ("single_direct_child_of_protocol_commit")
    assert transport["pending_at_runner_exit"] is True
    assert transport["dvc_required"] is False
    assert len(transport["exact_tracked_paths"]) == 6
    assert all(not Path(path).is_absolute() for path in transport["exact_tracked_paths"])
    assert str(ROOT.resolve()) not in str(transport)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_tag", "artifacts/wrong"),
        ("artifact_commit_relationship", "not_a_direct_child"),
        ("pending_at_runner_exit", False),
        ("dvc_required", True),
        ("exact_tracked_paths", ["models/unrelated.json"]),
    ],
)
def test_artifact_transport_drift_fails_closed(field: str, value: object) -> None:
    config = deepcopy(runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH))
    config["artifact_transport"][field] = value

    with pytest.raises(RuntimeError, match="artifact-transport identity"):
        runner._validate_artifact_transport(config)


def test_artifact_transport_rejects_absolute_tracked_path() -> None:
    config = deepcopy(runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH))
    config["artifact_transport"]["exact_tracked_paths"][0] = "C:/machine/output.csv"

    with pytest.raises(ValueError, match="unsafe"):
        runner._validate_artifact_transport(config)


def test_runner_rejects_unsafe_output_name_and_preflight_does_not_create(
    tmp_path: Path,
) -> None:
    config = runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH)
    unsafe = deepcopy(config)
    unsafe["output"]["policy_score_bounds"] = "../policy_score_bounds.csv"
    with pytest.raises(ValueError, match="safe"):
        runner._validate_output_names(unsafe)

    runner._preflight_output_paths(config, repo_root=tmp_path)
    assert not (tmp_path / config["output"]["data_root"] / runner.RUN_TAG).exists()
    assert not (tmp_path / config["output"]["model_root"] / runner.RUN_TAG).exists()


def test_protected_source_hash_and_byte_drift_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"pinned synthetic bytes")
    byte_count = source.stat().st_size
    descriptor = {
        "path": "source.bin",
        "bytes": byte_count,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    assert runner._verified_path(descriptor, protected_root=tmp_path) == source

    drifted = dict(descriptor)
    drifted["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="sha256"):
        runner._verified_path(drifted, protected_root=tmp_path)
    drifted = dict(descriptor)
    drifted["bytes"] = byte_count + 1
    with pytest.raises(RuntimeError, match="byte"):
        runner._verified_path(drifted, protected_root=tmp_path)


def test_protected_read_root_must_be_explicit_and_separate(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        runner.parse_args([])
    with pytest.raises(ValueError, match="separate"):
        runner._protected_root(tmp_path, repo_root=tmp_path)
    disclosure = runner._protected_read_disclosure(tmp_path.resolve())
    assert str(tmp_path.resolve()) not in str(disclosure)
    assert disclosure == {
        "protected_read_root_supplied": True,
        "protected_read_root_separate_from_execution_checkout": True,
        "absolute_materialization_paths_recorded": False,
    }


def test_environment_provenance_does_not_serialize_checkout_path() -> None:
    payload = runner._portable_environment(ROOT)
    assert payload["absolute_paths_recorded"] is False
    assert set(payload["executable"]) == {"basename", "bytes", "sha256"}
    assert str(ROOT.resolve()) not in str(payload)


def test_run_checks_clean_tag_before_opening_protected_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = runner._load_config(ROOT / runner.DEFAULT_CONFIG_PATH)
    source_opened = False
    monkeypatch.setattr(
        runner,
        "_resolve_locked_config_path",
        lambda *_args, **_kwargs: ROOT / runner.DEFAULT_CONFIG_PATH,
    )
    monkeypatch.setattr(runner, "_load_config", lambda _path: config)
    monkeypatch.setattr(runner, "_preflight_output_paths", lambda *_args, **_kwargs: None)

    def fail_clean_gate(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("clean-tag gate")

    def mark_source_open(*_args: object, **_kwargs: object) -> object:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("protected sources must remain unopened")

    monkeypatch.setattr(runner, "require_clean_tagged_head", fail_clean_gate)
    monkeypatch.setattr(runner, "_load_verified_sources", mark_source_open)

    with pytest.raises(RuntimeError, match="clean-tag gate"):
        runner.run(
            config_path=ROOT / runner.DEFAULT_CONFIG_PATH,
            protected_read_root=tmp_path,
            repo_root=ROOT,
        )
    assert source_opened is False
