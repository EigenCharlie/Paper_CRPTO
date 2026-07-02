# Paper 4 / CRPTO Crosswalk - 2026-07-02

## Decision

Keep CRPTO paper-facing and self-contained. The IJDS paper should not import a
second sequential-decision laboratory narrative. The useful material is already
absorbed as bounded comparators, robustness diagnostics and future-work gates.

## What Enters The IJDS Paper

| source material | IJDS destination | reason |
|---|---|---|
| Regret-auditability / SPO+ comparator | Body discussion and A19 supplement table | Shows the trade-off: SPO+ lowers decision regret, while CRPTO supplies the funded-set certificate. |
| Pool93 finite-grid search | Body and A35 | Central promoted result: return-bound frontier, exact alpha checks and selected body point. |
| Pool93 selected-allocation diagnostics | A36--A39 supplement | Grade composition, tail-risk repricing, cluster-bound sensitivity and fixed-allocation bootstrap. |
| Multi-source / localized / weighted coverage ideas | A23 and limitations | Explains where stronger coverage notions would require a new calibration protocol. |
| Tail-risk/OCE/CVaR diagnostics | A20--A22 and A37 | Useful risk-profile evidence, but not the optimized objective. |

## What Stays Out Of The IJDS Body

| material | status | boundary |
|---|---|---|
| Full PyEPO / DFL suite | thesis or extended evidence | DFL is a regret laboratory, not a conformal funded-set certificate. |
| FICO proxy comparison | reviewer-response or thesis governance | Score-governance diagnostic only; no fair-lending legal claim. |
| IFRS9/SICR proxy | thesis/future work | IFRS9-inspired only; no contractual allowance model. |
| CATE / causal policy value | parked | Observational diagnostics only; no policy-value claim. |
| Online conformal deployment | parked | Retrospective/source diagnostics only; no live deployment claim. |
| Fair-lending certification | out of scope | Requires protected attributes or an approved proxy protocol. |

## Paper-Facing Stop Rule

The current paper should stop at A35--A39 unless a new result changes one of
these claims:

1. the pool93 body/default return-bound frontier;
2. the exact funded-set certificate;
3. the selected-allocation tail, concentration or bootstrap profile;
4. the A19 regret-auditability contrast; or
5. a reviewer-requested limitation or reproducibility disclosure.

Everything else is useful research context, but not a reason to reopen the
champion or expand the IJDS body.

## Current Read

The strongest IJDS claim is not "best classifier" or "best regret learner." It
is a governed predict-then-optimize certificate: a calibrated PD model feeds
conformal uncertainty, a finite policy surface is searched exactly, and the
selected funded set is audited through a distribution-free Markov cap under the
stated weighted-validity assumption. Pool93 A35--A39 are the evidence package
for that claim.
