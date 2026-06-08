# CRPTO runbook

This runbook is scoped to the standalone `Paper_CRPTO` package.

## Environment

```powershell
uv sync --extra dev --extra search
cp .env.example .env
```

Use Windows PowerShell and the default `.venv/Scripts` environment. Do not set
custom Python/Quarto environment overrides for normal work.

## Safe daily checks

```powershell
uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q
uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project
uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
uv run dvc status --no-updates
uv run -- quarto render book --to html --no-execute
```

## Paper outputs

Safe deterministic outputs:

```powershell
uv run python scripts/export_crpto_tables.py
uv run python scripts/generate_crpto_figures.py --paper crpto
uv run python scripts/analyze_crpto_evidence.py
uv run python scripts/build_crpto_journal_package.py
uv run -- quarto render book --to html
```

These correspond to the public `just` recipes:

```bash
just tables
just figures
just evidence
just journal-package
just book
```

## Frozen champion guardrails

Do not re-run without explicit approval:

- `crpto.pd.champion`
- `crpto.conformal.intervals`
- `crpto.conformal.validation`
- `crpto.portfolio.optimization`
- `crpto.portfolio.bound_exact_eval`

The official CRPTO champion remains:

- run tag: `ijds-rebaseline-2026-06-07`
- policy: `bound_aware_276k_economic_champion`
- return: `$170,464.54`
- `V(alpha=0.01)=0.028875`
- `Gamma_CP(alpha=0.01)=0.187987`

## DVC and GitHub

Git tracks code, docs, JSON statuses, tables, figures, DVC lock and pointer
files. DVC stores raw data, processed data and model binaries.

Before pushing data:

```bash
uv run dvc remote list
uv run dvc push -r <remote-name>
```

If no remote is configured, the GitHub repo is still useful for source,
publication assets and metadata, but a fresh checkout cannot reproduce heavy
artifact tests until the DVC remote is configured.
