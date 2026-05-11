# Secrets, remotes and local credentials

This repository should be safe to push to GitHub without real credentials.
Only templates belong in Git.

## Files

- Commit: `.env.example`, `.env.local.example`, `.github/workflows/*`.
- Do not commit: `.env`, `.env.*` except examples, `.dvc/config.local`,
  `.claude/settings.local.json`, cloud keys, private keys, local tokens.

## Required variables

Use `.env.example` as the canonical list. The most common values are:

- `DAGSHUB_OWNER`, `DAGSHUB_USER`, `DAGSHUB_REPO=Paper_CRPTO`
- `DAGSHUB_TOKEN` or `DAGSHUB_USER_TOKEN`
- `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`,
  `MLFLOW_TRACKING_PASSWORD`
- `CRPTO_DATA_DIR`, `CRPTO_MODELS_DIR`, `CRPTO_DUCKDB_PATH`
- `OPTUNA_STORAGE` when using persistent Optuna studies

## GitHub Actions secrets

For a private repo with DVC/MLflow enabled, configure these in GitHub
repository settings, not in files:

- `DAGSHUB_TOKEN`
- `MLFLOW_TRACKING_USERNAME`
- `MLFLOW_TRACKING_PASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL` if using an
  S3-compatible DVC remote

The default workflows avoid pulling large DVC artifacts. They validate the
book, metadata, and artifact-independent tests. Full artifact tests should run
locally or in CI only after a DVC remote is configured.

## WSL and Windows venvs

Do not share one `.venv` between WSL and Windows PowerShell. If you work from
WSL, run:

```bash
export UV_PROJECT_ENVIRONMENT=.venv-wsl
export UV_LINK_MODE=copy
uv sync --extra dev --extra search
```

If you work from Windows PowerShell, use:

```powershell
uv venv
uv sync --extra dev --extra search
```

This prevents WSL `uv run` from replacing a Windows `.venv/Scripts` environment
with a POSIX `.venv/bin` environment.
