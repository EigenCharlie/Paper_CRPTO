# IJDS Credit-Risk Controls V2 Evaluation Protocol - 2026-07-13

## Frozen Source

V2 imports the V1b outcome-free score and residual-recipe freeze by run tag,
protocol tag, protocol commit, artifact descriptors, and freeze SHA-256. V2 may
not refit a learner, alter a bin, change a constraint, or regenerate a score.

## One Evaluation

After verification, V2 joins the September 2020 archive endpoint once and
reports every learner, residual window, taxonomy in `1/2/5/10`, temporal role,
and stratum. The canonical paper-facing robustness diagnostic is all-candidate
coverage for five groups over all eight windows; other taxonomies and strata
remain closed diagnostics.

For each learner and temporal role, V2 reports candidate, resolved, and
unresolved rows; ROC AUC, Gini, KS, average precision, Brier score, log loss,
ten-bin ECE, calibration-in-the-large, calibration intercept, and calibration
slope. These metrics describe model transport and do not select a learner.

## Interpretation

- All five learners and all eight residual windows are reported.
- No learner ranking, winner, ensemble, retuning, or feature removal is
  authorized from V2 outcomes.
- Platform-versus-borrower and monotonic-versus-active differences are
  dependence diagnostics, not superiority tests.
- The controls remain outside portfolio optimization.
- Robustness across these five specifications can strengthen the archive-
  specific model-class boundary of the coverage result. It cannot prove
  universal nontransport, deployment validity, or scorecard superiority.
