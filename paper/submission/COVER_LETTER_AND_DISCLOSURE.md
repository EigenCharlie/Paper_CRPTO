# IJDS Cover Letter and Disclosure Draft

This file is for the editor-facing submission package. It is not part of the
double-anonymous reviewer packet unless the submission system explicitly asks
for the corresponding disclosure fields.

## Cover Letter Core Paragraph

Dear Editors,

We submit "CRPTO: Conformal Robust Predict-Then-Optimize for Auditable Credit
Portfolio Decisions" for consideration at the INFORMS Journal on Data Science.
The paper studies credit allocation as a data-science decision pipeline rather
than as a predictive leaderboard. Starting from a frozen calibrated probability
of default artifact, CRPTO maps Mondrian conformal intervals into a robust
portfolio decision, certifies the promoted funded set with an exact
alpha-safe audit, and reports external frozen replications on Prosper and
Freddie/Mendeley panels without reopening the Lending Club champion search.
The contribution is intended for settings where decision auditability,
reproducibility, and model-risk governance matter as much as predictive rank.

## Data and Code Availability

The submission body and supplement are double-anonymous. During review, the
manuscript refers to a reproducible companion package without exposing
author-identifying URLs. After the venue permits disclosure, the companion can
include:

- public source code and Quarto manuscript sources;
- DVC metadata and pointers for processed artifacts and frozen model files;
- MLflow/DagsHub lineage for the CRPTO runs, subject to credential-free access
  rules;
- raw Lending Club source instructions rather than redistributed private data;
- the frozen extraction manifest and guardrail tests used to verify the
  promoted champion;
- commands for regenerating paper tables, figures, HTML previews, and local
  IJDS PDF verification drafts.

No secrets, tokens, private DVC credentials, or local machine paths should be
included in the reviewer packet.

## Double-Anonymous Handling

- Upload `paper/CRPTO_ijds.pdf` as the local body preview only if the official
  template PDF is not yet required.
- Upload `paper/supplement_ijds.pdf` as the local supplement preview only if
  the official workflow accepts HTML-print verification drafts.
- Keep public repository, DagsHub, MLflow, personal site, affiliation, and
  author-identifying acknowledgements out of reviewer-facing files.
- Use this file or the submission system fields for disclosure timing, not the
  anonymous manuscript body.

## Editorial Fit

The paper is positioned as data science for decisions: conformal prediction is
not only an uncertainty report, and robust optimization is not only a portfolio
heuristic. The central object is an executable, auditable decision recipe whose
numbers are backed by frozen artifacts, manifest regression tests, and
submission-ready tables and figures.
