# CRPTO task runner — cross-platform via `just`.
# Install: https://github.com/casey/just  (or `winget install Casey.Just` on Windows)

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
set dotenv-load := true

# --- Setup ---------------------------------------------------------------

# Full setup including SPO (pyepo + torch) extras
default: setup

setup:
    uv sync --extra dev --extra search --extra spo

# Lighter setup without SPO/torch
setup-base:
    uv sync --extra dev --extra search

setup-spo:
    uv sync --extra dev --extra search --extra spo

# --- Quality gates -------------------------------------------------------

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff check . --fix
    uv run ruff format .

type-check:
    uv run mypy src scripts

# Fast type checker from Astral. Daily active-scope use remains advisory while
# ty matures; the clean full scope is blocking in the final submission gate.
type-advisory:
    @uv run python scripts/run_ty_advisory.py --scope active

type-advisory-full:
    @uv run python scripts/run_ty_advisory.py --scope full --fail-on-diagnostics --output reports/ci/ty-advisory-full.txt

complexity-report:
    uvx radon cc src scripts -s -n D

api-docs-core:
    uv run --with pdoc pdoc src.optimization.portfolio_model src.models.calibration src.evaluation.backtesting src.evaluation.fairness --docformat google --output-directory reports/api-docs --no-browser

hooks-check:
    uv run pre-commit validate-config
    uvx prek validate-config .pre-commit-config.yaml

# Fast smoke: paper-final guardrails + Quarto book guardrails
smoke:
    uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py tests/test_publication_integrity.py -q

publication-integrity:
    uv run python scripts/check_publication_integrity.py

test:
    uv run pytest -q

test-fast:
    uv run pytest -q -m "not slow"

# --- Paper outputs (safe — do NOT touch the frozen champion) -------------

tables:
    uv run python scripts/export_crpto_tables.py

figures:
    uv run python scripts/generate_crpto_figures.py --paper crpto

evidence:
    uv run python scripts/analyze_crpto_evidence.py

journal-package:
    uv run python scripts/build_crpto_journal_package.py

paper-export: tables figures evidence journal-package book

# IJDS-oriented manuscript body (HTML writing preview).
paper-ijds:
    uv run -- quarto render paper/CRPTO_ijds.qmd --to html --no-execute

# IJDS-oriented online supplement (HTML writing preview).
paper-ijds-supplement:
    uv run -- quarto render paper/supplement_ijds.qmd --to html --no-execute

# Render the current submission-shaped manuscript surfaces.
paper-submission: paper-ijds paper-ijds-supplement

# Compile and scan the official INFORMS/IJDS LaTeX handoff draft.
paper-submission-official:
    @uv run python scripts/compile_ijds_submission.py

# Final local IJDS gate before freezing or uploading.
submission-check: publication-integrity lint type-check type-advisory-full smoke validate-champion paper-submission paper-submission-official

# IJDS-oriented manuscript body (local HTML-print PDF verification draft).
paper-ijds-pdf:
    uv run python scripts/render_submission_pdf_previews.py --body-only

# IJDS-oriented online supplement (local HTML-print PDF verification draft).
paper-ijds-supplement-pdf:
    uv run python scripts/render_submission_pdf_previews.py --supplement-only

# Render local PDF verification drafts for the submission surfaces.
paper-submission-pdf: paper-submission
    uv run python scripts/render_submission_pdf_previews.py

# --- Quarto book ---------------------------------------------------------

book:
    uv run python scripts/write_book_build_info.py
    uv run -- quarto render book --to html

book-pdf:
    @echo "CRPTO.pdf is intentionally not maintained as a routine artifact. Use paper-submission-pdf for IJDS PDFs; create a curated thesis PDF later from selected sections."

book-all: book
    uv run python scripts/write_book_build_info.py
    @echo "book-all currently means HTML book only; full thesis PDF is deferred until the thesis section set and APA layout are fixed."

book-preview:
    uv run -- quarto preview book

book-clean:
    uv run python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('book/_book', 'book/_freeze', 'book/.quarto')]; print('Quarto cache cleaned.')"

# --- DVC -----------------------------------------------------------------

dvc-status:
    uv run dvc status

dvc-dag:
    uv run dvc dag --md

# Regenerates downstream paper artefacts only (does NOT touch champion stages).
dvc-paper:
    uv run dvc repro --single-item crpto.paper.export_tables
    uv run dvc repro --single-item crpto.paper.evidence
    uv run dvc repro --single-item crpto.paper.journal_package
    uv run dvc repro --single-item crpto.paper.tail_satisficing_audit
    uv run dvc repro --single-item crpto.paper.figures
    uv run dvc repro --single-item crpto.book.render

# --- dbt -----------------------------------------------------------------

dbt-parse:
    uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project

dbt-test:
    uv run dbt test --project-dir dbt_project --profiles-dir dbt_project

dbt-build:
    uv run dbt build --project-dir dbt_project --profiles-dir dbt_project

# --- Governance ---------------------------------------------------------

validate-champion:
    uv run pytest tests/test_manifest_regression.py -q

drift-gate:
    $env:CRPTO_RUN_CHAMPION_DRIFT = "1"; uv run pytest tests/test_models/test_conformal_mapie_drift.py -q -s

bound-audit:
    uv run pytest tests/test_scripts/test_build_bound_tightening_audit.py tests/test_scripts/test_run_portfolio_bound_aware_search.py tests/test_scripts/test_run_portfolio_bound_exact_eval.py -q

mrm-card:
    uv run python -c "print('use /crpto-mrm-card via Claude Code or write the script')"

pipeline-state:
    uv run python -c "from src.utils.pipeline_state import load_pipeline_state; import json; s = load_pipeline_state(); print(json.dumps({'missing': s.missing, 'namespaces': list(s.state.keys())}, indent=2))"

params-check:
    uv run python scripts/build_params_view.py --check

# --- Optuna Dashboard ---------------------------------------------------

# Local HPO dashboard. Defaults to the journal file used by make_study(); pass
# OPTUNA_DASH_FILE to point at a different study.
optuna-dashboard FILE="data/processed/optuna/pd_catboost_hpo.log":
    uv run optuna-dashboard "journal:{{FILE}}"

# --- Dbt extras ---------------------------------------------------------

dbt-deps:
    uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project

dbt-docs:
    uv run dbt docs generate --project-dir dbt_project --profiles-dir dbt_project
    uv run dbt docs serve --project-dir dbt_project --profiles-dir dbt_project --port 8088

# --- DuckDB CLI ---------------------------------------------------------

# Interactive DuckDB session over the CRPTO warehouse. Useful for MRM
# reviewers who want to inspect the marts without booting a Quarto chunk.
duckdb FILE="data/processed/crpto.duckdb":
    uv run duckdb "{{FILE}}"

# Optional Datasette UI. Requires the duckdb-datasette plugin; if it is not
# installed this recipe fails fast with a helpful pointer.
datasette FILE="data/processed/crpto.duckdb":
    @uv run python -c "import datasette" 2>&1 || echo "Run: uv pip install datasette datasette-duckdb"
    uv run datasette serve --plugins-dir=. -i "{{FILE}}"

# --- One-shot orchestrator ----------------------------------------------

all:
    uv run python scripts/run_crpto_pipeline.py

# --- Help ---------------------------------------------------------------

help:
    @just --list
