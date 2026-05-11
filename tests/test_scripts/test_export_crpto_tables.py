from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


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
    with _preserve_files([Path("models/crpto_evidence_status.json")]):
        subprocess.run([sys.executable, "scripts/export_crpto_tables.py"], check=True)
    assert Path("reports/crpto/tables/crpto_table0_key_metrics.csv").exists()
