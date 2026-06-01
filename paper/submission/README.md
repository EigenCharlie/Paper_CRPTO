# IJDS Submission Package

This directory is the handoff checklist for the IJDS submission surfaces. The
source of truth remains:

- `paper/CRPTO_ijds.qmd` for the anonymous manuscript body.
- `paper/supplement_ijds.qmd` for the anonymous online supplement.

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

## Official Template Sources

- INFORMS author portal: <https://pubsonline.informs.org/authorportal/latex-style-files>
- IJDS submission guidelines: <https://pubsonline.informs.org/page/ijds/submission-guidelines>
- Overleaf template page: <https://www.overleaf.com/latex/templates/template-for-informs-journal-on-data-science/sbthszxgycfn>

Do not vendor private template downloads, reviewer forms, or authenticated
publisher material into this repository. Keep only public links and the
conversion notes needed to reproduce the submission package.

## Official LaTeX Submission Build

`CRPTO_ijds_submission.tex` is the official-template handoff draft in the
INFORMS class (`\documentclass[ijds,dblanonrev]{informs4}`). The source of
truth remains `paper/CRPTO_ijds.qmd`; the `.tex` is a synchronized submission
surface for the central IJDS body: title, abstract, keywords, core sections,
the new journal pipeline Figure 1, the bound-claim stack, alpha-gamma,
robust-region and regret-auditability figures, plus the core, exact-certificate,
champion-comparator, funded-set audit and regret tables. The
`informs2014.bst` + `../../book/references.bib` bibliography wiring is already
present. The only missing inputs are the publisher class/style files.

> **`informs4` is not on CTAN/TeX Live.** A `tlmgr`/CTAN search returns no
> package; the class and style are distributed only through the INFORMS author
> portal (or the IJDS Overleaf template). The `.tex` therefore cannot be compiled
> in this repo's TinyTeX until those files are downloaded — this is expected, not
> a defect.

Page budget: the Quarto proxy body currently renders to 15 pages including
references, with an estimated body-before-references length of ~12.4 pages (see
`docs/research/crpto_ijds_page_budget_2026.md`). The binding task is now
**polish**, not compression: keep the claim surgical, captions assertive, and
the QMD/official-template surfaces synchronized before a real submission build.

To produce the official submission PDF:

1. Download `informs4.cls` and `informs2014.bst` from the INFORMS author portal
   (or Overleaf) and drop them next to `CRPTO_ijds_submission.tex`. These are
   gitignored on purpose (`paper/submission/.gitignore`) — do not commit them.
2. Build:

   ```bash
   pdflatex CRPTO_ijds_submission
   bibtex   CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   pdflatex CRPTO_ijds_submission
   ```

3. The `dblanonrev` option keeps the body anonymous; verify against the anonymity
   checklist below before uploading.

## Anonymity Checklist

- Manuscript metadata uses `author: "Anonymous"`.
- Supplement metadata uses `author: "Anonymous"`.
- Public GitHub, DVC, MLflow, DagsHub and personal URLs are described as a
  companion package but not exposed in the double-anonymous body.
- Title-page, acknowledgements and repository disclosure are kept for the cover
  letter or for post-acceptance policy, not the anonymous manuscript.
- Local paths, parent-project paths and usernames do not appear in the submitted
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

- Recheck the official-template page budget after PDF pagination is available.
- Keep A3--A24 in the online supplement unless a reviewer-facing argument needs
  one compact table in the body.
- Preserve CRPTO as the coverage/auditability method and SPO+ as the low-regret
  comparator.
- Keep `CRPTO_ijds_submission.tex` synchronized with the QMD whenever the body
  adds or demotes a figure, table, theorem statement or major result paragraph.
- Regenerate previews with `just paper-submission` before release.
- Run the repository gates: `just lint`, `just smoke`, `just validate-champion`.
