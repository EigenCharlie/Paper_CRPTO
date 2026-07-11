"""Run the locked post hoc IJDS comparator-stringency audit.

The audit consumes the immutable maturity-safe v2 decision and outcome panels.
It does not refit a model, alter the selected guardrail, or run a protected DVC
stage. Its purpose is to test whether a same-threshold point-PD comparison is
invariant to a development-matched point-risk comparator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experiments import run_ijds_maturity_safe_challenger as parent_runner  # noqa: E402
from src.evaluation.coverage_transport import (  # noqa: E402
    coverage_and_default_transport_bounds,
)
from src.evaluation.maturity_safe_portfolio import (  # noqa: E402
    MonthlyPolicySpec,
    aggregate_monthly_evaluation,
    evaluate_policy_specs_by_month,
)
from src.evaluation.policy_contrast_bounds import sharp_policy_contrast_bounds  # noqa: E402
from src.optimization.policy_selection import (  # noqa: E402
    LinearPolicyCandidate,
    build_linear_policy_grid,
)
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
    write_csv_atomic,
)
from src.utils.pipeline_runtime import (  # noqa: E402
    atomic_write_json,
    atomic_write_parquet,
    utc_now_iso,
)

DEFAULT_CONFIG_PATH = (
    ROOT
    / "configs"
    / "experiments"
    / "ijds_maturity_safe_locked_comparator_stringency_2026-07-10.yaml"
)
ALLOWED_DATA_ROOT = Path("data/processed/experiments/champion_reopen")
ALLOWED_MODEL_ROOT = Path("models/experiments/champion_reopen")
IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/run_ijds_comparator_stringency_audit.py"),
    Path("scripts/experiments/run_ijds_maturity_safe_challenger.py"),
    Path("src/evaluation/coverage_transport.py"),
    Path("src/evaluation/maturity_safe_portfolio.py"),
    Path("src/evaluation/policy_contrast_bounds.py"),
    Path("src/evaluation/standardized_credit_payoff.py"),
    Path("src/optimization/policy.py"),
    Path("src/optimization/policy_evaluation.py"),
    Path("src/optimization/policy_selection.py"),
    Path("src/optimization/portfolio_model.py"),
    Path("src/utils/isolated_experiment.py"),
    Path("src/utils/pipeline_runtime.py"),
    Path("tests/test_experiments/test_ijds_comparator_stringency_audit.py"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


@dataclass(frozen=True)
class ParentFrames:
    """Verified parent inputs needed by the downstream audit."""

    decision: pd.DataFrame
    outcomes: pd.DataFrame
    development_guardrail_monthly: pd.DataFrame
    parent_allocations: pd.DataFrame
    parent_summary: dict[str, Any]
    parent_config: dict[str, Any]
    evidence_path: Path
    summary_path: Path


@dataclass(frozen=True)
class AuditSpecs:
    """Closed policy census and comparator labels."""

    specs: list[MonthlyPolicySpec]
    family_pairs: list[tuple[str, str, str]]
    thresholds: pd.DataFrame
    selected_guardrail_label: str
    selected_match_label: str
    same_threshold_label: str
    sensitivity_labels: dict[str, str]
    selected_candidate_id: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the audit CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return cast(dict[str, Any], payload)


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the locked downstream audit contract."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Comparator audit config must be a YAML mapping.")
    required = {
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "posthoc_diagnostic_after_active_results",
        "parent",
        "primary_policy",
        "comparators",
        "family_census",
        "analysis",
        "decision_gate",
        "execution",
        "output",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Comparator audit config is missing sections: {missing}")
    if payload["protocol_status"] != "locked_posthoc_comparator_audit_before_execution":
        raise ValueError("Comparator audit protocol is not locked.")
    if payload["posthoc_diagnostic_after_active_results"] is not True:
        raise ValueError("The post hoc status must be explicit.")
    if payload["primary_policy"].get("promotion_locked") is not True:
        raise ValueError("The parent-selected guardrail must remain promotion-locked.")
    family = payload["family_census"]
    if family.get("oot_reselection_forbidden") is not True:
        raise ValueError("OOT reselection must be forbidden.")
    if family.get("family_claim_requires_same_direction") != "9_of_9":
        raise ValueError("A family claim must require all nine directions.")
    if payload["analysis"].get("purpose_concentration_sensitivity") is not False:
        raise ValueError("Purpose-cap sensitivity is outside this protocol.")
    if payload["output"].get("immutability") != "hard_no_overwrite_choose_fresh_run_tag":
        raise ValueError("Comparator outputs must use hard no-overwrite semantics.")
    return cast(dict[str, Any], payload)


def prepare_output_paths(
    config: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> OutputPaths:
    """Validate containment and create fresh downstream output paths."""
    return prepare_isolated_output_paths(
        dict(config),
        repo_root=repo_root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )


def _verify_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Parent artifact hash drifted for {path}: {actual} != {expected}.")


def _load_parent_frames(config: Mapping[str, Any], *, repo_root: Path) -> ParentFrames:
    parent = config["parent"]
    evidence_path = resolve_repo_input(parent["evidence_manifest"], repo_root=repo_root)
    evidence = _json(evidence_path)
    if evidence.get("run_tag") != parent["run_tag"]:
        raise RuntimeError("Parent evidence run tag does not match the locked config.")
    if evidence.get("protocol_tag") != parent["protocol_tag"]:
        raise RuntimeError("Parent evidence protocol tag does not match the locked config.")

    summary_path = resolve_repo_input(evidence["summary"]["path"], repo_root=repo_root)
    receipt_path = resolve_repo_input(evidence["receipt"]["path"], repo_root=repo_root)
    _verify_hash(summary_path, str(evidence["summary"]["sha256"]))
    _verify_hash(receipt_path, str(evidence["receipt"]["sha256"]))
    summary = _json(summary_path)
    if summary.get("status") != "complete" or summary.get("run_tag") != parent["run_tag"]:
        raise RuntimeError("Parent maturity-safe summary is not the complete locked run.")

    data_dir = (repo_root / str(parent["data_dir"])).resolve()
    required = {
        "decision": data_dir / "portfolio" / "decision_panel_outcome_free.parquet",
        "outcomes": data_dir / "portfolio" / "outcomes_post_decision_boundary.parquet",
        "development": data_dir / "portfolio" / "development_guardrail_monthly.csv",
        "allocations": data_dir / "portfolio" / "monthly_funded_allocations.parquet",
    }
    for path in required.values():
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(repo_root).as_posix()
        descriptor = summary["artifacts"].get(relative)
        if not isinstance(descriptor, dict):
            raise RuntimeError(f"Parent summary does not describe {relative}.")
        _verify_hash(path, str(descriptor["sha256"]))

    parent_config_path = resolve_repo_input(parent["config"], repo_root=repo_root)
    parent_config = parent_runner.load_config(parent_config_path)
    return ParentFrames(
        decision=pd.read_parquet(required["decision"]),
        outcomes=pd.read_parquet(required["outcomes"]),
        development_guardrail_monthly=pd.read_csv(required["development"]),
        parent_allocations=pd.read_parquet(required["allocations"]),
        parent_summary=summary,
        parent_config=parent_config,
        evidence_path=evidence_path,
        summary_path=summary_path,
    )


def _parent_guardrail_candidates(parent_config: Mapping[str, Any]) -> list[LinearPolicyCandidate]:
    policy = parent_config["policy"]
    candidates = build_linear_policy_grid(
        risk_tolerances=[float(value) for value in policy["risk_tolerances"]],
        gammas=[float(value) for value in policy["gammas"]],
        uncertainty_aversions=[float(value) for value in policy["uncertainty_aversions"]],
    )
    return [
        LinearPolicyCandidate(
            candidate_id=candidate.candidate_id,
            risk_tolerance=candidate.risk_tolerance,
            gamma=candidate.gamma,
            uncertainty_aversion=candidate.uncertainty_aversion,
            policy_mode=candidate.policy_mode,
            delta_cap_quantile=candidate.delta_cap_quantile,
            tail_focus_quantile=candidate.tail_focus_quantile,
            min_budget_utilization=float(policy["min_budget_utilization_solver"]),
            pd_cap_slack_penalty=candidate.pd_cap_slack_penalty,
        )
        for candidate in candidates
    ]


def _point_candidate(
    candidate_id: str,
    risk_tolerance: float,
    parent_config: Mapping[str, Any],
) -> LinearPolicyCandidate:
    return LinearPolicyCandidate(
        candidate_id=candidate_id,
        risk_tolerance=float(risk_tolerance),
        gamma=0.0,
        uncertainty_aversion=0.0,
        min_budget_utilization=float(parent_config["policy"]["min_budget_utilization_solver"]),
    )


def _derive_audit_specs(config: Mapping[str, Any], parent: ParentFrames) -> AuditSpecs:
    candidates = _parent_guardrail_candidates(parent.parent_config)
    monthly = parent.development_guardrail_monthly.copy()
    expected_ids = {candidate.candidate_id for candidate in candidates}
    if set(monthly["candidate_id"].astype(str)) != expected_ids:
        raise RuntimeError("Parent development grid does not contain the locked nine candidates.")

    threshold_rows: list[dict[str, Any]] = []
    specs: list[MonthlyPolicySpec] = []
    family_pairs: list[tuple[str, str, str]] = []
    selected_id = str(config["primary_policy"]["candidate_id"])
    selected_guardrail_label = str(config["primary_policy"]["label"])
    selected_match_label = str(config["comparators"]["development_matched"]["label"])

    for candidate in candidates:
        rows = monthly.loc[monthly["candidate_id"].astype(str).eq(candidate.candidate_id)]
        if len(rows) != 6:
            raise RuntimeError(f"Expected six development rows for {candidate.candidate_id}.")
        values = pd.to_numeric(rows["weighted_pd_point"], errors="raise").to_numpy(dtype=float)
        matched_tau = float(values.mean())
        guard_label = (
            selected_guardrail_label
            if candidate.candidate_id == selected_id
            else f"guardrail_{candidate.candidate_id}"
        )
        point_label = (
            selected_match_label
            if candidate.candidate_id == selected_id
            else f"development_matched_point_{candidate.candidate_id}"
        )
        threshold_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "guardrail_risk_tolerance": candidate.risk_tolerance,
                "gamma": candidate.gamma,
                "monthly_point_pd_min": float(values.min()),
                "matched_point_pd_mean": matched_tau,
                "monthly_point_pd_max": float(values.max()),
                "guardrail_label": guard_label,
                "point_label": point_label,
            }
        )
        specs.extend(
            [
                MonthlyPolicySpec(candidate, True, guard_label),
                MonthlyPolicySpec(
                    _point_candidate(
                        f"point-match-{candidate.candidate_id}",
                        matched_tau,
                        parent.parent_config,
                    ),
                    False,
                    point_label,
                ),
            ]
        )
        family_pairs.append((candidate.candidate_id, guard_label, point_label))

    thresholds = pd.DataFrame(threshold_rows).sort_values("candidate_id", kind="mergesort")
    selected = thresholds.loc[thresholds["candidate_id"].eq(selected_id)].iloc[0]
    locked = config["comparators"]["development_matched"]
    tolerance = float(config["comparators"]["matching_tolerance"])
    observed = {
        "low": float(selected["monthly_point_pd_min"]),
        "mid": float(selected["matched_point_pd_mean"]),
        "high": float(selected["monthly_point_pd_max"]),
    }
    expected = {key: float(value) for key, value in locked["sensitivity_risk_tolerances"].items()}
    if any(
        not np.isclose(observed[key], expected[key], rtol=0.0, atol=tolerance) for key in expected
    ):
        raise RuntimeError(f"Development-matched threshold derivation drifted: {observed}.")

    same = config["comparators"]["same_threshold"]
    same_threshold_label = str(same["label"])
    specs.append(
        MonthlyPolicySpec(
            _point_candidate(
                "point-same-threshold",
                float(same["risk_tolerance"]),
                parent.parent_config,
            ),
            False,
            same_threshold_label,
        )
    )
    sensitivity_labels: dict[str, str] = {"mid": selected_match_label}
    for key in ("low", "high"):
        label = f"development_matched_point_pd_{key}"
        sensitivity_labels[key] = label
        specs.append(
            MonthlyPolicySpec(
                _point_candidate(f"point-match-{key}", expected[key], parent.parent_config),
                False,
                label,
            )
        )
    return AuditSpecs(
        specs=specs,
        family_pairs=family_pairs,
        thresholds=thresholds,
        selected_guardrail_label=selected_guardrail_label,
        selected_match_label=selected_match_label,
        same_threshold_label=same_threshold_label,
        sensitivity_labels=sensitivity_labels,
        selected_candidate_id=selected_id,
    )


def _aggregate_evaluations(evaluation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role in sorted(evaluation["role"].astype(str).unique()):
        role_rows = evaluation.loc[evaluation["role"].astype(str).eq(role)]
        for label in sorted(role_rows["policy_label"].astype(str).unique()):
            record = aggregate_monthly_evaluation(
                role_rows.loc[role_rows["policy_label"].astype(str).eq(label)]
            )
            record["role"] = role
            rows.append(record)
    return pd.DataFrame(rows).sort_values(["role", "policy_label"], kind="mergesort")


def _evaluate_all_blocks(
    parent: ParentFrames,
    specs: AuditSpecs,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    evaluations: list[pd.DataFrame] = []
    allocations: list[pd.DataFrame] = []
    for role in ("policy_development", "primary_oot", "censored_extension"):
        decision = parent.decision.loc[parent.decision["design_split"].eq(role)].drop(
            columns="design_split"
        )
        evaluation, funded = evaluate_policy_specs_by_month(
            decision,
            parent.outcomes,
            specs.specs,
            config=parent.parent_config,
            role=role,
        )
        evaluations.append(evaluation)
        allocations.append(funded)
    result = pd.concat(evaluations, ignore_index=True)
    funded = pd.concat(allocations, ignore_index=True)
    if not bool(result["full_budget"].all()):
        raise RuntimeError("At least one comparator audit solve failed to use the full budget.")
    return result, funded


def _max_exposure_difference(
    left: pd.DataFrame,
    right: pd.DataFrame,
) -> float:
    keys = ["role", "period", "id"]
    merged = left[[*keys, "exposure"]].merge(
        right[[*keys, "exposure"]],
        on=keys,
        how="outer",
        suffixes=("_left", "_right"),
        validate="one_to_one",
    )
    return float(
        (merged["exposure_left"].fillna(0.0) - merged["exposure_right"].fillna(0.0)).abs().max()
    )


def _verify_parent_replay(
    parent: ParentFrames,
    allocations: pd.DataFrame,
    specs: AuditSpecs,
    *,
    tolerance: float,
) -> dict[str, float]:
    comparisons = {
        "selected_guardrail": (
            specs.selected_guardrail_label,
            "selected_conformal_guardrail",
        ),
        "same_threshold_point_pd": (
            specs.same_threshold_label,
            "matched_point_pd",
        ),
    }
    result: dict[str, float] = {}
    for name, (new_label, parent_label) in comparisons.items():
        new = allocations.loc[
            allocations["role"].isin(["primary_oot", "censored_extension"])
            & allocations["policy_label"].eq(new_label)
        ]
        old = parent.parent_allocations.loc[
            parent.parent_allocations["role"].isin(["primary_oot", "censored_extension"])
            & parent.parent_allocations["policy_label"].eq(parent_label)
        ]
        difference = _max_exposure_difference(new, old)
        result[name] = difference
        if difference > tolerance:
            raise RuntimeError(f"Parent allocation replay drifted for {name}: {difference}.")
    return result


def _contrasts_for_pairs(
    allocations: pd.DataFrame,
    pairs: Sequence[tuple[str, str, str]],
    *,
    role: str,
    lgd: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate_id, guardrail, point in pairs:
        record = sharp_policy_contrast_bounds(
            allocations,
            policy_a=guardrail,
            policy_b=point,
            role=role,
            lgd=lgd,
        )
        record["candidate_id"] = candidate_id
        rows.append(record)
    return pd.DataFrame(rows)


def _selected_primary_contrasts(
    allocations: pd.DataFrame,
    specs: AuditSpecs,
    *,
    lgd: float,
) -> pd.DataFrame:
    labels = [
        specs.same_threshold_label,
        specs.sensitivity_labels["low"],
        specs.sensitivity_labels["mid"],
        specs.sensitivity_labels["high"],
    ]
    rows = [
        sharp_policy_contrast_bounds(
            allocations,
            policy_a=specs.selected_guardrail_label,
            policy_b=label,
            role="primary_oot",
            lgd=lgd,
        )
        for label in labels
    ]
    return pd.DataFrame(rows)


def _selector_leave_one_month_out(
    evaluation: pd.DataFrame,
    specs: AuditSpecs,
) -> pd.DataFrame:
    guard_labels = {guard for _, guard, _ in specs.family_pairs}
    development = evaluation.loc[
        evaluation["role"].eq("policy_development") & evaluation["policy_label"].isin(guard_labels)
    ].copy()
    rows: list[dict[str, Any]] = []
    for dropped in sorted(development["period"].astype(str).unique()):
        kept = development.loc[~development["period"].astype(str).eq(dropped)]
        ranking = (
            kept.groupby(["candidate_id", "policy_label"], as_index=False, observed=True)
            .agg(
                realized_payoff=("realized_payoff_lower", "sum"),
                expected_payoff=("expected_objective", "sum"),
            )
            .sort_values(
                ["realized_payoff", "expected_payoff", "candidate_id"],
                ascending=[False, False, True],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
        winner = ranking.iloc[0]
        rows.append(
            {
                "dropped_period": dropped,
                "winner_candidate_id": str(winner["candidate_id"]),
                "winner_policy_label": str(winner["policy_label"]),
                "winner_realized_payoff": float(winner["realized_payoff"]),
                "margin_over_second": float(
                    winner["realized_payoff"] - ranking.iloc[1]["realized_payoff"]
                ),
                "parent_selected_wins": bool(
                    str(winner["candidate_id"]) == specs.selected_candidate_id
                ),
            }
        )
    return pd.DataFrame(rows)


def _primary_leave_one_month_out(
    allocations: pd.DataFrame,
    specs: AuditSpecs,
    *,
    lgd: float,
) -> pd.DataFrame:
    primary = allocations.loc[allocations["role"].eq("primary_oot")]
    periods = sorted(primary["period"].astype(str).unique())
    baselines = [specs.same_threshold_label, specs.selected_match_label]
    rows: list[dict[str, Any]] = []
    for baseline in baselines:
        relevant = primary.loc[
            primary["policy_label"].isin([specs.selected_guardrail_label, baseline])
        ]
        for dropped in periods:
            record = sharp_policy_contrast_bounds(
                relevant.loc[~relevant["period"].astype(str).eq(dropped)],
                policy_a=specs.selected_guardrail_label,
                policy_b=baseline,
                role="primary_oot",
                lgd=lgd,
            )
            record["dropped_period"] = dropped
            rows.append(record)
    return pd.DataFrame(rows)


def _signed_union(
    allocations: pd.DataFrame,
    *,
    policy_a: str,
    policy_b: str,
    role: str,
) -> pd.DataFrame:
    relevant = allocations.loc[
        allocations["role"].eq(role) & allocations["policy_label"].isin([policy_a, policy_b])
    ].copy()
    keys = ["id", "period"]
    attributes = [
        "contractual_rate",
        "pd_point",
        "snapshot_default",
        "conformal_lower",
        "conformal_upper",
        "conformal_group",
    ]
    base = relevant[keys + attributes].drop_duplicates(keys)
    if base.duplicated(keys).any():
        raise RuntimeError("Policy union attributes do not align one-to-one.")
    exposure = relevant.pivot(index=keys, columns="policy_label", values="exposure").fillna(0.0)
    for label in (policy_a, policy_b):
        if label not in exposure.columns:
            exposure[label] = 0.0
    result = base.set_index(keys).join(exposure[[policy_a, policy_b]], how="outer")
    required_attributes = [column for column in attributes if column != "snapshot_default"]
    if bool(result[required_attributes].isna().any().any()):
        raise RuntimeError("Policy union contains missing decision attributes.")
    result["signed_exposure"] = result[policy_a] - result[policy_b]
    return result.reset_index()


def _payoff_decomposition(
    allocations: pd.DataFrame,
    specs: AuditSpecs,
    *,
    lgd: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for baseline in (specs.same_threshold_label, specs.selected_match_label):
        union = _signed_union(
            allocations,
            policy_a=specs.selected_guardrail_label,
            policy_b=baseline,
            role="primary_oot",
        )
        signed = union["signed_exposure"].to_numpy(dtype=float)
        rate = union["contractual_rate"].to_numpy(dtype=float)
        point = union["pd_point"].to_numpy(dtype=float)
        outcome = pd.to_numeric(union["snapshot_default"], errors="coerce").to_numpy(dtype=float)
        resolved = np.isfinite(outcome)
        penalty = -signed * (rate + lgd)
        contractual = float(signed @ rate)
        resolved_penalty = float((penalty[resolved] * outcome[resolved]).sum())
        unresolved_lower = float(np.minimum(0.0, penalty[~resolved]).sum())
        unresolved_upper = float(np.maximum(0.0, penalty[~resolved]).sum())
        expected_interest = float(signed @ ((1.0 - point) * rate))
        expected_default_loss = float((-signed * point * lgd).sum())
        rows.append(
            {
                "baseline": baseline,
                "contractual_component": contractual,
                "resolved_default_penalty": resolved_penalty,
                "unresolved_penalty_lower": unresolved_lower,
                "unresolved_penalty_upper": unresolved_upper,
                "realized_difference_lower": contractual + resolved_penalty + unresolved_lower,
                "realized_difference_upper": contractual + resolved_penalty + unresolved_upper,
                "expected_interest_component": expected_interest,
                "expected_default_loss_component": expected_default_loss,
                "expected_difference": expected_interest + expected_default_loss,
            }
        )
    return pd.DataFrame(rows)


def _payoff_bounds_at_lgd(union: pd.DataFrame, lgd: float) -> tuple[float, float, float]:
    signed = union["signed_exposure"].to_numpy(dtype=float)
    rate = union["contractual_rate"].to_numpy(dtype=float)
    point = union["pd_point"].to_numpy(dtype=float)
    outcome = pd.to_numeric(union["snapshot_default"], errors="coerce").to_numpy(dtype=float)
    repay = signed * rate
    default = -signed * float(lgd)
    observed = np.isfinite(outcome)
    lower = np.where(observed, np.where(outcome == 1.0, default, repay), np.minimum(repay, default))
    upper = np.where(observed, np.where(outcome == 1.0, default, repay), np.maximum(repay, default))
    expected = signed * ((1.0 - point) * rate - point * float(lgd))
    return float(expected.sum()), float(lower.sum()), float(upper.sum())


def _root(intercept: float, slope: float, domain: tuple[float, float]) -> float | None:
    if np.isclose(slope, 0.0, rtol=0.0, atol=1e-15):
        return None
    value = -intercept / slope
    return float(value) if domain[0] <= value <= domain[1] else None


def _lgd_break_even(
    allocations: pd.DataFrame,
    specs: AuditSpecs,
    *,
    domain: tuple[float, float],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for baseline in (specs.same_threshold_label, specs.selected_match_label):
        union = _signed_union(
            allocations,
            policy_a=specs.selected_guardrail_label,
            policy_b=baseline,
            role="primary_oot",
        )
        at_zero = _payoff_bounds_at_lgd(union, domain[0])
        at_one = _payoff_bounds_at_lgd(union, domain[1])
        row: dict[str, Any] = {"baseline": baseline}
        for index, metric in enumerate(("expected", "realized_lower", "realized_upper")):
            intercept = float(at_zero[index])
            slope = float((at_one[index] - at_zero[index]) / (domain[1] - domain[0]))
            row[f"{metric}_intercept"] = intercept
            row[f"{metric}_slope"] = slope
            row[f"{metric}_break_even_lgd"] = _root(intercept, slope, domain)
        rows.append(row)
    return pd.DataFrame(rows)


def _score_geometry(parent: ParentFrames, config: Mapping[str, Any]) -> pd.DataFrame:
    conformal = parent.parent_summary["conformal"]
    quantiles = [float(value) for value in conformal["residual_quantiles"]]
    gamma = float(config["primary_policy"]["gamma"])
    primary = parent.decision.loc[parent.decision["design_split"].eq("primary_oot")].copy()
    primary["decision_score"] = (1.0 - gamma) * primary["pd_point"] + gamma * primary[
        "conformal_upper"
    ]
    rows: list[dict[str, Any]] = []
    for group, group_rows in primary.groupby("conformal_group", observed=True):
        upper = group_rows["conformal_upper"].to_numpy(dtype=float)
        rows.append(
            {
                "conformal_group": int(group),
                "rows": int(len(group_rows)),
                "residual_quantile": quantiles[int(group)],
                "pd_min": float(group_rows["pd_point"].min()),
                "pd_mean": float(group_rows["pd_point"].mean()),
                "pd_max": float(group_rows["pd_point"].max()),
                "upper_mean": float(upper.mean()),
                "upper_one_share": float(np.isclose(upper, 1.0, atol=1e-12).mean()),
                "score_min": float(group_rows["decision_score"].min()),
                "score_mean": float(group_rows["decision_score"].mean()),
                "score_max": float(group_rows["decision_score"].max()),
                "unsaturated_score_formula": "p + gamma*c_g",
                "saturated_score_formula": "gamma + (1-gamma)*p",
            }
        )
    return pd.DataFrame(rows)


def _selected_transport(
    parent: ParentFrames,
    allocations: pd.DataFrame,
    specs: AuditSpecs,
) -> pd.DataFrame:
    candidates = parent.decision.loc[parent.decision["design_split"].eq("primary_oot")].drop(
        columns="design_split"
    )
    outcomes = parent.outcomes.loc[parent.outcomes["id"].isin(candidates["id"])]
    with_outcomes = candidates.merge(outcomes, on="id", how="left", validate="one_to_one")
    rows: list[pd.DataFrame] = []
    for label in (
        specs.selected_guardrail_label,
        specs.same_threshold_label,
        specs.selected_match_label,
    ):
        funded = allocations.loc[
            allocations["role"].eq("primary_oot") & allocations["policy_label"].eq(label)
        ]
        frame = coverage_and_default_transport_bounds(
            with_outcomes,
            funded,
            alpha=float(parent.parent_config["conformal"]["alpha"]),
        )
        frame.insert(0, "policy_label", label)
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def _group_exposure(allocations: pd.DataFrame) -> pd.DataFrame:
    result = (
        allocations.groupby(
            ["role", "policy_label", "conformal_group"],
            observed=True,
            as_index=False,
        )["exposure"]
        .sum()
        .sort_values(["role", "policy_label", "conformal_group"], kind="mergesort")
    )
    result["exposure_share"] = result["exposure"] / result.groupby(
        ["role", "policy_label"], observed=True
    )["exposure"].transform("sum")
    return result


def _decision_gate(
    selected: pd.DataFrame,
    leave_one_out: pd.DataFrame,
    specs: AuditSpecs,
) -> dict[str, Any]:
    def contrast(label: str) -> pd.Series:
        rows = selected.loc[selected["policy_b"].eq(label)]
        if len(rows) != 1:
            raise RuntimeError(f"Expected one selected contrast for {label}.")
        return rows.iloc[0]

    same = contrast(specs.same_threshold_label)
    matched = contrast(specs.selected_match_label)
    aggregate_checks = {
        "same_threshold_default_upper_lt_zero": float(same["weighted_default_difference_upper"])
        < 0.0,
        "development_matched_payoff_upper_lt_zero": float(
            matched["realized_payoff_difference_upper"]
        )
        < 0.0,
        "development_matched_default_lower_gt_zero": float(
            matched["weighted_default_difference_lower"]
        )
        > 0.0,
        "development_matched_miscoverage_lower_gt_zero": float(
            matched["weighted_miscoverage_difference_lower"]
        )
        > 0.0,
    }
    monthly_checks: list[dict[str, Any]] = []
    for _, row in leave_one_out.iterrows():
        baseline = str(row["policy_b"])
        if baseline == specs.same_threshold_label:
            passes = float(row["weighted_default_difference_upper"]) < 0.0
        else:
            passes = (
                float(row["realized_payoff_difference_upper"]) < 0.0
                and float(row["weighted_default_difference_lower"]) > 0.0
                and float(row["weighted_miscoverage_difference_lower"]) > 0.0
            )
        monthly_checks.append(
            {
                "baseline": baseline,
                "dropped_period": str(row["dropped_period"]),
                "passes": bool(passes),
            }
        )
    return {
        "aggregate_checks": aggregate_checks,
        "leave_one_month_out_checks": monthly_checks,
        "aggregate_passes": bool(all(aggregate_checks.values())),
        "leave_one_month_out_passes": bool(all(row["passes"] for row in monthly_checks)),
        "headline_eligible": bool(
            all(aggregate_checks.values()) and all(row["passes"] for row in monthly_checks)
        ),
    }


def _write_artifacts(
    *,
    paths: OutputPaths,
    repo_root: Path,
    frames: Mapping[str, pd.DataFrame],
    protocol_freeze: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    written: dict[Path, pd.DataFrame] = {}
    for relative, frame in frames.items():
        path = paths.data_dir / relative
        written[path] = frame
        if path.suffix == ".parquet":
            atomic_write_parquet(frame, path)
        else:
            write_csv_atomic(frame, path)
    descriptors = [
        *(relative_artifact_descriptor(path, repo_root=repo_root) for path in written),
        relative_artifact_descriptor(protocol_freeze, repo_root=repo_root),
    ]
    artifacts = {str(item["path"]): item for item in descriptors}
    schemas = {
        relative_artifact_descriptor(path, repo_root=repo_root)["path"]: dataframe_schema(frame)
        for path, frame in written.items()
    }
    return artifacts, schemas


def run_audit(*, config_path: Path, repo_root: Path = ROOT) -> Path:
    """Execute the locked comparator audit and return its deterministic summary."""
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
    paths = prepare_output_paths(config, repo_root=repo_root)
    parent = _load_parent_frames(config, repo_root=repo_root)
    specs = _derive_audit_specs(config, parent)
    protocol_freeze = atomic_write_json(
        paths.model_dir / "protocol_freeze.json",
        {
            "schema_version": str(config["schema_version"]),
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "posthoc_diagnostic_after_active_results": True,
            "parent_run_tag": str(config["parent"]["run_tag"]),
            "selected_guardrail": dict(config["primary_policy"]),
            "comparators": dict(config["comparators"]),
            "family_census": dict(config["family_census"]),
            "decision_gate": dict(config["decision_gate"]),
            "implementation_provenance": implementation_start,
        },
    )

    logger.info("Evaluating {} locked policy specs", len(specs.specs))
    evaluation, allocations = _evaluate_all_blocks(parent, specs)
    tolerance = float(config["execution"]["deterministic_tolerance"])
    replay = _verify_parent_replay(parent, allocations, specs, tolerance=tolerance)
    aggregate = _aggregate_evaluations(evaluation)
    lgd = float(parent.parent_config["payoff"]["lgd"])
    family_primary = _contrasts_for_pairs(
        allocations,
        specs.family_pairs,
        role="primary_oot",
        lgd=lgd,
    )
    family_development = _contrasts_for_pairs(
        allocations,
        specs.family_pairs,
        role="policy_development",
        lgd=lgd,
    )
    family_extension = _contrasts_for_pairs(
        allocations,
        specs.family_pairs,
        role="censored_extension",
        lgd=lgd,
    )
    selected = _selected_primary_contrasts(allocations, specs, lgd=lgd)
    selector_loo = _selector_leave_one_month_out(evaluation, specs)
    primary_loo = _primary_leave_one_month_out(allocations, specs, lgd=lgd)
    payoff = _payoff_decomposition(allocations, specs, lgd=lgd)
    lgd_domain = tuple(float(value) for value in config["analysis"]["lgd_domain"])
    if len(lgd_domain) != 2:
        raise ValueError("LGD domain must contain exactly two endpoints.")
    lgd_break_even = _lgd_break_even(
        allocations,
        specs,
        domain=(lgd_domain[0], lgd_domain[1]),
    )
    geometry = _score_geometry(parent, config)
    transport = _selected_transport(parent, allocations, specs)
    groups = _group_exposure(allocations)
    gate = _decision_gate(selected, primary_loo, specs)

    family_flags = family_primary.assign(
        payoff_guardrail_worse=lambda frame: frame["realized_payoff_difference_upper"] < 0.0,
        default_guardrail_worse=lambda frame: frame["weighted_default_difference_lower"] > 0.0,
        miscoverage_guardrail_worse=lambda frame: (
            frame["weighted_miscoverage_difference_lower"] > 0.0
        ),
    )
    family_all_three = (
        family_flags["payoff_guardrail_worse"]
        & family_flags["default_guardrail_worse"]
        & family_flags["miscoverage_guardrail_worse"]
    )
    family_claim = {
        "pairs": int(len(family_flags)),
        "payoff_guardrail_worse": int(family_flags["payoff_guardrail_worse"].sum()),
        "default_guardrail_worse": int(family_flags["default_guardrail_worse"].sum()),
        "miscoverage_guardrail_worse": int(family_flags["miscoverage_guardrail_worse"].sum()),
        "all_three_guardrail_worse": int(family_all_three.sum()),
        "family_direction_claim_allowed": bool(family_all_three.all()),
    }

    frames = {
        "portfolio/comparator_monthly_evaluation.csv": evaluation,
        "portfolio/comparator_monthly_funded_allocations.parquet": allocations,
        "portfolio/comparator_aggregate.csv": aggregate,
        "portfolio/matched_thresholds.csv": specs.thresholds,
        "portfolio/selected_primary_contrasts.csv": selected,
        "portfolio/family_primary_contrasts.csv": family_flags,
        "portfolio/family_development_contrasts.csv": family_development,
        "portfolio/family_extension_contrasts.csv": family_extension,
        "portfolio/selector_leave_one_month_out.csv": selector_loo,
        "portfolio/primary_leave_one_month_out.csv": primary_loo,
        "portfolio/payoff_decomposition.csv": payoff,
        "portfolio/lgd_break_even.csv": lgd_break_even,
        "portfolio/score_geometry.csv": geometry,
        "portfolio/selected_transport_decomposition.csv": transport,
        "portfolio/funded_group_exposure.csv": groups,
    }
    artifacts, schemas = _write_artifacts(
        paths=paths,
        repo_root=repo_root,
        frames=frames,
        protocol_freeze=protocol_freeze,
    )
    implementation_end = implementation_provenance(
        config_path=config_path,
        relative_paths=IMPLEMENTATION_PATHS,
        repo_root=repo_root,
    )
    if implementation_end != implementation_start:
        raise RuntimeError("Comparator audit implementation changed during execution.")

    selected_matched = selected.loc[selected["policy_b"].eq(specs.selected_match_label)].iloc[0]
    selected_same = selected.loc[selected["policy_b"].eq(specs.same_threshold_label)].iloc[0]
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "posthoc_diagnostic_after_active_results": True,
        "hypothesis": str(config["hypothesis"]),
        "claim_boundary": (
            "Post hoc comparator falsification audit. It changes no parent policy and "
            "does not create confirmatory, causal, prospective, or family-wide evidence "
            "unless the locked 9-of-9 rule is satisfied."
        ),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
        "config": relative_artifact_descriptor(config_path, repo_root=repo_root),
        "parent": {
            "run_tag": str(config["parent"]["run_tag"]),
            "evidence_manifest": relative_artifact_descriptor(
                parent.evidence_path,
                repo_root=repo_root,
            ),
            "summary": relative_artifact_descriptor(
                parent.summary_path,
                repo_root=repo_root,
            ),
            "allocation_replay_max_abs_difference": replay,
        },
        "matching": {
            "rule": str(config["comparators"]["development_matched"]["statistic"]),
            "selected_thresholds": specs.thresholds.loc[
                specs.thresholds["candidate_id"].eq(config["primary_policy"]["candidate_id"])
            ]
            .iloc[0]
            .to_dict(),
            "all_family_thresholds": specs.thresholds.to_dict(orient="records"),
            "same_threshold_is_secondary": True,
        },
        "monthly_evaluation": {
            "policy_specs": int(len(specs.specs)),
            "aggregate_by_role_and_policy": aggregate.to_dict(orient="records"),
        },
        "primary": {
            "same_threshold_contrast": selected_same.to_dict(),
            "development_matched_contrast": selected_matched.to_dict(),
            "threshold_sensitivity_contrasts": selected.to_dict(orient="records"),
            "leave_one_month_out": primary_loo.to_dict(orient="records"),
            "decision_gate": gate,
        },
        "family_census": {
            **family_claim,
            "primary_contrasts": family_flags.to_dict(orient="records"),
        },
        "selector_sensitivity": selector_loo.to_dict(orient="records"),
        "payoff_decomposition": payoff.to_dict(orient="records"),
        "lgd_break_even": lgd_break_even.to_dict(orient="records"),
        "score_geometry": geometry.to_dict(orient="records"),
        "implementation_provenance": implementation_start,
        "artifacts": artifacts,
        "schemas": schemas,
    }
    summary_path = atomic_write_json(
        paths.model_dir / str(config["output"]["deterministic_result"]),
        summary,
    )
    receipt = {
        "run_tag": str(config["run_tag"]),
        "started_at_utc": started_at,
        "completed_at_utc": utc_now_iso(),
        "runtime_seconds": float(time.perf_counter() - started_counter),
        "initial_git": initial_git,
        "final_git": git_provenance(repo_root),
        "environment": environment_provenance(repo_root),
        "deterministic_summary": relative_artifact_descriptor(
            summary_path,
            repo_root=repo_root,
        ),
    }
    atomic_write_json(paths.model_dir / str(config["output"]["execution_receipt"]), receipt)
    logger.info(
        "Comparator audit complete; headline_eligible={} family_9_of_9={}",
        gate["headline_eligible"],
        family_claim["family_direction_claim_allowed"],
    )
    return summary_path


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI entry point."""
    args = parse_args(argv)
    run_audit(config_path=args.config)


if __name__ == "__main__":
    main()
