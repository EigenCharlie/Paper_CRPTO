# CRPTO task runner — cross-platform via `just`.
# Install: https://github.com/casey/just  (or `winget install Casey.Just` on Windows)

set windows-shell := ["pwsh.exe", "-NoLogo", "-NoProfile", "-Command"]
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

# Fast smoke: paper-final guardrails + Quarto book guardrails
smoke:
    uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q

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

# --- Quarto book ---------------------------------------------------------

book:
    uv run -- quarto render book --to html

book-pdf:
    uv run -- quarto render book --to pdf

book-all:
    uv run -- quarto render book

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
    uv run dvc repro crpto.paper.export_tables crpto.paper.evidence crpto.paper.journal_package crpto.paper.figures crpto.book.render

# --- dbt -----------------------------------------------------------------

dbt-parse:
    uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project

dbt-test:
    uv run dbt test --project-dir dbt_project --profiles-dir dbt_project

dbt-build:
    uv run dbt build --project-dir dbt_project --profiles-dir dbt_project

# --- Governance ---------------------------------------------------------

validate-champion:
    uv run python -c "import json, hashlib; from pathlib import Path; m=json.loads(Path('EXTRACTION_MANIFEST.json').read_text()); print('manifest loaded:', len(m), 'top-level keys')"

mrm-card:
    uv run python -c "print('use /crpto-mrm-card via Claude Code or write the script')"

pipeline-state:
    uv run python -c "from src.utils.pipeline_state import load_pipeline_state; import json; s = load_pipeline_state(); print(json.dumps({'missing': s.missing, 'namespaces': list(s.state.keys())}, indent=2))"

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

# --- One-shot orchestrator ----------------------------------------------

all:
    uv run python scripts/run_crpto_pipeline.py

# --- Help ---------------------------------------------------------------

help:
    @just --list
