"""Tests for the nonnumeric IJDS claim contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ijds_audit.claim_ledger import (
    load_claim_ledger,
    materialize_claim_ledger,
    resolve_json_pointer,
)


def _write_ledger(tmp_path: Path, *, expected: str = "ready") -> Path:
    (tmp_path / "body.md").write_text("<!-- claim:test.empirical -->\n", encoding="utf-8")
    (tmp_path / "registry.md").write_text(
        "<!-- claim:test.empirical -->\n<!-- claim:test.theorem -->\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "claims.yaml"
    ledger.write_text(
        f"""schema_version: test.1
status: active_ijds_claim_contract
surfaces:
  body: body.md
  registry: registry.md
claims:
  - id: test.empirical
    status: active
    kind: empirical
    rule: equals
    result_pointer: /result/status
    expected: {expected}
    lineages: [test.evaluation]
    scope: unit_test
    forbidden_inference: [causal]
    surfaces:
      required: [body, registry]
      allowed: [body, registry]
  - id: test.theorem
    status: active
    kind: theorem
    rule: documented
    lineages: []
    scope: algebra
    forbidden_inference: [empirical_universality]
    surfaces:
      required: [registry]
      allowed: [registry]
""",
        encoding="utf-8",
    )
    return ledger


def test_claim_ledger_materializes_without_numeric_duplication(tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path)

    result = materialize_claim_ledger(
        ledger,
        evidence={"result": {"status": "ready"}},
        repo_root=tmp_path,
    )

    assert result["numeric_authority"] == "parent_evidence_manifest_only"
    assert [claim["id"] for claim in result["claims"]] == ["test.empirical", "test.theorem"]
    assert result["claims"][0]["result"] == "ready"
    assert result["claims"][1]["result"] is None


def test_claim_ledger_rejects_failed_rule_or_missing_marker(tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path)
    with pytest.raises(RuntimeError, match="failed"):
        materialize_claim_ledger(
            ledger,
            evidence={"result": {"status": "not-ready"}},
            repo_root=tmp_path,
        )

    (tmp_path / "body.md").write_text("no marker\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing markers"):
        materialize_claim_ledger(
            ledger,
            evidence={"result": {"status": "ready"}},
            repo_root=tmp_path,
        )


def test_claim_ledger_rejects_numeric_expected_result(tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path, expected="1.5")
    text = ledger.read_text(encoding="utf-8").replace("expected: 1.5", "expected: 1.5")
    ledger.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicates a numeric result"):
        load_claim_ledger(ledger)


def test_json_pointer_handles_escaped_object_keys() -> None:
    document = {"a/b": {"tilde~key": False}}
    assert resolve_json_pointer(document, "/a~1b/tilde~0key") is False


def test_active_claim_ledger_matches_generated_evidence() -> None:
    root = Path(__file__).resolve().parents[2]
    evidence = json.loads(
        (root / "reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json").read_text(
            encoding="utf-8"
        )
    )

    expected = materialize_claim_ledger(
        root / "configs/ijds_claim_ledger.yaml",
        evidence=evidence,
        repo_root=root,
    )

    assert evidence["claim_ledger"] == expected
