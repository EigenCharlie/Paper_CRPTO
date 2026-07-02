"""Build a priority execution context for exact portfolio reranking.

The exact certificate remains full-universe: this script only changes the order
in which the frozen shortlist is evaluated and removes redundant seeds when the
evaluation universe is not sampled.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def _resolve(path_like: object) -> Path:
    path = Path(str(path_like))
    return path if path.is_absolute() else ROOT / path


def _reason(row: pd.Series, *, champion_return: float) -> str:
    bucket = str(row.get("shortlist_bucket", ""))
    realized = float(row.get("realized_total_return", 0.0))
    ab_pass = bool(row.get("ab_pass_all", False))
    if realized > champion_return and ab_pass and bucket == "forced_incumbent_neighbors":
        return "above_champion_forced_incumbent_region"
    if realized > champion_return and ab_pass:
        return "above_champion_ab_pass"
    if bucket == "forced_incumbent_neighbors":
        return "forced_incumbent_region"
    if bucket == "incumbent_region":
        return "incumbent_region"
    return "remaining_shortlist"


def _tier(row: pd.Series, *, champion_return: float) -> int:
    reason = _reason(row, champion_return=champion_return)
    return {
        "above_champion_forced_incumbent_region": 0,
        "above_champion_ab_pass": 1,
        "forced_incumbent_region": 2,
        "incumbent_region": 3,
        "remaining_shortlist": 4,
    }[reason]


def build_priority_context(
    *,
    context_path: Path,
    output_context_path: Path | None = None,
    champion_return: float,
) -> dict[str, Any]:
    context_path = context_path.resolve()
    context = json.loads(context_path.read_text(encoding="utf-8"))
    shortlist_path = _resolve(context["shortlist_path"])
    shortlist = pd.read_parquet(shortlist_path)
    if shortlist.empty:
        raise ValueError(f"Cannot prioritize empty shortlist: {shortlist_path}")

    prioritized = shortlist.copy()
    prioritized["exact_priority_reason"] = prioritized.apply(
        _reason,
        axis=1,
        champion_return=float(champion_return),
    )
    prioritized["exact_priority_tier"] = prioritized.apply(
        _tier,
        axis=1,
        champion_return=float(champion_return),
    )
    prioritized["exact_priority_return_surplus"] = pd.to_numeric(
        prioritized["realized_total_return"], errors="coerce"
    ).fillna(0.0) - float(champion_return)
    prioritized = prioritized.sort_values(
        by=[
            "exact_priority_tier",
            "realized_total_return",
            "candidate_rank",
        ],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    prioritized["exact_priority_order"] = np.arange(1, len(prioritized) + 1)

    priority_shortlist_path = shortlist_path.with_name(shortlist_path.stem + "_priority.parquet")
    prioritized.to_parquet(priority_shortlist_path, index=False)

    requested_random_states = list(context.get("exact_random_states", context["random_states"]))
    exact_max_candidates = int(context.get("exact_max_candidates", context["max_candidates"]))
    effective_random_states = list(requested_random_states)
    full_universe_seed_deduped = False
    if exact_max_candidates <= 0 and len(effective_random_states) > 1:
        effective_random_states = [int(effective_random_states[0])]
        full_universe_seed_deduped = True

    priority_context = dict(context)
    priority_context["shortlist_path"] = str(priority_shortlist_path)
    priority_context["shortlist_priority_source_path"] = str(shortlist_path)
    priority_context["exact_priority_context_source_path"] = str(context_path)
    priority_context["exact_priority_generated_at_utc"] = datetime.now(tz=UTC).isoformat()
    priority_context["exact_priority_champion_return"] = float(champion_return)
    priority_context["exact_priority_strategy"] = [
        "above_champion_forced_incumbent_region",
        "above_champion_ab_pass",
        "forced_incumbent_region",
        "incumbent_region",
        "remaining_shortlist",
    ]
    priority_context["requested_exact_random_states"] = requested_random_states
    priority_context["exact_random_states"] = effective_random_states
    priority_context["full_universe_seed_deduped"] = bool(full_universe_seed_deduped)
    priority_context.setdefault("selection_policy", {})
    priority_context["selection_policy"]["exact_execution_order"] = "claim_priority_return_first"
    priority_context["selection_policy"]["full_universe_seed_deduped"] = bool(
        full_universe_seed_deduped
    )

    if output_context_path is None:
        output_context_path = context_path.with_name(context_path.stem + "_priority.json")
    output_context_path = output_context_path.resolve()
    output_context_path.write_text(
        json.dumps(priority_context, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "context_path": str(output_context_path),
        "priority_shortlist_path": str(priority_shortlist_path),
        "n_shortlist": int(len(prioritized)),
        "n_above_champion": int(
            (prioritized["realized_total_return"] > float(champion_return)).sum()
        ),
        "requested_exact_random_states": requested_random_states,
        "effective_exact_random_states": effective_random_states,
        "full_universe_seed_deduped": bool(full_universe_seed_deduped),
        "top_candidates": prioritized[
            [
                "exact_priority_order",
                "candidate_rank",
                "exact_priority_reason",
                "risk_tolerance",
                "policy_mode",
                "gamma",
                "uncertainty_aversion",
                "realized_total_return",
            ]
        ]
        .head(12)
        .to_dict(orient="records"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-path", required=True)
    parser.add_argument("--output-context-path", default="")
    parser.add_argument("--champion-return", type=float, default=170_464.54)
    args = parser.parse_args()

    payload = build_priority_context(
        context_path=Path(args.context_path),
        output_context_path=Path(args.output_context_path) if args.output_context_path else None,
        champion_return=float(args.champion_return),
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
