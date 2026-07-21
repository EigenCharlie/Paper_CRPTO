"""Shared contract for artifacts required by the strict manifest gate."""

from __future__ import annotations

from collections.abc import Mapping

PROTECTED_CHAMPION_FILES = (
    "models/pd_canonical.cbm",
    "models/pd_canonical_calibrator.pkl",
    "models/final_project_promotion.json",
    "models/conformal_policy_status.json",
    "models/champion_portfolio_policy.json",
    "models/champion_registry.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal/"
    "portfolio/pool93_ijds_claim_governance.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/"
    "portfolio/pool93_ijds_consolidated_governance.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/"
    "portfolio/pool93_ijds_consolidated_frontier.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/"
    "portfolio/pool93_ijds_consolidated_governance.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/"
    "portfolio/pool93_point_pd_baseline_audit.json",
)

_FROZEN_PREFIXES = (
    "models/",
    "data/processed/",
    "reports/crpto/tables/",
)
_NON_REPRODUCIBLE_SUFFIXES = (".pdf",)
_ALLOWED_DRIFT = frozenset(
    {
        "models/crpto_evidence_status.json",
        "models/crpto_journal_package_status.json",
    }
)


def frozen_manifest_paths(critical_hashes: Mapping[str, object]) -> tuple[str, ...]:
    """Return manifest paths whose bytes must remain fixed when present."""
    selected: list[str] = []
    for rel_path, entry in critical_hashes.items():
        if not rel_path.startswith(_FROZEN_PREFIXES):
            continue
        if rel_path in _ALLOWED_DRIFT or rel_path.endswith(_NON_REPRODUCIBLE_SUFFIXES):
            continue
        if not isinstance(entry, Mapping) or not entry.get("sha256"):
            continue
        selected.append(rel_path)
    return tuple(selected)


def strict_manifest_paths(critical_hashes: Mapping[str, object]) -> tuple[str, ...]:
    """Return every artifact that a strict checkout must materialize."""
    return tuple(sorted({*PROTECTED_CHAMPION_FILES, *frozen_manifest_paths(critical_hashes)}))
