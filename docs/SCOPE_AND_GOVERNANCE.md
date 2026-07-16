# Scope And Governance

## Public Scope

This repository contains the active CRPTO IJDS research object:

- exact data-role, endpoint, and feature contracts;
- frozen prediction and binary conformal coverage controls;
- outcome-blind portfolio construction and exact comparator analysis;
- registered aggregate evidence, tables, and figures;
- the anonymous paper, supplement, and official submission build;
- tests and CI needed to reproduce and audit those outputs.

It does not contain a production service, a live lending policy, an experiment
dashboard, or a narrative of prior CRPTO versions.

## Authorities

| Concern | Authority |
|---|---|
| Active prose claims | `docs/research/active_claims_2026-07-14.md` |
| Lineage and DVC identities | `configs/ijds_active_evidence_sources.yaml` |
| Executable qualitative claims | `configs/ijds_claim_ledger.yaml` |
| Numeric paper evidence | `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json` |
| Active code surface | `configs/crpto_publication_targets.yaml` |
| Historical protected hashes | `EXTRACTION_MANIFEST.json` |

No memo, old manuscript, stopped protocol, or unregistered run may override
these files.

## Safe Operations

- Read registered roots and rebuild active aggregate evidence.
- Render the body, supplement, generated TeX, and PDFs.
- Run tests, lint, static typing, source verification, and visual QA.
- Refactor current code when scientific outputs and lineage identities remain
  stable.
- Add a new, predeclared, contained experiment with a distinct run tag.

## Protected Operations

Explicit permission is required before running:

- `crpto.pd.champion`
- `crpto.conformal.intervals`
- `crpto.conformal.validation`
- `crpto.portfolio.optimization`
- `crpto.portfolio.bound_exact_eval`

Do not modify `EXTRACTION_MANIFEST.json` or overwrite protected artifacts. A
new result belongs under a new run tag; it must not replace a frozen root.

## Sealed Compatibility

`dvc.yaml`, `dvc.lock`, and files whose exact paths are fixed by the extraction
manifest form a non-executable compatibility capsule. Their only current role
is hash and provenance verification. Active commands must not call them, and
the manuscript must not cite their historical results.

The complete project history is preserved outside the repository in
`D:\crpto_legacy`, including a Git mirror, verified bundle, snapshots, and the
pre-consolidation material worktree.

## Data And Secrets

Keep raw CSVs, DVC cache, model binaries, local PDFs, `.env` files, tokens, and
temporary benchmark outputs out of Git. Commit only DVC pointers and aggregate
artifacts allowed by the active publication contract. Never place credentials
in YAML, code, notebooks, logs, or submission files.

## Change Classification

| Change | Required validation |
|---|---|
| Prose/citation only | claim sync, TeX generation, manuscript build |
| Deterministic builder | focused tests, idempotence, evidence reconciliation |
| Current code refactor | full tests, lint, mypy, ty, active checks |
| Data/model/conformal behavior | new protocol/run tag plus explicit drift and scientific review |
| Submission closeout | all gates, strict protected hashes, DVC remote, visual QA |

## Closeout

Before synchronization:

```powershell
just test
just lint
just type-check
just type-check-fast
just drift-gate
just ijds-active-check
just validate-champion-strict
just submission-build
just submission-check
just ijds-dvc-verify-remote
```

The project remains `prefreeze_active`; a clean closeout is not a submission
freeze.
