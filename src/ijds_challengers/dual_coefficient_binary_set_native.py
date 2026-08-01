"""Outcome-free logical certificates for the dual-coefficient binary-set-native model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePath
from typing import Any

import numpy as np
import pandas as pd
import yaml

RUN_TAG = "ijds-dual-coefficient-binary-set-native-2026-08-01-v1"
PROTOCOL_TAG = "protocol/ijds-dual-coefficient-binary-set-native-2026-08-01-v1"
MENU_KEYS = ("window_id", "role", "period")
RULERS = ("normalized_score", "objective_matched")
COORDINATES = (0.25, 0.5, 0.75)


def _safe_basename(value: Any, *, label: str) -> str:
    name = str(value)
    if not name or name in {".", ".."} or PurePath(name).name != name:
        raise ValueError(f"{label} must be one valid basename.")
    return name


def _descriptor(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"path", "bytes", "sha256"}:
        raise ValueError(f"{label} must contain exactly path, bytes, and sha256.")
    digest = str(value["sha256"])
    if (
        not isinstance(value["path"], str)
        or not isinstance(value["bytes"], int)
        or isinstance(value["bytes"], bool)
        or int(value["bytes"]) <= 0
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"{label} has an invalid artifact descriptor.")
    return dict(value)


def load_dual_coefficient_config(path: Path) -> dict[str, Any]:
    """Load the locked logical-certificate contract and reject estimand drift."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Dual-coefficient binary-set-native config must be a YAML mapping.")
    expected_top = {
        "schema_version",
        "protocol_status",
        "protocol_tag",
        "run_tag",
        "hypothesis",
        "predecessor",
        "inherited_contract",
        "conditional_theorem",
        "expected_census",
        "tolerances",
        "claim_boundary",
        "stop_rules",
        "output",
    }
    if set(payload) != expected_top:
        raise ValueError("Dual-coefficient binary-set-native top-level contract changed.")
    if (
        payload["protocol_status"] != "locked_candidate_outcome_free_before_execution"
        or payload["protocol_tag"] != PROTOCOL_TAG
        or payload["run_tag"] != RUN_TAG
    ):
        raise ValueError("Dual-coefficient binary-set-native run identity changed.")

    predecessor = payload["predecessor"]
    if (
        predecessor["run_tag"] != "ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
        or predecessor["protocol_tag"]
        != "protocol/ijds-set-native-binary-robust-counterpart-2026-07-31-v1"
        or predecessor["protocol_commit"] != "2066363ab0d09e25dade0f582a0c36c6aa7bee5c"
        or predecessor["artifact_tag"]
        != "artifacts/ijds-set-native-binary-robust-counterpart-2026-07-31-v1-phase-a"
        or predecessor["artifact_commit"] != "3ef847491e1ecdf55315774ddb295a634e441a54"
    ):
        raise ValueError("Predecessor identity changed.")
    for name in ("solve_records", "taxonomy", "summary", "manifest"):
        _descriptor(predecessor.get(name), label=f"predecessor.{name}")
    sources = predecessor.get("implementation_sources")
    expected_sources = {
        "config",
        "protocol",
        "runner",
        "implementation",
        "source_loader",
        "lp",
        "payoff",
        "conformal_sets",
        "parent_config",
        "parent_base_config",
        "config_loader",
    }
    if not isinstance(sources, dict) or set(sources) != expected_sources:
        raise ValueError("Predecessor implementation-source contract changed.")
    for name, descriptor in sources.items():
        _descriptor(descriptor, label=f"predecessor.implementation_sources.{name}")

    inherited = payload["inherited_contract"]
    expected_inherited = {
        "budget_rule": "exact_equality",
        "budget_dollars": 1_000_000.0,
        "cash_variable_present": False,
        "loan_bounds": "zero_to_requested_amount",
        "purpose_partition": "one_exhaustive_disjoint_group_per_candidate",
        "purpose_constraints": "upper_only",
        "maximum_concentration_by_purpose": 0.25,
        "contractual_rate_domain": [0.0, 1.0],
        "lgd": 0.45,
        "exact_set_score": "zero_iff_singleton_zero_else_one",
        "empty_set_semantics": "declared_fail_closed_completion_to_both_labels",
    }
    if inherited != expected_inherited:
        raise ValueError("Inherited exact-budget LP or payoff contract changed.")

    theorem = payload["conditional_theorem"]
    if (
        theorem.get("name") != "singleton_zero_substitution_and_continuous_frontier_collapse"
        or theorem.get("singleton_zero_payoff") != "contractual_rate"
        or theorem.get("non_singleton_zero_payoff") != "negative_lgd"
        or theorem.get("cap_domain") != [0.0, 1.0]
        or theorem.get("conclusion")
        != "every_maximin_optimizer_has_zero_non_singleton_zero_exposure"
        or theorem.get("frontier_conclusion")
        != "same_singleton_zero_maximin_optimal_face_and_value_for_every_cap"
    ):
        raise ValueError("Conditional theorem contract changed.")
    census = payload["expected_census"]
    if census != {
        "predecessor_rows": 1248,
        "rows_per_menu": 6,
        "windows": 8,
        "role_months_per_window": 26,
        "development_months_per_window": 11,
        "primary_months_per_window": 15,
        "menu_certificates": 208,
        "taxonomy_rows": 208,
    }:
        raise ValueError("The exact 1,248-to-208 census changed.")
    if any(float(value) <= 0.0 for value in payload["tolerances"].values()):
        raise ValueError("Every numerical tolerance must be positive.")
    if not all(value is True for value in payload["claim_boundary"].values()):
        raise ValueError("Every claim-boundary guard must remain true.")
    if not all(value is True for value in payload["stop_rules"].values()):
        raise ValueError("Every stop rule must remain true.")
    output = payload["output"]
    expected_output_keys = {
        "data_root",
        "model_root",
        "menu_certificates",
        "manifest",
        "summary",
        "receipt",
        "protocol_freeze",
        "artifact_tag",
        "dvc_required",
    }
    if set(output) != expected_output_keys or output["dvc_required"] is not False:
        raise ValueError("Output contract changed.")
    expected_output_values = {
        "data_root": "data/processed/experiments/ijds_audit",
        "model_root": "models/experiments/ijds_audit",
        "menu_certificates": "dual_coefficient_binary_set_native_menu_certificates.parquet",
        "manifest": "verified_outcome_free_manifest.json",
        "summary": "outcome_free_summary.json",
        "receipt": "outcome_free_execution_receipt.json",
        "protocol_freeze": "protocol_freeze.json",
        "artifact_tag": "artifacts/ijds-dual-coefficient-binary-set-native-2026-08-01-v1",
        "dvc_required": False,
    }
    if output != expected_output_values:
        raise ValueError("Exact isolated-output identity changed.")
    for key in ("menu_certificates", "manifest", "summary", "receipt", "protocol_freeze"):
        _safe_basename(output[key], label=f"output.{key}")
    return payload


def _required_columns(frame: pd.DataFrame, columns: set[str], *, label: str) -> None:
    missing = sorted(columns.difference(str(column) for column in frame.columns))
    if missing:
        raise RuntimeError(f"{label} lacks required columns: {missing}.")


def build_menu_certificates(
    solve_records: pd.DataFrame,
    taxonomy: pd.DataFrame,
    summary: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Reduce the complete predecessor grid to 208 fail-closed theorem certificates."""
    expected = config["expected_census"]
    tolerances = config["tolerances"]
    inherited = config["inherited_contract"]
    _required_columns(
        solve_records,
        {
            *MENU_KEYS,
            "frontier_ruler",
            "frontier_coordinate",
            "minimum_score",
            "minimum_score_portfolio_objective",
            "n_candidates",
            "total_allocated",
            "budget_residual",
            "cash_variable_present",
            "set_native_score",
            "empty_set_convention",
            "solver_status",
        },
        label="predecessor solve records",
    )
    _required_columns(
        taxonomy,
        {
            *MENU_KEYS,
            "n_candidates",
            "n_empty",
            "n_singleton_zero",
            "n_singleton_one",
            "n_two_label",
            "n_risk_zero",
            "n_risk_one",
            "empty_set_score",
        },
        label="predecessor taxonomy",
    )
    if len(solve_records) != int(expected["predecessor_rows"]):
        raise RuntimeError("Predecessor solve-record census is not 1,248 rows.")
    if len(taxonomy) != int(expected["taxonomy_rows"]):
        raise RuntimeError("Predecessor taxonomy census is not 208 rows.")
    if summary.get("run_tag") != config["predecessor"]["run_tag"]:
        raise RuntimeError("Predecessor summary run identity changed.")
    counts = summary.get("counts")
    if not isinstance(counts, Mapping) or (
        counts.get("cells") != 1248 or counts.get("taxonomy_rows") != 208
    ):
        raise RuntimeError("Predecessor summary census does not reconcile.")
    if summary.get("outcome_columns_passed") != []:
        raise RuntimeError("Predecessor summary reports outcome columns.")

    records = solve_records.copy()
    records["frontier_coordinate"] = pd.to_numeric(records["frontier_coordinate"], errors="raise")
    identity_columns = [*MENU_KEYS, "frontier_ruler", "frontier_coordinate"]
    if bool(records.duplicated(identity_columns).any()):
        raise RuntimeError("Predecessor frontier identities are duplicated.")
    if set(records["frontier_ruler"].astype(str)) != set(RULERS):
        raise RuntimeError("Predecessor ruler family changed.")
    if set(records["frontier_coordinate"].astype(float)) != set(COORDINATES):
        raise RuntimeError("Predecessor coordinate family changed.")
    minimum = pd.to_numeric(records["minimum_score"], errors="raise").to_numpy(float)
    if not bool(np.isfinite(minimum).all()) or bool(
        np.any(np.abs(minimum) > float(tolerances["minimum_score"]))
    ):
        raise RuntimeError("A predecessor menu lacks a zero minimum-score certificate.")
    total = pd.to_numeric(records["total_allocated"], errors="raise").to_numpy(float)
    budget = float(inherited["budget_dollars"])
    if not bool(np.isfinite(total).all()) or bool(
        np.any(np.abs(total - budget) > float(tolerances["total_allocated_dollars"]))
    ):
        raise RuntimeError("A predecessor cell does not fill the exact budget.")
    residual = pd.to_numeric(records["budget_residual"], errors="raise").to_numpy(float)
    if not bool(np.isfinite(residual).all()) or bool(
        np.any(np.abs(residual) > float(tolerances["budget_residual_dollars"]))
    ):
        raise RuntimeError("A predecessor budget residual exceeds tolerance.")
    if bool(records["cash_variable_present"].astype(bool).any()):
        raise RuntimeError("A predecessor cell contains a cash variable.")
    if set(records["set_native_score"].astype(str)) != {"zero_iff_exact_singleton_zero_else_one"}:
        raise RuntimeError("Predecessor exact binary-set score changed.")
    if set(records["empty_set_convention"].astype(str)) != {"fail_closed_one"}:
        raise RuntimeError("Predecessor empty-set fail-closure changed.")
    if set(records["solver_status"].astype(str)) != {"Optimal"}:
        raise RuntimeError("Predecessor includes a nonoptimal cell.")

    grouped = records.groupby(list(MENU_KEYS), observed=True, sort=True)
    group_sizes = grouped.size()
    if not bool((group_sizes == int(expected["rows_per_menu"])).all()):
        raise RuntimeError("Every menu must have exactly six predecessor frontier rows.")
    menu = grouped.agg(
        predecessor_rows=("minimum_score", "size"),
        minimum_score=("minimum_score", "max"),
        minimum_score_portfolio_objective_min=("minimum_score_portfolio_objective", "min"),
        minimum_score_portfolio_objective_max=("minimum_score_portfolio_objective", "max"),
        minimum_n_candidates=("n_candidates", "min"),
        maximum_n_candidates=("n_candidates", "max"),
        maximum_abs_budget_residual=("budget_residual", lambda x: float(np.abs(x).max())),
        minimum_total_allocated=("total_allocated", "min"),
        maximum_total_allocated=("total_allocated", "max"),
    ).reset_index()
    objective_min = pd.to_numeric(
        menu["minimum_score_portfolio_objective_min"], errors="raise"
    ).to_numpy(float)
    objective_max = pd.to_numeric(
        menu["minimum_score_portfolio_objective_max"], errors="raise"
    ).to_numpy(float)
    if not bool(np.isfinite(objective_min).all() and np.isfinite(objective_max).all()) or bool(
        np.any(np.abs(objective_max - objective_min) > 1.0e-8)
    ):
        raise RuntimeError(
            "The six predecessor repetitions disagree on the zero-score portfolio objective."
        )
    menu["minimum_score_portfolio_objective"] = objective_min
    menu = menu.drop(
        columns=[
            "minimum_score_portfolio_objective_min",
            "minimum_score_portfolio_objective_max",
        ]
    )
    tax = taxonomy.copy()
    if bool(tax.duplicated(list(MENU_KEYS)).any()):
        raise RuntimeError("Predecessor taxonomy identities are duplicated.")
    for column in (
        "n_candidates",
        "n_empty",
        "n_singleton_zero",
        "n_singleton_one",
        "n_two_label",
        "n_risk_zero",
        "n_risk_one",
    ):
        tax[column] = pd.to_numeric(tax[column], errors="raise").astype("int64")
    partition = tax[["n_empty", "n_singleton_zero", "n_singleton_one", "n_two_label"]].sum(axis=1)
    if not bool((partition == tax["n_candidates"]).all()):
        raise RuntimeError("Binary-set taxonomy does not partition every menu.")
    if not bool((tax["n_risk_zero"] == tax["n_singleton_zero"]).all()) or not bool(
        (tax["n_risk_one"] == tax["n_candidates"] - tax["n_singleton_zero"]).all()
    ):
        raise RuntimeError("Risk-zero is not exactly singleton-zero in every menu.")
    if not bool((pd.to_numeric(tax["empty_set_score"], errors="raise") == 1.0).all()):
        raise RuntimeError("Empty-set fail-closure is not one in every menu.")

    certificate = menu.merge(tax, on=list(MENU_KEYS), validate="one_to_one")
    if len(certificate) != int(expected["menu_certificates"]):
        raise RuntimeError("The merged logical-certificate census is not 208 menus.")
    if certificate["window_id"].nunique() != int(expected["windows"]):
        raise RuntimeError("The certificate window census is not eight.")
    if not bool(
        (certificate["minimum_n_candidates"] == certificate["maximum_n_candidates"]).all()
    ) or not bool((certificate["minimum_n_candidates"] == certificate["n_candidates"]).all()):
        raise RuntimeError("Candidate counts do not reconcile within a menu and taxonomy.")
    per_window = certificate.groupby("window_id", observed=True).size()
    if not bool((per_window == int(expected["role_months_per_window"])).all()):
        raise RuntimeError("Every window must contain exactly 26 role--month menus.")
    role_counts = certificate.groupby(["window_id", "role"], observed=True).size().unstack()
    if set(role_counts.columns.astype(str)) != {"policy_development", "primary_oot"}:
        raise RuntimeError("The two predecessor decision roles changed.")
    if not bool(
        (role_counts["policy_development"] == int(expected["development_months_per_window"])).all()
    ) or not bool((role_counts["primary_oot"] == int(expected["primary_months_per_window"])).all()):
        raise RuntimeError("The 11/15 monthly role census changed within a window.")

    certificate = certificate.assign(
        budget_dollars=budget,
        purpose_cap=float(inherited["maximum_concentration_by_purpose"]),
        lgd=float(inherited["lgd"]),
        contractual_rate_lower=float(inherited["contractual_rate_domain"][0]),
        contractual_rate_upper=float(inherited["contractual_rate_domain"][1]),
        condition_budget_equality=True,
        condition_no_cash=True,
        condition_disjoint_purpose_partition=True,
        condition_upper_only_purpose_caps=True,
        condition_nonnegative_contractual_rates=True,
        condition_positive_lgd=True,
        condition_singleton_zero_capacity_at_least_budget=True,
        condition_exact_binary_set_labels=True,
        capacity_lower_bound_dollars=budget,
        capacity_certificate="feasible_exact_budget_zero_minimum_set_score",
        payoff_definition=(
            "min_standardized_payoff_over_completed_nonempty_set_with_declared_empty_fail_closure"
        ),
        all_maximin_optimizers_singleton_zero=True,
        continuous_cap_frontier_collapses=True,
        cap_domain_lower=0.0,
        cap_domain_upper=1.0,
        new_optimization_executed=False,
        raw_archive_read=False,
        optimizer_unique_certified=False,
        policy_selected=False,
        validity_claim_established=False,
    )
    certificate = certificate.sort_values(list(MENU_KEYS), kind="mergesort").reset_index(drop=True)
    return certificate


def certificate_digest(frame: pd.DataFrame) -> str:
    """Hash the 208 certificates under one explicit canonical JSON encoding."""
    import hashlib

    ordered = frame.sort_values(list(MENU_KEYS), kind="mergesort")
    payload = json.dumps(
        ordered.to_dict(orient="records"),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
