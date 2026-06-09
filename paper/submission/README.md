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
INFORMS class (`\documentclass[ijds,dblanonrev]{informs4}`). The source of
truth remains `paper/CRPTO_ijds.qmd`; the `.tex` is a synchronized submission
surface for the central IJDS body: title, abstract, keywords, core sections,
the new journal pipeline Figure 1, the bound-claim stack, alpha-gamma,
robust-region and regret-auditability figures, plus the core, exact-certificate,
champion-comparator, funded-set audit and regret tables. The
`informs2014.bst` + `../../book/references.bib` bibliography wiring is already
present. Journal figures use PDF/vector exports from `reports/crpto/figures/`
where possible; Figure 1 intentionally uses the PNG export because the vector
PDF crop box cuts the right edge under `informs4`.

> **`informs4` is not on CTAN/TeX Live.** The class and bibliography style are
> distributed through the INFORMS author portal or the IJDS Overleaf template.
> Local copies are allowed for compilation and are gitignored. Do not commit
> `informs4.cls`, `informs2014.bst`, template PDFs, `.sty` files, or generated
> LaTeX build artifacts.

Current local build state (verified 2026-06-09): TinyTeX/TeX Live 2026,
Strawberry Perl 5.42.2.1, and the `listingsutf8` TeX package compile
`CRPTO_ijds_submission.tex` to a 23-page official-template PDF. The only LaTeX
log warnings left are a small `\maketitle` overfull from the `informs4`
anonymous title block and one float-only page, both visually acceptable. The
body is comfortably inside the IJDS 25-page initial-submission budget even
before excluding references.

To produce the official submission PDF:

1. Download or refresh `informs4.cls` and `informs2014.bst` from the INFORMS
   author portal (or Overleaf) and drop them next to
   `CRPTO_ijds_submission.tex`. These are gitignored on purpose
   (`paper/submission/.gitignore`); do not commit them.
2. Build manually:

   ```powershell
   pdflatex CRPTO_ijds_submission
   bibtex   CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   ```

   Or use `latexmk` through the Perl script directly. The TinyTeX
   `latexmk.exe` wrapper can fail on this Windows install, but the script path
   is stable:

   ```powershell
   $env:Path = "C:\Strawberry\perl\bin;C:\Strawberry\perl\site\bin;C:\Strawberry\c\bin;$env:APPDATA\TinyTeX\bin\windows;$env:Path"
   Push-Location paper/submission
   perl "$env:APPDATA\TinyTeX\texmf-dist\scripts\latexmk\latexmk.pl" -pdf -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   Pop-Location
   ```

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
  current local official-template build is 23 pages.
- Keep A3--A34 in the online supplement unless a reviewer-facing argument needs
  one compact table in the body.
- Preserve CRPTO as the coverage/auditability method and SPO+ as the low-regret
  comparator.
- Cross-check every headline claim against `CLAIM_AUDIT_MATRIX.md`.
- Keep `CRPTO_ijds_submission.tex` synchronized with the QMD whenever the body
  adds or demotes a figure, table, theorem statement or major result paragraph.
- Regenerate previews with `just paper-submission` before release.
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
   pdflatex CRPTO_ijds_submission
   bibtex   CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   ```

4. **Recount the official-template page budget** and demote body floats to the
   supplement only if it exceeds 25 pages. The local official-template build is
   currently 23 pages; the Chrome-print body preview is only a verification
   proxy.
5. **Verify anonymity** against the checklist above, then upload the body PDF and
   submit the title page separately.
