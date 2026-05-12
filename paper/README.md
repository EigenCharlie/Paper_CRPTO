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

Selected P2/P3-inspired diagnostics are part of the current paper/journal pack:
regret-auditability, OCE/CVaR tail risk, robust satisficing margins, and the
dependence-aware caveat. The active submission still uses the frozen CRPTO
result plus supplement evidence generated from existing artifacts; future
online, causal, multi-distribution, multi-dataset, production, or package tracks
remain future work.

## Render Commands

```bash
just paper-ijds
just paper-ijds-supplement
just paper-submission
```

The final submission PDF should use the official venue template. These Quarto
files are the writing source of truth until the IJDS LaTeX template is applied
with double-anonymous settings.

## Closeout Gates

Before tagging a submission release, do a final sweep for stale numbers,
captions, body-vs-supplement placement, and IJDS length. Keep public GitHub,
DagsHub, and MLflow links anonymized in the manuscript unless the venue policy
or cover-letter disclosure requires otherwise.
