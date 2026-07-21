# Current CRPTO/IJDS task surface. All recipes are Windows-compatible via `just`.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
set dotenv-load

default: help

# --- Environment and quality ---------------------------------------------

setup:
    uv sync --group dev --locked

lint:
    uv run --locked ruff check .
    uv run --locked ruff format --check .

fmt:
    uv run --locked ruff check . --fix
    uv run --locked ruff format .

type-check:
    uv run --locked mypy src scripts tests

type-check-fast:
    @uv run --locked python scripts/run_ty_advisory.py --scope active --fail-on-diagnostics --no-report

hooks-check:
    uv run --locked pre-commit validate-config

complexity-report:
    uv run --locked python scripts/run_complexity_report.py

test:
    uv run --locked pytest -q

coverage:
    uv run --locked pytest -q --cov=src --cov-branch --cov-report=term-missing --cov-report=xml

# Known exceptions are documented in docs/security/DEPENDENCY_RISK_REGISTER.md.
# Any advisory not named here fails the audit.
dependency-audit:
    uvx --from pip-audit==2.10.1 pip-audit --path .venv\Lib\site-packages --progress-spinner off --ignore-vuln PYSEC-2026-2447 --ignore-vuln PYSEC-2026-1806 --ignore-vuln PYSEC-2026-1805

smoke:
    uv run --locked pytest tests/test_publication_integrity.py tests/test_ijds_active_claim_sync.py tests/test_publication_targets.py -q

# Read-only regression gate for the current PD/conformal implementation and
# every paper-facing numerical contract. It does not execute a scientific run.
drift-gate: publication-integrity
    uv run --locked pytest -q tests/test_models/test_binary_conformal_guardrail.py tests/test_ijds_audit_core.py tests/test_ijds_active_claim_sync.py tests/test_ijds_v4_claim_sync.py tests/test_ijds_audit/test_credit_controls.py tests/test_ijds_audit/test_endpoint_recovery.py tests/test_ijds_audit/test_evaluation_outcome_contracts.py

# --- Active evidence and protocol entrypoints -----------------------------

publication-integrity:
    uv run --locked python scripts/check_publication_integrity.py

ijds-evidence:
    uv run --locked python scripts/build_ijds_binary_geometry_frontier_v4_evidence.py

ijds-tie-evidence:
    uv run --locked python scripts/build_ijds_policy_support_tie_evidence.py

ijds-v4 PHASE CONFIG:
    uv run --locked python scripts/experiments/run_ijds_binary_geometry_frontier_v4.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-credit-controls PHASE CONFIG:
    uv run --locked python scripts/experiments/run_ijds_credit_risk_controls.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-two-ruler-freeze CONFIG="configs/experiments/ijds_normalized_objective_frontier_2026-07-13_v1c.yaml":
    uv run --locked python scripts/experiments/run_ijds_normalized_objective_frontier.py --config "{{ CONFIG }}"

ijds-two-ruler-evaluate CONFIG:
    uv run --locked python scripts/experiments/run_ijds_normalized_objective_frontier_v2.py --config "{{ CONFIG }}"

ijds-raw-data-audit CONFIG="configs/experiments/ijds_raw_data_contract_2026-07-14_v2.yaml":
    uv run --locked python scripts/experiments/run_ijds_raw_data_audit.py --config "{{ CONFIG }}"

ijds-label-lag CONFIG="configs/experiments/ijds_label_lag_sensitivity_2026-07-14.yaml":
    uv run --locked python scripts/experiments/run_ijds_label_lag_sensitivity.py --config "{{ CONFIG }}"

ijds-fit-label-completion PHASE CONFIG="configs/experiments/ijds_fit_label_completion_sensitivity_2026-07-16.yaml":
    uv run --locked python scripts/experiments/run_ijds_fit_label_completion_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-endpoint-sensitivity CONFIG="configs/experiments/ijds_endpoint_availability_sensitivity_2026-07-14.yaml":
    uv run --locked python scripts/experiments/run_ijds_endpoint_availability_sensitivity.py --config "{{ CONFIG }}"

ijds-missingness PHASE CONFIG="configs/experiments/ijds_missingness_sensitivity_2026-07-15_v3.yaml":
    uv run --locked python scripts/experiments/run_ijds_missingness_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-structure PHASE CONFIG="configs/experiments/ijds_portfolio_structure_sensitivity_2026-07-15_v6.yaml":
    uv run --locked python scripts/experiments/run_ijds_portfolio_structure_sensitivity.py --phase "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-allocation-granularity PHASE CONFIG="configs/experiments/ijds_allocation_granularity_sensitivity_2026-07-16.yaml":
    uv run --locked python scripts/experiments/run_ijds_allocation_granularity_sensitivity.py "{{ PHASE }}" --config "{{ CONFIG }}"

ijds-tie-audit CONFIG="configs/experiments/ijds_policy_support_tie_audit_2026-07-12.yaml":
    uv run --locked python scripts/experiments/run_ijds_policy_support_tie_audit.py --config "{{ CONFIG }}"

# Read-only gate over all registered lineages and current paper surfaces.
ijds-active-check: publication-integrity
    uv run --locked pytest -q tests/test_ijds_anonymity.py tests/test_ijds_active_claim_sync.py tests/test_ijds_v4_claim_sync.py tests/test_ijds_rolling_origin_protocol.py tests/test_publication_targets.py tests/test_submission_preview_layout.py tests/test_supplement_table_sync.py
    uv run --locked pytest -q tests/test_ijds_audit tests/test_ijds_audit_core.py tests/test_ijds_normalized_objective_frontier.py tests/test_ijds_normalized_objective_frontier_v2.py tests/test_ijds_policy_support_tie_audit.py tests/test_ijds_policy_support_tie_evidence.py

# --- DVC capsule ----------------------------------------------------------

ijds-pull:
    uv run --locked python scripts/manage_ijds_dvc_capsule.py pull

ijds-push:
    uv run --locked python scripts/manage_ijds_dvc_capsule.py push

ijds-dvc-status:
    uv run --locked python scripts/manage_ijds_dvc_capsule.py status

ijds-dvc-remote-status:
    uv run --locked python scripts/manage_ijds_dvc_capsule.py status --cloud

ijds-dvc-verify-remote:
    uv run --locked python scripts/manage_ijds_dvc_capsule.py verify-remote

# --- Manuscript -----------------------------------------------------------

paper-body:
    uv run --locked -- quarto render paper/CRPTO_ijds.qmd --to html --no-execute

paper-supplement:
    uv run --locked -- quarto render paper/supplement_ijds.qmd --to html --no-execute

paper-tex:
    uv run --locked python scripts/build_ijds_submission_tex.py

paper-tex-check:
    uv run --locked python scripts/build_ijds_submission_tex.py --check

paper-official: paper-tex
    @uv run --locked python scripts/compile_ijds_submission.py --skip-render

paper-official-scan:
    @uv run --locked python scripts/compile_ijds_submission.py --scan-only

paper-pdf-audit:
    @uv run --locked python scripts/inspect_ijds_pdfs.py

paper-previews: paper-body paper-supplement
    uv run --locked python scripts/render_submission_pdf_previews.py

submission-build: ijds-tie-evidence ijds-evidence paper-body paper-supplement paper-official paper-previews

validate-champion:
    uv run --locked pytest tests/test_manifest_regression.py -q

validate-champion-strict:
    $env:CRPTO_REQUIRE_DVC_ARTIFACTS = "1"; uv run --locked pytest tests/test_manifest_regression.py -q

submission-check: ijds-active-check drift-gate paper-tex-check paper-official-scan paper-pdf-audit lint type-check type-check-fast validate-champion-strict

submission-closeout: test hooks-check dependency-audit submission-build submission-check ijds-dvc-verify-remote

all: test hooks-check dependency-audit submission-check
    @echo "Read-only checks complete: no evidence-generating or protected stage was executed."

help:
    @just --list
