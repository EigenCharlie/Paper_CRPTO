# IJDS Submission Roadmap - Target 2026-08-10

The date is an internal quality gate; IJDS submissions are rolling. Recheck
official submission, reviewer, data/code, and LaTeX guidance during submission
week.

## Submission Thesis

| IJDS dimension | CRPTO answer |
|---|---|
| Data | 540,121-loan status-independent 36-month universe with unresolved outcomes retained |
| Method | Exact binary split-Mondrian intervals, one frozen guardrail, comparator nesting, sharp bounds, and transport decomposition |
| Decision | Fifteen separate monthly $1M allocations with coherent payoff and development-risk-matched point PD |
| Evidence | Same-threshold default benefit reverses after alignment; selected result robust, family 7/9 |
| Latest PDF QA | Official 22 pages (references p. 19); body 22; supplement 21; 12 tables and 4 figures |
| Implication | Marginal coverage is not selected-decision validity, and equal numeric caps are not equal decision stringency |

## Completed Reconstruction

- Replaced outcome-conditioned candidate membership with an issue-date/term
  universe that retains unresolved states.
- Removed post-period labels from model, calibration, and conformal fitting.
- Replaced the pooled future menu with fresh monthly decisions.
- Aligned expected and realized standardized payoff.
- Locked the 2012H2 selector before primary evaluation.
- Added sharp single-policy and union-based pairwise bounds.
- Added the binary miscoverage identity and exact selection-transport
  decomposition.
- Recovered the closest-work boundary, four exact propositions, comparator
  inversion, and a nine-question managerial audit card.
- Executed the maturity-safe parent from a clean tagged commit and DVC-tracked
  its processed and model/result directories.
- Executed the post hoc comparator audit from a separate clean tagged commit,
  DVC-tracked both outputs, and generated a byte-idempotent evidence bundle.
- Rebuilt body, supplement, official TeX, cover letter, disclosures, claim
  matrix, publication config, and active claim registry.
- Demoted compact-v7 A35--A40 and A1--A34 diagnostics to historical provenance.

## Submission Closeout

| Window | Deliverable | Exit condition |
|---|---|---|
| Jul 10--14 | Numerical and code closeout | Complete; rerun the final gate after the anonymity edits |
| Jul 14--18 | PDF QA | Complete once the final rebuilt PDFs pass text and visual anonymity scans |
| Jul 18--24 | Clean-clone capsule | Complete once the final commit is pulled and evidence rebuilt from a fresh clone |
| Jul 25--31 | Independent cold review | Two independent passes completed; findings reconciled in the final audit memo |
| Aug 1--8 | Editor package | Complete except author-supplied affiliation, ORCID status, and transfer of prepared responses into the publisher PDF |
| Aug 9--10 | ScholarOne freeze | Author uploads files, inspects the generated proof, and submits only after the go/no-go checklist |

## Acceptance Risks

| Risk | Current mitigation |
|---|---|
| Negative result appears insufficiently novel | Lead with comparator non-invariance, maturity-safe design, sharp bounds, and decision-validity implication |
| Binary intervals are broad | Report width, endpoint saturation, binary geometry, and OOT coverage failure |
| Adaptive selection invalidates coverage | Make this the central finding; do not imply selected-set validity |
| Standardized payoff is mistaken for return | Use the exact formula and explicit cash-flow/IRR limitation everywhere |
| Retrospective tuning concern | State that prior work inspected history; call v2 code-locked, not preregistered or pristine |
| Comparator cherry-picking | Disclose post hoc timing; lock low/mean/high, all 15 LOMO rows, and complete 3x3 census |
| Development matching is treated as uniquely correct | State that it aligns one funded-risk moment and does not equate feasible sets |
| Selected result is overgeneralized | Report family direction 7/9 and retain both ambiguous rows |
| Censoring weakens inference | Keep all rows; use sharp bounds; isolate the heavily censored extension |
| Historical results leak back | Active sync tests forbid compact-v7 headline values on publication surfaces |
| Tooling is mistaken for novelty | Reproducibility supports the empirical claim; it is not the headline contribution |

## Freeze Rule

Do not retune the guardrail, model, payoff, dates, or bounds on 2016--2017
outcomes. Reopen only for a concrete reviewer request or a separately committed
and tagged protocol with a different estimand. A marginally better result is not
permission to create CRPTO v2 or a second paper.
