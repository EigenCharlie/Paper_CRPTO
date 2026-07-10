# IJDS Submission Roadmap - Target 2026-08-10

The date is an internal quality gate; IJDS submissions are rolling. Recheck
official submission, reviewer, data/code, and LaTeX guidance during submission
week.

## Submission Thesis

| IJDS dimension | CRPTO answer |
|---|---|
| Data | 540,121-loan status-independent 36-month universe with unresolved outcomes retained |
| Method | Exact binary split-Mondrian intervals, one linear upper-score guardrail, sharp outcome bounds, and transport decomposition |
| Decision | Fifteen separate monthly $1M credit allocations with coherent payoff and matched point-PD baselines |
| Evidence | Default improves, payoff and funded coverage worsen, with mechanism and temporal reversals exposed |
| Implication | Marginal conformal coverage is not a selected-decision guarantee; the guardrail acts mainly through composition |

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
- Executed the final protocol from a clean tagged commit and DVC-tracked both
  active run directories.
- Rebuilt body, supplement, official TeX, cover letter, disclosures, claim
  matrix, publication config, and active claim registry.
- Demoted compact-v7 A35--A40 and A1--A34 diagnostics to historical provenance.

## Remaining Submission Work

| Window | Deliverable | Exit condition |
|---|---|---|
| Jul 10--14 | Numerical and code closeout | Evidence idempotent; full tests, lint, mypy, ty and protected-manifest gate green |
| Jul 14--18 | PDF QA | Body, supplement and 16-page official PDF inspected page by page; no overflow or identity leak |
| Jul 18--24 | Clean-clone capsule | DVC pull and active evidence rebuild succeed from a fresh clone |
| Jul 25--31 | Independent cold review | Read only PDFs; reconcile every number, caption, citation and limitation |
| Aug 1--8 | Editor package | Title page, cover letter, disclosure form and sanitized archive finalized |
| Aug 9--10 | ScholarOne freeze | Upload, inspect generated proof, and submit only after go/no-go checklist |

## Acceptance Risks

| Risk | Current mitigation |
|---|---|
| Negative result appears insufficiently novel | Lead with maturity-safe design, sharp bounds, transport mechanism, and decision-validity implication |
| Binary intervals are broad | Report width, endpoint saturation, binary geometry, and OOT coverage failure |
| Adaptive selection invalidates coverage | Make this the central finding; do not imply selected-set validity |
| Standardized payoff is mistaken for return | Use the exact formula and explicit cash-flow/IRR limitation everywhere |
| Retrospective tuning concern | State that prior work inspected history; call v2 code-locked, not preregistered or pristine |
| Comparator cherry-picking | Report matched and independently selected point policies; allocations coincide |
| Censoring weakens inference | Keep all rows; use sharp bounds; isolate the heavily censored extension |
| Historical results leak back | Active sync tests forbid compact-v7 headline values on publication surfaces |
| Tooling is mistaken for novelty | Reproducibility supports the empirical claim; it is not the headline contribution |

## Freeze Rule

Do not retune the guardrail, model, payoff, dates, or bounds on 2016--2017
outcomes. Reopen only for a concrete reviewer request or a separately committed
and tagged protocol with a different estimand. A marginally better result is not
permission to create CRPTO v2 or a second paper.
