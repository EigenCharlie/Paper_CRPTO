from __future__ import annotations

import copy
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.experiments import run_ijds_set_native_binary_robust_counterpart_v1 as runner
from src.ijds_audit.config import load_v4_config
from src.ijds_challengers.set_native_binary_robust import (
    COORDINATES,
    RULERS,
    SetNativeCell,
    binary_set_risk_score,
    cell_from_shard_frame,
    cell_to_shard_frame,
    load_set_native_config,
    shard_relative_path,
    taxonomy_diagnostic,
    validate_phase_a_metadata,
)

ROOT = Path(__file__).resolve().parents[1]
PHASE_A_CONFIG = (
    ROOT / "configs/experiments/ijds_set_native_binary_robust_counterpart_2026-07-31_v1.yaml"
)
PHASE_B_CONFIG = (
    ROOT / "configs/experiments/"
    "ijds_set_native_binary_robust_counterpart_2026-07-31_v1_phase_b_blocked.yaml"
)
PROTOCOL = (
    ROOT / "docs/research/ijds_set_native_binary_robust_counterpart_v1_protocol_2026-07-31.md"
)


def test_phase_a_locks_exact_8x26x2x3_grid_without_gamma() -> None:
    config = load_set_native_config(PHASE_A_CONFIG)
    census = config["expected_census"]
    if census["phase_a_cells"] != 8 * 26 * 2 * 3 or census["phase_a_cells"] != 1248:
        pytest.fail("Phase A no longer locks the exact 8x26x2x3 census.")
    if tuple(config["frontier"]["rulers"]) != RULERS:
        pytest.fail("The two outcome-blind rulers changed.")
    if tuple(config["frontier"]["coordinate_grid"]) != COORDINATES:
        pytest.fail("The three frontier coordinates changed.")
    if "gamma" in config["frontier"]:
        pytest.fail("Set-native Phase A reintroduced a continuous embedding gamma.")


def test_binary_set_score_maps_only_singleton_zero_to_zero() -> None:
    lower = np.array([0.2, 0.0, 0.2, 0.0])
    upper = np.array([0.8, 0.8, 1.0, 1.0])
    taxonomy, risk = binary_set_risk_score(lower, upper)
    if taxonomy.tolist() != ["empty", "singleton_zero", "singleton_one", "two_label"]:
        pytest.fail(f"Unexpected exact binary-set taxonomy: {taxonomy.tolist()}.")
    np.testing.assert_array_equal(risk, np.array([1.0, 0.0, 1.0, 1.0]))
    diagnostic = taxonomy_diagnostic(
        taxonomy,
        risk,
        window_id="w01",
        role="primary_oot",
        period="2016-04",
    )
    if diagnostic["n_risk_zero"] != 1 or diagnostic["empty_set_score"] != 1.0:
        pytest.fail("The fail-closed empty-set convention is not explicit in diagnostics.")


@pytest.mark.parametrize(
    ("lower", "upper"),
    [
        ([0.0], [np.nan]),
        ([-0.1], [0.5]),
        ([0.1], [1.1]),
        ([0.8], [0.2]),
        ([0.0, 0.1], [1.0]),
    ],
)
def test_binary_set_score_rejects_invalid_interval_authority(
    lower: list[float], upper: list[float]
) -> None:
    with pytest.raises(ValueError, match="aligned ordered values"):
        binary_set_risk_score(lower, upper)


def test_v4_loader_resolves_inherited_usd_one_million_budget() -> None:
    visible = ROOT / "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-12.yaml"
    text = visible.read_text(encoding="utf-8")
    if "extends:" not in text or "budget:" in text:
        pytest.fail("The test no longer exercises inherited V4 policy authority.")
    resolved = load_v4_config(visible)
    if float(resolved["policy"]["budget"]) != 1_000_000.0:
        pytest.fail("load_v4_config did not resolve the inherited USD 1m budget.")
    source = inspect.getsource(runner.run_phase_a)
    if "load_v4_config(parent_config_path)" not in source:
        pytest.fail("Phase A bypasses recursive V4 config resolution.")


def _synthetic_cell() -> SetNativeCell:
    allocation = pd.DataFrame(
        {
            "id": pd.Series(["a", "b"], dtype="string"),
            "role": pd.Series(["primary_oot", "primary_oot"], dtype="str"),
            "period": pd.Series(["2016-04", "2016-04"], dtype="str"),
            "policy_label": pd.Series(["set_native_normalized_score_c025"] * 2, dtype="str"),
            "exposure": pd.Series([400_000.0, 600_000.0], dtype="float64"),
        }
    )
    record = {
        "window_id": "w01_2012m01_m06",
        "role": "primary_oot",
        "period": "2016-04",
        "frontier_ruler": "normalized_score",
        "frontier_coordinate": 0.25,
        "total_allocated": 1_000_000.0,
        "budget_residual": 0.0,
    }
    audit = {
        "window_id": "w01_2012m01_m06",
        "role": "primary_oot",
        "period": "2016-04",
        "ruler": "normalized_score",
        "coordinate": 0.25,
    }
    taxonomy = {
        "window_id": "w01_2012m01_m06",
        "role": "primary_oot",
        "period": "2016-04",
        "n_candidates": 2,
    }
    return SetNativeCell(record=record, allocations=allocation, audit=audit, taxonomy=taxonomy)


def test_atomic_shard_roundtrip_is_self_contained_and_canonical() -> None:
    cell = _synthetic_cell()
    shard = cell_to_shard_frame(cell)
    decoded = cell_from_shard_frame(shard)
    if decoded.identity != cell.identity or not decoded.allocations.equals(cell.allocations):
        pytest.fail("Atomic shard did not preserve its exact cell and allocation.")
    expected = Path("w01_2012m01_m06/primary_oot/2016-04/normalized_score_c025.parquet")
    if shard_relative_path(decoded) != expected:
        pytest.fail("Atomic shard path no longer derives only from cell identity.")


def test_atomic_shard_rejects_conflicting_repeated_metadata() -> None:
    shard = cell_to_shard_frame(_synthetic_cell())
    shard.loc[1, "__record__window_id"] = "conflict"
    with pytest.raises(RuntimeError, match="conflicting record field"):
        cell_from_shard_frame(shard)


def test_runtime_checkpoint_root_is_external_and_never_a_worktree_tmp(tmp_path: Path) -> None:
    config = load_set_native_config(PHASE_A_CONFIG)
    external = runner._checkpoint_root(config, ROOT, runtime_root=tmp_path)
    if external.is_relative_to(ROOT.resolve()):
        pytest.fail("Runtime checkpoint root remained inside the worktree.")
    if external.parent != tmp_path.resolve() or external.name != config["run_tag"]:
        pytest.fail("Explicit runtime root did not receive one safe run-tag child.")
    with pytest.raises(ValueError, match="outside repository"):
        runner._checkpoint_root(config, ROOT, runtime_root=ROOT / "tmp/forbidden-runtime")


def _complete_metadata() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, object]] = []
    audits: list[dict[str, object]] = []
    taxonomy: list[dict[str, object]] = []
    periods = (
        [f"2013-{month:02d}" for month in range(2, 13)]
        + [f"2016-{month:02d}" for month in range(4, 13)]
        + [f"2017-{month:02d}" for month in range(1, 7)]
    )
    roles = ["policy_development"] * 11 + ["primary_oot"] * 15
    for window in range(1, 9):
        window_id = f"w{window:02d}"
        for period, role in zip(periods, roles, strict=True):
            taxonomy.append(
                {
                    "window_id": window_id,
                    "role": role,
                    "period": period,
                    "n_candidates": 1,
                }
            )
            for ruler in RULERS:
                for coordinate in COORDINATES:
                    records.append(
                        {
                            "window_id": window_id,
                            "role": role,
                            "period": period,
                            "frontier_ruler": ruler,
                            "frontier_coordinate": coordinate,
                            "budget_residual": 0.0,
                        }
                    )
                    audits.append(
                        {
                            "window_id": window_id,
                            "role": role,
                            "period": period,
                            "ruler": ruler,
                            "coordinate": coordinate,
                        }
                    )
    return pd.DataFrame(records), pd.DataFrame(audits), pd.DataFrame(taxonomy)


def test_terminal_metadata_requires_all_1248_cells() -> None:
    config = load_set_native_config(PHASE_A_CONFIG)
    records, audits, taxonomy = _complete_metadata()
    validate_phase_a_metadata(records, audits, taxonomy, config=config)
    with pytest.raises(RuntimeError, match="cell census"):
        validate_phase_a_metadata(records.iloc[:-1], audits, taxonomy, config=config)


def test_phase_b_template_stops_before_any_outcome_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Blocked Phase B reached the outcome loader.")

    monkeypatch.setattr(runner, "load_outcome_universe", forbidden)
    with pytest.raises(RuntimeError, match="Phase B is blocked"):
        runner.run_phase_b(config_path=PHASE_B_CONFIG, repo_root=ROOT)


def test_phase_b_ready_status_requires_all_exact_hashes(tmp_path: Path) -> None:
    payload = runner.load_phase_b_config(PHASE_B_CONFIG)
    mutated = copy.deepcopy(payload)
    mutated["protocol_status"] = "locked_hash_pinned_phase_b_before_outcomes"
    mutated["schema_version"] = "2026-07-31.v1.phase-b.1"
    path = tmp_path / "ready-without-hashes.yaml"
    import yaml

    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="requires path, bytes, and sha256"):
        runner.load_phase_b_config(path)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update({"unexpected": True}), "top-level"),
        (lambda value: value.update({"run_tag": "changed"}), "identity"),
        (
            lambda value: value["source_v1d"].update({"artifact_tag": "changed"}),
            "V1d source",
        ),
        (
            lambda value: value["endpoint_source"]["config"].update({"bytes": 1}),
            "Endpoint V5",
        ),
        (
            lambda value: value["claim_boundary"].update({"no_policy_winner": False}),
            "claim boundary",
        ),
        (
            lambda value: value["output"].update({"immutability": "overwrite"}),
            "output contract",
        ),
    ],
)
def test_phase_b_template_rejects_authority_drift(
    tmp_path: Path,
    mutator: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    payload = runner.load_phase_b_config(PHASE_B_CONFIG)
    mutated = copy.deepcopy(payload)
    mutator(mutated)
    path = tmp_path / "mutated-phase-b.yaml"
    import yaml

    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        runner.load_phase_b_config(path)


def test_protocol_forbids_joint_coverage_and_probabilistic_robustness_inheritance() -> None:
    text = PROTOCOL.read_text(encoding="utf-8").casefold()
    if "cartesian product" not in text or "joint coverage" not in text:
        pytest.fail("Protocol omits the marginal-to-joint coverage boundary.")
    if "does not inherit a probabilistic robust-optimization guarantee" not in text:
        pytest.fail("Protocol overstates probabilistic robustness of the counterpart.")
    config = load_set_native_config(PHASE_A_CONFIG)
    boundary = config["claim_boundary"]
    if not boundary["no_joint_coverage_for_cartesian_product_of_marginal_sets"]:
        pytest.fail("Config permits a joint-coverage inference.")
    if not boundary["no_probabilistic_robustness_guarantee"]:
        pytest.fail("Config permits a probabilistic robustness inference.")
