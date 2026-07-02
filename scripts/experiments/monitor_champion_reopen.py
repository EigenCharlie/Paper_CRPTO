"""Print a compact leaderboard for champion-reopen experiment outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", default="champion-reopen-2026-06-19")
    parser.add_argument("--root", default="models/experiments/champion_reopen")
    parser.add_argument("--top", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _collect_status_rows(Path(args.root), run_tag=str(args.run_tag))
    if not rows:
        print("No champion-reopen training status files found yet.")
        return
    rows.sort(
        key=lambda row: (
            float(row.get("auc_roc", float("-inf"))),
            -float(row.get("brier_score", float("inf"))),
            -float(row.get("ece", float("inf"))),
        ),
        reverse=True,
    )
    print(f"Champion-reopen leaderboard ({len(rows)} completed cases)")
    print("rank auc_roc  brier    ece      seed case run_tag")
    for idx, row in enumerate(rows[: int(args.top)], start=1):
        print(
            f"{idx:>4} "
            f"{float(row.get('auc_roc', 0.0)):.6f} "
            f"{float(row.get('brier_score', 0.0)):.6f} "
            f"{float(row.get('ece', 0.0)):.6f} "
            f"{int(row.get('seed', 0)):>5} "
            f"{row.get('case_name', '')} "
            f"{row.get('run_tag', '')}"
        )


def _collect_status_rows(root: Path, *, run_tag: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    patterns = [
        f"{run_tag}*/**/selected_feature_training_status.json",
        f"{run_tag}*/**/hpo_training_status.json",
    ]
    for pattern in patterns:
        for path in root.glob(pattern):
            payload = _read_json(path)
            metrics = dict(payload.get("test_metrics", {}) or {})
            rows.append(
                {
                    "path": str(path),
                    "run_tag": payload.get("run_tag"),
                    "case_name": payload.get("case_name"),
                    "seed": payload.get("seed"),
                    "n_model_features": payload.get("n_model_features"),
                    "auc_roc": metrics.get("auc_roc"),
                    "brier_score": metrics.get("brier_score"),
                    "ece": metrics.get("ece"),
                    "log_loss": metrics.get("log_loss"),
                    "pr_auc": metrics.get("pr_auc"),
                }
            )
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


if __name__ == "__main__":
    main()
