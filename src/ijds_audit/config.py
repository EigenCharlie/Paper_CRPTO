"""Configuration loading and closed-design validation for the V4 audit."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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
        start = pd.Timestamp(window["start"])
        end = pd.Timestamp(window["end"])
        expected_end = start + pd.offsets.MonthEnd(6)
        if start != expected_start or end != expected_end:
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
    primary_start = pd.Period(str(design["primary_oot_start_month"]), freq="M").start_time
    primary_end = pd.Period(str(design["primary_oot_end_month"]), freq="M")
    extension_start = pd.Period(str(design["censored_extension_start_month"]), freq="M")
    extension_end = pd.Period(str(design["censored_extension_end_month"]), freq="M")
    if cutoff != primary_start - pd.Timedelta(days=1):
        raise ValueError("The information cutoff must immediately precede primary OOT.")
    if primary_end < primary_start.to_period("M"):
        raise ValueError("Primary OOT has an invalid month range.")
    if extension_start != primary_end + 1 or extension_end < extension_start:
        raise ValueError("The censored extension must immediately follow primary OOT.")


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
    _validate_rolling_origin(config)
    return config
