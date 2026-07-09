# ScholarOne Final Checklist

Use this checklist only after the paper content is frozen and the official IJDS
template files have been downloaded outside Git.

## Files to Prepare

| File | Source | Reviewer-facing? | Status |
|---|---|:---:|---|
| Anonymous manuscript PDF | `CRPTO_ijds_submission.tex` compiled with `informs4` and `dblanonrev`. | Yes | Local file ready. Official-template build verified 2026-07-07 (26 pages total; `.blg` warnings 0; `.log` has no undefined citations/references; source/metadata anonymity checks clean). Final ScholarOne proof remains a system-side gate. |
| Anonymous online supplement PDF | `paper/supplement_ijds.qmd` rendered and visually checked. | Yes | Local render and representative page QA verified 2026-07-07; source/metadata anonymity checks clean; final ScholarOne proof pending |
| Separate title page | `TITLE_PAGE_DRAFT.md` converted into the ScholarOne/title-page format. | No | Draft ready for separate upload/copy; complete affiliation and ORCID in ScholarOne if applicable. |
| Data and Code Disclosure Form | Official IJDS form using `DATA_CODE_DISCLOSURE_FORM_DRAFT.md`. | Editor/system | Draft language ready; official ScholarOne form entry remains manual. |
| Cover letter | `COVER_LETTER_AND_DISCLOSURE.md`, shortened if ScholarOne text boxes are tight. | Editor | Draft ready; final paste/proof inside ScholarOne remains manual. |
| Optional reproducibility note | `REPRODUCIBILITY_PACKAGE.md` or excerpted text if requested. | Editor/system | Optional |

## Official Template Build

1. Download or refresh `informs4.cls` and `informs2014.bst` from INFORMS/Overleaf.
2. Synchronize `CRPTO_ijds_submission.tex` manually from the pool93 A35--A40
   QMD source while preserving the official-template compaction.
3. Place the template files next to `CRPTO_ijds_submission.tex`; local gitignored copies are already present.
4. Build with `latexmk`. In Codex/PowerShell sessions where `WINDIR` is absent,
   initialize it first:

   ```powershell
   if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
   latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
   ```

   If LaTeX reports a support-file mismatch after a TeX Live update, run
   `fmtutil-sys --byfmt pdflatex` once with the same `WINDIR` initialization.
   If PowerShell/TinyTeX still fails, use the proven fallback:

   ```powershell
   if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   bibtex CRPTO_ijds_submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   ```

   The three `pdflatex` passes are intentional: the first creates `.aux`,
   BibTeX creates `.bbl`, the second imports bibliography and cross-reference
   data, and the third stabilizes references and pagination.

5. Confirm body page count is at most 25 pages excluding references and
   appendices. The local official-template build verified on 2026-07-07 is 26
   pages total; Section 9 (Conclusion) and References both start on page 22, so
   the manuscript remains comfortably inside the IJDS page budget when
   references are excluded. Recount after every official rebuild.

## Final Local Gates

```powershell
just lint
just smoke
just validate-champion
uv run pytest tests/test_publication_targets.py -q
uv run dvc status --no-updates
just paper-submission-pdf
```

Last local closeout on 2026-07-07: `just lint`, `just smoke`,
`just validate-champion`, `uv run pytest tests/test_publication_targets.py -q`,
`uv run pytest tests/test_pool93_body_claim_sync.py -q`,
`just paper-submission-pdf`, and `latexmk -pdf -gg -interaction=nonstopmode
CRPTO_ijds_submission.tex` passed. Representative PDF pages were rendered
locally for body/supplement/submission visual QA.

`uv run dvc status --no-updates` is intentionally treated as a pipeline-state
report, not a submission blocker. On 2026-07-07 it reported modified deps/outs
for protected and paper/book stages from earlier code/book work, while
`just validate-champion` remained green. Do not resolve that status by
rerunning protected stages during ScholarOne closeout; open a separate pipeline
debt task after submission if needed.

## QMD-vs-TeX Freeze Rule

`paper/CRPTO_ijds.qmd` remains the long-form narrative source. The official
`CRPTO_ijds_submission.tex` is a manually compacted INFORMS-template handoff
surface. After freeze, port substantive claim edits from QMD to TeX deliberately
and recompile; do not regenerate the `.tex` mechanically unless you are prepared
to redo the page-budget and visual QA.

## Anonymous PDF QA

- Body PDF has no author names, affiliation, acknowledgements, public repo URLs,
  DagsHub/MLflow URLs, local paths, or hidden PDF metadata that identifies the
  author.
- Supplement PDF has no author names, affiliation, acknowledgements, public repo
  URLs, DagsHub/MLflow URLs, local paths, or hidden PDF metadata.
- References render correctly with `informs2014.bst`.
- Figures are readable in grayscale or black-and-white printing.
- Tables do not overflow page margins.
- Captions state the takeaway and do not overclaim exact validity.
- Prosper/Freddie text remains labeled as external economic replication, not as
  new exact funded-set certificates.

## ScholarOne Proof QA

ScholarOne generates a proof after upload. Before final submission:

- **Go/no-go gate:** the ScholarOne-generated proof must be visually checked
  before final submission. Broken proof, missing figures, wrong file order,
  title-page leakage, or anonymous-body identity leakage means **NO-GO**:
  retract, repair locally, regenerate, and upload again.
- Open the generated proof, not only the local PDF.
- Recheck title, abstract, keywords, file order, supplement designation, and
  Data/Code Disclosure fields.
- Confirm the title page is not included in the anonymous reviewer PDF.
- Confirm the supplement is designated as online supplemental material.
- Confirm no optional file accidentally reveals identity to reviewers.
