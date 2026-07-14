# CRPTO — academic context and operating principles

This document captures the operating reality of CRPTO so that any future
collaborator (human or agent) does not over-engineer for an industrial
deployment that is never going to happen.

## What this project is

- A **master's thesis** by Carlos Alfredo Vergara Rojas.
- A research repository and one active IJDS manuscript built on the
  **Lending Club Loan Data 2007--2020Q3** archive (2,925,493 rows and 142 raw
  columns). The active design exhausts 640,543 eligible 36-month loans under
  its declared temporal and observability contract.
- The active deliverables are the anonymous **IJDS paper PDF**, a separate
  **online supplement PDF**, source/evidence registries, and a reproducibility
  capsule. The Quarto book and historical journal package are secondary and do
  not supply active claims.

## What this project is NOT

- **Not going to production.** There is no live scoring service, no
  microservice, no batch nightly job. No SLAs, no on-call.
- **Not a multi-author project.** Solo author. No code review board, no
  PR approval workflow, no separate QA team. The CLAUDE.md operating rules
  exist to keep agents disciplined, not to satisfy a corporate process.
- **Not getting new data.** Lending Club closed retail loan origination in
  late 2020. The dataset is **static and complete** for the period covered.
  There is no streaming pipeline, no schema drift, no concept drift on new
  cohorts. If we re-train, we re-train on the same historical window.
- **Not commercial software.** MIT-licensed code, CC-BY 4.0 text. Treat
  reviewers (paper, journal, MRM) as the only "stakeholders".

## Consequences for engineering decisions

| Decision | Industrial default | CRPTO academic stance |
| --- | --- | --- |
| CI/CD coverage | every push runs full test matrix | focused CI plus a full local submission gate before journal milestones |
| Branch protection on `main` | required reviews, status checks | none — single author can push direct |
| Dependabot version PRs | auto-merge after CI | dismissed by default; manual review when a real CVE shows up |
| Monitoring / observability | dashboards, alerts | MLflow for experiment trace, nothing else |
| Feature stores, registries | Hopsworks, Feast | DVC + dbt on DuckDB, all local |
| Re-training schedule | weekly/quarterly retrains | never automatically; only when the paper needs revision |
| Disaster recovery | multi-region backups | git + DVC remote on DagsHub is enough |
| Secrets management | Vault, KMS | `.env` local + GitHub Actions secrets if needed |

## Re-running the champion

The canonical outputs are protected by destination, not only by whether a
stage performs search. Do not run any DVC stage that writes the frozen PD,
conformal, validation, portfolio, or exact-evaluation paths without explicit
permission. This covers `crpto.pd.champion`, `crpto.conformal.intervals`,
`crpto.conformal.validation`, `crpto.portfolio.optimization`, and
`crpto.portfolio.bound_exact_eval`; Optuna HPO is likewise excluded.

Validation is intentionally separate from regeneration:

| Operation | Ordinary validation status |
| --- | --- |
| `just validate-champion` | yes; hashes protected artifacts without rewriting them |
| `just drift-gate` | yes; recomputes in test space and compares against frozen vectors |
| Versioned experiment replay | yes; must use a distinct run tag and contained experiment paths |
| `crpto.paper.*` | yes; regenerates publication evidence from declared inputs |
| `crpto.book.render` | yes; render only, with `--no-execute` |
| Any protected `dvc repro` stage | no, unless the user explicitly authorizes a named revalidation plan |

The historical drift tolerances remain useful for an explicitly authorized
migration: max absolute interval difference `≤ 1e-6`, coverage delta `≤ 5e-4`
per Mondrian cell, and portfolio robust-return delta `≤ $1.00`. They are not
permission to overwrite canonical artifacts.

## GitHub strategy (single-author public repo)

The repo is public for academic reproducibility. We keep:

- `book-publish.yml` — auto-deploys the Quarto book to GitHub Pages on every
  push to `main`. This is the single most valuable workflow because
  reviewers can read the book at https://eigencharlie.github.io/Paper_CRPTO/.
- `lint.yml` — catches formatting/import issues before they accumulate.
  Runs in ~30s.

We **drop** (or never adopt):

- Branch protection requiring reviews — no second author exists.
- Dependabot version PRs — too noisy when nobody triages them. Security
  alerts (Dependabot's separate "alerts" tab) remain on because they only
  fire for real CVEs.
- A full `pytest` workflow on every push — local pre-push hook already runs
  the artifact-independent suite, and reviewers do not consult the test tab.
- `dbt.yml` and `book-build.yml` — `dbt parse` without parquets is trivial
  and the book build is already part of book-publish.

If the project ever moves to multi-author (very unlikely), revisit this
document and re-enable the dropped workflows + branch protection.

## What we keep doing rigorously even in academic mode

These remain non-negotiable because they protect the paper's
reproducibility:

1. **Pin every dependency** in `uv.lock` and bump floors only when the
   lockfile already moved.
2. **DVC for data + model artifacts**; never commit binaries to Git.
3. **Pre-commit hooks** (ruff, nbstripout, non-blocking DVC drift report,
   smoke tests).
4. **Pre-push hooks** that run the artifact-independent test suite.
5. **MAPIE / Pandera / Optuna / MLflow** kept on the same major version as
   `uv.lock` (no silent surprises).
6. **EXTRACTION_MANIFEST.json** hashes are the canonical source of "is the
   champion intact?" — validated by the `crpto-validate-champion` skill
   and the `validate-champion` pre-push hook.

## When in doubt

Default to *less* tooling, not more. Every CI hook, every workflow, every
service has a maintenance cost that is paid by exactly one person. If a
proposed tool does not help write the paper or render the book, it does
not belong here.
