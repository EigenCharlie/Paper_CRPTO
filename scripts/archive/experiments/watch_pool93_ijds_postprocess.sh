#!/usr/bin/env bash
set -euo pipefail

RUN_TAG="${1:?run tag required}"
POLL_SECONDS="${2:-300}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_PATH="${ROOT_DIR}/models/experiments/champion_reopen/${RUN_TAG}/portfolio/runtime_status.json"
LOG_DIR="${ROOT_DIR}/reports/run_logs/champion_reopen/${RUN_TAG}"
LOG_PATH="${LOG_DIR}/postprocess.log"

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
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_claim_governance.py" \
    --run-tag "${RUN_TAG}"
  "${ROOT_DIR}/.venv-champion-search/bin/python" \
    "${ROOT_DIR}/scripts/search/build_pool93_ijds_frontier_claim_table.py" \
    --run-tag "${RUN_TAG}"
  date -Is
} >> "${LOG_PATH}" 2>&1
