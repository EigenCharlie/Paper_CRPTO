from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from scripts.experiments import run_ijds_funded_selection_estimand_audit_v1 as runner


def test_environment_provenance_does_not_serialize_checkout_path() -> None:
    payload = runner._portable_environment(runner.ROOT)
    assert payload["absolute_paths_recorded"] is False
    assert set(payload["executable"]) == {"basename", "bytes", "sha256"}
    assert str(runner.ROOT.resolve()) not in str(payload)


def test_manifest_identity_omits_historical_machine_local_payloads() -> None:
    payload = {
        "schema_version": "v",
        "status": "complete",
        "run_tag": "run",
        "protocol_tag": "protocol/run",
        "protocol_commit": "a" * 40,
        "environment": {"executable": r"C:\\machine\\python.exe"},
        "absolute_path": r"C:\\protected",
    }
    identity = runner._manifest_identity(payload)
    assert set(identity) == set(runner.MANIFEST_IDENTITY_KEYS)
    assert "C:\\" not in str(identity)


def test_locked_config_loads_and_names_all_three_estimand_outputs() -> None:
    config = runner._load_config(runner.ROOT / runner.LOCKED_CONFIG_PATH)
    names = runner._validate_output_names(config)
    assert names["track_bounds"] == "track_three_estimand_funded_selection_bounds.parquet"
    assert (
        names["support_and_fixed_capital_reconciliation"]
        == "support_and_fixed_capital_v3_reconciliation.parquet"
    )
    assert config["interpretation"][
        "fixed_capital_decision_weighting_is_the_active_granularity_estimand"
    ]


def test_artifact_transport_contract_is_exact_relative_and_git_native() -> None:
    config = runner._load_config(runner.ROOT / runner.LOCKED_CONFIG_PATH)
    transport = runner._validate_artifact_transport(config)

    assert transport["artifact_tag"] == runner.ARTIFACT_TAG
    assert transport["artifact_commit_relationship"] == (
        "single_direct_child_of_protocol_commit"
    )
    assert transport["pending_at_runner_exit"] is True
    assert transport["dvc_required"] is False
    assert len(transport["exact_tracked_paths"]) == 7
    assert all(not Path(path).is_absolute() for path in transport["exact_tracked_paths"])
    assert str(runner.ROOT.resolve()) not in str(transport)


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
    config = copy.deepcopy(runner._load_config(runner.ROOT / runner.LOCKED_CONFIG_PATH))
    config["artifact_transport"][field] = value

    with pytest.raises(RuntimeError, match="artifact-transport identity"):
        runner._validate_artifact_transport(config)


def test_artifact_transport_rejects_absolute_tracked_path() -> None:
    config = copy.deepcopy(runner._load_config(runner.ROOT / runner.LOCKED_CONFIG_PATH))
    config["artifact_transport"]["exact_tracked_paths"][0] = "C:/machine/output.parquet"

    with pytest.raises(ValueError, match="unsafe"):
        runner._validate_artifact_transport(config)


def test_output_basename_rejects_traversal() -> None:
    config = runner._load_config(runner.ROOT / runner.LOCKED_CONFIG_PATH)
    unsafe = copy.deepcopy(config)
    unsafe["output"]["track_bounds"] = "../escaped.parquet"
    with pytest.raises(ValueError, match="safe"):
        runner._validate_output_names(unsafe)


def test_protected_path_is_hash_bound(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"registered")
    descriptor = {
        "path": "source.bin",
        "bytes": len(b"registered"),
        "sha256": hashlib.sha256(b"registered").hexdigest(),
    }
    assert (
        runner._verified_protected_path(descriptor, protected_read_root=tmp_path)
        == source.resolve()
    )
    source.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="mismatched"):
        runner._verified_protected_path(descriptor, protected_read_root=tmp_path)


def test_clean_tag_gate_precedes_any_protected_source_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("placeholder: true\n", encoding="utf-8")
    monkeypatch.setattr(
        runner,
        "_resolve_locked_config_path",
        lambda config_path, repo_root: config_path.resolve(),
    )
    monkeypatch.setattr(runner, "_load_config", lambda path: {})
    monkeypatch.setattr(runner, "_preflight_output_paths", lambda config, repo_root: None)

    def fail_gate(repo_root: Path, tag: str) -> str:
        raise RuntimeError("clean-tag-gate")

    def forbidden_read(config, *, protected_read_root):
        raise AssertionError("protected source was read before clean-tag gate")

    monkeypatch.setattr(runner, "require_clean_tagged_head", fail_gate)
    monkeypatch.setattr(runner, "_load_verified_sources", forbidden_read)
    with pytest.raises(RuntimeError, match="clean-tag-gate"):
        runner.run(
            config_path=config_path,
            protected_read_root=tmp_path,
            repo_root=tmp_path,
        )


def test_cli_requires_explicit_protected_read_root() -> None:
    with pytest.raises(SystemExit):
        runner.build_parser().parse_args([])
