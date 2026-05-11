from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_export_crpto_tables_script_runs() -> None:
    subprocess.run([sys.executable, "scripts/export_crpto_tables.py"], check=True)
    assert Path("reports/crpto/tables/crpto_table0_key_metrics.csv").exists()
