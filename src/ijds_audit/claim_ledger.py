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


def load_claim_ledger(path: Path) -> dict[str, Any]:
    """Load and structurally validate a nonnumeric claim ledger."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Claim ledger must be a mapping.")
    if payload.get("status") != "active_ijds_claim_contract":
        raise ValueError("Unexpected claim-ledger status.")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, Mapping) or not surfaces:
        raise TypeError("Claim ledger must declare named surfaces.")
    if not all(
        isinstance(name, str) and isinstance(value, str) for name, value in surfaces.items()
    ):
        raise TypeError("Claim-ledger surfaces must map names to paths.")
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise TypeError("Claim ledger must contain claims.")
    identifiers: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            raise TypeError("Every claim contract must be a mapping.")
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id or not claim_id.isascii():
            raise TypeError("Claim IDs must be nonempty ASCII strings.")
        identifiers.append(claim_id)
        if claim.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"Claim {claim_id!r} has an invalid status.")
        if claim.get("kind") not in ALLOWED_KINDS:
            raise ValueError(f"Claim {claim_id!r} has an invalid kind.")
        if claim.get("rule") not in ALLOWED_RULES:
            raise ValueError(f"Claim {claim_id!r} has an invalid rule.")
        source = claim.get("result_pointer")
        if claim["rule"] == "equals":
            if not isinstance(source, str) or not source.startswith("/"):
                raise ValueError(f"Claim {claim_id!r} requires a JSON result pointer.")
            expected = claim.get("expected")
            if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                raise ValueError(f"Claim {claim_id!r} duplicates a numeric result.")
            if not isinstance(expected, (bool, str)) and expected is not None:
                raise TypeError(f"Claim {claim_id!r} has a nonportable expected value.")
        elif source is not None or "expected" in claim:
            raise ValueError(f"Documented claim {claim_id!r} cannot declare a result value.")
        claim_surfaces = claim.get("surfaces")
        if not isinstance(claim_surfaces, Mapping):
            raise TypeError(f"Claim {claim_id!r} must declare surfaces.")
        for field in ("required", "allowed"):
            names = claim_surfaces.get(field)
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise TypeError(f"Claim {claim_id!r} surfaces.{field} must be a string list.")
            unknown = sorted(set(names).difference(surfaces))
            if unknown:
                raise ValueError(f"Claim {claim_id!r} references unknown surfaces: {unknown}.")
        if not set(claim_surfaces["required"]).issubset(claim_surfaces["allowed"]):
            raise ValueError(f"Claim {claim_id!r} requires a forbidden surface.")
        boundaries = claim.get("forbidden_inference")
        if not isinstance(boundaries, list) or not all(
            isinstance(item, str) for item in boundaries
        ):
            raise TypeError(f"Claim {claim_id!r} needs forbidden-inference boundaries.")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Claim IDs must be globally unique.")
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
    surface_paths = {
        str(name): (repo_root / str(path)).resolve() for name, path in ledger["surfaces"].items()
    }
    for path in surface_paths.values():
        path.relative_to(repo_root.resolve())
    surface_text: dict[str, str] = {}
    if check_surfaces:
        for name, path in surface_paths.items():
            if not path.is_file():
                raise FileNotFoundError(f"Claim surface {name!r} is missing: {path}.")
            surface_text[name] = path.read_text(encoding="utf-8")

    materialized: list[dict[str, Any]] = []
    for raw_claim in ledger["claims"]:
        claim = dict(raw_claim)
        claim_id = str(claim["id"])
        result: Any = None
        if claim["rule"] == "equals" and claim["status"] == "active":
            result = resolve_json_pointer(evidence, str(claim["result_pointer"]))
            if isinstance(result, (int, float)) and not isinstance(result, bool):
                raise ValueError(f"Claim {claim_id!r} resolves to a duplicated numeric result.")
            if result != claim.get("expected"):
                raise RuntimeError(
                    f"Claim {claim_id!r} failed: {result!r} != {claim.get('expected')!r}."
                )
        marker = f"claim:{claim_id}"
        if check_surfaces and claim["status"] == "active":
            required = set(claim["surfaces"]["required"])
            allowed = set(claim["surfaces"]["allowed"])
            missing = sorted(name for name in required if marker not in surface_text[name])
            forbidden = sorted(
                name
                for name, text in surface_text.items()
                if name not in allowed and marker in text
            )
            if missing:
                raise RuntimeError(f"Claim {claim_id!r} is missing markers on {missing}.")
            if forbidden:
                raise RuntimeError(f"Claim {claim_id!r} appears on forbidden surfaces {forbidden}.")
        materialized.append(
            {
                "id": claim_id,
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
        )
    return {
        "schema_version": str(ledger["schema_version"]),
        "status": str(ledger["status"]),
        "numeric_authority": "parent_evidence_manifest_only",
        "contract": relative_artifact_descriptor(ledger_path, repo_root=repo_root),
        "claims": materialized,
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
