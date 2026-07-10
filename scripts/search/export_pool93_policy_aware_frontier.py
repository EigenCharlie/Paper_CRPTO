"""Export the policy-aware pool93 frontier as CSV and LaTeX."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DEFAULT_TAG = "champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2"
DEFAULT_FRONTIER = (
    ROOT
    / "models/experiments/champion_reopen"
    / DEFAULT_TAG
    / "portfolio/pool93_ijds_consolidated_frontier.json"
)
DEFAULT_TABLE_DIR = ROOT / "reports/crpto/experiments" / DEFAULT_TAG
DEFAULT_TABLE_NAME = "crpto_tableA35_pool93_ijds_frontier_policy_aware_v2"

ROLE_ORDER = (
    "minimum Markov-threshold endpoint",
    "lowest realized V return-bound point",
    "highest return under threshold<=0.3",
    "highest return under threshold<=0.32",
    "highest return under threshold<=0.345",
    "body/default balanced return-bound point",
    "highest return under threshold<=0.36",
    "highest return under threshold<=0.45",
    "max-return economic endpoint",
)
ROLE_LABELS = {
    "minimum Markov-threshold endpoint": "Minimum Markov-threshold endpoint",
    "lowest realized V return-bound point": "Low-threshold balanced endpoint",
    "highest return under threshold<=0.3": "Highest return under threshold <= 0.30",
    "highest return under threshold<=0.32": "Highest return under threshold <= 0.32",
    "highest return under threshold<=0.345": "Highest return under threshold <= 0.345",
    "body/default balanced return-bound point": "Body/default balanced point",
    "highest return under threshold<=0.36": "Highest return under threshold <= 0.36",
    "highest return under threshold<=0.45": "Highest return under threshold <= 0.45",
    "max-return economic endpoint": "Max-return economic endpoint",
}


def build_table(frontier: dict[str, Any]) -> pd.DataFrame:
    """Build the compact publication table in its declared role order."""
    rows_by_role = {str(row["role"]): dict(row) for row in frontier.get("rows", [])}
    missing = [role for role in ROLE_ORDER if role not in rows_by_role]
    if missing:
        raise ValueError(f"Policy-aware frontier is missing roles: {missing}")
    rows = []
    for role in ROLE_ORDER:
        row = rows_by_role[role]
        rows.append(
            {
                "role": ROLE_LABELS[role],
                "source_run": str(row["run_label"]),
                "candidate_id": int(row["local_candidate_id"]),
                "policy_family": str(row["family"]),
                "risk_tolerance": float(row["risk_tolerance"]),
                "policy_mode": str(row["policy_mode"]),
                "gamma": float(row["gamma"]),
                "uncertainty_aversion": float(row["uncertainty_aversion"]),
                "realized_return": float(row["return"]),
                "return_floor_surplus": float(row["return_floor_surplus"]),
                "Gamma_CP_alpha01": float(row["Gamma_CP"]),
                "Gamma_residual_alpha01": float(row["Gamma_residual"]),
                "V_alpha01": float(row["V"]),
                "endpoint_budget_alpha01": float(row["endpoint_budget"]),
                "endpoint_budget_upper_alpha01": float(row["endpoint_budget_upper"]),
                "Markov_threshold_alpha01": float(row["Markov_threshold"]),
                "Markov_cap_alpha01": float(row["Markov_cap"]),
                "alpha_grid_pass": str(row["alpha_pass"]),
                "n_funded_mean": float(row["n_funded_mean"]),
            }
        )
    return pd.DataFrame(rows)


def _format_tex(table: pd.DataFrame) -> str:
    lines = [
        "\\begin{tabular}{llrrrrrr}",
        "\\toprule",
        (
            "Role & Source & Return & $\\Gamma_{\\mathrm{CP}}$ & "
            "$\\Gamma_{\\mathrm{res}}$ & $V$ & Markov threshold & Pass \\\\"
        ),
        "\\midrule",
    ]
    for row in table.to_dict("records"):
        role = str(row["role"]).replace("<=", "$\\leq$")
        source = str(row["source_run"]).replace("_", " ")
        lines.append(
            f"{role} & {source} & {float(row['realized_return']):,.2f} & "
            f"{float(row['Gamma_CP_alpha01']):.6f} & "
            f"{float(row['Gamma_residual_alpha01']):.6f} & "
            f"{float(row['V_alpha01']):.6f} & "
            f"{float(row['Markov_threshold_alpha01']):.6f} & "
            f"{row['alpha_grid_pass']} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def write_frontier_table(table: pd.DataFrame, *, table_dir: Path, table_name: str) -> None:
    """Write the full audit CSV and compact publication LaTeX table."""
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / f"{table_name}.csv"
    tex_path = table_dir / f"{table_name}.tex"
    outputs = {
        csv_path: table.to_csv(index=False, lineterminator="\n"),
        tex_path: _format_tex(table),
    }
    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.write_text(content, encoding="utf-8", newline="")
    print(f"Wrote {csv_path.relative_to(ROOT).as_posix()}")
    print(f"Wrote {tex_path.relative_to(ROOT).as_posix()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", default=str(DEFAULT_FRONTIER))
    parser.add_argument("--table-dir", default=str(DEFAULT_TABLE_DIR))
    parser.add_argument("--table-name", default=DEFAULT_TABLE_NAME)
    args = parser.parse_args(argv)
    frontier = json.loads(Path(args.frontier).read_text(encoding="utf-8"))
    write_frontier_table(
        build_table(frontier),
        table_dir=Path(args.table_dir).resolve(),
        table_name=str(args.table_name),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
