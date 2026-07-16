# IJDS Submission Package

This directory is the pre-freeze anonymous IJDS handoff. The official TeX is
generated from `paper/CRPTO_ijds.qmd` and must not be edited directly.

## Authorities

- body: `paper/CRPTO_ijds.qmd`;
- supplement: `paper/supplement_ijds.qmd`;
- claim registry: `docs/research/active_claims_2026-07-14.md`;
- executable claim ledger: `configs/ijds_claim_ledger.yaml`;
- evidence registry: `configs/ijds_active_evidence_sources.yaml`;
- evidence manifest: `reports/crpto/ijds_binary_geometry_frontier_v4_evidence.json`;
- TeX generator: `scripts/build_ijds_submission_tex.py`;
- compiler: `scripts/compile_ijds_submission.py`.

The active study scans 2,925,493 raw rows and uses the exhaustive 640,543-loan
eligible design. It retains 376,890 primary OOT candidates, reconstructs
364,814 outcomes as observable by the cutoff, and bounds 12,076 unresolved
outcomes. Five retrospectively protocol-locked learner specifications support the coverage audit;
only CatBoost enters optimization. The decision audit reports five gamma
values, two rulers, three coordinates, exact declared point-cap supports, and
no winner. Evaluation-endpoint lags 0, 3, 6, 8, and 12 are reported without
selection; conformal-fit label timing is a separate sensitivity.

## IJDS Requirements

- IJDS-template PDF;
- at most 25 pages excluding references and appendices;
- separate online supplement;
- double-anonymous review;
- abstract no longer than 300 words;
- 1--10 keywords; and
- data/code disclosure at submission.

Recheck the official guidelines during submission week. Current links are in
`configs/crpto_publication_targets.yaml`.

## Build

```powershell
just submission-build
just submission-check
```

The first command writes active evidence and document outputs in causal order;
the second verifies them without replaying scientific evidence.
`build_ijds_submission_tex.py --check` rejects stale generated TeX.
`informs_style_assets.json` pins the local publisher kit. The compiler attempts
`latexmk`; when the Windows TinyTeX wrapper is unavailable it runs:

```text
pdflatex -> bibtex -> pdflatex -> pdflatex
```

The first `pdflatex` creates `.aux`, BibTeX creates `.bbl`, the second LaTeX
pass resolves citations and cross-references, and the final pass stabilizes
labels, floats, and pagination.

## QA Record

The pre-freeze closeout on 2026-07-15 produced the following current record:

- official PDF pages: `29`;
- pre-reference pages: `25` (references begin on page 26);
- body preview pages: `22`;
- supplement preview pages: `29`;
- abstract words: `249`;
- `.blg` warnings: `0`;
- undefined citations/references: `0`;
- page-level visual inspection: `80/80` pages across the official, body, and
  supplement PDFs; transient page renders were discarded after inspection;
- automated PDF inspection: one Letter page size per document, no blank page,
  and no author identity in the official PDF metadata.

## Acceptance Criteria

- the evidence source registry and manifest verify by hash;
- generated TeX is current with QMD;
- `.blg` has no warnings and `.log` has no undefined citations or labels;
- the pre-reference body is within the IJDS limit;
- all tables and figures are legible and inside margins;
- reviewer files contain no identity, local path, commit, tag, or hash;
- the abstract stays below 300 words;
- no retired endpoint or favorable `.25` claim returns; and
- scientific, drift, publication, compilation, and visual gates pass.

This is still pre-freeze. Final tagging and ScholarOne proof comparison require
an explicit later freeze decision.
