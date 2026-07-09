# CRPTO scripts map

This folder contains both current IJDS publication tooling and historical
research/search entry points. Treat the current submission path as narrow on
purpose.

## Current IJDS path

Use these for the active submission workflow:

- `check_publication_integrity.py` - checks that paper, supplement, README and
  official-template docs agree on the active pool93 IJDS claim.
- `compile_ijds_submission.py` - compiles the official INFORMS/IJDS LaTeX
  handoff and scans `.log`/`.blg` for unresolved citations or references.
- `run_ty_advisory.py` - runs pinned `ty` in a focused advisory scope for daily
  IJDS work or in a blocking full scope. Both scopes are currently clean;
  `submission-check` enforces the full scope.
- `build_crpto_journal_package.py` - builds the journal evidence package from
  frozen inputs.
- `export_crpto_tables.py` - exports paper tables from frozen artifacts.
- `generate_crpto_figures.py` - exports paper figures from frozen artifacts.
- `render_submission_pdf_previews.py` - creates local HTML-print preview PDFs
  for body and supplement.

The high-level commands are still the source of truth:

```powershell
just smoke
just type-advisory
just hooks-check
just complexity-report
just paper-submission
just paper-submission-official
just submission-check
```

Optional local inspection:

```powershell
just api-docs-core
```

This builds `reports/api-docs/` with `pdoc` for the core optimization,
calibration and evaluation modules. The output is ignored by Git.

`just complexity-report` runs `radon` over `src/` and `scripts/` and reports
D-or-higher blocks. Treat it as a refactor radar, not a submission gate: some
historical/protected search entry points remain intentionally long until a
post-submission cleanup lane justifies touching them.

## Protected or historical search paths

The large scripts under `scripts/search/` and `scripts/experiments/` are mostly
historical or governed research surfaces. Do not run HPO, conformal interval
generation, champion search, or protected portfolio search unless the work has
a fresh run tag, artifact sink, and drift/revalidation plan.

`scripts/search/run_conformal_search.py` and
`scripts/search/run_portfolio_search.py` are intentionally retired wrappers.
They now return actionable messages instead of importing the removed generic
`scripts.run_long_pipeline` orchestrator.

TabPFN, SPO+/PyEPO/Torch and cuOpt remain optional experiment stacks. The
scripts that need them use explicit optional imports so the base IJDS
environment stays light and full-tree type checks still remain useful.

The active paper should cite the frozen pool93 finite-grid certificate, not a
new ad hoc rerun from these entry points.

## Refactor priority

For pre-submission cleanup, prefer small changes that reduce publication risk:

1. keep claim synchronization checks strict;
2. keep `mypy` green;
3. use `just type-advisory` for daily IJDS work and `just type-advisory-full`
   for final local checks;
4. avoid broad rewrites of protected search code until after IJDS submission.
