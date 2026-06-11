"""Anti-regression guard for the april-lineage unification (2026-06-10).

The pre-unification PD metrics (AUC 0.7127 / Brier 0.1546 / ECE 0.0062, and
their short-form variants in figures) came from canonical retrains that never
fed the certificate. After the unification every ACTIVE narrative surface
must cite the certificate lineage (AUC 0.7139 / Brier 0.1544 / ECE 0.0070).

This test sweeps the active paper, book, figure-source and figure-script
surfaces for the retired values so they cannot silently reappear (e.g. via a
merge of an older branch). Historical research notes under ``docs/research``
and frozen one-shot tables are intentionally NOT scanned: they are dated
records of what was true at the time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Active narrative surfaces: anything a reviewer or jury reads as current.
ACTIVE_GLOBS = (
    "paper/CRPTO_ijds.qmd",
    "paper/supplement_ijds.qmd",
    "paper/submission/CRPTO_ijds_submission.tex",
    "book/chapters/*.qmd",
    "reports/crpto/figures/*.svg",
    "scripts/generate_crpto_figures.py",
)

# Retired PD-metric strings. Tokens are specific enough to avoid collisions
# with unrelated quantities (checked at introduction time): bare "0.006"-style
# short forms are only banned in their labelled figure/text contexts.
RETIRED_TOKENS = (
    "0.7127",
    "AUC 0.712,",
    "AUC `0.7127`",
    "ECE 0.0062",
    "ECE = 0.0062",
    "ECE 0.006<",  # svg text node short form
    "Brier `0.1546`",
    "Brier score `0.1546`",
)


def _active_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ACTIVE_GLOBS:
        files.extend(ROOT.glob(pattern))
    return [f for f in files if f.is_file()]


def test_active_surfaces_do_not_cite_retired_pd_metrics() -> None:
    files = _active_files()
    assert files, "Active-surface glob list resolved to nothing — fix the test."
    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in RETIRED_TOKENS:
            if token in text:
                line_no = text[: text.index(token)].count("\n") + 1
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{line_no} -> {token!r}")
    assert not offenders, (
        "Retired pre-unification PD metrics found on active surfaces "
        "(certificate lineage is AUC 0.7139 / Brier 0.1544 / ECE 0.0070):\n  "
        + "\n  ".join(offenders)
    )


def test_canonical_sources_carry_certificate_lineage() -> None:
    """pipeline_summary and metrics_summary must agree on the unified metrics."""
    import json

    summary_path = ROOT / "data" / "processed" / "pipeline_summary.json"
    metrics_path = ROOT / "reports" / "dvc" / "metrics_summary.json"
    if not (summary_path.is_file() and metrics_path.is_file()):
        pytest.skip("Canonical metric artifacts not available locally.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))["metrics"]
    assert summary["pd_auc"] == pytest.approx(metrics["pd.auc"], rel=1e-12)
    assert summary["pd_auc"] == pytest.approx(0.713852, abs=5e-6)
    assert summary["pd_brier"] == pytest.approx(0.154393, abs=5e-6)
    assert summary["pd_ece"] == pytest.approx(0.006998, abs=5e-6)
