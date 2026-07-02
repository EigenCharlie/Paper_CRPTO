"""Drift guard for the promoted pool93 IJDS body claim.

The paper body point (A35 "Body/default balanced point") lives in the pool93
governance sidecars and the A35-A39 tables, all generated outside the DVC DAG
by the champion-reopen experiment scripts. The IJDS manuscript embeds those
numbers as hand-written prose/Markdown, so a regenerated CSV or a retyped
figure can silently desync the submission from its evidence. These tests lock
the two-tag scheme together: the frozen rebaseline chain stays the declared
return floor, and the pool93 governance JSONs stay the authoritative source
for every body-claim number printed in the paper surfaces.

Only anchor values are checked -- enough to catch a stale copy/paste, without
re-implementing a Markdown table parser.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports" / "crpto" / "tables"

PAPER = REPO / "paper" / "CRPTO_ijds.qmd"
SUPPLEMENT = REPO / "paper" / "supplement_ijds.qmd"

TERMINAL_GOVERNANCE = (
    REPO
    / "models"
    / "experiments"
    / "champion_reopen"
    / "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal"
    / "portfolio"
    / "pool93_ijds_claim_governance.json"
)
CONSOLIDATED_GOVERNANCE = (
    REPO
    / "models"
    / "experiments"
    / "champion_reopen"
    / "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive"
    / "portfolio"
    / "pool93_ijds_consolidated_governance.json"
)
PROMOTION = REPO / "models" / "final_project_promotion.json"
MANIFEST = REPO / "EXTRACTION_MANIFEST.json"

POOL93_TABLE_STEMS = (
    "crpto_tableA35_pool93_ijds_frontier",
    "crpto_tableA36_pool93_body_funded_grade_audit",
    "crpto_tableA37_pool93_body_tail_risk",
    "crpto_tableA38_pool93_body_cluster_bound_audit",
    "crpto_tableA39_pool93_body_bootstrap_metrics",
)

TERMINAL_RUN_TAG = "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal"
REBASELINE_RUN_TAG = "ijds-rebaseline-2026-06-07"

EXPECTED_BODY = {
    "return": 184832.475845,
    "Gamma_CP": 0.162616,
    "V": 0.03535,
    "Markov_cap": 0.34508374,
    "endpoint_budget_upper": 0.24508374,
    "risk_tolerance": 0.1715,
    "gamma": 0.5475,
    "uncertainty_aversion": 0.05,
    "alpha_pass": "8/8",
}
EXPECTED_FLOOR = 170464.54
EXPECTED_FROZEN_RETURN = 170464.5429284627
EXPECTED_FRONTIER_COUNTS = {
    "raw_rows": 51678,
    "deduped_semantic_policies": 50010,
    "eligible_all_alpha_return_floor_policies": 27508,
}
EXPECTED_TERMINAL_COUNTS = {
    "n_policies": 37068,
    "n_all_alpha_passers": 37068,
    "n_all_alpha_passers_above_return_floor": 14814,
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        pytest.skip(f"{path.name} not present locally.")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rows(name: str) -> list[dict[str, str]]:
    path = TABLES / name
    if not path.is_file():
        pytest.skip(f"{name} not present locally.")
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _text(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path} not present locally.")
    return path.read_text(encoding="utf-8")


def _body_row_a35() -> dict[str, str]:
    rows = _read_rows("crpto_tableA35_pool93_ijds_frontier.csv")
    matches = [r for r in rows if r["role"] == "Body/default balanced point"]
    assert len(matches) == 1, "A35 must expose exactly one body/default balanced row"
    return matches[0]


def test_pool93_claim_governance_matches_expected_body_point() -> None:
    """Consolidated governance body point and A35 body row agree with the claim."""
    consolidated = _load_json(CONSOLIDATED_GOVERNANCE)
    body = consolidated["selected_candidates"]["paper_body"]
    assert body["return"] == pytest.approx(EXPECTED_BODY["return"], abs=1e-6)
    assert body["Gamma_CP"] == pytest.approx(EXPECTED_BODY["Gamma_CP"], abs=1e-9)
    assert body["V"] == pytest.approx(EXPECTED_BODY["V"], abs=1e-9)
    assert body["Markov_cap"] == pytest.approx(EXPECTED_BODY["Markov_cap"], abs=1e-9)
    assert body["endpoint_budget_upper"] == pytest.approx(
        EXPECTED_BODY["endpoint_budget_upper"], abs=1e-9
    )
    assert body["risk_tolerance"] == EXPECTED_BODY["risk_tolerance"]
    assert body["gamma"] == EXPECTED_BODY["gamma"]
    assert body["uncertainty_aversion"] == EXPECTED_BODY["uncertainty_aversion"]
    assert body["alpha_pass"] == EXPECTED_BODY["alpha_pass"]

    terminal = _load_json(TERMINAL_GOVERNANCE)
    assert terminal["run_tag"] == TERMINAL_RUN_TAG
    summary = terminal["claim_summary"]
    assert summary["declared_return_floor"] == EXPECTED_FLOOR
    assert summary["finite_grid_policy"]["alpha_grid_size"] == 8

    row = _body_row_a35()
    assert float(row["realized_return"]) == pytest.approx(body["return"], abs=1e-6)
    assert float(row["Gamma_CP_alpha01"]) == pytest.approx(body["Gamma_CP"], abs=1e-9)
    assert float(row["V_alpha01"]) == pytest.approx(body["V"], abs=1e-9)
    assert float(row["Markov_cap_alpha01"]) == pytest.approx(body["Markov_cap"], abs=1e-9)
    assert row["alpha_grid_pass"] == body["alpha_pass"]


def test_pool93_consolidated_governance_frontier_counts() -> None:
    """Frontier and terminal-search counts quoted in the paper match governance."""
    consolidated = _load_json(CONSOLIDATED_GOVERNANCE)
    for key, expected in EXPECTED_FRONTIER_COUNTS.items():
        assert consolidated["counts"][key] == expected, key

    terminal = _load_json(TERMINAL_GOVERNANCE)
    counts = terminal["claim_hierarchy"]["current_counts"]
    for key, expected in EXPECTED_TERMINAL_COUNTS.items():
        assert counts[key] == expected, key
    assert terminal["runtime_status"]["total_checks"] == 296544


def test_pool93_tables_exist() -> None:
    """A35-A39 evidence tables exist in both CSV and TEX form."""
    missing = [
        f"{stem}.{ext}"
        for stem in POOL93_TABLE_STEMS
        for ext in ("csv", "tex")
        if not (TABLES / f"{stem}.{ext}").is_file()
    ]
    assert not missing, "pool93 evidence tables missing: " + ", ".join(missing)


def test_pool93_paper_anchors_match_csvs() -> None:
    """Body-claim numbers printed in the paper surfaces derive from A35/A39."""
    row = _body_row_a35()
    budget = float(row["endpoint_budget_upper_alpha01"])
    deterministic_bound = budget + float(row["V_alpha01"])
    paper_anchors = [
        f"${float(row['realized_return']):,.2f}",
        f"{float(row['V_alpha01']):.6f}",
        f"{float(row['Gamma_CP_alpha01']):.6f}",
        f"{float(row['Markov_cap_alpha01']):.6f}",
        f"{budget:.6f}",
        f"{deterministic_bound:.6f}",
    ]

    boot = {r["metric"]: r for r in _read_rows("crpto_tableA39_pool93_body_bootstrap_metrics.csv")}
    return_boot = boot["funded_set_repriced_return_lgd45"]
    supplement_anchors = [
        *paper_anchors,
        f"${float(return_boot['boot_p025']):,.2f}",
        f"${float(return_boot['boot_p975']):,.2f}",
    ]

    missing: list[str] = []
    paper_text = _text(PAPER)
    missing.extend(f"{a} missing in {PAPER.name}" for a in paper_anchors if a not in paper_text)
    supplement_text = _text(SUPPLEMENT)
    missing.extend(
        f"{a} missing in {SUPPLEMENT.name}" for a in supplement_anchors if a not in supplement_text
    )
    assert not missing, "pool93 body-claim drift:\n" + "\n".join(missing)


def test_pool93_two_tag_scheme_is_coherent() -> None:
    """The frozen rebaseline chain stays the declared return floor for pool93."""
    promotion = _load_json(PROMOTION)
    assert promotion["run_tag"] == REBASELINE_RUN_TAG
    frozen_return = promotion["final_champion"]["realized_total_return"]
    assert frozen_return == pytest.approx(EXPECTED_FROZEN_RETURN, abs=1e-6)

    terminal = _load_json(TERMINAL_GOVERNANCE)
    floor = terminal["claim_summary"]["declared_return_floor"]
    assert floor == pytest.approx(round(frozen_return, 2), abs=1e-9)


def test_pool93_manifest_block_agrees() -> None:
    """EXTRACTION_MANIFEST pool93 block mirrors the governance sidecars."""
    manifest = _load_json(MANIFEST)
    block = manifest.get("pool93_ijds_promotion")
    if block is None:
        pytest.skip("pool93_ijds_promotion block not yet added to EXTRACTION_MANIFEST.json.")

    consolidated = _load_json(CONSOLIDATED_GOVERNANCE)
    body = consolidated["selected_candidates"]["paper_body"]
    point = block["paper_body_point"]
    assert block["terminal_run_tag"] == TERMINAL_RUN_TAG
    assert point["realized_total_return"] == pytest.approx(body["return"], abs=1e-6)
    assert point["alpha01_gamma_cp"] == pytest.approx(body["Gamma_CP"], abs=1e-9)
    assert point["alpha01_weighted_miscoverage_V"] == pytest.approx(body["V"], abs=1e-9)
    assert point["markov_cap_alpha01"] == pytest.approx(body["Markov_cap"], abs=1e-9)
    assert point["declared_return_floor"] == EXPECTED_FLOOR
    assert (
        block["frontier_counts"]["deduped_semantic_policies"]
        == (EXPECTED_FRONTIER_COUNTS["deduped_semantic_policies"])
    )

    hashed = set(manifest["critical_hashes"])
    missing = [
        f"reports/crpto/tables/{stem}.{ext}"
        for stem in POOL93_TABLE_STEMS
        for ext in ("csv", "tex")
        if f"reports/crpto/tables/{stem}.{ext}" not in hashed
    ]
    assert not missing, "pool93 tables not hash-protected: " + ", ".join(missing)
