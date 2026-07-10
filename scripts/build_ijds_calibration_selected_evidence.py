"""Build paper-facing evidence for the calibration-selected IJDS policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.optimization.policy_selection import policy_eligibility_mask  # noqa: E402
from src.utils.script_helpers import load_json, write_json, write_table  # noqa: E402

RUN_TAG = "champion-reopen-2026-06-19__pool93__ijds-calibration-selected-simple90-v6"
EXACT_ALPHA_TAG = "champion-reopen-2026-06-19__pool93__ijds-exact-alpha-grid-v1"
MODEL_DIR = ROOT / "models/experiments/champion_reopen" / RUN_TAG / "portfolio"
DATA_DIR = ROOT / "data/processed/experiments/champion_reopen" / RUN_TAG / "portfolio"
EXACT_MODEL_DIR = ROOT / "models/experiments/champion_reopen" / EXACT_ALPHA_TAG / "conformal"
TABLE_DIR = ROOT / "reports/crpto/tables"

TABLE_NAMES = {
    "alpha": "crpto_tableA35_exact_alpha_grid",
    "selector": "crpto_tableA36_calibration_policy_selector",
    "temporal": "crpto_tableA37_calibration_selected_temporal_evaluation",
    "grade": "crpto_tableA38_calibration_selected_grade_audit",
    "bootstrap": "crpto_tableA39_calibration_selected_bootstrap",
    "baseline": "crpto_tableA40_calibration_selected_point_baseline",
}
GOVERNANCE_NAME = "ijds_policy_governance.json"


def _weighted_average(frame: pd.DataFrame, column: str) -> float:
    weights = frame["funded_weight"].to_numpy(dtype=float)
    values = frame[column].to_numpy(dtype=float)
    return float(np.sum(weights * values) / max(weights.sum(), 1e-12))


def build_alpha_table(summary: dict[str, Any]) -> pd.DataFrame:
    rows = pd.DataFrame(summary["alpha_summaries"]).copy()
    rows.insert(0, "selected_for_policy", np.isclose(rows["target_alpha"], 0.10))
    return rows[
        [
            "selected_for_policy",
            "target_alpha",
            "used_alpha",
            "target_coverage",
            "empirical_coverage",
            "coverage_gap",
            "avg_width",
            "min_partition_coverage",
            "min_grade_coverage",
            "high_endpoint_at_one_rate",
        ]
    ]


def build_selector_table(grid: pd.DataFrame, summary: dict[str, Any]) -> pd.DataFrame:
    selected_id = str(summary["selected_policy"]["candidate_id"])
    cap = float(summary["design"]["markov_threshold_cap"])
    output = grid.copy()
    output["eligible"] = policy_eligibility_mask(
        output,
        markov_threshold_cap=cap,
        budget=float(summary["design"]["budget"]),
        min_budget_utilization=float(summary["design"]["selection_min_budget_utilization"]),
    )
    output["selected"] = output["candidate_id"].astype(str).eq(selected_id)
    return output[
        [
            "selected",
            "eligible",
            "candidate_id",
            "risk_tolerance",
            "gamma",
            "expected_objective",
            "n_funded",
            "weighted_pd_point",
            "weighted_pd_effective",
            "endpoint_budget",
            "markov_loss_threshold",
        ]
    ].sort_values(
        ["selected", "eligible", "expected_objective"],
        ascending=[False, False, False],
        kind="mergesort",
    )


def build_temporal_table(evaluation: pd.DataFrame) -> pd.DataFrame:
    role_labels = {
        "calibration_selected": "Calibration-selected 50/50 CRPTO",
        "incumbent_linear": "More-conservative 75% blend",
        "point_pd_matched_tau": "Point-PD matched-tau",
    }
    output = evaluation.copy()
    output["policy"] = output["role"].map(role_labels)
    return output[
        [
            "period",
            "policy",
            "risk_tolerance",
            "gamma",
            "n_funded",
            "expected_objective",
            "realized_return",
            "weighted_outcome",
            "weighted_miscoverage",
            "weighted_pd_point",
            "weighted_pd_effective",
            "endpoint_budget",
            "markov_loss_threshold",
        ]
    ]


def build_grade_table(allocations: pd.DataFrame) -> pd.DataFrame:
    selected = allocations.loc[allocations["role"].eq("calibration_selected")].copy()
    rows: list[dict[str, Any]] = []
    for grade, group in selected.groupby("grade", observed=True, sort=True):
        rows.append(
            {
                "grade": str(grade),
                "n_funded": int(len(group)),
                "exposure": float(group["funded_exposure"].sum()),
                "exposure_share": float(group["funded_weight"].sum()),
                "weighted_default_rate": _weighted_average(group, "outcome"),
                "weighted_miscoverage": _weighted_average(group, "miscoverage"),
                "weighted_pd_point": _weighted_average(group, "pd_point"),
                "weighted_pd_effective": _weighted_average(group, "pd_effective"),
                "weighted_pd_high": _weighted_average(group, "pd_high"),
                "realized_return": float(group["realized_return_contribution"].sum()),
            }
        )
    return pd.DataFrame(rows)


def _bootstrap_snapshot(
    sample: pd.DataFrame, *, total_exposure: float, lgd: float
) -> dict[str, float]:
    weights = sample["funded_exposure"].to_numpy(dtype=float)
    weights = weights / max(float(weights.sum()), 1e-12)
    outcome = sample["outcome"].to_numpy(dtype=float)
    rates = sample["int_rate"].to_numpy(dtype=float)
    point = sample["pd_point"].to_numpy(dtype=float)
    high = sample["pd_high"].to_numpy(dtype=float)
    realized_rate = np.where(outcome.astype(int) == 1, -float(lgd), rates)
    return {
        "realized_return": float(np.sum(weights * realized_rate) * total_exposure),
        "weighted_default_rate": float(np.sum(weights * outcome)),
        "weighted_miscoverage": float(np.sum(weights * sample["miscoverage"])),
        "Gamma_CP": float(np.sum(weights * (high - point))),
        "endpoint_budget": float(np.sum(weights * high)),
    }


def build_bootstrap_table(
    allocations: pd.DataFrame,
    evaluation: pd.DataFrame,
    *,
    n_draws: int = 5000,
    seed: int = 20260709,
    lgd: float = 0.45,
) -> pd.DataFrame:
    selected = allocations.loc[allocations["role"].eq("calibration_selected")].reset_index(
        drop=True
    )
    total_exposure = float(selected["funded_exposure"].sum())
    allocation_observed = _bootstrap_snapshot(
        selected,
        total_exposure=total_exposure,
        lgd=lgd,
    )
    official = evaluation.loc[
        evaluation["period"].eq("full_oot") & evaluation["role"].eq("calibration_selected")
    ].iloc[0]
    observed = {
        "realized_return": float(official["realized_return"]),
        "weighted_default_rate": float(official["weighted_outcome"]),
        "weighted_miscoverage": float(official["weighted_miscoverage"]),
        "Gamma_CP": float(official["gamma_cp"]),
        "endpoint_budget": float(official["endpoint_budget"]),
    }
    mismatches = [
        metric
        for metric, value in observed.items()
        if not np.isclose(allocation_observed[metric], value, rtol=1e-10, atol=1e-8)
    ]
    if mismatches:
        raise ValueError(
            "Funded allocations do not reconcile to the full-OOT evaluation: "
            + ", ".join(mismatches)
        )
    rng = np.random.default_rng(seed)
    draws = [
        _bootstrap_snapshot(
            selected.iloc[rng.integers(0, len(selected), size=len(selected))].reset_index(
                drop=True
            ),
            total_exposure=total_exposure,
            lgd=lgd,
        )
        for _ in range(n_draws)
    ]
    draw_frame = pd.DataFrame(draws)
    note = "Fixed funded-loan contribution bootstrap; model, intervals, selector, and solver are not resampled."
    return pd.DataFrame(
        [
            {
                "metric": metric,
                "observed": observed[metric],
                "boot_mean": float(draw_frame[metric].mean()),
                "boot_p025": float(draw_frame[metric].quantile(0.025)),
                "boot_p50": float(draw_frame[metric].quantile(0.50)),
                "boot_p975": float(draw_frame[metric].quantile(0.975)),
                "n_draws": n_draws,
                "seed": seed,
                "note": note,
            }
            for metric in draw_frame.columns
        ]
    )


def build_baseline_table(evaluation: pd.DataFrame) -> pd.DataFrame:
    full = evaluation.loc[evaluation["period"].eq("full_oot")].copy()
    selected = full.loc[full["role"].eq("calibration_selected")].iloc[0]
    labels = {
        "calibration_selected": "Calibration-selected 50/50 CRPTO",
        "incumbent_linear": "More-conservative 75% blend",
        "point_pd_matched_tau": "Point-PD matched-tau",
    }
    full["policy"] = full["role"].map(labels)
    full["return_delta_vs_selected"] = full["realized_return"] - float(selected["realized_return"])
    full["default_delta_vs_selected"] = full["weighted_outcome"] - float(
        selected["weighted_outcome"]
    )
    full["threshold_delta_vs_selected"] = full["markov_loss_threshold"] - float(
        selected["markov_loss_threshold"]
    )
    return full[
        [
            "policy",
            "n_funded",
            "expected_objective",
            "realized_return",
            "weighted_outcome",
            "weighted_miscoverage",
            "endpoint_budget",
            "markov_loss_threshold",
            "return_delta_vs_selected",
            "default_delta_vs_selected",
            "threshold_delta_vs_selected",
        ]
    ]


def build_governance(
    summary: dict[str, Any],
    exact_summary: dict[str, Any],
    evaluation: pd.DataFrame,
    bootstrap: pd.DataFrame,
    table_paths: dict[str, list[Path]],
) -> dict[str, Any]:
    full = evaluation.loc[
        evaluation["period"].eq("full_oot") & evaluation["role"].eq("calibration_selected")
    ].iloc[0]
    point = evaluation.loc[
        evaluation["period"].eq("full_oot") & evaluation["role"].eq("point_pd_matched_tau")
    ].iloc[0]
    return_boot = bootstrap.loc[bootstrap["metric"].eq("realized_return")].iloc[0]
    return {
        "schema_version": "2026-07-09.6",
        "generated_at_utc": summary["generated_at_utc"],
        "run_tag": RUN_TAG,
        "status": "active_ijds_policy",
        "selection_protocol": {
            **summary["selection_audit"],
            "calibration_metadata": summary["calibration_metadata"],
            "selector_forbidden_columns_present": summary["selector_forbidden_columns_present"],
        },
        "selected_policy": summary["selected_policy"],
        "full_oot": {
            "n_candidates": int(full["n_panel"]),
            "n_funded": int(full["n_funded"]),
            "total_allocated": float(full["total_allocated"]),
            "expected_objective": float(full["expected_objective"]),
            "realized_return": float(full["realized_return"]),
            "weighted_default_rate": float(full["weighted_outcome"]),
            "weighted_miscoverage": float(full["weighted_miscoverage"]),
            "weighted_pd_point": float(full["weighted_pd_point"]),
            "weighted_pd_effective": float(full["weighted_pd_effective"]),
            "Gamma_CP": float(full["gamma_cp"]),
            "Gamma_internalized": float(full["gamma_internalized"]),
            "Gamma_residual": float(full["gamma_residual"]),
            "endpoint_budget": float(full["endpoint_budget"]),
            "markov_loss_threshold": float(full["markov_loss_threshold"]),
            "observed_accounting_bound": float(
                full["endpoint_budget"] + full["weighted_miscoverage"]
            ),
            "markov_tail_probability_bound": float(np.sqrt(summary["design"]["alpha"])),
        },
        "point_pd_contrast": {
            "realized_return": float(point["realized_return"]),
            "weighted_default_rate": float(point["weighted_outcome"]),
            "weighted_miscoverage": float(point["weighted_miscoverage"]),
            "endpoint_budget": float(point["endpoint_budget"]),
            "markov_loss_threshold": float(point["markov_loss_threshold"]),
            "selected_return_cost": float(point["realized_return"] - full["realized_return"]),
            "selected_return_cost_pct": float(
                (point["realized_return"] - full["realized_return"]) / point["realized_return"]
            ),
            "selected_default_reduction": float(
                point["weighted_outcome"] - full["weighted_outcome"]
            ),
            "selected_threshold_reduction": float(
                point["markov_loss_threshold"] - full["markov_loss_threshold"]
            ),
        },
        "bootstrap_return_interval": {
            "p025": float(return_boot["boot_p025"]),
            "p975": float(return_boot["boot_p975"]),
            "n_draws": int(return_boot["n_draws"]),
        },
        "exact_alpha_reference_replay": exact_summary["reference_replay"],
        "paper_tables": {
            key: [str(path.relative_to(ROOT).as_posix()) for path in paths]
            for key, paths in table_paths.items()
        },
        "retired_active_claims": [
            "alpha01 intervals obtained by cross-family average-width scaling",
            "8/8 approximate alpha-grid pass as a headline certificate",
            "50,010-policy frontier as the active selector",
            "0.345084 Markov threshold",
            "capped_blended_uncertainty with delta_cap_quantile=0.975",
            "OOT-outcome-selected portfolio hyperparameters",
            "the exploratory 25-policy gamma=0.35, threshold-cap=0.65 challenger",
        ],
        "claim_boundary": summary["claim_boundary"],
    }


def run(*, bootstrap_draws: int, bootstrap_seed: int) -> dict[str, Any]:
    summary = load_json(MODEL_DIR / "calibration_selected_policy_summary.json")
    exact_summary = load_json(EXACT_MODEL_DIR / "exact_alpha_grid_summary.json")
    grid = pd.read_parquet(DATA_DIR / "calibration_policy_selection_grid.parquet")
    evaluation = pd.read_csv(DATA_DIR / "calibration_selected_policy_oot_evaluation.csv")
    allocations = pd.read_parquet(
        DATA_DIR / "calibration_selected_policy_full_oot_allocations.parquet"
    )
    tables = {
        "alpha": build_alpha_table(exact_summary),
        "selector": build_selector_table(grid, summary),
        "temporal": build_temporal_table(evaluation),
        "grade": build_grade_table(allocations),
        "bootstrap": build_bootstrap_table(
            allocations,
            evaluation,
            n_draws=bootstrap_draws,
            seed=bootstrap_seed,
        ),
        "baseline": build_baseline_table(evaluation),
    }
    table_paths = {
        key: write_table(TABLE_NAMES[key], frame, table_dir=TABLE_DIR, root=ROOT)
        for key, frame in tables.items()
    }
    governance = build_governance(
        summary,
        exact_summary,
        evaluation,
        tables["bootstrap"],
        table_paths,
    )
    write_json(MODEL_DIR / GOVERNANCE_NAME, governance)
    return governance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-draws", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260709)
    args = parser.parse_args()
    payload = run(
        bootstrap_draws=max(100, int(args.bootstrap_draws)),
        bootstrap_seed=int(args.bootstrap_seed),
    )
    print(json.dumps(payload["full_oot"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
