#!/usr/bin/env python
"""Run the standalone CRPTO pipeline in fixed, auditable steps."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = ROOT / "reports" / "run_logs"

STEPS = {
    "preflight": [
        "python -m pytest -q tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py",
    ],
    "core_data_pd": [
        "python src/data/make_dataset.py --input data/raw/Loan_status_2007-2020Q3.csv --output data/processed/loan_master.parquet",
        "python src/data/prepare_dataset.py",
        "python scripts/materialize_feature_artifacts.py --config configs/crpto_pd_model.yaml",
        "python scripts/train_pd_model.py --config configs/crpto_pd_model.yaml",
    ],
    "core_conformal": [
        "python scripts/generate_conformal_intervals.py --config configs/crpto_conformal_policy.yaml",
        "python scripts/benchmark_conformal_variants.py",
        "python scripts/backtest_conformal_coverage.py",
        "python scripts/validate_conformal_policy.py --config configs/crpto_conformal_policy.yaml",
    ],
    "core_portfolio": [
        "python scripts/optimize_portfolio.py --config configs/crpto_optimization.yaml",
        "python scripts/optimize_portfolio_tradeoff.py --config configs/crpto_optimization.yaml",
        "python scripts/simulate_ab_test.py",
    ],
    "diagnostics_governance": [
        "python scripts/run_fairness_audit.py --config configs/crpto_fairness_policy.yaml",
        "python scripts/generate_governance_status.py",
        "python scripts/generate_mrm_report.py --config configs/crpto_mrm_policy.yaml",
    ],
    "publication_exports": [
        "python scripts/export_crpto_tables.py",
        "python scripts/analyze_crpto_evidence.py",
        "python scripts/build_crpto_journal_package.py",
        "python scripts/generate_crpto_figures.py --paper crpto",
        "python scripts/run_crpto_vs_spo_stability.py",
        "QUARTO_PYTHON=.venv/bin/python quarto render book --to html",
    ],
}
ORDER = list(STEPS)


def run_command(cmd: str, log_file: Path) -> None:
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"\n$ {cmd}\n")
        handle.flush()
        subprocess.run(
            cmd, cwd=ROOT, shell=True, check=True, stdout=handle, stderr=subprocess.STDOUT
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CRPTO standalone pipeline.")
    parser.add_argument(
        "--run-tag", default=f"crpto-e2e-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    )
    parser.add_argument("--from-step", choices=ORDER, default=ORDER[0])
    parser.add_argument("--until-step", choices=ORDER, default=ORDER[-1])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    start = ORDER.index(args.from_step)
    end = ORDER.index(args.until_step)
    if start > end:
        raise SystemExit("--from-step must come before --until-step")

    run_dir = LOG_ROOT / args.run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    status = {"run_tag": args.run_tag, "started_at_utc": datetime.now(UTC).isoformat(), "steps": {}}

    for step in ORDER[start : end + 1]:
        marker = run_dir / f"{step}.done"
        if args.resume and marker.exists():
            status["steps"][step] = "skipped_done"
            continue
        log_file = run_dir / f"{step}.log"
        status["steps"][step] = "running"
        (run_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        for cmd in STEPS[step]:
            run_command(cmd, log_file)
        marker.write_text(datetime.now(UTC).isoformat() + "\n", encoding="utf-8")
        status["steps"][step] = "completed"

    status["completed_at_utc"] = datetime.now(UTC).isoformat()
    (run_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
