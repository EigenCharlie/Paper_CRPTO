from __future__ import annotations

import pandas as pd

from scripts.search.run_conformal_reopen_search import _phase2_top_designs


def _design(*, partition: str, alpha: float, width: float, rank: int) -> dict[str, object]:
    return {
        "partition": partition,
        "partition_probability_source": "calibrated",
        "n_score_bins": 10,
        "fallback_mode": "grade_then_global",
        "alpha_used_90": alpha,
        "alpha_used_95": 0.05,
        "score_scale_family": "bernoulli_sqrt",
        "min_group_size": 500,
        "calibration_fraction": 0.50,
        "avg_width_90": width,
        "selection_rank": rank,
    }


def test_phase2_top_designs_prefers_phase1_oot_confirmed_candidates() -> None:
    inner = pd.DataFrame(
        [
            _design(partition="score_decile_mondrian", alpha=0.085, width=0.79, rank=1),
            _design(partition="grade", alpha=0.095, width=0.77, rank=2),
        ]
    )
    oot = pd.DataFrame(
        [
            _design(partition="grade_x_scoreband_mondrian", alpha=0.075, width=0.78, rank=1),
        ]
    )

    top, source = _phase2_top_designs(
        aggregated=inner,
        phase1_candidates_frame=oot,
        top_k=2,
    )

    assert source == "phase1_oot_confirmed"
    assert top.iloc[0]["partition"] == "grade_x_scoreband_mondrian"
    assert set(top["phase2_design_source"]) == {"phase1_oot_confirmed"}


def test_phase2_top_designs_falls_back_to_inner_when_oot_empty() -> None:
    inner = pd.DataFrame(
        [
            _design(partition="score_decile_mondrian", alpha=0.085, width=0.79, rank=1),
        ]
    )

    top, source = _phase2_top_designs(
        aggregated=inner,
        phase1_candidates_frame=pd.DataFrame(),
        top_k=2,
    )

    assert source == "phase1_inner_aggregate"
    assert top.iloc[0]["partition"] == "score_decile_mondrian"
    assert set(top["phase2_design_source"]) == {"phase1_inner_aggregate"}
