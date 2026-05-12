# CRPTO Skill

Use this skill when working inside `C:\Users\carlos\Documents\Paper_CRPTO`.
CRPTO is a standalone academic paper project for Conformal Robust
Predict-Then-Optimize in credit risk. The repository is public-facing, but the
paper champion artifacts are frozen.

## Required Context

Before structural work, read these files in order:

1. `docs/ACADEMIC_CONTEXT.md`
2. `docs/SCOPE_AND_GOVERNANCE.md`
3. `CONTRIBUTING.md`
4. `EXTRACTION_MANIFEST.md`
5. `configs/crpto_publication_targets.yaml`
6. `docs/research/crpto_backlog_2026-05-04.md`

Use the local project context over generic habits. This is a single-author,
static-dataset, no-production academic repo. Keep code simple, functional, and
close to the existing style.

## Platform

- Work Windows-first in PowerShell.
- Prefer `uv run ...` for Python, Quarto, dbt, DVC, MLflow, pytest, and ruff.
- The local venv is `.venv/Scripts/python.exe`.
- Do not introduce Unix-only shell assumptions.

## Champion Rules

The frozen champion is the paper result:

- Run tag: `paper-thesis-final-economic-2026-04-06`
- Policy: `bound_aware_276k_economic_champion`
- Robust return: `$170,464.54`
- `V(alpha=0.01)`: `0.03645`
- `Gamma_CP(alpha=0.01)`: `0.18591`
- Exact pass: `True`
- Robust region: `45/45`

Never overwrite these frozen artifacts unless the user explicitly asks for a
champion rebuild:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/`
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

The active paper scope is the journal strengthening pack:

- A19/Fig15: regret-auditability frontier in the main narrative.
- A12: OCE/CVaR tail-risk diagnostic, not a replacement champion objective.
- A13: robust satisficing margins for committee/OR framing.
- A14: dependence-aware caveat or supplement proposition, with cluster
  diagnostics as evidence rather than proof of independence.
- A20: tail-satisficing challenger audit over the 45 existing alpha-safe
  policies. It is a journal-only comparator and must not promote a new champion.
- A21: cluster-bound tightening table. Use it to make the dependence-aware
  caveat mathematically transparent, while saying plainly that it is not tighter
  than Markov under the current exposure concentration.
- Multi-dataset credit replication remains journal backlog and does not block
  the current submission.

Do not re-run champion search, HPO, or protected portfolio stages to support
this pack. Use existing artifacts unless the user explicitly asks for a new
champion experiment.

## Objective Experiments

OCE/CVaR/satisficing can be implemented as an isolated research objective or
scoring layer. The default rule is:

- It may read existing allocations, predictions, intervals, or shortlist
  artifacts.
- It may generate new diagnostic tables, figures, configs, tests, and docs.
- It must not replace the champion objective, rank-1 policy, or frozen outputs.
- A tail-satisficing challenger audit may re-solve the 45 existing shortlist
  policies under a new paper/audit stage if outputs are new and the status marks
  `champion_promotion_changed=false`.
- If used for a new search, store results under a new experiment path and make
  the comparison explicit against the frozen champion.

## Submission Closeout

For the current submission, keep these gates visible:

- Consolidate A19/Fig15, A20/A21, paper/supplement, docs, and `dvc.lock`.
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
uv run python scripts/build_tail_satisficing_challenger_audit.py
uv run pytest tests/test_publication_targets.py -q
uv run pytest tests/test_scripts/test_build_crpto_journal_package.py -q
uv run pytest tests/test_scripts/test_tail_satisficing_challenger_audit.py -q
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
