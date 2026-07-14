"""Configuration loading and closed-design validation for the V4 audit."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        name = str(key)
        if value is None:
            merged.pop(name, None)
        elif isinstance(value, Mapping) and isinstance(merged.get(name), dict):
            merged[name] = _deep_merge(merged[name], value)
        else:
            merged[name] = copy.deepcopy(value)
    return merged


def _load_payload(path: Path, seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in seen:
        raise ValueError(f"Protocol config inheritance cycle at {resolved}.")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Protocol config must be a YAML mapping.")
    extends = payload.pop("extends", None)
    if extends is None:
        return payload
    return _deep_merge(
        _load_payload((resolved.parent / str(extends)).resolve(), seen | {resolved}),
        payload,
    )


def _validate_windows(config: Mapping[str, Any]) -> None:
    design = config["design"]
    specification = config["residual_specification"]
    windows = specification["windows"]
    if len(windows) != 8 or int(specification["window_months"]) != 6:
        raise ValueError("V4 requires exactly eight six-month residual windows.")
    conformal_start = pd.Timestamp(design["conformal_fit_start"])
    conformal_end = pd.Timestamp(design["conformal_fit_end"])
    expected_starts = pd.date_range(conformal_start, periods=8, freq="MS")
    identifiers: set[str] = set()
    observed_end: pd.Timestamp | None = None
    for expected_start, window in zip(expected_starts, windows, strict=True):
        identifier = str(window["id"])
        if identifier in identifiers:
            raise ValueError(f"Duplicate residual-window id: {identifier}.")
        identifiers.add(identifier)
        start = cast(pd.Timestamp, pd.Timestamp(window["start"]))
        end = cast(pd.Timestamp, pd.Timestamp(window["end"]))
        expected_end = start + pd.offsets.MonthEnd(6)
        if start != cast(pd.Timestamp, expected_start) or end != expected_end:
            raise ValueError(
                f"Residual window {identifier} is not the declared consecutive six-month window."
            )
        observed_end = end
    if observed_end != conformal_end:
        raise ValueError("The final residual window must end at design.conformal_fit_end.")


def _validate_design_chronology(config: Mapping[str, Any]) -> None:
    design = config["design"]
    development_end = pd.Timestamp(design["development_end"])
    calibration_start = pd.Timestamp(design["probability_calibration_start"])
    calibration_end = pd.Timestamp(design["probability_calibration_end"])
    conformal_start = pd.Timestamp(design["conformal_fit_start"])
    conformal_end = pd.Timestamp(design["conformal_fit_end"])
    policy_start = pd.Timestamp(design["policy_development_start"])
    policy_end = pd.Timestamp(design["policy_development_end"])

    if calibration_start != development_end + pd.Timedelta(days=1):
        raise ValueError("Probability calibration must start immediately after PD development.")
    if calibration_end != calibration_start + pd.offsets.MonthEnd(12):
        raise ValueError("Probability calibration must contain exactly twelve complete months.")
    if conformal_start != calibration_end + pd.Timedelta(days=1):
        raise ValueError("Residual fitting must start immediately after probability calibration.")
    if policy_start != conformal_end + pd.Timedelta(days=1):
        raise ValueError("Policy development must start immediately after residual fitting.")
    if policy_end != policy_start + pd.offsets.MonthEnd(11):
        raise ValueError("Policy development must contain exactly eleven complete months.")

    cutoff = pd.Timestamp(config["source"]["information_cutoff"])
    primary_start_period = cast(
        pd.Period, pd.Period(str(design["primary_oot_start_month"]), freq="M")
    )
    primary_start = primary_start_period.start_time
    primary_end = cast(pd.Period, pd.Period(str(design["primary_oot_end_month"]), freq="M"))
    extension_start = cast(
        pd.Period, pd.Period(str(design["censored_extension_start_month"]), freq="M")
    )
    extension_end = cast(
        pd.Period, pd.Period(str(design["censored_extension_end_month"]), freq="M")
    )
    if cutoff != primary_start - pd.Timedelta(days=1):
        raise ValueError("The information cutoff must immediately precede primary OOT.")
    if primary_end.ordinal < primary_start_period.ordinal:
        raise ValueError("Primary OOT has an invalid month range.")
    if (
        extension_start.ordinal != primary_end.ordinal + 1
        or extension_end.ordinal < extension_start.ordinal
    ):
        raise ValueError("The censored extension must immediately follow primary OOT.")


def _validate_evaluation_outcome_contract(config: Mapping[str, Any]) -> None:
    contract = config["target"].get("evaluation_outcome_contract")
    if contract is None:
        return
    expected_mode = "conservative_terminal_status_reconstruction"
    if contract.get("mode") != expected_mode:
        raise ValueError(f"Evaluation outcome mode must be {expected_mode!r}.")
    cutoff = pd.Timestamp(contract.get("cutoff"))
    if pd.isna(cutoff):
        raise ValueError("Evaluation outcome contract requires a valid cutoff.")
    if cutoff != pd.Timestamp(config["source"]["snapshot_date"]):
        raise ValueError("Endpoint reconstruction cutoff must match source.snapshot_date.")
    if contract.get("archive_is_verified_point_in_time_snapshot") is not False:
        raise ValueError(
            "The distributed archive cannot be declared a verified point-in-time snapshot."
        )
    if contract.get("terminal_status_source") != "distributed_archive_final_status":
        raise ValueError("Unexpected terminal-status source for endpoint reconstruction.")
    if int(contract.get("charged_off_reporting_lag_months", -1)) != int(
        config["source"]["charged_off_reporting_lag_months"]
    ):
        raise ValueError("Evaluation and fitting charge-off lags must agree.")


def _validate_rolling_origin(config: Mapping[str, Any]) -> None:
    rolling = config.get("rolling_origin")
    if rolling is None:
        return
    origin = int(rolling["origin_year"])
    expected_source = {"information_cutoff": f"{origin}-03-31"}
    expected_design = {
        "development_end": f"{origin - 6}-12-31",
        "probability_calibration_start": f"{origin - 5}-01-01",
        "probability_calibration_end": f"{origin - 5}-12-31",
        "conformal_fit_start": f"{origin - 4}-01-01",
        "conformal_fit_end": f"{origin - 3}-01-31",
        "policy_development_start": f"{origin - 3}-02-01",
        "policy_development_end": f"{origin - 3}-12-31",
        "primary_oot_start_month": f"{origin}-04",
        "primary_oot_end_month": f"{origin}-06",
        "censored_extension_start_month": f"{origin}-07",
        "censored_extension_end_month": f"{origin}-09",
    }
    for field, expected in expected_source.items():
        if str(config["source"][field]) != expected:
            raise ValueError(f"Rolling origin {origin} has an asymmetric source.{field}.")
    for field, expected in expected_design.items():
        if str(config["design"][field]) != expected:
            raise ValueError(f"Rolling origin {origin} has an asymmetric design.{field}.")
    if int(rolling.get("common_primary_months", -1)) != 3:
        raise ValueError("The rolling-origin common primary horizon must contain three months.")
    if int(rolling.get("reference_origin_year", -1)) != 2016:
        raise ValueError("The rolling-origin reference year must remain 2016.")
    if rolling.get("outcome_based_origin_selection") is not False:
        raise ValueError("Outcome-based origin selection is forbidden.")
    if rolling.get("pooled_origin_claims") is not False:
        raise ValueError("Pooled rolling-origin claims are forbidden.")


def load_v4_config(path: Path) -> dict[str, Any]:
    """Load V4 and reject any expansion of its closed analysis family."""
    config = _load_payload(path)
    required = {
        "source",
        "target",
        "design",
        "model",
        "probability_calibration",
        "conformal",
        "residual_specification",
        "learner_control",
        "payoff",
        "policy",
        "comparators",
        "analysis",
        "simulation",
        "execution",
        "output",
    }
    missing = sorted(required.difference(config))
    if missing:
        raise KeyError(f"V4 protocol config is missing sections: {missing}.")
    if config["protocol_status"] != "locked_retrospective_complete_specification_audit":
        raise ValueError("Unexpected V4 protocol status.")
    if config["design"].get("historical_archive_previously_inspected") is not True:
        raise ValueError("The inspected-archive disclosure must remain true.")
    if config["policy"].get("outcome_based_selection") is not False:
        raise ValueError("Outcome-based policy selection is forbidden.")
    if config["comparators"].get("selection_from_outcomes") is not False:
        raise ValueError("Outcome-based comparator selection is forbidden.")
    if config["analysis"].get("all_eight_windows_primary") is not True:
        raise ValueError("All eight residual windows must remain co-primary.")
    if config["analysis"].get("all_nine_policies_primary") is not True:
        raise ValueError("All nine policies must remain co-primary.")
    if [int(value) for value in config["conformal"]["diagnostic_group_counts"]] != [1, 2, 5, 10]:
        raise ValueError("The closed taxonomy diagnostic grid is 1/2/5/10.")
    if int(config["conformal"]["canonical_groups"]) != 5:
        raise ValueError("The canonical taxonomy must contain five groups.")
    if [int(value) for value in config["model"]["sensitivity_seeds"]] != [40, 41, 42, 43, 44]:
        raise ValueError("Inherited seed lineage changed unexpectedly.")
    if int(config["model"]["canonical_seed"]) != 42:
        raise ValueError("V4 portfolio optimization is locked to seed 42.")
    if len(config["policy"]["risk_tolerances"]) * len(config["policy"]["gammas"]) != 9:
        raise ValueError("The closed portfolio family must contain nine policies.")
    support = config["comparators"]["exact_point_cap_frontier"]
    if not 0.0 <= float(support["start"]) < float(support["stop"]) <= 1.0:
        raise ValueError("The broad frontier support must be a nonempty subset of [0, 1].")
    if config["learner_control"].get("portfolio_optimization") is not False:
        raise ValueError("The logistic learner is coverage-only.")
    resume = config.get("resume_outcome_free")
    if resume:
        required_resume = {
            "source_run_tag",
            "source_protocol_tag",
            "source_protocol_commit",
            "source_freeze_sha256",
        }
        missing_resume = sorted(required_resume.difference(resume))
        if missing_resume:
            raise KeyError(f"Outcome-free import is missing fields: {missing_resume}.")
        digest = str(resume["source_freeze_sha256"])
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Imported freeze SHA-256 must be lowercase hexadecimal.")
    _validate_windows(config)
    _validate_design_chronology(config)
    _validate_evaluation_outcome_contract(config)
    _validate_rolling_origin(config)
    return config


def load_credit_control_config(path: Path) -> dict[str, Any]:
    """Load the V4-aligned, coverage-only credit-risk control protocol."""
    config = load_v4_config(path)
    controls = config.get("credit_risk_controls")
    if not isinstance(controls, Mapping):
        raise KeyError("Credit-risk control config is missing credit_risk_controls.")

    expected_models = [
        "catboost_platt",
        "numeric_logistic_platt",
        "catboost_monotonic_platt",
        "woe_scorecard_platform_platt",
        "woe_scorecard_borrower_platt",
    ]
    if [str(value) for value in controls.get("co_primary_models", [])] != expected_models:
        raise ValueError("The five predeclared learner controls must remain co-primary.")
    if controls.get("all_models_reported") is not True:
        raise ValueError("Every predeclared learner must be reported.")
    if controls.get("selection_from_oot") is not False:
        raise ValueError("OOT model selection is forbidden.")
    if controls.get("portfolio_optimization") is not False:
        raise ValueError("Credit-risk controls are coverage-only.")
    if controls.get("sampling") != "none_all_eligible_rows":
        raise ValueError("Credit-risk controls must use every eligible row.")

    reference = controls.get("active_score_reference")
    if not isinstance(reference, Mapping):
        raise KeyError("The active V4 score reference is required.")
    digest = str(reference.get("sha256", ""))
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("Active score reference SHA-256 must be lowercase hexadecimal.")

    active_features = {
        *[str(value) for value in config["model"]["numeric_features"]],
        *[str(value) for value in config["model"]["categorical_features"]],
    }
    monotonic = controls.get("monotonic_catboost", {})
    constraints = monotonic.get("constraints", {})
    if not isinstance(constraints, Mapping) or not constraints:
        raise ValueError("Monotonic CatBoost requires a nonempty constraint map.")
    if not set(map(str, constraints)).issubset(active_features):
        raise ValueError("Monotonic constraints must use active model features only.")
    if {int(value) for value in constraints.values()}.difference({-1, 1}):
        raise ValueError("Monotonic constraints must be -1 or +1.")

    scorecards = controls.get("scorecards")
    if not isinstance(scorecards, Mapping) or set(scorecards) != {"platform", "borrower"}:
        raise ValueError("Exactly the platform and borrower scorecards are required.")
    platform_signals = {str(value) for value in controls.get("platform_signal_features", [])}
    for name, specification in scorecards.items():
        features = [str(value) for value in specification.get("features", [])]
        if not features or len(features) != len(set(features)):
            raise ValueError(f"Scorecard {name} has empty or duplicate features.")
        if not set(features).issubset(active_features):
            raise ValueError(f"Scorecard {name} uses a feature outside the active contract.")
    if not platform_signals.issubset(set(scorecards["platform"]["features"])):
        raise ValueError("The platform scorecard must include every declared platform signal.")
    if platform_signals.intersection(scorecards["borrower"]["features"]):
        raise ValueError("The borrower scorecard must exclude declared platform signals.")

    resume = config.get("resume_credit_control_freeze")
    if resume:
        required_resume = {
            "source_run_tag",
            "source_protocol_tag",
            "source_protocol_commit",
            "source_freeze_sha256",
        }
        missing_resume = sorted(required_resume.difference(resume))
        if missing_resume:
            raise KeyError(f"Credit-control import is missing fields: {missing_resume}.")
        digest = str(resume["source_freeze_sha256"])
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Imported credit-control freeze SHA-256 is invalid.")
    recovery = config.get("evaluation_recovery")
    if recovery:
        if recovery.get("status") != "numerical_calibration_recovery_only":
            raise ValueError("Unexpected credit-control evaluation recovery status.")
        if recovery.get("require_exact_coverage_equivalence") is not True:
            raise ValueError("Evaluation recovery must require exact coverage equivalence.")
        if recovery.get("calibration_solver") != "sklearn_unpenalized_lbfgs":
            raise ValueError("Unexpected calibration recovery solver.")
        reference = recovery.get("coverage_reference")
        if not isinstance(reference, Mapping):
            raise KeyError("Evaluation recovery requires a coverage reference.")
        digest = str(reference.get("sha256", ""))
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Coverage reference SHA-256 is invalid.")
    return config
