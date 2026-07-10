"""Select a simple CRPTO policy without consulting OOT outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.experiments.ijds_policy_support import (  # noqa: E402
    evaluate_candidate,
    load_policy_panel,
    solve_candidate,
)
from scripts.generate_conformal_intervals import (  # noqa: E402
    _build_probability_lookups,
    _build_tuning_split,
    _load_conformal_inputs,
)
from src.models.conformal_alpha_grid import (  # noqa: E402
    FrozenConformalRecipe,
    compute_exact_alpha_intervals,
)
from src.optimization.policy_evaluation import PolicyAllocationResult  # noqa: E402
from src.optimization.policy_selection import (  # noqa: E402
    FORBIDDEN_POLICY_SELECTION_COLUMNS,
    LinearPolicyCandidate,
    build_linear_policy_grid,
    select_policy_result_ex_ante,
)
from src.utils.script_helpers import (  # noqa: E402
    parse_percent_series,
    resolve_repo_artifact_path,
    write_json,
)

DEFAULT_CONFIG = (
    ROOT / "configs/experiments/champion_reopen_ijds_calibration_selected_simple90_v6.yaml"
)
FORBIDDEN_SELECTOR_COLUMNS = FORBIDDEN_POLICY_SELECTION_COLUMNS


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Experiment config must contain a mapping.")
    return payload


def _load_pickle_mapping(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict):
        raise TypeError("Frozen conformal results must contain a mapping.")
    return payload


def _experiment_paths(run_tag: str) -> tuple[Path, Path]:
    data_dir = ROOT / "data/processed/experiments/champion_reopen" / run_tag / "portfolio"
    model_dir = ROOT / "models/experiments/champion_reopen" / run_tag / "portfolio"
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, model_dir


def _load_calibration_selection_panel(
    config: dict[str, Any],
) -> tuple[pd.DataFrame, FrozenConformalRecipe, dict[str, Any]]:
    source = config["source"]
    design = config["design"]
    os.environ["UPSTREAM_CANONICAL_RUN_TAG"] = str(source["upstream_canonical_run_tag"])
    results_path = resolve_repo_artifact_path(source["conformal_results_path"], root=ROOT)
    payload = _load_pickle_mapping(results_path)
    recipe = FrozenConformalRecipe.from_results_payload(payload)
    inputs = _load_conformal_inputs(
        calibration_fraction=recipe.calibration_fraction,
        calibrator_override_path=(str(payload.get("calibrator_override_path", "")).strip() or None),
    )
    split = _build_tuning_split(
        cal_df=inputs.cal_df,
        test_df=inputs.test_df,
        X_cal=inputs.X_cal,
        y_cal=inputs.y_cal,
        group_cal_base=inputs.group_cal_base,
        y_prob_cal_raw=inputs.y_prob_cal_raw,
        tuning_holdout_ratio=recipe.tuning_holdout_ratio,
        tuning_random_state=recipe.tuning_random_state,
    )
    probability_fit, probability_tune, _probability_test = _build_probability_lookups(
        inputs,
        split,
    )
    intervals = compute_exact_alpha_intervals(
        recipe=recipe,
        target_alpha=float(design["alpha"]),
        y_cal=split.y_cal_fit,
        interval_probability_cal=probability_fit["calibrated"],
        interval_probability_eval=probability_tune["calibrated"],
        partition_probability_cal=probability_fit[recipe.partition_probability_source],
        partition_probability_eval=probability_tune[recipe.partition_probability_source],
        base_groups_cal=split.group_cal_fit_base,
        base_groups_eval=split.group_tune_base,
        issue_dates_eval=split.issue_tune,
    )
    panel = inputs.cal_df.iloc[split.idx_cal_tune].reset_index(drop=True).copy()
    panel["_pd_point"] = intervals.point
    panel["_pd_low"] = intervals.low
    panel["_pd_high"] = intervals.high
    panel["_loan_amount"] = pd.to_numeric(panel["loan_amnt"], errors="coerce").fillna(1.0)
    panel["_int_rate"] = parse_percent_series(panel["int_rate"])
    metadata = {
        "conformal_results_path": str(results_path.relative_to(ROOT)),
        "calibration_fit_rows": int(len(split.idx_cal_fit)),
        "calibration_selection_rows": int(len(split.idx_cal_tune)),
        "calibration_selection_start": str(pd.to_datetime(split.issue_tune).min().date()),
        "calibration_selection_end": str(pd.to_datetime(split.issue_tune).max().date()),
        "target_alpha": intervals.target_alpha,
        "used_alpha": intervals.used_alpha,
        "partition": recipe.partition,
    }
    return panel, recipe, metadata


def _measure_ex_ante_solution(
    frame: pd.DataFrame,
    candidate: LinearPolicyCandidate,
    result: PolicyAllocationResult,
    *,
    alpha: float,
) -> dict[str, Any]:
    exposure = result.allocation * frame["_loan_amount"].to_numpy(dtype=float)
    total_allocated = float(exposure.sum())
    if total_allocated <= 0.0:
        raise RuntimeError(f"Policy {candidate.candidate_id} allocated no calibration capital.")
    weights = exposure / total_allocated
    point = frame["_pd_point"].to_numpy(dtype=float)
    high = frame["_pd_high"].to_numpy(dtype=float)
    weighted_point = float(np.sum(weights * point))
    weighted_effective = float(np.sum(weights * result.effective_pd))
    endpoint_budget = float(np.sum(weights * high))
    return {
        **candidate.to_record(),
        "solver_status": str(result.solution.get("solver_status", "unknown")),
        "objective_risk_mode": result.objective_risk_mode,
        "expected_objective": float(result.solution["objective_value"]),
        "n_panel": int(len(frame)),
        "n_funded": int(np.count_nonzero(result.allocation > 0.01)),
        "total_allocated": total_allocated,
        "weighted_pd_point": weighted_point,
        "weighted_pd_effective": weighted_effective,
        "gamma_cp": float(np.sum(weights * (high - point))),
        "gamma_internalized": float(np.sum(weights * (result.effective_pd - point))),
        "gamma_residual": float(np.sum(weights * (high - result.effective_pd))),
        "endpoint_budget": endpoint_budget,
        "markov_loss_threshold": endpoint_budget + float(np.sqrt(alpha)),
        "effective_pd_cap_slack": float(candidate.risk_tolerance - weighted_effective),
    }


def _run_calibration_grid(
    panel: pd.DataFrame,
    candidates: list[LinearPolicyCandidate],
    *,
    config: dict[str, Any],
    output_path: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        logger.info("Calibration selector evaluating {}", candidate.candidate_id)
        result = solve_candidate(panel, candidate, config=config)
        rows.append(
            _measure_ex_ante_solution(
                panel,
                candidate,
                result,
                alpha=float(config["design"]["alpha"]),
            )
        )
    output = pd.DataFrame(rows)
    if FORBIDDEN_SELECTOR_COLUMNS.intersection(output.columns):
        raise AssertionError("Calibration selector artifact contains outcome-derived columns.")
    output.to_parquet(output_path, index=False)
    return output


def _match_candidate(
    candidates: list[LinearPolicyCandidate],
    settings: dict[str, Any],
) -> LinearPolicyCandidate:
    matches = [
        candidate
        for candidate in candidates
        if np.isclose(candidate.risk_tolerance, float(settings["risk_tolerance"]))
        and np.isclose(candidate.gamma, float(settings["gamma"]))
        and np.isclose(candidate.uncertainty_aversion, float(settings["uncertainty_aversion"]))
    ]
    if len(matches) != 1:
        raise ValueError(f"Policy settings must match exactly one candidate, got {len(matches)}.")
    return matches[0]


def _evaluate_fixed_policies(
    panel: pd.DataFrame,
    selected: LinearPolicyCandidate,
    incumbent: LinearPolicyCandidate,
    *,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods = ["full_oot", *list(config["design"]["period_order"])]
    rows: list[dict[str, Any]] = []
    allocation_frames: list[pd.DataFrame] = []
    for period in periods:
        frame = (
            panel.reset_index(drop=True)
            if period == "full_oot"
            else panel.loc[panel["_period"].astype(str).eq(period)].reset_index(drop=True)
        )
        point = LinearPolicyCandidate(
            candidate_id="point-pd",
            risk_tolerance=selected.risk_tolerance,
            gamma=0.0,
            uncertainty_aversion=0.0,
            policy_mode="point_estimate",
        )
        for role, candidate, robust in (
            ("calibration_selected", selected, True),
            ("incumbent_linear", incumbent, True),
            ("point_pd_matched_tau", point, False),
        ):
            record, result = evaluate_candidate(
                frame,
                candidate,
                config=config,
                robust=robust,
                period=period,
            )
            rows.append({"role": role, **record})
            if period == "full_oot":
                allocation_frames.append(
                    _funded_allocation_frame(
                        frame,
                        result,
                        role=role,
                        lgd=float(config["design"]["lgd"]),
                    )
                )
    return pd.DataFrame(rows), pd.concat(allocation_frames, ignore_index=True)


def _funded_allocation_frame(
    frame: pd.DataFrame,
    result: PolicyAllocationResult,
    *,
    role: str,
    lgd: float,
) -> pd.DataFrame:
    allocation = result.allocation
    funded = allocation > 0.01
    selected = frame.loc[funded].reset_index(drop=True).copy()
    selected_allocation = allocation[funded]
    exposure = selected_allocation * selected["_loan_amount"].to_numpy(dtype=float)
    total_exposure = float(exposure.sum())
    outcome = selected["_outcome"].to_numpy(dtype=float)
    rates = selected["_int_rate"].to_numpy(dtype=float)
    point = selected["_pd_point"].to_numpy(dtype=float)
    high = selected["_pd_high"].to_numpy(dtype=float)
    effective = result.effective_pd[funded]
    if "sub_grade" in selected.columns:
        loan_grade = selected["sub_grade"].astype(str).str[:1]
    elif "int_rate_bucket__grade" in selected.columns:
        loan_grade = selected["int_rate_bucket__grade"].astype(str).str.rsplit("__").str[-1]
    else:
        loan_grade = selected["grade"].astype(str)
    output = pd.DataFrame(
        {
            "role": role,
            "id": selected["id"].astype(str),
            "issue_d": selected["issue_d"],
            "grade": loan_grade,
            "conformal_group": selected["grade"].astype(str),
            "loan_amnt": selected["_loan_amount"].to_numpy(dtype=float),
            "int_rate": rates,
            "outcome": outcome,
            "pd_point": point,
            "pd_low": selected["_pd_low"].to_numpy(dtype=float),
            "pd_high": high,
            "pd_effective": effective,
            "allocation": selected_allocation,
            "funded_exposure": exposure,
            "funded_weight": exposure / total_exposure,
            "miscoverage": (outcome > high).astype(int),
            "expected_return_contribution": exposure * (rates - point * float(lgd)),
            "realized_return_contribution": np.where(
                outcome.astype(int) == 1,
                -float(lgd) * exposure,
                rates * exposure,
            ),
        }
    )
    return output


def _contrast_payload(evaluation: pd.DataFrame) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for period in ("full_oot", "2020+"):
        period_rows = evaluation.loc[evaluation["period"].eq(period)].set_index("role")
        selected = period_rows.loc["calibration_selected"]
        point = period_rows.loc["point_pd_matched_tau"]
        incumbent = period_rows.loc["incumbent_linear"]
        output[period] = {
            "selected_realized_return": float(selected["realized_return"]),
            "selected_weighted_outcome": float(selected["weighted_outcome"]),
            "selected_markov_threshold": float(selected["markov_loss_threshold"]),
            "return_cost_vs_point": float(point["realized_return"] - selected["realized_return"]),
            "default_delta_vs_point": float(
                selected["weighted_outcome"] - point["weighted_outcome"]
            ),
            "threshold_delta_vs_point": float(
                selected["markov_loss_threshold"] - point["markov_loss_threshold"]
            ),
            "return_delta_vs_incumbent": float(
                selected["realized_return"] - incumbent["realized_return"]
            ),
            "default_delta_vs_incumbent": float(
                selected["weighted_outcome"] - incumbent["weighted_outcome"]
            ),
        }
    return output


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def run(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    run_tag = str(config["run_tag"])
    data_dir, model_dir = _experiment_paths(run_tag)
    calibration_panel, recipe, calibration_metadata = _load_calibration_selection_panel(config)
    grid_config = config["policy_grid"]
    candidates = build_linear_policy_grid(
        risk_tolerances=[float(value) for value in grid_config["risk_tolerances"]],
        gammas=[float(value) for value in grid_config["gammas"]],
        uncertainty_aversions=[float(value) for value in grid_config["uncertainty_aversions"]],
    )
    selection_results = _run_calibration_grid(
        calibration_panel,
        candidates,
        config=config,
        output_path=data_dir / "calibration_policy_selection_grid.parquet",
    )
    selected_row, selection_audit = select_policy_result_ex_ante(
        selection_results,
        markov_threshold_cap=float(config["design"]["markov_threshold_cap"]),
        budget=float(config["design"]["budget"]),
        min_budget_utilization=float(config["design"]["selection_min_budget_utilization"]),
    )
    candidate_lookup = {candidate.candidate_id: candidate for candidate in candidates}
    selected = candidate_lookup[str(selected_row["candidate_id"])]
    incumbent = _match_candidate(candidates, config["incumbent_policy"])
    oot_panel = load_policy_panel(config)
    evaluation, allocations = _evaluate_fixed_policies(
        oot_panel,
        selected,
        incumbent,
        config=config,
    )
    evaluation_path = data_dir / "calibration_selected_policy_oot_evaluation.csv"
    allocation_path = data_dir / "calibration_selected_policy_full_oot_allocations.parquet"
    evaluation.to_csv(evaluation_path, index=False)
    allocations.to_parquet(allocation_path, index=False)
    payload: dict[str, Any] = {
        "schema_version": str(config["schema_version"]),
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_tag": run_tag,
        "source_commit": _git_commit(),
        "config_path": str(config_path.relative_to(ROOT)),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "design": config["design"],
        "calibration_metadata": calibration_metadata,
        "recipe": {
            "partition": recipe.partition,
            "partition_probability_source": recipe.partition_probability_source,
            "reference_target_alpha": recipe.reference_target_alpha,
            "reference_used_alpha": recipe.reference_used_alpha,
        },
        "grid_size": int(len(candidates)),
        "selector_columns": list(selection_results.columns),
        "selector_forbidden_columns_present": sorted(
            FORBIDDEN_SELECTOR_COLUMNS.intersection(selection_results.columns)
        ),
        "selection_audit": selection_audit,
        "selected_policy": selected.to_record(),
        "selected_calibration_metrics": selected_row.to_dict(),
        "incumbent_policy": incumbent.to_record(),
        "evaluation_path": str(evaluation_path.relative_to(ROOT)),
        "allocation_path": str(allocation_path.relative_to(ROOT)),
        "contrasts": _contrast_payload(evaluation),
        "claim_boundary": str(config["claim_boundary"]),
    }
    summary_path = model_dir / "calibration_selected_policy_summary.json"
    write_json(summary_path, payload)
    logger.info("Selected calibration-only policy: {}", selected.candidate_id)
    logger.info("Wrote calibration-only policy summary to {}", summary_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    payload = run(config_path.resolve())
    print(json.dumps(payload["contrasts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
