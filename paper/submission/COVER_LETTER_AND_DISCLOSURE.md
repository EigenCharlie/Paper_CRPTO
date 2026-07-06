# IJDS Cover Letter and Disclosure Draft

This file is for the editor-facing submission package. It is not part of the
double-anonymous reviewer packet unless the submission system explicitly asks
for the corresponding disclosure fields.

## Cover Letter Core Paragraph

Dear Editors,

We submit "CRPTO: Conformal Robust Predict-Then-Optimize for Auditable Credit
Portfolio Decisions" for consideration at the INFORMS Journal on Data Science.
The paper studies credit allocation as data science for decisions rather than
as a predictive leaderboard. Its data component is a static Lending Club
out-of-time panel, supported by frozen Prosper and Freddie/Mendeley external
economic replications. Its method maps a frozen calibrated probability-of-default
artifact through Mondrian conformal intervals into a robust portfolio decision.
Its decision object is the funded set under a budget and risk cap, and its main
implication is an auditable model-risk surface: the promoted Lending Club body
point earns `$184.8K` on a `$1M` budget while passing an exact empirical
alpha-grid funded-set audit, and the declared pool93 finite-grid frontier
contains 50,010 deduplicated semantic policies with 27,508 all-alpha
above-floor policies.
An opt-in drift harness verifies that the prediction-to-decision certificate
chain regenerates bit-exactly from the frozen artifacts under the locked stack.
The contribution is intended for settings where decision auditability,
reproducibility, and model-risk governance matter as much as predictive rank.

## Data and Code Availability

The submission body and supplement are double-anonymous. During review, the
manuscript refers to a reproducible companion package without exposing
author-identifying URLs. The submission will complete the IJDS Data and Code
Disclosure Form and acknowledge the accepted-paper reproducibility workflow.
After the venue permits disclosure, the companion can include:

- public source code and Quarto manuscript sources;
- DVC metadata and pointers for processed artifacts and frozen model files;
- MLflow/DagsHub lineage for the CRPTO runs, subject to credential-free access
  rules;
- raw-data source instructions from `RAW_DATA_SOURCE_NOTES.md` rather than
  redistributed raw CSVs when source terms or file size make rehosting
  inappropriate;
- Prosper and Freddie/Mendeley source notes for the external replication layer;
- the frozen extraction manifest and guardrail tests used to verify the
  promoted frontier;
- the drift harness that recomputes the conformal interval and certificate
  chain from frozen PD artifacts with zero endpoint drift under the locked stack;
- commands for regenerating paper tables, figures, HTML previews, and local
  IJDS PDF verification drafts.

No secrets, tokens, private DVC credentials, or local machine paths should be
included in the reviewer packet.

If ScholarOne asks for the disclosure option in prose, the intended answer is:
code and manuscript sources are releasable after anonymity is lifted; raw data
are public-source or source-controlled and therefore disclosed through source
instructions plus DVC pointers/processed artifacts when the journal workflow and
source terms permit.

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

The highest-risk interpretive boundary is also stated explicitly in the paper:
the Lending Club exact funded-set certificate is an exact accounting audit on
the frozen promoted portfolio under a declared weighted-validity assumption. The
Prosper and Freddie/Mendeley results are external economic replications and
exhaustiveness audits, not new exact funded-set certificates or prospective live
deployment guarantees.
