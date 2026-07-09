from __future__ import annotations

from pathlib import Path

import yaml


def test_publication_target_config_points_to_existing_sources() -> None:
    cfg = yaml.safe_load(Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8"))

    primary = cfg["primary_target"]
    assert primary["id"] == "informs_ijds"
    assert cfg["current_decision"]["write_first_for"] == "informs_ijds"
    assert cfg["current_decision"]["keep_second_ready_for"] == "ejor"

    assert Path(primary["manuscript_source"]).exists()
    assert Path(primary["supplement_source"]).exists()

    strategy = Path("docs/research/crpto_publication_strategy_2026-05-12.md")
    assert strategy.exists()


def test_publication_target_urls_are_official_https() -> None:
    cfg = yaml.safe_load(Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8"))

    targets = [cfg["primary_target"], *cfg["secondary_targets"]]
    for target in targets:
        for url in target["official_urls"].values():
            assert url.startswith("https://"), (target["id"], url)


def test_ijds_sources_are_anonymous_by_default() -> None:
    paths = [Path("paper/CRPTO_ijds.qmd"), Path("paper/supplement_ijds.qmd")]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert 'author: "Anonymous"' in text
        assert "Carlos Alfredo Vergara Rojas" not in text
        assert "TODO(manuscript)" not in text


def test_journal_strengthening_pack_classifies_current_and_backlog_items() -> None:
    cfg = yaml.safe_load(Path("configs/crpto_publication_targets.yaml").read_text(encoding="utf-8"))
    boundary = cfg["current_decision"]["p2_p3_boundary"]
    pack = cfg["journal_strengthening_pack"]
    included = pack["include_in_current_submission"]
    backlog = pack["backlog_not_blocking"]

    assert "no longer a blanket exclusion" in boundary
    assert "outside the submitted claim" in boundary
    assert "not acceptance criteria" in boundary
    assert set(included) == {
        "regret_auditability_frontier",
        "tail_risk_oce_cvar_diagnostic",
        "pool93_frontier_and_selected_allocation",
        "matched_point_pd_baseline",
        "robust_satisficing_margins",
        "dependence_aware_bound",
        "tail_satisficing_challenger_audit",
        "tail_constrained_reoptimization",
        "distribution_online_diagnostics",
        "multidataset_external_replication",
    }
    assert included["regret_auditability_frontier"]["status"] == "include_body"
    assert included["tail_risk_oce_cvar_diagnostic"]["status"] == "include_supplement"
    assert included["pool93_frontier_and_selected_allocation"]["status"] == (
        "include_body_and_supplement"
    )
    assert included["matched_point_pd_baseline"]["status"] == ("include_body_and_supplement")
    assert included["robust_satisficing_margins"]["status"] == ("include_supplement_or_short_body")
    assert included["dependence_aware_bound"]["status"] == "include_theory_appendix_or_caveat"
    assert included["tail_satisficing_challenger_audit"]["status"] == "include_supplement"
    assert included["tail_constrained_reoptimization"]["status"] == "include_supplement"
    assert included["distribution_online_diagnostics"]["status"] == "include_supplement"
    assert included["multidataset_external_replication"]["status"] == (
        "include_supplement_or_short_body"
    )
    pool93_artifacts = included["pool93_frontier_and_selected_allocation"]["artifacts"]
    assert "reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv" in pool93_artifacts
    assert "reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.csv" in (
        pool93_artifacts
    )
    assert "reports/crpto/tables/crpto_tableA40_pool93_point_baseline.csv" in (pool93_artifacts)
    for artifact in pool93_artifacts:
        assert Path(artifact).exists(), artifact
    multidataset_artifacts = included["multidataset_external_replication"]["artifacts"]
    assert "reports/crpto/tables/crpto_tableA28_external_lp_exhaustiveness.csv" in (
        multidataset_artifacts
    )
    assert "reports/crpto/tables/crpto_tableA33_freddie_segment_sensitivity.csv" in (
        multidataset_artifacts
    )
    assert "reports/crpto/figures/crpto_fig24_freddie_all_candidate_certificate.png" in (
        multidataset_artifacts
    )
    for artifact in multidataset_artifacts:
        assert Path(artifact).exists(), artifact
    assert backlog["prospective_multidataset_validation"]["status"] == (
        "future_protocol_not_blocker"
    )

    body = Path("paper/CRPTO_ijds.qmd").read_text(encoding="utf-8")
    supplement = Path("paper/supplement_ijds.qmd").read_text(encoding="utf-8")
    paper_readme = Path("paper/README.md").read_text(encoding="utf-8")

    for text in (body, supplement, paper_readme):
        assert "regret-auditability" in text.lower()
        assert "OCE/CVaR" in text
        assert "satisficing" in text.lower()
        assert "multi-dataset" in text.lower()
