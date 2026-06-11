"""Guard against silent drift between ``params.yaml`` and its source configs.

``params.yaml`` is a read-only documentary view: scripts read
``configs/crpto_*.yaml`` and ``models/final_project_promotion.json``, while
DVC uses ``params.yaml`` entries as cache keys for the protected stages.
Because the two surfaces are maintained by hand, a value edited on one side
can silently diverge on the other (this happened with
``pd.catboost.learning_rate``). These tests pin the keys that are true
mirrors. Keys that are documentary-only (``portfolio.policy_mode``,
``conformal.mondrian.partition_by``) have no canonical config counterpart
and are intentionally not asserted.

Unifying params.yaml with the configs remains a deferred refactor (see the
header comment in params.yaml); until then this test is the sync contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def params() -> dict[str, Any]:
    return _load_yaml(ROOT / "params.yaml")


@pytest.fixture(scope="module")
def pd_config() -> dict[str, Any]:
    return _load_yaml(ROOT / "configs" / "crpto_pd_model.yaml")


@pytest.fixture(scope="module")
def conformal_config() -> dict[str, Any]:
    return _load_yaml(ROOT / "configs" / "crpto_conformal_policy.yaml")


@pytest.fixture(scope="module")
def optimization_config() -> dict[str, Any]:
    return _load_yaml(ROOT / "configs" / "crpto_optimization.yaml")


@pytest.fixture(scope="module")
def promotion() -> dict[str, Any]:
    path = ROOT / "models" / "final_project_promotion.json"
    if not path.is_file():
        pytest.skip("final_project_promotion.json not available locally.")
    return json.loads(path.read_text(encoding="utf-8"))


def test_pd_params_mirror_pd_config(params: dict[str, Any], pd_config: dict[str, Any]) -> None:
    model_params = pd_config["model"]["params"]
    mirrored = params["pd"]["catboost"]
    assert params["pd"]["model"] == pd_config["model"]["type"]
    assert mirrored["depth"] == model_params["depth"]
    assert mirrored["iterations"] == model_params["iterations"]
    assert mirrored["learning_rate"] == pytest.approx(model_params["learning_rate"], rel=1e-12)
    assert params["pd"]["calibration"] == pd_config["calibration"]["method"]


def test_conformal_coverage_targets_mirror_policy_config(
    params: dict[str, Any], conformal_config: dict[str, Any]
) -> None:
    targets = params["conformal"]["coverage_targets"]
    policy = conformal_config["policy"]
    assert targets == [
        pytest.approx(policy["target_coverage_90_min"]),
        pytest.approx(policy["target_coverage_95_min"]),
    ]


def test_portfolio_params_mirror_optimization_config(
    params: dict[str, Any], optimization_config: dict[str, Any]
) -> None:
    portfolio = optimization_config["portfolio"]
    assert params["portfolio"]["max_concentration"] == pytest.approx(portfolio["max_concentration"])
    assert params["portfolio"]["max_portfolio_pd"] == pytest.approx(portfolio["max_portfolio_pd"])


def test_champion_params_mirror_promotion_artifact(
    params: dict[str, Any], promotion: dict[str, Any]
) -> None:
    champion = promotion["final_champion"]
    assert params["paper"]["run_tag"] == promotion["run_tag"]
    assert params["champion"]["v_alpha_001"] == pytest.approx(
        champion["alpha01_weighted_miscoverage_V"], abs=1e-12
    )
    assert params["champion"]["gamma_cp_alpha_001"] == pytest.approx(
        champion["alpha01_gamma_cp"], abs=1e-12
    )
    assert params["champion"]["alpha_exact_pass"] == bool(champion["alpha01_exact_pass"])
    # return_robust is a display mirror rounded to cents.
    assert params["champion"]["return_robust"] == pytest.approx(
        round(float(champion["realized_total_return"]), 2)
    )


def test_robust_region_mirror_matches_promotion(
    params: dict[str, Any], promotion: dict[str, Any]
) -> None:
    region = promotion["robust_region_summary"]
    expected = f"{region['n_alpha01_passers']}/{region['n_unique_policies']}"
    assert params["paper"]["region_robust"] == expected


def test_variant_selection_rank1_path_exists(params: dict[str, Any]) -> None:
    rank1 = params["conformal"]["variant_selection"]["rank1_path"]
    run_dir = ROOT / "data" / "processed" / "portfolio_bound_aware" / rank1
    if not run_dir.parent.exists():
        pytest.skip("portfolio_bound_aware artifacts not available locally — run `dvc pull`.")
    assert run_dir.is_dir(), f"rank1_path does not resolve to a run directory: {rank1}"
