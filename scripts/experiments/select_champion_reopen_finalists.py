"""Select CRPTO champion-reopen finalists after seed replay.

This script is read-only over experiment outputs. It combines the seed-42
feature-search result with seed-replay summaries, applies the promotion gates
from ``configs/experiments/champion_reopen.yaml``, and writes a ranked finalist
selection under the experiment report root.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/champion_reopen.yaml")
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail if any configured seed-replay summary is missing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_yaml(Path(args.config))
    run_tag = str(args.run_tag or config.get("run_tag", "champion-reopen-2026-06-19"))
    report_root = Path(config["output"]["report_dir"])
    selection = select_finalists(
        config=config,
        run_tag=run_tag,
        report_root=report_root,
        top_n=int(args.top_n),
        require_complete=bool(args.require_complete),
    )
    output_dir = report_root / run_tag / "finalist_selection"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "seed_replay_finalists.json").write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(selection["ranked_cases"]).to_csv(
        output_dir / "seed_replay_ranked_cases.csv", index=False
    )
    print(f"Wrote finalist selection: {output_dir / 'seed_replay_finalists.json'}")
    print("selected:", ", ".join(row["case_name"] for row in selection["selected_finalists"]))


def select_finalists(
    *,
    config: dict[str, Any],
    run_tag: str,
    report_root: Path,
    top_n: int,
    require_complete: bool,
) -> dict[str, Any]:
    champion = dict(config["champion_reopen"]["pd_promotion_gates"])
    replay_cases = list(config["champion_reopen"]["seed_replay_cases"])
    replay_seeds = list(
        config["champion_reopen"].get(
            "seed_replay_seeds", config.get("seeds", [42, 52, 62, 72, 82])
        )
    )
    expected_seeds = [42, *[int(seed) for seed in replay_seeds if int(seed) != 42]]
    rows, missing = _load_seed_rows(
        report_root=report_root, run_tag=run_tag, cases=replay_cases, seeds=expected_seeds
    )
    if require_complete and missing:
        raise SystemExit("Missing seed summaries: " + ", ".join(missing))
    ranked = _rank_cases(rows, champion=champion, expected_seed_count=len(expected_seeds))
    selected = _select_top_cases(ranked, top_n=top_n)
    return {
        "run_tag": run_tag,
        "expected_seeds": expected_seeds,
        "available_rows": len(rows),
        "missing": missing,
        "champion_metrics": {
            "auc_roc": champion["champion_auc"],
            "brier_score": champion["champion_brier"],
            "ece": champion["champion_ece"],
        },
        "gates": champion,
        "selected_finalists": selected,
        "ranked_cases": ranked,
    }


def _load_seed_rows(
    *,
    report_root: Path,
    run_tag: str,
    cases: list[str],
    seeds: list[int],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    feature_summary = (
        report_root
        / f"{run_tag}__feature_search"
        / "summary"
        / "seed_42"
        / "selected_feature_experiment_summary.json"
    )
    if feature_summary.exists():
        rows.extend(
            _rows_from_summary(
                feature_summary, allowed_cases=set(cases), source_stage="feature_search"
            )
        )
    else:
        missing.append(str(feature_summary))
    for seed in seeds:
        if int(seed) == 42:
            continue
        summary = (
            report_root
            / f"{run_tag}__seed_replay"
            / "summary"
            / f"seed_{int(seed)}"
            / "selected_feature_experiment_summary.json"
        )
        if summary.exists():
            rows.extend(
                _rows_from_summary(summary, allowed_cases=set(cases), source_stage="seed_replay")
            )
        else:
            missing.append(str(summary))
    return rows, missing


def _rows_from_summary(
    path: Path, *, allowed_cases: set[str], source_stage: str
) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in payload.get("results", []):
        case = str(item["case_name"])
        if case not in allowed_cases:
            continue
        metrics = dict(item["test_metrics"])
        rows.append(
            {
                "case_name": case,
                "seed": int(item["seed"]),
                "source_stage": source_stage,
                "n_model_features": int(item["n_model_features"]),
                "n_generated_features": int(item["n_generated_features"]),
                "auc_roc": float(metrics["auc_roc"]),
                "brier_score": float(metrics["brier_score"]),
                "ece": float(metrics["ece"]),
            }
        )
    return rows


def _rank_cases(
    rows: list[dict[str, Any]],
    *,
    champion: dict[str, Any],
    expected_seed_count: int,
) -> list[dict[str, Any]]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(row["case_name"], []).append(row)
    ranked: list[dict[str, Any]] = []
    for case, case_rows in sorted(by_case.items()):
        aucs = [row["auc_roc"] for row in case_rows]
        briers = [row["brier_score"] for row in case_rows]
        eces = [row["ece"] for row in case_rows]
        seeds = sorted({int(row["seed"]) for row in case_rows})
        mean_auc = mean(aucs)
        mean_brier = mean(briers)
        mean_ece = mean(eces)
        auc_std = pstdev(aucs) if len(aucs) > 1 else 0.0
        delta_auc = mean_auc - float(champion["champion_auc"])
        delta_brier = mean_brier - float(champion["champion_brier"])
        delta_ece = mean_ece - float(champion["champion_ece"])
        complete = len(seeds) >= expected_seed_count
        paper_facing = case in {"pool93", "catboost44"} or "business" in case
        gate_pass = bool(
            complete
            and delta_auc >= float(champion["min_auc_delta_mean"])
            and auc_std <= float(champion["max_auc_seed_std"])
            and delta_brier <= float(champion["max_brier_increase"])
            and delta_ece <= float(champion["max_ece_increase"])
        )
        score = (
            delta_auc
            - max(0.0, auc_std - float(champion["max_auc_seed_std"])) * 2.0
            - max(0.0, delta_brier) * 10.0
            - max(0.0, delta_ece) * 0.5
            + (0.00025 if paper_facing else 0.0)
        )
        ranked.append(
            {
                "case_name": case,
                "seed_count": len(seeds),
                "seeds": ",".join(str(seed) for seed in seeds),
                "complete": complete,
                "paper_facing": paper_facing,
                "gate_pass": gate_pass,
                "mean_auc_roc": mean_auc,
                "delta_auc_roc": delta_auc,
                "std_auc_roc": auc_std,
                "mean_brier_score": mean_brier,
                "delta_brier_score": delta_brier,
                "mean_ece": mean_ece,
                "delta_ece": delta_ece,
                "min_auc_roc": min(aucs),
                "max_auc_roc": max(aucs),
                "n_model_features": int(case_rows[0]["n_model_features"]),
                "n_generated_features": int(case_rows[0]["n_generated_features"]),
                "selection_score": score,
            }
        )
    ranked.sort(
        key=lambda row: (
            bool(row["gate_pass"]),
            float(row["selection_score"]),
            float(row["mean_auc_roc"]),
        ),
        reverse=True,
    )
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return ranked


def _select_top_cases(ranked: list[dict[str, Any]], *, top_n: int) -> list[dict[str, Any]]:
    if top_n <= 0:
        return []
    gate_pass = [row for row in ranked if row["gate_pass"]]
    selected = list(gate_pass[:top_n])
    if len(selected) < top_n:
        seen = {row["case_name"] for row in selected}
        for row in ranked:
            if row["case_name"] in seen:
                continue
            selected.append(row)
            seen.add(row["case_name"])
            if len(selected) >= top_n:
                break
    return selected


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected mapping config: {path}")
    return payload


if __name__ == "__main__":
    main()
