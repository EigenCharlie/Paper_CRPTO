#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
RUN_LABEL="${RUN_LABEL:?Set RUN_LABEL to the frontier portfolio run label}"
EXACT_PYTHON="${EXACT_PYTHON:-${REPO_ROOT}/.venv-champion-search/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-60}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-0}"
CONTEXT_PATH="${CONTEXT_PATH:-${REPO_ROOT}/models/experiments/champion_reopen/${RUN_LABEL}/portfolio/portfolio_bound_aware_exact_context.json}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_LABEL}"
LOG_PATH="${LOG_DIR}/exact_after_frontier.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

started_epoch="$(date +%s)"

{
  echo "EXACT_AFTER_FRONTIER_WAIT_START $(date -Is)"
  echo "RUN_LABEL=${RUN_LABEL}"
  echo "CONTEXT_PATH=${CONTEXT_PATH}"
  echo "EXACT_PYTHON=${EXACT_PYTHON}"
} >> "${LOG_PATH}" 2>&1

while [[ ! -f "${CONTEXT_PATH}" ]]; do
  now_epoch="$(date +%s)"
  elapsed="$((now_epoch - started_epoch))"
  if [[ "${WAIT_TIMEOUT_SECONDS}" != "0" && "${elapsed}" -ge "${WAIT_TIMEOUT_SECONDS}" ]]; then
    echo "EXACT_AFTER_FRONTIER_TIMEOUT elapsed=${elapsed} $(date -Is)" >> "${LOG_PATH}" 2>&1
    exit 124
  fi
  echo "EXACT_AFTER_FRONTIER_WAITING elapsed=${elapsed} $(date -Is)" >> "${LOG_PATH}" 2>&1
  sleep "${POLL_SECONDS}"
done

echo "EXACT_AFTER_FRONTIER_START $(date -Is)" >> "${LOG_PATH}" 2>&1
OMP_NUM_THREADS="${EXACT_THREADS:-8}" \
MKL_NUM_THREADS="${EXACT_THREADS:-8}" \
OPENBLAS_NUM_THREADS="${EXACT_THREADS:-8}" \
NUMEXPR_NUM_THREADS="${EXACT_THREADS:-8}" \
EXACT_THREADS="${EXACT_THREADS:-8}" \
PYTHONUNBUFFERED=1 \
"${EXACT_PYTHON}" -u scripts/search/run_portfolio_bound_exact_eval.py \
  --context-path "${CONTEXT_PATH}" >> "${LOG_PATH}" 2>&1
code="$?"
echo "EXACT_AFTER_FRONTIER_EXIT ${code} $(date -Is)" >> "${LOG_PATH}" 2>&1
exit "${code}"
