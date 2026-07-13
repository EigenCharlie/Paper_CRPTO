# IJDS Submission Package

This directory is the active anonymous IJDS handoff. The single editorial
source is `paper/CRPTO_ijds.qmd`; the official TeX is generated and must not be
edited directly.

## Active Sources

- body: `paper/CRPTO_ijds.qmd`;
- supplement: `paper/supplement_ijds.qmd`;
- TeX generator: `scripts/build_ijds_submission_tex.py`;
- INFORMS Pandoc template: `paper/submission/informs-pandoc-template.tex`;
- generated official TeX: `paper/submission/CRPTO_ijds_submission.tex`;
- claim authority: `docs/research/active_claims_2026-07-12.md`;
- evidence: `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`.

The active study uses one 640,543-loan status-independent design universe,
eight co-primary residual windows, two declared learners, all nine portfolio
policies, C0/C1/C2 comparators, exact development and stress cap supports,
sharp unresolved-outcome bounds, and a 19,200-repetition mechanism simulation.
It reports no learner, window, policy, cap, or comparator winner.

## Current IJDS Requirements

Official pages were rechecked July 12, 2026:

- [submission guidelines](https://pubsonline.informs.org/page/ijds/submission-guidelines);
- [data/code policy](https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy);
- [LaTeX files](https://pubsonline.informs.org/authorportal/latex-style-files);
- [GenAI policy](https://pubsonline.informs.org/page/ijds/llm-policy).

The current rules specify an IJDS-template PDF, at most 25 pages excluding
references and appendices, a separate online supplement, double-anonymous
review, 1--10 keywords, and an abstract of at most 300 words. The data/code
form is required at submission. Recheck all pages during submission week.

## Build

```powershell
just ijds-evidence
just paper-submission
just paper-submission-tex
just paper-submission-official
```

`build_ijds_submission_tex.py --check` fails when generated TeX is stale.
`informs_style_assets.json` pins the reviewed INFORMS class, bibliography,
equation, and logo files by byte count and SHA-256; the compiler rejects a
missing or changed style kit until the manifest is explicitly reviewed.

The official compiler first attempts `latexmk`. If the TinyTeX Windows wrapper
fails in `runscript.tlu`, the robust fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first `pdflatex` creates `.aux`; BibTeX creates `.bbl`; the second
`pdflatex` resolves citations and cross-references; the final pass stabilizes
labels, floats, and pagination.

## QA Record

Validated on July 12, 2026 after the V4 rewrite:

- official INFORMS PDF: 28 pages;
- references begin on page 25, leaving 24 pre-reference pages;
- HTML-print verification PDFs: body 21 pages, supplement 13 pages;
- main manuscript: five tables and three figures;
- abstract: 272 words; keywords: seven;
- `.blg`: no warnings;
- `.log`: no undefined citations, labels, or convergence requests;
- all 28 official, 21 body-preview, and 13 supplement pages were rendered and
  visually inspected; no clipping, overlap, blank page, broken table, missing
  glyph, or illegible figure was found; and
- the publisher-class first page retains its standard red template notice;
  title, abstract, keywords, and manuscript text remain inside the page.

Regenerate this record after every substantive edit. A stale page count is not
evidence for a later manuscript.

## Acceptance Criteria

- generated TeX is current with QMD;
- `.blg` has no warnings and `.log` has no undefined references/citations;
- pre-reference body is no more than 25 pages;
- tables and figures remain near first mention and inside margins;
- body and supplement contain no identifying metadata;
- the abstract stays below 300 words;
- no retired selected-policy, V1--V3, pool93, or compact-v7 headline returns;
- all V4 claim-sync and evidence-hash tests pass; and
- page-by-page visual inspection finds no clipping, overlap, blank page, or
  missing glyph.

## Final Gate

```powershell
just submission-check
just ijds-dvc-remote-status
git status --short
```

This is a pre-freeze working package. The eventual submission freeze requires
an explicit decision and a fresh final proof review.
