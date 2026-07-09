from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest


def _restore_payload(path: Path, payload: bytes | None) -> None:
    for attempt in range(5):
        try:
            if payload is None:
                path.unlink(missing_ok=True)
                return

            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.restore.{attempt}.tmp")
            tmp.write_bytes(payload)
            tmp.replace(path)
            return
        except OSError:
            tmp.unlink(missing_ok=True) if "tmp" in locals() else None
            if attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


@contextmanager
def _preserve_files(paths: list[Path]) -> Iterator[None]:
    snapshots = {path: path.read_bytes() if path.exists() else None for path in paths}
    try:
        yield
    finally:
        for path, payload in snapshots.items():
            _restore_payload(path, payload)


def test_build_crpto_journal_package_script_runs() -> None:
    pytest.importorskip("matplotlib")
    generated = [
        Path("models/crpto_journal_package_status.json"),
        Path("docs/research/crpto_journal_package_2026-05-04.md"),
        Path("book/assets/figures/publication/crpto_fig1_journal_pipeline.png"),
        Path("book/assets/figures/publication/crpto_fig1_journal_pipeline.pdf"),
        Path("book/assets/figures/publication/crpto_fig1_journal_pipeline.svg"),
        Path("reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.png"),
        Path("reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.pdf"),
        Path("book/assets/figures/publication/crpto_fig12_crpto_conceptual_pipeline.png"),
        Path("book/assets/figures/publication/crpto_fig12_crpto_conceptual_pipeline.pdf"),
        Path("reports/crpto/figures/crpto_fig13_alpha_gamma_funded_set.png"),
        Path("reports/crpto/figures/crpto_fig13_alpha_gamma_funded_set.pdf"),
        Path("book/assets/figures/publication/crpto_fig13_alpha_gamma_funded_set.png"),
        Path("book/assets/figures/publication/crpto_fig13_alpha_gamma_funded_set.pdf"),
        Path("reports/crpto/figures/crpto_fig14_robust_region_heatmap.png"),
        Path("reports/crpto/figures/crpto_fig14_robust_region_heatmap.pdf"),
        Path("book/assets/figures/publication/crpto_fig14_robust_region_heatmap.png"),
        Path("book/assets/figures/publication/crpto_fig14_robust_region_heatmap.pdf"),
        Path("reports/crpto/figures/crpto_fig15_regret_auditability_frontier.png"),
        Path("reports/crpto/figures/crpto_fig15_regret_auditability_frontier.pdf"),
        Path("book/assets/figures/publication/crpto_fig15_regret_auditability_frontier.png"),
        Path("book/assets/figures/publication/crpto_fig15_regret_auditability_frontier.pdf"),
        Path("reports/crpto/figures/crpto_fig20_bound_claim_layers.png"),
        Path("reports/crpto/figures/crpto_fig20_bound_claim_layers.pdf"),
        Path("book/assets/figures/publication/crpto_fig20_bound_claim_layers.png"),
        Path("book/assets/figures/publication/crpto_fig20_bound_claim_layers.pdf"),
        Path("reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.csv"),
        Path("reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.tex"),
    ]
    with _preserve_files(generated):
        subprocess.run([sys.executable, "scripts/build_crpto_journal_package.py"], check=True)
    assert Path("models/crpto_journal_package_status.json").exists()
    assert Path("reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv").exists()
    assert Path("reports/crpto/tables/crpto_tableA19_regret_auditability_frontier.csv").exists()
