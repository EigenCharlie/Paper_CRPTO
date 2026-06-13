# CRPTO Bound-Improvement Intake - 2026-05-21

> Ported from the CRPTO research archive
> (`paper1_bound_improvement_intake_2026-05-21`). **Documentation only.** Records
> the PD/conformal challenger package from the external regret-auditability
> sandbox and the gates a bound-improvement lane must pass. The frozen champion is
> not replaced; the regret-auditability lane was closed with append/park.

External artifact root: an external experiments volume outside this repository.

## Decision

This intake does not replace the frozen champion. It records a credible
PD/conformal challenger package and defines the gated runs for the
bound-improvement lane.

## PD signal

Main challenger `full_challenger_woe__bureau_behavior_15`: AUC `0.720679`, Brier
`0.153161`, ECE `0.007689`. Delta AUC vs incumbent replay `+0.008001`.

## Conformal signal

The sandbox-selected conformal configuration is usable, but not final: grade E
fails the strict 90% group gate and E/G are weak at 95%. The next action is a
focused conformal follow-up before any full cuOpt portfolio promotion.

## Portfolio quick signal

The quick CPU run produced an alpha01 pass candidate (return `75602.19`,
`V=0.098750`, `Gamma_CP=0.206650`, zero violation) using only 25k candidates — a
quick signal, not comparable to the 276k champion.

## Compatibility smoke

A HiGHS smoke run confirmed local compatibility with the external intervals and
produced an alpha01 pass candidate (mode `blended_uncertainty`, risk `0.175`,
gamma `0.425`, return `59767.36`, `V=0.092925`, `Gamma_CP=0.216429`, zero
violation). Compatibility smoke, not a replacement for the full cuOpt search.

## Gates

- Do not compare the quick 25k return directly with the frozen 276k champion.
- Run final portfolio only after focused conformal follow-up.
- Use cuOpt/proxy-first broad search plus exact rerank; CPU exact-all is out of
  scope.
- Promote only if the challenger improves a declared metric without breaking
  coverage, min-group coverage, exact alpha01 pass, zero violation, and
  source/temporal caveats.

## Bound fronts (agenda)

- `nested_prospective_confirmation`: run only after PD/conformal/portfolio
  selection is frozen. Gate: strict temporal or prospectively sealed split keeps
  alpha01 pass with zero violation.
- `direct_crc_ltt_decision_loss`: calibrate monotone loss
  `L=max(0, sum w_i Y_i - tau)` or `V` directly. Gate: decision-loss gate passes
  without weakening return or coverage.
- `dependency_aware_concentration`: cluster by `issue_month`, `grade`,
  source/state and compare cluster-robust tail bounds. Gate: cluster-aware bound
  is less vacuous than Markov and more credible than iid.
- `mondrian_funded_set_refinement`: compute `sum_g W_g alpha_g` for selected and
  challenger policies. Gate: weighted group bound improves over nominal alpha
  without hidden subgroup failure.
- `decision_aware_conformal_selector`: select by coverage, width, robust_return,
  `V`, `gamma_cp`, violation and group gates. Gate: selector changes or confirms
  the conformal choice under decision metrics.
- `less_conservative_uncertainty_sets`: compare grade x scoreband or
  polyhedral/contextual conformal candidates. Gate: `Gamma_CP` falls while
  coverage and min-group gates hold.
- `online_shift_aware_bound`: temporal replay or online/weighted conformal only
  as a declared retrospective gate. Gate: coverage and `V` stable under sealed
  temporal slices.
- `richer_financial_target`: prototype `LGD*default` or ECL proxy loss if data
  quality is sufficient. Gate: financial target improves interpretability without
  adding unsupported IFRS9 claims.
