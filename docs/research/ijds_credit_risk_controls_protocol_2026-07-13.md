# IJDS Credit-Risk Learner Controls - Locked V1 Protocol

## Purpose

This retrospective, previously inspected-archive audit asks whether the active
V4 candidate-coverage result depends on one learner, on unconstrained boosting,
or on LendingClub's own pricing and grade signals. It is a robustness control,
not a learner competition and not a new portfolio search.

## Closed Model Family

Five learners are co-primary and all results must be reported:

1. the active CatBoost plus independent 2011 Platt calibration;
2. the active numeric-logistic coverage control plus its own Platt map;
3. CatBoost with the same feature contract and domain-safe monotonic
   constraints, plus its own Platt map;
4. an OptBinning WOE/IV scorecard using borrower, contract, platform grade, and
   pricing signals, followed by regularized logistic regression and Platt;
5. the same scorecard protocol without grade, subgrade, interest, installment,
   or their derived platform-price signals.

The existing active scores are refit and must reproduce the hashed V4 score
artifact to `1e-12`; the referenced values are then used. Every model uses the
same status-independent 36-month universe, temporal train tail, 2011
probability-calibration block, eight six-month residual windows, taxonomies
`1/2/5/10`, and 2016--2017 evaluation menus.

## Data Contract

- The full raw file is scanned; no row sample is permitted.
- Model fitting uses every label-available row in its declared temporal role.
- The 60-month population is outside the common payoff and maturity horizon.
- The 2014--March 2016 gap is not relabeled from early resolutions; doing so
  would induce duration selection. A survival target would be a different
  estimand and paper scope.
- Late-schema bureau variables absent from 2007--2011 cannot enter these
  controls. Missing-by-era imputation is not treated as temporal validation.

## WOE, IV, Monotonicity, And Stability

OptBinning is fit on the PD-development training block only, with automatic
monotonic binning, two to eight bins, and a five-percent minimum bin share.
All bin tables, IV values, logistic coefficients, missing handling, and
feature-level population-stability indices are persisted. The borrower-only
scorecard estimates dependence on incumbent underwriting signals; it does not
claim those signals are illegitimate.

Monotonic constraints are imposed only where the direction has a defensible
credit-risk interpretation. Ambiguous effects such as loan amount, open-account
count, employment length, and interactions remain unconstrained.

## Stop And Interpretation Rules

- No OOT outcome may select, tune, remove, promote, or weight a learner.
- No scorecard, constraint, feature, bin, taxonomy, residual window, or origin
  is changed after OOT evaluation.
- All eight windows and all five learners are reported, including failures.
- The controls never enter portfolio optimization in this protocol.
- A result may strengthen model-class robustness of the observed coverage
  failure. It cannot establish universal nontransport, causal validity,
  deployment readiness, scorecard superiority, or a better policy.
- Prediction metrics, calibration slopes, PSI, IV, and WOE are diagnostics;
  none is a new IJDS novelty claim by itself.
