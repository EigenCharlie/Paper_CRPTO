# Quarto extensions for the CRPTO book

This directory holds Quarto extensions installed via `quarto add <repo>`. The
project currently relies on Quarto built-ins (lightbox, code-fold, hover refs,
etc.) and does not require any extension to render.

The list below documents the **recommended** extensions for an academic book of
this kind. Install only the ones you need; each one adds metadata to
`_extensions/<name>/_extension.yml` and an entry in `.gitignore`-tracked
directories.

## Recommended

```bash
# Run from the repository root.

# Glossary support — useful for CRPTO terminology (PD, ECE, V(α), Γ_CP, MRM, SR 11-7).
quarto add coatless/quarto-glossary

# Embed snippets from src/ directly into chapters without copy-paste.
quarto add quarto-ext/include-code-files

# Iconify icons for chapter cards and callouts (decorative).
quarto add mcanouil/quarto-iconify

# Pretty typesetting of LaTeX, BibTeX, X̄ symbols.
quarto add quarto-ext/fancy-text
```

## Journal templates (install ONE when you choose a target journal)

```bash
quarto add quarto-journals/elsevier
quarto add quarto-journals/acm
quarto add quarto-journals/springer
```

After installing a template, add the appropriate format block to
`_quarto.yml`, e.g. `format: { elsevier-pdf: default }`.

## Why we did not install these automatically

`quarto add` requires:

1. The Quarto CLI to be in `PATH` (it should be).
2. Internet access to fetch the extension from GitHub.
3. A clean git working tree (it modifies files and the commit history).

Because the project is being prepared for a first GitHub push, we are leaving
the extension installation to the user so the initial commit history remains
predictable.

## Built-ins already in use

- **Lightbox**: `lightbox: auto` in `_quarto.yml` (Quarto 1.5+).
- **Hover citations / cross-refs**: `citations-hover: true`, `crossrefs-hover: true`.
- **Code folding and tools**: `code-fold: show`, `code-tools: { toggle: true }`.
- **APA bibliography**: `csl: apa.csl` + `bibliography: references.bib`.
- **Dark mode**: `theme: { light: ..., dark: darkly }`.
- **`df-print: paged`**: paged tables in HTML.
