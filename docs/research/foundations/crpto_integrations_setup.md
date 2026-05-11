# CRPTO integrations setup

This note documents integrations for the standalone `Paper_CRPTO` repository.
It intentionally excludes the parent project's Streamlit, FastAPI, causal,
survival, IFRS9 and insights-factory lanes.

## GitHub

Target repository:

```text
EigenCharlie/Paper_CRPTO
```

Repository state:

- Public repo: <https://github.com/EigenCharlie/Paper_CRPTO>
- GitHub Pages target: <https://eigencharlie.github.io/Paper_CRPTO/>
- `main` is protected by `ruff`, `pytest` and `build`.

Publication rules:

1. Commit only Git-safe files: source, docs, Quarto, tables, figures, JSON
   statuses, DVC lock and DVC pointer files.
2. Keep `.env`, `.env.*` except examples, `.dvc/config.local`, raw data,
   processed data, model binaries and local caches out of Git.
3. Review the rendered book before treating GitHub Pages as publication-ready.

## DVC

The local package contains raw and processed artifacts for independent work,
but GitHub should receive only DVC metadata and pointer files. Configure a
remote outside Git before pushing data:

```bash
uv run dvc remote add -d dagshub <remote-url-from-dagshub-or-storage-ui>
uv run dvc push -r dagshub
```

Store credentials in environment variables or `.dvc/config.local`, never in
`.dvc/config`.

## MLflow / DagsHub

Use `.env.example` as the source of truth:

```bash
DAGSHUB_OWNER=EigenCharlie
DAGSHUB_USER=EigenCharlie
DAGSHUB_REPO=Paper_CRPTO
MLFLOW_TRACKING_URI=https://dagshub.com/EigenCharlie/Paper_CRPTO.mlflow
MLFLOW_EXPERIMENT_NAME=crpto
```

Use `DAGSHUB_TOKEN` or `DAGSHUB_USER_TOKEN` locally. In GitHub Actions, store
tokens as repository secrets.

## Validation

```bash
uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project
uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q
uv run dvc status --no-updates
```

Full artifact tests require local data/model artifacts or a configured DVC
remote.
