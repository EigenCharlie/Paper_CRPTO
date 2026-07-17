# CRPTO Manuscript Workspace

This directory contains one active IJDS manuscript and one online supplement.

## Active Sources

- Claim registry: `../docs/research/active_claims_2026-07-14.md`.
- Evidence source registry: `../configs/ijds_active_evidence_sources.yaml`.
- Paper-facing evidence: `../reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`.
- Canonical body: `CRPTO_ijds.qmd`.
- Canonical supplement: `supplement_ijds.qmd`.
- Generated official TeX: `submission/CRPTO_ijds_submission.tex`.

The paper is a retrospective identification audit of one integrated
ML--conformal--optimization pipeline. The distributed archive is not a verified
point-in-time snapshot, so the endpoint is reconstructed as observable by the
declared cutoff. All 376,890 primary candidates remain in the menus; 364,814
are resolved and 12,076 enter sharp binary bounds. No learner, window, gamma,
ruler, coordinate, comparator, or policy is selected.

Earlier manuscript versions are outside the active capsule and preserved in
Git history and `D:\crpto_legacy`. `CRPTO_ijds.qmd` is the only body source;
never edit generated TeX directly.

## Build

```powershell
just submission-build
```

The official compiler attempts `latexmk`; its robust fallback is
`pdflatex -> bibtex -> pdflatex -> pdflatex`. The first LaTeX pass writes the
auxiliary graph, BibTeX writes the bibliography, and the final two passes
resolve citations, labels, floats, and pagination.

## Validation

```powershell
just ijds-active-check
just paper-tex-check
just paper-official-scan
just validate-champion
just type-check
just type-check-fast
git status --short
```

Page counts and visual QA records belong in `submission/README.md` and must be
regenerated after substantive edits. The project remains pre-freeze until an
explicit submission-freeze decision.

`submission-build` writes paper-facing evidence and document outputs in causal
order. `submission-check` and `ijds-active-check` verify the current outputs
without replaying evidence or a scientific protocol.
