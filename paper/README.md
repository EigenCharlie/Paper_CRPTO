# CRPTO Manuscript Workspace

This directory contains the single active IJDS paper and its online supplement.
The Quarto book remains a broader companion dossier; it is not the source of
active manuscript claims.

## Active Paper

- Title: "CRPTO: When Marginal Conformal Coverage Meets Maturity-Safe Credit
  Portfolio Selection".
- Claim registry: `../docs/research/active_claims_2026-07-10.md`.
- Active evidence: `../reports/crpto/ijds_maturity_safe_evidence.json`.
- Body source: `CRPTO_ijds.qmd`.
- Supplement source: `supplement_ijds.qmd`.
- Official IJDS source: `submission/CRPTO_ijds_submission.tex`.

The paper reports one method and one mixed result. A selected conformal
upper-score guardrail reduces default relative to point PD by changing score
stratum composition, but loses standardized payoff and worsens funded-set
miscoverage. It does not claim selected-set validity, universal dominance,
cash-flow return, causality, prospectiveness, or a Markov certificate.

The compact-v7 A35--A40 bundle and earlier A1--A34 diagnostics are historical
provenance only. They must not fill or redefine an active result.

The recovered manuscript adds a closest-work boundary, three exact
identification propositions, the development-to-OOT reversal, and a managerial
audit card. These additions restore the useful depth of the broad draft without
restoring its invalid population, payoff, Markov, or external-validation claims.
The active evidence package contains four compact main-table exports, S1--S7,
and four figures; the official manuscript presents ten numbered tables.

## Submission Materials

`submission/` contains the official template source, package README, claim
matrix, cover letter, title page, data/code draft, reproducibility plan,
roadmap, and ScholarOne checklist. Editor-facing identity files remain outside
the anonymous manuscript and supplement.

## Build

```powershell
just ijds-evidence
just paper-ijds
just paper-ijds-supplement
just paper-submission
just paper-submission-official
```

Quarto HTML files are writing previews. Browser-print PDFs support visual QA.
The submission PDF comes from the official `informs4` TeX with `dblanonrev`.
The verified 2026-07-10 surfaces are 21 pages for the body preview, 17 for the
supplement preview, and 21 for the official IJDS PDF; references begin on page
18 of the official PDF.

## Closeout

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

After every substantive edit, reconcile body, supplement, official TeX,
evidence JSON, claim registry, cover letter, and title page; then inspect the
generated PDFs rather than trusting source-only checks.
