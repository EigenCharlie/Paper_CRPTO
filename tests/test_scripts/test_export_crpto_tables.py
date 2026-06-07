from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from scripts import analyze_crpto_evidence


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


def test_export_crpto_tables_script_runs() -> None:
    # The script intentionally refreshes the CRPTO evidence status timestamp.
    # Preserve the committed artifact so the test remains side-effect free.
    generated_paths = [
        *Path("reports/crpto/tables").glob("crpto_table*.*"),
        Path("models/crpto_evidence_status.json"),
        Path("docs/research/crpto_p1_evidence_2026-05-04.md"),
    ]
    with _preserve_files(generated_paths):
        subprocess.run([sys.executable, "scripts/export_crpto_tables.py"], check=True)
    assert Path("reports/crpto/tables/crpto_table0_key_metrics.csv").exists()


def test_evidence_repo_path_uses_posix_separators() -> None:
    path = analyze_crpto_evidence.ROOT / "reports" / "crpto" / "tables" / "example.csv"
    repo_path = analyze_crpto_evidence._repo_path(path)

    assert repo_path == "reports/crpto/tables/example.csv"
    assert "\\" not in repo_path
