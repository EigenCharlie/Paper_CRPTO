# IJDS Claim Audit Matrix

This matrix is the editorial guardrail for the active calibration-selected
midpoint policy. Numeric authority is
`ijds_policy_governance.json` plus A35--A40.

| Claim | Evidence | Main reviewer risk | Defensible wording |
|---|---|---|---|
| The 90% conformal recipe is replayed exactly. | A35; stored endpoint replay max error `6.67e-16`. | "Exact" is mistaken for universal conditional validity. | Exact refers to numerical reconstruction of the frozen finite-sample recipe. Coverage remains marginal/Mondrian under its assumptions. |
| The 99% setting is not decision-useful here. | A35: width `0.988215`; `93.5424%` of upper endpoints equal one. | Reviewer thinks 90% was chosen only to improve economics. | The 90% level is the frozen recipe's reference level and preserves materially more ranking resolution; alpha sensitivity is fully reported. |
| The final policy is simple. | `q=(p+u)/2`, `tau=0.17`; one linear policy family. | Complexity or hidden nonlinear logic. | Point PD prices expected loss; the midpoint is used only in the risk constraint. |
| Final ranking does not use OOT outcomes or statistical assumptions. | A36; outcomes stored separately from a 12-column frame, nine candidates, five eligible, zero outcome/Markov fields. | Historical OOT inspection makes "untouched holdout" false. | Call it a retrospective lockbox replay with an outcome-free final ranking code path, not preregistration or a pristine prospective trial. |
| The selector has a declared stable rule. | A36: full budget, effective-PD feasibility, deterministic `B_u<=0.28`, then maximum expected objective; winner stable on `[0.259036,0.290491)`. | The endpoint cap appears chosen to force the midpoint. | Report the complete 3x3 grid, cap-change boundaries, and the independent December replay. |
| Selector stability is not selected-set validity. | December reselects `linear-005` before outcomes are opened; default `0.145650`, miscoverage `0.124925`. | The 90% conformal label is read as 90% funded-set coverage. | Lead with the observed miss: stable outcome-free selection does not transfer marginal conformal validity to optimizer-selected weights. |
| The selected funded set has an exact accounting audit. | Full OOT: return `$179,327.59`, default `0.039375`, miscoverage `0.036875`, endpoint `0.258051`, `B_u+V=0.294926`. | Accounting is confused with a coverage theorem. | The identity is deterministic after outcomes; it is not nominal selected-set coverage. |
| The Markov statement is secondary and conditional. | Threshold `0.574279`; tail-probability bound `0.316228` under weighted validity. | Bound is too loose or presented as a hard risk cap. | Use it as sensitivity only. Operational controls are `tau`, midpoint exposure, and observed funded-set metrics. |
| A40 is a matched point-PD comparison. | Same candidates, budget, concentration, LGD, solver, and `tau=0.17`. | Comparator changes multiple semantics or sees labels. | Only the risk score changes; neither optimization reads OOT outcomes. |
| Robustness has a measured price. | A40: `8.678%` realized-return cost and `7.9025` percentage-point default reduction. | Default and miscoverage reductions are conflated. | Report default reduction (`7.9025` pp) separately from miscoverage reduction (`0.5025` pp). |
| The midpoint is not the safest CRPTO policy. | A40: 75% blend return `$172,939.50`, default `0.035875`, threshold `0.516624`. | Selected point is sold as dominant. | It is the highest calibration expected-objective candidate under the declared screen. |
| Performance is temporally heterogeneous. | A37: CRPTO wins strongly in 2018H2; point PD dominates 2019H2 and 2020+. | Full-panel result is overgeneralized. | State the reversals in body and abstract; no universal dominance claim. |
| Funded-set composition is correctly labeled. | A38 uses letter grade recovered from `sub_grade` and stores conformal group separately. | Score-quantile groups are mistaken for loan grades. | Call A38 a business composition audit, not fairness certification. |
| Bootstrap uncertainty is bounded. | A39 primary month-cluster return interval `$163,421.14`--`$193,551.65`; funded-loan sensitivity `$162,706.17`--`$193,924.74`. | Interval is read as full model/selection uncertainty. | Both are fixed-allocation diagnostics; model, conformal recipe, selector, and optimizer remain fixed. |
| Earlier methods do not multiply the contribution. | Supplement A1--A34. | Paper reads as several papers or an uncontrolled tournament. | OCE/CVaR, SPO+, online-style checks, and external replications are diagnostics or context, not active selectors. |
| Reproducibility is substantive evidence quality. | Run tags, configs, A35--A40 builder, claim-sync tests, manifest validation. | Tooling is presented as the only novelty. | Lead with decision method and empirical implication; reproducibility makes them auditable. |

## Do Not Claim

- pristine prospective or preregistered OOT evaluation;
- nominal conformal validity for optimizer-selected funded weights;
- universal dominance over point PD or decision-focused learning;
- causal return or default effects;
- legal fair-lending certification;
- live post-2020 Lending Club performance;
- that external Prosper/Freddie diagnostics replicate the final midpoint
  selector exactly.

## Required Headline Numbers

- selected return: `$179,327.59`;
- selected default / miscoverage: `0.039375 / 0.036875`;
- `Gamma_CP / Gamma_residual`: `0.176102 / 0.088051`;
- endpoint / observed accounting / conditional threshold:
  `0.258051 / 0.294926 / 0.574279`;
- point-PD return: `$196,369.14`;
- return cost / default reduction: `8.678% / 7.9025` pp;
- selector: `5/9` eligible, selected `tau=0.17`, `gamma=0.50`.
- deterministic selector cap / stability interval: `0.28 / [0.259036, 0.290491)`;
- December audit default / miscoverage: `0.145650 / 0.124925`;
- primary month-cluster return interval: `$163,421.14`--`$193,551.65`.
