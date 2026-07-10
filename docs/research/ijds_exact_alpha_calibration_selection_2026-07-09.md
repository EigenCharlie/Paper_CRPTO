# IJDS Exact-Alpha and Calibration-Selection Closeout

Date: 2026-07-09

## Why the active claim changed

The previous paper-facing alpha sweep did not recompute conformal quantiles at
each alpha. It scaled stored 90% row radii using average-width ratios from a
different conformal family. The resulting alpha-0.01 endpoints were useful as
an exploratory approximation, but they did not support the manuscript's
"exact alpha" language. The former `8/8`, `0.345084` threshold, and 50,010-grid
selection claims were therefore retired rather than cosmetically relabeled.

## Exact replay

`src/models/conformal_alpha_grid.py` reconstructs the frozen score-decile
Mondrian recipe from its result payload and recomputes quantiles for each alpha.
At the reference 90% level, replay matches the stored point, low, and high
vectors to at most `6.67e-16`. The exact alpha sweep also exposes why
`alpha = 0.01` is not decision-useful here: average interval width is `0.9882`
and `93.54%` of upper endpoints equal one.

## Final policy protocol

The final run is
`champion-reopen-2026-06-19__pool93__ijds-calibration-selected-simple90-v6`.
It uses the exactly replayed 90% interval recipe and a nine-policy round-number
grid:

- `tau in {0.15, 0.17, 0.19}`;
- `gamma in {0.25, 0.50, 0.75}`;
- linear `q = p + gamma(u-p)` only;
- no cap, tail rule, or uncertainty-aversion penalty;
- point-PD expected net return in the objective;
- conformal `q` only in the portfolio-risk constraint.

The policy-ranking code reads no default, realized-return, or miscoverage
columns. It requires at least 99.9% budget use, feasibility of the effective-PD
cap, and `B_u + sqrt(0.10) <= 0.60` on the calibration holdout. Five candidates
are eligible. Maximizing expected point-PD objective selects
`tau = 0.17, gamma = 0.50`, the interpretable midpoint
`q = (p+u)/2`.

## What was learned from the challengers

- The exploratory 25-policy selector chose `gamma = 0.35` and earned
  `$181,758.69` OOT, but its threshold was `0.646094` and its policy grid and
  cap were harder to defend.
- The final 50/50 policy earns `$179,327.59`, only `$2,431.11` less, while
  lowering weighted default from `0.04855` to `0.039375` and the threshold from
  `0.646094` to `0.574279`.
- A 75% blend is safer (`0.035875` default; `0.516624` threshold) but earns
  `$6,388.08` less than the selected midpoint.
- The matched point-PD policy earns more on the full OOT panel, but its default
  rate and endpoint audit are substantially worse. It also beats CRPTO in some
  temporal slices, so no universal dominance claim is supportable.

## Interpretation

The scientific upgrade is not a larger search. It is a smaller and auditable
decision rule, an exact conformal replay at the level actually used, separation
of point-PD economics from conformal feasibility, and a policy selector whose
inputs can be inspected for outcome leakage. This is the active IJDS narrative.

The historical OOT panel was inspected during earlier project development.
Accordingly, v6 is described as a retrospective lockbox replay with an
OOT-outcome-column-free final selector conditional on the frozen conformal
recipe, not as a pristine prospective holdout or
preregistered trial.
