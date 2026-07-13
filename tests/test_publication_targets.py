from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _config() -> dict:
    return yaml.safe_load(
        Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8")
    )


def test_publication_target_points_to_active_sources() -> None:
    cfg = _config()
    primary = cfg["primary_target"]
    active = cfg["active_scientific_contract"]

    assert cfg["version"] == "2026-07-13"
    assert cfg["decision_status"] == "reconstructed_active"
    assert primary["id"] == "informs_ijds"
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"
    for key in ("manuscript_source", "supplement_source", "official_tex_source"):
        assert Path(primary[key]).is_file()
    assert Path(active["claim_registry"]).is_file()
    assert Path(active["evidence_manifest"]).is_file()


def test_publication_target_urls_are_official_https() -> None:
    cfg = _config()
    targets = [cfg["primary_target"], *cfg["secondary_targets"]]
    for target in targets:
        for url in target["official_urls"].values():
            assert url.startswith("https://"), (target["id"], url)


def test_ijds_sources_are_anonymous_by_default() -> None:
    for path in (Path("paper/CRPTO_ijds.qmd"), Path("paper/supplement_ijds.qmd")):
        text = path.read_text(encoding="utf-8")
        assert 'author: "Anonymous"' in text
        assert "Carlos Alfredo Vergara Rojas" not in text
        assert "cavr94@gmail.com" not in text
    tex = Path("paper/submission/CRPTO_ijds_submission.tex").read_text(encoding="utf-8")
    assert r"\documentclass[ijds,dblanonrev]{informs4}" in tex
    assert r"\ACKNOWLEDGMENT" not in tex
    assert "Carlos Alfredo Vergara Rojas" not in tex
    title_template = Path("paper/submission/TITLE_PAGE_DRAFT.md").read_text(encoding="utf-8")
    assert "Carlos Alfredo Vergara Rojas" not in title_template
    assert "cavr94@gmail.com" not in title_template
    cover_template = Path("paper/submission/COVER_LETTER_AND_DISCLOSURE.md").read_text(
        encoding="utf-8"
    )
    assert "Carlos Alfredo Vergara Rojas" not in cover_template
    assert "cavr94@gmail.com" not in cover_template


def test_active_contract_is_small_complete_and_numerically_locked() -> None:
    active = _config()["active_scientific_contract"]
    assert active["outcome_free_run_tag"].endswith("2026-07-12-v1")
    assert active["run_tag"].endswith("2026-07-12-v2")
    assert active["two_ruler_outcome_free_run_tag"].endswith("2026-07-13-v1c")
    assert active["two_ruler_run_tag"].endswith("2026-07-13-v2")
    assert active["credit_control_outcome_free_run_tag"].endswith("2026-07-13-v1b")
    assert active["credit_control_run_tag"].endswith("2026-07-13-v2b")
    assert active["previously_inspected_retrospective_archive"] is True
    assert active["confirmatory"] is False
    assert active["prospective"] is False
    assert active["policy_winner_allowed"] is False
    assert "complete gamma path" in active["method"]["decision_diagnostic"].lower()
    assert "nine fixed-cap policies" in active["method"]["comparator"].lower()
    assert "basis endpoints" in active["method"]["comparator"].lower()
    headline = active["headline"]
    assert headline["primary_candidates"] == 376890
    assert headline["primary_resolved"] == 365339
    assert headline["primary_unresolved"] == 11551
    assert headline["residual_windows"] == 8
    assert headline["learners"] == 5
    assert headline["v4_detailed_coverage_learners"] == 2
    assert headline["portfolio_learners"] == 1
    assert headline["catboost_coverage_bounds"] == pytest.approx([0.838531, 0.882167])
    assert headline["logistic_coverage_bounds"] == pytest.approx([0.845687, 0.895654])
    assert headline["monotonic_catboost_coverage_bounds"] == pytest.approx([0.844050, 0.885991])
    assert headline["platform_woe_coverage_bounds"] == pytest.approx([0.844199, 0.894317])
    assert headline["borrower_woe_coverage_bounds"] == pytest.approx([0.846849, 0.896973])
    assert headline["all_five_all_eight_upper_below_nominal"] is True
    assert headline["raw_archive"] == {
        "rows": 2925493,
        "valid_loans": 2925492,
        "term36_rows": 2060077,
        "term60_rows": 865415,
        "active_design_rows": 640543,
        "raw_columns": 142,
        "eligible_raw_features": 28,
        "late_schema_features": 48,
    }
    assert headline["phase_transition"] == pytest.approx(
        {
            "stratum": 2,
            "w7_prevalence": 0.101703,
            "w8_prevalence": 0.097147,
            "w7_quantile": 0.888435,
            "w8_quantile": 0.111801,
            "w7_width": 0.984263,
            "w8_width": 0.207631,
        }
    )
    two_ruler = headline["two_ruler"]
    assert two_ruler["solves"] == 6240
    assert two_ruler["funded_rows"] == 622455
    assert two_ruler["tracks"] == 6
    assert two_ruler["window_cells"] == 48
    assert two_ruler["coordinates"] == pytest.approx([0.25, 0.50, 0.75])
    assert two_ruler["objective_matched_025_payoff_usd"] == pytest.approx(5603.66)
    assert two_ruler["objective_matched_025_changed_loan_month_positions"] == 44
    assert two_ruler["objective_matched_025_one_way_turnover_usd"] == pytest.approx(155937.27)
    assert two_ruler["policy_winner_allowed"] is False
    assert headline["c2_cells"] == 1080
    assert headline["c2_maximum_match_residual"] < 1e-16
    assert headline["exact_frontier_caps"] == 3067
    assert headline["development_support_hull"] == pytest.approx([0.055573, 0.099997])
    assert headline["broad_stress_envelopes_crossing_zero"] == 216
    assert headline["development_default_envelopes_crossing_zero"] == 72
    assert headline["w8_development_envelopes_crossing_zero"] == 27
    assert headline["simulation_repetitions"] == 19200
    assert headline["universal_policy_direction_allowed"] is False
    assert len(active["required_artifacts"]) == 17
    for artifact in active["required_artifacts"]:
        assert Path(artifact).is_file(), artifact
    assert len(active["dvc_pointers"]) == 12
    for pointer in active["dvc_pointers"]:
        assert Path(pointer).is_file(), pointer

    code_surface = active["active_code_surface"]
    assert code_surface["historical_execution_in_active_capsule"] is False
    for group in (
        "paper_pipeline",
        "immutable_protocol_entrypoints",
        "source_inventory_manifests",
    ):
        for path in code_surface[group]:
            assert Path(path).is_file(), path


def test_historical_diagnostics_are_explicitly_outside_active_evidence() -> None:
    historical = _config()["historical_boundary"]
    assert historical["compact_v7_status"] == "git_history_only"
    assert historical["diagnostics_status"] == "git_history_only"
    text = " ".join(historical["diagnostics"])
    assert "A1--A24" in text
    assert "A25--A34" in text
    assert "A35--A40" in text
    assert "cannot validate" in historical["rule"]
