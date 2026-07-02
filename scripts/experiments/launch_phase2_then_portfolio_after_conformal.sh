#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
HPO_RUN_TAG="${HPO_RUN_TAG:-champion-reopen-2026-06-19__hpo-wave1}"
CASE_NAME="${CASE_NAME:-pool93}"
CONFORMAL_RUN_TAG="${CONFORMAL_RUN_TAG:-${HPO_RUN_TAG}__claim-max-incremental-conformal__${CASE_NAME}__conformal}"
UPSTREAM_RUN_TAG="${UPSTREAM_RUN_TAG:-${HPO_RUN_TAG}__${CASE_NAME}__seed42}"
PROFILE="${PROFILE:-search_conformal_claim_max}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv-champion-search/bin/python}"
CUOPT_PYTHON="${CUOPT_PYTHON:-/home/eigenlinux/.venvs/crpto-cuopt-26-6/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-300}"
PHASE1_WORKERS="${PHASE1_WORKERS:-3}"
THREADS_PER_WORKER="${THREADS_PER_WORKER:-2}"
RUN_LABEL="${RUN_LABEL:-${HPO_RUN_TAG}__${CASE_NAME}__cuopt-frontier-26-06}"
ORCHESTRATOR_LABEL="${ORCHESTRATOR_LABEL:-${CONFORMAL_RUN_TAG}__phase2-then-cuopt}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${ORCHESTRATOR_LABEL}"
LOG_PATH="${LOG_DIR}/phase2_then_cuopt.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

STATUS_PATH="${REPO_ROOT}/models/conformal_gap/${CONFORMAL_RUN_TAG}/conformal_reopen_status.json"

phase2_ready() {
  "${PYTHON_BIN}" - <<PY
import json
from pathlib import Path

status_path = Path("${STATUS_PATH}")
if not status_path.exists():
    raise SystemExit(1)
payload = json.loads(status_path.read_text(encoding="utf-8"))
phase2 = payload.get("phase2") or {}
search_path = phase2.get("search_path")
ok = bool(phase2.get("always_evaluate")) and bool(search_path) and Path(search_path).exists()
raise SystemExit(0 if ok else 1)
PY
}

final_intervals_path() {
  "${PYTHON_BIN}" - <<PY
import json
from pathlib import Path

repo = Path("${REPO_ROOT}")
payload = json.loads(Path("${STATUS_PATH}").read_text(encoding="utf-8"))
namespace = str(payload.get("final_namespace", "")).strip()
if not namespace:
    raise SystemExit(1)
candidate = repo / "data" / "processed" / "conformal_gap" / namespace / "conformal_intervals_mondrian.parquet"
if not candidate.exists():
    raise SystemExit(1)
print(candidate)
PY
}

{
  echo "PHASE2_THEN_CUOPT_WAIT_START $(date -Is)"
  echo "run_tag=${CONFORMAL_RUN_TAG}"
  echo "upstream=${UPSTREAM_RUN_TAG}"
  echo "status=${STATUS_PATH}"
  while [[ ! -f "${STATUS_PATH}" ]]; do
    echo "PHASE2_THEN_CUOPT_WAITING_CONFORMAL $(date -Is)"
    sleep "${POLL_SECONDS}"
  done

  if phase2_ready; then
    echo "PHASE2_ALREADY_EVALUATED $(date -Is)"
  else
    echo "PHASE2_EVALUATION_START $(date -Is)"
    OMP_NUM_THREADS="${THREADS_PER_WORKER}" \
    MKL_NUM_THREADS="${THREADS_PER_WORKER}" \
    OPENBLAS_NUM_THREADS="${THREADS_PER_WORKER}" \
    NUMEXPR_NUM_THREADS="${THREADS_PER_WORKER}" \
    PYTHONUNBUFFERED=1 \
    nice -n 10 "${PYTHON_BIN}" -u scripts/search/run_conformal_reopen_search.py \
      --run-tag "${CONFORMAL_RUN_TAG}" \
      --pipeline-profile "${PROFILE}" \
      --upstream-canonical-run-tag "${UPSTREAM_RUN_TAG}" \
      --phase1-workers "${PHASE1_WORKERS}" \
      --force-phase2
    echo "PHASE2_EVALUATION_DONE $(date -Is)"
  fi

  interval_path="$(final_intervals_path)"
  echo "CUOPT_AFTER_PHASE2_INTERVALS_READY $(date -Is) ${interval_path}"
  CONFORMAL_INTERVALS_PATH="${interval_path}" \
  CUOPT_PYTHON="${CUOPT_PYTHON}" \
  RUN_LABEL="${RUN_LABEL}" \
  scripts/experiments/launch_portfolio_cuopt_frontier_26_06.sh
  code="$?"
  echo "PHASE2_THEN_CUOPT_EXIT ${code} $(date -Is)"
  exit "${code}"
} >> "${LOG_PATH}" 2>&1
