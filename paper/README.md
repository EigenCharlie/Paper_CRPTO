# paper-crpto Manuscript Workspace

This folder contains the manuscript extraction layer for the standalone CRPTO
paper. The Quarto book remains the full companion dossier; this folder is where
the submission-shaped versions are written.

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

Selected P2/P3-inspired diagnostics are part of the current paper/journal pack:
regret-auditability, OCE/CVaR tail risk, robust satisficing margins,
multi-distribution diagnostics, online replay diagnostics, the pool93 A35
finite-grid frontier, the A36 funded-set grade audit, the A37/A38 selected
pool93 tail-risk and cluster-bound audits, and external Prosper/Freddie economic
replications. Tail-risk row-level repricing is supplement evidence for the
selected pool93 allocation, not a hidden promotion criterion. Prospective
live online validation, causal variants, new multi-dataset protocols beyond the
frozen Prosper/Freddie replications, production, and package tracks remain
future work.

## Render Commands

```bash
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
