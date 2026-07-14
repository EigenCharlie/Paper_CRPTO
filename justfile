# CRPTO task runner — cross-platform via `just`.
# Install: https://github.com/casey/just  (or `winget install Casey.Just` on Windows)

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
set dotenv-load

# --- Setup ---------------------------------------------------------------

# Full setup including SPO (pyepo + torch) extras
default: help

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
    uv run mypy src scripts tests

# Fast type checker from Astral. Daily active-scope use remains advisory while
# ty matures; the clean full scope is blocking in the final submission gate.
type-advisory:
    @uv run python scripts/run_ty_advisory.py --scope active

type-advisory-full:
    @uv run python scripts/run_ty_advisory.py --scope full --fail-on-diagnostics --output reports/ci/ty-advisory-full.txt

complexity-report:
    uvx radon cc src scripts -s -n C --exclude "scripts/archive/*"

api-docs-core:
    uv run --with pdoc pdoc src.ijds_audit.geometry src.ijds_audit.portfolio src.ijds_audit.evaluation src.ijds_challengers.frontier src.ijds_challengers.evaluation --docformat google --output-directory reports/api-docs --no-browser

hooks-check:
    uv run pre-commit validate-config
    uvx prek validate-config .pre-commit-config.yaml

# Fast active-manuscript smoke. This is read-only with respect to paper evidence.
smoke-active:
    uv run pytest tests/test_publication_integrity.py tests/test_ijds_active_claim_sync.py tests/test_publication_targets.py -q

# Historical champion/book integrity remains separate from the active IJDS capsule.
historical-integrity:
    uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q

smoke: smoke-active historical-integrity

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

ijds-evidence:
    uv run python scripts/build_ijds_binary_geometry_frontier_v4_evidence.py

# Pre-freeze robustness evidence. This does not replace the active V4 manifest.
ijds-rolling-origin-evidence:
    uv run python scripts/build_ijds_rolling_origin_stability_evidence.py

ijds-rolling-origin-check:
    uv run pytest -q tests/test_ijds_rolling_origin_protocol.py tests/test_ijds_rolling_origin_evidence.py

# Locked synthetic mechanism experiment; never empirical sign validation.
ijds-decision-active-simulation:
    uv run python scripts/experiments/run_ijds_decision_active_simulation.py

ijds-decision-active-check:
    uv run pytest -q tests/test_ijds_decision_active_simulation.py

ijds-decision-active-evidence:
    uv run python scripts/build_ijds_decision_active_evidence.py
    uv run pytest -q tests/test_ijds_decision_active_evidence.py

ijds-policy-support-tie-audit:
    uv run python scripts/experiments/run_ijds_policy_support_tie_audit.py

ijds-policy-support-tie-check:
    uv run pytest -q tests/test_ijds_policy_support_tie_audit.py

ijds-policy-support-tie-evidence:
    uv run python scripts/build_ijds_policy_support_tie_evidence.py
    uv run pytest -q tests/test_ijds_policy_support_tie_evidence.py

# Locked two-ruler challenger; V1c is outcome-free and cannot evaluate outcomes.
ijds-normalized-objective-frontier-v1c-freeze:
    uv run python scripts/experiments/run_ijds_normalized_objective_frontier.py

ijds-normalized-objective-frontier-v1c-check:
    uv run pytest -q tests/test_ijds_normalized_objective_frontier.py

# Post-freeze V2 verifies V1c hashes before its single archive-outcome join.
ijds-normalized-objective-frontier-v2-evaluate:
    uv run python scripts/experiments/run_ijds_normalized_objective_frontier_v2.py

ijds-normalized-objective-frontier-v2-check:
    uv run pytest -q tests/test_ijds_normalized_objective_frontier_v2.py

ijds-historical-v1-v3-evidence:
    uv run python scripts/build_ijds_fixed_taxonomy_c2_evidence.py

# Historical P1/C1 evidence remains reproducible but is not paper-facing.
ijds-historical-p1-c1-evidence:
    uv run python scripts/build_ijds_maturity_safe_evidence.py
    uv run python scripts/build_ijds_comparator_stringency_evidence.py

# Historical compact-v7 evidence retained for provenance only.
ijds-historical-v7-evidence:
    uv run python scripts/build_ijds_calibration_selected_evidence.py

# Explicit methodology replays. These write only to versioned experiment paths.
ijds-exact-alpha:
    uv run python scripts/experiments/run_ijds_exact_alpha_grid_challenger.py --config configs/experiments/champion_reopen_ijds_exact_alpha_grid_v1.yaml

ijds-policy-challenger:
    uv run python scripts/experiments/run_ijds_calibration_selected_policy_challenger.py --config configs/experiments/champion_reopen_ijds_calibration_selected_endpoint28_v7.yaml

ijds-historical-v7-replay: ijds-exact-alpha ijds-policy-challenger ijds-historical-v7-evidence

# Read-only active-capsule gate over the current evidence and all three immutable
# freeze/evaluation pairs represented by the twelve active DVC pointers.
ijds-active-check: publication-integrity ijds-normalized-objective-frontier-v1c-check ijds-normalized-objective-frontier-v2-check
    uv run pytest -q tests/test_ijds_anonymity.py tests/test_ijds_active_claim_sync.py tests/test_ijds_v4_claim_sync.py tests/test_publication_targets.py tests/test_publication_integrity.py tests/test_submission_preview_layout.py tests/test_supplement_table_sync.py tests/test_scripts/test_compile_ijds_submission.py tests/test_scripts/test_manage_ijds_dvc_capsule.py tests/test_ijds_audit_core.py tests/test_ijds_audit/test_raw_data_audit.py tests/test_ijds_audit/test_credit_controls.py

# Explicit replay rebuilds only paper-facing evidence. Run `ijds-active-check`
# after the manuscript surfaces have also been rebuilt.
ijds-active-replay: ijds-evidence

# V4 is intentionally two-phase. There is no combined target: the outcome-free
# artifacts must be inspected and hashed before archive outcomes are joined.
ijds-v4-freeze CONFIG:
    uv run python scripts/experiments/run_ijds_binary_geometry_frontier_v4.py freeze --config "{{ CONFIG }}"

ijds-v4-evaluate CONFIG:
    uv run python scripts/experiments/run_ijds_binary_geometry_frontier_v4.py evaluate --config "{{ CONFIG }}"

ijds-v4-code-check:
    uv run pytest tests/test_ijds_audit_core.py -q
    uv run ruff check src/ijds_audit scripts/experiments/run_ijds_binary_geometry_frontier_v4.py tests/test_ijds_audit_core.py
    uv run mypy src/ijds_audit scripts/experiments/run_ijds_binary_geometry_frontier_v4.py tests/test_ijds_audit_core.py

ijds-pull:
    uv run python scripts/manage_ijds_dvc_capsule.py pull

ijds-dvc-status:
    uv run python scripts/manage_ijds_dvc_capsule.py status

ijds-dvc-remote-status:
    uv run python scripts/manage_ijds_dvc_capsule.py status --cloud

# Current paper export path. Legacy champion/book exports remain explicit below.
paper-export:
    just ijds-active-replay
    just paper-submission

historical-paper-export: tables figures evidence journal-package book

# IJDS-oriented manuscript body (HTML writing preview).
paper-ijds:
    uv run -- quarto render paper/CRPTO_ijds.qmd --to html --no-execute

# IJDS-oriented online supplement (HTML writing preview).
paper-ijds-supplement:
    uv run -- quarto render paper/supplement_ijds.qmd --to html --no-execute

# Render the current submission-shaped manuscript surfaces.
paper-submission: paper-ijds paper-ijds-supplement

# Generate the official INFORMS TeX from the canonical QMD source.
paper-submission-tex:
    uv run python scripts/build_ijds_submission_tex.py

paper-submission-tex-check:
    uv run python scripts/build_ijds_submission_tex.py --check

# Compile and scan the official INFORMS/IJDS LaTeX handoff draft.
paper-submission-official: paper-submission-tex
    @uv run python scripts/compile_ijds_submission.py --skip-render

paper-submission-official-scan:
    @uv run python scripts/compile_ijds_submission.py --scan-only

# Explicitly write all active paper outputs in causal order. This is not a freeze.
submission-build:
    just ijds-active-replay
    just paper-submission
    just paper-submission-official
    just paper-submission-pdf

# Read-only final local gate over already-built outputs.
submission-check: ijds-active-check paper-submission-tex-check paper-submission-official-scan lint type-check type-advisory-full test validate-champion-strict

# Build, then verify. Submission freeze remains a separate human decision.
submission-closeout: submission-build submission-check

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
    uv run -- quarto render book --to html --no-execute

book-pdf:
    @echo "CRPTO.pdf is intentionally not maintained as a routine artifact. Use paper-submission-pdf for IJDS PDFs; create a curated thesis PDF later from selected sections."

book-all: book
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

# Historical champion/book DVC exports; never part of the active IJDS capsule.
historical-dvc-paper:
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

# Submission closeout requires every manifest-listed artifact to be present;
# the ordinary target remains useful in partial development checkouts.
validate-champion-strict:
    $env:CRPTO_REQUIRE_DVC_ARTIFACTS = "1"; uv run pytest tests/test_manifest_regression.py -q

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
    uv run optuna-dashboard "journal:{{ FILE }}"

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
    uv run duckdb "{{ FILE }}"

# Optional Datasette UI. Requires the duckdb-datasette plugin; if it is not
# installed this recipe fails fast with a helpful pointer.
datasette FILE="data/processed/crpto.duckdb":
    @uv run python -c "import datasette" 2>&1 || echo "Run: uv pip install datasette datasette-duckdb"
    uv run datasette serve --plugins-dir=. -i "{{ FILE }}"

# --- Safe one-shot release gate -----------------------------------------

all: submission-check
    @echo "Read-only checks complete: no evidence replay or protected stage was executed."

# --- Help ---------------------------------------------------------------

help:
    @just --list
