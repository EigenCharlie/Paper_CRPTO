# Secrets, remotes and local credentials

This public repository should be safe to push to GitHub without real
credentials. Only templates belong in Git.

## Files

- Commit: `.env.example`, `.env.local.example`, `.github/workflows/*`.
- Do not commit: `.env`, `.env.*` except examples, `.dvc/config.local`,
  `.claude/settings.local.json`, cloud keys, private keys, local tokens.

## Required variables

Use `.env.example` as the canonical list. The most common values are:

- `DAGSHUB_OWNER=EigenCharlie94`, `DAGSHUB_USER=EigenCharlie94`,
  `DAGSHUB_REPO=Paper_CRPTO`
- `DAGSHUB_TOKEN` or `DAGSHUB_USER_TOKEN`
- `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`,
  `MLFLOW_TRACKING_PASSWORD`
- `CRPTO_DATA_DIR`, `CRPTO_MODELS_DIR`, `CRPTO_DUCKDB_PATH`
- `OPTUNA_STORAGE` when using persistent Optuna studies

## Standalone remotes

CRPTO no longer points to the parent DagsHub project. The committed DVC remote
is:

```text
https://dagshub.com/EigenCharlie94/Paper_CRPTO.s3
```

The MLflow tracking URI is:

```text
https://dagshub.com/EigenCharlie94/Paper_CRPTO.mlflow
```

The old old upstream GitHub remote (`EigenCharlie94/Lending-Club-End-to-End`) may still be
mentioned in learning/provenance notes, but it must not appear in active
runtime config, `.env.example`, DVC config or GitHub Actions secrets.

## GitHub Actions secrets

For CI with DVC/MLflow enabled, configure these in GitHub repository settings,
not in files:

- `DAGSHUB_TOKEN`
- `DAGSHUB_USER_TOKEN`
- `MLFLOW_TRACKING_USERNAME`
- `MLFLOW_TRACKING_PASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL` if using an
  S3-compatible DVC remote

The default workflows avoid pulling large DVC artifacts. They validate the
book, metadata, and artifact-independent tests. Full artifact tests should run
locally or in CI only after a DVC remote is configured.

## GitHub security settings

For `EigenCharlie/Paper_CRPTO`, keep these enabled in repository settings:

- Dependency graph and Dependabot security updates.
- Secret scanning.
- Optional branch protection on `main` if the project becomes multi-author.
  In the current single-author academic mode, `lint` and `book-publish` run on
  push, while `tests-full` is manually triggered before journal milestones.

`dependency-review` requires the Dependency graph. If GitHub reports the
repository as unsupported, enable it in Settings -> Security and analysis
before merging dependency PRs.

## Windows-native environment

The official local environment for this standalone repository is Windows
PowerShell with `.venv/Scripts`.

Use:

```powershell
uv venv
uv sync --extra dev --extra search
```

Do not set custom Python/Quarto environment overrides for normal work. `uv run`
selects the project venv and `uv run -- quarto ...` provides the right Python
context for Quarto renders.
