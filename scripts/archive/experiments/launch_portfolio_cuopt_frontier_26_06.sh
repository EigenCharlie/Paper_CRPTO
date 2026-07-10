#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
CUOPT_PYTHON="${CUOPT_PYTHON:-/home/eigenlinux/.venvs/crpto-cuopt-26-6/bin/python}"
EXACT_PYTHON="${EXACT_PYTHON:-${REPO_ROOT}/.venv-champion-search/bin/python}"
PROFILE_PATH="${PROFILE_PATH:-configs/profiles/search_portfolio_cuopt_frontier_26_06.yaml}"
CONFORMAL_INTERVALS_PATH="${CONFORMAL_INTERVALS_PATH:?Set CONFORMAL_INTERVALS_PATH to conformal_intervals_mondrian.parquet}"
RUN_LABEL="${RUN_LABEL:-champion-reopen-cuopt-frontier-26-06-$(date +%Y%m%d-%H%M%S)}"
RUN_EXACT_AFTER_FRONTIER="${RUN_EXACT_AFTER_FRONTIER:-true}"
LOG_DIR="${REPO_ROOT}/reports/run_logs/champion_reopen/${RUN_LABEL}"
LOG_PATH="${LOG_DIR}/cuopt_frontier.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_ROOT}"

{
  echo "CUOPT_FRONTIER_START $(date -Is)"
  echo "CUOPT_PYTHON=${CUOPT_PYTHON}"
  echo "PROFILE_PATH=${PROFILE_PATH}"
  echo "CONFORMAL_INTERVALS_PATH=${CONFORMAL_INTERVALS_PATH}"
  echo "RUN_LABEL=${RUN_LABEL}"
  echo "RUN_EXACT_AFTER_FRONTIER=${RUN_EXACT_AFTER_FRONTIER}"
} | tee -a "${LOG_PATH}"

"${CUOPT_PYTHON}" - <<'PY' 2>&1 | tee -a "${LOG_PATH}"
import os
import subprocess
from pathlib import Path

import yaml

from scripts.experiments.run_champion_claim_max_downstream import _portfolio_command

repo = Path(os.environ.get("REPO_ROOT", "/mnt/c/Users/carlos/Documents/Paper_CRPTO"))
profile_path = repo / os.environ.get(
    "PROFILE_PATH", "configs/profiles/search_portfolio_cuopt_frontier_26_06.yaml"
)
run_label = os.environ["RUN_LABEL"]
conformal_path = Path(os.environ["CONFORMAL_INTERVALS_PATH"])
cuopt_python = os.environ["CUOPT_PYTHON"]

profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
profile.setdefault("execution", {})["python_executable"] = cuopt_python

output_dir = (
    repo
    / "data"
    / "processed"
    / "experiments"
    / "champion_reopen"
    / run_label
    / "portfolio"
)
model_dir = (
    repo
    / "models"
    / "experiments"
    / "champion_reopen"
    / run_label
    / "portfolio"
)

cmd = _portfolio_command(
    portfolio_profile=profile,
    conformal_intervals_path=conformal_path,
    run_label=run_label,
    output_dir=output_dir,
    model_dir=model_dir,
)
print("COMMAND", " ".join(map(str, cmd)), flush=True)
raise SystemExit(subprocess.run(cmd, cwd=str(repo), check=False).returncode)
PY
code="${PIPESTATUS[0]}"

echo "CUOPT_FRONTIER_EXIT ${code} $(date -Is)" | tee -a "${LOG_PATH}"
if [[ "${code}" == "0" && "${RUN_EXACT_AFTER_FRONTIER}" == "true" ]]; then
  echo "CUOPT_FRONTIER_EXACT_HANDOFF $(date -Is)" | tee -a "${LOG_PATH}"
  RUN_LABEL="${RUN_LABEL}" \
  EXACT_PYTHON="${EXACT_PYTHON}" \
  scripts/experiments/launch_portfolio_exact_after_frontier.sh
  code="$?"
  echo "CUOPT_FRONTIER_EXACT_EXIT ${code} $(date -Is)" | tee -a "${LOG_PATH}"
fi
exit "${code}"
