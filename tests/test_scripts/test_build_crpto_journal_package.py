from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest


@contextmanager
def _preserve_files(paths: list[Path]) -> Iterator[None]:
    snapshots = {path: path.read_bytes() if path.exists() else None for path in paths}
    try:
        yield
    finally:
        for path, payload in snapshots.items():
            if payload is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)


def test_build_crpto_journal_package_script_runs() -> None:
    pytest.importorskip("matplotlib")
    generated = [
        Path("models/crpto_journal_package_status.json"),
        Path("reports/crpto/figures/crpto_fig12_crpto_conceptual_pipeline.pdf"),
        Path("reports/crpto/figures/crpto_fig13_alpha_gamma_funded_set.pdf"),
        Path("reports/crpto/figures/crpto_fig14_robust_region_heatmap.pdf"),
    ]
    with _preserve_files(generated):
        subprocess.run([sys.executable, "scripts/build_crpto_journal_package.py"], check=True)
    assert Path("models/crpto_journal_package_status.json").exists()
    assert Path("reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv").exists()
