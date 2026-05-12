from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_tail_satisficing_challenger_audit import _build_cluster_bound_table


def test_tail_satisficing_audit_artifacts_exist() -> None:
    status_path = Path("models/crpto_tail_satisficing_audit_status.json")
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert status["champion_promotion_changed"] is False
    assert status["tail_satisficing_audit"]["n_policies_audited"] == 45
    assert status["tail_satisficing_audit"]["promotion_status"] == (
        "journal_audit_only_not_champion"
    )

    for artifact in status["generated_artifacts"]:
        assert Path(artifact).exists()


def test_cluster_bound_table_is_not_tighter_than_markov_for_concentrated_fixture() -> None:
    funded = pd.DataFrame(
        {
            "period": ["a", "a", "b"],
            "original_grade": ["C", "D", "D"],
            "portfolio_weight": [0.45, 0.35, 0.20],
            "miscovered_alpha01": [False, True, False],
        }
    )

    table = _build_cluster_bound_table(funded)

    assert set(table["cluster_type"]) == {"period", "grade", "period_grade"}
    assert not bool(table["cluster_bound_tighter_than_markov"].any())
    assert table["empirical_weighted_miscoverage_V"].max() == 0.35
