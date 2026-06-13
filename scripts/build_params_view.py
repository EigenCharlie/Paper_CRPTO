"""Build the DVC ``params.yaml`` view from canonical CRPTO configs.

The project scripts read ``configs/*.yaml`` and promotion JSON artifacts; DVC
uses ``params.yaml`` as a compact cache-key surface. This helper keeps that
surface reproducible without making DVC stages depend on ad hoc manual edits.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a YAML mapping.")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object.")
    return payload


def build_params_view(root: Path = ROOT) -> dict[str, Any]:
    """Return the generated ``params.yaml`` mapping."""
    existing = _load_yaml(root / "params.yaml")
    pd_config = _load_yaml(root / "configs" / "crpto_pd_model.yaml")
    conformal_config = _load_yaml(root / "configs" / "crpto_conformal_policy.yaml")
    optimization_config = _load_yaml(root / "configs" / "crpto_optimization.yaml")
    promotion = _load_json(root / "models" / "final_project_promotion.json")

    champion = promotion["final_champion"]
    robust_region = promotion["robust_region_summary"]
    model_params = pd_config["model"]["params"]
    policy = conformal_config["policy"]
    portfolio_config = optimization_config["portfolio"]

    existing_paper = dict(existing.get("paper", {}) or {})
    existing_conformal = dict(existing.get("conformal", {}) or {})
    existing_portfolio = dict(existing.get("portfolio", {}) or {})

    return {
        "paper": {
            "run_tag": promotion["run_tag"],
            "champion_policy": existing_paper.get("champion_policy", champion["label"]),
            "region_robust": (
                f"{robust_region['n_alpha01_passers']}/{robust_region['n_unique_policies']}"
            ),
        },
        "champion": {
            "return_robust": round(float(champion["realized_total_return"]), 2),
            "v_alpha_001": float(champion["alpha01_weighted_miscoverage_V"]),
            "gamma_cp_alpha_001": float(champion["alpha01_gamma_cp"]),
            "alpha_exact_pass": bool(champion["alpha01_exact_pass"]),
        },
        "pd": {
            "model": pd_config["model"]["type"],
            "catboost": {
                "depth": int(model_params["depth"]),
                "iterations": int(model_params["iterations"]),
                "learning_rate": float(model_params["learning_rate"]),
            },
            "calibration": pd_config["calibration"]["method"],
        },
        "conformal": {
            "alpha": existing_conformal.get("alpha", 0.01),
            "coverage_targets": [
                float(policy["target_coverage_90_min"]),
                float(policy["target_coverage_95_min"]),
            ],
            "mondrian": existing_conformal.get("mondrian", {}),
            "variant_selection": existing_conformal.get("variant_selection", {}),
        },
        "portfolio": {
            "policy_mode": existing_portfolio.get("policy_mode", "bound_aware"),
            "uncertainty_aversion": existing_portfolio.get("uncertainty_aversion", 0.0),
            "max_concentration": float(portfolio_config["max_concentration"]),
            "max_portfolio_pd": float(portfolio_config["max_portfolio_pd"]),
            "min_budget_utilization": existing_portfolio.get("min_budget_utilization", 0.5),
        },
        "optuna": existing.get("optuna", {}),
        "book": existing.get("book", {}),
    }


def dump_params_view(params: dict[str, Any]) -> str:
    """Serialize params deterministically for checks and optional rewrites."""
    return yaml.safe_dump(params, sort_keys=False, allow_unicode=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if params.yaml is stale.")
    parser.add_argument("--write", action="store_true", help="Rewrite params.yaml from sources.")
    args = parser.parse_args()

    target = ROOT / "params.yaml"
    generated = dump_params_view(build_params_view(ROOT))

    if args.check:
        current = dump_params_view(_load_yaml(target))
        if current != generated:
            diff = "\n".join(
                difflib.unified_diff(
                    current.splitlines(),
                    generated.splitlines(),
                    fromfile="params.yaml",
                    tofile="generated",
                    lineterm="",
                )
            )
            raise SystemExit(f"params.yaml is stale:\n{diff}")
        logger.info("params.yaml is synchronized with canonical configs.")
        return

    if args.write:
        target.write_text(generated, encoding="utf-8")
        logger.info("Wrote {}", target)
        return

    logger.info(generated)


if __name__ == "__main__":
    main()
