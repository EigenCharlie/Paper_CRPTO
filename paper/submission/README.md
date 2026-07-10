# IJDS Submission Package

This directory contains the active maturity-safe IJDS handoff and editor-facing
materials.

## Scientific Sources

- anonymous body: `paper/CRPTO_ijds.qmd`;
- anonymous supplement: `paper/supplement_ijds.qmd`;
- official template: `paper/submission/CRPTO_ijds_submission.tex`;
- claim authority: `docs/research/active_claims_2026-07-10.md`;
- evidence authority: `reports/crpto/ijds_maturity_safe_evidence.json`.

The active result uses a status-independent 540,121-loan universe, exact 90%
binary Mondrian intervals, a 2012H2-selected score
`q=0.75p+0.25u` with `tau=0.17`, and 15 fresh monthly 2016--2017 decisions.
Relative to point PD, the guardrail reduces default but loses standardized
payoff and worsens funded-set miscoverage. Compact-v7 A35--A40 and earlier
diagnostics are immutable history, not active evidence.

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

Current verified build (2026-07-10): 21 pages total, with references beginning
on page 18, and citation/reference clean. The writing previews are 21 body
pages and 17 supplement pages. All three PDFs were inspected page by page.
Recount and repeat visual QA after every substantive TeX edit.

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
