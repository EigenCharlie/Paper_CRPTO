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
