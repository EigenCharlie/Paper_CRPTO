from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

import scripts.experiments.run_ijds_residual_transport_frontier as runner
from scripts.experiments.run_ijds_residual_transport_frontier import (
    DEFAULT_CONFIG_PATH,
    PROTOCOL_TAG,
    _load_config,
    _preflight_output_paths,
    _reconcile_temporal_reference,
    _validate_output_names,
    _verified_source,
)

ROOT = Path(__file__).resolve().parents[1]


def test_environment_provenance_does_not_serialize_checkout_path() -> None:
    payload = runner._portable_environment(ROOT)
    assert payload["absolute_paths_recorded"] is False
    assert set(payload["executable"]) == {"basename", "bytes", "sha256"}
    assert str(ROOT.resolve()) not in str(payload)


def test_canonical_residual_transport_config_locks_complete_grid_and_nonclaims() -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)

    assert config["protocol_tag"] == PROTOCOL_TAG
    assert config["design"]["expected_monthly_rows"] == 3000
    assert config["design"]["expected_pooled_rows"] == 200
    assert len(config["design"]["learners"]) == 5
    assert len(config["design"]["window_ids"]) == 8
    assert len(config["design"]["issue_months"]) == 15
    assert config["interpretation"]["directional_ks_is_descriptive_only"] is True
    assert config["interpretation"]["directional_ks_uses_exact_integer_cross_products"] is True
    assert config["interpretation"]["no_p_values_or_multiplicity_claim"] is True
    assert config["interpretation"]["no_two_origin_sensitivity"] is True
    assert (
        config["interpretation"][
            "directional_discrepancy_comparison_requires_strict_sharp_range_separation"
        ]
        is True
    )


def test_artifact_transport_contract_is_exact_relative_and_git_native() -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    transport = runner._validate_artifact_transport(config)

    assert transport["artifact_tag"] == runner.ARTIFACT_TAG
    assert transport["artifact_commit_relationship"] == (
        "single_direct_child_of_protocol_commit"
    )
    assert transport["pending_at_runner_exit"] is True
    assert transport["dvc_required"] is False
    assert len(transport["exact_tracked_paths"]) == 4
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
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    config["artifact_transport"][field] = value

    with pytest.raises(RuntimeError, match="artifact-transport identity"):
        runner._validate_artifact_transport(config)


def test_artifact_transport_rejects_absolute_tracked_path() -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    config["artifact_transport"]["exact_tracked_paths"][0] = "C:/machine/output.csv"

    with pytest.raises(ValueError, match="unsafe"):
        runner._validate_artifact_transport(config)


@pytest.mark.parametrize(
    ("key", "unsafe"),
    [
        ("monthly_table", "../monthly.csv"),
        ("pooled_table", "nested/pooled.csv"),
        ("summary", "summary.txt"),
        ("execution_receipt", ""),
    ],
)
def test_output_names_fail_closed(key: str, unsafe: str) -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    config["output"][key] = unsafe

    with pytest.raises(ValueError, match="safe"):
        _validate_output_names(config)


def test_preflight_does_not_create_output_directories(tmp_path: Path) -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))

    _preflight_output_paths(config, repo_root=tmp_path)

    assert not (tmp_path / config["output"]["data_root"] / config["run_tag"]).exists()
    assert not (tmp_path / config["output"]["model_root"] / config["run_tag"]).exists()


def test_exact_source_can_be_materialized_under_protected_read_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "clone"
    protected_root = tmp_path / "materialized"
    source = protected_root / "data/locked/source.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"exact protected bytes")
    descriptor = {
        "path": "data/locked/source.bin",
        "bytes": source.stat().st_size,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }

    path, role = _verified_source(
        descriptor,
        repo_root=repo_root,
        protected_read_root=protected_root,
        label="fixture",
    )

    assert path == source
    assert role == "protected_read_root"
    drifted = dict(descriptor)
    drifted["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="descriptor mismatch"):
        _verified_source(
            drifted,
            repo_root=repo_root,
            protected_read_root=protected_root,
            label="fixture",
        )


@pytest.mark.parametrize("unsafe_path", ["../escape.bin", "C:escape.bin", "/absolute.bin"])
def test_protected_source_rejects_descriptor_traversal(tmp_path: Path, unsafe_path: str) -> None:
    descriptor = {"path": unsafe_path, "bytes": 1, "sha256": "0" * 64}

    with pytest.raises(ValueError, match="unsafe"):
        _verified_source(
            descriptor,
            repo_root=tmp_path / "clone",
            protected_read_root=tmp_path / "materialized",
            label="fixture",
        )


def test_cli_accepts_protected_read_root() -> None:
    args = runner.parse_args(
        [
            "--config",
            str(DEFAULT_CONFIG_PATH),
            "--protected-read-root",
            "D:/locked-materialization",
        ]
    )

    assert args.config == DEFAULT_CONFIG_PATH
    assert args.protected_read_root == Path("D:/locked-materialization")


def test_run_enforces_clean_tag_before_opening_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    source_opened = False
    monkeypatch.setattr(
        runner, "_resolve_locked_config_path", lambda *_args, **_kwargs: ROOT / DEFAULT_CONFIG_PATH
    )
    monkeypatch.setattr(runner, "_load_config", lambda _path: config)
    monkeypatch.setattr(runner, "_preflight_output_paths", lambda *_args, **_kwargs: None)

    def fail_clean_gate(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("clean-tag gate")

    def mark_source_open(*_args: object, **_kwargs: object) -> object:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("sources must remain unopened")

    monkeypatch.setattr(runner, "require_clean_tagged_head", fail_clean_gate)
    monkeypatch.setattr(runner, "_load_verified_sources", mark_source_open)

    with pytest.raises(RuntimeError, match="clean-tag gate"):
        runner.run(config_path=ROOT / DEFAULT_CONFIG_PATH, repo_root=ROOT)
    assert source_opened is False


def test_final_gate_reverifies_all_sources_and_git(monkeypatch: pytest.MonkeyPatch) -> None:
    source_paths = {"source": Path("locked/source.bin")}
    materialization = {"source": "protected_read_root"}
    initial_git = {"commit": "abc", "dirty": False}
    calls = 0

    def verified_sources(*_args: object, **_kwargs: object):
        nonlocal calls
        calls += 1
        return source_paths, materialization, {}, {}, {}, {}

    monkeypatch.setattr(runner, "_load_verified_sources", verified_sources)
    monkeypatch.setattr(runner, "git_provenance", lambda _root: initial_git)
    runner._reverify_sources_and_git_before_write(
        {},
        repo_root=ROOT,
        protected_read_root=None,
        expected_paths=source_paths,
        expected_materialization=materialization,
        expected_git=initial_git,
    )
    assert calls == 1

    monkeypatch.setattr(
        runner,
        "git_provenance",
        lambda _root: {"commit": "def", "dirty": False},
    )
    with pytest.raises(RuntimeError, match="Git state changed"):
        runner._reverify_sources_and_git_before_write(
            {},
            repo_root=ROOT,
            protected_read_root=None,
            expected_paths=source_paths,
            expected_materialization=materialization,
            expected_git=initial_git,
        )


def _reference_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for group in range(5):
        rows.append(
            {
                "learner": "learner",
                "window_id": "window",
                "taxonomy_groups": 5,
                "conformal_group": group,
                "role": "primary_oot",
                "candidate_rows": 10 + group,
                "resolved_rows": 8 + group,
                "unresolved_rows": 2,
                "coverage_resolved": 0.80 + group / 100,
                "coverage_lower": 0.70 + group / 100,
                "coverage_upper": 0.90 + group / 100,
                "score_min": group / 10,
                "score_max": (group + 1) / 10,
                "fit_residual_quantile": 0.1 + group / 20,
                "fit_score_min": group / 11,
                "fit_score_max": (group + 1) / 11,
            }
        )
    temporal = pd.DataFrame(rows)
    return temporal, temporal.sample(frac=1.0, random_state=11).reset_index(drop=True)


def test_temporal_reference_reconciliation_is_keyed_not_positional() -> None:
    temporal, reference = _reference_pair()

    result = _reconcile_temporal_reference(
        temporal,
        reference,
        learners=("learner",),
        windows=("window",),
        role="primary_oot",
        taxonomy_groups=5,
    )

    assert result["rows"] == 5
    assert result["key_grid_exact"] is True
    assert max(result["maximum_absolute_differences"].values()) == 0.0
