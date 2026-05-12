# CRPTO scope and governance

This repository is the standalone home for the CRPTO paper, journal package,
Quarto book and reproducibility pipeline. It is intentionally scoped to the
CRPTO paper lane only; extraction history and lessons are kept in
`docs/PROJECT_HISTORY.md`.

## Public scope

CRPTO covers:

- Lending Club credit-risk data preparation used by the frozen paper run.
- Canonical PD champion, calibration contract and model-risk documentation.
- Conformal prediction intervals and diagnostics used by the paper evidence.
- Robust predict-then-optimize portfolio policy and SPO/funded-set analyses.
- Fair-lending, governance, MRM, traceability and journal appendix material.
- Quarto book, manuscript draft, tables, figures and publication exports.
- CI, dbt, DVC metadata, MLflow/DagsHub integration templates and local skills.

CRPTO does not cover:

- Parent-project Streamlit or FastAPI apps.
- Paper 2/Paper 3 lanes, IFRS9, survival, causal, quantum/GPU labs or the
  insights factory, except where a CRPTO chapter cites prior context.
- New model-training research unless it is explicitly isolated from the frozen
  champion or run under a new tag.

## Frozen champion contract

The official CRPTO run remains:

- run tag: `paper-thesis-final-economic-2026-04-06`
- policy: `bound_aware_276k_economic_champion`
- robust return: `$170,464.54`
- `V(alpha=0.01)=0.03645`
- `Gamma_CP(alpha=0.01)=0.18591`
- exact pass: `true`
- robust region: `45/45`

Do not overwrite these protected files without an explicit revalidation plan:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- `EXTRACTION_MANIFEST.json`

## Safe work

Safe changes by default:

- Documentation, README, runbooks, Quarto prose and non-executed book renders.
- Artifact-independent tests and adapters that do not change model outputs.
- CI/workflow maintenance, dependency-review metadata and public docs.
- Regenerating CRPTO tables, figures, evidence summaries and journal package
  from already-frozen artifacts.
- Adding tests around utilities, schemas, policy aliases and pipeline state.

Potentially safe but review first:

- dbt model changes that only read existing CRPTO DuckDB/parquet artifacts.
- DVC metadata edits that do not repro protected stages.
- Dependency floor bumps that do not affect protected model or conformal code.

Not safe on `main`:

- `dvc repro crpto.pd.champion`
- `dvc repro crpto.conformal.intervals`
- `dvc repro crpto.conformal.validation`
- `dvc repro crpto.portfolio.optimization`
- `dvc repro crpto.portfolio.bound_exact_eval`
- MAPIE, feature-config or conformal refactors that require fresh champion
  artifacts before drift validation.

## Refactor lanes

The files in `docs/refactor/` are plans, not approvals to execute. The current
high-risk lanes are:

- `MAPIE_MIGRATION_PLAN.md`: code is MAPIE 1.x-compatible, but the champion
  conformal artifact still needs drift validation before protected stages run.
- `CONFORMAL_REFACTOR_PLAN.md`: modularization must preserve pickled
  calibrator compatibility or create a new run tag.
- `FEATURE_CONFIG_PARQUET_PLAN.md`: changing `feature_config.pkl` affects the
  data/features contract and requires downstream validation.

## Public GitHub rules

The GitHub repo is public: <https://github.com/EigenCharlie/Paper_CRPTO>.

Keep in Git:

- Source, tests, Quarto, docs, tables, figures, JSON status files, DVC lock
  files and DVC pointer files.

Keep out of Git:

- `.env`, `.env.*` except templates, `.dvc/config.local`, raw CSVs, processed
  parquet/DuckDB files, model binaries, MLflow runs, local caches and tokens.

GitHub repository security currently expects:

- Dependency graph and Dependabot security updates enabled.
- Secret scanning enabled.
- No required branch protection in the current single-author academic mode.
  If CRPTO becomes multi-author, re-enable branch protection with at least
  `lint` and `book-publish` as required checks.

The default CI must remain lightweight: `lint` and `book-publish` run on push.
The artifact-aware `tests-full` workflow is manual and should be run before
journal milestones or any protected-stage revalidation.

## Environment

Use the Windows-native project environment:

- Windows PowerShell: `.venv/Scripts/python.exe`
- Python tools: `uv run ...`
- Quarto renders: `uv run -- quarto ...`

Do not route normal CRPTO work through non-Windows shells. If a shell or tool
creates a non-Windows virtualenv layout, treat it as a misconfigured local
environment and recreate the venv from PowerShell.

## Release checklist

Before considering a CRPTO change ready:

1. `just lint`
2. `just smoke`
3. `uv run pytest tests/test_utils/test_pipeline_state.py tests/test_utils/test_optuna_storage.py -q`
4. `uv run -- quarto render book --to html --no-execute`
5. Confirm `git status --short` does not include data, models or secrets.

For any protected-stage or dependency migration, add a branch-specific drift
report before merge.
