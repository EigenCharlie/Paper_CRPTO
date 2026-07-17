# IJDS Fitting-Label Completion Sensitivity Protocol V2 - 2026-07-16

## Numerical Recovery

The tagged V1 protocol stopped before writing scientific artifacts because an
`observed_only` refit under the current lock differed from the historical
outcome-free score by `7.389153786618863e-6`, above its unrealistic `1e-12`
score tolerance. V2 changes no scenario, sample, endpoint, model, or estimand.
Before evaluation it fixes a conservative `1e-4` score/recipe tolerance and,
independently, requires the observed-only coverage cells to reconcile with the
active artifact within `1e-5` and their geometry within `2e-5`. V1 is a stopped
numerical protocol, not evidence.

## Question

Does the active CatBoost/Platt coverage conclusion survive declared joint
completions of labels that have a terminal archive outcome but were unavailable
under the September 30, 2020 information contract when their fitting block was
constructed?

## Locked Design

- Retain the active status-independent 640,543-row universe, features, temporal
  roles, CatBoost hyperparameters, Platt block, five-group taxonomy, eight
  residual windows, endpoint contract, and primary OOT census.
- Refit the primary CatBoost model, Platt map, taxonomy, and eight canonical
  residual recipes under exactly four complete scenarios:
  `observed_only`, `all_unavailable_nondefault`,
  `all_unavailable_default`, and `hindsight_terminal`.
- Change only the 41 PD-development, 24 probability-calibration, and 150
  conformal-fit labels unavailable at the information cutoff. Never change an
  evaluation row or use an OOT outcome to choose a scenario.
- Freeze scores, recipes, fit audits, and scenario counts before the primary
  OOT endpoint join. Evaluate every scenario over every window, overall and in
  the declared phase stratum 2.
- Require the `observed_only` score and recipe replay to match the active
  outcome-free freeze within the V2 numerical recovery tolerances. After the
  endpoint join, separately reconcile all 16 overall/phase coverage cells with
  the active artifact before interpreting any completion scenario.

## Estimands

For each scenario and residual window, report the sharp all-candidate primary
OOT coverage interval under the active six-month endpoint-availability rule,
plus phase-stratum geometry. The primary diagnostic is whether every overall
coverage upper bound remains below 0.90.

## Interpretation Boundary

CatBoost, Platt scaling, taxonomy construction, and conformal fitting are
nonlinear in the labels. The four scenarios are declared joint stress corners;
they are not sharp extrema over all `2^215` assignments. No result can select a
completion, model, window, encoding, or policy. `hindsight_terminal` is a
diagnostic and is not an information-feasible deployment rule.

## Stop Rules

- Stop on parent-artifact, ID-census, tag, commit, lock, or baseline-replay
  mismatch.
- Stop if any fitting scenario changes a non-fitting row.
- Stop if any scenario/window/stratum cell is absent or nonfinite.
- Report all four scenarios regardless of direction.
- Do not execute or overwrite any protected historical stage or artifact.
