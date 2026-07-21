from __future__ import annotations

import json
from pathlib import Path

import yaml


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_one_shot_alias_is_read_only_and_current_only() -> None:
    justfile = _text("justfile")

    assert "all: test hooks-check dependency-audit submission-check" in justfile
    assert "submission-check: ijds-active-check drift-gate" in justfile
    assert "run_crpto_pipeline.py" not in justfile
    assert "dvc repro" not in justfile


def test_active_drift_gate_is_read_only_and_claim_bound() -> None:
    justfile = _text("justfile")

    assert "drift-gate: publication-integrity" in justfile
    assert "tests/test_models/test_binary_conformal_guardrail.py" in justfile
    assert "tests/test_ijds_active_claim_sync.py" in justfile
    assert "CRPTO_RUN_CHAMPION_DRIFT" not in justfile


def test_compatibility_surfaces_are_not_active_recipes() -> None:
    justfile = _text("justfile").lower()

    for retired_recipe in ("book", "dbt", "notebook", "scripts/search", "dvc repro"):
        assert retired_recipe not in justfile


def test_publication_contract_names_every_executable_protocol() -> None:
    config = yaml.safe_load(_text("configs/crpto_publication_targets.yaml"))
    surface = config["active_scientific_contract"]["active_code_surface"]
    declared = {
        *surface["paper_pipeline"],
        *surface["protocol_entrypoints"],
        *surface["support_tools"],
    }
    actual_experiments = {
        path.as_posix()
        for path in Path("scripts/experiments").glob("*.py")
        if path.name != "__init__.py"
    }

    assert actual_experiments == set(surface["protocol_entrypoints"])
    assert all(Path(path).is_file() for path in declared)


def test_extra_scripts_are_only_sealed_path_bound_compatibility() -> None:
    config = yaml.safe_load(_text("configs/crpto_publication_targets.yaml"))
    surface = config["active_scientific_contract"]["active_code_surface"]
    active = {
        *surface["paper_pipeline"],
        *surface["protocol_entrypoints"],
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


def test_manual_full_workflow_runs_the_collected_suite() -> None:
    workflow = _text(".github/workflows/tests-full.yml")
    assert "fetch-depth: 0" in workflow
    assert "fetch-tags: true" in workflow
    assert "uses: extractions/setup-just@v4" in workflow
    assert 'just-version: "1.56.0"' in workflow
    assert "uses: quarto-dev/quarto-actions/setup@v2" in workflow
    assert 'version: "1.9.38"' in workflow
    assert "run: just coverage" in workflow
    assert "run: just dependency-audit" in workflow
    assert "run: just drift-gate" in workflow


def test_lint_workflow_installs_only_quality_tools() -> None:
    workflow = _text(".github/workflows/lint.yml")

    assert "uv sync --only-group quality --frozen" in workflow
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


def test_runtime_dependencies_exclude_reproducibility_and_compatibility_tools() -> None:
    pyproject = _text("pyproject.toml")
    runtime, groups = pyproject.split("[dependency-groups]", maxsplit=1)

    assert '"dvc[s3]>=3.60"' not in runtime
    assert '"pyomo>=6.10"' not in runtime
    assert "repro = [" in groups
    assert "compat = [" in groups


def test_paper_owns_its_bibliography_and_citation_style() -> None:
    body = _text("paper/CRPTO_ijds.qmd")
    supplement = _text("paper/supplement_ijds.qmd")
    template = _text("paper/submission/informs-pandoc-template.tex")

    assert "bibliography: references.bib" in body
    assert "csl: apa.csl" in body
    assert "bibliography: references.bib" in supplement
    assert "csl: apa.csl" in supplement
    assert r"\bibliography{../references}" in template
