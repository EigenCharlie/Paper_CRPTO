# Current CRPTO/IJDS task surface. All recipes are Windows-compatible via `just`.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
set dotenv-load

default: help

# --- Environment and quality ---------------------------------------------

setup:
    uv sync --extra dev

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff check . --fix
    uv run ruff format .

type-check:
    uv run mypy src scripts tests

type-check-fast:
    @uv run python scripts/run_ty_advisory.py --scope active --fail-on-diagnostics --no-report

hooks-check:
    uv run pre-commit validate-config
    uvx prek validate-config .pre-commit-config.yaml

complexity-report:
    uv run python scripts/run_complexity_report.py

test:
    uv run pytest -q

smoke:
    uv run pytest tests/test_publication_integrity.py tests/test_ijds_active_claim_sync.py tests/test_publication_targets.py -q

# Read-only regression gate for the current PD/conformal implementation and
# every paper-facing numerical contract. It does not execute a scientific run.
drift-gate: publication-integrity
    uv run pytest -q tests/test_models/test_binary_conformal_guardrail.py tests/test_ijds_audit_core.py tests/test_ijds_active_claim_sync.py tests/test_ijds_v4_claim_sync.py tests/test_ijds_audit/test_credit_controls.py tests/test_ijds_audit/test_endpoint_recovery.py tests/test_ijds_audit/test_evaluation_outcome_contracts.py

# --- Active evidence and protocol entrypoints -----------------------------

publication-integrity:
    uv run python scripts/check_publication_integrity.py

ijds-evidence:
    uv run python scripts/build_ijds_binary_geometry_frontier_v4_evidence.py

ijds-tie-evidence:
    uv run python scripts/build_ijds_policy_support_tie_evidence.py

ijds-v4 PHASE CONFIG:
    uv run python scripts/experiments/run_ijds_binary_geometry_frontier_v4.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-credit-controls PHASE CONFIG:
    uv run python scripts/experiments/run_ijds_credit_risk_controls.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-two-ruler-freeze CONFIG="configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1c.yaml":
    uv run python scripts/experiments/run_ijds_normalized_objective_frontier.py --config "{{ CONFIG }}"

ijds-two-ruler-evaluate CONFIG:
    uv run python scripts/experiments/run_ijds_normalized_objective_frontier_v2.py --config "{{ CONFIG }}"

ijds-raw-data-audit CONFIG="configs/experiments/ijds_raw_data_contract_2026-07-14_v2.yaml":
    uv run python scripts/experiments/run_ijds_raw_data_audit.py --config "{{ CONFIG }}"

ijds-label-lag CONFIG="configs/experiments/ijds_label_lag_sensitivity_2026-07-14.yaml":
    uv run python scripts/experiments/run_ijds_label_lag_sensitivity.py --config "{{ CONFIG }}"

ijds-fit-label-completion PHASE CONFIG="configs/experiments/ijds_fit_label_completion_sensitivity_2026-07-16.yaml":
    uv run python scripts/experiments/run_ijds_fit_label_completion_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-endpoint-sensitivity CONFIG="configs/experiments/ijds_endpoint_availability_sensitivity_2026-07-14.yaml":
    uv run python scripts/experiments/run_ijds_endpoint_availability_sensitivity.py --config "{{ CONFIG }}"

ijds-missingness PHASE CONFIG="configs/experiments/ijds_missingness_sensitivity_2026-07-15_v3.yaml":
    uv run python scripts/experiments/run_ijds_missingness_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-structure PHASE CONFIG="configs/experiments/ijds_portfolio_structure_sensitivity_2026-07-15_v6.yaml":
    uv run python scripts/experiments/run_ijds_portfolio_structure_sensitivity.py --phase "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-allocation-granularity PHASE CONFIG="configs/experiments/ijds_allocation_granularity_sensitivity_2026-07-16.yaml":
    uv run python scripts/experiments/run_ijds_allocation_granularity_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-tie-audit CONFIG="configs/experiments/ijds_policy_support_tie_audit_2026-07-12.yaml":
    uv run python scripts/experiments/run_ijds_policy_support_tie_audit.py --config "{{ CONFIG }}"

# Read-only gate over all registered lineages and current paper surfaces.
ijds-active-check: publication-integrity
    uv run pytest -q tests/test_ijds_anonymity.py tests/test_ijds_active_claim_sync.py tests/test_ijds_v4_claim_sync.py tests/test_ijds_rolling_origin_protocol.py tests/test_publication_targets.py tests/test_submission_preview_layout.py tests/test_supplement_table_sync.py
    uv run pytest -q tests/test_ijds_audit tests/test_ijds_audit_core.py tests/test_ijds_normalized_objective_frontier.py tests/test_ijds_normalized_objective_frontier_v2.py tests/test_ijds_policy_support_tie_audit.py tests/test_ijds_policy_support_tie_evidence.py

# --- DVC capsule ----------------------------------------------------------

ijds-pull:
    uv run python scripts/manage_ijds_dvc_capsule.py pull

ijds-push:
    uv run python scripts/manage_ijds_dvc_capsule.py push

ijds-dvc-status:
    uv run python scripts/manage_ijds_dvc_capsule.py status

ijds-dvc-remote-status:
    uv run python scripts/manage_ijds_dvc_capsule.py status --cloud

ijds-dvc-verify-remote:
    uv run python scripts/manage_ijds_dvc_capsule.py verify-remote

# --- Manuscript -----------------------------------------------------------

paper-body:
    uv run -- quarto render paper/CRPTO_ijds.qmd --to html --no-execute

paper-supplement:
    uv run -- quarto render paper/supplement_ijds.qmd --to html --no-execute

paper-tex:
    uv run python scripts/build_ijds_submission_tex.py

paper-tex-check:
    uv run python scripts/build_ijds_submission_tex.py --check

paper-official: paper-tex
    @uv run python scripts/compile_ijds_submission.py --skip-render

paper-official-scan:
    @uv run python scripts/compile_ijds_submission.py --scan-only

paper-pdf-audit:
    @uv run python scripts/inspect_ijds_pdfs.py

paper-previews: paper-body paper-supplement
    uv run python scripts/render_submission_pdf_previews.py

submission-build: ijds-tie-evidence ijds-evidence paper-body paper-supplement paper-official paper-previews

validate-champion:
    uv run pytest tests/test_manifest_regression.py -q

validate-champion-strict:
    $env:CRPTO_REQUIRE_DVC_ARTIFACTS = "1"; uv run pytest tests/test_manifest_regression.py -q

submission-check: ijds-active-check drift-gate paper-tex-check paper-official-scan paper-pdf-audit lint type-check type-check-fast validate-champion-strict

submission-closeout: submission-build submission-check ijds-dvc-verify-remote

all: submission-check
    @echo "Read-only checks complete: no evidence-generating or protected stage was executed."

help:
    @just --list
