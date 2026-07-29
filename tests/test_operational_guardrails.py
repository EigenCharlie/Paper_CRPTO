from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
import yaml


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_runtime_python_has_no_optimized_away_assert_guards() -> None:
    config = yaml.safe_load(_text("configs/crpto_publication_targets.yaml"))
    surface = config["active_scientific_contract"]["active_code_surface"]
    quarantine = config["executed_quarantine_capsule"]
    stopped = config["stopped_tagged_candidate_capsule"]
    superseded = config["superseded_protocol_capsule"]
    declared_scripts = {
        *surface["paper_pipeline"],
        *surface["protocol_entrypoints"],
        *surface["support_tools"],
        *quarantine["replay_entrypoints"],
        *stopped["replay_entrypoints"],
        *superseded["protocol_entrypoints"],
    }
    runtime_paths = {
        *Path("src").rglob("*.py"),
        *(Path(value) for value in declared_scripts if Path(value).suffix.lower() == ".py"),
    }
    offenders: list[str] = []
    for path in sorted(runtime_paths):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                offenders.append(f"{path.as_posix()}:{node.lineno}")

    if offenders:
        pytest.fail(
            "Runtime checks must raise explicit exceptions because the audited "
            f"Calibre runtime removes assert statements under optimization: {offenders}"
        )


def test_one_shot_alias_is_read_only_and_current_only() -> None:
    justfile = _text("justfile")

    assert "all: test hooks-check dependency-audit submission-check" in justfile
    assert "submission-check: ijds-active-check drift-gate" in justfile
    assert "run_crpto_pipeline.py" not in justfile
    assert "dvc repro" not in justfile


def test_page_budget_is_opt_in_only_at_submission_freeze() -> None:
    justfile = _text("justfile")

    assert re.search(r"(?m)^paper-pdf-audit:\s*\n\s*@.*inspect_ijds_pdfs\.py\s*$", justfile)
    assert re.search(
        r"(?m)^paper-pdf-audit-freeze:\s*\n"
        r"\s*@.*inspect_ijds_pdfs\.py --enforce-freeze-page-limit\s*$",
        justfile,
    )
    submission = re.search(r"(?m)^submission-check: (.+)$", justfile)
    freeze = re.search(r"(?m)^submission-freeze-check: (.+)$", justfile)
    ordinary = re.search(r"(?m)^all: (.+)$", justfile)
    assert submission and freeze and ordinary
    assert "paper-pdf-audit " in f"{submission.group(1)} "
    assert "paper-pdf-audit-freeze" not in submission.group(1)
    assert "paper-pdf-audit-freeze" in freeze.group(1)
    assert "submission-check" in ordinary.group(1)
    assert "submission-freeze-check" not in ordinary.group(1)
    assert "paper-pdf-audit-dev" not in justfile
    assert "submission-check-dev" not in justfile


def test_active_drift_gate_is_read_only_and_claim_bound() -> None:
    justfile = _text("justfile")

    assert "drift-gate: publication-integrity" in justfile
    assert "tests/test_models/test_binary_conformal_guardrail.py" in justfile
    assert "tests/test_ijds_active_claim_sync.py" in justfile
    assert "CRPTO_RUN_CHAMPION_DRIFT" not in justfile


def test_compatibility_surfaces_are_not_active_recipes() -> None:
    justfile = _text("justfile").lower()
    recipes = set(re.findall(r"(?m)^([a-z0-9_-]+)(?:\s+[^:]*)?:", justfile))

    for retired_recipe in ("book", "dbt", "notebook"):
        assert retired_recipe not in recipes
    for retired_command in ("scripts/search", "dvc repro"):
        assert retired_command not in justfile
    assert {"companion-build", "companion-html", "companion-pdf"}.issubset(recipes)


def test_publication_contract_names_every_executable_protocol() -> None:
    config = yaml.safe_load(_text("configs/crpto_publication_targets.yaml"))
    surface = config["active_scientific_contract"]["active_code_surface"]
    quarantine = config["executed_quarantine_capsule"]
    stopped = config["stopped_tagged_candidate_capsule"]
    superseded = config["superseded_protocol_capsule"]
    active_protocols = set(surface["protocol_entrypoints"])
    quarantine_protocols = set(quarantine["replay_entrypoints"])
    stopped_protocols = set(stopped["replay_entrypoints"])
    superseded_protocols = set(superseded["protocol_entrypoints"])
    assert active_protocols.isdisjoint(quarantine_protocols)
    assert active_protocols.isdisjoint(stopped_protocols)
    assert active_protocols.isdisjoint(superseded_protocols)
    assert quarantine_protocols.isdisjoint(stopped_protocols)
    assert quarantine_protocols.isdisjoint(superseded_protocols)
    assert stopped_protocols.isdisjoint(superseded_protocols)
    protocol_entrypoints = {
        *active_protocols,
        *quarantine_protocols,
        *stopped_protocols,
        *superseded_protocols,
    }
    declared = {
        *surface["paper_pipeline"],
        *protocol_entrypoints,
        *surface["support_tools"],
    }
    actual_experiments = {
        path.as_posix()
        for path in Path("scripts/experiments").glob("*.py")
        if path.name != "__init__.py"
    }

    unclassified = sorted(actual_experiments.difference(protocol_entrypoints))
    multiply_classified = sorted(
        (active_protocols & quarantine_protocols)
        | (active_protocols & stopped_protocols)
        | (active_protocols & superseded_protocols)
        | (quarantine_protocols & stopped_protocols)
        | (quarantine_protocols & superseded_protocols)
        | (stopped_protocols & superseded_protocols)
    )
    missing = sorted(protocol_entrypoints.difference(actual_experiments))
    assert not unclassified, f"unclassified experiment entrypoints: {unclassified}"
    assert not multiply_classified, f"multiply classified entrypoints: {multiply_classified}"
    assert not missing, f"classified experiment entrypoints are missing: {missing}"
    assert all(Path(path).is_file() for path in declared)


def test_extra_scripts_are_only_sealed_path_bound_compatibility() -> None:
    config = yaml.safe_load(_text("configs/crpto_publication_targets.yaml"))
    surface = config["active_scientific_contract"]["active_code_surface"]
    quarantine = config["executed_quarantine_capsule"]
    stopped = config["stopped_tagged_candidate_capsule"]
    superseded = config["superseded_protocol_capsule"]
    active = {
        *surface["paper_pipeline"],
        *surface["protocol_entrypoints"],
        *quarantine["replay_entrypoints"],
        *stopped["replay_entrypoints"],
        *superseded["protocol_entrypoints"],
        *surface["support_tools"],
    }
    dvc = yaml.safe_load(_text("dvc.yaml"))
    path_bound = {
        item
        for stage in dvc["stages"].values()
        for item in stage.get("deps", [])
        if isinstance(item, str) and item.startswith("scripts/") and item.endswith(".py")
    }
    manifest = json.loads(_text("EXTRACTION_MANIFEST.json"))
    path_bound.update(
        path
        for path in manifest["critical_hashes"]
        if path.startswith("scripts/") and path.endswith(".py")
    )
    actual = {
        path.as_posix() for path in Path("scripts").rglob("*.py") if path.name != "__init__.py"
    }

    assert actual == active | path_bound


def test_clean_clone_workflow_runs_the_publication_capsule_and_suite() -> None:
    workflow = yaml.safe_load(_text(".github/workflows/tests-full.yml"))
    job = workflow["jobs"]["clean-clone"]
    assert job["runs-on"] == "windows-latest"
    steps = {step.get("name", step.get("uses")): step for step in job["steps"]}
    checkout = next(step for step in job["steps"] if step.get("uses") == "actions/checkout@v5")
    assert checkout["with"] == {"fetch-depth": 0, "fetch-tags": True}
    assert steps["Install just"]["with"]["just-version"] == "1.56.0"
    assert steps["Install Quarto"]["with"]["version"] == "1.9.38"
    assert steps["Pull publication DVC capsule"]["run"] == "just ijds-pull-publication"
    derived = steps["Rebuild derived policy-support evidence"]["run"]
    assert "just ijds-tie-evidence ijds-policy-support-evidence" in derived
    for path in (
        "reports/crpto/ijds_policy_support_tie_evidence.json",
        "reports/crpto/ijds_policy_support_optimal_face_evidence.json",
        "reports/crpto/tables/crpto_ijds_policy_family_domain.csv",
        "reports/crpto/tables/crpto_ijds_gamma_endpoint_audit.csv",
        "reports/crpto/tables/crpto_ijds_comparator_support_domain.csv",
        "docs/research/ijds_policy_support_tie_results_2026-07-12.md",
    ):
        assert path in derived
    rebuilt = steps["Rebuild publication evidence from the pulled DVC capsule"]["run"]
    assert "--stage-only staging/ci-active-evidence" in rebuilt
    assert "--verify-stage-against-canonical staging/ci-active-evidence" in rebuilt
    assert steps["Full author tests"]["run"] == "just coverage"
    assert steps["Dependency audit"]["run"] == "just dependency-audit"
    assert steps["Active implementation and evidence drift gate"]["run"] == "just drift-gate"
    assert "PYTHONOPTIMIZE" in steps["Optimized-runtime guard"]["run"]


def test_lint_workflow_installs_only_quality_tools() -> None:
    workflow = _text(".github/workflows/lint.yml")

    assert "uv sync --only-group quality --locked" in workflow
    assert "uv run --no-sync ruff check ." in workflow
    assert "uv sync --group dev" not in workflow


def test_dependency_audit_is_cross_platform() -> None:
    justfile = _text("justfile")

    assert "uv run --locked --with pip-audit==2.10.1 pip-audit" in justfile
    assert r".venv\Lib\site-packages" not in justfile


def test_strict_manifest_gate_has_windows_and_posix_environment_prefixes() -> None:
    justfile = _text("justfile")

    assert 'if os() == "windows"' in justfile
    assert "$env:CRPTO_REQUIRE_DVC_ARTIFACTS = '1';" in justfile
    assert '"CRPTO_REQUIRE_DVC_ARTIFACTS=1"' in justfile
    assert "{{ strict-manifest-prefix }} uv run --locked pytest" in justfile


def test_type_gates_cover_product_and_test_code() -> None:
    justfile = _text("justfile")
    pyproject = _text("pyproject.toml")

    assert "uv run --locked mypy src scripts tests" in justfile
    assert 'files = ["src", "scripts", "tests"]' in pyproject


def test_runtime_and_author_dependencies_exclude_retired_solver_layers() -> None:
    pyproject = _text("pyproject.toml")
    runtime, groups = pyproject.split("[dependency-groups]", maxsplit=1)

    assert '"dvc[s3]>=3.60"' not in runtime
    assert "repro = [" in groups
    assert "pyomo" not in pyproject.lower()
    assert "cuopt" not in pyproject.lower()


def test_paper_owns_its_bibliography_and_citation_style() -> None:
    body = _text("paper/CRPTO_ijds.qmd")
    supplement = _text("paper/supplement_ijds.qmd")
    template = _text("paper/submission/informs-pandoc-template.tex")

    assert "bibliography: references.bib" in body
    assert "csl: apa.csl" in body
    assert "bibliography: references.bib" in supplement
    assert "csl: apa.csl" in supplement
    assert r"\bibliography{../references}" in template


def test_marginal_gap_publication_loader_never_conditions_on_result_sign() -> None:
    builder = _text("scripts/build_ijds_binary_geometry_frontier_v4_evidence.py")

    assert "table[upper_column].lt(0.0).all()" not in builder
    assert "table[lower_column].gt(0.0).all()" not in builder
    assert 'reporting.get("result_sign_is_stop_condition") is not False' in builder
