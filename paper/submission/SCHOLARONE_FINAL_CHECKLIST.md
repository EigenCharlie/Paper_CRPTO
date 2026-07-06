# ScholarOne Final Checklist

Use this checklist only after the paper content is frozen and the official IJDS
template files have been downloaded outside Git.

## Files to Prepare

| File | Source | Reviewer-facing? | Status |
|---|---|:---:|---|
| Anonymous manuscript PDF | `CRPTO_ijds_submission.tex` compiled with `informs4` and `dblanonrev`. | Yes | Source synchronized with pool93 A35--A39 and the dual-tag provenance passages; local official-template build verified 2026-07-06 (26 pages total; conclusion and references start on p. 22); final ScholarOne proof pending |
| Anonymous online supplement PDF | `paper/supplement_ijds.qmd` rendered and visually checked. | Yes | Local render and page QA pass; final ScholarOne proof pending |
| Separate title page | `TITLE_PAGE_DRAFT.md` converted into the ScholarOne/title-page format. | No | Pending ScholarOne copy |
| Data and Code Disclosure Form | Official IJDS form using `DATA_CODE_DISCLOSURE_FORM_DRAFT.md`. | Editor/system | Pending official form entry |
| Cover letter | `COVER_LETTER_AND_DISCLOSURE.md`, shortened if ScholarOne text boxes are tight. | Editor | Draft ready; final text-box copy pending |
| Optional reproducibility note | `REPRODUCIBILITY_PACKAGE.md` or excerpted text if requested. | Editor/system | Optional |

## Official Template Build

1. Download or refresh `informs4.cls` and `informs2014.bst` from INFORMS/Overleaf.
2. Regenerate/synchronize `CRPTO_ijds_submission.tex` from the pool93 A35--A39 QMD source.
3. Place the template files next to `CRPTO_ijds_submission.tex`; local gitignored copies are already present.
4. Build with `latexmk` when the local TinyTeX wrapper works:

   ```powershell
   latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
   ```

   If PowerShell/TinyTeX fails with `runscript.tlu`/`nil`, use the proven
   fallback:

   ```powershell
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   bibtex CRPTO_ijds_submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   ```

5. Confirm body page count is at most 25 pages excluding references and
   appendices. The local official-template build verified on 2026-07-06 is 26
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
