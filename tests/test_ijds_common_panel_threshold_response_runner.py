from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from scripts.experiments.run_ijds_common_panel_threshold_response_v7 import (
    DEFAULT_CONFIG_PATH,
    _load_config,
    _preflight_output_paths,
    _reconcile_temporal_reference,
    _validate_output_names,
)

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_v7_config_is_complete_and_locked() -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)

    assert config["design"]["expected_stratum_pairs"] == 175
    assert config["design"]["expected_learner_pairs"] == 35
    assert config["interpretation"]["preregistered"] is False
    assert config["interpretation"]["no_ranking_or_selection"] is True


@pytest.mark.parametrize(
    ("key", "unsafe"),
    [
        ("stratum_table", "../response.csv"),
        ("learner_table", "nested/response.csv"),
        ("summary", "summary.txt"),
        ("execution_receipt", ""),
    ],
)
def test_v7_output_names_fail_closed_before_directory_creation(key: str, unsafe: str) -> None:
    config = _load_config(ROOT / DEFAULT_CONFIG_PATH)
    config = deepcopy(config)
    config["output"][key] = unsafe

    with pytest.raises(ValueError, match="safe"):
        _validate_output_names(config)


def test_v7_output_names_reject_casefold_aliases() -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    config["output"]["learner_table"] = config["output"]["stratum_table"].upper()

    with pytest.raises(ValueError, match="alias"):
        _validate_output_names(config)


def test_v7_preflight_does_not_create_output_directories(tmp_path: Path) -> None:
    config = deepcopy(_load_config(ROOT / DEFAULT_CONFIG_PATH))
    data_dir = tmp_path / config["output"]["data_root"] / config["run_tag"]
    model_dir = tmp_path / config["output"]["model_root"] / config["run_tag"]

    _preflight_output_paths(config, repo_root=tmp_path)

    assert not data_dir.exists()
    assert not model_dir.exists()


def _reference_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for group in range(5):
        rows.append(
            {
                "learner": "learner",
                "window_id": "window",
                "taxonomy_groups": 5,
                "conformal_group": group,
                "role": "primary_oot",
                "candidate_rows": 10 + group,
                "resolved_rows": 8 + group,
                "unresolved_rows": 2,
                "coverage_resolved": 0.80 + group / 100,
                "coverage_lower": 0.70 + group / 100,
                "coverage_upper": 0.90 + group / 100,
                "score_min": group / 10,
                "score_max": (group + 1) / 10,
                "fit_residual_quantile": 0.1 + group / 20,
                "fit_score_min": group / 11,
                "fit_score_max": (group + 1) / 11,
            }
        )
    temporal = pd.DataFrame(rows)
    reference = temporal.sample(frac=1.0, random_state=7).reset_index(drop=True)
    return temporal, reference


def test_temporal_reference_reconciliation_is_keyed_not_row_positional() -> None:
    temporal, reference = _reference_pair()

    result = _reconcile_temporal_reference(
        temporal,
        reference,
        learners=("learner",),
        windows=("window",),
        role="primary_oot",
        taxonomy_groups=5,
    )

    assert result["rows"] == 5
    assert result["key_grid_exact"] is True
    assert max(result["maximum_absolute_differences"].values()) == 0.0


@pytest.mark.parametrize("field", ["candidate_rows", "coverage_upper"])
def test_temporal_reference_reconciliation_fails_on_numeric_drift(field: str) -> None:
    temporal, reference = _reference_pair()
    reference.loc[0, field] += 1

    with pytest.raises(RuntimeError, match=field):
        _reconcile_temporal_reference(
            temporal,
            reference,
            learners=("learner",),
            windows=("window",),
            role="primary_oot",
            taxonomy_groups=5,
        )
