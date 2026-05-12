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
    assert "future work" in boundary
    assert set(included) == {
        "regret_auditability_frontier",
        "tail_risk_oce_cvar_diagnostic",
        "robust_satisficing_margins",
        "dependence_aware_bound",
    }
    assert included["regret_auditability_frontier"]["status"] == "include_body"
    assert included["tail_risk_oce_cvar_diagnostic"]["status"] == "include_supplement"
    assert included["robust_satisficing_margins"]["status"] == ("include_supplement_or_short_body")
    assert included["dependence_aware_bound"]["status"] == "include_theory_appendix_or_caveat"
    assert backlog["multi_dataset_credit_replication"]["status"] == ("journal_backlog_not_blocker")

    body = Path("paper/CRPTO_ijds.qmd").read_text(encoding="utf-8")
    supplement = Path("paper/supplement_ijds.qmd").read_text(encoding="utf-8")
    closure = Path("docs/research/crpto_submission_closure_2026-05-12.md").read_text(
        encoding="utf-8"
    )

    for text in (body, supplement, closure):
        assert "regret-auditability" in text.lower()
        assert "OCE/CVaR" in text
        assert "satisficing" in text.lower()
        assert "multi-dataset" in text.lower()
