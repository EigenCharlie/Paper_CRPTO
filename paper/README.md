# CRPTO Manuscript Workspace

This directory contains one active IJDS paper and one online supplement. The
Quarto book is a broader internal dossier, not a source of manuscript claims.

## Active Paper

- Title: "CRPTO: Auditing Temporal Transport and Comparator Choice in
  Conformal Portfolios".
- Claim registry: `../docs/research/active_claims_2026-07-12.md`.
- Evidence: `../reports/crpto/ijds_fixed_taxonomy_c2_evidence.json`.
- Canonical source: `CRPTO_ijds.qmd`.
- Supplement: `supplement_ijds.qmd`.
- Generated official source: `submission/CRPTO_ijds_submission.tex`.

The paper reports a retrospective decision audit, not a selected policy. OOT
candidate coverage falls below 90% under both residual windows, all four fixed
taxonomies, and the late-window lag grid. Portfolio directions vary across
timing, C0/C1/C2, comparator scopes, seeds, purpose constraints, and LGD; all
27 envelopes are indeterminate in each scope. The defensible claim is observed
coverage transport failure plus comparator non-invariance.

Historical selected-policy, compact-v7, pool93, external-transfer, and A1--A40
materials remain recoverable from Git/DVC but are outside the active capsule.

## Editorial Architecture

`CRPTO_ijds.qmd` is the single editorial source for the body. The deterministic
builder and `submission/informs-pandoc-template.tex` generate the official
INFORMS TeX. This removes manual QMD/TeX duplication. The supplement remains a
separate QMD because IJDS requires appendices and lengthy diagnostics in an
online supplement.

## Build

```powershell
just ijds-evidence
just paper-submission
just paper-submission-tex
just paper-submission-official
```

The validated official PDF has 28 pages, with references beginning on page 25
(24 pre-reference pages), 7 main tables, and 3 figures. The abstract has 260
words and the keyword list has 7 entries.

## Closeout

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

After substantive edits, rebuild evidence and TeX, compile all surfaces, and
inspect rendered pages. The repository remains pre-freeze until the user makes
an explicit freeze decision.
