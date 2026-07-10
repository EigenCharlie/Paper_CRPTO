from __future__ import annotations

from pathlib import Path


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_one_shot_alias_cannot_run_retired_canonical_pipeline() -> None:
    justfile = _text("justfile")
    assert "all: submission-check" in justfile
    assert "uv run python scripts/run_crpto_pipeline.py" not in justfile

    runner = _text("scripts/run_crpto_pipeline.py")
    assert "is retired because it rewrote protected artifacts" in runner
    assert "train_pd_model.py" not in runner
    assert "generate_conformal_intervals.py" not in runner
    assert "optimize_portfolio.py" not in runner


def test_book_render_defaults_are_no_execute_and_source_stable() -> None:
    justfile = _text("justfile")
    dvc = _text("dvc.yaml")
    build_info = _text("book/includes/_build-info.qmd")

    assert "quarto render book --to html --no-execute" in justfile
    assert "quarto render book --to html --no-execute" in dvc
    assert "write_book_build_info.py" not in justfile
    assert "write_book_build_info.py" not in dvc
    assert "Rama:" not in build_info
    assert "Actualizado:" not in build_info
    assert "TARGET.write_text" not in _text("scripts/write_book_build_info.py")


def test_historical_dvc_dataset_explicitly_opts_into_resolved_only_replay() -> None:
    """Keep the frozen canonical lane compatible with the maturity-safe default."""
    dvc = _text("dvc.yaml")

    dataset_stage = dvc.split("crpto.data.splits:", maxsplit=1)[0]
    assert "src/data/make_dataset.py" in dataset_stage
    assert "--legacy-resolved-only" in dataset_stage


def test_manual_full_workflow_runs_the_collected_suite() -> None:
    workflow = _text(".github/workflows/tests-full.yml")
    assert "- name: Full author tests\n        run: uv run pytest -q" in workflow
    assert "tests/test_optimization/ \\" not in workflow


def test_mypy_gate_covers_product_and_test_code() -> None:
    justfile = _text("justfile")
    pyproject = _text("pyproject.toml")

    assert "uv run mypy src scripts tests" in justfile
    assert 'files = ["src", "scripts", "tests"]' in pyproject


def test_example_data_root_matches_dbt_processed_artifacts() -> None:
    env_example = _text(".env.example")
    assert "CRPTO_DATA_DIR=data/processed" in env_example
    assert "CRPTO_DATA_DIR=data\n" not in env_example
