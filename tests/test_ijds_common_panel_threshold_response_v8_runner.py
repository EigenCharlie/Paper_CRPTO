from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
import yaml

import scripts.experiments.run_ijds_common_panel_threshold_response_v8 as runner
from scripts.experiments.run_ijds_common_panel_threshold_response_v8 import (
    DEFAULT_CONFIG_PATH,
    _load_config,
    _preflight_output_paths,
    _reconcile_temporal_reference,
    _validate_output_names,
)

ROOT = Path(__file__).resolve().parents[1]
V8_MODEL_DIR = (
    ROOT / "models/experiments/ijds_audit/ijds-common-panel-threshold-response-2026-07-26-v8"
)
V8_DATA_DIR = (
    ROOT
    / "data/processed/experiments/ijds_audit/ijds-common-panel-threshold-response-2026-07-26-v8"
)
PUBLICATION_TARGETS = ROOT / "configs/crpto_publication_targets.yaml"


def test_canonical_v8_config_is_complete_and_locked() -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)

    assert config["design"]["expected_stratum_pairs"] == 175
    assert config["design"]["expected_learner_pairs"] == 35
    assert config["interpretation"]["preregistered"] is False
    assert config["interpretation"]["no_ranking_or_selection"] is True
    assert config["interpretation"]["v7_outputs_already_inspected"] is True
    assert config["interpretation"]["protected_raw_archive_read_only"] is True
    assert config["interpretation"]["sharpness_is_cellwise_not_joint"] is True


def test_completed_v8_replay_is_clean_truthful_and_scientifically_identical_to_v7() -> None:
    summary = json.loads(
        (V8_MODEL_DIR / "common_panel_threshold_response_v8_summary.json").read_text(
            encoding="utf-8"
        )
    )
    receipt = json.loads((V8_MODEL_DIR / "execution_receipt.json").read_text(encoding="utf-8"))
    expected_commit = "06a7d864776247fbb5128105deb229de4476be65"
    expected_tag = "protocol/ijds-common-panel-threshold-response-2026-07-26-v8"
    raw_descriptor = summary["source_artifacts"]["raw_archive"]

    assert summary["status"] == "complete_clean_tagged_common_panel_threshold_response_v8"
    assert receipt["status"] == "complete_clean_tagged_common_panel_threshold_response_v8_receipt"
    assert summary["protocol_commit"] == receipt["protocol_commit"] == expected_commit
    assert summary["protocol_tag"] == receipt["protocol_tag"] == expected_tag
    assert (
        summary["initial_git"]
        == receipt["initial_git"]
        == {
            "commit": expected_commit,
            "dirty": False,
            "dirty_entries": 0,
            "dirty_paths": [],
        }
    )
    assert receipt["final_git"] == summary["initial_git"]
    assert summary["protected_artifacts_read"] == [raw_descriptor]
    assert receipt["protected_artifacts_read"] == [raw_descriptor]
    assert summary["protected_artifacts_written"] == receipt["protected_artifacts_written"] == []

    publication_targets = yaml.safe_load(PUBLICATION_TARGETS.read_text(encoding="utf-8"))
    frozen_v7_hashes = publication_targets["superseded_common_panel_protocol_capsule"][
        "frozen_v7_artifact_sha256"
    ]
    assert set(frozen_v7_hashes) == {
        "adjacent_stratum_threshold_response.csv",
        "adjacent_learner_threshold_response.csv",
    }
    for filename, v7_sha256 in frozen_v7_hashes.items():
        v8_bytes = (V8_DATA_DIR / filename).read_bytes()
        assert hashlib.sha256(v8_bytes).hexdigest() == v7_sha256


@pytest.mark.parametrize(
    ("key", "unsafe"),
    [
        ("stratum_table", "../response.csv"),
        ("learner_table", "nested/response.csv"),
        ("summary", "summary.txt"),
        ("execution_receipt", ""),
    ],
)
def test_v8_output_names_fail_closed_before_directory_creation(key: str, unsafe: str) -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    config = deepcopy(config)
    config["output"][key] = unsafe

    with pytest.raises(ValueError, match="safe"):
        _validate_output_names(config)


def test_v8_output_names_reject_casefold_aliases() -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    config["output"]["learner_table"] = config["output"]["stratum_table"].upper()

    with pytest.raises(ValueError, match="alias"):
        _validate_output_names(config)


def test_v8_preflight_does_not_create_output_directories(tmp_path: Path) -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    data_dir = tmp_path / config["output"]["data_root"] / config["run_tag"]
    model_dir = tmp_path / config["output"]["model_root"] / config["run_tag"]

    _preflight_output_paths(config, repo_root=tmp_path)

    assert not data_dir.exists()
    assert not model_dir.exists()


def test_v8_run_enforces_clean_tag_before_opening_sources(
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


def test_v8_source_and_nested_descriptors_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("bound bytes", encoding="utf-8")
    descriptor = {
        "path": "source.txt",
        "bytes": source.stat().st_size,
        "sha256": runner.relative_artifact_descriptor(source, repo_root=tmp_path)["sha256"],
    }

    assert runner._verified_path(descriptor, repo_root=tmp_path) == source
    drifted = dict(descriptor)
    drifted["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="sha256"):
        runner._verified_path(drifted, repo_root=tmp_path)
    with pytest.raises(RuntimeError, match="nested descriptor"):
        runner._require_same_descriptor(
            {**descriptor, "bytes": descriptor["bytes"] + 1},
            descriptor,
            label="fixture",
        )


def _reference_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
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
    reference = temporal.sample(frac=1.0, random_state=7).reset_index(drop=True)
    return temporal, reference


def test_temporal_reference_reconciliation_is_keyed_not_row_positional() -> None:
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


@pytest.mark.parametrize("field", ["candidate_rows", "coverage_upper"])
def test_temporal_reference_reconciliation_fails_on_numeric_drift(field: str) -> None:
    temporal, reference = _reference_pair()
    reference.loc[0, field] += 1

    with pytest.raises(RuntimeError, match=field):
        _reconcile_temporal_reference(
            temporal,
            reference,
            learners=("learner",),
            windows=("window",),
            role="primary_oot",
            taxonomy_groups=5,
        )
