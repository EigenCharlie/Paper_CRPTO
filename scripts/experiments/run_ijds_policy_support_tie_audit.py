"""Run the locked outcome-free IJDS policy-support and solver-tie audit."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.standardized_credit_payoff import (  # noqa: E402
    contractual_rate_decimal,
    expected_objective_coefficients,
)
from src.ijds_audit.config import load_v4_config  # noqa: E402
from src.ijds_audit.policy_support import (  # noqa: E402
    build_cap_census,
    classify_cap,
    point_basis_diagnostics,
)
from src.ijds_audit.portfolio import PointPortfolioSession  # noqa: E402
from src.ijds_audit.protocol import load_recipes, verified_freeze_artifact_paths  # noqa: E402
from src.models.binary_conformal_guardrail import apply_binary_outcome_recipe  # noqa: E402
from src.utils.isolated_experiment import (  # noqa: E402
    OutputPaths,
    dataframe_schema,
    environment_provenance,
    git_provenance,
    implementation_provenance,
    prepare_output_paths as prepare_isolated_output_paths,
    relative_artifact_descriptor,
    require_clean_tagged_head,
    resolve_repo_input,
    sha256_file,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = ROOT / "configs/experiments/ijds_policy_support_tie_audit_2026-07-12.yaml"
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")
IMPLEMENTATION_PATHS = (
    Path("docs/research/ijds_policy_support_tie_audit_protocol_2026-07-12.md"),
    Path("scripts/experiments/run_ijds_policy_support_tie_audit.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/ijds_audit/config.py"),
    Path("src/ijds_audit/policy_support.py"),
    Path("src/ijds_audit/portfolio.py"),
    Path("src/ijds_audit/protocol.py"),
    Path("src/models/binary_conformal_guardrail.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_ijds_policy_support_tie_audit.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)
OUTCOME_TOKENS = ("status", "outcome", "default", "pymnt", "realized", "miscoverage")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the audit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the locked structural-audit contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Policy-support audit config must be a YAML mapping.")
    required = {
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "parent",
        "source_ingest",
        "family_audit",
        "comparator_support",
        "tie_audit",
        "claim_boundary",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Policy-support audit config is missing sections: {missing}.")
    if payload["protocol_status"] != "locked_outcome_free_structural_audit_before_execution":
        raise ValueError("Policy-support audit protocol is not locked.")
    family = payload["family_audit"]
    if [float(value) for value in family["risk_tolerances"]] != [0.15, 0.17, 0.19]:
        raise ValueError("The inherited risk-tolerance census changed.")
    if [float(value) for value in family["gamma_grid"]] != [0.0, 0.25, 0.5, 0.75, 1.0]:
        raise ValueError("The semantic gamma endpoint census changed.")
    if payload["claim_boundary"].get("outcome_columns_passed") != []:
        raise ValueError("The policy-support audit cannot accept outcome columns.")
    if payload["claim_boundary"].get("no_policy_promotion") is not True:
        raise ValueError("Policy promotion must remain forbidden.")
    if payload["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Policy-support outputs must remain immutable.")
    return cast(dict[str, Any], payload)


def prepare_output_paths(config: Mapping[str, Any], *, repo_root: Path = ROOT) -> OutputPaths:
    """Create fresh, contained audit output directories."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _verified_parent_paths(
    config: Mapping[str, Any], *, repo_root: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    parent = config["parent"]
    descriptor = parent["protocol_freeze"]
    freeze_path = (repo_root / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(freeze_path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Parent protocol freeze mismatch for {field}.")
    freeze = _json(freeze_path)
    expected = {
        "run_tag": str(parent["run_tag"]),
        "protocol_tag": str(parent["protocol_tag"]),
        "protocol_commit": str(parent["protocol_commit"]),
        "status": "outcome_free_allocations_frozen_before_archive_outcome_join",
    }
    for field, value in expected.items():
        if freeze.get(field) != value:
            raise RuntimeError(f"Parent freeze field mismatch: {field}.")
    if freeze.get("outcome_columns_passed_to_policy_or_comparator") != []:
        raise RuntimeError("Parent outcome-free freeze reports an outcome column.")
    return verified_freeze_artifact_paths(freeze, repo_root=repo_root), freeze


def _load_decision_base(
    *,
    scores_path: Path,
    raw_path: Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    source = config["source_ingest"]
    if sha256_file(raw_path) != str(source["raw_sha256"]):
        raise RuntimeError("Raw archive hash does not match the locked audit source.")
    scores = pd.read_parquet(scores_path)
    roles = {str(value) for value in config["family_audit"]["roles"]}
    score_frame = scores.loc[scores["design_split"].isin(roles)].copy()
    score_frame["id"] = score_frame["id"].astype("string")
    if bool(score_frame["id"].duplicated().any()):
        raise RuntimeError("Frozen decision scores contain duplicate IDs.")
    target_ids = set(score_frame["id"].astype(str))
    allowed = [str(value) for value in source["allowed_raw_columns"]]
    if any(token in column.casefold() for column in allowed for token in OUTCOME_TOKENS):
        raise ValueError("Raw-column allowlist contains an outcome-like name.")
    pieces: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        raw_path,
        usecols=allowed,
        dtype={"id": "string"},
        chunksize=int(source["chunksize"]),
        low_memory=False,
    ):
        selected = chunk.loc[chunk["id"].astype(str).isin(target_ids)]
        if not selected.empty:
            pieces.append(selected)
    raw = pd.concat(pieces, ignore_index=True)
    raw["id"] = raw["id"].astype("string")
    if bool(raw["id"].duplicated().any()) or set(raw["id"].astype(str)) != target_ids:
        raise RuntimeError("Raw decision fields do not align one-to-one with frozen scores.")
    frame = score_frame.merge(raw, on="id", how="left", validate="one_to_one")
    frame = frame.rename(columns={"pd_catboost_platt": "pd_point"})
    frame["issue_d"] = pd.to_datetime(frame["issue_d"])
    frame["loan_amnt"] = pd.to_numeric(frame["loan_amnt"], errors="raise").astype(float)
    frame["purpose"] = frame["purpose"].astype("string").fillna("unknown")
    frame["contractual_rate"] = contractual_rate_decimal(frame["int_rate"])
    frame = frame.drop(columns=["int_rate", "pd_numeric_logistic_platt"])
    forbidden = [
        column
        for column in frame.columns
        if any(token in str(column).casefold() for token in OUTCOME_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"Decision base contains forbidden columns: {forbidden}.")
    counts = frame["design_split"].value_counts().to_dict()
    expected = {"policy_development": 94_885, "primary_oot": 376_890}
    if counts != expected:
        raise RuntimeError(f"Decision role census changed: {counts}.")
    return frame.sort_values(["issue_d", "id"], kind="mergesort").reset_index(drop=True)


def _portfolio_session(
    month: pd.DataFrame,
    *,
    score: np.ndarray,
    objective: np.ndarray,
    parent_config: Mapping[str, Any],
    threads: int,
) -> PointPortfolioSession:
    return PointPortfolioSession(
        month,
        point_score=score,
        objective_rate=objective,
        budget=float(parent_config["policy"]["budget"]),
        purpose_cap=float(parent_config["policy"]["max_concentration_by_purpose"]),
        time_limit=int(parent_config["execution"]["solver_time_limit_seconds"]),
        threads=int(threads),
    )


def _period_frames(base: pd.DataFrame, role: str) -> tuple[tuple[str, pd.DataFrame], ...]:
    frame = base.loc[base["design_split"].eq(role)].copy()
    periods = frame["issue_d"].dt.to_period("M")
    return tuple(
        (str(period), frame.loc[periods.eq(period)].copy()) for period in sorted(periods.unique())
    )


def _run_family_audit(
    base: pd.DataFrame,
    recipes: Mapping[str, Any],
    parent_records: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, float]]:
    family = config["family_audit"]
    tolerances = [float(value) for value in family["risk_tolerances"]]
    gammas = [float(value) for value in family["gamma_grid"]]
    cap_tolerance = float(family["cap_classification_tolerance"])
    threads = int(config["tie_audit"]["threads"])
    budget = float(parent_config["policy"]["budget"])
    point = base["pd_point"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    windows = recipes["catboost_platt"]
    for window_index, (window_id, group_recipes) in enumerate(sorted(windows.items()), start=1):
        logger.info("Family domain: window {}/8 {}", window_index, window_id)
        _, _, upper = apply_binary_outcome_recipe(point, group_recipes[5])
        for gamma in gammas:
            effective = point + gamma * (upper - point)
            scored = base.assign(pd_effective=effective, conformal_upper=upper)
            for role in ("policy_development", "primary_oot"):
                for period, month in _period_frames(scored, role):
                    q = month["pd_effective"].to_numpy(dtype=float)
                    p = month["pd_point"].to_numpy(dtype=float)
                    rates = month["contractual_rate"].to_numpy(dtype=float)
                    objective = expected_objective_coefficients(
                        p, rates, lgd=float(parent_config["payoff"]["lgd"])
                    )
                    minimum_session = _portfolio_session(
                        month,
                        score=q,
                        objective=-q,
                        parent_config=parent_config,
                        threads=threads,
                    )
                    minimum = minimum_session.solve(1.0)
                    session = _portfolio_session(
                        month,
                        score=q,
                        objective=objective,
                        parent_config=parent_config,
                        threads=threads,
                    )
                    unconstrained = session.solve(1.0)
                    q_min = float(minimum.weighted_point_score)
                    q_obj = float(unconstrained.weighted_point_score)
                    score_range = q_obj - q_min
                    if score_range < -cap_tolerance:
                        raise RuntimeError("Effective-score feasible range has reversed endpoints.")
                    for tau in tolerances:
                        classification = classify_cap(
                            tau,
                            minimum_feasible_score=q_min,
                            unconstrained_objective_score=q_obj,
                            tolerance=cap_tolerance,
                        )
                        solution = None if classification == "infeasible" else session.solve(tau)
                        realized_score = (
                            float("nan")
                            if solution is None
                            else float(solution.weighted_point_score)
                        )
                        rows.append(
                            {
                                "window_id": window_id,
                                "role": role,
                                "period": period,
                                "gamma": gamma,
                                "risk_tolerance": tau,
                                "candidate_rows": int(len(month)),
                                "minimum_feasible_score": q_min,
                                "unconstrained_objective_score": q_obj,
                                "decision_score_range": score_range,
                                "cap_classification": classification,
                                "weighted_effective_score": realized_score,
                                "cap_slack": (
                                    float("nan") if solution is None else tau - realized_score
                                ),
                                "cap_binding": bool(
                                    solution is not None
                                    and abs(tau - realized_score) <= cap_tolerance
                                ),
                                "total_allocated": (
                                    float("nan")
                                    if solution is None
                                    else float(solution.total_allocated)
                                ),
                                "budget_residual": (
                                    float("nan")
                                    if solution is None
                                    else float(solution.total_allocated - budget)
                                ),
                                "expected_objective": (
                                    float("nan")
                                    if solution is None
                                    else float(solution.objective_value)
                                ),
                                "effective_minus_point_mean": float(np.mean(q - p)),
                                "upper_saturated_share": float(
                                    np.mean(
                                        month["conformal_upper"].to_numpy(dtype=float)
                                        >= 1.0 - 1e-12
                                    )
                                ),
                            }
                        )
    result = pd.DataFrame(rows)
    expected_rows = 8 * (11 + 15) * 5 * 3
    if len(result) != expected_rows:
        raise RuntimeError(f"Policy-family audit produced {len(result)} rows, not {expected_rows}.")

    parent = parent_records.loc[
        parent_records["comparator_rule"].eq("guardrail")
        & parent_records["role"].isin(family["roles"]),
        [
            "window_id",
            "role",
            "period",
            "gamma",
            "risk_tolerance",
            "weighted_pd_effective",
            "expected_objective",
        ],
    ].rename(
        columns={
            "weighted_pd_effective": "parent_weighted_effective_score",
            "expected_objective": "parent_expected_objective",
        }
    )
    merged = result.merge(
        parent,
        on=["window_id", "role", "period", "gamma", "risk_tolerance"],
        how="left",
        validate="one_to_one",
    )
    interior = merged["gamma"].isin(family["inherited_interior_gammas"])
    if int(interior.sum()) != 1_872 or bool(
        merged.loc[interior, "parent_expected_objective"].isna().any()
    ):
        raise RuntimeError("Inherited policy-family reconstruction lost a frozen cell.")
    merged["parent_score_difference"] = (
        merged["weighted_effective_score"] - merged["parent_weighted_effective_score"]
    )
    merged["parent_objective_difference"] = (
        merged["expected_objective"] - merged["parent_expected_objective"]
    )
    score_difference = float(merged.loc[interior, "parent_score_difference"].abs().max())
    objective_difference = float(merged.loc[interior, "parent_objective_difference"].abs().max())
    if score_difference > float(family["reconstruction_score_tolerance"]):
        raise RuntimeError(f"Frozen funded-score reconstruction drifted by {score_difference}.")
    if objective_difference > float(family["reconstruction_objective_tolerance"]):
        raise RuntimeError(f"Frozen objective reconstruction drifted by {objective_difference}.")
    return merged, {
        "maximum_absolute_parent_score_difference": score_difference,
        "maximum_absolute_parent_objective_difference": objective_difference,
    }


def _run_point_cap_audit(
    base: pd.DataFrame,
    solve_records: pd.DataFrame,
    comparator_support: pd.DataFrame,
    frontier: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    parent_config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tie = config["tie_audit"]
    support = config["comparator_support"]
    primary = _period_frames(base, "primary_oot")
    periods = [period for period, _ in primary]
    broad_values = [float(value) for value in support["broad_stress"]]
    if len(broad_values) != 2:
        raise ValueError("Broad comparator stress support requires two endpoints.")
    census = build_cap_census(
        solve_records,
        comparator_support,
        frontier,
        periods=periods,
        broad_support=(broad_values[0], broad_values[1]),
        tolerance=float(support["cap_deduplication_tolerance"]),
    )
    rows: list[dict[str, Any]] = []
    sensitivity_inputs: dict[str, list[dict[str, Any]]] = {}
    for period_index, (period, month) in enumerate(primary, start=1):
        logger.info("Point-cap basis census: month {}/15 {}", period_index, period)
        point = month["pd_point"].to_numpy(dtype=float)
        rates = month["contractual_rate"].to_numpy(dtype=float)
        objective = expected_objective_coefficients(
            point, rates, lgd=float(parent_config["payoff"]["lgd"])
        )
        minimum_session = _portfolio_session(
            month,
            score=point,
            objective=-point,
            parent_config=parent_config,
            threads=int(tie["threads"]),
        )
        point_minimum = minimum_session.solve(1.0).weighted_point_score
        session = _portfolio_session(
            month,
            score=point,
            objective=objective,
            parent_config=parent_config,
            threads=int(tie["threads"]),
        )
        point_objective = session.solve(1.0).weighted_point_score
        period_caps = census.loc[census["period"].eq(period)]
        for cap_row in period_caps.itertuples(index=False):
            cap = float(cap_row.point_cap)
            classification = classify_cap(
                cap,
                minimum_feasible_score=float(point_minimum),
                unconstrained_objective_score=float(point_objective),
                tolerance=float(config["family_audit"]["cap_classification_tolerance"]),
            )
            if classification == "infeasible":
                raise RuntimeError(f"Declared point support is infeasible in {period}: {cap}.")
            solution = session.solve(cap)
            diagnostics = point_basis_diagnostics(
                session,
                solution,
                dual_tolerance=float(tie["dual_tolerance"]),
                primal_tolerance=float(tie["primal_tolerance"]),
            )
            if abs(float(diagnostics["objective_reconciliation_error"])) > float(
                tie["objective_reconciliation_tolerance"]
            ):
                raise RuntimeError(f"Point objective failed reconciliation at {period}/{cap}.")
            row = {
                **cap_row._asdict(),
                "cap_classification": classification,
                "minimum_feasible_point_score": float(point_minimum),
                "unconstrained_objective_point_score": float(point_objective),
                "weighted_point_score": float(solution.weighted_point_score),
                "point_cap_slack": float(cap - solution.weighted_point_score),
                "cap_binding": bool(
                    abs(cap - solution.weighted_point_score)
                    <= float(config["family_audit"]["cap_classification_tolerance"])
                ),
                "expected_objective": float(solution.objective_value),
                "basis_cap_lower": float(solution.basis_cap_lower),
                "basis_cap_upper": float(solution.basis_cap_upper),
                **diagnostics,
            }
            rows.append(row)
            if bool(diagnostics["basis_primal_degenerate"]) or int(
                diagnostics["near_zero_nonbasic_reduced_costs"]
            ):
                sensitivity_inputs.setdefault(period, []).append(
                    {
                        "point_cap": cap,
                        "base_exposure": solution.exposure.copy(),
                        "base_objective": float(solution.objective_value),
                        "base_weighted_point": float(solution.weighted_point_score),
                    }
                )
    diagnostics_frame = pd.DataFrame(rows)
    if len(diagnostics_frame) != len(census):
        raise RuntimeError("Point-cap diagnostics lost a census row.")

    sensitivity_rows: list[dict[str, Any]] = []
    primary_by_period = dict(primary)
    for period, items in sorted(sensitivity_inputs.items()):
        month = primary_by_period[period]
        original_ids = month["id"].astype("string").to_numpy()
        reversed_month = month.sort_values("id", ascending=False, kind="mergesort").copy()
        reversed_point = reversed_month["pd_point"].to_numpy(dtype=float)
        reversed_objective = expected_objective_coefficients(
            reversed_point,
            reversed_month["contractual_rate"].to_numpy(dtype=float),
            lgd=float(parent_config["payoff"]["lgd"]),
        )
        reversed_session = _portfolio_session(
            reversed_month,
            score=reversed_point,
            objective=reversed_objective,
            parent_config=parent_config,
            threads=int(tie["threads"]),
        )
        for item in items:
            reversed_solution = reversed_session.solve(float(item["point_cap"]))
            reversed_exposure = pd.Series(
                reversed_solution.exposure,
                index=reversed_month["id"].astype("string"),
            ).reindex(original_ids)
            if bool(reversed_exposure.isna().any()):
                raise RuntimeError("Reordered tie audit lost a candidate ID.")
            base_exposure = np.asarray(item["base_exposure"], dtype=float)
            distance = float(
                np.abs(base_exposure - reversed_exposure.to_numpy(dtype=float)).sum()
                / (base_exposure.sum() + reversed_solution.exposure.sum())
            )
            objective_difference = float(
                reversed_solution.objective_value - float(item["base_objective"])
            )
            if abs(objective_difference) > float(tie["objective_reconciliation_tolerance"]):
                raise RuntimeError(
                    f"Column-order objective instability at {period}/{item['point_cap']}."
                )
            sensitivity_rows.append(
                {
                    "period": period,
                    "point_cap": float(item["point_cap"]),
                    "allocation_distance": distance,
                    "objective_difference": objective_difference,
                    "weighted_point_difference": float(
                        reversed_solution.weighted_point_score - float(item["base_weighted_point"])
                    ),
                    "tie_sensitive": bool(distance > float(tie["order_sensitivity_tolerance"])),
                }
            )
    sensitivity = pd.DataFrame(
        sensitivity_rows,
        columns=[
            "period",
            "point_cap",
            "allocation_distance",
            "objective_difference",
            "weighted_point_difference",
            "tie_sensitive",
        ],
    )
    return diagnostics_frame, sensitivity


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", double_precision=15))


def _compact_summary(
    family: pd.DataFrame,
    reconstruction: Mapping[str, float],
    diagnostics: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> dict[str, Any]:
    family_counts = (
        family.groupby(
            ["role", "gamma", "risk_tolerance", "cap_classification"],
            observed=True,
            sort=True,
        )
        .size()
        .rename("cells")
        .reset_index()
    )
    source_columns = [column for column in diagnostics if column.startswith("is_")]
    support_rows = []
    for column in source_columns:
        selected = diagnostics.loc[diagnostics[column]]
        support_rows.append(
            {
                "source": column.removeprefix("is_"),
                "cap_month_rows": int(len(selected)),
                "decision_active": int(selected["cap_classification"].eq("decision_active").sum()),
                "objective_slack": int(selected["cap_classification"].eq("objective_slack").sum()),
                "near_zero_bases": int(selected["near_zero_nonbasic_reduced_costs"].gt(0).sum()),
                "primal_degenerate_bases": int(selected["basis_primal_degenerate"].sum()),
            }
        )
    inherited = family["gamma"].isin([0.25, 0.5, 0.75])
    gamma_one = family["gamma"].eq(1.0)
    return {
        "family": {
            "rows": int(len(family)),
            "inherited_rows": int(inherited.sum()),
            "inherited_infeasible": int(
                family.loc[inherited, "cap_classification"].eq("infeasible").sum()
            ),
            "inherited_decision_active": int(
                family.loc[inherited, "cap_classification"].eq("decision_active").sum()
            ),
            "gamma_one_infeasible": int(
                family.loc[gamma_one, "cap_classification"].eq("infeasible").sum()
            ),
            "gamma_one_decision_active": int(
                family.loc[gamma_one, "cap_classification"].eq("decision_active").sum()
            ),
            "gamma_one_objective_slack": int(
                family.loc[gamma_one, "cap_classification"].eq("objective_slack").sum()
            ),
            "classification_counts": _records(family_counts),
            **dict(reconstruction),
        },
        "point_cap_census": {
            "rows": int(len(diagnostics)),
            "periods": int(diagnostics["period"].nunique()),
            "named_unique_cap_months": int(
                diagnostics[
                    [
                        "is_named_c0",
                        "is_named_c1",
                        "is_named_c2",
                    ]
                ]
                .any(axis=1)
                .sum()
            ),
            "minimum_absolute_nonbasic_reduced_cost": float(
                diagnostics["minimum_absolute_nonbasic_reduced_cost"].min()
            ),
            "near_zero_bases": int(diagnostics["near_zero_nonbasic_reduced_costs"].gt(0).sum()),
            "primal_degenerate_bases": int(diagnostics["basis_primal_degenerate"].sum()),
            "maximum_dual_sign_violation": float(diagnostics["maximum_dual_sign_violation"].max()),
            "maximum_objective_reconciliation_error": float(
                diagnostics["objective_reconciliation_error"].abs().max()
            ),
            "support_sources": support_rows,
        },
        "order_sensitivity": {
            "triggered_rows": int(len(sensitivity)),
            "tie_sensitive_rows": int(
                sensitivity["tie_sensitive"].sum() if not sensitivity.empty else 0
            ),
            "maximum_allocation_distance": float(
                sensitivity["allocation_distance"].max() if not sensitivity.empty else 0.0
            ),
            "maximum_absolute_objective_difference": float(
                sensitivity["objective_difference"].abs().max() if not sensitivity.empty else 0.0
            ),
        },
    }


def run_audit(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the tagged audit and return its deterministic summary path."""
    started_at = utc_now_iso()
    started_counter = time.perf_counter()
    config_path = resolve_repo_input(config_path, repo_root=repo_root)
    config = load_config(config_path)
    protocol_commit = require_clean_tagged_head(repo_root, str(config["protocol_tag"]))
    initial_git = git_provenance(repo_root)
    implementation_start = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    parent_paths, parent_freeze = _verified_parent_paths(config, repo_root=repo_root)
    parent_config_path = resolve_repo_input(config["parent"]["config"], repo_root=repo_root)
    parent_config = load_v4_config(parent_config_path)
    raw_path = resolve_repo_input(config["source_ingest"]["raw_path"], repo_root=repo_root)
    base = _load_decision_base(
        scores_path=parent_paths["scores"],
        raw_path=raw_path,
        config=config,
    )
    recipes = load_recipes(parent_paths["recipes"])
    solve_records = pd.read_parquet(parent_paths["solve_records"])
    comparator_support = pd.read_parquet(parent_paths["comparator_support"])
    frontier = pd.read_parquet(parent_paths["frontier_breakpoints"])
    paths = prepare_output_paths(config, repo_root=repo_root)
    protocol_freeze = atomic_write_json(
        paths.model_dir / "protocol_freeze.json",
        {
            "schema_version": str(config["schema_version"]),
            "status": "outcome_free_policy_support_tie_audit_frozen",
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "claim_boundary": dict(config["claim_boundary"]),
            "outcome_columns_passed": [],
            "parent_protocol_freeze": config["parent"]["protocol_freeze"],
            "parent_outcome_free_artifacts": parent_freeze["outcome_free_artifacts"],
            "raw_source": relative_artifact_descriptor(raw_path, repo_root=repo_root),
            "implementation_provenance": implementation_start,
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )

    family, reconstruction = _run_family_audit(
        base,
        recipes,
        solve_records,
        config=config,
        parent_config=parent_config,
    )
    diagnostics, sensitivity = _run_point_cap_audit(
        base,
        solve_records,
        comparator_support,
        frontier,
        config=config,
        parent_config=parent_config,
    )
    output = config["output"]
    frames = {
        str(output["family_feasibility"]): family,
        str(output["point_cap_diagnostics"]): diagnostics,
        str(output["order_sensitivity"]): sensitivity,
    }
    written: dict[Path, pd.DataFrame] = {}
    for filename, frame in frames.items():
        path = atomic_write_parquet(frame, paths.data_dir / filename, index=False)
        written[path] = frame
    implementation_end = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Policy-support implementation changed during execution.")
    artifacts = {
        descriptor["path"]: descriptor
        for descriptor in [
            relative_artifact_descriptor(protocol_freeze, repo_root=repo_root),
            *(relative_artifact_descriptor(path, repo_root=repo_root) for path in written),
        ]
    }
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": (
            "Outcome-free structural evidence only. No empirical metric, direction, "
            "policy promotion, universal comparator support, or selected-set claim."
        ),
        "outcome_columns_passed": [],
        "results": _compact_summary(family, reconstruction, diagnostics, sensitivity),
        "parent_protocol_freeze": config["parent"]["protocol_freeze"],
        "raw_source": relative_artifact_descriptor(raw_path, repo_root=repo_root),
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": {
            relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
            for path, frame in written.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    summary_path = atomic_write_json(paths.model_dir / str(output["deterministic_result"]), summary)
    receipt = {
        "run_tag": str(config["run_tag"]),
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "initial_git": initial_git,
        "final_git": git_provenance(repo_root),
        "environment": environment_provenance(repo_root),
        "deterministic_summary": relative_artifact_descriptor(summary_path, repo_root=repo_root),
    }
    atomic_write_json(paths.model_dir / str(output["execution_receipt"]), receipt)
    logger.info("Policy-support and tie audit complete: {}", summary_path)
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI entry point."""
    args = parse_args(argv)
    run_audit(config_path=args.config)


if __name__ == "__main__":
    main()
