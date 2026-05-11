from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_build_crpto_journal_package_script_runs() -> None:
    pytest.importorskip("matplotlib")
    subprocess.run([sys.executable, "scripts/build_crpto_journal_package.py"], check=True)
    assert Path("models/crpto_journal_package_status.json").exists()
    assert Path("reports/crpto/tables/crpto_tableA18_robust_region_policy_family.csv").exists()
