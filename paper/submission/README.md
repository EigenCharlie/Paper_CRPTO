# IJDS Submission Package

This directory is the handoff checklist for the IJDS submission surfaces. The
source of truth remains:

- `paper/CRPTO_ijds.qmd` for the anonymous manuscript body.
- `paper/supplement_ijds.qmd` for the anonymous online supplement.
- `paper/submission/COVER_LETTER_AND_DISCLOSURE.md` for editor-facing cover
  letter language and data/code disclosure timing.
- `paper/submission/IJDS_SUBMISSION_ROADMAP_2026-08-10.md` for the internal
  two-month readiness plan.
- `paper/submission/CLAIM_AUDIT_MATRIX.md` for the claim/evidence/risk map.
- `paper/submission/REPRODUCIBILITY_PACKAGE.md` for the IJDS data/code package
  plan.
- `paper/submission/TITLE_PAGE_DRAFT.md` for the separate non-anonymous title
  page.
- `paper/submission/DATA_CODE_DISCLOSURE_FORM_DRAFT.md` for official-form
  answer drafting.
- `paper/submission/SCHOLARONE_FINAL_CHECKLIST.md` for the final upload/proof
  checklist.

## Render Commands

```powershell
just paper-submission
just paper-submission-pdf
```

The HTML render is the writing preview. The PDF render is a local HTML-print
verification draft for pagination and visual inspection. The final submission
PDF should be produced with the official INFORMS IJDS LaTeX template and
double-anonymous review option (`dblanonrev`), not with a hand-written local
style.

Editorial submission notes, venue reminders and page-budget comments belong in
this README or the cover-letter checklist, not in the anonymous manuscript body.

`COVER_LETTER_AND_DISCLOSURE.md` is intentionally separated from the anonymous
body and supplement. Use it for editor-facing disclosure fields, then keep the
reviewer packet free of public repository URLs, author identity, local paths and
private remote details.

## Official Template Sources

- INFORMS author portal: <https://pubsonline.informs.org/authorportal/latex-style-files>
- IJDS submission guidelines: <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- IJDS data/code disclosure policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>
- IJDS reviewer guidelines: <https://pubsonline.informs.org/page/ijds/reviewer-guidelines>
- Overleaf template page: <https://www.overleaf.com/latex/templates/template-for-informs-journal-on-data-science/sbthszxgycfn>

Do not vendor private template downloads, reviewer forms, or authenticated
publisher material into this repository. Local copies of the official template
files can live in this directory for compilation, but they are gitignored on
purpose.

## Official LaTeX Submission Build

`CRPTO_ijds_submission.tex` is the official-template handoff draft in the
INFORMS class (`\documentclass[ijds,dblanonrev]{informs4}`). The narrative
source remains `paper/CRPTO_ijds.qmd`, but the official `.tex` is now a
manually compacted IJDS-template surface. After freeze, do **not** regenerate it
mechanically from QMD; port substantive claim changes deliberately, then rebuild
and recheck the 26-page official PDF. The synchronized submission surface should
carry the central IJDS body: title, abstract,
keywords, core sections, the journal pipeline Figure 1, the bound-claim stack,
the A35 finite-grid frontier, the A36--A39 selected-allocation audits in the
supplement, the regret-auditability comparison, plus the core, exact-certificate,
funded-set audit and regret tables. The
`informs2014.bst` + `../../book/references.bib` bibliography wiring is already
present. Journal figures use PDF/vector exports from `reports/crpto/figures/`
where possible; Figure 1 intentionally uses the PNG export because the vector
PDF crop box cuts the right edge under `informs4`.

> **`informs4` is not on CTAN/TeX Live.** The class and bibliography style are
> distributed through the INFORMS author portal or the IJDS Overleaf template.
> Local copies are allowed for compilation and are gitignored. Do not commit
> `informs4.cls`, `informs2014.bst`, template PDFs, `.sty` files, or generated
> LaTeX build artifacts.

Current local build state (verified 2026-07-07): TinyTeX/TeX Live 2026,
`pdflatex`, `bibtex`, and the `listingsutf8` TeX package compile
`CRPTO_ijds_submission.tex` to a 26-page official-template PDF. Section 9
(Conclusion) and References both start on page 22, so the body remains inside
the IJDS 25-page initial-submission budget when references are excluded. The
only LaTeX log warnings left are a small `\maketitle` overfull from the
`informs4` anonymous title block and font-size / underfull paragraph warnings,
visually acceptable unless the final ScholarOne proof shows a layout issue.

`latexmk` remains the preferred command because it automates the required
LaTeX/BibTeX convergence loop. On 2026-07-07, the local Codex PowerShell
environment was missing `WINDIR`, which made TinyTeX wrapper scripts fail with
`runscript.tlu:712: attempt to concatenate a nil value`. Set `WINDIR` from
`SystemRoot` before calling TinyTeX wrappers in that environment. After
`tlmgr update --self --all`, the LaTeX format also had to be refreshed with
`fmtutil-sys --byfmt pdflatex` to resolve an `expl3` format mismatch.

To produce the official submission PDF:

1. Download or refresh `informs4.cls` and `informs2014.bst` from the INFORMS
   author portal (or Overleaf) and drop them next to
   `CRPTO_ijds_submission.tex`. These are gitignored on purpose
   (`paper/submission/.gitignore`); do not commit them.
2. Build with `latexmk`. In Codex/PowerShell sessions where `WINDIR` is absent,
   initialize it first:

   ```powershell
   if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
   latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
   ```

   If LaTeX reports mismatched support files after a TeX Live update, rebuild
   the local TinyTeX format once:

   ```powershell
   if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
   fmtutil-sys --byfmt pdflatex
   ```

   If PowerShell/TinyTeX still fails, use the proven fallback:

   ```powershell
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   bibtex CRPTO_ijds_submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   ```

   The three `pdflatex` passes are intentional. The first pass writes the
   `.aux` file that BibTeX needs; `bibtex` then writes the `.bbl`; the second
   `pdflatex` pass reads the bibliography and updates citations, cross
   references, labels, and page anchors; the final pass stabilizes any values
   that shifted after the bibliography and floats were inserted.

3. The `dblanonrev` option keeps the body anonymous; verify against the anonymity
   checklist below before uploading.

## Anonymity Checklist

- Manuscript metadata uses `author: "Anonymous"`.
- Supplement metadata uses `author: "Anonymous"`.
- Public GitHub, DVC, MLflow, DagsHub and personal URLs are described as a
  companion package but not exposed in the double-anonymous body.
- Cover-letter/data-code wording lives in `COVER_LETTER_AND_DISCLOSURE.md`.
- Title-page, acknowledgements and repository disclosure are kept for the cover
  letter or for post-acceptance policy, not the anonymous manuscript.
- Local paths, private workspace paths and usernames do not appear in the submitted
  sources.

## SPO+ Numbering Rule

Use the committed A19/Figure 15 artifact for body claims:

- Two-stage regret: `0.425896`
- SPO+ regret: `0.216837`
- Relative reduction: `49.09%`
- Wilcoxon: `p = 1.39e-164`

The PyEPO 1.3.7 closeout remains a curated appendix note:

- Two-stage regret: `0.358073`
- SPO+ regret: `0.184366`
- Relative reduction: `48.51%`
- Wilcoxon: `p = 3.80e-163`

These protocols are compatible but not interchangeable.

## Final Assembly Checklist

- Recheck the official IJDS sources linked above within the final submission
  week; policies and forms can change.
- Verify the Data and Code Disclosure Form language against
  `REPRODUCIBILITY_PACKAGE.md` and `DATA_CODE_DISCLOSURE_FORM_DRAFT.md`.
- Convert `TITLE_PAGE_DRAFT.md` into the separate title page requested by
  ScholarOne.
- Use `SCHOLARONE_FINAL_CHECKLIST.md` while uploading and reviewing the generated
  proof.
- Recheck the official-template page budget if the body changes materially. The
  current local official-template build is 26 pages total; Section 9 and
  References start on page 22, keeping the body within the 25-page limit when
  references are excluded.
- Keep A3--A39 in the online supplement unless a reviewer-facing argument needs
  one compact table in the body.
- Preserve CRPTO as the coverage/auditability method and SPO+ as the low-regret
  comparator.
- Cross-check every headline claim against `CLAIM_AUDIT_MATRIX.md`.
- Keep `CRPTO_ijds_submission.tex` semantically synchronized with the QMD
  whenever the body adds or demotes a figure, table, theorem statement or major
  result paragraph. Preserve the manual compaction choices that keep the
  official-template PDF inside the IJDS page budget.
- Regenerate previews with `just paper-submission-pdf` before release.
- Run the repository gates: `just lint`, `just smoke`, `just validate-champion`.

## Final Step - Official Compile

This remains a final-week action before upload, gated on an explicit decision
to freeze the manuscript. `CRPTO_ijds_submission.tex` already carries the full
ported prose, the economic-anchor ladder, and the temporal-split and tail-risk
tables. Local publisher class/style files are available in this directory and
gitignored; recheck the official source before final submission in case INFORMS
updates the template.

1. **Confirm closure.** The body content, numbers, and figures are final and the
   repository gates pass.
2. **Refresh the official template files if needed** (gitignored on purpose;
   never commit):
   - `informs4.cls` and `informs2014.bst` from the INFORMS author portal
     <https://pubsonline.informs.org/authorportal/latex-style-files> or the
     IJDS Overleaf template (v2.00, 29 Apr 2025, the latest checked locally)
     <https://www.overleaf.com/latex/templates/template-for-informs-journal-on-data-science/sbthszxgycfn>.
   - Drop both next to `CRPTO_ijds_submission.tex` if local copies are absent or
     stale. The fastest fallback is to paste the `.tex` into the Overleaf
     template, which already bundles both files.
3. **Compile:**

   ```powershell
   latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
   ```

   Use the documented `pdflatex -> bibtex -> pdflatex -> pdflatex` fallback if
   the local TinyTeX wrapper fails after the `WINDIR` and format-refresh steps.

   ```powershell
   if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   bibtex CRPTO_ijds_submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   ```

   The repeated `pdflatex` calls are not redundant: pass 1 creates `.aux`,
   BibTeX creates `.bbl`, pass 2 imports bibliography/citation data, and pass 3
   converges final references and pagination.

4. **Recount the official-template page budget** and demote body floats to the
   supplement only if the body exceeds 25 pages excluding references. The local
   official-template build is currently 26 pages total; Section 9 and References
   start on page 22. The Chrome-print body preview is only a verification proxy.
5. **Verify anonymity** against the checklist above, then upload the body PDF and
   submit the title page separately.
