# ScholarOne Final Checklist

Use this checklist only after the paper content is frozen and the official IJDS
template files have been downloaded outside Git.

## Files to Prepare

| File | Source | Reviewer-facing? | Status |
|---|---|:---:|---|
| Anonymous manuscript PDF | `CRPTO_ijds_submission.tex` compiled with `informs4` and `dblanonrev`. | Yes | Local build and visual QA pass; final ScholarOne proof pending |
| Anonymous online supplement PDF | `paper/supplement_ijds.qmd` rendered and visually checked. | Yes | Local render and page QA pass; final ScholarOne proof pending |
| Separate title page | `TITLE_PAGE_DRAFT.md` converted into the ScholarOne/title-page format. | No | TODO |
| Data and Code Disclosure Form | Official IJDS form using `DATA_CODE_DISCLOSURE_FORM_DRAFT.md`. | Editor/system | TODO |
| Cover letter | `COVER_LETTER_AND_DISCLOSURE.md`, shortened if ScholarOne text boxes are tight. | Editor | Draft ready; final text-box copy pending |
| Optional reproducibility note | `REPRODUCIBILITY_PACKAGE.md` or excerpted text if requested. | Editor/system | Optional |

## Official Template Build

1. Download or refresh `informs4.cls` and `informs2014.bst` from INFORMS/Overleaf.
2. Place them next to `CRPTO_ijds_submission.tex`; local gitignored copies are already present.
3. Build:

   ```powershell
   pdflatex CRPTO_ijds_submission
   bibtex CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   ```

4. Confirm body page count is at most 25 pages excluding references and
   appendices. The local official-template build is currently 23 pages total.

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

- Open the generated proof, not only the local PDF.
- Recheck title, abstract, keywords, file order, supplement designation, and
  Data/Code Disclosure fields.
- Confirm the title page is not included in the anonymous reviewer PDF.
- Confirm the supplement is designated as online supplemental material.
- Confirm no optional file accidentally reveals identity to reviewers.
