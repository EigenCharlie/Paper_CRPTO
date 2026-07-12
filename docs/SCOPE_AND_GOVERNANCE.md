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

## Active paper contract

The current IJDS paper is the fixed-taxonomy comparator and temporal-design audit:

- outcome-free run `ijds-fixed-taxonomy-c2-2026-07-11-v1` and hash-linked
  evaluation run `ijds-fixed-taxonomy-c2-2026-07-11-v2`;
- isolated temporal sensitivity
  `ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1`;
- common status-independent OOT universe of 465,117 36-month loans;
- CatBoost/Platt fitting before conformal residual estimation on early and late
  availability-safe windows, with score taxonomies fixed before either;
- four declared taxonomies and all nine guardrails reported as co-primary;
- coherent standardized payoff `(1-p)r-p*LGD` in the objective and
  `(1-Y)r-Y*LGD` in evaluation;
- 15 separate monthly USD 1 million decisions from April 2016 through June
  2017;
- unresolved outcomes retained with sharp paired common-outcome bounds;
- five-group OOT coverage bounds `[0.854714,0.879647]` early and
  `[0.845072,0.870973]` late;
- exact C2 funded-point-score matching with payoff lower for 7/9 early and 5/9
  late, so the policy count is not timing-stable;
- all 27 policy-metric envelopes contain zero in core,
  development-supported, and broad scopes, so no policy, window, or universal
  direction is promoted; and
- active publication artifacts `crpto_ijds_ft_*`, governed by
  `ijds_fixed_taxonomy_c2_evidence.json`.

The paper describes a code-locked retrospective temporal audit. It does not
claim a prospective trial, causal effect, latent-PD confidence interval,
selected-set conformal guarantee, cash-flow return, fair-lending certificate,
or Markov certificate. The full authority is
`docs/research/active_claims_2026-07-12.md`.

Maturity-safe P1/C1, compact-v7, the previous IJDS rebaseline, and the pool93
frontier are retained as historical provenance, not as active body claims:

- run tag: `ijds-rebaseline-2026-06-07`
- policy: `bound_aware_276k_economic_champion`
- robust return: `$170,464.54`
- `V(alpha=0.01)=0.028875`
- `Gamma_CP(alpha=0.01)=0.187987`
- exact pass: `true`
- robust region: `45/45`

The older run tag `paper-thesis-final-economic-2026-04-06` is retained as
historical provenance, not as the current manifest baseline.

Do not overwrite these protected files without an explicit revalidation plan:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
- `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv`
- `reports/crpto/tables/crpto_tableA36_pool93_body_funded_grade_audit.csv`
- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.csv`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.csv`
- `reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.csv`
- `reports/crpto/tables/crpto_tableA40_pool93_point_baseline.csv`
- `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_frontier.json`
- `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/portfolio/pool93_ijds_consolidated_governance.json`
- `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2/portfolio/pool93_point_pd_baseline_audit.json`
- `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal/portfolio/pool93_ijds_claim_governance.json`
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

- `MAPIE_MIGRATION_PLAN.md`: code is MAPIE 1.x-compatible and the June 2026
  drift report is green under the current stack. Protected conformal stage
  reruns still require explicit approval.
- `CONFORMAL_REFACTOR_PLAN.md`: script-level extraction is underway, but
  class/module modularization must preserve pickled calibrator compatibility
  or create a new run tag.
- `archive/FEATURE_CONFIG_PARQUET_PLAN.md` (executed 2026-06-13, archived):
  the live feature contract is now YAML/Parquet; changing it affects the
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
