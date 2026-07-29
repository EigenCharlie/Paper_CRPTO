from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml
from dvc_data.hashfile.hash_info import HashInfo
from dvc_data.hashfile.meta import Meta
from dvc_data.hashfile.tree import Tree

import scripts.experiments.run_ijds_set_preserving_embedding_sensitivity_v1 as runner_module
import src.ijds_challengers.set_preserving_embedding as embedding_module
from scripts.experiments.run_ijds_set_preserving_embedding_sensitivity_v1 import (
    EVALUATION_STATUS,
    FREEZE_STATUS,
    IMPLEMENTATION_PATHS,
    PHASE_A_ARTIFACT_KEYS,
    PHASE_B_TRANSPORT_STATUS,
    RUNNER_PATH,
    TRANSITIVE_PYTHON_PATHS,
    TRANSPORT_RECEIPT_PATH,
    TRANSPORT_SCHEMA_VERSION,
    UV_LOCK_PATH,
    _candidate_identity_contract,
    _canonical_json_bytes,
    _directory_content_descriptor,
    _evaluation_summary,
    _phase_b_transport_receipt_path,
    _require_phase_a_artifact_transport,
    _require_tagged_ancestor,
    _require_v2_implementation_equals_v1,
    _require_v2_is_v1_plus_pin,
    _resolve_strict_tag,
    _verified_phase_a_materialization,
    _verify_phase_a_transport_receipt,
    parse_args,
    prepare_output_paths,
    run_evaluation,
    run_outcome_free,
    verify_phase_a_clean_clone_transport,
    verify_phase_b_clean_clone_transport,
)
from src.ijds_challengers.normalized_frontier import (
    _is_minimum_endpoint_boundary_failure,
)
from src.ijds_challengers.set_preserving_embedding import (
    CONTRAST_GAMMA,
    CONTRAST_THETA,
    GAMMA_GRID,
    THETA_GRID,
    SetPreservingFrontierBuild,
    build_sharp_embedding_contrasts,
    common_25_score_objective_lower,
    embedding_diagnostics,
    load_set_preserving_config,
    metric_direction_census,
    policy_label,
    retain_primary_decision_inputs,
    set_preserving_upper,
    validate_complete_evaluation,
    validate_complete_frontier,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1a.yaml"


def test_config_locks_complete_grid_and_both_contrast_families() -> None:
    config = load_set_preserving_config(CONFIG)

    observed = (
        tuple(config["embedding"]["theta_grid"]),
        tuple(config["frontier"]["gamma_grid"]),
        config["expected_census"]["frontier_solves"],
        config["expected_census"]["order_replays"],
        config["expected_census"]["independent_solver_cells"],
        config["contrasts"]["families"],
        all(config["claim_boundary"].values()),
    )
    expected = (
        THETA_GRID,
        GAMMA_GRID,
        31_200,
        18_000,
        3_600,
        [CONTRAST_GAMMA, CONTRAST_THETA],
        True,
    )
    if observed != expected:
        pytest.fail(f"Locked embedding configuration changed: {observed!r}.")


def test_config_rejects_directory_components_in_output_names(tmp_path: Path) -> None:
    invalid = CONFIG.read_text(encoding="utf-8").replace(
        'allocations: "frontier_funded_allocations.parquet"',
        'allocations: "../frontier_funded_allocations.parquet"',
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="directory component"):
        load_set_preserving_config(path)


def test_config_rejects_disabled_no_selection_boundary(tmp_path: Path) -> None:
    invalid = CONFIG.read_text(encoding="utf-8").replace(
        "no_theta_selection: true", "no_theta_selection: false"
    )
    path = tmp_path / "invalid.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="no-selection"):
        load_set_preserving_config(path)


def test_config_rejects_solver_capital_rate_renormalization(tmp_path: Path) -> None:
    invalid = CONFIG.read_text(encoding="utf-8").replace(
        'solver_allocated_capital_renormalization: "forbidden"',
        'solver_allocated_capital_renormalization: "allowed"',
    )
    path = tmp_path / "invalid-normalization.yaml"
    path.write_text(invalid, encoding="utf-8")

    with pytest.raises(ValueError, match="common-capital"):
        load_set_preserving_config(path)


def test_v1_cannot_self_authorize_outcome_evaluation() -> None:
    with pytest.raises(RuntimeError, match="V1 cannot authorize outcomes"):
        run_evaluation(config_path=CONFIG, repo_root=ROOT)


def test_hash_pinned_evaluation_config_requires_complete_source_authority(
    tmp_path: Path,
) -> None:
    source = """source_frontier:
  run_tag: "source-v1"
  protocol_tag: "protocol/source-v1"
  protocol_commit: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  artifact_tag: "artifacts/source-v1"
  artifact_commit: "dddddddddddddddddddddddddddddddddddddddd"
  dvc_pointers:
    data:
      path: "data/processed/experiments/ijds_audit/source-v1.dvc"
      bytes: 100
      sha256: "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    model:
      path: "models/experiments/ijds_audit/source-v1.dvc"
      bytes: 100
      sha256: "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
  clean_clone_transport_receipt:
    path: "reports/crpto/ijds_set_preserving_embedding_sensitivity_2026-07-29_v1a_clean_clone_transport_receipt.json"
    bytes: 100
    sha256: "9999999999999999999999999999999999999999999999999999999999999999"
  config:
    path: "configs/experiments/source-v1.yaml"
    bytes: 456
    sha256: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  freeze:
    path: "models/source-v1/protocol_freeze.json"
    bytes: 123
    sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
"""
    valid = CONFIG.read_text(encoding="utf-8").replace(
        'protocol_status: "locked_candidate_two_phase_before_execution"',
        'protocol_status: "locked_hash_pinned_postfreeze_evaluation"',
    )
    valid = valid.replace(
        'run_tag: "ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a"',
        'run_tag: "evaluation-v2"\n' + source.rstrip(),
    )
    valid_path = tmp_path / "valid-v2.yaml"
    valid_path.write_text(valid, encoding="utf-8")
    loaded = load_set_preserving_config(valid_path)
    if loaded["source_frontier"]["freeze"]["bytes"] != 123:
        pytest.fail("Hash-pinned evaluation authority was not retained exactly.")

    missing = valid.replace(source.rstrip() + "\n", "")
    missing_path = tmp_path / "missing-source-v2.yaml"
    missing_path.write_text(missing, encoding="utf-8")
    with pytest.raises(ValueError, match="requires a committed source_frontier"):
        load_set_preserving_config(missing_path)


def test_v2_may_change_only_administrative_identity_and_source_pin() -> None:
    source = load_set_preserving_config(CONFIG)
    evaluation = copy.deepcopy(source)
    evaluation.update(
        {
            "schema_version": "2026-07-26.2",
            "protocol_status": "locked_hash_pinned_postfreeze_evaluation",
            "protocol_tag": "protocol/evaluation-v2",
            "run_tag": "evaluation-v2",
            "source_frontier": {"pinned": True},
        }
    )
    _require_v2_is_v1_plus_pin(evaluation, source)

    endpoint_drift = copy.deepcopy(evaluation)
    endpoint_drift["outcomes"]["parent_config"] = str(source["parent"]["config"])
    with pytest.raises(RuntimeError, match="canonically identical"):
        _require_v2_is_v1_plus_pin(endpoint_drift, source)

    tolerance_drift = copy.deepcopy(evaluation)
    tolerance_drift["contrasts"]["rate_negative_control_tolerance"] = 1.0
    with pytest.raises(RuntimeError, match="canonically identical"):
        _require_v2_is_v1_plus_pin(tolerance_drift, source)


def test_candidate_identity_contract_is_order_invariant_but_id_exact() -> None:
    candidates = pd.DataFrame(
        {
            "id": ["3", "1", "2"],
            "role": ["primary_oot", "policy_development", "primary_oot"],
            "period": ["2016-05", "2015-04", "2016-04"],
        }
    )
    expected = _candidate_identity_contract(candidates)
    observed = _candidate_identity_contract(candidates.iloc[::-1].reset_index(drop=True))
    if observed != expected:
        pytest.fail("Candidate fingerprint depends on input row order.")

    swapped = candidates.copy()
    swapped.loc[0, "id"] = "4"
    if _candidate_identity_contract(swapped) == expected:
        pytest.fail("Candidate fingerprint accepted an ID swap with unchanged counts.")
    with pytest.raises(RuntimeError, match="duplicate loan IDs"):
        _candidate_identity_contract(pd.concat([candidates, candidates.iloc[[0]]]))


def test_strict_tag_resolution_accepts_only_actual_tag_refs() -> None:
    parent_tag = "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    expected = "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd"
    if _resolve_strict_tag(ROOT, parent_tag) != expected:
        pytest.fail("Strict tag resolution changed for the verified parent tag.")
    for revision_expression in (
        "HEAD",
        "--all",
        expected,
        "codex/full-conformal-audit-remediation",
    ):
        with pytest.raises(RuntimeError):
            _resolve_strict_tag(ROOT, revision_expression)


def test_historical_v1_config_is_retained_byte_for_byte() -> None:
    relative = "configs/experiments/ijds_set_preserving_embedding_sensitivity_2026-07-26_v1.yaml"
    historical = subprocess.run(
        [
            "git",
            "show",
            "protocol/ijds-set-preserving-embedding-sensitivity-2026-07-26-v1:" + relative,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if (ROOT / relative).read_bytes() != historical:
        pytest.fail("The stopped V1 config was not retained byte-for-byte.")


def test_strict_tag_resolution_rejects_lightweight_tags(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "root",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "tag", "lightweight"], cwd=tmp_path, check=True)
    with pytest.raises(RuntimeError, match="must be annotated"):
        _resolve_strict_tag(tmp_path, "lightweight")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "tag",
            "-a",
            "annotated",
            "-m",
            "authority",
        ],
        cwd=tmp_path,
        check=True,
    )
    if _resolve_strict_tag(tmp_path, "annotated") != commit:
        pytest.fail("Annotated tag did not resolve to its peeled commit.")


def test_source_tag_must_be_an_ancestor_of_evaluation_head() -> None:
    parent_tag = "protocol/ijds-binary-geometry-frontier-v4-2026-07-12-v1"
    parent_commit = "2f8a7606e4eb65aa3ae3701fb3af8d9a51c953cd"
    head = _resolve_strict_tag(ROOT, parent_tag)
    _require_tagged_ancestor(
        source_tag=parent_tag,
        source_commit=parent_commit,
        evaluation_commit=head,
        root=ROOT,
    )
    with pytest.raises(RuntimeError, match="no longer resolves"):
        _require_tagged_ancestor(
            source_tag=parent_tag,
            source_commit="0" * 40,
            evaluation_commit=head,
            root=ROOT,
        )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        message,
    )
    return _git(repo, "rev-parse", "HEAD")


def _annotated_tag(repo: Path, tag: str) -> None:
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "tag",
        "-a",
        tag,
        "-m",
        tag,
    )


def _descriptor(repo: Path, relative: str) -> dict[str, object]:
    payload = (repo / relative).read_bytes()
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _write_dvc_pointer(
    repo: Path,
    relative: str,
    *,
    run_tag: str,
    nfiles: int,
    output_path: str | None = None,
    digest_digit: str = "a",
    digest: str | None = None,
    size: int = 123,
) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "outs:\n"
        f"- md5: {digest or digest_digit * 32}.dir\n"
        f"  size: {size}\n"
        f"  nfiles: {nfiles}\n"
        "  hash: md5\n"
        f"  path: {output_path or run_tag}\n",
        encoding="utf-8",
    )


def _phase_a_artifact_repo(
    repo: Path,
    *,
    preexisting: bool = False,
    wrong_data_output: bool = False,
    materialized: bool = True,
) -> tuple[dict[str, object], str, str]:
    _git(repo, "init")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    (repo / RUNNER_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / RUNNER_PATH).write_text("# synthetic runner\n", encoding="utf-8")
    (repo / UV_LOCK_PATH).write_text("version = 1\n", encoding="utf-8")
    run_tag = "phase-a-v1a"
    paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    if preexisting:
        _write_dvc_pointer(repo, paths["data"], run_tag=run_tag, nfiles=8, digest_digit="b")
        _write_dvc_pointer(repo, paths["model"], run_tag=run_tag, nfiles=3, digest_digit="b")
    protocol_commit = _commit(repo, "protocol")
    _annotated_tag(repo, "protocol/phase-a-v1a")
    _write_dvc_pointer(
        repo,
        paths["data"],
        run_tag=run_tag,
        nfiles=8,
        output_path="wrong-run" if wrong_data_output else None,
    )
    _write_dvc_pointer(repo, paths["model"], run_tag=run_tag, nfiles=3)
    artifact_commit = _commit(repo, "two pointers")
    _annotated_tag(repo, "artifacts/phase-a-v1a")
    if materialized:
        for relative in paths.values():
            (repo / relative).with_suffix("").mkdir(parents=True)
    source: dict[str, object] = {
        "run_tag": run_tag,
        "protocol_tag": "protocol/phase-a-v1a",
        "protocol_commit": protocol_commit,
        "artifact_tag": "artifacts/phase-a-v1a",
        "artifact_commit": artifact_commit,
        "dvc_pointers": {key: _descriptor(repo, relative) for key, relative in paths.items()},
    }
    return source, protocol_commit, artifact_commit


def test_phase_a_artifact_commit_requires_new_exact_two_directory_pointers(
    tmp_path: Path,
) -> None:
    source, _, artifact_commit = _phase_a_artifact_repo(tmp_path)
    observed = _require_phase_a_artifact_transport(
        source, evaluation_commit=artifact_commit, root=tmp_path
    )
    if observed["data"]["nfiles"] != 8 or observed["model"]["nfiles"] != 3:
        pytest.fail("Exact Phase-A DVC pointer census was not retained.")


def test_phase_a_artifact_commit_rejects_preexisting_pointer(tmp_path: Path) -> None:
    source, _, artifact_commit = _phase_a_artifact_repo(tmp_path, preexisting=True)
    with pytest.raises(RuntimeError, match="already existed"):
        _require_phase_a_artifact_transport(
            source, evaluation_commit=artifact_commit, root=tmp_path
        )


def test_phase_a_artifact_commit_rejects_wrong_out_path(tmp_path: Path) -> None:
    source, _, artifact_commit = _phase_a_artifact_repo(tmp_path, wrong_data_output=True)
    with pytest.raises(RuntimeError, match="output path, digest, or file census"):
        _require_phase_a_artifact_transport(
            source, evaluation_commit=artifact_commit, root=tmp_path
        )


def test_phase_a_artifact_transport_requires_materialized_paths(tmp_path: Path) -> None:
    source, _, artifact_commit = _phase_a_artifact_repo(tmp_path, materialized=False)
    with pytest.raises(RuntimeError, match="must be occupied"):
        _require_phase_a_artifact_transport(
            source, evaluation_commit=artifact_commit, root=tmp_path
        )


def test_phase_a_artifact_commit_rejects_multiple_parents(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    protocol_commit = _commit(tmp_path, "protocol")
    _annotated_tag(tmp_path, "protocol/phase-a-v1a")
    main_branch = _git(tmp_path, "branch", "--show-current")
    _git(tmp_path, "checkout", "-b", "side")
    (tmp_path / "side.txt").write_text("side\n", encoding="utf-8")
    _commit(tmp_path, "side")
    _git(tmp_path, "checkout", main_branch)
    run_tag = "phase-a-v1a"
    paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    _write_dvc_pointer(tmp_path, paths["data"], run_tag=run_tag, nfiles=8)
    _write_dvc_pointer(tmp_path, paths["model"], run_tag=run_tag, nfiles=3)
    _commit(tmp_path, "pointers")
    _git(
        tmp_path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "merge",
        "--no-ff",
        "side",
        "-m",
        "merge artifact",
    )
    artifact_commit = _git(tmp_path, "rev-parse", "HEAD")
    _annotated_tag(tmp_path, "artifacts/phase-a-v1a")
    source = {
        "run_tag": run_tag,
        "protocol_tag": "protocol/phase-a-v1a",
        "protocol_commit": protocol_commit,
        "artifact_tag": "artifacts/phase-a-v1a",
        "artifact_commit": artifact_commit,
        "dvc_pointers": {key: _descriptor(tmp_path, relative) for key, relative in paths.items()},
    }
    with pytest.raises(RuntimeError, match="exactly one parent"):
        _require_phase_a_artifact_transport(
            source, evaluation_commit=artifact_commit, root=tmp_path
        )


def test_phase_b_protocol_must_be_direct_child_of_phase_a_artifacts(tmp_path: Path) -> None:
    source, _, _ = _phase_a_artifact_repo(tmp_path)
    (tmp_path / "intermediate.txt").write_text("intermediate\n", encoding="utf-8")
    _commit(tmp_path, "intermediate commit")
    (tmp_path / "v1b.yaml").write_text("protocol: v1b\n", encoding="utf-8")
    evaluation_commit = _commit(tmp_path, "V1b protocol")
    with pytest.raises(RuntimeError, match="single-parent direct child"):
        _require_phase_a_artifact_transport(
            source,
            evaluation_commit=evaluation_commit,
            root=tmp_path,
        )


def _materialize_test_phase_a(
    repo: Path,
    *,
    source: dict[str, object],
    protocol_commit: str,
    config_override: dict[str, object] | None = None,
) -> dict[str, object]:
    run_tag = str(source["run_tag"])
    if config_override is None:
        artifact_names = {name: f"{name}.parquet" for name in PHASE_A_ARTIFACT_KEYS}
        output = {
            "data_root": "data/processed/experiments/ijds_audit",
            "model_root": "models/experiments/ijds_audit",
            **artifact_names,
            "outcome_free_summary": "outcome_free_summary.json",
            "outcome_free_receipt": "outcome_free_execution_receipt.json",
            "protocol_freeze": "protocol_freeze.json",
        }
        config: dict[str, object] = {
            "run_tag": run_tag,
            "protocol_tag": str(source["protocol_tag"]),
            "output": output,
        }
    else:
        config = copy.deepcopy(config_override)
        output = config["output"]
        if not isinstance(output, dict):
            pytest.fail("Synthetic Phase-A config output must be a mapping.")
        artifact_names = {name: str(output[name]) for name in PHASE_A_ARTIFACT_KEYS}
    data_dir = repo / "data/processed/experiments/ijds_audit" / run_tag / "frontier"
    model_dir = repo / "models/experiments/ijds_audit" / run_tag
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    for name in PHASE_A_ARTIFACT_KEYS:
        (data_dir / artifact_names[name]).write_bytes(f"artifact:{name}\n".encode())
    identity = {
        "status": FREEZE_STATUS,
        "run_tag": run_tag,
        "protocol_tag": str(source["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    summary_path = model_dir / str(output["outcome_free_summary"])
    execution_receipt_path = model_dir / str(output["outcome_free_receipt"])
    summary_path.write_text(json.dumps(identity) + "\n", encoding="utf-8")
    execution_receipt_path.write_text(json.dumps(identity) + "\n", encoding="utf-8")
    freeze = {
        **identity,
        "schemas": {name: {} for name in PHASE_A_ARTIFACT_KEYS},
        "outcome_free_artifacts": {
            name: _descriptor(
                repo,
                (
                    Path("data/processed/experiments/ijds_audit")
                    / run_tag
                    / "frontier"
                    / artifact_names[name]
                ).as_posix(),
            )
            for name in PHASE_A_ARTIFACT_KEYS
        },
        "summary": _descriptor(repo, summary_path.relative_to(repo).as_posix()),
        "execution_receipt": _descriptor(repo, execution_receipt_path.relative_to(repo).as_posix()),
    }
    (model_dir / str(output["protocol_freeze"])).write_text(
        json.dumps(freeze, indent=2) + "\n", encoding="utf-8"
    )
    return config


def _test_directory_md5(directory: Path) -> str:
    entries = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        entries.append(
            {
                "md5": hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                "relpath": path.relative_to(directory).as_posix(),
            }
        )
    # DVC 3.67.1 Tree.as_bytes uses json.dumps(..., sort_keys=True) with
    # default separators before MD5; this fixture therefore pins a real
    # directory-object digest rather than a decorative hexadecimal token.
    serialized = json.dumps(entries, sort_keys=True).encode("utf-8")
    return hashlib.md5(serialized, usedforsecurity=False).hexdigest()


def test_directory_digest_matches_pinned_dvc_tree_as_bytes(tmp_path: Path) -> None:
    directory = tmp_path / "tree"
    files = [directory / "b.bin", directory / "nested" / "a.txt"]
    for index, path in enumerate(files):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"payload-{index}\n".encode())

    observed = _directory_content_descriptor(directory, files, repo_root=tmp_path)
    dvc_tree = Tree()
    for path in files:
        payload = path.read_bytes()
        relative = path.relative_to(directory).as_posix()
        dvc_tree.add(
            tuple(relative.split("/")),
            Meta(),
            HashInfo(
                "md5",
                hashlib.md5(payload, usedforsecurity=False).hexdigest(),
            ),
        )
    expected = hashlib.md5(dvc_tree.as_bytes(), usedforsecurity=False).hexdigest() + ".dir"
    if observed["dvc_md5"] != expected:
        pytest.fail(
            "Manual content reconciliation drifted from pinned DVC Tree.as_bytes: "
            f"observed={observed['dvc_md5']}, expected={expected}."
        )


def _clean_transport_repo(
    repo: Path, *, pointer_size_delta: int = 0
) -> tuple[dict[str, object], dict[str, object], str, str]:
    _git(repo, "init")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / ".gitignore").write_text(
        "/data/processed/experiments/ijds_audit/*/\n/models/experiments/ijds_audit/*/\n",
        encoding="utf-8",
    )
    config_relative = CONFIG.relative_to(ROOT)
    (repo / config_relative).parent.mkdir(parents=True, exist_ok=True)
    config_text = CONFIG.read_text(encoding="utf-8").replace(
        "ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a",
        "phase-a-v1a",
    )
    (repo / config_relative).write_text(config_text, encoding="utf-8")
    (repo / RUNNER_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / RUNNER_PATH).write_bytes((ROOT / RUNNER_PATH).read_bytes())
    (repo / UV_LOCK_PATH).write_bytes((ROOT / UV_LOCK_PATH).read_bytes())
    config = load_set_preserving_config(repo / config_relative)
    protocol_commit = _commit(repo, "V1a protocol")
    _annotated_tag(repo, str(config["protocol_tag"]))
    run_tag = str(config["run_tag"])
    artifact_tag = "artifacts/ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a"
    source: dict[str, object] = {
        "run_tag": run_tag,
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    _materialize_test_phase_a(
        repo,
        source=source,
        protocol_commit=protocol_commit,
        config_override=config,
    )
    roots = {
        "data": repo / str(config["output"]["data_root"]) / run_tag,
        "model": repo / str(config["output"]["model_root"]) / run_tag,
    }
    pointer_paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    for key, nfiles in (("data", 8), ("model", 3)):
        files = [path for path in roots[key].rglob("*") if path.is_file()]
        _write_dvc_pointer(
            repo,
            pointer_paths[key],
            run_tag=run_tag,
            nfiles=nfiles,
            size=sum(path.stat().st_size for path in files) + pointer_size_delta,
            digest=_test_directory_md5(roots[key]),
        )
    artifact_commit = _commit(repo, "Phase-A DVC pointers")
    _annotated_tag(repo, artifact_tag)
    source.update(
        {
            "artifact_tag": artifact_tag,
            "artifact_commit": artifact_commit,
            "dvc_pointers": {
                key: _descriptor(repo, relative) for key, relative in pointer_paths.items()
            },
            "config": _descriptor(repo, config_relative.as_posix()),
        }
    )
    for directory in roots.values():
        shutil.rmtree(directory)
    return source, config, protocol_commit, artifact_commit


def _spy_transport_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repo: Path,
    source: dict[str, object],
    config: dict[str, object],
    protocol_commit: str,
    pull_returncode: int = 0,
    materialize: bool = True,
    drift: bool = False,
    status_returncode: int = 0,
    status_stdout: bytes = b"{}\n",
) -> list[list[str]]:
    original = subprocess.run
    calls: list[list[str]] = []
    pointer_paths = [str(source["dvc_pointers"][key]["path"]) for key in ("data", "model")]
    expected_pull = [sys.executable, "-I", "-m", "dvc", "pull", *pointer_paths]
    expected_status = [
        sys.executable,
        "-I",
        "-m",
        "dvc",
        "status",
        "--json",
        *pointer_paths,
    ]

    def spy(argv: object, *args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        command = [str(value) for value in argv] if isinstance(argv, (list, tuple)) else []
        if command in (expected_pull, expected_status) and (
            Path(str(kwargs.get("cwd"))).resolve() != repo.resolve()
            or kwargs.get("shell") is not False
            or kwargs.get("check") is not False
            or kwargs.get("capture_output") is not True
            or kwargs.get("text") is not False
        ):
            pytest.fail(f"Transport subprocess kwargs changed: {kwargs}")
        if command == expected_pull:
            calls.append(command)
            if pull_returncode == 0 and materialize:
                run_tag = str(source["run_tag"])
                output = config["output"]
                if not isinstance(output, dict):
                    pytest.fail("Synthetic transport config output must be a mapping.")
                roots = [repo / str(output[key]) / run_tag for key in ("data_root", "model_root")]
                if any(path.exists() for path in roots):
                    pytest.fail("Phase-A outputs existed before the spied DVC pull.")
                _materialize_test_phase_a(
                    repo,
                    source=source,
                    protocol_commit=protocol_commit,
                    config_override=config,
                )
            if drift:
                (repo / UV_LOCK_PATH).write_text("drift\n", encoding="utf-8")
            return subprocess.CompletedProcess(
                command,
                pull_returncode,
                stdout=b"pull-complete\n" if pull_returncode == 0 else b"",
                stderr=b"" if pull_returncode == 0 else b"pull-failed\n",
            )
        if command == expected_status:
            calls.append(command)
            return subprocess.CompletedProcess(
                command,
                status_returncode,
                stdout=status_stdout,
                stderr=b"" if status_returncode == 0 else b"status-failed\n",
            )
        return original(argv, *args, **kwargs)

    monkeypatch.setattr(runner_module.subprocess, "run", spy)
    return calls


def test_clean_clone_transport_invokes_exact_pull_contract_once_and_receipt_is_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit, artifact_commit = _clean_transport_repo(tmp_path)
    calls = _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    receipt_path = verify_phase_a_clean_clone_transport(
        config_path=Path(source["config"]["path"]),
        artifact_tag=str(source["artifact_tag"]),
        repo_root=tmp_path,
    )
    pointer_paths = [str(source["dvc_pointers"][key]["path"]) for key in ("data", "model")]
    expected_pull = [sys.executable, "-I", "-m", "dvc", "pull", *pointer_paths]
    if calls.count(expected_pull) != 1:
        pytest.fail(f"Expected exactly one isolated DVC pull command, observed {calls}.")
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt_path.read_bytes() != _canonical_json_bytes(payload):
        pytest.fail("Transport receipt is not the unique canonical JSON byte representation.")
    if (
        payload["schema_version"] != TRANSPORT_SCHEMA_VERSION
        or payload["runtime"]["dvc"]["version"] != "3.67.1"
        or payload["authority"]["protocol"]["object_type"] != "tag"
        or payload["authority"]["artifact"]["peeled_commit"] != artifact_commit
        or payload["execution"]["dvc_pull"]["transcript"]["shell"] is not False
        or payload["execution"]["dvc_pull"]["transcript"]["cwd"] != "."
    ):
        pytest.fail(f"Canonical receipt omitted locked authority: {payload}")
    run_tag = str(source["run_tag"])
    roots = {
        "data": tmp_path / str(config["output"]["data_root"]) / run_tag,
        "model": tmp_path / str(config["output"]["model_root"]) / run_tag,
    }
    for key in ("data", "model"):
        observed_md5 = payload["authority"]["dvc_pointers"][key]["out"]["md5"]
        if observed_md5 != f"{_test_directory_md5(roots[key])}.dir":
            pytest.fail(f"{key} pointer does not contain the real DVC directory digest.")
    lowered = receipt_path.read_bytes().lower()
    if any(token in lowered for token in (b"c:/users/", b"c:\\users\\", b"/home/")):
        pytest.fail("Transport receipt leaked a personal absolute path.")
    with pytest.raises((FileExistsError, RuntimeError), match=r"occupied|absent|clean predeclared"):
        verify_phase_a_clean_clone_transport(
            config_path=Path(source["config"]["path"]),
            artifact_tag=str(source["artifact_tag"]),
            repo_root=tmp_path,
        )
    if calls.count(expected_pull) != 1:
        pytest.fail("A rejected second invocation executed another DVC pull.")


@pytest.mark.parametrize(
    (
        "pull_returncode",
        "materialize",
        "drift",
        "status_returncode",
        "status_stdout",
        "message",
    ),
    [
        (9, False, False, 0, b"{}\n", "return code 9"),
        (0, False, False, 0, b"{}\n", "did not materialize"),
        (0, True, True, 0, b"{}\n", "Git authority changed"),
        (0, True, False, 7, b"", "status failed with return code 7"),
        (0, True, False, 0, b'{"changed":["data"]}\n', "status reports content drift"),
    ],
)
def test_clean_clone_transport_fails_on_subprocess_or_state_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pull_returncode: int,
    materialize: bool,
    drift: bool,
    status_returncode: int,
    status_stdout: bytes,
    message: str,
) -> None:
    source, config, protocol_commit, _ = _clean_transport_repo(tmp_path)
    calls = _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
        pull_returncode=pull_returncode,
        materialize=materialize,
        drift=drift,
        status_returncode=status_returncode,
        status_stdout=status_stdout,
    )
    with pytest.raises(RuntimeError, match=message):
        verify_phase_a_clean_clone_transport(
            config_path=Path(source["config"]["path"]),
            artifact_tag=str(source["artifact_tag"]),
            repo_root=tmp_path,
        )
    if len([call for call in calls if "pull" in call]) != 1:
        pytest.fail(f"Fault path did not execute exactly one DVC pull: {calls}")


def test_clean_clone_transport_rejects_preexisting_output_without_pull(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit, _ = _clean_transport_repo(tmp_path)
    run_tag = str(source["run_tag"])
    (tmp_path / "data/processed/experiments/ijds_audit" / run_tag).mkdir(parents=True)
    calls = _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    with pytest.raises(RuntimeError, match="absent before pull"):
        verify_phase_a_clean_clone_transport(
            config_path=Path(source["config"]["path"]),
            artifact_tag=str(source["artifact_tag"]),
            repo_root=tmp_path,
        )
    if any("pull" in call for call in calls):
        pytest.fail("Preexisting-output rejection nevertheless invoked DVC pull.")


def test_clean_clone_transport_reconciles_pointer_size_to_real_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit, _ = _clean_transport_repo(tmp_path, pointer_size_delta=1)
    _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    with pytest.raises(RuntimeError, match=r"out.size/nfiles disagree"):
        verify_phase_a_clean_clone_transport(
            config_path=Path(source["config"]["path"]),
            artifact_tag=str(source["artifact_tag"]),
            repo_root=tmp_path,
        )


def test_materialized_phase_a_rejects_fabricated_dvc_directory_digest(
    tmp_path: Path,
) -> None:
    source, config, protocol_commit, artifact_commit = _clean_transport_repo(tmp_path)
    _materialize_test_phase_a(
        tmp_path,
        source=source,
        protocol_commit=protocol_commit,
        config_override=config,
    )
    pointer_outs = _require_phase_a_artifact_transport(
        source, evaluation_commit=artifact_commit, root=tmp_path
    )
    pointer_outs["data"]["md5"] = f"{'0' * 32}.dir"
    with pytest.raises(RuntimeError, match="directory digest disagrees with real content"):
        _verified_phase_a_materialization(
            config,
            protocol_commit=protocol_commit,
            repo_root=tmp_path,
            pointer_outs=pointer_outs,
        )


def test_phase_b_receipt_verifier_accepts_only_committed_canonical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit, _ = _clean_transport_repo(tmp_path)
    calls = _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    verify_phase_a_clean_clone_transport(
        config_path=Path(source["config"]["path"]),
        artifact_tag=str(source["artifact_tag"]),
        repo_root=tmp_path,
    )
    evaluation_commit = _commit(tmp_path, "V1b canonical receipt pin")
    evaluation_tag = "protocol/test-v1b-canonical"
    _annotated_tag(tmp_path, evaluation_tag)
    source["clean_clone_transport_receipt"] = _descriptor(
        tmp_path, TRANSPORT_RECEIPT_PATH.as_posix()
    )
    pointer_outs = _require_phase_a_artifact_transport(
        source, evaluation_commit=evaluation_commit, root=tmp_path
    )
    _verify_phase_a_transport_receipt(
        source,
        source_config=config,
        pointer_outs=pointer_outs,
        evaluation_commit=evaluation_commit,
        evaluation_tag=evaluation_tag,
        root=tmp_path,
    )
    if len([call for call in calls if "pull" in call]) != 1:
        pytest.fail("Phase-B verification reran DVC pull instead of verifying its receipt.")


def _materialize_test_phase_b(
    repo: Path, *, config: dict[str, object], protocol_commit: str
) -> None:
    run_tag = str(config["run_tag"])
    output = config["output"]
    if not isinstance(output, dict):
        pytest.fail("Synthetic Phase-B output must be a mapping.")
    data_dir = repo / str(output["data_root"]) / run_tag / "evaluation"
    model_dir = repo / str(output["model_root"]) / run_tag
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths = {}
    for name in runner_module.PHASE_B_ARTIFACT_KEYS:
        path = data_dir / str(output[name])
        path.write_bytes(f"evaluation:{name}\n".encode())
        artifact_paths[name] = path
    identity = {
        "status": EVALUATION_STATUS,
        "run_tag": run_tag,
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
    }
    summary = model_dir / str(output["evaluation_summary"])
    receipt = model_dir / str(output["evaluation_receipt"])
    summary.write_text(json.dumps(identity) + "\n", encoding="utf-8")
    receipt.write_text(json.dumps(identity) + "\n", encoding="utf-8")
    manifest = {
        **identity,
        "evaluation_artifacts": {
            name: _descriptor(repo, path.relative_to(repo).as_posix())
            for name, path in artifact_paths.items()
        },
        "summary": _descriptor(repo, summary.relative_to(repo).as_posix()),
        "execution_receipt": _descriptor(repo, receipt.relative_to(repo).as_posix()),
    }
    (model_dir / str(output["evaluation_manifest"])).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _clean_phase_b_transport_repo(
    repo: Path,
) -> tuple[dict[str, object], dict[str, object], str]:
    _git(repo, "init")
    _git(repo, "config", "core.autocrlf", "false")
    (repo / ".gitignore").write_text(
        "/data/processed/experiments/ijds_audit/*/\n/models/experiments/ijds_audit/*/\n",
        encoding="utf-8",
    )
    config = load_set_preserving_config(CONFIG)
    config = copy.deepcopy(config)
    config["schema_version"] = "2026-07-29.2-test-v1b"
    config["protocol_status"] = "locked_hash_pinned_postfreeze_evaluation"
    config["protocol_tag"] = "protocol/phase-b-v1b"
    config["run_tag"] = "phase-b-v1b"

    def dummy(path: str, digit: str) -> dict[str, object]:
        return {"path": path, "bytes": 1, "sha256": digit * 64}

    config["source_frontier"] = {
        "run_tag": "phase-a-v1a",
        "protocol_tag": "protocol/phase-a-v1a",
        "protocol_commit": "a" * 40,
        "artifact_tag": "artifacts/phase-a-v1a",
        "artifact_commit": "b" * 40,
        "dvc_pointers": {
            "data": dummy("data/processed/experiments/ijds_audit/phase-a-v1a.dvc", "c"),
            "model": dummy("models/experiments/ijds_audit/phase-a-v1a.dvc", "d"),
        },
        "clean_clone_transport_receipt": dummy(TRANSPORT_RECEIPT_PATH.as_posix(), "e"),
        "config": dummy("configs/source-v1a.yaml", "f"),
        "freeze": dummy("models/source-v1a/protocol_freeze.json", "1"),
    }
    config_relative = Path("configs/experiments/phase_b_v1b.yaml")
    (repo / config_relative).parent.mkdir(parents=True, exist_ok=True)
    (repo / config_relative).write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (repo / RUNNER_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / RUNNER_PATH).write_bytes((ROOT / RUNNER_PATH).read_bytes())
    (repo / UV_LOCK_PATH).write_bytes((ROOT / UV_LOCK_PATH).read_bytes())
    loaded = load_set_preserving_config(repo / config_relative)
    protocol_commit = _commit(repo, "V1b protocol")
    _annotated_tag(repo, str(loaded["protocol_tag"]))
    _materialize_test_phase_b(repo, config=loaded, protocol_commit=protocol_commit)
    run_tag = str(loaded["run_tag"])
    roots = {
        "data": repo / str(loaded["output"]["data_root"]) / run_tag,
        "model": repo / str(loaded["output"]["model_root"]) / run_tag,
    }
    pointer_paths = {
        "data": f"data/processed/experiments/ijds_audit/{run_tag}.dvc",
        "model": f"models/experiments/ijds_audit/{run_tag}.dvc",
    }
    for key, nfiles in (("data", 6), ("model", 3)):
        files = [path for path in roots[key].rglob("*") if path.is_file()]
        _write_dvc_pointer(
            repo,
            pointer_paths[key],
            run_tag=run_tag,
            nfiles=nfiles,
            size=sum(path.stat().st_size for path in files),
            digest=_test_directory_md5(roots[key]),
        )
    artifact_commit = _commit(repo, "Phase-B DVC pointers")
    artifact_tag = "artifacts/phase-b-v1b"
    _annotated_tag(repo, artifact_tag)
    source: dict[str, object] = {
        "run_tag": run_tag,
        "protocol_tag": str(loaded["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "artifact_tag": artifact_tag,
        "artifact_commit": artifact_commit,
        "dvc_pointers": {
            key: _descriptor(repo, relative) for key, relative in pointer_paths.items()
        },
        "config": _descriptor(repo, config_relative.as_posix()),
    }
    for directory in roots.values():
        shutil.rmtree(directory)
    return source, loaded, protocol_commit


def test_phase_b_clean_clone_gate_reconciles_exact_six_plus_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit = _clean_phase_b_transport_repo(tmp_path)
    original = subprocess.run
    calls: list[list[str]] = []
    pointers = [str(source["dvc_pointers"][key]["path"]) for key in ("data", "model")]
    pull_argv = [sys.executable, "-I", "-m", "dvc", "pull", *pointers]
    status_argv = [sys.executable, "-I", "-m", "dvc", "status", "--json", *pointers]

    def spy(argv: object, *args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        command = [str(value) for value in argv] if isinstance(argv, (list, tuple)) else []
        if command == pull_argv:
            calls.append(command)
            _materialize_test_phase_b(tmp_path, config=config, protocol_commit=protocol_commit)
            return subprocess.CompletedProcess(command, 0, stdout=b"pull-b\n", stderr=b"")
        if command == status_argv:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=b"{}\n", stderr=b"")
        return original(argv, *args, **kwargs)

    monkeypatch.setattr(runner_module.subprocess, "run", spy)
    receipt = verify_phase_b_clean_clone_transport(
        config_path=Path(source["config"]["path"]),
        artifact_tag=str(source["artifact_tag"]),
        repo_root=tmp_path,
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    if (
        calls.count(pull_argv) != 1
        or payload["status"] != PHASE_B_TRANSPORT_STATUS
        or payload["materialized_phase_b"]["census"]
        != {"data_files": 6, "model_files": 3, "total_files": 9}
        or receipt.read_bytes() != _canonical_json_bytes(payload)
        or receipt.relative_to(tmp_path) != _phase_b_transport_receipt_path("phase-b-v1b")
    ):
        pytest.fail(f"Phase-B clean-clone gate did not close its 6+3 contract: {payload}")


@pytest.mark.parametrize("canonical_forgery", [False, True])
def test_phase_b_receipt_verifier_rejects_noncanonical_or_fabricated_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_forgery: bool,
) -> None:
    source, config, protocol_commit, artifact_commit = _clean_transport_repo(tmp_path)
    _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    receipt_path = verify_phase_a_clean_clone_transport(
        config_path=Path(source["config"]["path"]),
        artifact_tag=str(source["artifact_tag"]),
        repo_root=tmp_path,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    if canonical_forgery:
        payload["execution"]["dvc_pull"]["succeeded"] = False
        receipt_path.write_bytes(_canonical_json_bytes(payload))
    else:
        reordered = {"status": payload["status"]}
        reordered.update({key: value for key, value in payload.items() if key != "status"})
        receipt_path.write_text(
            json.dumps(reordered, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    evaluation_commit = _commit(tmp_path, "V1b receipt pin")
    evaluation_tag = f"protocol/test-v1b-{int(canonical_forgery)}"
    _annotated_tag(tmp_path, evaluation_tag)
    source["clean_clone_transport_receipt"] = _descriptor(
        tmp_path, TRANSPORT_RECEIPT_PATH.as_posix()
    )
    pointer_outs = _require_phase_a_artifact_transport(
        source, evaluation_commit=evaluation_commit, root=tmp_path
    )
    expected_message = "does not record successful" if canonical_forgery else "not canonical"
    with pytest.raises(RuntimeError, match=expected_message):
        _verify_phase_a_transport_receipt(
            source,
            source_config=config,
            pointer_outs=pointer_outs,
            evaluation_commit=evaluation_commit,
            evaluation_tag=evaluation_tag,
            root=tmp_path,
        )


def test_phase_b_receipt_verifier_rejects_boolean_returncode_forgery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, config, protocol_commit, _ = _clean_transport_repo(tmp_path)
    _spy_transport_subprocess(
        monkeypatch,
        repo=tmp_path,
        source=source,
        config=config,
        protocol_commit=protocol_commit,
    )
    receipt_path = verify_phase_a_clean_clone_transport(
        config_path=Path(source["config"]["path"]),
        artifact_tag=str(source["artifact_tag"]),
        repo_root=tmp_path,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    transcript = payload["execution"]["dvc_pull"]["transcript"]
    transcript["returncode"] = False
    transcript_body = {
        key: value for key, value in transcript.items() if key != "transcript_sha256"
    }
    transcript["transcript_sha256"] = hashlib.sha256(
        _canonical_json_bytes(transcript_body)
    ).hexdigest()
    receipt_path.write_bytes(_canonical_json_bytes(payload))
    evaluation_commit = _commit(tmp_path, "V1b boolean returncode forgery")
    evaluation_tag = "protocol/test-v1b-bool-returncode"
    _annotated_tag(tmp_path, evaluation_tag)
    source["clean_clone_transport_receipt"] = _descriptor(
        tmp_path, TRANSPORT_RECEIPT_PATH.as_posix()
    )
    pointer_outs = _require_phase_a_artifact_transport(
        source, evaluation_commit=evaluation_commit, root=tmp_path
    )
    with pytest.raises(RuntimeError, match="transcript does not reconcile exactly"):
        _verify_phase_a_transport_receipt(
            source,
            source_config=config,
            pointer_outs=pointer_outs,
            evaluation_commit=evaluation_commit,
            evaluation_tag=evaluation_tag,
            root=tmp_path,
        )


def test_materialized_phase_a_rejects_extra_file(tmp_path: Path) -> None:
    source, protocol_commit, _ = _phase_a_artifact_repo(tmp_path)
    config = _materialize_test_phase_a(tmp_path, source=source, protocol_commit=protocol_commit)
    _verified_phase_a_materialization(config, protocol_commit=protocol_commit, repo_root=tmp_path)
    run_tag = str(source["run_tag"])
    extra = tmp_path / "models/experiments/ijds_audit" / run_tag / "unexpected.json"
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="file census"):
        _verified_phase_a_materialization(
            config, protocol_commit=protocol_commit, repo_root=tmp_path
        )


def test_v2_implementation_requires_exact_census_and_identical_shared_bytes() -> None:
    locked = {path.as_posix() for path in IMPLEMENTATION_PATHS}

    def descriptor(path: str, digest: str) -> dict[str, object]:
        return {"path": path, "bytes": 1, "sha256": digest}

    source_files = {path: descriptor(path, "a" * 64) for path in locked}
    evaluation_files = copy.deepcopy(source_files)
    source_files["configs/source-v1.yaml"] = descriptor("configs/source-v1.yaml", "b" * 64)
    evaluation_files["configs/evaluation-v2.yaml"] = descriptor(
        "configs/evaluation-v2.yaml", "c" * 64
    )
    source = {"source_files": source_files}
    evaluation = {"source_files": evaluation_files}
    _require_v2_implementation_equals_v1(
        source,
        evaluation,
        source_config_path="configs/source-v1.yaml",
        evaluation_config_path="configs/evaluation-v2.yaml",
    )

    drifted = copy.deepcopy(evaluation)
    drifted["source_files"][next(iter(locked))]["sha256"] = "d" * 64
    with pytest.raises(RuntimeError, match="scientific dependency changed"):
        _require_v2_implementation_equals_v1(
            source,
            drifted,
            source_config_path="configs/source-v1.yaml",
            evaluation_config_path="configs/evaluation-v2.yaml",
        )

    incomplete = copy.deepcopy(evaluation)
    incomplete["source_files"].pop(next(iter(locked)))
    with pytest.raises(RuntimeError, match="omits or adds"):
        _require_v2_implementation_equals_v1(
            source,
            incomplete,
            source_config_path="configs/source-v1.yaml",
            evaluation_config_path="configs/evaluation-v2.yaml",
        )


def test_transitive_authority_includes_outcome_and_v5_dependencies() -> None:
    observed = {path.as_posix() for path in IMPLEMENTATION_PATHS}
    required = {
        "src/data/outcome_observability.py",
        "src/ijds_audit/prediction.py",
        "src/evaluation/coverage_transport.py",
        "src/models/maturity_safe_pd.py",
        "src/optimization/portfolio_model.py",
        "docs/research/ijds_endpoint_reason_recovery_v5_erratum_2026-07-15.md",
        "configs/experiments/ijds_binary_geometry_frontier_v4_2026-07-15_v5.yaml",
    }
    missing = required - observed
    if missing:
        pytest.fail(f"Transitive authority omits dependencies: {sorted(missing)}.")


def _repo_import_closure(start: Path) -> set[str]:
    """Independently derive the repo-local AST import closure plus package initializers."""

    def module_file(name: str) -> Path | None:
        candidate = ROOT.joinpath(*name.split("."))
        source = candidate.with_suffix(".py")
        if source.is_file():
            return source
        initializer = candidate / "__init__.py"
        return initializer if initializer.is_file() else None

    def module_name(path: Path) -> str:
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    observed: set[Path] = set()
    queue = [start.resolve()]
    while queue:
        path = queue.pop(0)
        if path in observed:
            continue
        observed.add(path)
        for parent in list(path.relative_to(ROOT).parents)[:-1]:
            initializer = (ROOT / parent / "__init__.py").resolve()
            if initializer.is_file() and initializer not in observed and initializer not in queue:
                queue.append(initializer)

        tree = ast.parse(path.read_text(encoding="utf-8"))
        current = module_name(path)
        package = current if path.name == "__init__.py" else current.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            candidates: list[str] = []
            if isinstance(node, ast.Import):
                candidates.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")
                    if node.level > 1:
                        base = base[: -(node.level - 1)]
                    prefix = ".".join(base)
                    imported = ".".join(value for value in (prefix, node.module or "") if value)
                else:
                    imported = node.module or ""
                candidates.append(imported)
                candidates.extend(
                    ".".join(value for value in (imported, alias.name) if value)
                    for alias in node.names
                )
            for candidate in candidates:
                if not candidate.startswith(("src", "scripts")):
                    continue
                resolved = module_file(candidate)
                if resolved is not None and resolved.resolve() not in observed:
                    queue.append(resolved.resolve())
    return {path.relative_to(ROOT).as_posix() for path in observed}


def test_transitive_python_authority_equals_ast_closure() -> None:
    runner = ROOT / "scripts/experiments/run_ijds_set_preserving_embedding_sensitivity_v1.py"
    expected = _repo_import_closure(runner)
    observed = {path.as_posix() for path in TRANSITIVE_PYTHON_PATHS}
    if observed != expected:
        pytest.fail(
            "Transitive Python authority differs from AST closure: "
            f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}."
        )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Point LP is not optimal: Infeasible.", True),
        ("Point LP is not optimal: Unknown.", True),
        ("Point LP did not fill its budget: residual=1e-10", True),
        ("Point LP is not optimal: Unbounded.", False),
        ("Point LP did not bind its cap.", False),
    ],
)
def test_minimum_endpoint_retry_taxonomy_is_closed(message: str, expected: bool) -> None:
    observed = _is_minimum_endpoint_boundary_failure(RuntimeError(message))
    if observed is not expected:
        pytest.fail(f"Retry classification changed for {message!r}: {observed}.")


def test_runner_requires_an_explicit_phase() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--config", str(CONFIG)])
    with pytest.raises(SystemExit):
        parse_args(["--config", str(CONFIG), "--phase", "verify-phase-a-transport"])
    with pytest.raises(SystemExit):
        parse_args(["--config", str(CONFIG), "--phase", "verify-phase-b-transport"])
    parsed = parse_args(
        [
            "--config",
            str(CONFIG),
            "--phase",
            "verify-phase-b-transport",
            "--artifact-tag",
            "artifacts/test-phase-b",
        ]
    )
    if parsed.phase != "verify-phase-b-transport" or parsed.artifact_tag != (
        "artifacts/test-phase-b"
    ):
        pytest.fail("The Phase-B clean-clone gate is not reachable through the committed CLI.")
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--config",
                str(CONFIG),
                "--phase",
                "outcome-free",
                "--artifact-tag",
                "artifacts/not-valid-here",
            ]
        )


def test_output_paths_are_contained_and_immutable(tmp_path: Path) -> None:
    config = copy.deepcopy(load_set_preserving_config(CONFIG))
    config["run_tag"] = "set-preserving-test"
    paths = prepare_output_paths(config, repo_root=tmp_path)

    expected_data = tmp_path / "data/processed/experiments/ijds_audit/set-preserving-test"
    expected_model = tmp_path / "models/experiments/ijds_audit/set-preserving-test"
    if paths.data_dir != expected_data or paths.model_dir != expected_model:
        pytest.fail(f"Output paths escaped isolation: {paths!r}.")
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_output_paths(config, repo_root=tmp_path)


def test_embedding_preserves_all_four_binary_set_types_exactly() -> None:
    point = np.array([0.20, 0.30, 0.70, 0.80])
    lower = np.array([0.05, 0.00, 0.40, 0.00])
    upper = np.array([0.60, 0.80, 1.00, 1.00])
    original_code = (lower == 0.0).astype(np.int8) + 2 * (upper == 1.0)
    np.testing.assert_array_equal(original_code, np.array([0, 1, 2, 3]))

    for theta in THETA_GRID:
        embedded = set_preserving_upper(point, lower, upper, theta=theta)
        embedded_code = (lower == 0.0).astype(np.int8) + 2 * (embedded == 1.0)
        np.testing.assert_array_equal(embedded_code, original_code)
        ordinary = upper < 1.0
        if not bool(np.all(point[ordinary] <= embedded[ordinary])):
            pytest.fail("Embedded upper endpoint fell below the point score.")
        if not bool(np.all(embedded[ordinary] <= upper[ordinary])):
            pytest.fail("Embedded upper endpoint exceeded the original endpoint.")
        if not bool(np.all(embedded[ordinary] < 1.0)):
            pytest.fail("Embedding acquired label 1 outside the original set.")
        if not bool(np.all(embedded[~ordinary] == 1.0)):
            pytest.fail("Embedding removed label 1 from the original set.")


def test_primary_decision_scrub_rejects_residual_learner_controls() -> None:
    config = load_set_preserving_config(CONFIG)
    retained = list(config["source_ingest"]["retained_decision_columns"])
    discarded = list(config["source_ingest"]["discarded_coverage_control_columns"])
    frame = pd.DataFrame({column: [0] for column in [*retained, *discarded]})

    scrubbed = retain_primary_decision_inputs(frame, config=config)

    if scrubbed.columns.tolist() != retained:
        pytest.fail(f"Primary-only scrub retained the wrong schema: {scrubbed.columns.tolist()}.")
    drifted = frame.assign(pd_unexpected_control=0.5)
    with pytest.raises(RuntimeError, match="schema drifted"):
        retain_primary_decision_inputs(drifted, config=config)


def test_embedding_endpoints_and_gamma_zero_are_exact_negative_controls() -> None:
    point = np.array([0.2, 0.4, 0.7])
    lower = np.array([0.0, 0.1, 0.2])
    upper = np.array([0.8, 1.0, 0.9])

    theta_zero = set_preserving_upper(point, lower, upper, theta=0.0)
    theta_one = set_preserving_upper(point, lower, upper, theta=1.0)
    np.testing.assert_array_equal(theta_zero, upper)
    np.testing.assert_array_equal(theta_one, np.array([0.2, 1.0, 0.7]))
    for theta in THETA_GRID:
        embedded = set_preserving_upper(point, lower, upper, theta=theta)
        score = point + 0.0 * (embedded - point)
        np.testing.assert_array_equal(score, point)
        if embedding_diagnostics(point, lower, upper, theta=theta)["sets_changed"] != 0:
            pytest.fail("Embedding diagnostic reports a changed binary set.")


@pytest.mark.parametrize(
    ("point", "lower", "upper", "message"),
    [
        ([0.2], [0.3], [0.8], "lower <= point"),
        ([0.9], [0.1], [0.8], "lower <= point"),
        ([np.nan], [0.0], [1.0], "finite"),
        ([1.1], [0.0], [1.0], r"\[0,1\]"),
    ],
)
def test_embedding_fails_closed_on_invalid_intervals(
    point: list[float], lower: list[float], upper: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        set_preserving_upper(np.asarray(point), np.asarray(lower), np.asarray(upper), theta=0.25)


def test_global_objective_lower_uses_all_25_scores() -> None:
    states = {
        (theta, gamma): SimpleNamespace(minimum_objective=10.0 + theta + gamma)
        for theta in THETA_GRID
        for gamma in GAMMA_GRID
    }
    states[(1.0, 0.75)] = SimpleNamespace(minimum_objective=42.0)

    lower = common_25_score_objective_lower(
        states,
        objective_optimum=100.0,
        minimum_range=1.0e-4,
    )
    if lower != 42.0:
        pytest.fail(f"Global objective lower endpoint ignored a score cell: {lower}.")

    incomplete = dict(states)
    incomplete.pop((1.0, 0.75))
    with pytest.raises(ValueError, match="all 25 scores"):
        common_25_score_objective_lower(
            incomplete,
            objective_optimum=100.0,
            minimum_range=1.0e-4,
        )


def test_policy_labels_are_unique_over_the_complete_grid() -> None:
    labels = {
        policy_label(ruler, theta, gamma, coordinate)
        for ruler in ("objective_matched", "normalized_score")
        for theta in THETA_GRID
        for gamma in GAMMA_GRID
        for coordinate in (0.25, 0.5, 0.75)
    }
    if len(labels) != 150:
        pytest.fail(f"Policy labels collide: observed {len(labels)} labels.")


def test_direction_census_separates_literal_sign_from_tolerance_decision() -> None:
    config = load_set_preserving_config(CONFIG)
    base = {
        "window_id": "W1",
        "contrast_family": CONTRAST_GAMMA,
        "ruler": "objective_matched",
        "coordinate": 0.25,
        "theta": 0.0,
        "theta_reference": 0.0,
        "gamma": 1.0,
        "gamma_reference": 0.0,
        "policy_a": policy_label("objective_matched", 0.0, 1.0, 0.25),
        "policy_b": policy_label("objective_matched", 0.0, 0.0, 0.25),
        "weighted_default_difference_lower": 0.0,
        "weighted_default_difference_upper": 0.0,
        "weighted_miscoverage_difference_lower": 0.0,
        "weighted_miscoverage_difference_upper": 0.0,
    }
    bounds = pd.DataFrame(
        [
            {
                **base,
                "realized_payoff_difference_lower": 5.0e-5,
                "realized_payoff_difference_upper": 5.0e-5,
            },
            {
                **base,
                "window_id": "W2",
                "realized_payoff_difference_lower": -2.0e-4,
                "realized_payoff_difference_upper": -5.0e-5,
            },
        ]
    )
    directions = metric_direction_census(bounds, metrics=config["metrics"])
    payoff = directions.loc[directions["metric"].eq("standardized_payoff")]
    observed = payoff[["geometric_direction", "direction_at_tolerance"]].itertuples(
        index=False, name=None
    )
    expected = [
        ("positive", "within_tolerance"),
        ("negative", "not_directionally_separated_at_tolerance"),
    ]
    if list(observed) != expected:
        pytest.fail(f"Literal/tolerance direction semantics drifted: {payoff.to_dict('records')}.")


def _synthetic_joined_allocations() -> pd.DataFrame:
    gamma_one = policy_label("objective_matched", 0.0, 1.0, 0.25)
    gamma_zero = policy_label("objective_matched", 0.0, 0.0, 0.25)
    theta_quarter = policy_label("objective_matched", 0.25, 0.0, 0.25)
    facts = {
        "a": ("2016-04", 0.0, 0.05),
        "b": ("2016-04", 1.0, 0.06),
        "c": ("2016-05", 1.0, 0.07),
        "d": ("2016-05", 0.0, 0.08),
    }
    exposures = {
        gamma_one: {"a": 99.99999, "c": 100.0},
        gamma_zero: {"b": 100.0, "d": 99.99998},
        theta_quarter: {"b": 100.0, "d": 99.99998},
    }
    rows: list[dict[str, object]] = []
    for label, policy_exposure in exposures.items():
        for loan_id, exposure in policy_exposure.items():
            period, outcome, rate = facts[loan_id]
            rows.append(
                {
                    "id": loan_id,
                    "window_id": "W1",
                    "role": "primary_oot",
                    "period": period,
                    "policy_label": label,
                    "exposure": exposure,
                    "expected_payoff_contribution": exposure * 0.01,
                    "contractual_rate": rate,
                    "conformal_lower": 0.0,
                    "conformal_upper": 1.0,
                    "snapshot_default": outcome,
                }
            )
    return pd.DataFrame(rows)


def test_sharp_bounds_use_common_committed_capital_monthly_and_pooled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = (
        {
            "contrast_family": CONTRAST_GAMMA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.0,
            "theta_reference": 0.0,
            "gamma": 1.0,
            "gamma_reference": 0.0,
        },
        {
            "contrast_family": CONTRAST_THETA,
            "ruler": "objective_matched",
            "coordinate": 0.25,
            "theta": 0.25,
            "theta_reference": 0.0,
            "gamma": 0.0,
            "gamma_reference": 0.0,
        },
    )
    monkeypatch.setattr(embedding_module, "_contrast_specs", lambda: specs)
    config = copy.deepcopy(load_set_preserving_config(CONFIG))
    config["frontier"]["expected_windows"] = 1
    config["frontier"]["expected_primary_months"] = 2
    config["normalization"]["committed_budget_per_period"] = 100.0
    config["expected_census"]["monthly_sharp_contrasts"] = 4
    config["expected_census"]["monthly_negative_controls"] = 2
    config["expected_census"]["window_sharp_contrasts"] = 2
    config["expected_census"]["window_negative_controls"] = 1
    config["expected_census"]["direction_rows"] = 6

    monthly, window, directions = build_sharp_embedding_contrasts(
        _synthetic_joined_allocations(), config=config, lgd=1.0, budget=100.0
    )

    gamma_monthly = monthly.loc[monthly["contrast_family"].eq(CONTRAST_GAMMA)]
    np.testing.assert_allclose(
        gamma_monthly["weighted_default_difference_lower"].to_numpy(),
        np.array([-1.0, 1.0]),
    )
    np.testing.assert_array_equal(
        gamma_monthly[
            ["policy_a_normalization_capital", "policy_b_normalization_capital"]
        ].to_numpy(dtype=float),
        np.full((2, 2), 100.0),
    )
    if set(gamma_monthly["normalization_rule"].astype(str)) != {"monthly_parent_committed_budget"}:
        pytest.fail("Monthly sharp bounds did not retain the parent-budget rule.")
    gamma_window = window.loc[window["contrast_family"].eq(CONTRAST_GAMMA)].iloc[0]
    # The tiny unequal solver residuals would create a spurious negative value
    # under policy-specific normalization. The locked 2B denominator is exact.
    np.testing.assert_allclose(
        [
            gamma_window["weighted_default_difference_lower"],
            gamma_window["weighted_default_difference_upper"],
        ],
        [0.0, 0.0],
        rtol=0.0,
        atol=1.0e-15,
    )
    wrong_policy_specific_value = 100.0 / 199.99999 - 100.0 / 199.99998
    if (
        abs(wrong_policy_specific_value)
        <= config["metrics"]["funded_default"]["direction_tolerance"]
    ):
        pytest.fail("Synthetic residuals no longer distinguish the rejected estimand.")
    np.testing.assert_array_equal(
        gamma_window[
            [
                "policy_a_normalization_capital",
                "policy_b_normalization_capital",
                "normalization_periods",
                "committed_budget_per_period",
            ]
        ].to_numpy(dtype=float),
        np.array([200.0, 200.0, 2.0, 100.0]),
    )
    if gamma_window["normalization_rule"] != ("pooled_period_count_times_parent_committed_budget"):
        pytest.fail("Pooled sharp bound did not retain its fixed-capital rule.")
    np.testing.assert_allclose(
        gamma_window["realized_payoff_rate_difference_lower"],
        gamma_window["realized_payoff_difference_lower"] / 200.0,
        rtol=0.0,
        atol=1.0e-15,
    )

    negative = window.loc[window["contrast_family"].eq(CONTRAST_THETA)].iloc[0]
    np.testing.assert_array_equal(
        negative[
            [
                "expected_objective_difference",
                "weighted_default_difference_lower",
                "weighted_default_difference_upper",
            ]
        ].to_numpy(dtype=float),
        np.zeros(3),
    )
    negative_directions = directions.loc[
        directions["contrast_family"].eq(CONTRAST_THETA), "direction_at_tolerance"
    ]
    if set(negative_directions) != {"within_tolerance"}:
        pytest.fail(f"Negative-control directions changed: {set(negative_directions)}.")

    mutated_reference = monthly.copy()
    mutated_reference.loc[mutated_reference.index[0], "policy_b"] = "mutated-policy"
    with pytest.raises(RuntimeError, match="mutated contrast specification"):
        validate_complete_evaluation(mutated_reference, window, directions, config=config)

    corrupted_directions = directions.copy()
    gamma_direction = corrupted_directions.index[
        corrupted_directions["contrast_family"].eq(CONTRAST_GAMMA)
    ][0]
    corrupted_directions.loc[gamma_direction, "lower"] += 0.5
    with pytest.raises(RuntimeError, match="does not reconcile"):
        validate_complete_evaluation(monthly, window, corrupted_directions, config=config)

    cancelled = monthly.copy()
    cancelled_negative = cancelled.index[cancelled["contrast_family"].eq(CONTRAST_THETA)]
    cancelled.loc[cancelled_negative, "expected_objective_difference"] = [50.0, -50.0]
    for lower_name, upper_name in (
        ("realized_payoff_difference_lower", "realized_payoff_difference_upper"),
        ("weighted_default_difference_lower", "weighted_default_difference_upper"),
    ):
        values = [50.0, -50.0] if lower_name.startswith("realized") else [1.0, -1.0]
        cancelled.loc[cancelled_negative, lower_name] = values
        cancelled.loc[cancelled_negative, upper_name] = values
    cancelled.loc[cancelled_negative, "realized_payoff_rate_difference_lower"] = [0.5, -0.5]
    cancelled.loc[cancelled_negative, "realized_payoff_rate_difference_upper"] = [0.5, -0.5]
    with pytest.raises(RuntimeError, match="monthly negative control"):
        validate_complete_evaluation(cancelled, window, directions, config=config)

    nonfinite = monthly.copy()
    nonfinite.loc[nonfinite.index[0], "policy_a_capital"] = np.nan
    with pytest.raises(RuntimeError, match="contains a non-finite"):
        validate_complete_evaluation(nonfinite, window, directions, config=config)

    summary = _evaluation_summary(
        config=config,
        protocol_commit="a" * 40,
        freeze={"status": FREEZE_STATUS},
        evaluated=pd.DataFrame({"row": [1]}),
        joined=pd.DataFrame({"row": [1]}),
        monthly=monthly,
        window=window,
        directions=directions,
        outcome_audit=pd.DataFrame({"unresolved_rows": [0]}),
        protected_reads=[],
    )
    normalization = summary["normalization"]
    if (
        normalization["committed_budget_B_dollars"] != 100.0
        or normalization["primary_periods_T"] != 2
        or normalization["pooled_capital_TB_dollars"] != 200.0
        or normalization["monthly_policy_capital_reconciles_to_B"] is not True
        or normalization["pooled_policy_capital_reconciles_to_TB"] is not True
        or normalization["payoff_rates_reconcile_to_common_capital"] is not True
    ):
        pytest.fail(
            f"Normalization summary did not retain B, T, TB and residual gates: {normalization}"
        )


@pytest.mark.parametrize(
    ("field", "census_key"),
    [
        ("solve_records", "frontier_solves"),
        ("allocations", "allocations"),
        ("embedding_diagnostics", "embedding_diagnostics"),
        ("minimum_endpoint_diagnostics", "minimum_score_endpoints"),
        ("objective_optimum_diagnostics", "objective_optima"),
        ("order_sensitivity", "order_replays"),
        ("independent_validation", "independent_solver_cells"),
        ("allocation_contrasts", "outcome_free_allocation_contrasts"),
    ],
)
def test_frontier_validation_rejects_nonfinite_in_every_numeric_table(
    field: str, census_key: str
) -> None:
    frames = {
        "solve_records": pd.DataFrame({"value": [1.0]}),
        "allocations": pd.DataFrame({"value": [1.0]}),
        "embedding_diagnostics": pd.DataFrame({"value": [1.0]}),
        "minimum_endpoint_diagnostics": pd.DataFrame({"value": [1.0]}),
        "objective_optimum_diagnostics": pd.DataFrame(
            {"value": [1.0], "basis_valid": pd.Series([True], dtype=bool)}
        ),
        "order_sensitivity": pd.DataFrame({"value": [1.0]}),
        "independent_validation": pd.DataFrame({"value": [1.0]}),
        "allocation_contrasts": pd.DataFrame({"value": [1.0]}),
    }
    frames[field].loc[0, "value"] = np.nan
    build = SetPreservingFrontierBuild(**frames)
    expected = {
        "frontier_solves": 1,
        "embedding_diagnostics": 1,
        "minimum_score_endpoints": 1,
        "objective_optima": 1,
        "order_replays": 1,
        "independent_solver_cells": 1,
        "outcome_free_allocation_contrasts": 1,
    }
    with pytest.raises(RuntimeError, match=f"{census_key} contains a non-finite"):
        validate_complete_frontier(build, config={"expected_census": expected}, budget=1.0)


def test_frontier_validation_requires_explicit_valid_basis_column() -> None:
    frame = pd.DataFrame({"value": [1.0]})
    solve = pd.DataFrame(
        {
            "value": [1.0],
            "frontier_ruler": ["normalized_score"],
            "frontier_cap": [1.0],
            "objective_target": [np.nan],
            "risk_tolerance": [1.0],
        }
    )
    allocations = solve.drop(columns="risk_tolerance").copy()
    build = SetPreservingFrontierBuild(
        solve_records=solve,
        allocations=allocations,
        embedding_diagnostics=frame.copy(),
        minimum_endpoint_diagnostics=frame.copy(),
        objective_optimum_diagnostics=frame.copy(),
        order_sensitivity=frame.copy(),
        independent_validation=frame.copy(),
        allocation_contrasts=frame.copy(),
    )
    expected = {
        "frontier_solves": 1,
        "embedding_diagnostics": 1,
        "minimum_score_endpoints": 1,
        "objective_optima": 1,
        "order_replays": 1,
        "independent_solver_cells": 1,
        "outcome_free_allocation_contrasts": 1,
    }
    with pytest.raises(RuntimeError, match="point basis is absent or invalid"):
        validate_complete_frontier(build, config={"expected_census": expected}, budget=1.0)


@pytest.mark.parametrize(
    ("target", "ruler", "column", "value", "message"),
    [
        ("solve", "normalized_score", "frontier_cap", np.inf, "contains an infinite"),
        (
            "solve",
            "normalized_score",
            "objective_target",
            0.0,
            "not-applicable pattern",
        ),
        (
            "solve",
            "objective_matched",
            "frontier_cap",
            0.0,
            "not-applicable pattern",
        ),
        ("allocations", "normalized_score", "frontier_cap", np.inf, "contains an infinite"),
    ],
)
def test_frontier_structural_nullability_is_exact_and_infinity_is_forbidden(
    target: str, ruler: str, column: str, value: float, message: str
) -> None:
    solve = pd.DataFrame(
        {
            "value": [1.0],
            "frontier_ruler": ["normalized_score"],
            "frontier_cap": [1.0],
            "objective_target": [np.nan],
            "risk_tolerance": [1.0],
        }
    )
    allocations = solve.drop(columns="risk_tolerance").copy()
    selected = solve if target == "solve" else allocations
    selected.loc[0, "frontier_ruler"] = ruler
    if ruler == "objective_matched":
        selected.loc[0, "frontier_cap"] = np.nan
        selected.loc[0, "objective_target"] = 1.0
        if "risk_tolerance" in selected:
            selected.loc[0, "risk_tolerance"] = np.nan
    selected.loc[0, column] = value
    frame = pd.DataFrame({"value": [1.0]})
    build = SetPreservingFrontierBuild(
        solve_records=solve,
        allocations=allocations,
        embedding_diagnostics=frame.copy(),
        minimum_endpoint_diagnostics=frame.copy(),
        objective_optimum_diagnostics=pd.DataFrame(
            {"value": [1.0], "basis_valid": pd.Series([True], dtype=bool)}
        ),
        order_sensitivity=frame.copy(),
        independent_validation=frame.copy(),
        allocation_contrasts=frame.copy(),
    )
    expected = {
        "frontier_solves": 1,
        "embedding_diagnostics": 1,
        "minimum_score_endpoints": 1,
        "objective_optima": 1,
        "order_replays": 1,
        "independent_solver_cells": 1,
        "outcome_free_allocation_contrasts": 1,
    }
    with pytest.raises(RuntimeError, match=message):
        validate_complete_frontier(build, config={"expected_census": expected}, budget=1.0)


def test_phase_a_hashes_raw_before_frontier_construction_and_afterward() -> None:
    source = inspect.getsource(run_outcome_free)
    hash_positions = []
    start = 0
    needle = "sha256_file(raw_path)"
    while (position := source.find(needle, start)) >= 0:
        hash_positions.append(position)
        start = position + len(needle)
    build_position = source.index("load_outcome_free_decision_base")
    if not hash_positions or hash_positions[0] > build_position or len(hash_positions) < 3:
        pytest.fail("Raw SHA-256 is not checked before Phase-A build and at both post-build seals.")
