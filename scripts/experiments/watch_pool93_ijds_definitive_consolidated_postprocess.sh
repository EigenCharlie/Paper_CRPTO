#!/usr/bin/env bash
set -euo pipefail

TRIGGER_RUN_TAG="${1:?trigger run tag required}"
POLL_SECONDS="${2:-300}"
OUTPUT_TAG="${3:-champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_PATH="${ROOT_DIR}/models/experiments/champion_reopen/${TRIGGER_RUN_TAG}/portfolio/runtime_status.json"
LOG_DIR="${ROOT_DIR}/reports/run_logs/champion_reopen/${TRIGGER_RUN_TAG}"
LOG_PATH="${LOG_DIR}/consolidated_definitive_postprocess.log"

mkdir -p "${LOG_DIR}"

while true; do
  if "${ROOT_DIR}/.venv-champion-search/bin/python" - "${STATUS_PATH}" <<'PY'
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
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_consolidated_frontier.py" \
    --output-tag "${OUTPUT_TAG}" \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-expanded-refine \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-micro-refine \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-bound-closure \
    --run-tag champion-reopen-2026-06-19__pool93__ijds-claim-bound-floor-closure \
    --run-tag "${TRIGGER_RUN_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_consolidated_governance.py" \
    --consolidated-tag "${OUTPUT_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_body_allocation_audit.py" \
    --consolidated-tag "${OUTPUT_TAG}" \
    --threads 1 \
    --solver-backend highspy
  date -Is
} >> "${LOG_PATH}" 2>&1
