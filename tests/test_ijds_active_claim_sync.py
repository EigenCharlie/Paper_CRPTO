"""Drift guards for the active maturity-safe IJDS evidence and manuscripts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

import scripts.build_ijds_maturity_safe_evidence as evidence_builder

REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "reports/crpto/tables"
EVIDENCE = REPO / "reports/crpto/ijds_maturity_safe_evidence.json"
RUN_TAG = "champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2"
PROTOCOL_TAG = "protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2"
PROTOCOL_COMMIT = "78a64fe67a4df46c3d19b9243deb991c56fd1ff6"
SURFACES = (
    REPO / "paper/CRPTO_ijds.qmd",
    REPO / "paper/supplement_ijds.qmd",
    REPO / "paper/submission/CRPTO_ijds_submission.tex",
)


def _json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"Missing JSON evidence: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(stem: str) -> list[dict[str, str]]:
    with (TABLES / f"{stem}.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize(text: str) -> str:
    value = text.lower()
    replacements = {
        r"\$": "$",
        r"\%": "%",
        r"\_": "_",
        "{,}": ",",
        "{": "",
        "}": "",
        "`": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value)


def test_default_evidence_validation_does_not_require_the_raw_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = {
        "status": "complete",
        "run_tag": RUN_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "artifacts": {},
        "raw_source": {
            "path": "data/raw/not-present.csv",
            "bytes": 1,
            "sha256": "not-read-by-default",
        },
    }
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    clean_git = {"commit": PROTOCOL_COMMIT, "dirty": False}
    receipt = {
        "initial_git": clean_git,
        "final_git": clean_git,
        "deterministic_summary": {
            "bytes": summary_path.stat().st_size,
            "sha256": _sha256(summary_path),
        },
    }
    monkeypatch.setattr(evidence_builder, "ROOT", tmp_path)
    monkeypatch.setattr(evidence_builder, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(evidence_builder, "_verify_git_binding", lambda: None)

    evidence_builder._verify_run(summary, receipt, verify_raw=False)


def test_active_evidence_locks_clean_v2_protocol() -> None:
    evidence = _json(EVIDENCE)
    summary_path = REPO / evidence["summary"]["path"]
    receipt_path = REPO / evidence["receipt"]["path"]
    summary = _json(summary_path)
    receipt = _json(receipt_path)

    assert evidence["status"] == "active_maturity_safe_ijds_evidence"
    assert evidence["run_tag"] == RUN_TAG
    assert evidence["protocol_tag"] == PROTOCOL_TAG
    assert evidence["protocol_commit"] == PROTOCOL_COMMIT
    assert summary["status"] == "complete"
    assert summary["run_tag"] == RUN_TAG
    assert summary["protocol_tag"] == PROTOCOL_TAG
    assert summary["protocol_commit"] == PROTOCOL_COMMIT
    assert summary["protected_stages_run"] == []
    assert summary["protected_artifacts_written"] == []
    assert receipt["initial_git"]["dirty"] is False
    assert receipt["final_git"]["dirty"] is False
    assert _sha256(summary_path) == evidence["summary"]["sha256"]
    assert _sha256(receipt_path) == evidence["receipt"]["sha256"]


def test_active_policy_and_timing_are_not_post_oot_selected() -> None:
    evidence = _json(EVIDENCE)
    summary = _json(REPO / evidence["summary"]["path"])
    selected = summary["selection"]["selected_guardrail"]

    assert summary["row_counts"]["universe"] == 540121
    assert summary["row_counts"]["primary_oot"] == 376890
    assert summary["row_counts"]["primary_oot_months"] == 15
    assert summary["selection"]["period"] == "2012-07_to_2012-12"
    assert summary["selection"]["primary_or_extension_outcomes_used"] is False
    assert summary["selection"]["endpoint_cap_used"] is False
    assert selected["candidate_id"] == "linear-004"
    assert selected["risk_tolerance"] == pytest.approx(0.17)
    assert selected["gamma"] == pytest.approx(0.25)
    assert summary["payoff"]["id"] == "coherent_standardized_binary_payoff_v1"
    assert summary["payoff"]["lgd"] == pytest.approx(0.45)


def test_active_tables_agree_with_summary() -> None:
    evidence = _json(EVIDENCE)
    summary = _json(REPO / evidence["summary"]["path"])
    primary = summary["monthly_evaluation"]["aggregate_by_role_and_policy"]
    guard_summary = next(
        row
        for row in primary
        if row["role"] == "primary_oot" and row["policy_label"] == "selected_conformal_guardrail"
    )
    point_summary = next(
        row
        for row in primary
        if row["role"] == "primary_oot" and row["policy_label"] == "matched_point_pd"
    )
    policy_rows = _rows("crpto_ijds_ms_table2_primary_policy")
    guard_table = next(row for row in policy_rows if row["policy"] == "Conformal guardrail")
    point_table = next(row for row in policy_rows if row["policy"] == "Point PD, matched tau")

    for table_row, summary_row in ((guard_table, guard_summary), (point_table, point_summary)):
        for field in (
            "expected_objective",
            "realized_payoff_lower",
            "realized_payoff_upper",
            "weighted_default_lower",
            "weighted_default_upper",
            "weighted_miscoverage_lower",
            "weighted_miscoverage_upper",
            "unresolved_exposure_share",
        ):
            assert float(table_row[field]) == pytest.approx(summary_row[field])

    coverage = _rows("crpto_ijds_ms_tableS2_coverage")
    primary_coverage = next(row for row in coverage if row["block"].startswith("primary_oot"))
    conformal = summary["conformal"]["primary_oot_all_candidate_pooled"]
    assert float(primary_coverage["coverage_lower"]) == pytest.approx(
        conformal["all_candidate_coverage_lower"]
    )
    assert float(primary_coverage["coverage_upper"]) == pytest.approx(
        conformal["all_candidate_coverage_upper"]
    )


def test_primary_contrast_is_sharp_sign_robust_and_noncausal() -> None:
    rows = _rows("crpto_ijds_ms_table3_primary_contrast")
    matched = next(row for row in rows if row["policy_b"] == "matched_point_pd")

    assert float(matched["realized_payoff_difference_lower"]) == pytest.approx(-322703.787478)
    assert float(matched["realized_payoff_difference_upper"]) == pytest.approx(-58040.339247)
    assert float(matched["weighted_default_difference_lower"]) == pytest.approx(-0.046274834615)
    assert float(matched["weighted_default_difference_upper"]) == pytest.approx(-0.020093094595)
    assert float(matched["weighted_miscoverage_difference_lower"]) == pytest.approx(0.008821832051)
    assert float(matched["weighted_miscoverage_difference_upper"]) == pytest.approx(0.029850238738)
    assert matched["payoff_direction_sign_robust"] == "True"
    assert matched["default_direction_sign_robust"] == "True"
    assert matched["miscoverage_direction_sign_robust"] == "True"
    assert matched["causal_interpretation"] == "False"


def test_development_success_reverses_out_of_time() -> None:
    evidence = _json(EVIDENCE)
    rows = _rows("crpto_ijds_ms_table4_development_to_oot")
    development = next(row for row in rows if row["block"] == "policy_development_2012H2")
    primary = next(row for row in rows if row["block"].startswith("locked_primary"))
    headline = evidence["headline"]["development_to_oot"]

    assert headline[0]["block"] == development["block"]
    assert headline[1]["block"] == primary["block"]
    assert float(development["expected_payoff_difference"]) == pytest.approx(-72701.673353)
    assert float(development["realized_payoff_difference_lower"]) == pytest.approx(50260.10081)
    assert float(development["weighted_default_difference_lower"]) == pytest.approx(-0.063802154704)
    assert float(development["weighted_miscoverage_difference_lower"]) == pytest.approx(
        -0.007358371111
    )
    assert float(primary["realized_payoff_difference_upper"]) < 0.0
    assert float(primary["expected_payoff_difference"]) == pytest.approx(-240977.778623)
    assert float(primary["weighted_default_difference_upper"]) < 0.0
    assert float(primary["weighted_miscoverage_difference_lower"]) > 0.0


def test_evidence_manifest_hashes_every_publication_output() -> None:
    evidence = _json(EVIDENCE)
    paths = {item["path"] for item in evidence["outputs"]}
    required = {
        "reports/crpto/tables/crpto_ijds_ms_table1_protocol.csv",
        "reports/crpto/tables/crpto_ijds_ms_table2_primary_policy.csv",
        "reports/crpto/tables/crpto_ijds_ms_table3_primary_contrast.csv",
        "reports/crpto/tables/crpto_ijds_ms_table4_development_to_oot.csv",
        *{
            f"reports/crpto/tables/crpto_ijds_ms_tableS{i}_{suffix}.csv"
            for i, suffix in (
                (1, "selection_grid"),
                (2, "coverage"),
                (3, "monthly_primary"),
                (4, "transport"),
                (5, "group_exposure"),
                (6, "extension"),
                (7, "monthly_contrast"),
            )
        },
        "reports/crpto/figures/crpto_ijds_ms_fig0_pipeline.pdf",
        "reports/crpto/figures/crpto_ijds_ms_fig1_timeline.pdf",
        "reports/crpto/figures/crpto_ijds_ms_fig2_monthly.pdf",
        "reports/crpto/figures/crpto_ijds_ms_fig3_transport.pdf",
    }
    assert required <= paths
    for item in evidence["outputs"]:
        path = REPO / item["path"]
        assert path.is_file(), path
        assert path.stat().st_size == item["bytes"]
        assert _sha256(path) == item["sha256"]


def test_active_manuscript_surfaces_share_numeric_and_narrative_anchors() -> None:
    anchors = (
        "540,121",
        "0.854923",
        "0.879692",
        "0.020093",
        "0.046275",
        "0.008822",
        "0.029850",
        "$50,260.10",
        "$72,701.67",
        "$58,040",
        "$322,703.79",
        "0.611338",
        "within-group",
        "standardized payoff",
        "latent",
        "development-to-oot",
    )
    for surface in SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        missing = [_normalize(anchor) for anchor in anchors if _normalize(anchor) not in text]
        assert not missing, f"{surface.name} missing active anchors: {missing}"


def test_body_sources_retain_recovered_ijds_argument() -> None:
    anchors = (
        "closest-work boundary",
        "identification and theory",
        "development success does not transport",
        "managerial audit card",
    )
    for surface in (SURFACES[0], SURFACES[2]):
        text = _normalize(surface.read_text(encoding="utf-8"))
        missing = [_normalize(anchor) for anchor in anchors if _normalize(anchor) not in text]
        assert not missing, f"{surface.name} missing recovered argument: {missing}"


def test_body_and_official_share_section_architecture() -> None:
    sections = (
        "Introduction",
        "Related Work",
        "Data and Locked Evaluation Design",
        "Method",
        "Identification and Theory",
        "Results",
        "Discussion",
        "Limitations",
        "Reproducibility",
        "Conclusion",
    )
    body = SURFACES[0].read_text(encoding="utf-8")
    official = SURFACES[2].read_text(encoding="utf-8")
    assert "# Abstract {.unnumbered}" in body
    body_matches = [
        re.search(rf"(?m)^# {re.escape(section)}(?:\s|$)", body) for section in sections
    ]
    assert all(match is not None for match in body_matches)
    body_positions = [match.start() for match in body_matches if match is not None]
    official_positions = [official.index(rf"\section{{{section}}}") for section in sections]
    assert body_positions == sorted(body_positions)
    assert official_positions == sorted(official_positions)


def test_body_and_official_share_citations_and_display_counts() -> None:
    body = SURFACES[0].read_text(encoding="utf-8")
    official = SURFACES[2].read_text(encoding="utf-8")
    body_citations = {
        key
        for key in re.findall(r"@([A-Za-z0-9_:-]+)", body)
        if not key.startswith(("fig-", "tbl-", "eq-", "sec-"))
    }
    official_citations: set[str] = set()
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", official):
        official_citations.update(key.strip() for key in group.split(","))

    assert body_citations == official_citations
    assert len(body_citations) == 41
    assert body.count("{#tbl-") == 10
    assert body.count("{#fig-") == 4
    assert official.count(r"\begin{table}") == 10
    assert official.count(r"\begin{figure}") == 4


def test_compact_v7_headlines_cannot_reenter_active_surfaces() -> None:
    retired = (
        "champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7",
        "$179,327.59",
        "276,869",
        "0.039375",
        "0.036875",
        "0.258051",
        "0.574279",
        "$196,369.14",
        "8.678%",
        "7.9025",
    )
    for surface in SURFACES:
        text = _normalize(surface.read_text(encoding="utf-8"))
        present = [_normalize(token) for token in retired if _normalize(token) in text]
        assert not present, f"{surface.name} retains compact-v7 claims: {present}"
