#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/mnt/c/Users/carlos/Documents/Paper_CRPTO"
RUN_TAG="${RUN_TAG:-champion-reopen-2026-06-19__hpo-wave1}"
N_TRIALS="${N_TRIALS:-96}"
SEED="${SEED:-42}"
TABPREP_SEED="${TABPREP_SEED:-42}"
CASES="${CASES:-pool93,pool93_business80,pool93_woe,pooltop72_tab60,pooltop80_tab90,pooltop93_tab120,pooltop80_business80,pooltop72_business80}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_TAG}"
LOG_PATH="${LOG_DIR}/hpo_wave1.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

{
  echo "TMUX_START $(date -Is) cwd=$(pwd)"
  echo "RUN_TAG=${RUN_TAG} N_TRIALS=${N_TRIALS} SEED=${SEED} CASES=${CASES}"
} | tee -a "${LOG_PATH}"

set +e
.venv-champion-search/bin/python -u scripts/experiments/run_champion_reopen_hpo.py \
  --config configs/experiments/champion_reopen.yaml \
  --run-tag "${RUN_TAG}" \
  --cases "${CASES}" \
  --seed "${SEED}" \
  --tabprep-seed "${TABPREP_SEED}" \
  --n-trials "${N_TRIALS}" \
  --full-data \
  --resume \
  2>&1 | tee -a "${LOG_PATH}"
code="${PIPESTATUS[0]}"
set -e

echo "TMUX_EXIT ${code} $(date -Is)" | tee -a "${LOG_PATH}"
exit "${code}"
