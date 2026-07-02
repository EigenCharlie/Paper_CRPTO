"""Orchestrate the CRPTO champion-reopen experiment waves.

The script is intentionally conservative: it writes command manifests and
runtime status under experiment-only roots, and only launches expensive work
when ``--execute`` is supplied.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.pipeline_runtime import atomic_write_json, write_runtime_status  # noqa: E402


@dataclass(frozen=True)
class ReopenCommand:
    """One resumable command in a champion-reopen stage."""

    name: str
    stage: str
    command: list[str]
    expected_output: str
    log_path: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/experiments/champion_reopen.yaml",
        help="Champion-reopen config.",
    )
    parser.add_argument("--run-tag", default=None, help="Override config run_tag.")
    parser.add_argument(
        "--stage",
        choices=["plan", "smoke", "feature_search", "seed_replay", "calibration", "all"],
        default="plan",
    )
    parser.add_argument("--execute", action="store_true", help="Run commands after writing manifest.")
    parser.add_argument("--resume", action="store_true", help="Skip commands whose expected output exists.")
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=None,
        help="Override smoke sample rows for the smoke stage.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config(Path(args.config))
    run_tag = str(args.run_tag or config.get("run_tag", "champion-reopen-2026-06-19"))
    started = time.perf_counter()
    commands = _build_commands(
        config=config,
        stage=str(args.stage),
        run_tag=run_tag,
        sample_rows_override=args.sample_rows,
    )
    manifest_path = _write_command_manifest(
        config=config,
        run_tag=run_tag,
        stage=str(args.stage),
        commands=commands,
        execute=bool(args.execute),
        resume=bool(args.resume),
    )
    status_path = _orchestration_status_path(config, run_tag=run_tag)
    write_runtime_status(
        "champion_reopen_orchestration",
        phase="manifest_written",
        state="running" if args.execute and commands else "planned",
        run_tag=run_tag,
        status_path=status_path,
        extra={
            "stage": str(args.stage),
            "execute": bool(args.execute),
            "resume": bool(args.resume),
            "command_count": len(commands),
            "manifest_path": str(manifest_path),
        },
    )
    if not args.execute:
        print(f"Wrote command manifest: {manifest_path}")
        return

    executed: list[dict[str, Any]] = []
    for item in commands:
        expected = Path(item.expected_output)
        if args.resume and expected.exists():
            executed.append({**asdict(item), "state": "skipped_existing_output"})
            continue
        log_path = Path(item.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log:
            log.write("$ " + " ".join(item.command) + "\n\n")
            log.flush()
            proc = subprocess.run(
                item.command,
                cwd=REPO_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        state = "completed" if proc.returncode == 0 else "failed"
        executed.append({**asdict(item), "state": state, "returncode": proc.returncode})
        write_runtime_status(
            "champion_reopen_orchestration",
            phase="command_complete",
            state="running" if proc.returncode == 0 else "failed",
            run_tag=run_tag,
            status_path=status_path,
            extra={
                "stage": str(args.stage),
                "latest_command": item.name,
                "latest_returncode": proc.returncode,
                "executed": executed,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

    write_runtime_status(
        "champion_reopen_orchestration",
        phase="complete",
        state="completed",
        run_tag=run_tag,
        status_path=status_path,
        extra={
            "stage": str(args.stage),
            "executed": executed,
            "elapsed_seconds": time.perf_counter() - started,
        },
    )
    print(f"Completed stage {args.stage}; manifest: {manifest_path}")


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise TypeError(f"Config must be a mapping: {path}")
    config.setdefault("champion_reopen", {})
    config.setdefault("output", {})
    return config


def _build_commands(
    *,
    config: Mapping[str, Any],
    stage: str,
    run_tag: str,
    sample_rows_override: int | None,
) -> list[ReopenCommand]:
    if stage == "plan":
        return []
    if stage == "all":
        stages = ["smoke", "feature_search", "seed_replay"]
        return [
            command
            for substage in stages
            for command in _build_commands(
                config=config,
                stage=substage,
                run_tag=run_tag,
                sample_rows_override=sample_rows_override,
            )
        ]
    if stage == "smoke":
        sample_rows = int(
            sample_rows_override
            if sample_rows_override is not None
            else config["champion_reopen"].get("smoke_sample_rows", 50000)
        )
        return [
            _feature_selection_command(
                config=config,
                stage=stage,
                run_tag=f"{run_tag}__smoke",
                seed=42,
                tabprep_seed=42,
                cases=config["champion_reopen"]["smoke_cases"],
                sample_rows=sample_rows,
                reason="Smoke test ranking, guardrails, calibration, and output isolation.",
            )
        ]
    if stage == "feature_search":
        return [
            _feature_selection_command(
                config=config,
                stage=stage,
                run_tag=f"{run_tag}__feature_search",
                seed=42,
                tabprep_seed=42,
                cases=config["champion_reopen"]["feature_search_cases"],
                sample_rows=0,
                reason="Full-data feature subset tournament on the canonical TabPrep space.",
            )
        ]
    if stage == "seed_replay":
        seed_replay_seeds = config["champion_reopen"].get("seed_replay_seeds", config.get("seeds", [42, 52, 62, 72, 82]))
        return [
            _feature_selection_command(
                config=config,
                stage=stage,
                run_tag=f"{run_tag}__seed_replay",
                seed=int(seed),
                tabprep_seed=42,
                cases=config["champion_reopen"]["seed_replay_cases"],
                sample_rows=0,
                reason="Replay selected subsets across CatBoost seeds with fixed TabPrep features.",
            )
            for seed in seed_replay_seeds
        ]
    if stage == "calibration":
        cases = config["champion_reopen"]["seed_replay_cases"]
        return [
            _feature_selection_command(
                config=config,
                stage=stage,
                run_tag=f"{run_tag}__calibration_{method}",
                seed=42,
                tabprep_seed=42,
                cases=cases,
                sample_rows=0,
                calibration_method=str(method),
                reason=f"Calibration tournament lane for {method}.",
            )
            for method in config.get("calibration", {}).get("candidates", [])
        ]
    raise ValueError(f"Unsupported stage: {stage}")


def _feature_selection_command(
    *,
    config: Mapping[str, Any],
    stage: str,
    run_tag: str,
    seed: int,
    tabprep_seed: int,
    cases: Sequence[str],
    sample_rows: int,
    reason: str,
    calibration_method: str | None = None,
) -> ReopenCommand:
    command = [
        sys.executable,
        "scripts/experiments/run_tabprep_feature_selection_catboost.py",
        "--config",
        "configs/experiments/champion_reopen.yaml",
        "--run-tag",
        run_tag,
        "--seed",
        str(seed),
        "--tabprep-seed",
        str(tabprep_seed),
        "--variant",
        "balanced_1500",
        "--selector-model",
        str(config["champion_reopen"]["selector_model"]),
        "--ranking-method",
        str(config["champion_reopen"].get("ranking_method", "pvc")),
        "--shap-rows",
        str(config["champion_reopen"].get("shap_rows", 30000)),
        "--cases",
        ",".join(cases),
    ]
    if sample_rows > 0:
        command.extend(["--sample-rows", str(sample_rows)])
    else:
        command.append("--full-data")
    if calibration_method:
        command.extend(["--calibration-method", calibration_method])
    summary = _summary_path(config, run_tag=run_tag, seed=seed)
    return ReopenCommand(
        name=f"{stage}:{run_tag}:seed_{seed}",
        stage=stage,
        command=command,
        expected_output=str(summary),
        log_path=str(_log_path(run_tag=run_tag, name=f"{stage}_seed_{seed}")),
        reason=reason,
    )


def _write_command_manifest(
    *,
    config: Mapping[str, Any],
    run_tag: str,
    stage: str,
    commands: Sequence[ReopenCommand],
    execute: bool,
    resume: bool,
) -> Path:
    root = Path(config["output"]["report_dir"]) / run_tag / "orchestration"
    payload = {
        "run_tag": run_tag,
        "stage": stage,
        "execute": bool(execute),
        "resume": bool(resume),
        "command_count": len(commands),
        "commands": [asdict(command) for command in commands],
        "monitor_commands": [
            f"tail -f reports/run_logs/champion_reopen/{run_tag}*/*.log",
            f"{sys.executable} scripts/experiments/monitor_champion_reopen.py --run-tag {run_tag}",
        ],
    }
    return atomic_write_json(root / "command_manifest.json", payload)


def _summary_path(config: Mapping[str, Any], *, run_tag: str, seed: int) -> Path:
    return (
        Path(config["output"]["report_dir"])
        / run_tag
        / "summary"
        / f"seed_{seed}"
        / "selected_feature_experiment_summary.json"
    )


def _orchestration_status_path(config: Mapping[str, Any], *, run_tag: str) -> Path:
    return Path(config["output"]["model_dir"]) / run_tag / "orchestration" / "runtime_status.json"


def _log_path(*, run_tag: str, name: str) -> Path:
    safe = name.replace(":", "_").replace("/", "_")
    return Path("reports/run_logs/champion_reopen") / run_tag / f"{safe}.log"


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items))


if __name__ == "__main__":
    main()
