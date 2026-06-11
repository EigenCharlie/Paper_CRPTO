from __future__ import annotations

import pytest

from scripts.build_bound_tightening_audit import (
    FUNDED_LOANS_PATH,
    _cluster_assumption_rows,
    _threshold_rows,
)


def test_bound_tightening_audit_preserves_main_markov_claim() -> None:
    import pandas as pd

    funded = pd.read_csv(FUNDED_LOANS_PATH)
    table, stats = _threshold_rows(funded)
    alpha01 = table[table["alpha"].eq(0.01)]

    markov = alpha01.loc[alpha01["bound"].eq("markov")].iloc[0]
    assert markov["threshold_t"] == pytest.approx(0.1)
    assert not bool(markov["tighter_than_markov"])
    assert stats["empirical_v"] == pytest.approx(0.028875, abs=1e-12)
    assert stats["n_eff"] == pytest.approx(126.066, rel=1e-4)


def test_conditional_bounds_show_tightness_but_require_extra_assumptions() -> None:
    import pandas as pd

    funded = pd.read_csv(FUNDED_LOANS_PATH)
    table, _ = _threshold_rows(funded)
    alpha01 = table[table["alpha"].eq(0.01)]

    hoeffding = alpha01.loc[alpha01["bound"].eq("hoeffding")].iloc[0]
    bernstein = alpha01[
        alpha01["bound"].eq("bernstein") & alpha01["variance_mode"].eq("strong_individual_validity")
    ].iloc[0]
    freedman = alpha01[
        alpha01["bound"].eq("freedman_martingale")
        & alpha01["variance_mode"].eq("strong_individual_validity")
    ].iloc[0]
    cantelli = alpha01[
        alpha01["bound"].eq("cantelli_one_sided")
        & alpha01["variance_mode"].eq("weak_weighted_validity")
    ].iloc[0]

    assert hoeffding["threshold_t"] > 0.1
    assert bernstein["threshold_t"] == pytest.approx(0.069832, rel=1e-4)
    assert freedman["threshold_t"] == pytest.approx(bernstein["threshold_t"])
    assert cantelli["threshold_t"] == pytest.approx(0.066125, rel=1e-4)
    assert bool(bernstein["tighter_than_markov"])
    assert "chernoff_mgf" not in set(alpha01["bound"])
    assert "chebyshev_two_sided" not in set(alpha01["bound"])
    assert "azuma_hoeffding_martingale" not in set(alpha01["bound"])
    assert "union_markov_45_policy_region" not in set(alpha01["bound"])


def test_assumption_audit_marks_independence_as_unverified() -> None:
    import pandas as pd

    funded = pd.read_csv(FUNDED_LOANS_PATH)
    _, stats = _threshold_rows(funded)
    audit = _cluster_assumption_rows(funded, stats)

    loan_independence = audit.loc[audit["assumption"].eq("loan_independence")].iloc[0]
    union_markov = audit.loc[audit["assumption"].eq("post_selection_uniformity")].iloc[0]
    martingale = audit.loc[audit["assumption"].eq("sequential_martingale_protocol")].iloc[0]
    chernoff = audit.loc[audit["assumption"].eq("chernoff_mgf")].iloc[0]
    chebyshev = audit.loc[audit["assumption"].eq("chebyshev_two_sided")].iloc[0]
    cluster_rows = audit[audit["assumption"].str.startswith("cluster_independence_")]

    assert loan_independence["status"] == "not_verified"
    assert union_markov["status"] == "not_supported_by_markov"
    assert martingale["status"] == "not_available"
    assert chernoff["status"] == "drop_from_table"
    assert chebyshev["status"] == "drop_from_table"
    assert set(cluster_rows["status"]) == {"conditional_loose"}
