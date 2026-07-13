"""Build tracked evidence from the locked policy-support and tie audit."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.isolated_experiment import relative_artifact_descriptor, write_csv_atomic
from src.utils.pipeline_runtime import atomic_write_json, atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
RUN_TAG = "ijds-policy-support-tie-audit-2026-07-12-v1"
PROTOCOL_TAG = "protocol/ijds-policy-support-tie-audit-2026-07-12-v1"
PROTOCOL_COMMIT = "115eaf1b81ed5f05ffe601e9c20079059c40c200"
MODEL_DIR = ROOT / "models/experiments/ijds_audit" / RUN_TAG
DATA_DIR = ROOT / "data/processed/experiments/ijds_audit" / RUN_TAG
SOURCE_SUMMARY = MODEL_DIR / "policy_support_tie_audit_summary.json"
FAMILY_PATH = DATA_DIR / "policy_family_feasibility.parquet"
DIAGNOSTICS_PATH = DATA_DIR / "point_cap_basis_diagnostics.parquet"
SENSITIVITY_PATH = DATA_DIR / "point_cap_order_sensitivity.parquet"
EVIDENCE_PATH = ROOT / "reports/crpto/ijds_policy_support_tie_evidence.json"
TABLE_DIR = ROOT / "reports/crpto/tables"
MEMO_PATH = ROOT / "docs/research/ijds_policy_support_tie_results_2026-07-12.md"


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object at {path}.")
    return payload


def _verify_descriptor(descriptor: Mapping[str, Any]) -> Path:
    path = (ROOT / str(descriptor["path"])).resolve()
    actual = relative_artifact_descriptor(path, repo_root=ROOT)
    for field in ("path", "bytes", "sha256"):
        if actual[field] != descriptor[field]:
            raise RuntimeError(f"Policy-support source mismatch for {path}: {field}.")
    return path


def _family_table(family: pd.DataFrame) -> pd.DataFrame:
    table = (
        family.groupby(
            ["role", "gamma", "risk_tolerance", "cap_classification"],
            observed=True,
            sort=True,
        )
        .agg(
            cells=("period", "size"),
            binding_cells=("cap_binding", "sum"),
            minimum_score=("minimum_feasible_score", "min"),
            mean_score=("weighted_effective_score", "mean"),
            maximum_score=("unconstrained_objective_score", "max"),
            objective_mean=("expected_objective", "mean"),
        )
        .reset_index()
    )
    if int(table["cells"].sum()) != 3_120:
        raise RuntimeError("Policy-family summary lost an endpoint cell.")
    return table


def _endpoint_table(family: pd.DataFrame) -> pd.DataFrame:
    keys = ["window_id", "role", "period", "risk_tolerance"]
    gamma_075 = family.loc[family["gamma"].eq(0.75), [*keys, "expected_objective"]].rename(
        columns={"expected_objective": "gamma_075_objective"}
    )
    gamma_100 = family.loc[
        family["gamma"].eq(1.0), [*keys, "expected_objective", "cap_classification"]
    ].rename(
        columns={
            "expected_objective": "gamma_100_objective",
            "cap_classification": "gamma_100_cap_classification",
        }
    )
    paired = gamma_075.merge(gamma_100, on=keys, validate="one_to_one")
    paired["gamma_100_minus_075_objective"] = (
        paired["gamma_100_objective"] - paired["gamma_075_objective"]
    )
    table = (
        paired.groupby(["role", "risk_tolerance"], observed=True, sort=True)
        .agg(
            cells=("period", "size"),
            gamma_100_decision_active=(
                "gamma_100_cap_classification",
                lambda values: int(values.eq("decision_active").sum()),
            ),
            objective_difference_mean=("gamma_100_minus_075_objective", "mean"),
            objective_difference_min=("gamma_100_minus_075_objective", "min"),
            objective_difference_max=("gamma_100_minus_075_objective", "max"),
        )
        .reset_index()
    )
    if len(paired) != 624 or int(table["cells"].sum()) != 624:
        raise RuntimeError("Gamma endpoint pairing lost a family cell.")
    return table


def _support_table(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in sorted(name for name in diagnostics if name.startswith("is_")):
        selected = diagnostics.loc[diagnostics[column]]
        counts = selected["cap_classification"].value_counts()
        rows.append(
            {
                "source": column.removeprefix("is_"),
                "cap_month_rows": int(len(selected)),
                "decision_active": int(counts.get("decision_active", 0)),
                "objective_boundary": int(counts.get("objective_boundary", 0)),
                "objective_slack": int(counts.get("objective_slack", 0)),
                "primal_degenerate_bases": int(selected["basis_primal_degenerate"].sum()),
                "near_zero_bases": int(selected["near_zero_nonbasic_reduced_costs"].gt(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def _memo(evidence: Mapping[str, Any]) -> str:
    results = evidence["results"]
    family = results["family"]
    point = results["point_cap_census"]
    order = results["order_sensitivity"]
    return f"""# IJDS Policy-Support and Solver-Tie Audit Results

## Status

The outcome-free audit completed under `{PROTOCOL_TAG}` at commit
`{PROTOCOL_COMMIT[:7]}`. It read only ID, amount, contractual rate, purpose,
frozen design role, point score, and frozen conformal recipes. No outcome column
entered a solve. These results are pre-freeze structural evidence and do not by
themselves promote a policy or empirical direction.

## Policy-family domain

- The audit retained 3,120 cells: eight windows, 26 months, five gamma levels,
  and three fixed risk tolerances.
- All 1,872 inherited interior cells were feasible; 1,846 were decision-active.
  The 26 slack cells all occur at `gamma=.25` in W8.
- `gamma=0` is objective-slack in all 624 cells under
  `tau={{.15,.17,.19}}`. It is correctly treated as a point-score nesting
  control, not an uncertainty-aware policy.
- `gamma=1` is feasible and decision-active in all 624 cells. Relative to
  `gamma=.75` on the same menu and cap, its plug-in objective is lower in all
  624 cells, by a mean of `{family["gamma_one_minus_075_objective_mean"]:.2f}`
  and a range from `{family["gamma_one_minus_075_objective_min"]:.2f}` to
  `{family["gamma_one_minus_075_objective_max"]:.2f}` plug-in objective dollars per
  monthly USD 1 million budget.
- Parent V4 scores and objectives reconcile to
  `{family["maximum_absolute_parent_score_difference"]:.3e}` and
  `{family["maximum_absolute_parent_objective_difference"]:.3e}`.

The endpoint result means the current nine-policy family is computationally
active but semantically incomplete. The next specification must either include
`gamma=1` as a complete-family sensitivity or replace fixed caps with a tagged
normalized-stringency design that includes both endpoints. Silent omission is
no longer defensible.

## Comparator support

The tolerance-deduplicated union contains `{point["rows"]}` cap-month pairs in
15 primary months. The earlier exploratory statement of 2,249 solves was not a
complete census; the correct named unique count is
`{point["named_unique_cap_months"]}` and the full union also includes support
endpoints and 2,952 period-specific basis breakpoints.

- All 45 C0 cap-months are objective-slack for point PD.
- C1 has 1,079 active and one slack cap-month.
- C2 has 1,075 active and four objective-boundary cap-months.
- Every lower development endpoint is active; six upper endpoints are slack.
- Broad `.05` is active in every month, while broad `.12` is slack in every
  month. `[.05,.12]` is therefore a stress interval spanning active and slack
  regions, not a normative admissible support.

## Solver ties

There are `{point["primal_degenerate_bases"]}` primal-degenerate bases, mostly
because basis breakpoints are transition points. None has a nonbasic reduced
cost within `1e-7` of zero; the minimum absolute nonbasic reduced cost is
`{point["minimum_absolute_nonbasic_reduced_cost"]:.6g}`. All
`{order["triggered_rows"]}` triggered caps were rerun after reversing loan-ID
order. Zero were tie-sensitive; maximum exposure distance was
`{order["maximum_allocation_distance"]:.3e}` and maximum absolute objective
difference `{order["maximum_absolute_objective_difference"]:.3e}`.

Thus primal degeneracy does not explain the portfolio directions in this finite
census. This supports deterministic stability at the evaluated caps, not a
universal uniqueness theorem over every real cap.

## Required next decision

Do not freeze the current family. The highest-value challenger is an
outcome-free normalized stringency parameter
`lambda=(q_cap-q_min)/(q_obj-q_min)` over both score endpoints. It directly
addresses the all-slack point endpoint and the arbitrary cross-score meaning of
one numeric tau. It must be separately tagged and reported whether it strengthens
or weakens the V4 conclusion. A simpler fallback is to add `gamma=1` to the
fixed-cap sensitivity and retain the exact support caveat.
"""


def build() -> Path:
    """Verify immutable sources and emit compact tracked evidence."""
    summary = _json(SOURCE_SUMMARY)
    if summary.get("status") != "complete":
        raise RuntimeError("Policy-support source run is incomplete.")
    if summary.get("protocol_tag") != PROTOCOL_TAG:
        raise RuntimeError("Policy-support protocol tag mismatch.")
    if summary.get("protocol_commit") != PROTOCOL_COMMIT:
        raise RuntimeError("Policy-support protocol commit mismatch.")
    if summary.get("outcome_columns_passed") != []:
        raise RuntimeError("Policy-support source reports an outcome column.")
    for descriptor in summary["artifacts"].values():
        _verify_descriptor(descriptor)

    family = pd.read_parquet(FAMILY_PATH)
    diagnostics = pd.read_parquet(DIAGNOSTICS_PATH)
    sensitivity = pd.read_parquet(SENSITIVITY_PATH)
    if len(family) != 3_120 or len(diagnostics) != 7_297 or len(sensitivity) != 2_941:
        raise RuntimeError("Policy-support source cardinality changed.")
    family_table = _family_table(family)
    endpoint_table = _endpoint_table(family)
    support_table = _support_table(diagnostics)
    table_paths = {
        "family": write_csv_atomic(family_table, TABLE_DIR / "crpto_ijds_policy_family_domain.csv"),
        "gamma_endpoint": write_csv_atomic(
            endpoint_table, TABLE_DIR / "crpto_ijds_gamma_endpoint_audit.csv"
        ),
        "comparator_support": write_csv_atomic(
            support_table, TABLE_DIR / "crpto_ijds_comparator_support_domain.csv"
        ),
    }

    gamma_pair = family.loc[
        family["gamma"].eq(1.0),
        [
            "window_id",
            "role",
            "period",
            "risk_tolerance",
            "expected_objective",
        ],
    ].merge(
        family.loc[
            family["gamma"].eq(0.75),
            [
                "window_id",
                "role",
                "period",
                "risk_tolerance",
                "expected_objective",
            ],
        ],
        on=["window_id", "role", "period", "risk_tolerance"],
        suffixes=("_100", "_075"),
        validate="one_to_one",
    )
    gamma_difference = gamma_pair["expected_objective_100"] - gamma_pair["expected_objective_075"]
    source_results = summary["results"]
    results = {
        "family": {
            **source_results["family"],
            "gamma_zero_objective_slack": int(
                family.loc[family["gamma"].eq(0.0), "cap_classification"]
                .eq("objective_slack")
                .sum()
            ),
            "inherited_slack": int(
                family.loc[family["gamma"].isin([0.25, 0.5, 0.75]), "cap_classification"]
                .eq("objective_slack")
                .sum()
            ),
            "gamma_one_minus_075_objective_mean": float(gamma_difference.mean()),
            "gamma_one_minus_075_objective_min": float(gamma_difference.min()),
            "gamma_one_minus_075_objective_max": float(gamma_difference.max()),
        },
        "point_cap_census": source_results["point_cap_census"],
        "order_sensitivity": source_results["order_sensitivity"],
    }
    evidence = {
        "schema_version": "2026-07-12.1",
        "status": "complete_prefreeze_structural_evidence",
        "active_claim_status": "not_active_until_family_redesign_decision",
        "run_tag": RUN_TAG,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "claim_boundary": summary["claim_boundary"],
        "outcome_columns_passed": [],
        "results": results,
        "source_summary": relative_artifact_descriptor(SOURCE_SUMMARY, repo_root=ROOT),
        "source_artifacts": summary["artifacts"],
        "tables": {
            name: relative_artifact_descriptor(path, repo_root=ROOT)
            for name, path in table_paths.items()
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    atomic_write_json(EVIDENCE_PATH, evidence)
    atomic_write_text(MEMO_PATH, _memo(evidence))
    return EVIDENCE_PATH


if __name__ == "__main__":
    build()
