#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
HPO_RUN_TAG="${HPO_RUN_TAG:-champion-reopen-2026-06-19__hpo-wave1}"
CASE_NAME="${CASE_NAME:-pool93}"
CONFORMAL_RUN_TAG="${CONFORMAL_RUN_TAG:-${HPO_RUN_TAG}__claim-max-incremental-conformal__${CASE_NAME}__conformal}"
UPSTREAM_RUN_TAG="${UPSTREAM_RUN_TAG:-${HPO_RUN_TAG}__${CASE_NAME}__seed42}"
PROFILE="${PROFILE:-search_conformal_claim_max}"
PHASE1_WORKERS="${PHASE1_WORKERS:-3}"
THREADS_PER_WORKER="${THREADS_PER_WORKER:-2}"
POLL_SECONDS="${POLL_SECONDS:-300}"
SERIAL_TMUX_SESSION="${SERIAL_TMUX_SESSION:-champion_claim_max_incremental_conformal}"
RUN_LABEL="${RUN_LABEL:-${CONFORMAL_RUN_TAG}__parallel-phase1}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_LABEL}"
LOG_PATH="${LOG_DIR}/parallel_conformal.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

FIRST_NAMESPACE="${CONFORMAL_RUN_TAG}__phase1__calfrac-0.50__holdout-0.20__seed-42"
FIRST_RESULT="${REPO_ROOT}/models/conformal_gap/${FIRST_NAMESPACE}/conformal_results_mondrian.pkl"

{
  echo "PARALLEL_CONFORMAL_WAIT_START $(date -Is)"
  echo "run_tag=${CONFORMAL_RUN_TAG}"
  echo "upstream=${UPSTREAM_RUN_TAG}"
  echo "first_checkpoint=${FIRST_RESULT}"
  while [[ ! -f "${FIRST_RESULT}" ]]; do
    echo "PARALLEL_CONFORMAL_WAITING_FIRST_CHECKPOINT $(date -Is)"
    sleep "${POLL_SECONDS}"
  done

  echo "PARALLEL_CONFORMAL_FIRST_CHECKPOINT_READY $(date -Is)"
  if tmux has-session -t "${SERIAL_TMUX_SESSION}" 2>/dev/null; then
    echo "PARALLEL_CONFORMAL_STOPPING_SERIAL_TMUX ${SERIAL_TMUX_SESSION} $(date -Is)"
    tmux kill-session -t "${SERIAL_TMUX_SESSION}" || true
  fi

  echo "PARALLEL_CONFORMAL_COMMAND_START $(date -Is)"
  OMP_NUM_THREADS="${THREADS_PER_WORKER}" \
  MKL_NUM_THREADS="${THREADS_PER_WORKER}" \
  OPENBLAS_NUM_THREADS="${THREADS_PER_WORKER}" \
  NUMEXPR_NUM_THREADS="${THREADS_PER_WORKER}" \
  PYTHONUNBUFFERED=1 \
  nice -n 10 .venv-champion-search/bin/python -u scripts/search/run_conformal_reopen_search.py \
    --run-tag "${CONFORMAL_RUN_TAG}" \
    --pipeline-profile "${PROFILE}" \
    --upstream-canonical-run-tag "${UPSTREAM_RUN_TAG}" \
    --phase1-workers "${PHASE1_WORKERS}"
  code="$?"
  echo "PARALLEL_CONFORMAL_COMMAND_EXIT ${code} $(date -Is)"
  exit "${code}"
} >> "${LOG_PATH}" 2>&1
