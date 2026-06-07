# CRPTO paper spine checklist - 2026-06-01

Purpose: keep the IJDS body, supplement, Quarto companion, artifacts, and tests
aligned while the manuscript keeps improving.

| Claim | Paper location | Evidence surface | Guardrail |
|---|---|---|---|
| CRPTO is an auditable conformal robust credit-portfolio decision built from frozen calibrated PD artifacts. | `paper/CRPTO_ijds.qmd`, Introduction and Related Work. | Fig. 12, closest-work table, chapter 24 bibliography map. | Do not rephrase as first conformal credit paper or AUC leaderboard. |
| The PD layer is good enough because it is calibrated for downstream decision use. | Results and Method. | AUC, Brier, ECE, model contract, calibration artifacts. | Keep AUC secondary to calibration and decision utility. |
| Conformal intervals are decision inputs, not decorative uncertainty plots. | Method, Theory, Results. | Alpha-gamma figure, `V(alpha)`, `Gamma_CP`, exact alpha check. | Do not imply exact conditional coverage by borrower profile. |
| The champion is selected inside an exact alpha-safe robust region. | Results. | Robust return `$170,464.54`, `45/45` region, exact pass. | Do not rerun `bound_exact_eval` or HPO without a new protocol. |
| SPO+ is a valid low-regret comparator but not the same governance object. | Robustness and Comparators. | A19/Fig. 15, regret-auditability frontier. | Do not claim CRPTO dominates DFL on regret. |
| A20--A34 strengthen the journal story without promoting a new champion. | Supplement. | Tail, satisficing, cluster, CVaR/OCE, MDCP/ACI diagnostics, Prosper/Freddie replication and price-of-robustness scaling. | Keep challenger/external diagnostics distinct from official policy. |
| Fairness and MRM are governance diagnostics, not legal certification. | Discussion and supplement Appendix D. | Proxy/intersectional audits, MRM boundary text. | Direct protected-attribute claims stay out of scope. |
| Pages is a paper companion, not a submission package. | Book landing and chapter routes. | Build metadata, reading routes, bibliography map. | Submission conversion remains a later phase. |

## Pre-polish checks

- Every new paper claim must point to at least one table, figure, artifact, or
  appendix row.
- Every future-work sentence must say whether it is diagnostic-safe or
  method-changing.
- Every new citation in the body must either sharpen the novelty boundary or
  support a limitation.
- Every Pages-facing route should answer a visitor question: paper, thesis,
  supplement, bibliography, or future work.
