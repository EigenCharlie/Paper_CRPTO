#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
CONFORMAL_RUN_TAG="${CONFORMAL_RUN_TAG:?Set CONFORMAL_RUN_TAG to the conformal reopen run tag}"
CUOPT_PYTHON="${CUOPT_PYTHON:-/home/eigenlinux/.venvs/crpto-cuopt-26-6/bin/python}"
RUN_LABEL="${RUN_LABEL:-${CONFORMAL_RUN_TAG}__cuopt-frontier-26-06}"
POLL_SECONDS="${POLL_SECONDS:-300}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_LABEL}"
LOG_PATH="${LOG_DIR}/wait_and_launch.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

STATUS_PATH="${REPO_ROOT}/models/conformal_gap/${CONFORMAL_RUN_TAG}/conformal_reopen_status.json"

echo "CUOPT_WAIT_START $(date -Is) status=${STATUS_PATH}" | tee -a "${LOG_PATH}"

while true; do
  if [[ -f "${STATUS_PATH}" ]]; then
    interval_path="$("${CUOPT_PYTHON}" - <<PY
import json
from pathlib import Path

status_path = Path("${STATUS_PATH}")
payload = json.loads(status_path.read_text(encoding="utf-8"))
namespace = str(payload.get("final_namespace", "")).strip()
if namespace:
    candidate = Path("${REPO_ROOT}") / "data" / "processed" / "conformal_gap" / namespace / "conformal_intervals_mondrian.parquet"
    if candidate.exists():
        print(candidate)
PY
)"
    if [[ -n "${interval_path}" && -f "${interval_path}" ]]; then
      echo "CUOPT_INTERVALS_READY $(date -Is) ${interval_path}" | tee -a "${LOG_PATH}"
      CONFORMAL_INTERVALS_PATH="${interval_path}" \
      CUOPT_PYTHON="${CUOPT_PYTHON}" \
      RUN_LABEL="${RUN_LABEL}" \
      scripts/experiments/launch_portfolio_cuopt_frontier_26_06.sh
      code="$?"
      echo "CUOPT_WAIT_EXIT ${code} $(date -Is)" | tee -a "${LOG_PATH}"
      exit "${code}"
    fi
  fi
  echo "CUOPT_WAITING $(date -Is)" | tee -a "${LOG_PATH}"
  sleep "${POLL_SECONDS}"
done
