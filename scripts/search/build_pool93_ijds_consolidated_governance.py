"""Build the paper-facing governance sidecar for the consolidated pool93 frontier."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSOLIDATED_TAG = "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2"
DEFAULT_BODY_ROLE = "body/default balanced return-bound point"


def _default_paths(consolidated_tag: str) -> tuple[Path, Path]:
    portfolio_dir = ROOT / "models/experiments/champion_reopen" / consolidated_tag / "portfolio"
    return (
        portfolio_dir / "pool93_ijds_consolidated_frontier.json",
        portfolio_dir / "pool93_ijds_consolidated_governance.json",
    )


def _find_role(rows: list[dict[str, Any]], role: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("role")) == role:
            return dict(row)
    raise ValueError(f"Role {role!r} not found in consolidated frontier.")


def build_governance(frontier_path: Path, *, body_role: str) -> dict[str, Any]:
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    rows = list(frontier.get("rows", []))
    body = _find_role(rows, body_role)
    strict_threshold = _find_role(rows, "highest return under threshold<=0.345")
    low_threshold = _find_role(rows, "minimum Markov-threshold endpoint")
    max_return = _find_role(rows, "max-return economic endpoint")
    return {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "source_frontier_path": str(frontier_path),
        "source_run_tags": frontier.get("source_run_tags", []),
        "counts": frontier.get("counts", {}),
        "selection_rule": frontier.get("selection_rule", {}),
        "certificate_semantics_audit": frontier.get("certificate_semantics_audit", {}),
        "claim_hierarchy": {
            "status": "final",
            "paper_body_candidate": body_role,
            "paper_body_claim": (
                "The selected pool93 body point is the highest-return eligible "
                "finite-grid policy under the declared exact Markov-threshold ceiling "
                "and passes all eight predeclared alpha checks."
            ),
            "appendix_frontier_candidates": [
                "minimum Markov-threshold endpoint",
                "highest return under threshold<=0.345",
                "highest return under threshold<=0.36",
                "max-return economic endpoint",
            ],
            "do_not_claim": [
                "continuous-region optimality beyond the evaluated finite policy grid",
                "nominal funded-set alpha coverage when V(alpha) exceeds alpha",
                "prospective live-selection validity from retrospective OOT selection",
                "pool93-specific row-level tail/CVaR dominance unless regenerated from the promoted allocation",
            ],
            "promotion_gate": [
                "consolidated frontier generated from completed exact runs",
                "semantic-policy deduplication applied",
                "policy-aware endpoint decomposition applied to every alpha=0.01 row",
                "selected body point passes 8/8 alpha checks",
                "zero realized risk-tolerance excess at alpha=0.01",
                "return exceeds declared return floor",
                "A35 frontier, A36 funded-set grade audit, and A40 matched baseline are regenerated from retained artifacts",
            ],
        },
        "selected_candidates": {
            "paper_body": body,
            "strict_threshold_leq_0_345": strict_threshold,
            "minimum_markov_threshold_endpoint": low_threshold,
            "max_return_economic_endpoint": max_return,
        },
        "paper_artifacts": {
            "frontier_table_csv": "reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv",
            "frontier_table_tex": "reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.tex",
            "funded_grade_audit_csv": "reports/crpto/tables/crpto_tableA36_pool93_body_funded_grade_audit.csv",
            "funded_grade_audit_tex": "reports/crpto/tables/crpto_tableA36_pool93_body_funded_grade_audit.tex",
            "point_baseline_csv": "reports/crpto/tables/crpto_tableA40_pool93_point_baseline.csv",
            "point_baseline_tex": "reports/crpto/tables/crpto_tableA40_pool93_point_baseline.tex",
            "point_baseline_audit": (
                "models/experiments/champion_reopen/"
                "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/"
                "portfolio/pool93_point_pd_baseline_audit.json"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consolidated-tag", default=DEFAULT_CONSOLIDATED_TAG)
    parser.add_argument("--frontier", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--body-role", default=DEFAULT_BODY_ROLE)
    args = parser.parse_args(argv)

    default_frontier, default_output = _default_paths(str(args.consolidated_tag))
    frontier_path = Path(args.frontier) if args.frontier else default_frontier
    output_path = Path(args.output) if args.output else default_output
    payload = build_governance(frontier_path, body_role=str(args.body_role))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
