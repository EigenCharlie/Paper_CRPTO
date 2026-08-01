# IJDS decision-loss-aligned conformal design (2026-07-30)

## Status, scope, and authority

This document is a **prospective design note only**. It is not an executable
protocol, not an active evidence source, and not authority for a manuscript
claim. It authorizes no run, no inspection of new outcomes, and no promotion of
the currently inspected IJDS archive.

The purpose of the design is to state what would be required to align a future
conformal guarantee with a portfolio-level decision loss. It does not establish
selected-loan coverage, funded-set FCR control, temporal transport, or policy
utility for the current manuscript.

In particular:

- the historical 11 development and 15 target issue months have already been
  inspected and cannot be relabeled as fresh risk-calibration or evaluation
  contexts;
- the current archive does not provide the complete, untouched endpoint panel
  required below;
- no current figure, table, diagnostic, policy comparison, or realized outcome
  may be used to choose a favorable catalog entry and then support a
  confirmatory claim;
- no current paper, claim-ledger, or active-evidence entry is changed by this
  note; and
- implementation would require a new dated protocol, configuration, immutable
  run tag, output namespace, and independent audit, all frozen before the
  relevant new outcomes are accessed.

The temporal assumptions and chronology fields in
[`ijds_temporal_transport_dependence_contract_2026-07-30.md`](ijds_temporal_transport_dependence_contract_2026-07-30.md)
are part of this design. The selected-exposure route in
[`ijds_selected_exposure_validity_design_2026-07-30.md`](ijds_selected_exposure_validity_design_2026-07-30.md)
is a distinct estimand and must not be conflated with the monthly loss proposed
here.

## Scientific question

The prospective question is:

> Can a policy, chosen from a finite catalog frozen before risk-calibration
> outcomes are opened, control the expected fixed-capital share assigned to
> loans whose realized binary labels fall outside their prediction sets in a
> new issue month?

This is a portfolio-level risk question. It is not the conditional coverage of
a focal selected loan, and it is not the false coverage rate among funded
loans. Those selected-unit questions require the separate JOMI-based route.

## Predeclared phased program

The phases below address different estimands. Passing a later phase does not
retroactively validate an earlier one, and failure in one phase cannot be
hidden by success in another.

| Phase | Primary object | Intended guarantee | Load-bearing conditions | Status |
|---|---|---|---|---|
| S1 | Equal-notional, fixed-\(K\) funded set | JOMI focal selection-conditional coverage and the corresponding FCR implication | Same-population exchangeability, deterministic permutation-equivariant selection, exact taxonomy, exactly \(K\) equal allocations | Prospective; specified separately |
| S2 | Concentration-bounded funded set | Dollar-weighted FCP bounded through JOMI at level \(\alpha/\kappa\) and a deterministic count-to-dollar inequality | All S1 conditions plus a predeclared hard bound \(a_i/A\leq\kappa/K\) and proof audit | Prospective; specified separately |
| D | Complete issue-month context | Expected bounded monthly decision loss under CRC, or simultaneous certification of a finite policy catalog under LTT | Untouched complete contexts, frozen catalog, temporal theorem contract, and route-specific assumptions | Prospective; this document |

The intended order is S1, then S2, then D. S1 is the cleanest
selection-conditional target because equal notional makes count FCP and dollar
FCP coincide. S2 adds only the predeclared concentration inequality; it must
not be described as direct exposure-weighted conformal validity. Phase D
changes the unit and estimand to a whole month and is useful only if the
scientific target is aggregate portfolio risk.

No nested-lot or arbitrary exposure-weighted extension may enter this program
without a separate theorem and proof audit. No empirical regularity observed
in the current archive can substitute for that theorem.

## Frozen monthly decision object

### Context as the theorem unit

Let \(Z_t\) denote the complete information for one non-overlapping issue-month
context \(t\). The context contains the entire eligible menu, point-in-time
features, the frozen policy inputs, and—only after maturity—the complete
endpoint vector. Loans within a month may be dependent. The month, not an
individual loan, is the exchangeable or i.i.d. unit required by the
route-specific theorem.

The policy \(\pi\) maps the outcome-free portion of \(Z_t\) to:

- a prediction set \(C_{it}^{\pi}\subseteq\{0,1\}\) for every eligible loan
  \(i\);
- a nonnegative allocation \(a_{it}^{\pi}\);
- an explicit cash remainder; and
- deterministic audit metadata for every solver and tie decision.

The capital denominator \(B>0\) is fixed before the context is observed. The
policy must satisfy

\[
    a_{it}^{\pi}\geq 0,
    \qquad
    \sum_i a_{it}^{\pi}\leq B.
\]

### Primary bounded loss

The sole primary risk loss is

\[
    L_t(\pi)
    =
    \frac{1}{B}
    \sum_i
    a_{it}^{\pi}
    \mathbf{1}
    \left\{
      Y_{it}\notin C_{it}^{\pi}
    \right\},
    \qquad
    0\leq L_t(\pi)\leq 1.
\]

Uninvested cash remains in the denominator. Consequently, this is a
**fixed-capital decision-miscoverage loss**, not a funded-loan average. A
policy that invests little can obtain a small loss; capital utilization must
therefore be reported as an informativeness diagnostic, never silently folded
into the primary guarantee.

For a new context drawn under the stated temporal theorem contract, define

\[
    R(\pi)=\mathbb{E}\!\left[L_{\mathrm{new}}(\pi)\right].
\]

One risk target \(\alpha_{\mathrm{risk}}\in(0,1)\) is primary. Under LTT, one
confidence error \(\delta_{\mathrm{cert}}\in(0,1)\) is also primary. Both must
be fixed on the design split. Additional losses, thresholds, or populations
require a predeclared joint-error or multiplicity contract; none may be added
after risk-calibration outcomes are viewed.

The primary loss is deliberately simple. Recovery severity, payoff, return,
capital utilization, singleton rate, set size, and concentration may be
reported only as separately named utility or informativeness quantities unless
a new protocol supplies their own valid risk guarantees.

## Finite policy catalog

Before risk-calibration outcomes are accessible, freeze a finite catalog

\[
    \Pi=\{\pi_1,\ldots,\pi_J\}.
\]

Every entry must be an end-to-end policy, not merely a score threshold. Its
manifest must identify:

1. the fitted learner and immutable model artifact;
2. the point-in-time feature contract and missing-value behavior;
3. the calibration-score definition and binary-set construction;
4. every threshold or tuning coordinate;
5. the economic objective and all optimization coefficients;
6. the complete constraint system, budget, purpose caps, exposure caps, and
   cash treatment;
7. granularity, rounding, and residual-capital rules;
8. solver name and version, tolerances, seeds, warm-start policy, and status
   handling;
9. a deterministic total tie order independent of row order and protected
   identifiers;
10. behavior for infeasibility, timeout, numerical ambiguity, missing input,
    and empty menus; and
11. a safe abstention or fallback entry.

All learner fitting, catalog construction, policy tuning, utility tradeoffs,
and compute-driven catalog reduction occur on train and design data only.
After the risk-calibration role begins, catalog entries cannot be added,
removed, renamed, reparameterized, or rerun with altered solver semantics.

A full binary prediction set or cash-only policy can make miscoverage
trivially zero. Such a fallback is useful for safety but scientifically
uninformative. The design must therefore predeclare minimum utility and
informativeness conditions. Certification of only a trivial fallback is
reported as abstention for the useful-policy question, not as substantive
success.

## Four-way data separation

The future archive must be partitioned by immutable context identifiers and
calendar boundaries into four non-overlapping roles.

### 1. Train

The train role is used to fit learners, feature transformations, score
functions, and any model-based policy inputs. Every training label must be
fully mature under the fixed endpoint definition, and every feature must be
available at the simulated decision timestamp.

### 2. Design

The design role is used to choose:

- the finite catalog and any ordered CRC family;
- \(\alpha_{\mathrm{risk}}\) and, for LTT,
  \(\delta_{\mathrm{cert}}\);
- the temporal sampling unit and population;
- the CRC or LTT route;
- the p-value engine and multiplicity procedure for LTT;
- the deployment selector among certified policies;
- utility and informativeness guardrails;
- sample-size, power, and computational budgets; and
- all synthetic and negative-control tests.

Design labels may be used for design choices, but a context used here is then
forever ineligible for risk calibration or evaluation.

### 3. Risk calibration

The risk-calibration role consists of untouched, complete issue-month
contexts. It is used only for the predeclared CRC calibration rule or the
predeclared LTT tests. It cannot be used to refit the learner, edit the
catalog, select a loss, revise solver handling, or redesign a figure.

### 4. Evaluation

The evaluation role consists of later, untouched, complete issue-month
contexts. Its outcomes are opened once, only after the catalog and the
risk-calibration output are frozen. Evaluation estimates realized performance
and checks prespecified diagnostics. It cannot select the deployed policy,
repair calibration, choose the most favorable subgroup, or alter the theorem
statement.

The split manifest must prove disjoint context IDs, disjoint loan IDs,
non-overlapping endpoint windows, and absence of duplicated listings or
resubmissions across roles. If a context has unresolved eligible endpoints,
the study waits for completion; it does not drop unresolved loans, impute a
favorable completion, or redefine the eligible population.

## Temporal and endpoint contract

Chronological ordering alone does not imply exchangeability, independence, or
transport. Before outcomes in the risk-calibration role are accessed, the
implementation protocol must specify:

- the exact decision timestamp for every context;
- the feature-availability timestamp for every input;
- the endpoint definition, maturity horizon, and availability timestamp;
- the fixed eligible population and duplicate-resolution rule;
- the context spacing, embargo, and overlap rules;
- the role and calendar assigned to every context;
- the hypothesized joint law linking risk-calibration and future contexts;
- any weighting or blocking map; and
- the exact theorem invoked under that law.

CRC below requires exchangeable random loss functions across contexts. The
baseline LTT route below requires i.i.d. contexts for its chosen valid
p-values. If serial dependence, distribution shift, covariate shift,
policy-induced feedback, or overlapping outcomes make those assumptions
indefensible, execution stops unless a separate, prospectively locked theorem
supplies an explicit discrepancy, decoupling, mixing, or weighted-risk bound.

An embargo can reduce mechanical leakage; it cannot prove temporal
independence. Likewise, a diagnostic from the already inspected archive cannot
be converted post hoc into a transport penalty. If enough complete and
scientifically defensible context units cannot be reserved, no monthly
conformal claim is attempted.

## Route A1: classical conformal risk control for a monotone family

CRC is eligible only for an ordered family
\(\{\pi_{\lambda}:\lambda\in\Lambda\}\) locked on the design role. The finite
grid, order, interpolation convention if any, and safe terminal value
\(\lambda_{\max}\) must all be declared in the catalog.

For every possible context—not merely on average or on the observed design
sample—the complete loss function must satisfy the theorem conditions:

1. \(L_t(\lambda)\in[0,1]\);
2. \(L_t(\lambda)\) is non-increasing in \(\lambda\);
3. \(L_t(\lambda)\) is right-continuous under the stated parameterization; and
4. the safe terminal value satisfies
   \[
     L_t(\lambda_{\max})
     \leq
     \alpha_{\mathrm{risk}}
     -
     \frac{1}{n_{\mathrm{cal}}+1}
   \]
   almost surely.

The last term is the finite-sample correction for a loss bounded above by one.
More generally, the original CRC theorem uses the loss upper bound
\(B_{\mathrm{loss}}\) and requires an attainable loss no greater than
\(\alpha_{\mathrm{risk}}-B_{\mathrm{loss}}/(n_{\mathrm{cal}}+1)\).
Consequently, even a zero-loss terminal policy cannot satisfy this route when
\(\alpha_{\mathrm{risk}}<1/(n_{\mathrm{cal}}+1)\). That failure is a
resolution NO-GO, not permission to omit the correction or increase the target
risk after calibration.

The cleanest admissible construction freezes allocations independently of
\(\lambda\) and lets increasing \(\lambda\) only expand nested prediction sets.
Then every indicator in the weighted sum is pointwise non-increasing, so the
monthly loss is pointwise non-increasing.

If \(\lambda\) changes eligibility, allocations, objective coefficients,
constraints, tie resolution, or the optimizer solution, monotonicity must not
be inferred from wider sets. Reoptimization can move capital toward newly
miscovered loans and make the aggregate loss increase. Empirical monotonicity
on a finite archive is not a universal proof. A reoptimized or otherwise
non-monotone catalog fails this classical scalar route; it must use either the
stability-certified Route A2 or the LTT route fixed below.

Under the exchangeable-loss and regularity conditions of conformal risk
control, the theorem-aligned CRC rule targets

\[
    \mathbb{E}
    \left[
      L_{\mathrm{new}}(\widehat{\lambda})
    \right]
    \leq
    \alpha_{\mathrm{risk}}.
\]

This is an expectation guarantee for a new context. It is not:

- a guarantee that every realized future month has loss at most
  \(\alpha_{\mathrm{risk}}\);
- focal selected-loan coverage;
- selected-set FCR control;
- a guarantee conditional on a particular future menu;
- a utility or return guarantee; or
- a temporal-robustness guarantee outside the declared context law.

The implementation protocol must reproduce the exact CRC selection rule from
the cited theorem and audit its finite-grid convention. No informal
``empirical loss below \(\alpha\)'' rule may be substituted.

## Route A2: stability-certified CRC for a non-monotone algorithm

Non-monotonicity no longer implies that CRC is impossible in principle
[@angelopoulos2026nonmonotonic]. It changes the theorem and adds a stability
burden. Before outcomes, this route must freeze:

1. exchangeable complete context units;
2. a symmetric, permutation-invariant algorithm \(\mathcal A\), including
   deterministic solver and tie-breaking semantics;
3. a full-data reference algorithm \(\mathcal A^*\);
4. the loss and multidimensional parameter space;
5. a valid upper bound \(\beta\) on the theorem's leave-one-out stability
   quantity; and
6. a reference-risk certificate no larger than
   \(\alpha_{\mathrm{risk}}-\beta\).

The route stops if exchangeability or symmetry fails, if LP basis changes or
degeneracy make the declared stability bound invalid, if \(\beta\) is vacuous,
if \(\alpha_{\mathrm{risk}}-\beta\) is unattainable, or if the failure
probability of an estimated bound is not propagated. A bootstrap estimate of
\(\beta\) is a diagnostic unless accompanied by a separately proved
finite-sample upper-confidence contract; it cannot be inserted as if exact.
For a generic bounded loss on a discretized grid, the cited extension obtains
an additive stability/discretization remainder rather than the unadjusted
classical target automatically.

This route can be attractive for a stable smooth algorithm. It is not the
default for the present reoptimized LP catalog, whose active-set changes,
degeneracy, and solver tie resolution would themselves require a new stability
audit.

## Route B: learn-then-test for a non-monotone or reoptimized catalog

LTT is the default route when the end-to-end loss is not provably monotone,
including when every catalog entry reoptimizes allocations.

For every risk-calibration context and every frozen policy, compute the
complete matrix

\[
    \mathcal{L}
    =
    \left\{
      L_t(\pi_j):
      t=1,\ldots,n_{\mathrm{cal}},
      \ j=1,\ldots,J
    \right\}.
\]

No missing cell, favorable early stop, or selective policy rerun is allowed.
For each policy, use one prospectively selected, theorem-valid one-sided
p-value for the null that its population risk is not at most
\(\alpha_{\mathrm{risk}}\). The exact p-value formula and all assumptions must
appear in the implementation protocol; a bounded-loss concentration p-value
cannot silently be replaced by a Bernoulli-only formula.

Apply a predeclared family-wise error rate procedure at level
\(\delta_{\mathrm{cert}}\). Bonferroni is the conservative default. A
fixed-sequence, graphical, or other more powerful procedure is permitted only
if its ordering and transition graph were frozen on the design role.

Under the i.i.d.-context and valid-p-value conditions of learn-then-test, the
returned set \(\widehat{\Pi}\) targets the simultaneous statement

\[
    \Pr\!\left\{
      \sup_{\pi\in\widehat{\Pi}} R(\pi)
      \leq
      \alpha_{\mathrm{risk}}
    \right\}
    \geq
    1-\delta_{\mathrm{cert}}.
\]

Because the statement is simultaneous over the returned set, the frozen
deployment rule may select one certified entry. The utility selector itself
must be specified using train/design information; evaluation outcomes cannot
be used to choose the winner. If \(\widehat{\Pi}\) is empty, the result is
abstention. Neither \(\alpha_{\mathrm{risk}}\) nor
\(\delta_{\mathrm{cert}}\) may be relaxed after seeing the result.

LTT permits a finite non-monotone catalog; it does not turn the contexts into
i.i.d. observations, certify untested policies, or guarantee that each
realized month satisfies the loss target.

## Synthetic and adversarial validation

Synthetic validation is required before a fresh risk-calibration outcome is
opened. It validates the implementation, not the temporal assumptions.

### Loss and accounting tests

- Exhaustively enumerate small menus, binary labels, prediction sets,
  allocations, and cash remainders.
- Verify \(0\leq L_t(\pi)\leq1\), the fixed denominator \(B\), exact treatment
  of zero allocations, and conservation of allocated capital plus cash.
- Verify that row permutations, identifier reversals, repeated executions, and
  equivalent solver bases produce identical policy outputs.
- Fail on silent infeasibility, timeout, ambiguous solver status, or
  non-deterministic tie handling.

### CRC tests

- Under fixed allocations and nested sets, verify pointwise monotonicity for
  every enumerated label vector.
- Construct at least one explicit counterexample in which reoptimization
  reallocates capital and \(L_t(\lambda)\) increases despite wider sets.
- Verify the finite-sample-corrected safe terminal policy and right-continuous
  finite-grid convention.
- Compare the implementation against hand-computed CRC examples and the
  theorem's exact calibration rule.

Any monotonicity counterexample for the proposed CRC family is a hard CRC
failure. The family can proceed only through a separately frozen LTT plan.

### LTT tests

- Simulate i.i.d. bounded monthly losses at and beyond the null boundary and
  verify super-uniform p-values.
- Enumerate small catalogs and estimate family-wise error under global and
  partial null configurations.
- Verify that catalog reordering changes no Bonferroni result and changes a
  fixed-sequence result only as prospectively specified.
- Verify that one missing policy-context cell, a failed solve, or a late catalog
  edit invalidates the complete certification run.

### Temporal negative controls

- Include positive controls generated from the exact i.i.d. or exchangeable
  context model used by the theorem.
- Include negative controls with deterministic trend, regime shift, serial
  dependence, overlapping endpoints, duplicated loans, and delayed features.
- Confirm that chronology and embargo checks detect mechanical leakage but do
  not falsely label dependent or shifted data as exchangeable.

All prespecified synthetic scenarios and failures are reported. Selecting only
successful simulations or figures is forbidden.

## Computational plan

No evidence execution is authorized by this note. A future implementation
first performs a design-only benchmark with synthetic data and design-role
contexts.

### Equal-notional JOMI stage

The first selected-exposure stage uses one frozen learner and deterministic
fixed-\(K\), equal-notional selection rule. Its implementation budget is
estimated before any fresh outcomes are accessed. For label-free selection,
reuse only reductions justified by the JOMI taxonomy; do not assume that a
generic \(2nK\) swap computation is necessary or valid. Checkpoints must
preserve every focal-unit/taxonomy result, not only successful cases.

### \(\kappa\)-concentration stage

The second stage adds the hard, predeclared allocation bound and the
deterministic count-to-dollar inequality. Computational optimization is
permitted only after the inequality and all edge cases have passed an
independent proof audit. The value of \(\kappa\) cannot be tuned using target
outcomes.

### Monthly CRC stage

For a fixed-allocation nested-set family:

1. solve the allocation policy once per context;
2. evaluate all predeclared set thresholds vectorially;
3. store the full context-by-threshold loss matrix;
4. apply the exact CRC calibration rule once; and
5. reproduce the chosen threshold from the immutable matrix.

Repeated optimization at every threshold is both computationally costly and a
threat to monotonicity. It is excluded from CRC unless a universal
monotonicity proof is supplied.

### Monthly LTT stage

For \(n_{\mathrm{cal}}\) contexts and \(J\) policies, the calibration workload
is exactly \(n_{\mathrm{cal}}J\) policy-context executions, plus all
prespecified synthetic validation. Evaluation workload and whether all
certified entries or only the frozen deployed entry are evaluated must be
specified before evaluation outcomes are opened.

On the design role, benchmark and freeze:

- \(J\), \(n_{\mathrm{cal}}\), and the number of synthetic scenarios;
- median, 95th-percentile, and maximum solve time;
- peak memory and disk requirements;
- maximum worker count and deterministic scheduling order;
- total allowed solver calls and wall-clock budget;
- checkpoint frequency and atomic output format; and
- behavior after interruption, timeout, or partial output.

If the projected workload is infeasible, reduce the catalog on the design role
and freeze a new manifest before risk-calibration outcomes are touched. Once
calibration starts, compute pressure is not permission to shrink the catalog,
drop slow policies, change tolerances, or retain a partial matrix.

## Hard stop rules

The future study stops without a positive claim if any of the following holds:

1. the context unit, population, \(B\), primary loss,
   \(\alpha_{\mathrm{risk}}\), or—under LTT—
   \(\delta_{\mathrm{cert}}\) was not fixed in advance;
2. a policy, threshold, loss, subgroup, plot, or multiplicity method was chosen
   using current historical outcomes or future evaluation outcomes;
3. train, design, risk-calibration, and evaluation IDs or outcome windows
   overlap;
4. a feature was unavailable at the simulated decision time;
5. any eligible endpoint is unresolved, selectively excluded, or completed
   under an unregistered rule;
6. duplicate or resubmitted loans cross data roles without a predeclared
   population rule;
7. the declared exchangeability/i.i.d. contract is indefensible and no
   prospectively locked replacement theorem applies;
8. the catalog, solver version, tolerance, seed, tie rule, or status handling
   changes after calibration begins;
9. a CRC loss family lacks a universal pointwise monotonicity argument,
   right-continuity convention, or terminal policy meeting the exact
   \(B_{\mathrm{loss}}/(n_{\mathrm{cal}}+1)\) finite-sample correction;
10. an LTT p-value is invalid for bounded non-Bernoulli losses, the
    multiplicity implementation fails, or any policy-context cell is missing;
11. synthetic enumeration, permutation, repeatability, negative-control, or
    accounting tests fail;
12. the run exceeds its compute budget, terminates partially, or requires
    selective restart;
13. no nontrivial policy is certified; or
14. the evaluation result motivates a revised claim or policy without a new
    prospective study.

Switching from CRC to LTT is allowed only before risk-calibration outcomes are
accessed, or under a separate newly frozen protocol. A failed CRC attempt
cannot inspect outcomes and then reuse them for an opportunistic LTT rescue.

The current inspected archive is a hard no-go for this confirmatory design
because it is not a fresh four-way split, has too few defensible context units
for an automatic monthly theorem claim, and does not supply the required
complete endpoint panel.

## Required future artifacts

A valid future run must preserve, at minimum:

- the immutable train/design/risk-calibration/evaluation census;
- the point-in-time chronology and endpoint-completeness audit;
- the finite catalog manifest and hashes of every model and configuration;
- the exact issue-month population and duplicate-resolution ledger;
- the complete context-by-policy or context-by-threshold loss matrix;
- the CRC monotonicity certificate and safe-terminal audit, or the complete LTT
  p-value and multiplicity object;
- solver receipts, status codes, seeds, tolerances, and deterministic tie
  traces;
- the synthetic and adversarial validation report, including failures;
- the compute budget and actual resource receipt;
- the complete, prespecified evaluation table;
- every prespecified figure, including null and unfavorable panels; and
- a machine-readable interpretation object separating theorem guarantee,
  empirical evaluation, utility, and limitations.

Missing artifacts fail closed. Reconstructed summaries, selected screenshots,
or prose assertions cannot replace the immutable loss matrix and audit trail.

## Guarantee and literature map

| Component | Supporting result | What it can support | What it cannot support |
|---|---|---|---|
| Equal-notional fixed-\(K\) selection | JOMI / focal conditional validity (`jin2025focal`) | Focal selection-conditional validity and, under the exact taxonomy and selection conditions, an FCR implication; equal notional equates count and dollar FCP | Arbitrary LP-weighted selected-set coverage or temporal transport |
| \(\kappa\)-bounded allocation | Deterministic inequality plus JOMI at \(\alpha/\kappa\) | A conservative expected dollar-FCP bound if the hard allocation bound and JOMI assumptions both hold | Direct exposure-weighted conformal validity; the inequality still requires proof audit |
| Monotone monthly loss | Conformal risk control (`angelopoulos2024risk`) | Expected bounded loss control for a new exchangeable context under the theorem's monotonicity and regularity conditions | Non-monotone reoptimization, per-month high-probability control, focal coverage, or temporal robustness |
| Stable non-monotone algorithm | Stability-based non-monotone CRC (`angelopoulos2026nonmonotonic`) | Expected risk control under exchangeability, algorithm symmetry, a valid reference-risk margin, and a nonvacuous certified stability penalty | Automatic validity for an unstable reoptimized LP, an unqualified bootstrap stability estimate, per-month high-probability control, or temporal transport |
| Finite reoptimized catalog | Learn then test (`angelopoulos2025ltt`) | With valid p-values and FWER control, simultaneous high-probability certification that all returned policies meet the population-risk target | Independence/exchangeability by assertion, untested policies, per-realization control, or utility |
| Temporal deployment | Prospective temporal contract linked above | A declared unit, chronology, population, and explicit route to a transport theorem | An active guarantee from the current archive |
| Complete endpoints | This design requirement | A loss matrix for the full predeclared eligible population without selective missingness | A theorem for censored or selectively observed endpoints |

CRC and LTT address expected population risk. JOMI addresses
selection-conditional coverage. These guarantees are complementary only when
reported under their own assumptions and estimands; they must never be merged
into a broader claim that none of the individual theorems supplies.

## Figure and reporting discipline

All confirmatory tables and figures must be enumerated before evaluation
outcomes are opened. Every predeclared risk, utility, capital-utilization,
concentration, set-size, and temporal diagnostic is reported on the complete
evaluation family with its denominator and context count.

Exploratory figures from the current inspected archive may motivate a future
design, but they cannot:

- select a catalog entry or threshold;
- become confirmatory evidence;
- justify a temporal assumption;
- determine which evaluation panel is shown; or
- be described as a replication of the future study.

An unexpected evaluation pattern may be reported as exploratory and used to
design a later study. It does not authorize rewriting the frozen claim around
the observed result.

## Promotion boundary

This design becomes executable only after a separate implementation protocol
has:

1. fixed the estimand, catalog, route, calendars, theorem assumptions, compute
   budget, and stop rules;
2. been committed and tagged before any fresh risk-calibration or evaluation
   outcome is accessed;
3. passed synthetic, chronology, endpoint, solver, and independence audits; and
4. received an independent scientific and code review.

Only a complete run that passes every gate may be considered for later
promotion to the active claim registry, claim ledger, evidence manifest, and
paper. Until then, the scientifically correct manuscript statement is that
decision-loss-aligned conformal control remains a prospective design.
