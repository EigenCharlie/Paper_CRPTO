"""Historical integrity checks for the manifest-protected pool93 bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports" / "crpto" / "tables"
MANIFEST = REPO / "EXTRACTION_MANIFEST.json"
PROMOTION = REPO / "models" / "final_project_promotion.json"
TERMINAL_GOVERNANCE = (
    REPO
    / "models/experiments/champion_reopen"
    / "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal"
    / "portfolio/pool93_ijds_claim_governance.json"
)
CONSOLIDATED_GOVERNANCE = (
    REPO
    / "models/experiments/champion_reopen"
    / "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2"
    / "portfolio/pool93_ijds_consolidated_governance.json"
)
POOL93_TABLE_STEMS = (
    "crpto_tableA35_pool93_ijds_frontier",
    "crpto_tableA36_pool93_body_funded_grade_audit",
    "crpto_tableA37_pool93_body_tail_risk",
    "crpto_tableA38_pool93_body_cluster_bound_audit",
    "crpto_tableA39_pool93_body_bootstrap_metrics",
    "crpto_tableA40_pool93_point_baseline",
)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        pytest.skip(f"Historical artifact unavailable: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_historical_pool93_bundle_remains_internally_coherent() -> None:
    consolidated = _load(CONSOLIDATED_GOVERNANCE)
    terminal = _load(TERMINAL_GOVERNANCE)
    promotion = _load(PROMOTION)

    assert consolidated["counts"]["deduped_semantic_policies"] == 50_010
    assert consolidated["counts"]["eligible_all_alpha_return_floor_policies"] == 27_508
    assert terminal["runtime_status"]["total_checks"] == 296_544
    assert promotion["run_tag"] == "ijds-rebaseline-2026-06-07"
    assert terminal["claim_summary"]["declared_return_floor"] == pytest.approx(
        round(promotion["final_champion"]["realized_total_return"], 2)
    )


def test_historical_pool93_tables_remain_hash_protected() -> None:
    manifest = _load(MANIFEST)
    hashed = set(manifest["critical_hashes"])
    expected = {
        f"reports/crpto/tables/{stem}.{suffix}"
        for stem in POOL93_TABLE_STEMS
        for suffix in ("csv", "tex")
    }
    assert expected.issubset(hashed)
    assert all((TABLES / path.split("/")[-1]).is_file() for path in expected)
