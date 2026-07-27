from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = ROOT / "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3f.py"
RUNNER_PATH = ROOT / "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3f.py"
CONFIG_PATH = ROOT / "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f.yaml"
PROTOCOL_PATH = (
    ROOT / "docs/research/ijds_marginal_mean_score_outcome_gap_v3f_protocol_2026-07-26.md"
)
RUNTIME_TEMPLATE_PATH = (
    ROOT / "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3f_calibre_global.json"
)
LOCKED_V2_SCIENCE: dict[str, Any] = {
    "role": "primary_oot",
    "endpoint_cutoff": "2020-09-30",
    "charged_off_availability_lag_months": 6,
    "expected_candidates": 376890,
    "expected_resolved": 364814,
    "expected_unresolved": 12076,
    "expected_resolved_y0": 307842,
    "expected_resolved_y1": 56972,
    "issue_months": [
        "2016-04",
        "2016-05",
        "2016-06",
        "2016-07",
        "2016-08",
        "2016-09",
        "2016-10",
        "2016-11",
        "2016-12",
        "2017-01",
        "2017-02",
        "2017-03",
        "2017-04",
        "2017-05",
        "2017-06",
    ],
    "learners": [
        "catboost_platt",
        "numeric_logistic_platt",
        "catboost_monotonic_platt",
        "woe_scorecard_platform_platt",
        "woe_scorecard_borrower_platt",
    ],
    "score_columns": {
        "catboost_platt": "pd_catboost_platt",
        "numeric_logistic_platt": "pd_numeric_logistic_platt",
        "catboost_monotonic_platt": "pd_catboost_monotonic_platt",
        "woe_scorecard_platform_platt": "pd_woe_scorecard_platform_platt",
        "woe_scorecard_borrower_platt": "pd_woe_scorecard_borrower_platt",
    },
    "endpoint_reason_census": {
        "charged_off_by_reconstructed_cutoff": {
            "candidate_rows": 56972,
            "resolved_rows": 56972,
            "unresolved_rows": 0,
        },
        "fully_paid_by_reconstructed_cutoff": {
            "candidate_rows": 307842,
            "resolved_rows": 307842,
            "unresolved_rows": 0,
        },
        "nonterminal_or_unresolved_status": {
            "candidate_rows": 11551,
            "resolved_rows": 0,
            "unresolved_rows": 11551,
        },
        "terminal_after_reconstructed_cutoff": {
            "candidate_rows": 47,
            "resolved_rows": 0,
            "unresolved_rows": 47,
        },
        "terminal_availability_date_missing": {
            "candidate_rows": 478,
            "resolved_rows": 0,
            "unresolved_rows": 478,
        },
    },
}
CALIBRE_PROTOCOL_SENTINEL = {
    "database_path": None,
    "installation_uuid": "00000000-0000-4000-8000-000000000000",
}
LITERAL_PRE_SOURCE_ENV = "IJDS_V3F_RUN_LITERAL_PRE_SOURCE_INTEGRATION"
LITERAL_PRE_SOURCE_ARG = "--literal-pre-source-integration"
_LITERAL_GIT_EXECUTABLE = Path("C:/Program Files/Git/mingw64/bin/git.exe")
_LITERAL_CALIBRE_EXECUTABLE = "C:/Program Files/Calibre2/calibre-debug.exe"
_LITERAL_PROTOCOL_TAG = "protocol/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f"
_LITERAL_V3E_COMMIT = "daf79db716555d7399651468700fa04c2192d31b"
_LITERAL_RUNTIME_MANIFEST = (
    ROOT / "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f_runtime.json"
)
_LITERAL_CONFIG_DIR = (
    ROOT / ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f-config"
)
_LITERAL_CACHE_DIR = (
    ROOT / ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f-calibre-cache"
)
_LITERAL_PYCACHE_DIR = (
    ROOT / ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f-pycache"
)
_LITERAL_OUTPUT_ROOTS = (
    ROOT / "data/processed/experiments/ijds_audit/"
    "ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f",
    ROOT / "models/experiments/ijds_audit/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f",
)
_LITERAL_EXPECTED_DIFF_PATHS = tuple(
    sorted(
        (
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f.yaml",
            "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f_runtime.json",
            "configs/runtime/ijds_marginal_mean_score_outcome_gap_v3f_calibre_global.json",
            "docs/research/ijds_marginal_mean_score_outcome_gap_v3f_protocol_2026-07-26.md",
            "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3f.py",
            "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3f.py",
            "src/ijds_audit/marginal_mean_score_outcome_gap_v3f.py",
            "tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3f.py",
            "tests/test_ijds_audit/test_marginal_mean_score_outcome_gap_v3f.py",
        )
    )
)
_LITERAL_EXPECTED_LOCAL_MODULES = [
    "calibre.debug",
    "scripts",
    "scripts.experiments.bootstrap_ijds_marginal_mean_score_outcome_gap_v3f",
    "src",
    "src.data",
    "src.data.outcome_observability",
    "src.ijds_audit",
    "src.ijds_audit.marginal_mean_score_outcome_gap_v3f",
    "src.utils",
    "src.utils.artifact_descriptor",
]


def _literal_driver_require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _literal_driver_git_environment() -> dict[str, str]:
    retained = (
        "COMSPEC",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "PATH",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
        "PSModulePath",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERDOMAIN_ROAMINGPROFILE",
        "WINDIR",
    )
    environment = {key: os.environ[key] for key in retained if key in os.environ}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return environment


def _literal_driver_git(args: list[str], *, binary: bool = False) -> bytes | str:
    process = subprocess.run(
        [
            str(_LITERAL_GIT_EXECUTABLE),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.excludesFile=NUL",
            *args,
        ],
        cwd=ROOT,
        env=_literal_driver_git_environment(),
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=not binary,
    )
    if process.returncode != 0:
        stderr = process.stderr if isinstance(process.stderr, str) else process.stderr.decode()
        raise RuntimeError(f"Literal V3F Git command failed ({args}): {stderr.strip()}.")
    return process.stdout


def _literal_driver_tree(root: Path) -> tuple[tuple[str, str, int | None, str | None], ...]:
    _literal_driver_require(
        root.is_dir() and not root.is_symlink(),
        f"Literal V3F runtime root is invalid: {root}.",
    )
    rows: list[tuple[str, str, int | None, str | None]] = []
    for candidate in sorted(root.rglob("*"), key=lambda value: value.as_posix().casefold()):
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            rows.append((relative, "symlink", None, None))
        elif candidate.is_dir():
            rows.append((relative, "directory", None, None))
        elif candidate.is_file():
            payload = candidate.read_bytes()
            rows.append((relative, "file", len(payload), hashlib.sha256(payload).hexdigest()))
        else:
            rows.append((relative, "other", None, None))
    return tuple(rows)


def _literal_driver_state() -> dict[str, Any]:
    head = str(_literal_driver_git(["rev-parse", "HEAD"])).strip()
    tag = str(
        _literal_driver_git(
            [
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"refs/tags/{_LITERAL_PROTOCOL_TAG}^{{commit}}",
            ]
        )
    ).strip()
    status = _literal_driver_git(
        ["status", "--porcelain=v2", "-z", "--untracked-files=all"], binary=True
    )
    parent_line = str(_literal_driver_git(["rev-list", "--parents", "-n", "1", head])).strip()
    raw_diff = _literal_driver_git(
        ["diff", "--name-only", "-z", _LITERAL_V3E_COMMIT, head, "--"], binary=True
    )
    if not isinstance(raw_diff, bytes):
        raise TypeError("Literal V3F diff was not captured as bytes.")
    diff_paths = tuple(sorted(value.decode("utf-8") for value in raw_diff.split(b"\0") if value))
    return {
        "head": head,
        "tag": tag,
        "status": status,
        "parent_line": parent_line,
        "diff_paths": diff_paths,
        "config_tree": _literal_driver_tree(_LITERAL_CONFIG_DIR),
        "cache_tree": _literal_driver_tree(_LITERAL_CACHE_DIR),
        "pycache_tree": _literal_driver_tree(_LITERAL_PYCACHE_DIR),
        "output_roots_present": sorted(
            path.relative_to(ROOT).as_posix() for path in _LITERAL_OUTPUT_ROOTS if path.exists()
        ),
    }


def _literal_driver_child_environment(runtime_manifest: dict[str, Any]) -> dict[str, str]:
    bootstrap = runtime_manifest["bootstrap"]
    forbidden = {str(value).upper() for value in bootstrap["forbidden_environment"]}
    forbidden.update(str(value).upper() for value in bootstrap["forbidden_environment_names"])
    prefixes = tuple(str(value).upper() for value in bootstrap["forbidden_environment_prefixes"])
    environment = dict(os.environ)
    for name in list(environment):
        upper = name.upper()
        if upper in forbidden or any(upper.startswith(prefix) for prefix in prefixes):
            environment.pop(name)
    environment["CALIBRE_CONFIG_DIRECTORY"] = str(_LITERAL_CONFIG_DIR.resolve())
    environment["CALIBRE_CACHE_DIRECTORY"] = str(_LITERAL_CACHE_DIR.resolve())
    return environment


def _run_literal_pre_source_driver() -> dict[str, Any]:
    _literal_driver_require(Path.cwd().resolve() == ROOT.resolve(), "Literal V3F cwd changed.")
    _literal_driver_require(
        Path(__file__).resolve()
        == (ROOT / "tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3f.py"),
        "Literal V3F driver path changed.",
    )
    before = _literal_driver_state()
    _literal_driver_require(before["head"] == before["tag"], "Literal V3F HEAD/tag mismatch.")
    _literal_driver_require(before["status"] == b"", "Literal V3F worktree is not clean.")
    _literal_driver_require(
        before["parent_line"].split() == [before["head"], _LITERAL_V3E_COMMIT],
        "Literal V3F protocol commit is not the direct V3E child.",
    )
    _literal_driver_require(
        before["diff_paths"] == _LITERAL_EXPECTED_DIFF_PATHS,
        "Literal V3F protocol diff is not exactly nine paths.",
    )
    expected_config_tree = (
        ("caches", "directory", None, None),
        (
            "global.py.json",
            "file",
            91,
            "7e8c7cdace709da838ca523f61bab5f7919d1973fb086938d045231e7195ae98",
        ),
        ("plugins", "directory", None, None),
    )
    _literal_driver_require(
        before["config_tree"] == expected_config_tree,
        "Literal V3F sentinel/config state changed.",
    )
    _literal_driver_require(before["cache_tree"] == (), "Literal V3F cache is not empty.")
    _literal_driver_require(before["pycache_tree"] == (), "Literal V3F pycache is not empty.")
    _literal_driver_require(
        before["output_roots_present"] == [], "Literal V3F output root already exists."
    )
    runtime_manifest = json.loads(_LITERAL_RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    _literal_driver_require(
        runtime_manifest.get("schema_version") == "2026-07-26.3f-runtime-1",
        "Literal V3F runtime manifest changed.",
    )
    command = [
        _LITERAL_CALIBRE_EXECUTABLE,
        "-e",
        "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3f.py",
        "--",
        "--phase",
        "pre-source-only",
        "--config",
        "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f.yaml",
    ]
    process = subprocess.run(
        command,
        cwd=ROOT,
        env=_literal_driver_child_environment(runtime_manifest),
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=240,
    )
    _literal_driver_require(
        process.returncode == 0,
        f"Literal V3F child failed: stdout={process.stdout!r}, stderr={process.stderr!r}",
    )
    _literal_driver_require(process.stderr.strip() == "", "Literal V3F child emitted stderr.")
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    _literal_driver_require(len(lines) == 1, "Literal V3F child did not emit exactly one line.")
    receipt = json.loads(lines[0])
    expected_receipt = {
        "status": "complete_pre_source_authority_snapshot_attestation",
        "phase": "pre-source-only",
        "protocol_commit": before["head"],
        "head_tag": _LITERAL_PROTOCOL_TAG,
        "authority_files": 25,
        "authority_snapshot_files": 25,
        "git_bound_source_checks_complete": True,
        "loaded_local_modules_exact": True,
        "next_compute_operation": "_load_scientific_sources",
        "output_preflight_complete": True,
        "runtime_observation_complete": True,
        "terminal_fixed_point_verified": True,
        "terminal_revalidation_passes": 3,
        "terminal_revalidated": True,
    }
    for key, expected in expected_receipt.items():
        _literal_driver_require(
            receipt.get(key) == expected,
            f"Literal V3F child receipt changed on {key}.",
        )
    priming_paths = receipt.get("terminal_priming_mismatch_paths")
    priming_count = receipt.get("terminal_priming_mismatch_count")
    _literal_driver_require(
        isinstance(priming_paths, list)
        and isinstance(priming_count, int)
        and priming_count == len(priming_paths),
        "Literal V3F child omitted bounded terminal priming diagnostics.",
    )
    _literal_driver_require(
        receipt.get("loaded_local_modules") == _LITERAL_EXPECTED_LOCAL_MODULES,
        "Literal V3F child local-module census changed.",
    )
    after = _literal_driver_state()
    _literal_driver_require(after == before, "Literal V3F child mutated protected state.")
    return {
        "status": "complete_literal_pre_source_regression",
        "protocol_commit": before["head"],
        "child_status": receipt["status"],
        "authority_files": receipt["authority_files"],
        "authority_snapshot_files": receipt["authority_snapshot_files"],
        "loaded_local_modules": receipt["loaded_local_modules"],
        "next_compute_operation": receipt["next_compute_operation"],
        "terminal_fixed_point_verified": receipt["terminal_fixed_point_verified"],
        "terminal_priming_mismatch_count": priming_count,
        "terminal_priming_mismatch_paths": priming_paths,
        "terminal_revalidation_passes": receipt["terminal_revalidation_passes"],
        "state_unchanged": True,
        "source_data_opened": False,
        "outcomes_reconstructed": False,
        "outputs_created": False,
    }


if __name__ == "__main__":
    _literal_driver_require(
        sys.argv[1:] == [LITERAL_PRE_SOURCE_ARG],
        f"Literal V3F driver accepts only {LITERAL_PRE_SOURCE_ARG}.",
    )
    print(json.dumps(_run_literal_pre_source_driver(), ensure_ascii=False, sort_keys=True))
    raise SystemExit(0)


import pandas as pd  # noqa: E402
import pytest  # noqa: E402
import yaml  # noqa: E402


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("marginal_gap_v3f_runner_test", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import the V3F runner for tests.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bootstrap() -> ModuleType:
    spec = importlib.util.spec_from_file_location("marginal_gap_v3f_bootstrap_test", BOOTSTRAP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import the V3F bootstrap for tests.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _config() -> dict[str, Any]:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("V3F test config is not a mapping.")
    return payload


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_git(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "v3f-test@example.invalid")
    _git(repo, "config", "user.name", "V3F Test")


def _runtime_tree(root: Path) -> tuple[tuple[str, str, int | None, str | None], ...]:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"Literal V3F runtime root is invalid: {root}.")
    rows: list[tuple[str, str, int | None, str | None]] = []
    for candidate in sorted(root.rglob("*"), key=lambda value: value.as_posix().casefold()):
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            rows.append((relative, "symlink", None, None))
        elif candidate.is_dir():
            rows.append((relative, "directory", None, None))
        elif candidate.is_file():
            payload = candidate.read_bytes()
            rows.append((relative, "file", len(payload), hashlib.sha256(payload).hexdigest()))
        else:
            rows.append((relative, "other", None, None))
    return tuple(rows)


def _literal_pre_source_state(runner: ModuleType, config: dict[str, Any]) -> dict[str, Any]:
    config_dir = (ROOT / str(config["execution"]["calibre_config_directory"])).resolve()
    cache_dir = (ROOT / str(config["execution"]["calibre_cache_directory"])).resolve()
    pycache_dir = (
        ROOT / ".runtime_calibre/ijds-marginal-mean-score-outcome-gap-2026-07-26-v3f-pycache"
    ).resolve()
    data_dir, model_dir, targets = runner.output_targets(config, repo_root=ROOT)
    status = runner._git(
        ["status", "--porcelain=v2", "-z", "--untracked-files=all"],
        repo_root=ROOT,
        binary=True,
    )
    if not isinstance(status, bytes):
        raise TypeError("Literal V3F Git status was not captured as bytes.")
    return {
        "head": str(runner._git(["rev-parse", "HEAD"], repo_root=ROOT)).strip(),
        "tag": runner._resolve_strict_tag(ROOT, runner.PROTOCOL_TAG),
        "status": status,
        "config_tree": _runtime_tree(config_dir),
        "cache_tree": _runtime_tree(cache_dir),
        "pycache_tree": _runtime_tree(pycache_dir),
        "output_paths_present": sorted(
            path.relative_to(ROOT).as_posix()
            for path in (data_dir, model_dir, *targets.values())
            if path.exists()
        ),
    }


def test_v3f_config_preserves_v2_science_and_quarantines_v2_outputs() -> None:
    runner = _runner()
    config = runner._load_config(CONFIG_PATH)
    for key, expected in LOCKED_V2_SCIENCE.items():
        _require(config["design"][key] == expected, f"V3F changed locked science: {key}")
    _require(config["prior_lineage"]["v2_outputs_are_inputs"] is False, "V2 output import enabled")
    _require(
        config["prior_lineage"]["v3_protocol_commit"] == "934cdb2f2a9418625eddf0f9bc4cb771d2654696",
        "aborted V3 parent commit changed",
    )
    _require(
        config["prior_lineage"]["v3_status"] == "aborted_precompute_runtime_path_not_git_ignored",
        "aborted V3 reason changed",
    )
    _require(config["prior_lineage"]["v3_outcomes_read"] is False, "V3 read outcomes")
    _require(config["prior_lineage"]["v3_outputs_exist"] is False, "V3 outputs appeared")
    _require(config["prior_lineage"]["v3_outputs_are_inputs"] is False, "V3 output import enabled")
    _require(
        config["prior_lineage"]["v3a_protocol_commit"]
        == "88f71852db9d740e54d290e378a070f0a43b8541",
        "aborted V3A parent commit changed",
    )
    _require(
        config["prior_lineage"]["v3a_status"]
        == "aborted_pre_science_calibre_e_entrypoint_sys_path_mismatch",
        "aborted V3A reason changed",
    )
    _require(config["prior_lineage"]["v3a_outcomes_read"] is False, "V3A read outcomes")
    _require(config["prior_lineage"]["v3a_outputs_exist"] is False, "V3A outputs appeared")
    _require(
        config["prior_lineage"]["v3a_outputs_are_inputs"] is False,
        "V3A output import enabled",
    )
    _require(config["prior_lineage"]["v3b_outcomes_read"] is False, "V3B read outcomes")
    _require(config["prior_lineage"]["v3b_outputs_exist"] is False, "V3B outputs appeared")
    _require(
        config["prior_lineage"]["v3b_outputs_are_inputs"] is False,
        "V3B output import enabled",
    )
    _require(
        config["prior_lineage"]["v3c_protocol_commit"]
        == "d3ebcdd96087e1419a73961c947fea6e85c8a0e9",
        "aborted V3C parent commit changed",
    )
    _require(
        config["prior_lineage"]["v3c_status"]
        == "aborted_pre_outcome_runner_authority_census_handoff_mismatch",
        "aborted V3C reason changed",
    )
    _require(
        config["prior_lineage"]["v3c_scientific_modules_imported"] is True,
        "V3C scientific import boundary changed",
    )
    _require(config["prior_lineage"]["v3c_config_read"] is False, "V3C read config")
    _require(
        config["prior_lineage"]["v3c_source_data_read"] is False,
        "V3C read source data",
    )
    _require(config["prior_lineage"]["v3c_outcomes_read"] is False, "V3C read outcomes")
    _require(config["prior_lineage"]["v3c_outputs_exist"] is False, "V3C outputs appeared")
    _require(
        config["prior_lineage"]["v3c_outputs_are_inputs"] is False,
        "V3C output import enabled",
    )
    _require(
        config["prior_lineage"]["v3d_protocol_commit"]
        == "b51e0fbc25a941d9ea3b1e68c6c7ba5823b33ba5",
        "aborted V3D parent commit changed",
    )
    _require(
        config["prior_lineage"]["v3d_status"] == "aborted_pre_source_authority_config_duplicate",
        "aborted V3D reason changed",
    )
    _require(
        config["prior_lineage"]["v3d_scientific_modules_imported"] is True,
        "V3D scientific import boundary changed",
    )
    _require(config["prior_lineage"]["v3d_config_read"] is True, "V3D did not read config")
    _require(
        config["prior_lineage"]["v3d_git_bound_source_checks_started"] is False,
        "V3D started Git-bound source checks",
    )
    _require(
        config["prior_lineage"]["v3d_source_data_read"] is False,
        "V3D read source data",
    )
    _require(config["prior_lineage"]["v3d_outcomes_read"] is False, "V3D read outcomes")
    _require(config["prior_lineage"]["v3d_outputs_exist"] is False, "V3D outputs appeared")
    _require(
        config["prior_lineage"]["v3d_outputs_are_inputs"] is False,
        "V3D output import enabled",
    )
    _require(
        config["prior_lineage"]["v3e_protocol_commit"]
        == "daf79db716555d7399651468700fa04c2192d31b",
        "aborted V3E parent commit changed",
    )
    _require(
        config["prior_lineage"]["v3e_status"]
        == "aborted_terminal_authenticated_context_mismatch",
        "aborted V3E reason changed",
    )
    _require(
        config["prior_lineage"]["v3e_source_data_read"] is True,
        "V3E source-read boundary changed",
    )
    _require(
        config["prior_lineage"]["v3e_outcomes_reconstructed"] is True,
        "V3E outcome reconstruction was hidden",
    )
    _require(
        config["prior_lineage"]["v3e_terminal_validator_passed"] is False,
        "invalid V3E terminal validation was promoted",
    )
    _require(
        config["prior_lineage"]["v3e_outputs_are_inputs"] is False,
        "V3E failed outputs became V3F inputs",
    )
    _require(
        len(config["prior_lineage"]["v3e_output_descriptors"]) == 6,
        "V3E aborted six-file descriptor census changed",
    )
    _require(
        config["scientific_contract"]["result_sign_is_stop_condition"] is False,
        "sign-based stop returned",
    )
    _require(
        config["scientific_contract"]["reported_interval_is_identified_set_hull"] is True,
        "finite-grid hull boundary missing",
    )
    _require(
        config["scientific_contract"]["joint_exact_identified_set"]
        == "shared_completion_finite_grid_not_cartesian_product",
        "joint five-learner set reverted to an invalid Cartesian product",
    )
    artifact = config["output"]["artifact_registration"]
    _require(artifact["dvc_tracked"] is False, "tiny aggregate outputs reverted to new DVC")
    _require(len(artifact["expected_paths"]) == 6, "Git-native six-file census changed")


@pytest.mark.parametrize(
    ("family", "field", "replacement"),
    [
        ("scientific_contract", "formula_upper", "mean_score"),
        ("reporting_contract", "causal_or_prospective_interpretation", True),
        ("stop_rules", "stop_on_endpoint_reason_or_total_drift", False),
        ("prior_lineage", "v2_outputs_are_inputs", True),
        ("prior_lineage", "v3a_outcomes_read", True),
        ("prior_lineage", "v3b_outcomes_read", True),
        ("prior_lineage", "v3c_source_data_read", True),
        ("prior_lineage", "v3d_source_data_read", True),
        ("prior_lineage", "v3e_outputs_are_inputs", True),
        ("source_identity", "raw_rows", 1),
    ],
)
def test_config_exact_contract_rejects_semantic_field_drift(
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    field: str,
    replacement: Any,
) -> None:
    runner = _runner()
    payload = _config()
    payload[family][field] = replacement
    monkeypatch.setattr(
        runner,
        "_SEALED_AUTHORITY_BYTES",
        {runner.DEFAULT_CONFIG_PATH: yaml.safe_dump(payload, sort_keys=False).encode("utf-8")},
    )
    with pytest.raises(RuntimeError, match="changed"):
        runner._load_config(CONFIG_PATH)


def test_v3f_ast_closure_is_exact_and_contains_no_assert_statements() -> None:
    runner = _runner()
    bootstrap = _bootstrap()
    derived = runner.derive_local_python_closure(repo_root=ROOT)
    expected = tuple(sorted(runner.TRANSITIVE_PYTHON_PATHS, key=lambda value: value.as_posix()))
    _require(derived == expected, f"AST closure mismatch: {derived} != {expected}")
    runner._require_no_assert_statements(derived, repo_root=ROOT)
    bootstrap_authority = {
        bootstrap.BOOTSTRAP_PATH,
        *bootstrap.EXPECTED_SCIENTIFIC_CLOSURE,
        *bootstrap.NONPYTHON_AUTHORITY,
    }
    runner_authority = {
        *runner.BOOTSTRAP_PYTHON_PATHS,
        *runner.TRANSITIVE_PYTHON_PATHS,
        *runner.NONPYTHON_AUTHORITY_PATHS,
    }
    _require(
        bootstrap_authority == runner_authority,
        f"bootstrap/runner authority handoff mismatch: {bootstrap_authority ^ runner_authority}",
    )
    _require(len(runner_authority) == 25, "runner authority census is not exactly 25 paths")
    _require(
        len(runner.NONPYTHON_AUTHORITY_PATHS) == len(set(runner.NONPYTHON_AUTHORITY_PATHS)),
        "runner non-Python authority census contains a duplicate",
    )
    _require(
        runner.NONPYTHON_AUTHORITY_PATHS.count(runner.DEFAULT_CONFIG_PATH) == 1,
        "sealed config is not present exactly once in non-Python authority",
    )
    _require(
        runner.DEFAULT_CONFIG_PATH in runner_authority,
        "sealed config is absent from the runner authority census",
    )
    _require(Path(".gitignore") in runner.NONPYTHON_AUTHORITY_PATHS, ".gitignore is unsealed")
    _require(
        Path(".gitattributes") in runner.NONPYTHON_AUTHORITY_PATHS,
        ".gitattributes is unsealed",
    )
    _require(
        Path(".gitignore") in _bootstrap().NONPYTHON_AUTHORITY,
        ".gitignore is absent from bootstrap authority",
    )
    _require(
        Path(".gitattributes") in _bootstrap().NONPYTHON_AUTHORITY,
        ".gitattributes is absent from bootstrap authority",
    )
    _require(
        ".runtime_calibre/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines(),
        "canonical runtime paths are not Git-ignored",
    )
    _require(
        ".python-version text eol=lf"
        in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines(),
        ".python-version is not pinned to LF checkout bytes",
    )
    _require(
        (ROOT / ".python-version").read_bytes() == b"3.11\n",
        ".python-version checkout bytes differ from its Git blob",
    )


def test_bootstrap_import_adds_no_scientific_modules_and_direct_runner_is_rejected() -> None:
    scientific_prefixes = (
        "dateutil",
        "numpy",
        "pandas",
        "pyarrow",
        "scripts",
        "six",
        "src",
        "tzdata",
        "yaml",
    )
    before = set(sys.modules)
    bootstrap = _bootstrap()
    newly_loaded = set(sys.modules).difference(before)
    leaked = sorted(
        name
        for name in newly_loaded
        if any(name == prefix or name.startswith(prefix + ".") for prefix in scientific_prefixes)
    )
    _require(not leaked, f"bootstrap import loaded scientific modules: {leaked}")
    _require(
        bootstrap.derive_local_python_closure(repo_root=ROOT)
        == tuple(sorted(bootstrap.EXPECTED_SCIENTIFIC_CLOSURE, key=lambda path: path.as_posix())),
        "bootstrap closure omitted an initializer or relative import",
    )
    runner = _runner()
    if hasattr(runner, "_IJDS_V3F_BOOTSTRAP_ATTESTATION"):
        delattr(runner, "_IJDS_V3F_BOOTSTRAP_ATTESTATION")
    with pytest.raises(RuntimeError, match="without the authenticated bootstrap"):
        runner._require_bootstrap_attestation(phase="compute")


def test_scientific_module_census_catches_scripts_and_runner_aliases() -> None:
    bootstrap = _bootstrap()
    scripts_namespace = ModuleType("scripts.experiments")
    disguised_runner = ModuleType("innocuous_alias")
    disguised_runner.__file__ = str(ROOT / bootstrap.RUNNER_PATH)
    census = bootstrap._scientific_module_census(
        {
            "scripts.experiments": scripts_namespace,
            "innocuous_alias": disguised_runner,
            "unrelated_stdlib": ModuleType("unrelated_stdlib"),
        },
        repo_root=ROOT,
    )
    _require(
        census == ["innocuous_alias", "scripts.experiments"],
        f"scientific-module census missed a runner alias: {census}",
    )


def test_sealed_importer_resolves_namespace_and_blocks_local_disk_fallback(
    tmp_path: Path,
) -> None:
    bootstrap = _bootstrap()
    (tmp_path / "scripts/experiments").mkdir(parents=True)
    (tmp_path / "scripts/experiments/unsealed.py").write_text("VALUE = 'disk'\n", encoding="utf-8")
    sources = {
        Path("scripts/__init__.py"): b"PACKAGE = 'sealed'\n",
        Path("scripts/experiments/bootstrap_test.py"): b"VALUE = 'sealed'\n",
    }
    saved_modules = {
        name: module for name, module in sys.modules.items() if name.startswith("scripts")
    }
    for name in list(saved_modules):
        sys.modules.pop(name, None)
    finder = bootstrap._install_sealed_importer(sources, repo_root=tmp_path)
    try:
        module = importlib.import_module("scripts.experiments.bootstrap_test")
        _require(module.VALUE == "sealed", "sealed namespace import used disk bytes")
        namespace = sys.modules["scripts.experiments"]
        _require(
            namespace.__spec__ is not None and namespace.__spec__.origin == "v3f-sealed-namespace",
            "intermediate scripts.experiments namespace was not sealed",
        )
        with pytest.raises(ImportError, match="escaped the sealed V3F census"):
            importlib.import_module("scripts.experiments.unsealed")
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        for name in [value for value in sys.modules if value.startswith("scripts")]:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)


def test_protocol_commands_and_authorized_argv_require_the_bootstrap() -> None:
    config = _config()
    runner = _runner()
    runtime_manifest = json.loads(
        (
            ROOT
            / "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f_runtime.json"
        ).read_text(encoding="utf-8")
    )
    _require(
        runtime_manifest["bootstrap"]["preimport_sys_path"] == ["scripts/experiments"],
        "Calibre -e preimport path is not pinned exactly",
    )
    bootstrap_relative = "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3f.py"
    carrier = runtime_manifest["bootstrap"]["calibre_entrypoint_carrier"]
    _require(carrier["module_key"] == "calibre.debug", "Calibre carrier key changed")
    _require(carrier["aliases"] == ["calibre.debug"], "carrier alias contract changed")
    _require(carrier["module_name"] == "__main__", "Calibre carrier name changed")
    _require(carrier["bootstrap_path"] == bootstrap_relative, "carrier path is unbound")
    _require(
        carrier["loader_module"] == "bypy_importer"
        and carrier["loader_class"] == "FrozenByteCodeLoader",
        "Calibre carrier loader changed",
    )
    _require(carrier["carrier_is_executing_globals"] is True, "carrier globals unbound")
    _require(
        tuple(map(Path, config["execution"]["handoff_import_paths"]))
        == runner.HANDOFF_IMPORTED_PYTHON_PATHS,
        "handoff eager-import census changed",
    )
    runner_relative = "scripts/experiments/run_ijds_marginal_mean_score_outcome_gap_v3f.py"
    for phase in (
        "attest-only",
        "handoff-only",
        "pre-source-only",
        "compute",
        "verify-artifact",
    ):
        argv = config["execution"]["authorized_orig_argv"][phase]
        _require(argv[2] == bootstrap_relative, f"{phase} bypasses the authenticated bootstrap")
        _require(runner_relative not in argv, f"{phase} directly launches the scientific runner")
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    _require(
        protocol.count(f"-e {bootstrap_relative}") == 5,
        "protocol does not contain exactly five canonical bootstrap invocations",
    )
    _require(
        protocol.index("--phase attest-only")
        < protocol.index("--phase handoff-only")
        < protocol.index("--phase pre-source-only")
        < protocol.index("--phase compute"),
        "entrypoint, handoff, and pre-source attestations are not ordered before compute",
    )
    _require(f"-e {runner_relative}" not in protocol, "protocol still documents a bootstrap bypass")


def test_literal_regression_driver_exits_before_undeclared_test_imports() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    guard = source.index('if __name__ == "__main__":')
    _require(guard < source.index("import pandas as pd"), "literal driver imports pandas")
    _require(guard < source.index("import pytest"), "literal driver imports pytest")
    _require(guard < source.index("import yaml"), "literal driver imports PyYAML")
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    literal_path = "tests/test_experiments/test_ijds_marginal_mean_score_outcome_gap_v3f.py"
    _require(
        protocol.count(f"-e {literal_path} --") == 1,
        "protocol does not contain exactly one stdlib literal-regression invocation",
    )
    _require(
        protocol.index(f"-e {literal_path} --")
        < protocol.index("--literal-pre-source-integration"),
        "protocol literal-regression argument precedes no driver invocation",
    )


def test_attest_only_returns_before_scientific_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap()
    printed: list[str] = []
    fake_attestation = {
        "schema_version": "2026-07-26.3f-bootstrap-1",
        "phase": "attest-only",
        "protocol_commit": "a" * 40,
        "head_tag": bootstrap.PROTOCOL_TAG,
        "authority": {"source_files": {f"path-{index}": {} for index in range(25)}},
        "calibre_config": {
            "global": {
                "path": ".runtime_calibre/config/global.py.json",
                "bytes": 91,
                "sha256": "7e8c7cdace709da838ca523f61bab5f7919d1973fb086938d045231e7195ae98",
            }
        },
    }
    monkeypatch.setattr(
        bootstrap,
        "build_bootstrap_attestation",
        lambda **_kwargs: fake_attestation,
    )
    monkeypatch.setattr(
        bootstrap,
        "revalidate_attest_only_entrypoint",
        lambda *_args, **_kwargs: {
            "module_origins": {
                "calibre_entrypoint_carrier": {
                    "module_key": "calibre.debug",
                    "aliases": ["calibre.debug"],
                    "carrier_is_executing_globals": True,
                    "bootstrap_sha256": "b" * 64,
                }
            },
            "scientific_modules": [],
        },
    )
    monkeypatch.setattr("builtins.print", lambda value: printed.append(str(value)))
    bootstrap.main(
        [
            "--phase",
            "attest-only",
            "--config",
            bootstrap.CONFIG_PATH.as_posix(),
        ]
    )
    _require(len(printed) == 1, "attest-only did not emit exactly one receipt")
    receipt = json.loads(printed[0])
    _require(
        receipt["status"] == "complete_pre_science_entrypoint_attestation",
        "attest-only receipt status changed",
    )
    _require(receipt["authority_files"] == 25, "attest-only authority count changed")
    _require(receipt["scientific_modules_loaded"] is False, "attest-only entered science")
    _require(receipt["scientific_module_census"] == [], "measured science census missing")
    _require(
        receipt["calibre_entrypoint_carrier"]["carrier_is_executing_globals"] is True,
        "attest-only receipt omitted the measured carrier",
    )


def test_handoff_only_prints_one_pre_outcome_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    printed: list[str] = []
    expected = {
        "status": "complete_pre_outcome_runner_handoff_attestation",
        "phase": "handoff-only",
        "authority_files": 25,
        "config_loaded_from_sealed_bytes": True,
        "loaded_local_modules_exact": True,
        "output_targets_absent": True,
        "terminal_priming_mismatch_count": 0,
        "terminal_priming_mismatch_paths": [],
        "terminal_fixed_point_verified": True,
        "terminal_revalidation_passes": 3,
        "terminal_revalidated": True,
    }
    monkeypatch.setattr(runner, "run_handoff_only", lambda **_kwargs: expected)
    monkeypatch.setattr("builtins.print", lambda value: printed.append(str(value)))
    runner.main(
        [
            "--phase",
            "handoff-only",
            "--config",
            runner.DEFAULT_CONFIG_PATH.as_posix(),
        ]
    )
    _require(len(printed) == 1, "handoff-only did not emit exactly one receipt")
    _require(json.loads(printed[0]) == expected, "handoff-only receipt changed")


def test_pre_source_only_prints_one_authority_snapshot_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    printed: list[str] = []
    expected = {
        "status": "complete_pre_source_authority_snapshot_attestation",
        "phase": "pre-source-only",
        "authority_files": 25,
        "authority_snapshot_files": 25,
        "git_bound_source_checks_complete": True,
        "loaded_local_modules_exact": True,
        "next_compute_operation": "_load_scientific_sources",
        "output_preflight_complete": True,
        "runtime_observation_complete": True,
        "terminal_priming_mismatch_count": 0,
        "terminal_priming_mismatch_paths": [],
        "terminal_fixed_point_verified": True,
        "terminal_revalidation_passes": 3,
        "terminal_revalidated": True,
    }
    monkeypatch.setattr(runner, "run_pre_source_only", lambda **_kwargs: expected)
    monkeypatch.setattr("builtins.print", lambda value: printed.append(str(value)))
    runner.main(
        [
            "--phase",
            "pre-source-only",
            "--config",
            runner.DEFAULT_CONFIG_PATH.as_posix(),
        ]
    )
    _require(len(printed) == 1, "pre-source-only did not emit exactly one receipt")
    _require(json.loads(printed[0]) == expected, "pre-source-only receipt changed")


def test_pre_source_phase_is_exact_compute_prefix_before_first_source_access() -> None:
    runner_tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in runner_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def calls(function_name: str) -> list[str]:
        function = functions[function_name]
        return [
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]

    compute_calls = calls("run_compute")
    _require(
        compute_calls.index("_authority_snapshot")
        < compute_calls.index("_preflight_outputs")
        < compute_calls.index("_load_scientific_sources"),
        "compute does not execute authority snapshot and output preflight before source access",
    )
    pre_source_calls = calls("run_pre_source_only")
    _require("_authority_snapshot" in pre_source_calls, "pre-source omitted authority snapshot")
    _require("_preflight_outputs" in pre_source_calls, "pre-source omitted output preflight")
    _require(
        "_load_scientific_sources" not in pre_source_calls,
        "pre-source crossed the first scientific-source access boundary",
    )


def test_compute_reauthenticates_sources_and_context_after_receipt_before_seal() -> None:
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_source)
    functions = {
        node.name: node
        for node in runner_tree.body
        if isinstance(node, ast.FunctionDef)
    }
    write_function = functions["_write_compute_outputs"]

    def target_names(target: ast.expr) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            return {name for item in target.elts for name in target_names(item)}
        return set()

    expected_assignments = {
        "authenticated_before_receipt",
        "receipt",
        "receipt_path",
        "final_source_seal",
        "final_authority",
        "authenticated_before_seal",
        "seal",
        "seal_path",
    }
    assignment_lines: dict[str, int] = {}
    for node in ast.walk(write_function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            for name in target_names(target) & expected_assignments:
                assignment_lines[name] = node.lineno
    validation_lines = [
        node.lineno
        for node in ast.walk(write_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "validate_execution_seal"
    ]
    _require(
        set(assignment_lines) == expected_assignments,
        "compute writer no longer exposes every post-receipt authentication stage",
    )
    _require(
        len(validation_lines) == 1
        and assignment_lines["authenticated_before_receipt"]
        < assignment_lines["receipt"]
        < assignment_lines["receipt_path"]
        < assignment_lines["final_source_seal"]
        < assignment_lines["final_authority"]
        < assignment_lines["authenticated_before_seal"]
        < assignment_lines["seal"]
        < assignment_lines["seal_path"]
        < validation_lines[0],
        "compute writer lost receipt-write, source/context revalidation, seal-write ordering",
    )
    function_source = ast.get_source_segment(runner_source, write_function)
    if function_source is None:
        raise AssertionError("compute writer source could not be recovered")
    for required_fragment in (
        '"protocol_commit": authenticated_before_receipt["protocol_commit"]',
        'authenticated_git = authenticated_before_receipt["protocol_git"]',
        'authenticated_implementation = authenticated_before_receipt["implementation_provenance"]',
        'authenticated_runtime = authenticated_before_receipt["compute_runtime"]',
        '"protocol_commit": authenticated_before_seal["protocol_commit"]',
        'final_authenticated_git = authenticated_before_seal["protocol_git"]',
        'final_authenticated_runtime = authenticated_before_seal["compute_runtime"]',
        'final_bootstrap = authenticated_before_seal["compute_bootstrap_attestation"]',
        '"initial_git": authenticated_git',
        '"preterminal_git": authenticated_git',
        '"implementation_provenance": authenticated_implementation',
        '"runtime": authenticated_runtime',
        '"initial_git": final_authenticated_git',
        '"preterminal_git": final_authenticated_git',
        '"final_git": final_authenticated_git',
        '"final_source_seal": final_source_seal',
        '"final_bootstrap_attestation": final_bootstrap',
    ):
        _require(
            required_fragment in function_source,
            f"compute receipt/seal lost authenticated binding: {required_fragment}",
        )
    for authority_label in (
        '"initial_git"',
        '"preterminal_git"',
        '"final_git"',
        '"initial_implementation"',
        '"preterminal_implementation"',
        '"final_implementation"',
        '"initial_runtime"',
        '"preterminal_runtime"',
        '"final_runtime"',
    ):
        _require(
            authority_label in function_source,
            f"compute writer stopped comparing {authority_label} to authenticated context",
        )
    validator_calls = [
        node.func.id
        for node in ast.walk(functions["validate_execution_seal"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    _require(
        "_source_seal" in validator_calls and "_authenticated_seal_context" in validator_calls,
        "post-write validator no longer rehashes sources and reconstructs authority",
    )


def test_literal_calibre_pre_source_origin_gate_preserves_all_state() -> None:
    if os.environ.get(LITERAL_PRE_SOURCE_ENV) != "1":
        pytest.skip(f"Set {LITERAL_PRE_SOURCE_ENV}=1 only in a clean tagged V3F gate clone.")
    runner = _runner()
    config = _config()
    expected_command = [
        "C:/Program Files/Calibre2/calibre-debug.exe",
        "-e",
        "scripts/experiments/bootstrap_ijds_marginal_mean_score_outcome_gap_v3f.py",
        "--",
        "--phase",
        "pre-source-only",
        "--config",
        "configs/experiments/ijds_marginal_mean_score_outcome_gap_2026-07-26_v3f.yaml",
    ]
    _require(
        list(config["execution"]["authorized_orig_argv"]["pre-source-only"]) == expected_command,
        "literal pre-source command drifted",
    )
    before = _literal_pre_source_state(runner, config)
    _require(before["head"] == before["tag"], "literal gate HEAD is not the exact protocol tag")
    _require(before["status"] == b"", "literal gate worktree is not clean")
    expected_config_tree = (
        ("caches", "directory", None, None),
        (
            "global.py.json",
            "file",
            91,
            "7e8c7cdace709da838ca523f61bab5f7919d1973fb086938d045231e7195ae98",
        ),
        ("plugins", "directory", None, None),
    )
    _require(before["config_tree"] == expected_config_tree, "literal gate sentinel changed")
    _require(before["cache_tree"] == (), "literal gate Calibre cache is not empty")
    _require(before["pycache_tree"] == (), "literal gate pycache is not empty")
    _require(before["output_paths_present"] == [], "literal gate found a V3F output path")

    runtime_manifest = json.loads((ROOT / runner.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))
    bootstrap_contract = runtime_manifest["bootstrap"]
    forbidden = {str(value).upper() for value in bootstrap_contract["forbidden_environment"]}
    forbidden.update(
        str(value).upper() for value in bootstrap_contract["forbidden_environment_names"]
    )
    prefixes = tuple(
        str(value).upper() for value in bootstrap_contract["forbidden_environment_prefixes"]
    )
    environment = dict(os.environ)
    for name in list(environment):
        upper = name.upper()
        if upper in forbidden or any(upper.startswith(prefix) for prefix in prefixes):
            environment.pop(name)
    environment["CALIBRE_CONFIG_DIRECTORY"] = str(
        (ROOT / str(config["execution"]["calibre_config_directory"])).resolve()
    )
    environment["CALIBRE_CACHE_DIRECTORY"] = str(
        (ROOT / str(config["execution"]["calibre_cache_directory"])).resolve()
    )
    process = subprocess.run(
        expected_command,
        cwd=ROOT,
        env=environment,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=240,
    )
    _require(
        process.returncode == 0,
        f"literal pre-source gate failed: stdout={process.stdout!r}, stderr={process.stderr!r}",
    )
    _require(process.stderr.strip() == "", "literal pre-source gate emitted stderr")
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    _require(len(lines) == 1, f"literal pre-source gate emitted {len(lines)} stdout lines")
    receipt = json.loads(lines[0])
    expected_receipt = {
        "status": "complete_pre_source_authority_snapshot_attestation",
        "phase": "pre-source-only",
        "protocol_commit": before["head"],
        "head_tag": runner.PROTOCOL_TAG,
        "authority_files": 25,
        "authority_snapshot_files": 25,
        "git_bound_source_checks_complete": True,
        "loaded_local_modules_exact": True,
        "next_compute_operation": "_load_scientific_sources",
        "output_preflight_complete": True,
        "runtime_observation_complete": True,
        "terminal_fixed_point_verified": True,
        "terminal_revalidation_passes": 3,
        "terminal_revalidated": True,
    }
    for key, expected in expected_receipt.items():
        _require(receipt.get(key) == expected, f"literal pre-source receipt changed on {key}")
    priming_paths = receipt.get("terminal_priming_mismatch_paths")
    _require(
        isinstance(priming_paths, list)
        and receipt.get("terminal_priming_mismatch_count") == len(priming_paths),
        "literal pre-source priming diagnostics changed",
    )
    _require(
        receipt.get("loaded_local_modules") == runner._expected_handoff_local_modules(),
        "literal pre-source local-module census changed",
    )
    after = _literal_pre_source_state(runner, config)
    _require(after == before, "literal pre-source gate mutated Git/runtime/output state")


def test_terminal_revalidation_callback_is_bound_to_entrypoint_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap()
    runner = _runner()
    callback = bootstrap.revalidate_bootstrap_attestation
    monkeypatch.setitem(sys.modules, "calibre.debug", bootstrap)
    monkeypatch.setattr(
        runner,
        "_IJDS_V3F_REVALIDATE_BOOTSTRAP_ATTESTATION",
        callback,
        raising=False,
    )
    _require(
        runner._require_revalidation_callback() is callback,
        "entrypoint-bound terminal callback was not retained",
    )
    monkeypatch.setattr(
        runner,
        "_IJDS_V3F_REVALIDATE_BOOTSTRAP_ATTESTATION",
        lambda **_kwargs: {},
    )
    with pytest.raises(RuntimeError, match="not bound to the authenticated"):
        runner._require_revalidation_callback()
    forged_globals = dict(vars(bootstrap))
    forged = FunctionType(
        callback.__code__,
        forged_globals,
        callback.__name__,
        callback.__defaults__,
        callback.__closure__,
    )
    forged.__qualname__ = callback.__qualname__
    forged.__kwdefaults__ = callback.__kwdefaults__
    monkeypatch.setattr(
        runner,
        "_IJDS_V3F_REVALIDATE_BOOTSTRAP_ATTESTATION",
        forged,
    )
    with pytest.raises(RuntimeError, match="not bound to the authenticated"):
        runner._require_revalidation_callback()


def test_handoff_requires_exact_complete_local_module_set() -> None:
    runner = _runner()
    expected = runner._expected_handoff_local_modules()
    _require("calibre.debug" in expected, "entrypoint carrier missing from handoff set")
    _require(
        "scripts.experiments.bootstrap_ijds_marginal_mean_score_outcome_gap_v3f" in expected,
        "sealed bootstrap import missing from handoff set",
    )
    _require(
        "scripts.experiments.run_ijds_marginal_mean_score_outcome_gap_v3f" not in expected,
        "exec-compiled runner was incorrectly treated as a sys.modules import",
    )
    _require(len(expected) == 10, f"handoff local module census changed: {expected}")


def test_calibre_template_is_fixed_sentinel_and_config_seal_rejects_personal_metadata(
    tmp_path: Path,
) -> None:
    bootstrap = _bootstrap()
    template_bytes = RUNTIME_TEMPLATE_PATH.read_bytes()
    _require(
        json.loads(template_bytes) == CALIBRE_PROTOCOL_SENTINEL,
        "Calibre template differs from the fixed nonidentifying sentinel",
    )
    _require(len(template_bytes) == 91, "Calibre sentinel byte length changed")
    _require(
        bootstrap.hashlib.sha256(template_bytes).hexdigest()
        == "7e8c7cdace709da838ca523f61bab5f7919d1973fb086938d045231e7195ae98",
        "Calibre sentinel SHA-256 changed",
    )
    template = tmp_path / "template.json"
    template.write_text(
        json.dumps(CALIBRE_PROTOCOL_SENTINEL, indent=2) + "\n",
        encoding="utf-8",
    )
    directory = tmp_path / "config"
    (directory / "caches").mkdir(parents=True)
    (directory / "plugins").mkdir()
    (directory / "global.py.json").write_bytes(template.read_bytes())
    manifest = {
        "bootstrap": {
            "calibre_config_directory": "config",
            "calibre_global_template": "template.json",
        }
    }
    observed = bootstrap._calibre_config_seal(manifest, repo_root=tmp_path)
    _require(observed["caches_empty"] is True, "empty Calibre cache was not certified")
    (directory / "global.py.json").write_text(
        json.dumps(
            {
                "database_path": "C:/Users/example/library.db",
                "installation_uuid": "not-portable",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="differs from its Git-bound template"):
        bootstrap._calibre_config_seal(manifest, repo_root=tmp_path)


def test_calibre_cache_is_dedicated_and_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap = _bootstrap()
    cache = tmp_path / "calibre-cache"
    cache.mkdir()
    monkeypatch.setenv("CALIBRE_CACHE_DIRECTORY", str(cache))
    manifest = {"bootstrap": {"calibre_cache_directory": "calibre-cache"}}
    _require(
        bootstrap._calibre_cache_seal(manifest, repo_root=tmp_path)["empty"] is True,
        "empty dedicated Calibre cache was not certified",
    )
    (cache / "foreign-state.bin").write_bytes(b"state")
    with pytest.raises(RuntimeError, match="not empty"):
        bootstrap._calibre_cache_seal(manifest, repo_root=tmp_path)


def test_distribution_seal_changes_after_recorded_file_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap = _bootstrap()
    site = tmp_path / ".venv/Lib/site-packages"
    info = site / "demo-1.0.dist-info"
    info.mkdir(parents=True)
    module = site / "demo.py"
    module.write_bytes(b"VALUE = 1\n")
    record = info / "RECORD"
    record.write_bytes(b"demo.py,,\ndemo-1.0.dist-info/RECORD,,\n")

    class FakeDistribution:
        def __init__(self) -> None:
            self.metadata = {"Name": "demo"}
            self.version = "1.0"
            self.files = (Path("demo.py"), Path("demo-1.0.dist-info/RECORD"))

        @staticmethod
        def locate_file(entry: Path) -> Path:
            return site / entry

    monkeypatch.setattr(
        bootstrap.importlib.metadata,
        "distributions",
        lambda **_kwargs: [FakeDistribution()],
    )
    initial = bootstrap._distribution_seal("demo", repo_root=tmp_path)
    module.write_bytes(b"VALUE = 2\n")
    mutated = bootstrap._distribution_seal("demo", repo_root=tmp_path)
    _require(initial["bytes"] == mutated["bytes"], "mutation unexpectedly changed byte count")
    _require(
        initial["composite_sha256"] != mutated["composite_sha256"],
        "recorded distribution mutation escaped the byte seal",
    )


def test_clean_clone_venv_materializer_copies_only_locked_record_closure(
    tmp_path: Path,
) -> None:
    bootstrap = _bootstrap()
    source_venv = tmp_path / "source-venv"
    source_site = source_venv / "Lib/site-packages"
    info = source_site / "demo-1.0.dist-info"
    info.mkdir(parents=True)
    (source_site / "demo.py").write_bytes(b"VALUE = 1\n")
    (source_site / "unsealed.py").write_bytes(b"SHOULD_NOT_COPY = True\n")
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n",
        encoding="utf-8",
    )
    (info / "RECORD").write_text(
        "demo.py,,\ndemo-1.0.dist-info/METADATA,,\ndemo-1.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )
    expected = bootstrap._distribution_seal_at_venv("demo", venv=source_venv)
    target = tmp_path / "target"
    runtime_path = target / bootstrap.RUNTIME_MANIFEST_PATH
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": "2026-07-26.3f-runtime-1",
                "bootstrap": {},
                "git": {},
                "calibre": {},
                "distributions": {"demo": expected},
                "module_paths": {},
            }
        ),
        encoding="utf-8",
    )
    receipt = bootstrap.materialize_locked_project_venv(source_venv, repo_root=target)
    _require(receipt["distributions"] == {"demo": expected}, "venv seal changed")
    _require(
        not (target / ".venv/Lib/site-packages/unsealed.py").exists(),
        "venv materializer copied an unsealed site-packages file",
    )
    _require(
        (target / ".venv/Lib/site-packages/demo.py").read_bytes() == b"VALUE = 1\n",
        "venv materializer changed recorded bytes",
    )


def test_loaded_native_module_must_belong_to_sealed_runtime_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap = _bootstrap()
    manifest = json.loads((ROOT / bootstrap.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))
    evil_path = tmp_path / "unsealed_extension.pyd"
    evil_path.write_bytes(b"not-a-real-extension")
    evil = ModuleType("v3f_unsealed_native_test")
    evil.__file__ = str(evil_path)
    monkeypatch.setitem(sys.modules, evil.__name__, evil)
    with pytest.raises(RuntimeError, match="escaped the sealed V3F inventories"):
        bootstrap.require_loaded_native_modules(manifest, repo_root=ROOT)


def test_loaded_pure_python_site_module_must_belong_to_sealed_record_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap()
    manifest = json.loads((ROOT / bootstrap.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))
    evil = ModuleType("v3f_unsealed_pure_site_test")
    evil.__file__ = str(ROOT / ".venv/Lib/site-packages/unsealed_optional_dependency.py")
    monkeypatch.setitem(sys.modules, evil.__name__, evil)
    with pytest.raises(RuntimeError, match="seven sealed RECORD closures"):
        bootstrap.require_loaded_site_modules(manifest, repo_root=ROOT)


def test_calibre_entrypoint_carrier_is_narrowly_attested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap()
    bootstrap_spec = bootstrap.__spec__
    if bootstrap_spec is None:
        raise RuntimeError("Test bootstrap spec is absent.")
    original_module_key = str(bootstrap_spec.name)

    class FrozenByteCodeLoader:
        pass

    FrozenByteCodeLoader.__module__ = "bypy_importer"
    loader: Any = FrozenByteCodeLoader()
    expected = json.loads((ROOT / bootstrap.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))[
        "bootstrap"
    ]["calibre_entrypoint_carrier"]
    spec = importlib.machinery.ModuleSpec(
        str(expected["spec_name"]), loader, origin=str(expected["spec_origin"])
    )
    _require(original_module_key in sys.modules, "imported bootstrap module is absent")
    carrier = ModuleType(str(expected["module_name"]))
    carrier.__file__ = str(ROOT / bootstrap.BOOTSTRAP_PATH)
    carrier.__package__ = str(expected["package"])
    vars(carrier)["__cached__"] = None
    carrier.__loader__ = loader
    carrier.__spec__ = spec
    monkeypatch.setitem(sys.modules, str(expected["module_key"]), carrier)
    sealed = {bootstrap.BOOTSTRAP_PATH: (ROOT / bootstrap.BOOTSTRAP_PATH).read_bytes()}
    manifest = json.loads((ROOT / bootstrap.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))
    receipt = bootstrap.require_calibre_entrypoint_carrier(
        manifest,
        sealed,
        entrypoint_globals=vars(carrier),
        repo_root=ROOT,
    )
    _require(receipt["module_key"] == "calibre.debug", "carrier module key changed")
    _require(receipt["aliases"] == ["calibre.debug"], "carrier alias census missing")
    _require(receipt["carrier_is_executing_globals"] is True, "carrier globals detached")
    _require(len(receipt["bootstrap_sha256"]) == 64, "carrier bootstrap hash missing")
    for foreign_globals in ({}, dict(vars(carrier)), vars(bootstrap), None):
        with pytest.raises(RuntimeError, match="carrier identity changed"):
            bootstrap.require_calibre_entrypoint_carrier(
                manifest,
                sealed,
                entrypoint_globals=foreign_globals,
                repo_root=ROOT,
            )
    with pytest.raises(TypeError, match="entrypoint_globals"):
        bootstrap.require_calibre_entrypoint_carrier(
            manifest,
            sealed,
            repo_root=ROOT,
        )
    monkeypatch.setitem(sys.modules, "calibre.debug.alias", carrier)
    with pytest.raises(RuntimeError, match="aliases changed"):
        bootstrap.require_calibre_entrypoint_carrier(
            manifest,
            sealed,
            entrypoint_globals=vars(carrier),
            repo_root=ROOT,
        )


def test_bootstrap_rejects_git_environment_and_nonempty_isolation_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap = _bootstrap()
    monkeypatch.setenv("GIT_DIR", "C:/attacker/repository")
    manifest = {
        "bootstrap": {
            "forbidden_environment": ["GIT_DIR", "PYTHONPATH"],
            "forbidden_environment_names": ["TZ"],
            "forbidden_environment_prefixes": ["OMP_"],
        }
    }
    with pytest.raises(RuntimeError, match="forbidden environment"):
        bootstrap._require_forbidden_environment(manifest)
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.setenv("OMP_NUM_THREADS", "9")
    with pytest.raises(RuntimeError, match="forbidden environment"):
        bootstrap._require_forbidden_environment(manifest)
    sanitized = bootstrap._git_environment()
    _require("GIT_DIR" not in sanitized, "attacker GIT_DIR reached authenticated Git")
    _require(sanitized["GIT_CONFIG_NOSYSTEM"] == "1", "system Git config was not disabled")
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    (isolated / "unexpected.pyc").write_bytes(b"bytecode")
    with pytest.raises(RuntimeError, match="not empty"):
        bootstrap._require_directory_empty(isolated, label="test isolation directory")


def test_strict_tag_rejects_revision_expression_before_git_lookup(tmp_path: Path) -> None:
    runner = _runner()
    with pytest.raises(RuntimeError, match="safe tag name"):
        runner._resolve_strict_tag(tmp_path, "protocol/example^{}")
    with pytest.raises(RuntimeError, match="safe tag name"):
        runner._resolve_strict_tag(tmp_path, "refs/tags/protocol/example")


def test_v3f_protocol_parent_must_be_direct_aborted_v3e_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    _init_git(tmp_path)
    marker = tmp_path / "marker.txt"
    marker.write_text("aborted-v3e", encoding="utf-8")
    _git(tmp_path, "add", "marker.txt")
    _git(tmp_path, "commit", "-m", "aborted v3e")
    aborted = _git(tmp_path, "rev-parse", "HEAD")
    marker.write_text("v3f", encoding="utf-8")
    _git(tmp_path, "commit", "-am", "v3f")
    protocol = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(runner, "ABORTED_V3E_PROTOCOL_COMMIT", aborted)
    monkeypatch.setattr(runner, "EXPECTED_V3F_PROTOCOL_DIFF_PATHS", ("marker.txt",))
    runner._require_v3f_protocol_parent(protocol_commit=protocol, repo_root=tmp_path)
    marker.write_text("extra", encoding="utf-8")
    _git(tmp_path, "commit", "-am", "extra")
    extra = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="direct child"):
        runner._require_v3f_protocol_parent(protocol_commit=extra, repo_root=tmp_path)


def test_runtime_contract_accepts_only_exact_calibre_argv_and_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _runner()
    bootstrap = _bootstrap()
    config = _config()
    config_directory = tmp_path / "calibre-config"
    config_directory.mkdir(parents=True, exist_ok=False)
    config["execution"]["calibre_config_directory"] = config_directory.relative_to(ROOT).as_posix()
    cache = tmp_path / "calibre-cache"
    cache.mkdir(parents=True, exist_ok=False)
    config["execution"]["calibre_cache_directory"] = cache.relative_to(ROOT).as_posix()
    monkeypatch.setenv("CALIBRE_CONFIG_DIRECTORY", str(config_directory))
    monkeypatch.setenv("CALIBRE_CACHE_DIRECTORY", str(cache))
    authority_paths = {
        *runner.BOOTSTRAP_PYTHON_PATHS,
        *runner.TRANSITIVE_PYTHON_PATHS,
        *runner.NONPYTHON_AUTHORITY_PATHS,
    }
    sealed = {path: (ROOT / path).read_bytes() for path in authority_paths}
    authority_descriptors = {
        path.as_posix(): runner._descriptor_from_bytes(payload, relative_path=path.as_posix())
        for path, payload in sealed.items()
    }
    monkeypatch.setattr(runner, "_SEALED_AUTHORITY_BYTES", sealed)
    monkeypatch.setattr(runner, "_RUNNER_EXECUTED_FROM_SEALED_BYTES", True)
    monkeypatch.setattr(runner, "_IJDS_V3F_RUNNER_EXECUTED_FROM_SEALED_BYTES", True, raising=False)
    monkeypatch.setattr(
        runner,
        "require_sealed_import_runtime",
        lambda *_args, **_kwargs: {
            "finder_composite_sha256": "f" * 64,
            "loaded_sealed_modules": {},
        },
    )
    observed_carrier_bindings: list[dict[str, Any]] = []

    def fake_loaded_module_origins(
        *_args: Any, entrypoint_globals: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        observed_carrier_bindings.append(entrypoint_globals)
        return {}

    monkeypatch.setattr(runner, "require_loaded_module_origins", fake_loaded_module_origins)
    monkeypatch.setattr(
        runner,
        "_IJDS_V3F_BOOTSTRAP_ATTESTATION",
        {
            "schema_version": "2026-07-26.3f-bootstrap-1",
            "phase": "compute",
            "head_tag": runner.PROTOCOL_TAG,
            "authority": {"source_files": authority_descriptors},
        },
        raising=False,
    )
    monkeypatch.setitem(sys.modules, "calibre.debug", bootstrap)
    monkeypatch.setattr(
        runner,
        "_IJDS_V3F_REVALIDATE_BOOTSTRAP_ATTESTATION",
        bootstrap.revalidate_bootstrap_attestation,
        raising=False,
    )
    for module_name in (
        "src.data.outcome_observability",
        "src.ijds_audit.marginal_mean_score_outcome_gap_v3f",
        "src.utils.artifact_descriptor",
    ):
        monkeypatch.setattr(sys.modules[module_name], "__cached__", None, raising=False)
    monkeypatch.setattr(
        runner.sys,
        "path",
        [str(ROOT.resolve()), str((ROOT / ".venv/Lib/site-packages").resolve())],
    )
    runtime_manifest = json.loads((ROOT / runner.RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8"))
    for module, manifest_key in (
        (runner.dateutil, "dateutil"),
        (runner.np, "numpy"),
        (runner.pd, "pandas"),
        (runner.pyarrow, "pyarrow"),
        (runner.yaml, "yaml"),
        (runner.six, "six"),
        (runner.tzdata, "tzdata"),
    ):
        monkeypatch.setattr(
            module,
            "__file__",
            str((ROOT / runtime_manifest["module_paths"][manifest_key]).resolve()),
        )
    expected = list(config["execution"]["authorized_orig_argv"]["compute"])
    expected[0] = str(Path(expected[0]))
    monkeypatch.setattr(runner.sys, "orig_argv", expected)
    observed = runner._runtime_observation(config, phase="compute")
    _require(
        observed_carrier_bindings == [vars(bootstrap)],
        "runtime origin audit was not bound to the authenticated carrier globals",
    )
    _require(observed["python"]["optimize"] == 2, "Calibre optimize flag was hidden")
    _require(observed["python"]["debug"] is False, "Calibre debug flag was hidden")
    serialized_runtime = json.dumps(observed, ensure_ascii=False)
    _require("C:/Users/" not in serialized_runtime, "runtime receipt leaked a user path")
    _require("carlos" not in serialized_runtime.casefold(), "runtime receipt leaked a username")
    bad_argv = list(expected)
    bad_argv[-1] = "configs/experiments/not-canonical.yaml"
    monkeypatch.setattr(runner.sys, "orig_argv", bad_argv)
    with pytest.raises(RuntimeError, match="authorized argv"):
        runner._runtime_observation(config, phase="compute")
    monkeypatch.setattr(runner.sys, "orig_argv", expected)
    bad_lock = copy.deepcopy(config)
    bad_lock["execution"]["uv_lock_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match=r"uv\.lock"):
        runner._runtime_observation(bad_lock, phase="compute")
    bad_optimize = copy.deepcopy(config)
    bad_optimize["execution"]["python"]["optimize"] = 0
    with pytest.raises(RuntimeError, match="optimize flags"):
        runner._runtime_observation(bad_optimize, phase="compute")
    cache.rmdir()


def test_git_blob_check_detects_same_length_working_mutation(tmp_path: Path) -> None:
    runner = _runner()
    _init_git(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_bytes(b"abcd\n")
    _git(tmp_path, "add", "config.yaml")
    _git(tmp_path, "commit", "-m", "lock")
    commit = _git(tmp_path, "rev-parse", "HEAD")
    runner.require_working_file_matches_git(path, commit=commit, repo_root=tmp_path)
    path.write_bytes(b"abce\n")
    with pytest.raises(RuntimeError, match="differs from Git blob"):
        runner.require_working_file_matches_git(path, commit=commit, repo_root=tmp_path)


def test_source_byte_seal_detects_same_length_mutation(tmp_path: Path) -> None:
    runner = _runner()
    path = tmp_path / "source.json"
    original = b'{"x":1}\n'
    path.write_bytes(original)
    descriptor = {
        "path": "source.json",
        "bytes": len(original),
        "sha256": runner.hashlib.sha256(original).hexdigest(),
    }
    _path, captured = runner._read_verified_bytes(
        descriptor, label="test source", repo_root=tmp_path
    )
    _require(captured == original, "source was not parsed from its sealed bytes")
    path.write_bytes(b'{"x":2}\n')
    with pytest.raises(RuntimeError, match="sha256"):
        runner._read_verified_bytes(descriptor, label="test source", repo_root=tmp_path)


def test_output_preflight_and_exclusive_writes_are_no_overwrite(tmp_path: Path) -> None:
    runner = _runner()
    config = _config()
    (tmp_path / "data/processed/experiments/ijds_audit").mkdir(parents=True)
    (tmp_path / "models/experiments/ijds_audit").mkdir(parents=True)
    runner._preflight_outputs(config, repo_root=tmp_path)
    data_dir, _model_dir, _targets = runner.output_targets(config, repo_root=tmp_path)
    data_dir.mkdir()
    with pytest.raises(FileExistsError, match="occupied"):
        runner._preflight_outputs(config, repo_root=tmp_path)
    target = tmp_path / "exclusive.bin"
    target.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        runner._exclusive_write_bytes(target, b"new")
    _require(target.read_bytes() == b"old", "exclusive write overwrote an existing target")
    nan_target = tmp_path / "nan.json"
    with pytest.raises(ValueError):
        runner._exclusive_write_json(nan_target, {"x": float("nan")})
    _require(not nan_target.exists(), "strict JSON failure left a final target")
    parquet_target = tmp_path / "exclusive.parquet"
    parquet_frame = pd.DataFrame({"x": pd.Series([1, 2], dtype="int64")})
    runner._exclusive_write_parquet(parquet_target, parquet_frame)
    _require(
        pd.read_parquet(parquet_target).equals(parquet_frame),
        "exclusive Parquet write changed the frame",
    )
    with pytest.raises(FileExistsError):
        runner._exclusive_write_parquet(parquet_target, pd.DataFrame({"x": [3]}))
    _require(
        pd.read_parquet(parquet_target).equals(parquet_frame),
        "exclusive Parquet write overwrote an existing target",
    )


def test_v3e_terminal_context_failure_class_is_reproduced_and_v3f_reaches_fixed_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    first = {
        "schema_version": "2026-07-26.3f-bootstrap-1",
        "terminal_module_origins": {"loaded_site_modules": ["pandas"]},
        "terminal_revalidated": True,
    }
    stable = {
        "schema_version": "2026-07-26.3f-bootstrap-1",
        "terminal_module_origins": {
            "loaded_site_modules": ["pandas", "pyarrow.parquet"]
        },
        "terminal_revalidated": True,
    }
    one_shot_values = iter((copy.deepcopy(first), copy.deepcopy(stable)))

    def v3e_one_shot(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return next(one_shot_values)

    sealed_once = v3e_one_shot()
    validated_once = v3e_one_shot()
    reproduced_paths = runner._mismatch_paths(
        sealed_once, validated_once, prefix="$.seal.final_bootstrap_attestation"
    )
    _require(
        reproduced_paths
        == [
            "$.seal.final_bootstrap_attestation.terminal_module_origins."
            "loaded_site_modules:length:1!=2"
        ],
        f"V3E terminal-context failure class was not reproduced: {reproduced_paths}",
    )

    fixed_point_values = iter(
        (copy.deepcopy(first), copy.deepcopy(stable), copy.deepcopy(stable))
    )

    def v3f_callback(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return next(fixed_point_values)

    monkeypatch.setattr(
        runner,
        "_require_bootstrap_attestation",
        lambda *, phase: {"phase": phase},
    )
    monkeypatch.setattr(runner, "_require_revalidation_callback", lambda: v3f_callback)
    monkeypatch.setattr(runner, "_SEALED_AUTHORITY_BYTES", {})
    terminal = runner._stable_terminal_bootstrap_attestation(
        phase="compute", repo_root=tmp_path
    )
    _require(terminal == stable, "V3F did not retain the verified terminal fixed point")


def test_v3f_terminal_context_rejects_a_nonconvergent_revalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    values = iter(
        (
            {"terminal_module_origins": {"loaded_site_modules": ["a"]}},
            {"terminal_module_origins": {"loaded_site_modules": ["a", "b"]}},
            {"terminal_module_origins": {"loaded_site_modules": ["a", "c"]}},
        )
    )

    def callback(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return next(values)

    monkeypatch.setattr(
        runner,
        "_require_bootstrap_attestation",
        lambda *, phase: {"phase": phase},
    )
    monkeypatch.setattr(runner, "_require_revalidation_callback", lambda: callback)
    monkeypatch.setattr(runner, "_SEALED_AUTHORITY_BYTES", {})
    with pytest.raises(RuntimeError, match="did not reach a two-pass fixed point"):
        runner._stable_terminal_bootstrap_attestation(phase="compute", repo_root=tmp_path)


def _build_sealed_output_fixture(
    runner: ModuleType, config: dict[str, Any], root: Path
) -> tuple[dict[str, Path], Path, dict[str, Any]]:
    (root / "data/processed/experiments/ijds_audit").mkdir(parents=True)
    (root / "models/experiments/ijds_audit").mkdir(parents=True)
    data_dir, model_dir, targets = runner.output_targets(config, repo_root=root)
    data_dir.mkdir()
    model_dir.mkdir()
    targets["table"].parent.mkdir(parents=True)
    pd.DataFrame({"x": range(5)}).to_parquet(targets["table"], index=False)
    pd.DataFrame({"x": range(5)}).to_parquet(targets["endpoint_reason_census"], index=False)
    pd.DataFrame({"x": range(75)}).to_parquet(
        targets["monthly_endpoint_reason_census"], index=False
    )
    artifacts = {
        "marginal_mean_score_outcome_gap": runner.relative_artifact_descriptor(
            targets["table"], repo_root=root
        ),
        "endpoint_reason_census": runner.relative_artifact_descriptor(
            targets["endpoint_reason_census"], repo_root=root
        ),
        "monthly_endpoint_reason_census": runner.relative_artifact_descriptor(
            targets["monthly_endpoint_reason_census"], repo_root=root
        ),
    }
    protocol_git = {
        "commit": "a" * 40,
        "porcelain_v2_sha256": runner.hashlib.sha256(b"").hexdigest(),
        "porcelain_v2_bytes": 0,
        "clean": True,
    }
    implementation = {
        "hash_algorithm": "sha256",
        "protocol_commit": "a" * 40,
        "source_files": {"sealed.py": {"bytes": 1, "sha256": "d" * 64}},
        "executed_from_sealed_git_bytes": True,
    }
    runtime = {
        "runner_executed_from_sealed_bytes": True,
        "sealed_import_runtime": {"finder_composite_sha256": "e" * 64},
        "loaded_native_modules": {},
    }
    bootstrap_attestation = {
        "schema_version": "2026-07-26.3f-bootstrap-1",
        "phase": "compute",
        "protocol_commit": "a" * 40,
        "head_tag": runner.PROTOCOL_TAG,
        "head": protocol_git,
        "terminal_revalidated": True,
    }
    authenticated_context = {
        "protocol_commit": "a" * 40,
        "protocol_git": protocol_git,
        "implementation_provenance": implementation,
        "compute_runtime": runtime,
        "compute_bootstrap_attestation": bootstrap_attestation,
    }
    summary = {
        "schema_version": runner.SCHEMA_VERSION,
        "status": "complete_clean_tagged_v3f_pending_git_artifact_commit",
        "run_tag": runner.RUN_TAG,
        "protocol_tag": runner.PROTOCOL_TAG,
        "protocol_commit": "a" * 40,
        "artifact_tag_required_before_promotion": runner.ARTIFACT_TAG,
        "estimand": runner.ESTIMAND,
        "candidate_identity": {},
        "endpoint_row_sha256": "b" * 64,
        "issue_months": [],
        "endpoint": {},
        "identification": {},
        "results": {},
        "source_audit": {},
        "source_seal": {"composite_sha256": "c" * 64},
        "schemas": {},
        "artifacts": artifacts,
        "reporting_contract": {},
        "git_artifact_commit_performed": False,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    targets["summary"].write_text(json.dumps(summary), encoding="utf-8")
    summary_descriptor = runner.relative_artifact_descriptor(targets["summary"], repo_root=root)
    receipt = {
        "schema_version": runner.SCHEMA_VERSION,
        "status": "complete_clean_tagged_v3f_receipt_pending_git_artifact_commit",
        "run_tag": runner.RUN_TAG,
        "protocol_tag": runner.PROTOCOL_TAG,
        "protocol_commit": "a" * 40,
        "artifact_tag_required_before_promotion": runner.ARTIFACT_TAG,
        "started_at_utc": "2026-07-26T00:00:00+00:00",
        "completed_at_utc": "2026-07-26T00:00:01+00:00",
        "runtime_seconds": 1.0,
        "initial_git": protocol_git,
        "preterminal_git": protocol_git,
        "implementation_provenance": implementation,
        "runtime": runtime,
        "initial_source_seal": {"composite_sha256": "c" * 64},
        "preterminal_source_seal": {"composite_sha256": "c" * 64},
        "summary": summary_descriptor,
        "artifacts": artifacts,
        "preterminal_implementation_provenance": implementation,
        "preterminal_runtime": runtime,
        "git_artifact_commit": {
            "performed": False,
            "required_before_promotion": True,
            "transport": "git_force_tracked_direct_child_commit",
            "dvc_tracked": False,
            "expected_paths": config["output"]["artifact_registration"]["expected_paths"],
        },
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    targets["execution_receipt"].write_text(json.dumps(receipt), encoding="utf-8")
    receipt_descriptor = runner.relative_artifact_descriptor(
        targets["execution_receipt"], repo_root=root
    )
    seal = {
        "schema_version": runner.SCHEMA_VERSION,
        "status": "terminal_v3f_seal_pending_git_artifact_commit",
        "run_tag": runner.RUN_TAG,
        "protocol_tag": runner.PROTOCOL_TAG,
        "protocol_commit": "a" * 40,
        "artifact_tag_required_before_promotion": runner.ARTIFACT_TAG,
        "git_artifact_commit_performed": False,
        "active_evidence_authorized": False,
        "summary": summary_descriptor,
        "execution_receipt": receipt_descriptor,
        "artifacts": artifacts,
        "expected_data_inventory": list(runner._expected_inventories(config)[0]),
        "expected_model_inventory": list(runner._expected_inventories(config)[1]),
        "source_composite_sha256": "c" * 64,
        "preterminal_source_composite_sha256": "c" * 64,
        "final_source_seal": {"composite_sha256": "c" * 64},
        "implementation_provenance": implementation,
        "runtime": runtime,
        "final_implementation_provenance": implementation,
        "final_runtime": runtime,
        "final_bootstrap_attestation": bootstrap_attestation,
        "initial_git": protocol_git,
        "preterminal_git": protocol_git,
        "final_git": protocol_git,
        "protected_stages_run": [],
        "protected_artifacts_written": [],
    }
    targets["execution_seal"].write_text(json.dumps(seal), encoding="utf-8")
    return targets, targets["execution_seal"], authenticated_context


def _patch_validation_authority(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    authenticated: dict[str, Any],
) -> None:
    monkeypatch.setattr(
        runner,
        "_authenticated_seal_context",
        lambda *_args, **_kwargs: copy.deepcopy(authenticated),
    )
    stable_source_seal = {"composite_sha256": "c" * 64}
    monkeypatch.setattr(
        runner,
        "_source_seal",
        lambda *_args, **_kwargs: (copy.deepcopy(stable_source_seal), {}),
    )


def test_terminal_execution_seal_detects_bit_flip_and_extra_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    config = _config()
    targets, _seal_path, authenticated = _build_sealed_output_fixture(runner, config, tmp_path)
    _patch_validation_authority(runner, monkeypatch, authenticated)
    runner.validate_execution_seal(config, repo_root=tmp_path)
    original = targets["table"].read_bytes()
    targets["table"].write_bytes(original + b"x")
    with pytest.raises(RuntimeError, match="no longer binds"):
        runner.validate_execution_seal(config, repo_root=tmp_path)
    targets["table"].write_bytes(original)
    extra = targets["summary"].parent / "extra.json"
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="inventory changed"):
        runner.validate_execution_seal(config, repo_root=tmp_path)


def test_terminal_execution_seal_rehashes_and_rejects_postwrite_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    config = _config()
    _targets, _seal_path, authenticated = _build_sealed_output_fixture(
        runner, config, tmp_path
    )
    _patch_validation_authority(runner, monkeypatch, authenticated)
    drifted_source_seal = {"composite_sha256": "f" * 64}
    monkeypatch.setattr(
        runner,
        "_source_seal",
        lambda *_args, **_kwargs: (copy.deepcopy(drifted_source_seal), {}),
    )
    with pytest.raises(
        RuntimeError,
        match=r"post-write source seal mismatch:.*postwrite_source_seal\.composite_sha256",
    ):
        runner.validate_execution_seal(config, repo_root=tmp_path)


@pytest.mark.parametrize("family", ["implementation", "runtime", "bootstrap"])
def test_terminal_seal_rejects_coherent_authority_erasure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    runner = _runner()
    config = _config()
    targets, _seal_path, authenticated = _build_sealed_output_fixture(runner, config, tmp_path)
    _patch_validation_authority(runner, monkeypatch, authenticated)
    receipt = json.loads(targets["execution_receipt"].read_text(encoding="utf-8"))
    seal = json.loads(targets["execution_seal"].read_text(encoding="utf-8"))
    if family == "implementation":
        receipt["implementation_provenance"] = {}
        receipt["preterminal_implementation_provenance"] = {}
        seal["implementation_provenance"] = {}
        seal["final_implementation_provenance"] = {}
    elif family == "runtime":
        receipt["runtime"] = {}
        receipt["preterminal_runtime"] = {}
        seal["runtime"] = {}
        seal["final_runtime"] = {}
    else:
        seal["final_bootstrap_attestation"] = {"schema_version": "2026-07-26.3f-bootstrap-1"}
    targets["execution_receipt"].write_text(json.dumps(receipt), encoding="utf-8")
    seal["execution_receipt"] = runner.relative_artifact_descriptor(
        targets["execution_receipt"], repo_root=tmp_path
    )
    targets["execution_seal"].write_text(json.dumps(seal), encoding="utf-8")
    with pytest.raises(RuntimeError, match="authenticated terminal context mismatch"):
        runner.validate_execution_seal(config, repo_root=tmp_path)


def test_git_native_artifacts_are_small_aggregate_only_and_path_neutral(tmp_path: Path) -> None:
    runner = _runner()
    config = _config()
    targets, _seal_path, _authenticated = _build_sealed_output_fixture(runner, config, tmp_path)
    audit = runner.validate_aggregate_only_artifacts(config, repo_root=tmp_path)
    _require(
        audit["parquet_rows"]
        == {"table": 5, "endpoint_reason_census": 5, "monthly_endpoint_reason_census": 75},
        "aggregate row contract changed",
    )
    original_table = pd.read_parquet(targets["table"])
    leaked_table = original_table.assign(id=[f"loan-{index}" for index in range(5)])
    leaked_table.to_parquet(targets["table"], index=False)
    with pytest.raises(RuntimeError, match="row-level columns"):
        runner.validate_aggregate_only_artifacts(config, repo_root=tmp_path)
    original_table.to_parquet(targets["table"], index=False)
    summary = json.loads(targets["summary"].read_text(encoding="utf-8"))
    summary["database_path"] = "C:/Users/example/library.db"
    targets["summary"].write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(RuntimeError, match="personal or row-level keys"):
        runner.validate_aggregate_only_artifacts(config, repo_root=tmp_path)


def test_verify_recomputation_defeats_a_coherently_resealed_scientific_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _runner()
    config = _config()
    targets, _seal_path, authenticated = _build_sealed_output_fixture(runner, config, tmp_path)
    _patch_validation_authority(runner, monkeypatch, authenticated)
    expected_table = pd.read_parquet(targets["table"])
    expected_endpoint = pd.read_parquet(targets["endpoint_reason_census"])
    expected_monthly = pd.read_parquet(targets["monthly_endpoint_reason_census"])
    result = runner.MarginalMeanScoreOutcomeGapV3FResult(
        table=expected_table,
        endpoint_reason_census=expected_endpoint,
        monthly_endpoint_reason_census=expected_monthly,
        join_audit={},
        issue_months=(),
        endpoint_row_sha256="b" * 64,
    )

    pd.DataFrame({"x": [2]}).to_parquet(targets["table"], index=False)
    artifacts = {
        "marginal_mean_score_outcome_gap": runner.relative_artifact_descriptor(
            targets["table"], repo_root=tmp_path
        ),
        "endpoint_reason_census": runner.relative_artifact_descriptor(
            targets["endpoint_reason_census"], repo_root=tmp_path
        ),
        "monthly_endpoint_reason_census": runner.relative_artifact_descriptor(
            targets["monthly_endpoint_reason_census"], repo_root=tmp_path
        ),
    }
    summary = json.loads(targets["summary"].read_text(encoding="utf-8"))
    summary["artifacts"] = artifacts
    targets["summary"].write_text(json.dumps(summary), encoding="utf-8")
    summary_descriptor = runner.relative_artifact_descriptor(targets["summary"], repo_root=tmp_path)
    receipt = json.loads(targets["execution_receipt"].read_text(encoding="utf-8"))
    receipt["artifacts"] = artifacts
    receipt["summary"] = summary_descriptor
    targets["execution_receipt"].write_text(json.dumps(receipt), encoding="utf-8")
    receipt_descriptor = runner.relative_artifact_descriptor(
        targets["execution_receipt"], repo_root=tmp_path
    )
    seal = json.loads(targets["execution_seal"].read_text(encoding="utf-8"))
    seal["artifacts"] = artifacts
    seal["summary"] = summary_descriptor
    seal["execution_receipt"] = receipt_descriptor
    targets["execution_seal"].write_text(json.dumps(seal), encoding="utf-8")

    runner.validate_execution_seal(config, repo_root=tmp_path)
    with pytest.raises(RuntimeError, match="differs from recomputation"):
        runner.validate_recomputed_scientific_outputs(
            config,
            result=result,
            source_seal={"composite_sha256": "c" * 64},
            source_audit={},
            protocol_commit="a" * 40,
            repo_root=tmp_path,
        )


def test_source_dvc_directory_descriptor_rehashes_every_file(tmp_path: Path) -> None:
    runner = _runner()
    directory = tmp_path / "data/processed/experiments/ijds_audit" / runner.RUN_TAG
    directory.mkdir(parents=True)
    for index in range(3):
        (directory / f"f{index}.bin").write_bytes(f"value-{index}".encode())
    observed = runner._dvc_directory_descriptor(directory)
    expected = {
        "md5": "8ac93946d6c2b0a555990adea28cafe9.dir",
        "size": 21,
        "nfiles": 3,
        "hash": "md5",
        "file_inventory_sha256": (
            "a40fcc800f6b2a1e96623e235cc5e94f9268ec2f266277b3bac97404b55b0cb6"
        ),
    }
    _require(observed == expected, f"DVC directory serialization changed: {observed}")
    (directory / "f0.bin").write_bytes(b"bit-flip")
    mutated = runner._dvc_directory_descriptor(directory)
    _require(mutated["md5"] != expected["md5"], "source DVC bit flip escaped directory MD5")
    _require(
        mutated["file_inventory_sha256"] != expected["file_inventory_sha256"],
        "source DVC bit flip escaped SHA-256 inventory",
    )


def test_artifact_diff_and_git_blobs_require_exactly_six_outputs(tmp_path: Path) -> None:
    runner = _runner()
    config = _config()
    _init_git(tmp_path)
    (tmp_path / "protocol.txt").write_text("locked", encoding="utf-8")
    _git(tmp_path, "add", "protocol.txt")
    _git(tmp_path, "commit", "-m", "protocol")
    protocol_commit = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "data/processed/experiments/ijds_audit").mkdir(parents=True)
    (tmp_path / "models/experiments/ijds_audit").mkdir(parents=True)
    _data, _model, targets = runner.output_targets(config, repo_root=tmp_path)
    for index, path in enumerate(targets.values()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"aggregate-{index}".encode())
    relative_targets = tuple(
        sorted(path.relative_to(tmp_path).as_posix() for path in targets.values())
    )
    _git(tmp_path, "add", "-f", *relative_targets)
    _git(tmp_path, "commit", "-m", "six aggregate artifacts")
    artifact_commit = _git(tmp_path, "rev-parse", "HEAD")
    runner._require_direct_child_artifact_commit(
        protocol_commit=protocol_commit,
        artifact_commit=artifact_commit,
        repo_root=tmp_path,
    )
    observed = runner._artifact_diff_paths(
        protocol_commit=protocol_commit,
        artifact_commit=artifact_commit,
        repo_root=tmp_path,
    )
    _require(observed == relative_targets, "six-file Git-native artifact diff changed")
    descriptors = runner._git_bound_artifact_descriptors(
        targets, artifact_commit=artifact_commit, repo_root=tmp_path
    )
    _require(len(descriptors) == 6, "not all Git-native artifacts were blob-bound")
    first = next(iter(targets.values()))
    original = first.read_bytes()
    first.write_bytes(original + b"mutation")
    with pytest.raises(RuntimeError, match="differs from its artifact-tag Git blob"):
        runner._git_bound_artifact_descriptors(
            targets, artifact_commit=artifact_commit, repo_root=tmp_path
        )
    first.write_bytes(original)
    (tmp_path / ".gitignore").write_text("extra\n", encoding="utf-8")
    _git(tmp_path, "add", ".gitignore")
    _git(tmp_path, "commit", "-m", "extra")
    extra_commit = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="direct single-parent child"):
        runner._require_direct_child_artifact_commit(
            protocol_commit=protocol_commit,
            artifact_commit=extra_commit,
            repo_root=tmp_path,
        )
    with_extra = runner._artifact_diff_paths(
        protocol_commit=protocol_commit,
        artifact_commit=extra_commit,
        repo_root=tmp_path,
    )
    _require(".gitignore" in with_extra, "artifact diff hid an extra tracked path")
