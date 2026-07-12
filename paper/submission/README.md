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
- evidence: `reports/crpto/ijds_fixed_taxonomy_c2_evidence.json`.

The active study uses a common 465,117-loan OOT panel, two locked residual
windows, four fixed conformal taxonomies, all nine co-primary policies, three
comparator scopes, sharp unresolved-outcome bounds, two 180-cell seed-purpose
censuses, and 800 controlled-simulation repetitions. It reports no policy or
timing-window winner.

## Current IJDS Requirements

Official pages rechecked July 12, 2026:

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

`build_ijds_submission_tex.py --check` fails when the generated TeX is stale.
`informs_style_assets.json` pins the reviewed INFORMS class, bibliography,
equation, and logo files by byte count and SHA-256; the compiler rejects a
missing or different style kit until the manifest is explicitly reviewed.
The official compiler first attempts `latexmk`; the current TinyTeX Windows
wrapper may fail in `runscript.tlu`, in which case the documented fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first LaTeX pass creates `.aux`; BibTeX creates `.bbl`; the second LaTeX
pass resolves citations and references; the final pass stabilizes labels,
floats, and pagination.

## Current QA Record

Validated July 12, 2026:

- official INFORMS manuscript: **28 pages**;
- references begin on page 25, so the pre-reference body is 24 pages;
- main manuscript: 7 tables and 3 figures;
- title: 10 words; abstract: 260 words; keywords: 7;
- `.blg`: no warnings;
- `.log`: no undefined citations, labels, or convergence request;
- one publisher-class `\maketitle` overfull diagnostic (17.54 pt) is visually
  inside the page and originates beside the template notice/logo;
- all 28 pages were rendered and visually inspected; figures, tables, headers,
  footers, and references are legible with no clipping or overlap.

The page count is deliberately near, but below, the 25-page pre-reference
limit. Recount and repeat visual QA after substantive edits.

## Acceptance Criteria

- generated TeX is current with QMD;
- `.blg` has no warnings and `.log` has no undefined references/citations;
- pre-reference body is no more than 25 pages;
- tables and figures remain near first mention and inside margins;
- body and supplement contain no identifying metadata;
- the 260-word abstract stays below 300 words;
- no retired selected-policy or compact-v7 headline returns; and
- page-by-page visual inspection finds no clipping, overlap, blank page, or
  missing glyph.

## Final Gate

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

This is a pre-freeze working package. The eventual submission freeze requires
an explicit decision and a fresh final proof review.
