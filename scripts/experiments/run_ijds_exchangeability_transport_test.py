"""Run the tagged exact-rank IJDS exchangeability transport audit."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.ijds_audit.config import load_v4_config
from src.ijds_audit.exchangeability_transport_test import (
    build_exchangeability_transport_test,
)
from src.ijds_audit.protocol import (
    configured_archive_outcomes,
    load_outcome_universe,
    load_recipes,
)
from src.utils.artifact_descriptor import relative_artifact_descriptor
from src.utils.isolated_experiment import (
    environment_provenance,
    implementation_provenance,
    prepare_output_paths,
    require_clean_tagged_head,
    resolve_repo_input,
)
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_parquet

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DATA_ROOT = Path("data/processed/experiments/ijds_audit")
ALLOWED_MODEL_ROOT = Path("models/experiments/ijds_audit")


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Exchangeability transport config must be a mapping.")
    required = {
        "schema_version",
        "run_tag",
        "protocol_tag",
        "source",
        "design",
        "multiplicity",
        "output",
        "interpretation",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Exchangeability transport config omits fields: {missing}.")
    return payload


def _verified_path(descriptor: Mapping[str, Any], *, repo_root: Path) -> Path:
    path = resolve_repo_input(str(descriptor["path"]), repo_root=repo_root)
    actual = relative_artifact_descriptor(path, repo_root=repo_root)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor.get(field):
            raise RuntimeError(f"Exchangeability transport source mismatched on {field}: {path}.")
    return path


def _require_same_descriptor(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("path", "bytes", "sha256"):
        if actual.get(field) != expected.get(field):
            raise RuntimeError(f"{label} descriptor changed on {field}.")


def run(*, config_path: Path, repo_root: Path) -> Path:
    """Execute only from a clean HEAD carrying the exact protocol tag."""
    root = repo_root.resolve()
    resolved_config = resolve_repo_input(config_path, repo_root=root)
    config = _load_config(resolved_config)
    protocol_commit = require_clean_tagged_head(root, str(config["protocol_tag"]))

    source = config["source"]
    active_config_path = _verified_path(source["active_v5_config"], repo_root=root)
    active_config = load_v4_config(active_config_path)
    summary_path = _verified_path(source["credit_control_summary"], repo_root=root)
    credit_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if credit_summary.get("status") != "complete_no_model_selection_credit_risk_control_evaluation":
        raise RuntimeError("The source five-model evaluation is incomplete.")
    evaluation_artifacts = credit_summary.get("evaluation_artifacts")
    if not isinstance(evaluation_artifacts, Mapping) or not isinstance(
        evaluation_artifacts.get("temporal_coverage"), Mapping
    ):
        raise TypeError("The source five-model summary omits temporal coverage.")
    _require_same_descriptor(
        evaluation_artifacts["temporal_coverage"],
        source["temporal_coverage"],
        label="Active V5 temporal coverage",
    )
    temporal_path = _verified_path(source["temporal_coverage"], repo_root=root)
    temporal_reference = pd.read_parquet(temporal_path)

    freeze_path = _verified_path(source["credit_control_freeze"], repo_root=root)
    source_freeze = credit_summary.get("source_freeze")
    if not isinstance(source_freeze, Mapping):
        raise TypeError("The source five-model summary omits its outcome-free freeze.")
    _require_same_descriptor(
        source_freeze,
        source["credit_control_freeze"],
        label="Five-model outcome-free freeze",
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "credit_control_scores_frozen_before_primary_oot_outcome_join":
        raise RuntimeError("The source five-model outcome-free freeze is incomplete.")
    if freeze.get("primary_oot_outcome_columns_in_frozen_scores") != []:
        raise RuntimeError("The frozen five-model scores report outcome leakage.")

    frozen_artifacts = freeze.get("outcome_free_artifacts")
    if not isinstance(frozen_artifacts, Mapping):
        raise TypeError("The source five-model freeze omits outcome-free artifacts.")
    artifact_paths: dict[str, Path] = {}
    for name in ("scores", "recipes", "fit_audit"):
        frozen_descriptor = frozen_artifacts.get(name)
        configured_descriptor = source.get(name)
        if not isinstance(frozen_descriptor, Mapping) or not isinstance(
            configured_descriptor, Mapping
        ):
            raise TypeError(f"The exchangeability source omits {name!r}.")
        _require_same_descriptor(
            frozen_descriptor,
            configured_descriptor,
            label=f"Frozen {name}",
        )
        artifact_paths[name] = _verified_path(configured_descriptor, repo_root=root)

    raw_path = _verified_path(source["raw_archive"], repo_root=root)
    configured_raw_path = resolve_repo_input(active_config["source"]["raw_path"], repo_root=root)
    if configured_raw_path != raw_path:
        raise RuntimeError("The active endpoint config no longer points to the frozen raw archive.")

    design = config["design"]
    multiplicity = config["multiplicity"]
    learners = tuple(str(value) for value in design["learners"])
    window_ids = tuple(str(value) for value in design["window_ids"])
    taxonomy_groups = int(design["taxonomy_groups"])
    if (len(learners), len(window_ids), taxonomy_groups) != (5, 8, 5):
        raise RuntimeError("The locked five-by-eight-by-five test grid changed.")
    if float(design["nominal_miscoverage"]) != 0.10:
        raise RuntimeError("The locked split-conformal alpha changed.")
    if str(design["test_sidedness"]) != "upper_tail_excess_miscoverage":
        raise RuntimeError("The locked one-sided test direction changed.")
    if str(design["null_law"]) != "exchangeable_split_conformal_beta_binomial_upper_bound":
        raise RuntimeError("The locked exchangeable-rank null law changed.")
    if str(design["unresolved_primary_count"]) != "sharp_loanwise_minimum_misses":
        raise RuntimeError("The locked unresolved-endpoint test count changed.")
    if int(multiplicity["strata_per_cell"]) != taxonomy_groups:
        raise RuntimeError("The within-cell multiplicity count changed.")
    if int(multiplicity["cell_family_size"]) != len(learners) * len(window_ids):
        raise RuntimeError("The Holm cell-family size changed.")
    if str(multiplicity["within_cell_method"]) != "bonferroni":
        raise RuntimeError("The predeclared within-cell method is not Bonferroni.")
    if str(multiplicity["across_cells_method"]) != "holm":
        raise RuntimeError("The predeclared across-cell method is not Holm.")
    if float(multiplicity["familywise_alpha"]) != 0.05:
        raise RuntimeError("The locked familywise alpha changed.")

    scores = pd.read_parquet(artifact_paths["scores"])
    recipes = load_recipes(artifact_paths["recipes"])
    fit_audit = pd.read_parquet(
        artifact_paths["fit_audit"],
        columns=[
            "id",
            "issue_d",
            "learner",
            "window_id",
            "taxonomy_groups",
            "conformal_group",
            "pd_point",
            "conformal_lower",
            "conformal_upper",
            "terminal_default",
            "covered",
        ],
        filters=[("taxonomy_groups", "==", taxonomy_groups)],
    )
    universe = load_outcome_universe(active_config, raw_path=raw_path)
    outcomes = configured_archive_outcomes(universe, active_config)
    strata, cells = build_exchangeability_transport_test(
        scores,
        outcomes,
        fit_audit,
        temporal_reference,
        recipes,
        learners=learners,
        window_ids=window_ids,
        role=str(design["role"]),
        taxonomy_groups=taxonomy_groups,
        expected_issue_months=tuple(str(value) for value in design["issue_months"]),
        expected_candidates=int(design["expected_candidates"]),
        expected_resolved=int(design["expected_resolved"]),
        expected_unresolved=int(design["expected_unresolved"]),
        expected_resolved_y0=int(design["expected_resolved_y0"]),
        expected_resolved_y1=int(design["expected_resolved_y1"]),
        nominal_miscoverage=float(design["nominal_miscoverage"]),
        familywise_alpha=float(multiplicity["familywise_alpha"]),
    )
    expected_strata = len(learners) * len(window_ids) * taxonomy_groups
    expected_cells = len(learners) * len(window_ids)
    if len(strata) != expected_strata or len(cells) != expected_cells:
        raise RuntimeError("The complete exchangeability reporting grid is incomplete.")

    outputs = prepare_output_paths(
        config,
        repo_root=root,
        allowed_data_root=ALLOWED_DATA_ROOT,
        allowed_model_root=ALLOWED_MODEL_ROOT,
    )
    strata_path = atomic_write_parquet(
        strata,
        outputs.data_dir / str(config["output"]["strata_table"]),
    )
    cells_path = atomic_write_parquet(
        cells,
        outputs.data_dir / str(config["output"]["cell_table"]),
    )
    summary = {
        "schema_version": str(config["schema_version"]),
        "status": "complete_retrospective_exchangeability_transport_test",
        "run_tag": str(config["run_tag"]),
        "protocol_tag": str(config["protocol_tag"]),
        "protocol_commit": protocol_commit,
        "scope": "five_learners_by_eight_windows_by_five_frozen_score_strata",
        "source_artifacts": {
            "active_v5_config": relative_artifact_descriptor(active_config_path, repo_root=root),
            "credit_control_summary": relative_artifact_descriptor(summary_path, repo_root=root),
            "temporal_coverage": relative_artifact_descriptor(temporal_path, repo_root=root),
            "credit_control_freeze": relative_artifact_descriptor(freeze_path, repo_root=root),
            "scores": relative_artifact_descriptor(artifact_paths["scores"], repo_root=root),
            "recipes": relative_artifact_descriptor(artifact_paths["recipes"], repo_root=root),
            "fit_audit": relative_artifact_descriptor(artifact_paths["fit_audit"], repo_root=root),
            "raw_archive": relative_artifact_descriptor(raw_path, repo_root=root),
        },
        "counts": {
            "stratum_tests": int(len(strata)),
            "learner_window_cells": int(len(cells)),
            "learners": int(strata["learner"].nunique()),
            "windows_per_learner": int(strata["window_id"].nunique()),
            "strata_per_cell": taxonomy_groups,
            "candidate_rows": int(
                strata.groupby(["learner", "window_id"])["candidate_rows"].sum().iloc[0]
            ),
            "resolved_rows": int(
                strata.groupby(["learner", "window_id"])["resolved_rows"].sum().iloc[0]
            ),
            "unresolved_rows": int(
                strata.groupby(["learner", "window_id"])["unresolved_rows"].sum().iloc[0]
            ),
        },
        "rank_null": {
            "sidedness": "upper_tail_excess_miscoverage",
            "law": "BetaBinomial(m, n + 1 - r, r)",
            "rank": "r = ceil((n + 1) * (1 - alpha))",
            "assumptions": [
                "exchangeability_of_calibration_and_target_scores_within_frozen_stratum",
                "fixed_outcome_free_score_taxonomy",
            ],
            "continuous_scores_give_exact_count_law": True,
            "ties_use_random_lexicographic_augmentation_as_a_proof_device": True,
            "deterministic_strict_miss_count_is_bounded_by_broken_tie_count": True,
            "beta_binomial_upper_tail_is_conservative_with_ties": True,
            "all_calibration_threshold_ties_singleton": bool(
                strata["continuous_threshold_tie_singleton"].astype(bool).all()
            ),
            "strata_with_non_singleton_calibration_threshold_ties": int(
                (~strata["continuous_threshold_tie_singleton"].astype(bool)).sum()
            ),
            "resolved_target_scores_equal_threshold": int(
                strata["resolved_target_residual_equal_threshold"].sum()
            ),
            "unresolved_target_equal_threshold_minimum": int(
                strata["unresolved_min_equal_threshold"].sum()
            ),
            "unresolved_target_equal_threshold_maximum": int(
                strata["unresolved_max_equal_threshold"].sum()
            ),
            "zero_observed_ties_would_not_prove_continuity": True,
        },
        "unresolved_endpoint_rule": {
            "primary_count": "resolved misses plus loan-wise minimum of misses under y=0 and y=1",
            "sharp_under_unrestricted_binary_completion": True,
            "p_value_role": "supremum upper-tail p-value over unresolved binary completions",
            "maximum_miss_count_reported_but_not_used_for_rejection": True,
        },
        "multiplicity": {
            "familywise_alpha": float(multiplicity["familywise_alpha"]),
            "within_cell": "Bonferroni over five frozen score strata",
            "across_cells": "Holm step-down over forty learner-window omnibus p-values",
            "dependence_assumption": "none_for_bonferroni_or_holm_fwer_control",
            "formal_rejection_family": "forty_learner_window_intersection_nulls",
            "stratum_flags_control_global_200_test_fwer": False,
            "post_inspection_not_study_wide_confirmatory_error_control": True,
        },
        "results": {
            "raw_strata_rejecting_at_family_alpha": int(
                (
                    strata["exact_log_p_value"] <= math.log(float(multiplicity["familywise_alpha"]))
                ).sum()
            ),
            "within_cell_bonferroni_flags_at_cell_alpha": int(
                strata["within_cell_bonferroni_reject_at_cell_alpha"].astype(bool).sum()
            ),
            "stratum_rejections_are_not_global_200_test_claims": True,
            "holm_rejected_cells": int(
                cells["holm_reject_exchangeability_null"].astype(bool).sum()
            ),
            "minimum_exact_log_p_value": float(strata["exact_log_p_value"].min()),
            "minimum_holm_adjusted_log_p_value": float(cells["holm_adjusted_log_p_value"].min()),
        },
        "interpretation": dict(config["interpretation"]),
        "artifacts": {
            "stratum_tests": relative_artifact_descriptor(strata_path, repo_root=root),
            "learner_window_cells": relative_artifact_descriptor(cells_path, repo_root=root),
        },
        "implementation_provenance": implementation_provenance(
            config_path=resolved_config,
            repo_root=root,
            relative_paths=[
                Path("scripts/experiments/run_ijds_exchangeability_transport_test.py"),
                Path("src/ijds_audit/exchangeability_transport_test.py"),
                Path("src/ijds_audit/protocol.py"),
                Path("src/data/outcome_observability.py"),
                Path("src/models/binary_conformal_guardrail.py"),
                Path("src/utils/isolated_experiment.py"),
                Path("docs/research/ijds_exchangeability_transport_test_protocol_2026-07-21.md"),
            ],
        ),
        "environment": environment_provenance(root),
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    output_summary_path = atomic_write_json(
        outputs.model_dir / str(config["output"]["summary"]), summary
    )
    atomic_write_json(
        outputs.model_dir / str(config["output"]["execution_receipt"]),
        {
            "schema_version": str(config["schema_version"]),
            "run_tag": str(config["run_tag"]),
            "protocol_tag": str(config["protocol_tag"]),
            "protocol_commit": protocol_commit,
            "summary": relative_artifact_descriptor(output_summary_path, repo_root=root),
            "environment": environment_provenance(root),
            "protected_stages_run": [],
            "protected_artifacts_written": [],
        },
    )
    return output_summary_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    print(run(config_path=args.config, repo_root=args.repo_root))


if __name__ == "__main__":
    main()
