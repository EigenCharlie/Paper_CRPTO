# paper-crpto Manuscript Workspace

This folder contains the manuscript extraction layer for the standalone CRPTO
paper. The Quarto book remains the full companion dossier; this folder is where
the submission-shaped versions are written.

> **Scientific status (2026-07-10): NO-GO.** The current QMD, supplement, and
> official TeX are a frozen compact-v7 snapshot, not submission-ready sources.
> Preserve them until the maturity-safe evidence is stable; do not update their
> numbers piecemeal. Reconstruction decisions live in
> `../docs/research/ijds_three_front_reconstruction_2026-07-10.md`.

## Current Venue Decision

- Primary target: INFORMS Journal on Data Science.
- Secondary pivot: European Journal of Operational Research.
- Config source: `../configs/crpto_publication_targets.yaml`.
- Strategy memo: `../docs/research/crpto_publication_strategy_2026-05-12.md`.

## Files

- `CRPTO.qmd`: generic landing manuscript stub.
- `CRPTO_ijds.qmd`: active IJDS-style anonymous body source and current
  manuscript source of truth.
- `supplement_ijds.qmd`: IJDS-style online supplement source.
- `submission/README.md`: IJDS handoff checklist, anonymity guardrails, PDF
  draft commands, and SPO+ numbering rule.
- `submission/COVER_LETTER_AND_DISCLOSURE.md`: editor-facing cover letter and
  data/code disclosure draft; keep it out of the anonymous reviewer packet
  unless the submission system asks for disclosure text.
- `submission/IJDS_SUBMISSION_ROADMAP_2026-08-10.md`: target-date readiness
  plan and 15-track improvement checklist.
- `submission/CLAIM_AUDIT_MATRIX.md`: claim-to-evidence map and reviewer
  objection bank.
- `submission/REPRODUCIBILITY_PACKAGE.md`: IJDS data/code disclosure and
  accepted-paper reproducibility plan.
- `submission/TITLE_PAGE_DRAFT.md`: non-anonymous title-page draft for
  ScholarOne.
- `submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md`: working text for the official
  IJDS disclosure form.
- `submission/SCHOLARONE_FINAL_CHECKLIST.md`: final upload/proof checklist.

The historical compact-v7 paper has one method: exact 90% conformal replay, the midpoint
guardrail `q=(p+u)/2`, `tau=0.17`, and a nine-cell November selector under
`B_u<=0.28`. A35 is the exact-alpha audit, A36 is the split selector/December
audit, A37 is temporal evaluation, A38 is letter-grade composition, A39 is the
month-cluster bootstrap with loan-level sensitivity, and A40 is the matched
point-PD comparison. OCE/CVaR, SPO+, satisficing, online-style checks,
and Prosper/Freddie replications remain supplement diagnostics; they do not
select or redefine the midpoint policy. Prospective validation, causal variants,
live recalibration, production, and package tracks remain outside the claim.

## Render Commands

```powershell
just ijds-evidence
just paper-ijds
just paper-ijds-supplement
just paper-submission
just paper-submission-pdf
```

The HTML render is the writing preview; the PDF render is an HTML-print
verification draft produced from the anonymous previews. The final submission
PDF should use the official venue template. These Quarto files are the writing
source of truth until the IJDS LaTeX template is applied with double-anonymous
settings.

## Closeout Gates

Before tagging a submission release, do a final sweep for stale numbers,
captions, body-vs-supplement placement, and IJDS length. Keep public GitHub,
DagsHub, and MLflow links anonymized in the manuscript unless the venue policy
or cover-letter disclosure requires otherwise.
Use the roadmap and claim audit matrix as the final editorial checklist before
freezing the official `informs4` PDF.
