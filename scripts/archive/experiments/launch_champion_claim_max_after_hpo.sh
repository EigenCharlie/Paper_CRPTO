#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/mnt/c/Users/carlos/Documents/Paper_CRPTO"
HPO_RUN_TAG="${HPO_RUN_TAG:-champion-reopen-2026-06-19__hpo-wave1}"
RUN_TAG="${RUN_TAG:-${HPO_RUN_TAG}__claim-max-downstream}"
TOP_K="${TOP_K:-4}"
MANDATORY_CASES="${MANDATORY_CASES:-pool93}"
PAPER_FACING_TOP_K="${PAPER_FACING_TOP_K:-3}"
SKIP_CASES="${SKIP_CASES:-}"
POLL_SECONDS="${POLL_SECONDS:-300}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_TAG}"
LOG_PATH="${LOG_DIR}/claim_max_downstream.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

{
  echo "TMUX_START $(date -Is) cwd=$(pwd)"
  echo "HPO_RUN_TAG=${HPO_RUN_TAG} RUN_TAG=${RUN_TAG} TOP_K=${TOP_K} MANDATORY_CASES=${MANDATORY_CASES} PAPER_FACING_TOP_K=${PAPER_FACING_TOP_K} SKIP_CASES=${SKIP_CASES}"
} | tee -a "${LOG_PATH}"

extra_args=()
if [[ -n "${SKIP_CASES}" ]]; then
  extra_args+=(--skip-cases "${SKIP_CASES}")
fi

set +e
.venv-champion-search/bin/python -u scripts/experiments/run_champion_claim_max_downstream.py \
  --hpo-run-tag "${HPO_RUN_TAG}" \
  --run-tag "${RUN_TAG}" \
  --top-k "${TOP_K}" \
  --mandatory-cases "${MANDATORY_CASES}" \
  --paper-facing-top-k "${PAPER_FACING_TOP_K}" \
  --wait-for-hpo-complete \
  --poll-seconds "${POLL_SECONDS}" \
  "${extra_args[@]}" \
  2>&1 | tee -a "${LOG_PATH}"
code="${PIPESTATUS[0]}"
set -e

echo "TMUX_EXIT ${code} $(date -Is)" | tee -a "${LOG_PATH}"
exit "${code}"
