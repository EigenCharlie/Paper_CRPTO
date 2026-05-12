# paper-crpto Manuscript Workspace

This folder contains the manuscript extraction layer for the standalone CRPTO
paper. The Quarto book remains the full companion dossier; this folder is where
the submission-shaped versions are written.

## Current Venue Decision

- Primary target: INFORMS Journal on Data Science.
- Secondary pivot: European Journal of Operational Research.
- Config source: `../configs/crpto_publication_targets.yaml`.
- Strategy memo: `../docs/research/crpto_publication_strategy_2026-05-12.md`.

## Files

- `CRPTO.qmd`: generic landing manuscript stub.
- `CRPTO_ijds.qmd`: IJDS-style anonymous body draft.
- `supplement_ijds.qmd`: IJDS-style online supplement scaffold.

## Render Commands

```bash
just paper-ijds
just paper-ijds-supplement
just paper-submission
```

The final submission PDF should use the official venue template. These Quarto
files are the writing source of truth until the target template is installed.
