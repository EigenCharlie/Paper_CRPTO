from __future__ import annotations

import json
from pathlib import Path


def test_crpto_vs_spo_stability_artifacts_exist() -> None:
    status_path = Path("data/processed/crpto_vs_spo_stability.json")
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status.get("schema_version")
    assert Path("reports/crpto/figures/crpto_fig11_crpto_stability.png").exists()
