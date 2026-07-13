# IJDS normalized-score and objective-matched frontier protocol

## Status

This protocol is locked before the complete outcome-free V1 run under tag
`protocol/ijds-normalized-objective-frontier-2026-07-12-v1`. It is a
specification-complete retrospective challenger over the already inspected V4
archive. It is not a preregistration, a pristine lockbox, a submission freeze,
or a repair of conformal validity.

V4 remains the active manuscript evidence until a separate V2 evaluator
verifies the V1 freeze by hash, joins outcomes once, and passes the promotion
rules below. The V1 runner cannot accept a status, outcome, default, payment,
realized-payoff, or miscoverage column.

## Why another specification is necessary

The outcome-free support audit established that the inherited fixed-cap family
was not semantically complete:

- `gamma=0` was objective-slack in 624/624 cells;
- omitted `gamma=1` was feasible and decision-active in 624/624 cells; and
- at the same numeric cap, `gamma=1` sacrificed more plug-in objective than
  `gamma=.75` in every cell.

A fixed numeric `tau` therefore compares different locations on different
score scales. The challenger replaces that single ruler with two declared,
non-equivalent coordinates. Neither is called neutral.

## Frozen research object

The parent is the immutable V4-v1 outcome-free freeze at commit `2f8a760`.
Before use, the challenger verifies its freeze descriptor, protocol identity,
all referenced artifact hashes, empty outcome-column list, and source archive
hash. It imports only:

- the status-independent score universe and design roles;
- the CatBoost five-group residual recipes for all eight windows;
- contractual amount, rate, and purpose from an explicit raw-column allowlist;
- the coherent plug-in objective, USD 1 million monthly budget, and 25% purpose
  cap from the parent config.

The complete family is
`gamma={0,.25,.50,.75,1}` with
`q_gamma=p+gamma(U-p)`. The 11 development and 15 primary monthly menus and all
eight windows are retained. No outcome selects a gamma, ruler, coordinate,
month, or window.

## Common base polytope

For month `t`, let `A_t` contain allocations satisfying exact budget, loan
bounds, and the purpose cap. Let `v` be the coherent plug-in payoff rate and
`s` one member of the complete gamma score path. The score-minimum and a common
score-independent plug-in optimum are

\[
m_s=B^{-1}\min_{a\in A_t}s^Ta,
\qquad
z^*=\max_{a\in A_t}v^Ta,
\qquad
o_s=B^{-1}s^Ta^*.
\]

The optimizer `a*` is solved once per menu in stable ID order. For every score,
the minimum and maximum funded score subject to
`v^Ta >= z* - 1e-7 dollars` are also solved. A score range above `1e-8` at the
objective optimum is treated as unresolved objective-tie dependence and stops
the run.

## Ruler 1: objective-matched efficient frontier

This is the primary ruler. Let `z_min,s` be the plug-in objective of a
minimum-score portfolio and define the common lower endpoint

\[
z_L=\max_s z_{min,s}.
\]

For `rho in {.25,.50,.75}`, set

\[
z(rho)=z_L+rho(z^*-z_L)
\]

and solve

\[
\min_{a\in A_t}s^Ta\quad\text{subject to}\quad v^Ta\ge z(rho).
\]

All scores therefore face the same absolute model-implied objective floor on
their common attainable support. This controls plug-in opportunity cost, not
true expected return. It does not make either score a true risk measure.

## Ruler 2: normalized-score relaxation

This is the secondary structural ruler. For
`lambda in {.25,.50,.75}`, define

\[
c_s(lambda)=m_s+lambda(o_s-m_s)
\]

and maximize `v^Ta` over `A_t` subject to
`s^Ta <= B c_s(lambda)`.

If `s_tilde=a s+b` for `a>0`, then
`m_tilde=a m_s+b`, `o_tilde=a o_s+b`, and
`c_tilde=a c_s+b`. The feasible allocation set is therefore unchanged at the
same lambda. This proves positive-affine score invariance and nestedness in
lambda. Equal lambda is not equal true risk, funded default, shadow price,
objective sacrifice, or operational tolerance.

The denominator `o_s-m_s` must exceed `1e-4` in every cell. Every interior cap
must bind within `1e-8`; an endpoint failure is not dropped or repaired.

## Frozen cells and primary contrast

The V1 freeze contains exactly

`8 windows x 26 months x 5 gammas x 3 coordinates x 2 rulers = 6,240`

solve records, plus every positive funded exposure. The primary empirical
contrast, evaluated only in V2, is the full-upper endpoint minus the point-score
endpoint (`gamma=1 - gamma=0`) for each window, ruler, coordinate, and metric.
Interior gammas remain a complete diagnostic path and cannot be selected as a
winner.

The endpoint contrast is a deterministic archive contrast. It is not a causal
effect, population expectation, investor return, or conformal robustness
certificate. Unresolved outcomes must use one common loan-wise assignment over
the funded union to obtain sharp fixed-allocation bounds.

## Numerical falsification

1. All solves use one-thread HiGHS simplex with exact budget.
2. Every primary endpoint allocation is rerun after reversing ID order.
   Exposure distance is `L1/(2B)`. Distance above `1e-10` or objective drift
   above USD `1e-5` stops the run.
3. For primary periods April 2016, November 2016, and June 2017, every endpoint,
   window, ruler, and coordinate is independently resolved with OR-Tools GLOP.
   Objective-rate or funded-score disagreement above `1e-7` stops the run.
4. Synthetic unit tests enumerate a small continuous LP's vertices and compare
   both ruler formulations with the solver output.
5. Budget residual above USD `1e-6`, normalized-cap residual above `1e-8`, or
   absolute objective-floor mismatch above USD `1e-5` stops the run.

The second solver validates the declared finite grid, not every real-valued
frontier point. This challenger therefore makes no new "exact all-cap
frontier" claim.

## Outcome-free stop rules

Stop before any outcome join if:

- a parent hash, source hash, ID alignment, month count, or window count differs;
- any forbidden column reaches the decision frame;
- one of the 6,240 cells is missing or infeasible;
- a normalized score or common objective range is numerically empty;
- the score-independent objective optimum has unresolved score tie range;
- ID reversal or GLOP validation exceeds tolerance; or
- all 360 primary endpoint comparisons for one ruler are allocation-identical
  within `1e-6` of budget.

No threshold or tolerance may be relaxed after seeing the run. A stopped or
degenerate run is reported as evidence rather than silently redesigned.

## V2 evaluation and promotion rules

V2 requires a new protocol commit and tag containing the exact V1 freeze
descriptor. Only then may it join archive outcomes. It must report every
predeclared endpoint contrast for standardized payoff, funded default, and
funded binary miscoverage under sharp common-outcome bounds.

The challenger may strengthen the negative identification audit if rulers or
windows disagree. A positive descriptive direction is eligible for further
rolling-origin evaluation only if its sharp bound has the same nonzero sign in
all eight windows, all three coordinates, and both rulers. That condition still
does not restore conformal validity. Any positive CRPTO claim would additionally
have to survive every feasible rolling origin under a separately locked replay.

No majority vote, selected coordinate, selected gamma, selected window, or
post-outcome comparator narrowing is allowed.

## Pre-tag structural smoke

Before locking the protocol tag, one outcome-free cell was used only to test
formulation and numerical scale: April 2016, W1, all five gammas, with no
status or outcome columns loaded. The attainable score ranges were
`0.078139`, `0.216985`, `0.355830`, `0.494675`, and `0.633521`. At an objective
floor USD `1e-6` below the optimum, the minimum-to-maximum score spans were
between `4.04e-10` and `6.54e-9`; this showed that the diagnostic was measuring
the deliberately allowed objective slack rather than an alternate exact
optimum. The locked floor tolerance was therefore tightened prospectively to
USD `1e-7`, while the `1e-8` score-range stop was retained.

For gamma endpoints and coordinate `.50`, normalized and objective-matched
caps reconciled within `1.46e-11` dollars or machine precision. GLOP versus
HiGHS objective-rate and funded-score differences were at most `5.82e-17` in
that smoke. These values are implementation checks, not empirical findings and
did not determine any policy direction.

## Neighbor-method boundary

RAC, conformal robustness control, CROMS, CREME/inverse CRC, CREDO,
decision-calibrated sets, and end-to-end conformal optimization motivate the
decision-level question but are not valid plug-ins here. Their finite-sample
claims require exchangeable decision contexts or a specifically modeled
non-exchangeable sequence. CRPTO has 376,890 candidate loans but only 11 common
development menus, and the action is a coupled monthly allocation. The full
applicability contract is recorded in
`docs/research/ijds_decision_method_applicability_2026-07-12.md`.
