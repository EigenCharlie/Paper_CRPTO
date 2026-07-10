from __future__ import annotations

import pandas as pd

from scripts.generate_crpto_figures import (
    PALETTE,
    _alpha_annotation_offset,
    _alpha_pareto_column_map,
    _alpha_pareto_missing_columns,
    _alpha_pareto_subframe,
    _alpha_pareto_variant_styles,
    _alpha_tick_labels,
)


def test_alpha_pareto_column_map_detects_semantic_columns() -> None:
    df = pd.DataFrame(
        columns=[
            "method_name",
            "alpha_level",
            "empirical_coverage",
            "mean_width",
            "n_eligible_loans",
        ]
    )

    columns = _alpha_pareto_column_map(df)

    assert columns == {
        "variant": "method_name",
        "alpha": "alpha_level",
        "coverage": "empirical_coverage",
        "width": "mean_width",
        "eligible": "n_eligible_loans",
    }
    assert _alpha_pareto_missing_columns(columns) == []


def test_alpha_pareto_variant_styles_label_mondrian_and_global() -> None:
    colors, labels = _alpha_pareto_variant_styles(["mondrian", "global"])

    assert labels == {
        "mondrian": "Mondrian CP",
        "global": "Global Split-CP",
    }
    assert colors == {
        "mondrian": PALETTE["blue"],
        "global": PALETTE["orange"],
    }


def test_alpha_pareto_subframe_sorts_alpha_and_formats_labels() -> None:
    df = pd.DataFrame(
        {
            "variant": ["global", "mondrian", "global"],
            "alpha": [0.2, 0.1, 0.05],
            "coverage": [0.93, 0.91, 0.90],
        }
    )

    sub = _alpha_pareto_subframe(
        df,
        variant_col="variant",
        alpha_col="alpha",
        variant="global",
    )

    assert list(sub["alpha"]) == [0.05, 0.2]
    assert _alpha_tick_labels(sub["alpha"]) == ["0.05", "0.2"]
    assert _alpha_annotation_offset(0, 2) == (4, 4)
    assert _alpha_annotation_offset(1, 2) == (-24, -8)
