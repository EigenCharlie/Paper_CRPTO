# IJDS decision-method applicability audit

## Status

This memo is a pre-run methodological contract. It was written before any
normalized-frontier or objective-matched challenger was evaluated against
realized outcomes. It does not change the active claim registry, select a new
policy, or authorize a submission freeze.

The central question is not whether a neighboring method can be implemented.
It is whether its guarantee is stated for the same statistical unit as the
CRPTO decision.

## CRPTO's statistical and decision units

For month $t$, the context is the complete candidate menu $X_t$, the uncertain
outcome is the vector $Y_t$ of loan outcomes, and the action is the coupled
allocation vector $a_t$. Budget and purpose constraints make one loan's
allocation depend on the other loans in the same menu. The primary archive has
376,890 candidate loans but only 15 OOT monthly decisions; the common
policy-development period has 11 monthly menus.

Candidate-level exchangeability, if it held, would therefore not by itself
give exchangeability of monthly menu--outcome pairs. Treating 376,890 loans as
376,890 independent portfolio decisions would use the wrong unit and ignore
the optimization coupling. The observed 2012--2016 transport failure also
rules out silently importing an i.i.d. guarantee.

## Applicability matrix

| Method | Object and guarantee | Required calibration unit | Fit to the present archive | What CRPTO may borrow | What CRPTO must not claim |
|---|---|---|---|---|---|
| Split/Mondrian conformal prediction | Marginal label coverage under exchangeability; groupwise marginal coverage when the grouping rule is fixed | Loan-level labeled pairs from the deployment law | **Diagnostic only.** The candidate coverage guarantee does not transport in either learner, and it is not funded-set validity | Exact ranks, fixed taxonomies, explicit coverage audit | Latent-PD intervals, selected-set coverage, or portfolio reliability |
| Hegazy et al., valid selection | Coverage-adjusted selection among individually valid conformal sets through stability/randomization; online variants target long-run coverage | Exchangeable prediction instances in batch mode, or a declared online sequence | **Not a repair for V4.** V4 reports all windows and policies rather than selecting one. It would become relevant only if a window, learner, or set were selected | The principle that validity is not closed under data-dependent selection | That co-primary reporting is a selected-set procedure, or that stable loan-level selection certifies a monthly allocation |
| Bao et al., CROMS | Selects a conformal model to reduce decision risk; F-CROMS gives finite-sample $1-\alpha$ coverage and J-CROMS $1-2\alpha$ under i.i.d./exchangeability | Labeled context--outcome instances on which the robust decision is evaluated | **No current guarantee.** Temporal transport fails, and the relevant portfolio context has only 11 development menus. V4 intentionally has no model selector | Decision risk is the correct criterion when a selector is introduced; full-conformal handling of selection is preferable to naive reuse | A CROMS guarantee from choosing among the eight already inspected residual windows |
| Kiyani et al., RAC | Joint prediction-set and max--min action design for a high-probability utility certificate; finite-sample distribution-free construction under the paper's sampling setup | Independent draws of the complete context, outcome, action, and utility problem | **Conceptually close but not plug-and-play.** A CRPTO context is a high-dimensional monthly menu, not a loan; the archive is too short at that level | Prediction sets should be judged by the downstream utility quantile, and heuristic residual sets need not be decision-optimal | That the clipped loan-wise interval is an optimal risk-averse interface or yields a VaR certificate |
| Hu et al., conformal robustness control | Optimizes a set/risk certificate under an explicit robustness constraint; finite-sample robustness relies on i.i.d./exchangeable data | Complete context--outcome decision instances | **Infeasible as a valid present repair.** Eleven development menus cannot support the proposed high-capacity family, and 2012--2016 exchangeability is contradicted by the audit | Coverage is sufficient but not necessary for downstream robustness | A robustness certificate obtained by recalibrating 376,890 coupled loan rows as if they were decisions |
| Stratigakos et al., decision-calibrated sets | Calibrates set size against expected downstream constraint violations using conformal risk control | Exchangeable operational instances; the application treats high-frequency forecast errors as approximately exchangeable | **Motivating comparator, not a transferable theorem.** CRPTO has few monthly contexts and no defensible approximate-exchangeability claim | Report decision loss separately from predictive coverage; define the operational violation before calibration | That loan-level coverage controls monthly default, budget, or portfolio payoff violations |
| Zhou--Zhu, inverse CRC/CREME | Finite-sample upper bounds on miscoverage and bounded regret over a robustness family; split recalibration protects post-hoc frontier selection | Exchangeable context--outcome pairs with a bounded decision-regret loss | **Closest diagnostic ideal, presently uncertifiable.** CRPTO can enumerate a frontier, but 11 development menus and temporal shift do not support its certificate | A robustness parameter should be evaluated as a Pareto frontier, not at one conventional level | Calling CRPTO's sharp unresolved-outcome envelope a conformal risk or regret confidence bound |
| Zhou--Orfanoudaki--Zhu, CREDO | Lower-bounds the probability that a prescribed action remains near-optimal using inverse feasible regions and generative conformal balls | Samples of the complete uncertain scenario for the same optimization problem | **Potential future methodology, not a small extension.** Each scenario would be a full monthly outcome vector and would require a defensible generative law | The audit-versus-prescription distinction and inverse-feasible-region viewpoint | Decision-optimality probability from fifteen realized monthly vectors |
| Yeh et al., end-to-end conformal optimization | Learns task-aware convex uncertainty sets and applies split conformal calibration; the paper explicitly observes loss of coverage under temporal shift | Exchangeable multivariate context--outcome pairs after model training | **Different paper-scale method.** It would replace the frozen modular credit stack and still would not fix temporal exchangeability | Use its temporal-shift failure as direct evidence that end-to-end expressiveness does not rescue an invalid calibration law | That a PICNN challenger is a sensitivity analysis of the existing CRPTO estimand |
| Sun et al., predict-then-calibrate | Calibrates uncertainty in contextual linear optimization and evaluates risk-sensitive objectives | Validation instances from the target contextual decision law | **Useful architecture precedent, insufficient repair.** Prediction and calibration should remain separate, but the target-law sample is still missing | Modular information boundaries and explicit objective-vector uncertainty | That an old residual pool calibrates 2016 monthly decisions merely because the optimizer is unchanged |
| Non-exchangeable/online conformal risk control | Weighted, discrepancy-aware, block, or online guarantees under method-specific assumptions | A sequential stream or known/estimable shift relationship at the decision unit | **Research lead, not yet identified.** Two feasible rolling origins do not estimate a monthly shift law or provide a long online sequence | State precisely which discrepancy or online loss is controlled | Using the phrase "non-exchangeable conformal" without its weights, dependence conditions, or long-run target |

## Consequence for the next challenger

No neighboring method can be added honestly as a positive certificate with the
current archive. The scientifically valid next step is therefore a better
**identification design**, not a relabeled robustness guarantee.

Two outcome-free comparator coordinates are admissible for study:

1. **Normalized score relaxation.** For score $s$, let $m_s$ be the minimum
   attainable funded score and let $o_s$ be the funded score of the
   unconstrained plug-in-objective solution. Define
   $c_s(\lambda)=m_s+\lambda(o_s-m_s)$ for $\lambda\in[0,1]$. This coordinate is
   invariant to a positive affine transformation of $s$ and compares the same
   relative location between the minimum-score and objective-optimal
   portfolios. It does not equalize economic opportunity cost.
2. **Objective-matched efficient frontier.** For a common target $z$, minimize
   each score $s^Ta/B$ subject to the same base constraints and
   $v^Ta\ge z$. Point and guardrail portfolios then face the same model-implied
   plug-in objective floor. This isolates allocation composition at a common
   opportunity cost and is also invariant to positive affine score changes. It
   does not make the point score or guardrail score a true risk measure.

The objective-matched frontier is the stronger primary comparator contract. A
small normalized-score grid is useful as an interpretability cross-check. Both
must be frozen without outcomes, must include
$\gamma\in\{0,.25,.50,.75,1\}$, and must report the complete declared grid.

## Promotion and stop rules

1. Keep V4 active until a tagged challenger has a byte-stable outcome-free
   freeze, a separately verified outcome join, and reconciled evidence.
2. Do not select a learner, residual window, gamma, frontier coordinate, or
   objective target from realized payoff, default, or miscoverage.
3. A positive empirical direction may be described only if its sharp
   common-outcome bound has one sign over every predeclared window and the
   complete common frontier support. Otherwise the result is comparator
   dependence.
4. Neither design can restore a conformal guarantee after the observed
   temporal failure. At most it can improve identification of the optimization
   handoff.
5. Stop rather than relax the protocol if the common objective support is
   empty, an endpoint is infeasible, source hashes differ, outcomes enter the
   freeze, or solver ties change exposures materially.
6. A failed challenger remains evidence: it can strengthen the conclusion that
   an apparently favorable portfolio direction was a comparator-coordinate
   artifact.

## Editorial implication

The strongest defensible IJDS paper remains one integrated ML--conformal--OR
paper. Its contribution is not that those ingredients have never been joined.
It is an information-safe method for auditing whether a transported conformal
object, a risk-score transformation, and a comparator contract identify the
claimed decision effect. A valid future positive repair may be added only if it
operates on monthly menu--outcome instances or states a different estimand
without ambiguity.
