# IJDS Submission Package

This directory contains the active maturity-safe and comparator-aware IJDS
handoff and editor-facing materials.

## Scientific Sources

- anonymous body: `paper/CRPTO_ijds.qmd`;
- anonymous supplement: `paper/supplement_ijds.qmd`;
- official template: `paper/submission/CRPTO_ijds_submission.tex`;
- claim authority: `docs/research/active_claims_2026-07-10.md`;
- parent evidence: `reports/crpto/ijds_maturity_safe_evidence.json`;
- comparator evidence:
  `reports/crpto/ijds_comparator_stringency_evidence.json`.
- comparator post-run audit:
  `docs/research/ijds_comparator_stringency_results_2026-07-10.md`.

The active result uses a status-independent 540,121-loan universe, exact 90%
binary Mondrian intervals, a 2012H2-selected score
`q=0.75p+0.25u` with `tau_q=0.17`, and 15 fresh monthly 2016--2017 decisions.
The same-threshold point baseline is loose. Against point PD aligned at
`tau_p=0.068313`, the guardrail loses realized standardized payoff and has
higher default and funded-set miscoverage. The comparator audit is explicitly
post hoc and the family direction is 7/9, not 9/9. Compact-v7 A35--A40 and
earlier diagnostics are immutable history, not active evidence.

## Preview

```powershell
just ijds-evidence
just paper-submission
```

Quarto HTML and browser-print PDFs are writing and visual-QA previews. The
upload PDF must come from `CRPTO_ijds_submission.tex` with the official INFORMS
class and `dblanonrev` option.

## Official Sources

- INFORMS style files: <https://pubsonline.informs.org/authorportal/latex-style-files>
- IJDS submission guidelines: <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- IJDS data/code policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- IJDS reviewer guidelines: <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>

Recheck these sources during submission week. Local publisher class/style files
support compilation and remain outside the project's scientific evidence.
They are intentionally ignored by Git. A fresh clone must place
`informs4.cls`, `informs2014.bst`, `eqndefns-left.sty`, and `informs_Logo.pdf`
in this directory after downloading the current INFORMS style package. The
compile wrapper checks this prerequisite and lists any missing asset before
invoking LaTeX.

## Official Build

```powershell
just paper-submission-official
```

The wrapper locates TinyTeX's working `latexmk.pl` payload and launches it with
Perl on Windows. The robust fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

```powershell
cd paper/submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
bibtex CRPTO_ijds_submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
```

The three LaTeX calls are intentional. The first writes `.aux`, BibTeX reads it
and writes `.bbl`, the second LaTeX pass resolves citations and references, and
the final pass stabilizes labels, float positions, and pagination.

## Build Acceptance

Accept the official PDF only when:

- `.blg` has no warnings;
- `.log` has no undefined citations or references;
- the initial-submission body satisfies the IJDS 25-page rule;
- tables and figures are readable and inside margins;
- content and metadata remain double-anonymous; and
- page-by-page inspection finds no clipping, overlap, blank content, or
  missing glyphs.

The page count recorded here must be refreshed by
`just paper-submission-official` after every substantive TeX edit. Accept only
the count and reference start reported by the latest clean compile and repeat
page-by-page visual QA for all three PDFs.

Latest validated build (2026-07-10):

- official INFORMS manuscript: 22 pages; references begin on page 19, leaving
  18 pre-reference pages against the 25-page initial-submission limit;
- anonymous browser-print body preview: 22 pages;
- anonymous browser-print supplement: 21 pages;
- official main-body inventory: 12 tables and 4 figures;
- title: 9 words; abstract: 269 words; keywords: 7;
- `.blg`: no warnings; `.log`: no undefined citations or references;
- one publisher-class `\maketitle` overfull diagnostic (17.54 pt, adjacent to
  `informs_Logo.pdf`) and the audit-card cell underfull diagnostics were
  visually checked and do not cross margins or hide content;
- every page of all three PDFs was rendered to PNG and inspected for clipping,
  overlap, blank pages, missing glyphs, and table/figure legibility.

## Anonymity

- QMD metadata uses `author: "Anonymous"`.
- TeX uses `\documentclass[ijds,dblanonrev]{informs4}`.
- Author, affiliation, email, acknowledgements, repository ownership, personal
  URLs, local paths, and private remotes stay out of reviewer-facing files.
- Cover letter, disclosure, and title page are editor-facing files uploaded to
  their designated ScholarOne fields.

## Final Gate

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

Use `SCHOLARONE_FINAL_CHECKLIST.md` for final proof review. DVC status is a
report, not permission to rerun protected historical stages.
