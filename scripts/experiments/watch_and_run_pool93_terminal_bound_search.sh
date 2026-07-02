#!/usr/bin/env bash
set -euo pipefail

TRIGGER_RUN_TAG="${1:-champion-reopen-2026-06-19__pool93__ijds-claim-bound-floor-closure}"
TERMINAL_RUN_TAG="${2:-champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal}"
POLL_SECONDS="${3:-180}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TRIGGER_STATUS="${ROOT_DIR}/models/experiments/champion_reopen/${TRIGGER_RUN_TAG}/portfolio/runtime_status.json"
TERMINAL_LOG_DIR="${ROOT_DIR}/reports/run_logs/champion_reopen/${TERMINAL_RUN_TAG}"
TERMINAL_LOG="${TERMINAL_LOG_DIR}/local_exact_refine_bound_terminal12.log"
POSTPROCESS_LOG="${TERMINAL_LOG_DIR}/postprocess_and_consolidate.log"

mkdir -p "${TERMINAL_LOG_DIR}"

while true; do
  if "${ROOT_DIR}/.venv-champion-search/bin/python" - "${TRIGGER_STATUS}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
status = json.loads(path.read_text(encoding="utf-8"))
complete = status.get("phase") == "selection_complete" and status.get("state") == "completed"
raise SystemExit(0 if complete else 1)
PY
  then
    break
  fi
  sleep "${POLL_SECONDS}"
done

{
  date -Is
  echo "Starting terminal bound search after ${TRIGGER_RUN_TAG}"
} >> "${POSTPROCESS_LOG}" 2>&1

PYTHONUNBUFFERED=1 HIGHS_NATIVE_FALLBACK_SCIPY=1 \
  "${ROOT_DIR}/.venv-champion-search/bin/python" -u \
  "${ROOT_DIR}/scripts/search/run_pool93_ijds_local_refinement.py" \
  --run-tag "${TERMINAL_RUN_TAG}" \
  --profile claim_bound_terminal \
  --exact-threads 1 \
  --parallel-workers 12 \
  --checkpoint-every 25 \
  >> "${TERMINAL_LOG}" 2>&1

{
  date -Is
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_claim_governance.py" \
    --run-tag "${TERMINAL_RUN_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_frontier_claim_table.py" \
    --run-tag "${TERMINAL_RUN_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_consolidated_frontier.py" \
    --output-tag champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-expanded-refine \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-micro-refine \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-bound-closure \
    --run-tag "${TRIGGER_RUN_TAG}" \
    --run-tag "${TERMINAL_RUN_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_consolidated_governance.py" \
    --consolidated-tag champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_body_allocation_audit.py" \
    --consolidated-tag champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive \
    --threads 1 \
    --solver-backend highspy
  date -Is
} >> "${POSTPROCESS_LOG}" 2>&1
