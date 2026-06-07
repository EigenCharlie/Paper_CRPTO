# paper-crpto Quarto Design Practices - 2026-05-12

This note records the Quarto practices retained from the historical book and adapted
for the independent `Paper_CRPTO` repository.

## Purpose

The standalone book is not only a manuscript preview. It is the public companion
for paper-crpto: paper-ready narrative, journal appendix, reviewer evidence,
artifact traceability and future-work boundaries in one place.

The short paper should compress this material later. The book should preserve
the reasoning, caveats and reproducibility paths that would be too long for a
submission PDF.

## Practices Kept

- Keep a whole-game landing page before the detailed chapters: central question,
  diagram, mini-abstract, champion statement and route table.
- Keep chapter cards and a curated navigation grid so reviewers can enter by
  paper, journal appendix, technical audit or future-work route.
- Keep search context, page navigation, repository actions and sidebar tools in
  `book/_quarto.yml`; this matters more for a public companion than for a local
  thesis draft.
- Keep dark/light themes and explicit CSS for tables, figures, sidebars and
  overflow. GitHub Pages should not depend on the viewer having the same local
  browser or notebook width as the author.
- Keep `execute.freeze: auto`: publication renders should not silently recompute
  the champion, but intentional page changes can refresh their own frozen
  outputs.
- Keep local PDF/Typst as optional targets. GitHub Pages renders HTML with
  `--no-execute`; the final journal PDF should be built deliberately when the
  venue is known.
- Use callouts for scope, caveats, reviewer warnings and artifact ownership.
- Keep figures in project-owned paths (`reports/crpto/figures/` and
  `book/assets/figures/`) and avoid remote-only media.

## Practices Not Ported

- Streamlit/showcase navigation from the historical workspace is not part of the
  public CRPTO companion. It remains product/P3 work unless a venue asks for an
  interactive dashboard.
- Paper 2, causal, survival/IFRS9 and research-lab navigation are not book
  sections here. They can appear only as future-work context.
- The old monorepo alphabetic chapter labels are retired. The standalone book
  uses semantic chapter names: `01-introduccion.qmd` through
  `14-release.qmd`, followed by the extended dossier chapters `15`--`23`.
- Automatic PDF downloads are not enabled in GitHub Pages until the workflow
  builds a PDF artifact with a known TeX/Typst toolchain.

## Render Policy

- Public render: `uv run -- quarto render book --to html --no-execute`.
- Local full validation: run the CRPTO smoke tests first, then render the book.
- Full-book PDF: intentionally deferred. The HTML book is the canonical live
  dossier; `CRPTO.pdf` is too large and layout-fragile to maintain before the
  thesis section set and APA layout are fixed. Keep local PDF work focused on
  `CRPTO_ijds.pdf` and `supplement_ijds.pdf`.

## Design Rule

The book can be richer than the paper, but it must not be noisier than the
evidence. Any new section should answer one of four questions:

- What claim does this support?
- What artifact or script reproduces it?
- What reviewer objection does it answer?
- What future-work boundary does it protect?
