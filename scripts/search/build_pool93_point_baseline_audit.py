"""Build a matched point-PD baseline for the selected pool93 decision.

The audit holds the candidate universe, budget, concentration cap and risk
tolerance fixed. It changes only the decision uncertainty treatment: the
baseline constrains calibrated point PD, while the selected CRPTO allocation
uses its declared effective-PD policy. Outputs are isolated from the frozen
champion and contain no policy search.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.optimize_portfolio_tradeoff import _parse_percent_series  # noqa: E402
from scripts.search.build_pool93_body_allocation_audit import (  # noqa: E402
    _load_role_row,
    _manifest_path,
    _policy_from_row,
)
from scripts.validate_alpha_gamma_bound import (  # noqa: E402
    DEFAULT_LGD,
    DEFAULT_MAX_CONCENTRATION,
    DEFAULT_TIME_LIMIT,
    _compute_intervals_at_alpha,
    _load_aligned_dataset,
)
from src.optimization.certificate_semantics import (  # noqa: E402
    FundedCertificateMetrics,
    compute_funded_certificate_metrics,
)
from src.optimization.portfolio_model import (  # noqa: E402
    optimize_portfolio_allocation,
    solution_allocation_vector,
)
from src.utils.script_helpers import resolve_repo_artifact_path, write_table  # noqa: E402

DEFAULT_TAG = "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2"
DEFAULT_ROLE = "body/default balanced return-bound point"
DEFAULT_FRONTIER = (
    ROOT
    / "models/experiments/champion_reopen"
    / DEFAULT_TAG
    / "portfolio/pool93_ijds_consolidated_frontier.json"
)
DEFAULT_BODY_ALLOCATION = (
    ROOT
    / "data/processed/experiments/champion_reopen"
    / "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive"
    / "portfolio/pool93_body_allocation_alpha01.parquet"
)
DEFAULT_OUTPUT_DIR = ROOT / "models/experiments/champion_reopen" / DEFAULT_TAG / "portfolio"
DEFAULT_DATA_OUTPUT_DIR = (
    ROOT / "data/processed/experiments/champion_reopen" / DEFAULT_TAG / "portfolio"
)
DEFAULT_TABLE_DIR = ROOT / "reports/crpto/experiments" / DEFAULT_TAG


def _realized_return(
    allocation: np.ndarray,
    loan_amounts: np.ndarray,
    int_rates: np.ndarray,
    default_flag: np.ndarray,
) -> float:
    exposure = allocation * loan_amounts
    funded = allocation > 0.01
    contributions = np.where(
        funded & (default_flag.astype(int) == 1),
        -DEFAULT_LGD * exposure,
        np.where(funded, int_rates * exposure, 0.0),
    )
    return float(contributions.sum())


def _economic_metrics(
    *,
    allocation: np.ndarray,
    loan_amounts: np.ndarray,
    int_rates: np.ndarray,
    pd_point: np.ndarray,
) -> dict[str, float]:
    exposure = allocation * loan_amounts
    return {
        "total_allocated": float(exposure.sum()),
        "expected_return_gross": float(np.sum(exposure * int_rates)),
        "expected_loss_point": float(np.sum(exposure * pd_point * DEFAULT_LGD)),
        "expected_return_net_point": float(
            np.sum(exposure * int_rates) - np.sum(exposure * pd_point * DEFAULT_LGD)
        ),
    }


def _comparison_table(
    point: dict[str, Any],
    selected: dict[str, Any],
) -> pd.DataFrame:
    point_return = float(point["realized_return"])
    rows = []
    for label, payload in (
        ("Point-PD two-stage LP", point),
        ("Selected CRPTO", selected),
    ):
        rows.append(
            {
                "policy": label,
                "realized_return": float(payload["realized_return"]),
                "return_cost_vs_point_pct": 100.0
                * (point_return - float(payload["realized_return"]))
                / point_return,
                "n_funded": int(payload["certificate"]["n_funded"]),
                "weighted_default_rate": float(payload["certificate"]["weighted_outcome"]),
                "V_alpha01": float(payload["certificate"]["weighted_miscoverage"]),
                "Gamma_CP_alpha01": float(payload["certificate"]["gamma_cp"]),
                "endpoint_budget_alpha01": float(payload["certificate"]["endpoint_budget"]),
                "Markov_threshold_alpha01": float(payload["certificate"]["markov_loss_threshold"]),
                "expected_return_net_point": float(payload["expected_return_net_point"]),
            }
        )
    return pd.DataFrame(rows)


def _format_comparison_tex(table: pd.DataFrame) -> str:
    """Render the compact comparison used in the paper and supplement."""
    lines = [
        "\\begin{tabular}{lrrrrr}",
        "\\toprule",
        (
            "Policy & Realized return & Weighted default & "
            "$\\Gamma_{\\mathrm{CP}}$ & $B_u$ & Markov threshold \\\\"
        ),
        "\\midrule",
    ]
    for row in table.to_dict("records"):
        lines.append(
            f"{row['policy']} & \\${float(row['realized_return']):,.2f} & "
            f"{float(row['weighted_default_rate']):.6f} & "
            f"{float(row['Gamma_CP_alpha01']):.6f} & "
            f"{float(row['endpoint_budget_alpha01']):.6f} & "
            f"{float(row['Markov_threshold_alpha01']):.6f} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def _certificate_payload(
    certificate: FundedCertificateMetrics,
    *,
    realized_return: float,
    economic: dict[str, float],
    solver_status: str,
) -> dict[str, Any]:
    return {
        "solver_status": solver_status,
        "realized_return": realized_return,
        **economic,
        "certificate": asdict(certificate),
    }


def build_audit(
    *,
    frontier_path: Path,
    body_allocation_path: Path,
    role: str,
    alpha: float,
    output_dir: Path,
    data_output_dir: Path,
    table_dir: Path,
    threads: int,
) -> dict[str, Any]:
    row = _load_role_row(frontier_path, role)
    policy = _policy_from_row(row)
    manifest = json.loads(_manifest_path(str(row["run_tag"])).read_text(encoding="utf-8"))
    interval_path = resolve_repo_artifact_path(manifest["conformal_intervals_path"], root=ROOT)
    aligned = _load_aligned_dataset(
        conformal_intervals_path=str(interval_path),
        max_candidates=int(manifest.get("max_candidates", 0) or 0),
        random_state=int(manifest.get("random_state", 42)),
    )
    pd_point, pd_low, pd_high = _compute_intervals_at_alpha(aligned, alpha)
    y_true = pd.to_numeric(aligned["y_true"], errors="coerce").fillna(0.0).to_numpy(float)
    default_flag = (
        pd.to_numeric(aligned["default_flag"], errors="coerce").fillna(0).to_numpy(dtype=int)
    )
    loan_amounts = pd.to_numeric(aligned["loan_amnt"], errors="coerce").fillna(1.0).to_numpy(float)
    int_rates = _parse_percent_series(aligned["int_rate"])
    risk_tolerance = float(policy["risk_tolerance"])
    solution = optimize_portfolio_allocation(
        loans=aligned,
        pd_point=pd_point,
        pd_low=pd_low,
        pd_high=pd_high,
        lgd=np.full(len(aligned), DEFAULT_LGD, dtype=float),
        int_rates=int_rates,
        total_budget=float(manifest.get("budget", 1_000_000.0)),
        max_concentration=DEFAULT_MAX_CONCENTRATION,
        max_portfolio_pd=risk_tolerance,
        robust=False,
        uncertainty_aversion=0.0,
        min_budget_utilization=float(policy["min_budget_utilization"]),
        pd_cap_slack_penalty=float(policy["pd_cap_slack_penalty"]),
        pd_constraint_override=pd_point,
        time_limit=DEFAULT_TIME_LIMIT,
        threads=max(1, int(threads)),
        solver_backend=str(policy["solver_backend"]),
    )
    point_allocation = solution_allocation_vector(solution, len(aligned))
    point_exposure = point_allocation * loan_amounts
    point_weights = point_exposure / max(float(point_exposure.sum()), 1e-12)
    point_certificate = compute_funded_certificate_metrics(
        point_weights,
        outcomes=y_true,
        pd_point=pd_point,
        pd_high=pd_high,
        pd_effective=pd_point,
        alpha=alpha,
        risk_tolerance=risk_tolerance,
        pd_cap_slack=float(solution.get("pd_cap_slack", 0.0)),
    )
    point_payload = _certificate_payload(
        point_certificate,
        realized_return=_realized_return(
            point_allocation,
            loan_amounts,
            int_rates,
            default_flag,
        ),
        economic=_economic_metrics(
            allocation=point_allocation,
            loan_amounts=loan_amounts,
            int_rates=int_rates,
            pd_point=pd_point,
        ),
        solver_status=str(solution.get("solver_status", "unknown")),
    )

    funded = pd.read_parquet(body_allocation_path)
    selected_weights = funded["funded_weight"].to_numpy(float)
    selected_point = funded["pd_point_alpha01"].to_numpy(float)
    selected_high = funded["pd_high_alpha01"].to_numpy(float)
    selected_effective = funded["effective_pd"].to_numpy(float)
    selected_outcomes = funded["default_flag"].to_numpy(float)
    selected_exposure = funded["funded_exposure"].to_numpy(float)
    selected_rates = _parse_percent_series(funded["int_rate"])
    selected_certificate = compute_funded_certificate_metrics(
        selected_weights,
        outcomes=selected_outcomes,
        pd_point=selected_point,
        pd_high=selected_high,
        pd_effective=selected_effective,
        alpha=alpha,
        risk_tolerance=risk_tolerance,
    )
    selected_payload = _certificate_payload(
        selected_certificate,
        realized_return=float(funded["realized_return"].sum()),
        economic={
            "total_allocated": float(selected_exposure.sum()),
            "expected_return_gross": float(np.sum(selected_exposure * selected_rates)),
            "expected_loss_point": float(np.sum(selected_exposure * selected_point * DEFAULT_LGD)),
            "expected_return_net_point": float(
                np.sum(selected_exposure * selected_rates)
                - np.sum(selected_exposure * selected_point * DEFAULT_LGD)
            ),
        },
        solver_status="frozen_selected_allocation",
    )

    table = _comparison_table(point_payload, selected_payload)
    table_paths = write_table(
        "crpto_tableA40_pool93_point_baseline",
        table,
        table_dir=table_dir,
        root=ROOT,
        float_precision=6,
    )
    table_paths[1].write_text(
        _format_comparison_tex(table),
        encoding="utf-8",
        newline="",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    data_output_dir.mkdir(parents=True, exist_ok=True)
    point_rows = aligned.loc[point_allocation > 0.01].copy()
    point_rows["allocation"] = point_allocation[point_allocation > 0.01]
    point_rows["funded_exposure"] = point_exposure[point_allocation > 0.01]
    point_rows["funded_weight"] = point_weights[point_allocation > 0.01]
    point_rows_path = data_output_dir / "pool93_point_pd_baseline_alpha01.parquet"
    point_rows.to_parquet(point_rows_path, index=False)

    return_cost = float(point_payload["realized_return"]) - float(
        selected_payload["realized_return"]
    )
    payload = {
        "schema_version": "2026-07-09.1",
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "run_tag": DEFAULT_TAG,
        "comparison": "matched point-PD two-stage LP versus selected CRPTO",
        "fixed_design": {
            "candidate_universe": len(aligned),
            "budget": float(manifest.get("budget", 1_000_000.0)),
            "risk_tolerance": risk_tolerance,
            "max_concentration": DEFAULT_MAX_CONCENTRATION,
            "alpha": alpha,
        },
        "point_pd_baseline": point_payload,
        "selected_crpto": selected_payload,
        "contrasts": {
            "realized_return_cost": return_cost,
            "realized_return_cost_pct": 100.0
            * return_cost
            / float(point_payload["realized_return"]),
            "weighted_default_rate_reduction": point_certificate.weighted_outcome
            - selected_certificate.weighted_outcome,
            "weighted_miscoverage_reduction": point_certificate.weighted_miscoverage
            - selected_certificate.weighted_miscoverage,
            "markov_threshold_reduction": point_certificate.markov_loss_threshold
            - selected_certificate.markov_loss_threshold,
        },
        "claim_boundary": (
            "Frozen OOT matched-policy audit; it quantifies a return-risk trade-off and "
            "does not establish causal, prospective or universal dominance."
        ),
        "outputs": {
            "point_funded_rows": str(point_rows_path),
            "table_csv": str(table_paths[0]),
            "table_tex": str(table_paths[1]),
        },
    }
    output_path = output_dir / "pool93_point_pd_baseline_audit.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER))
    parser.add_argument("--body-allocation", default=str(DEFAULT_BODY_ALLOCATION))
    parser.add_argument("--role", default=DEFAULT_ROLE)
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--data-output-dir", default=str(DEFAULT_DATA_OUTPUT_DIR))
    parser.add_argument("--table-dir", default=str(DEFAULT_TABLE_DIR))
    args = parser.parse_args(argv)
    payload = build_audit(
        frontier_path=Path(args.frontier).resolve(),
        body_allocation_path=Path(args.body_allocation).resolve(),
        role=str(args.role),
        alpha=float(args.alpha),
        output_dir=Path(args.output_dir).resolve(),
        data_output_dir=Path(args.data_output_dir).resolve(),
        table_dir=Path(args.table_dir).resolve(),
        threads=max(1, int(args.threads)),
    )
    print(json.dumps(payload["contrasts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
