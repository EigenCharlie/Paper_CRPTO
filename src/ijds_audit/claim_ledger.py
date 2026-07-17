"""Nonnumeric claim contracts bound to the single paper evidence manifest."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from src.utils.artifact_descriptor import relative_artifact_descriptor

ALLOWED_STATUSES = {"active", "pending", "retired"}
ALLOWED_KINDS = {"empirical", "theorem", "boundary"}
ALLOWED_RULES = {"equals", "documented"}


def _surface_registry(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise TypeError("Claim ledger must declare named surfaces.")
    if not all(isinstance(name, str) and isinstance(path, str) for name, path in value.items()):
        raise TypeError("Claim-ledger surfaces must map names to paths.")
    return {str(name): str(path) for name, path in value.items()}


def _validate_result_rule(claim: Mapping[str, Any], *, claim_id: str) -> None:
    source = claim.get("result_pointer")
    if claim["rule"] == "documented":
        if source is not None or "expected" in claim:
            raise ValueError(f"Documented claim {claim_id!r} cannot declare a result value.")
        return
    if not isinstance(source, str) or not source.startswith("/"):
        raise ValueError(f"Claim {claim_id!r} requires a JSON result pointer.")
    expected = claim.get("expected")
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        raise ValueError(f"Claim {claim_id!r} duplicates a numeric result.")
    if not isinstance(expected, (bool, str)) and expected is not None:
        raise TypeError(f"Claim {claim_id!r} has a nonportable expected value.")


def _claim_surface_contract(
    value: object,
    *,
    claim_id: str,
    known_surfaces: set[str],
) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        raise TypeError(f"Claim {claim_id!r} must declare surfaces.")
    contract: dict[str, list[str]] = {}
    for field in ("required", "allowed"):
        names = value.get(field)
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise TypeError(f"Claim {claim_id!r} surfaces.{field} must be a string list.")
        contract[field] = [str(name) for name in names]
        unknown = sorted(set(names).difference(known_surfaces))
        if unknown:
            raise ValueError(f"Claim {claim_id!r} references unknown surfaces: {unknown}.")
    if not set(contract["required"]).issubset(contract["allowed"]):
        raise ValueError(f"Claim {claim_id!r} requires a forbidden surface.")
    return contract


def _validated_claim(value: object, *, known_surfaces: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Every claim contract must be a mapping.")
    claim = dict(value)
    claim_id = claim.get("id")
    if not isinstance(claim_id, str) or not claim_id or not claim_id.isascii():
        raise TypeError("Claim IDs must be nonempty ASCII strings.")
    for field, allowed in (
        ("status", ALLOWED_STATUSES),
        ("kind", ALLOWED_KINDS),
        ("rule", ALLOWED_RULES),
    ):
        if claim.get(field) not in allowed:
            raise ValueError(f"Claim {claim_id!r} has an invalid {field}.")
    _validate_result_rule(claim, claim_id=claim_id)
    claim["surfaces"] = _claim_surface_contract(
        claim.get("surfaces"),
        claim_id=claim_id,
        known_surfaces=known_surfaces,
    )
    boundaries = claim.get("forbidden_inference")
    if not isinstance(boundaries, list) or not all(isinstance(item, str) for item in boundaries):
        raise TypeError(f"Claim {claim_id!r} needs forbidden-inference boundaries.")
    return claim


def load_claim_ledger(path: Path) -> dict[str, Any]:
    """Load and structurally validate a nonnumeric claim ledger."""
    raw_payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise TypeError("Claim ledger must be a mapping.")
    payload = dict(raw_payload)
    if payload.get("status") != "active_ijds_claim_contract":
        raise ValueError("Unexpected claim-ledger status.")
    surfaces = _surface_registry(payload.get("surfaces"))
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise TypeError("Claim ledger must contain claims.")
    claims = [_validated_claim(claim, known_surfaces=set(surfaces)) for claim in raw_claims]
    identifiers = [str(claim["id"]) for claim in claims]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Claim IDs must be globally unique.")
    payload["surfaces"] = surfaces
    payload["claims"] = claims
    return payload


def resolve_json_pointer(document: Mapping[str, Any], pointer: str) -> Any:
    """Resolve an RFC 6901 object pointer without array-index extensions."""
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must be empty or start with '/'.")
    current: Any = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, Mapping) or token not in current:
            raise KeyError(f"JSON pointer does not resolve: {pointer}.")
        current = current[token]
    return current


def materialize_claim_ledger(
    ledger_path: Path,
    *,
    evidence: Mapping[str, Any],
    repo_root: Path,
    check_surfaces: bool = True,
) -> dict[str, Any]:
    """Verify claim results and markers, returning a manifest-ready ledger."""
    ledger = load_claim_ledger(ledger_path)
    root = repo_root.resolve()
    surface_paths = {name: (root / path).resolve() for name, path in ledger["surfaces"].items()}
    for path in surface_paths.values():
        path.relative_to(root)
    surface_text = _read_surface_text(surface_paths) if check_surfaces else {}

    materialized = [
        _materialize_claim(
            claim,
            evidence=evidence,
            surface_text=surface_text,
            check_surfaces=check_surfaces,
        )
        for claim in ledger["claims"]
    ]
    return {
        "schema_version": str(ledger["schema_version"]),
        "status": str(ledger["status"]),
        "numeric_authority": "parent_evidence_manifest_only",
        "contract": relative_artifact_descriptor(ledger_path, repo_root=repo_root),
        "claims": materialized,
    }


def _read_surface_text(surface_paths: Mapping[str, Path]) -> dict[str, str]:
    text: dict[str, str] = {}
    for name, path in surface_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Claim surface {name!r} is missing: {path}.")
        text[name] = path.read_text(encoding="utf-8")
    return text


def _active_claim_result(claim: Mapping[str, Any], evidence: Mapping[str, Any]) -> Any:
    if claim["status"] != "active" or claim["rule"] != "equals":
        return None
    claim_id = str(claim["id"])
    result = resolve_json_pointer(evidence, str(claim["result_pointer"]))
    if isinstance(result, (int, float)) and not isinstance(result, bool):
        raise ValueError(f"Claim {claim_id!r} resolves to a duplicated numeric result.")
    if result != claim.get("expected"):
        raise RuntimeError(f"Claim {claim_id!r} failed: {result!r} != {claim.get('expected')!r}.")
    return result


def _check_surface_markers(claim: Mapping[str, Any], surface_text: Mapping[str, str]) -> None:
    if claim["status"] != "active":
        return
    claim_id = str(claim["id"])
    marker = f"claim:{claim_id}"
    required = set(claim["surfaces"]["required"])
    allowed = set(claim["surfaces"]["allowed"])
    missing = sorted(name for name in required if marker not in surface_text[name])
    forbidden = sorted(
        name for name, text in surface_text.items() if name not in allowed and marker in text
    )
    if missing:
        raise RuntimeError(f"Claim {claim_id!r} is missing markers on {missing}.")
    if forbidden:
        raise RuntimeError(f"Claim {claim_id!r} appears on forbidden surfaces {forbidden}.")


def _materialize_claim(
    claim: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any],
    surface_text: Mapping[str, str],
    check_surfaces: bool,
) -> dict[str, Any]:
    result = _active_claim_result(claim, evidence)
    if check_surfaces:
        _check_surface_markers(claim, surface_text)
    return {
        "id": str(claim["id"]),
        "status": str(claim["status"]),
        "kind": str(claim["kind"]),
        "lineages": list(claim.get("lineages", [])),
        "scope": str(claim.get("scope", "")),
        "rule": str(claim["rule"]),
        "result_pointer": claim.get("result_pointer"),
        "result": result if claim["status"] == "active" else None,
        "forbidden_inference": list(claim["forbidden_inference"]),
        "surfaces": dict(claim["surfaces"]),
    }


def claim_markers_from_manifest(evidence_path: Path) -> set[str]:
    """Return active claim markers from one generated evidence manifest."""
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    ledger = payload.get("claim_ledger", {})
    claims = ledger.get("claims", []) if isinstance(ledger, Mapping) else []
    return {
        f"claim:{claim['id']}"
        for claim in claims
        if isinstance(claim, Mapping) and claim.get("status") == "active"
    }
