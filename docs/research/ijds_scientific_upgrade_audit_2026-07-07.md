# IJDS scientific upgrade audit - 2026-07-07

Scope: decide which high-upside CRPTO extensions can strengthen the current
paper as framing, diagnostics, or limitations, and which would require a new
research result before promotion.

## Decision

The current IJDS paper should not promote a new selector, learner, conformal
protocol, or external certificate before submission. It should, however, make
the upgrade boundary explicit. This turns likely reviewer questions into a
strength of the paper: CRPTO is an auditable post-hoc decision certificate over
frozen evidence, and the supplement shows where stronger future certificates
would enter.

## Changes applied

- Added a body-level scientific upgrade map in `paper/CRPTO_ijds.qmd`.
- Ported the same map to the official submission `.tex`.
- Added a longer supplement section that separates paper improvements available
  now from evidence required for promotion.
- Updated the active claim registry so the recommended body wording says
  "selected policy" rather than "selected pool93 body point".

## What can improve the current paper without a new run

| Upgrade | Current-paper use |
|---|---|
| Tail-aware selection | Present A20--A22 and A37 as tail-profile and challenger diagnostics, not selectors. |
| Prospective/nested selection | Use A3, A9, and A35 denominators to answer post-selection concerns. |
| Multi-distribution validity | Use A23 to show which grade/vintage cells are stable or thin. |
| Online validity | Use A24 as a static OOT replay, not as live control. |
| Decision-focused learning | Use A19 to show the regret-auditability frontier. |
| Causal decision layer | Keep as a limitation and future protocol, not a claim. |

## What would become a new research result

A new result is required if the paper wants to claim any of the following:

1. CVaR/OCE is the promoted selector rather than a diagnostic.
2. The selected policy comes from a fully prospective search/evaluation design.
3. The conformal layer targets multi-distribution, group-weighted, or online
   validity as its promoted guarantee.
4. The PD model is trained end-to-end through the optimizer.
5. A causal policy effect is identified rather than a predictive/prescriptive
   certificate.

Those may be good CRPTO v2 directions. They are not safe as current-body claims
without new protocols, new outputs, and new claim-sync guards.

## Code architecture implication

The current codebase is strongest when treated as a frozen research pipeline:
data -> features -> PD -> conformal intervals -> robust portfolio -> exact audit
-> paper outputs. Refactoring within that architecture is useful only when it
improves maintainability without changing the evidence. If Carlos wants a
simpler scientific claim, the clean path is not a broad refactor of old scripts;
it is a new tagged run with a smaller declared protocol and a side-by-side
comparison against the current selected policy.
