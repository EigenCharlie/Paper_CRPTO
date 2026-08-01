from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_ijds_bibliography_views import (
    build_bibliography_views,
    citation_keys,
    parse_bibtex_entries,
)


def _write_fixture(root: Path, *, body: str = "Body [@alpha].") -> bytes:
    paper = root / "paper"
    paper.mkdir(parents=True)
    master = b"""@article{alpha,
  title = {An {Exact} Title},
  year = {2024}
}

@inproceedings{beta,
  title = {Reserve Entry},
  year = {2025}
}
"""
    (paper / "references.bib").write_bytes(master)
    (paper / "CRPTO_ijds.qmd").write_text(body, encoding="utf-8")
    (paper / "supplement_ijds.qmd").write_text("Supplement [@alpha].", encoding="utf-8")
    return master


def test_build_views_preserves_master_and_partitions_every_entry(tmp_path: Path) -> None:
    master_before = _write_fixture(tmp_path)

    assert build_bibliography_views(root=tmp_path)
    assert (tmp_path / "paper/references.bib").read_bytes() == master_before
    receipt = json.loads((tmp_path / "paper/references_partition.json").read_text("utf-8"))
    active = receipt["views"]["active"]
    reserve = receipt["views"]["reserve"]

    assert active["keys"] == ["alpha"]
    assert reserve["keys"] == ["beta"]
    assert active["entry_count"] + reserve["entry_count"] == 2
    assert receipt["validation"] == {
        "active_equals_body_plus_supplement_citations": True,
        "duplicate_master_keys": [],
        "missing_citation_keys": [],
        "partition_complete": True,
        "partition_disjoint": True,
    }
    assert receipt["master_bibliography"]["sha256"] == hashlib.sha256(master_before).hexdigest()
    assert receipt["citation_sources"][0]["citation_key_count"] == 1
    assert build_bibliography_views(root=tmp_path, check=True)

    body = tmp_path / "paper/CRPTO_ijds.qmd"
    body.write_text(body.read_text("utf-8") + "\nUnrelated prose edit.\n", encoding="utf-8")
    assert build_bibliography_views(root=tmp_path, check=True)


def test_citation_scan_ignores_quarto_crossrefs_comments_and_code() -> None:
    text = """
Visible [@alpha; -@beta] and @gamma.
See @fig-result and @eq-bound.
<!-- hidden [@commented] -->
`[@inline_code]`
```python
value = "@fenced_code"
```
"""

    assert citation_keys(text) == ("alpha", "beta", "gamma")


def test_parser_rejects_casefolded_duplicate_keys() -> None:
    bibliography = """@article{Same, title={First}}
@article{same, title={Second}}
"""

    with pytest.raises(RuntimeError, match="Duplicate BibTeX keys"):
        parse_bibtex_entries(bibliography)


def test_builder_fails_closed_on_a_missing_citation(tmp_path: Path) -> None:
    _write_fixture(tmp_path, body="Body [@not_in_master].")

    with pytest.raises(RuntimeError, match="not_in_master"):
        build_bibliography_views(root=tmp_path)


def test_repository_bibliography_views_are_current_and_complete() -> None:
    receipt = json.loads(Path("paper/references_partition.json").read_text("utf-8"))
    master_keys = receipt["master_bibliography"]["keys"]
    active_keys = receipt["views"]["active"]["keys"]
    reserve_keys = receipt["views"]["reserve"]["keys"]

    assert len(master_keys) == len(set(master_keys))
    assert set(active_keys).isdisjoint(reserve_keys)
    assert set(active_keys) | set(reserve_keys) == set(master_keys)
    assert receipt["validation"]["missing_citation_keys"] == []
    assert build_bibliography_views(check=True)
