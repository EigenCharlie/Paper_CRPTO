from __future__ import annotations

from pathlib import Path

import pytest

from src.ijds_audit.config import load_v4_config

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs" / "experiments"


@pytest.mark.parametrize(
    ("origin", "cutoff", "development_end", "calibration_start", "primary_start"),
    [
        (2015, "2015-03-31", "2009-12-31", "2010-01-01", "2015-04"),
        (2017, "2017-03-31", "2011-12-31", "2012-01-01", "2017-04"),
    ],
)
def test_rolling_origin_configs_shift_the_complete_design(
    origin: int,
    cutoff: str,
    development_end: str,
    calibration_start: str,
    primary_start: str,
) -> None:
    config = load_v4_config(CONFIGS / f"ijds_rolling_origin_{origin}_2026-07-12.yaml")
    assert config["source"]["information_cutoff"] == cutoff
    assert config["design"]["development_end"] == development_end
    assert config["design"]["probability_calibration_start"] == calibration_start
    assert config["design"]["primary_oot_start_month"] == primary_start
    assert config["design"]["primary_oot_end_month"] == f"{origin}-06"
    assert config["rolling_origin"]["origin_year"] == origin
    assert config["rolling_origin"]["outcome_based_origin_selection"] is False
    assert config.get("resume_outcome_free") is None


def test_window_validation_is_relative_to_declared_origin(tmp_path: Path) -> None:
    source = CONFIGS / "ijds_rolling_origin_2015_2026-07-12.yaml"
    payload = source.read_text(encoding="utf-8")
    broken = payload.replace('start: "2011-02-01"', 'start: "2011-03-01"', 1)
    path = tmp_path / "broken.yaml"
    path.write_text(
        broken.replace(
            'extends: "ijds_binary_geometry_frontier_v4_2026-07-12.yaml"',
            f'extends: "{(CONFIGS / "ijds_binary_geometry_frontier_v4_2026-07-12.yaml").as_posix()}"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="consecutive six-month window"):
        load_v4_config(path)


def test_chronology_validator_rejects_a_post_cutoff_primary_gap(tmp_path: Path) -> None:
    source = CONFIGS / "ijds_rolling_origin_2017_2026-07-12.yaml"
    payload = source.read_text(encoding="utf-8")
    broken = payload.replace(
        'primary_oot_start_month: "2017-04"',
        'primary_oot_start_month: "2017-05"',
    )
    path = tmp_path / "broken.yaml"
    path.write_text(
        broken.replace(
            'extends: "ijds_binary_geometry_frontier_v4_2026-07-12.yaml"',
            f'extends: "{(CONFIGS / "ijds_binary_geometry_frontier_v4_2026-07-12.yaml").as_posix()}"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="information cutoff"):
        load_v4_config(path)


def test_rolling_origin_validator_rejects_an_asymmetric_training_origin(tmp_path: Path) -> None:
    source = CONFIGS / "ijds_rolling_origin_2015_2026-07-12.yaml"
    payload = source.read_text(encoding="utf-8")
    broken = payload.replace("origin_year: 2015", "origin_year: 2014")
    path = tmp_path / "broken.yaml"
    path.write_text(
        broken.replace(
            'extends: "ijds_binary_geometry_frontier_v4_2026-07-12.yaml"',
            f'extends: "{(CONFIGS / "ijds_binary_geometry_frontier_v4_2026-07-12.yaml").as_posix()}"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"asymmetric source\.information_cutoff"):
        load_v4_config(path)
