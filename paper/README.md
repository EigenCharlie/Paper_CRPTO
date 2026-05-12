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
- `CRPTO_ijds.qmd`: IJDS-style anonymous body source.
- `supplement_ijds.qmd`: IJDS-style online supplement source.

P2/P3 backlog items are not part of the current paper. The active submission is
the frozen CRPTO result plus supplement evidence generated from existing
artifacts; future online, causal, multi-distribution, production, or package
tracks are discussed only as future work.

## Render Commands

```bash
just paper-ijds
just paper-ijds-supplement
just paper-submission
```

The final submission PDF should use the official venue template. These Quarto
files are the writing source of truth until the IJDS LaTeX template is applied
with double-anonymous settings.
