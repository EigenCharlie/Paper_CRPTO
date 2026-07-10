# IJDS Submission Package

This directory contains the official-template handoff and editor-facing
submission materials. The synchronized scientific sources are:

- `paper/CRPTO_ijds.qmd`: anonymous body.
- `paper/supplement_ijds.qmd`: anonymous online supplement.
- `paper/submission/CRPTO_ijds_submission.tex`: manually compacted
  `informs4` handoff.
- `paper/submission/CLAIM_AUDIT_MATRIX.md`: active claim/evidence map.
- `paper/submission/REPRODUCIBILITY_PACKAGE.md`: data/code package plan.

The active manuscript has one policy: exact 90% conformal replay,
`q=(p+u)/2`, `tau=0.17`, and a nine-cell November selector under
`B_u<=0.28`. An outcome-free December replay and post-selection audit are part
of A36; the audit deliberately records that stable policy identity does not
imply selected-set coverage. A35--A40 are the active evidence bundle. Keep
body, supplement, TeX, and governance numerically aligned with
`tests/test_ijds_active_claim_sync.py`.

## Preview

```powershell
just ijds-evidence
just paper-submission
just paper-submission-pdf
```

HTML and browser-print PDFs are writing and visual-QA previews. The upload PDF
must come from `CRPTO_ijds_submission.tex` with the official INFORMS class and
the `dblanonrev` option.

## Official Sources

- INFORMS style files: <https://pubsonline.informs.org/authorportal/latex-style-files>
- IJDS submission guidelines: <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- IJDS data/code policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- IJDS reviewer guidelines: <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>
- IJDS Overleaf template: <https://www.overleaf.com/latex/templates/template-for-informs-journal-on-data-science/sbthszxgycfn>

Local copies of `informs4.cls`, `informs2014.bst`, and related publisher files
are used for compilation and remain gitignored. Recheck official sources during
the final submission week.

## Official Build

Run from `paper/submission`:

```powershell
if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
```

`latexmk` is preferred because it automates convergence. The repository build
resolves TinyTeX's `latexmk.pl` and launches it with Perl on Windows, bypassing
the defective `runscript.tlu` executable wrapper. If that payload is unavailable
or fails, the robust fallback is:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

```powershell
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
bibtex CRPTO_ijds_submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
```

The three `pdflatex` calls are intentional:

1. The first pass writes `.aux`, including citation keys and unresolved labels.
2. BibTeX reads `.aux` and writes the formatted `.bbl`.
3. The second LaTeX pass imports `.bbl` and resolves citations and references.
4. The final pass stabilizes labels, float positions, and pagination changed by
   the bibliography and cross-references.

After a TeX Live update, an `expl3` format mismatch can be repaired once with:

```powershell
if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
fmtutil-sys --byfmt pdflatex
```

The repository wrapper runs the working `latexmk` payload first and falls back
automatically:

```powershell
just paper-submission-official
```

## Build Acceptance

The official-template PDF is acceptable only when:

- `.blg` has no bibliography warnings;
- `.log` has no undefined citations or references;
- the body is at most 25 pages under the IJDS counting rule;
- tables do not overflow or become unreadably small;
- the PDF remains double-anonymous;
- visual inspection confirms that figures, equations, and references render.

Current verified build (2026-07-09): 13 pages total; References begin on page
11, so the main text occupies pages 1--10 and remains well within the 25-page
limit. The bibliography is clean, and visual inspection of all 13 pages found
no clipping, overlap, missing glyphs, or unreadable tables.

Do not keep a page-count statement in this README without rebuilding the
current TeX. The final compile wrapper records the current count and warning
scan.

## Anonymity

- QMD metadata uses `author: "Anonymous"`.
- TeX uses `\documentclass[ijds,dblanonrev]{informs4}`.
- Author names, acknowledgements, repository ownership, personal URLs, local
  usernames, and private remotes stay out of the reviewer packet.
- Cover-letter and data/code language lives in
  `COVER_LETTER_AND_DISCLOSURE.md` and related editor-facing files.
- `TITLE_PAGE_DRAFT.md` is uploaded separately when ScholarOne requests it.

## Final Gate

```powershell
just submission-check
uv run dvc status --no-updates
git status --short
```

Use `SCHOLARONE_FINAL_CHECKLIST.md` for upload order and proof review. Preserve
the active midpoint narrative; OCE/CVaR, SPO+, external replications, and other
historical diagnostics remain supplement context rather than additional active
methods.
