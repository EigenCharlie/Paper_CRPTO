# CRPTO Skill

Use this skill when working inside `C:\Users\carlos\Documents\Paper_CRPTO`.
CRPTO is a standalone academic paper project for Conformal Robust
Predict-Then-Optimize in credit risk. The repository is public-facing, but the
paper champion artifacts are frozen.

## Required Context

Before structural work, read these files in order:

1. `docs/ACADEMIC_CONTEXT.md`
2. `docs/SCOPE_AND_GOVERNANCE.md`
3. `docs/research/active_claims_2026-07-04.md`
4. `CONTRIBUTING.md`
5. `EXTRACTION_MANIFEST.md`
6. `configs/crpto_publication_targets.yaml`
7. `docs/research/README.md`

Use the local project context over generic habits. This is a single-author,
static-dataset, no-production academic repo. Keep code simple, functional, and
close to the existing style.

## Platform

- Work Windows-first in PowerShell.
- Prefer `uv run ...` for Python, Quarto, dbt, DVC, MLflow, pytest, and ruff.
- The local venv is `.venv/Scripts/python.exe`.
- Do not introduce Unix-only shell assumptions.

## Champion Rules

The current IJDS paper-facing body claim is the promoted pool93 finite-grid
frontier closure. It is a deterministic policy-grid re-evaluation over the
frozen upstream PD/calibration/conformal artifacts, not a retraining run.

- Terminal run tag:
  `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal`
- Active certificate tag:
  `champion-reopen-2026-06-19__pool93__ijds-certificate-semantics-v2`
- Body point source run:
  `champion-reopen-2026-06-19__pool93__ijds-claim-micro-ext`
- Policy family: `claim_micro_ext_body_cap345`
- Policy mode: `capped_blended_uncertainty`
- Robust return: `$184,832.48`
- Return-floor surplus: `$14,367.94`
- `V(alpha=0.01)`: `0.035350`
- `Gamma_CP(alpha=0.01)`: `0.162616`
- `Gamma_internalized(alpha=0.01)`: `0.089032`
- `Gamma_residual(alpha=0.01)`: `0.073584`
- Exact endpoint budget at `alpha=0.01`: `0.245083866`
- Exact Markov loss threshold at `alpha=0.01`: `0.345083866`
- Realized risk-tolerance excess: `0.0`
- Declared alpha-grid pass: `8/8`
- Consolidated frontier: `50,010` deduplicated semantic policies, `27,508`
  eligible all-alpha above-floor policies.
- Terminal exact search: `37,068/37,068` all-alpha passers and `296,544`
  completed exact candidate-alpha checks.
- Matched A40 point-PD baseline: `5.875%` realized-return cost, `0.08305`
  weighted default/miscoverage reduction, and `0.435495` threshold reduction.

The frozen upstream baseline remains retained for provenance and as the
declared return floor:

- Run tag: `ijds-rebaseline-2026-06-07`
- Policy: `bound_aware_276k_economic_champion`
- Robust return: `$170,464.54`
- `V(alpha=0.01)`: `0.028875`
- `Gamma_CP(alpha=0.01)`: `0.187987`
- Exact pass: `True`
- Former robust region: `45/45`

The older run tag `paper-thesis-final-economic-2026-04-06` is historical
provenance only. Do not use it as the active body claim.

Never overwrite these frozen artifacts unless the user explicitly asks for a
champion rebuild:

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

Protected DVC stages:

- Do not run without explicit permission: `crpto.portfolio.bound_exact_eval`
  and any Optuna/HPO or policy search.
- Treat as protected revalidation stages: `crpto.pd.champion`,
  `crpto.conformal.intervals`, `crpto.conformal.validation`, and
  `crpto.portfolio.optimization`. If the user explicitly permits them, run them
  as a drift check and validate hashes before/after.
- Safe paper stages: `crpto.paper.export_tables`, `crpto.paper.evidence`,
  `crpto.paper.journal_package`, `crpto.paper.tail_satisficing_audit`,
  `crpto.paper.figures`, `crpto.paper.spo_stability`, and `crpto.book.render`.

If the user says a change may touch the champion, isolate the work:

- Use a dedicated branch and a clear run label.
- Write new outputs under a new path; do not replace frozen champion files.
- Produce a drift report with expected tolerances.
- Run `just validate-champion` before and after.
- Do not update `EXTRACTION_MANIFEST.json` unless the user explicitly approves
  a new frozen release.

## Current Journal Scope

The active paper scope is the IJDS pool93 certificate plus bounded diagnostics:

- A19/Fig15: regret-auditability frontier in the main narrative.
- A35: promoted pool93 finite-grid return-bound frontier.
- A36: funded-set grade composition audit for the selected pool93 allocation.
- A37: pool93 selected-allocation LGD/CVaR/OCE tail-risk repricing.
- A38: pool93 selected-allocation cluster-bound sensitivity; Markov remains
  the body theorem because the cluster thresholds are not tighter here.
- A39: fixed-allocation bootstrap diagnostic; it does not resample model,
  solver, conformal intervals or policy search.
- A40: matched point-PD baseline with candidates and operating constraints fixed;
  one frozen OOT trade-off, not a causal or universal-dominance claim.
- A20--A22: legacy tail-risk/OCE/CVaR diagnostic package retained in the
  supplement, not as the promoted pool93 selector.
- A23--A24: multi-distribution/online coverage diagnostics, not universal
  conditional-coverage claims.
- A25--A34: Prosper/Freddie external economic replication, not new Lending Club
  champions.

Do not re-run champion search, HPO, conformal interval generation or protected
portfolio stages to support this pack. Use existing artifacts unless the user
explicitly asks for a new isolated experiment with a claim target, evidence
gate, artifact sink and stop rule.

## Objective Experiments

OCE/CVaR/satisficing can be implemented as an isolated research objective or
scoring layer. The default rule is:

- It may read existing allocations, predictions, intervals, or shortlist
  artifacts.
- It may generate new diagnostic tables, figures, configs, tests, and docs.
- It must not replace the champion objective, rank-1 policy, or frozen outputs.
- A tail-satisficing challenger audit may read or re-score frozen allocations
  under a new paper/audit stage if outputs are new and the status marks
  `champion_promotion_changed=false`. It must not replace the A35 pool93 body
  selector without a new promotion protocol.
- If used for a new search, store results under a new experiment path and make
  the comparison explicit against the active pool93 body claim and the frozen
  upstream rebaseline.

## Submission Closeout

For the current submission, keep these gates visible:

- Consolidate A19/Fig15, A20--A40, paper/supplement, docs, manifest hashes and
  `dvc.lock`.
- Sweep the manuscript for stale numbers, captions, body-vs-appendix placement,
  and IJDS length.
- Convert the final `.qmd` into the official IJDS LaTeX template when the PDF
  is ready for submission.
- Keep GitHub/DagsHub/MLflow disclosure compatible with double-anonymous
  review: anonymize in the manuscript, reveal in cover letter or after review
  according to venue policy.
- Create the reproducible release tag/bundle only after the final PDF passes.
- Treat `dvc push` as optional and credential-dependent.

## Standard Checks

Use focused checks while editing, then close with the strongest feasible set:

```powershell
uv run python scripts/build_crpto_journal_package.py
uv run pytest tests/test_publication_targets.py -q
uv run pytest tests/test_scripts/test_build_crpto_journal_package.py -q
uv run pytest tests/test_pool93_body_claim_sync.py -q
just smoke
just lint
just validate-champion
just paper-submission
uv run dvc status --no-updates
```

For a full milestone, also run `just test`, `just type-check`, and the relevant
Quarto render. Do not bypass hooks.

## Writing And Docs

- Spanish for book, paper prose, and research notes.
- English for code, identifiers, CI, and docstrings.
- Do not reformat the whole book in one pass.
- Avoid broad refactors unless they directly reduce risk for the current task.
- Never commit secrets, `.env`, local credentials, or heavyweight raw data.
