---
name: crpto
description: Work on the standalone CRPTO paper project without disturbing frozen champion artifacts.
---

# CRPTO Skill

Use this skill for work inside the standalone `Paper_CRPTO` repository.

## Guardrails

- Treat the champion as frozen unless the user explicitly asks for a rebuild.
- Do not rewrite or delete:
  - `models/pd_canonical.cbm`
  - `models/pd_canonical_calibrator.pkl`
  - `models/final_project_promotion.json`
  - `models/conformal_policy_status.json`
  - `data/processed/conformal_intervals_mondrian.parquet`
  - `data/processed/portfolio_bound_aware/**`
- Never commit `.env`, `.env.*` except examples, `.dvc/config.local`, private
  keys, cloud credentials, or local settings files.

## Common checks

```powershell
uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q
uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project
uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
uv run dvc status --no-updates
uv run -- quarto render book --to html --no-execute
```

Use Windows PowerShell and the default `.venv/Scripts` environment. Do not use
non-Windows shells as the normal execution path for this repo.

## Publication flow

The GitHub repository is `EigenCharlie/Paper_CRPTO`; the book publishes through
GitHub Pages after `book-publish` passes.
