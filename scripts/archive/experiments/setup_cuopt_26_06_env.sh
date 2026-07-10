#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/mnt/c/Users/carlos/Documents/Paper_CRPTO}"
CUOPT_ENV_DIR="${CUOPT_ENV_DIR:-/home/eigenlinux/.venvs/crpto-cuopt-26-6}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

cd "${REPO_ROOT}"

if command -v uv >/dev/null 2>&1; then
  uv venv --seed --python "${PYTHON_BIN}" "${CUOPT_ENV_DIR}"
else
  "${PYTHON_BIN}" -m venv "${CUOPT_ENV_DIR}"
fi

if ! "${CUOPT_ENV_DIR}/bin/python" -m pip --version >/dev/null 2>&1; then
  "${CUOPT_ENV_DIR}/bin/python" -m ensurepip --upgrade
fi
"${CUOPT_ENV_DIR}/bin/python" -m pip install --upgrade pip wheel setuptools
"${CUOPT_ENV_DIR}/bin/python" -m pip install \
  --extra-index-url=https://pypi.nvidia.com \
  "cuopt-cu13==26.6.*"
"${CUOPT_ENV_DIR}/bin/python" -m pip install \
  --no-deps -e .
"${CUOPT_ENV_DIR}/bin/python" -m pip install \
  "pandas>=2.3,<4" \
  "numpy>=2.0,<3" \
  "pyarrow>=18" \
  "scipy>=1.14,<2" \
  "pyyaml>=6.0" \
  "loguru>=0.7" \
  "pyomo>=6.10" \
  "highspy>=1.10" \
  "tqdm>=4.66"

"${CUOPT_ENV_DIR}/bin/python" - <<'PY'
import json
import sys

modules = {}
for name in ["cuopt", "cudf", "cupy", "pandas", "pyomo", "highspy"]:
    module = __import__(name)
    modules[name] = getattr(module, "__version__", "ok")

print(json.dumps({"python": sys.executable, "modules": modules}, indent=2))
PY

echo "CUOPT_ENV_READY ${CUOPT_ENV_DIR}"
