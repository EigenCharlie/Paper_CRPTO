"""Freeze the exact historical identity and quarantine of candidate replays."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "configs/experiments/ijds_hash_bound_candidate_receipt_index_2026-07-26.yaml"
PUBLICATION_TARGETS = ROOT / "configs/crpto_publication_targets.yaml"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_descriptor(descriptor: dict[str, object]) -> None:
    relative = Path(str(descriptor["path"]))
    assert not relative.is_absolute()
    path = (ROOT / relative).resolve()
    path.relative_to(ROOT.resolve())
    assert path.is_file()
    byte_count = descriptor["bytes"]
    assert type(byte_count) is int
    assert path.stat().st_size == byte_count
    assert _sha256(path) == str(descriptor["sha256"])


def test_candidate_receipt_index_freezes_execution_time_code_without_local_outputs() -> None:
    payload = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
    assert payload["paper_evidence_allowed"] is False
    assert payload["protocol_commit_available_at_execution"] is False
    historical_lock = subprocess.run(
        ["git", "show", f"{payload['base_git_commit']}:uv.lock"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert payload["scientific_uv_lock_sha256"] == hashlib.sha256(historical_lock).hexdigest()

    for run in payload["runs"].values():
        config = run["execution_implementation"]["config"]
        config_payload = yaml.safe_load((ROOT / config["path"]).read_text(encoding="utf-8"))
        assert config_payload["run_tag"] == run["run_tag"]
        assert config_payload["protocol_path"] == run["protocol"]["path"]
        _assert_descriptor(run["protocol"])
        for descriptor in run["execution_implementation"].values():
            _assert_descriptor(descriptor)


def test_executed_quarantine_crosswalk_matches_the_receipt_index_exactly() -> None:
    index = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
    targets = yaml.safe_load(PUBLICATION_TARGETS.read_text(encoding="utf-8"))
    capsule = targets["executed_quarantine_capsule"]

    assert capsule["receipt_indexes"] == [INDEX_PATH.relative_to(ROOT).as_posix()]
    assert set(capsule["protocols"]) == {run["protocol"]["path"] for run in index["runs"].values()}
    assert set(capsule["configs"]) == {
        run["execution_implementation"]["config"]["path"] for run in index["runs"].values()
    }
    assert set(capsule["replay_entrypoints"]) == {
        run["execution_implementation"]["runner"]["path"] for run in index["runs"].values()
    }
    assert set(capsule["implementations"]) == {
        run["execution_implementation"]["module"]["path"] for run in index["runs"].values()
    }
    assert set(capsule["quarantined_run_scope"]) == {
        run["run_tag"] for run in index["runs"].values()
    }


def test_candidate_capsule_records_every_known_reuse_blocker() -> None:
    payload = yaml.safe_load(PUBLICATION_TARGETS.read_text(encoding="utf-8"))
    capsule = payload["executed_quarantine_capsule"]
    assert capsule["active_paper_evidence_allowed"] is False
    assert capsule["active_claim_support_allowed"] is False
    assert set(capsule["known_reuse_blockers"]) == {
        "output_filenames_are_not_contained_or_unique_in_the_executed_runners",
        "one_class_no_interleaving_is_marked_true_in_the_executed_v6_helper",
        "conformal_group_is_cast_before_exact_integrality_validation",
        "v6_selects_a_catboost_stratum_transition_not_declared_by_its_protocol",
        "poisson_binomial_reference_omits_a_joint_conditional_independence_assumption",
        "shared_io_and_provenance_helpers_were_not_fully_hash_bound_at_execution",
    }
