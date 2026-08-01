# Exact Binary Conformal Geometry: Statements, Refutations, and What Survives

Status: theory note, revision 3, after a fourth adversarial review.
Date: 2026-07-26.
Scope: statements, proofs and refutations only. Nothing here is paper-facing until a
registered lineage exists in `configs/ijds_active_evidence_sources.yaml` and the claim
ledger.

**Revision note.** Revision 1 of this file proposed three results (T1, T2, T3). Two
were wrong or tautological as stated and one was already published. This revision
records the refutations explicitly, because the refutations are more useful than the
original claims and two of them are corrections the *existing manuscript* needs.
Superseded material is marked WITHDRAWN or REFUTED rather than deleted.

---

## 0. Setting

Fix a frozen score stratum `g`. Calibration units `i = 1..n` with Platt-scaled scores
`p_i in [0,1]`, binary endpoints `Y_i`, default count `D = #{Y_i = 1}`,
`k = ceil((n+1)(1-alpha))`, `alpha = 0.10`. The nonconformity score is

    s_i(y) = |y - p_i| = 1 - phat_i(y),

which in the binary case is exactly the **least-ambiguous set-valued classifier
(LAC)** score of Sadinle, Lei and Wasserman (2019). The manuscript now identifies
and cites that equivalence. Note the
caveat that comes with the name: LAC's small-expected-size optimality is an *oracle*
result in the true `phat`, and is not inherited by a Platt-scaled estimate.

Objects: `S_i = {y : |y - p_i| <= c}`, `[l_i, u_i] = [max(0, p_i - c), min(1, p_i + c)]`,
`m_i = 1{Y_i=0, l_i>0} + 1{Y_i=1, u_i<1}`.

Implementation facts that the statements must respect
(`src/models/binary_conformal_guardrail.py`):

- `c` is `sort(residuals)[k-1]`, ascending, so `c = R_(k)` — but only if `k <= n`.
- When `k > n` the code sets the quantile to **`1.0`, not `+infinity`**. This is
  observationally identical for the binary set map, but the note must not assert a
  convention the code does not implement.
- `fit_binary_outcome_recipe` validates finiteness but **not** `p in [0,1]`. The
  order-statistic statement is therefore conditional on that precondition holding.

---

## 1. L1 — Order-statistic characterization

Because `s_i(Y_i) = p_i` when `Y_i = 0` and `1 - p_i` when `Y_i = 1`, the calibration
residuals are the **multiset sum** of two mirror samples:

    R = {{ p_i : Y_i = 0 }}  (+)  {{ 1 - p_i : Y_i = 1 }},     c = R_(k).

**Preconditions:** `p_i in [0,1]` for all calibration `i`, and `k <= n`.

**Exact boundary:**

    n - k = floor(alpha*(n+1)) - 1.

This is an identity for every integer `n >= 1` and every `alpha` in `(0,1)`, not a
regularity of this archive. Write `N = n+1`. Since `N` is an integer,
`ceil(N - x) = N - floor(x)`, so
`k = ceil(N(1-alpha)) = ceil(N - N*alpha) = N - floor(N*alpha)`, and therefore
`n - k = (N-1) - (N - floor(N*alpha)) = floor(alpha*(n+1)) - 1`. When
`floor(N*alpha) = 0` the boundary is `-1`, which is exactly the `k = n+1`
capped-threshold case.

Revision 1 said "approximately alpha*n". Use the closed form.

---

## 2. L2 — Phase criterion, with the corrected hypothesis

Revision 1 used the separation condition
(S): `max{p_i : Y_i=0} < 1 - max{p_i : Y_i=1}` for everything. That was an error.

When both calibration classes are nonempty, **(S) is sufficient for exactly one
claim:** `c` is a nondefault residual iff `k <= n - D`, i.e. iff
`D <= n - k`. (S) is precisely no-interleaving of the two mirror samples.
One-class blocks obey the general order-statistic identity but require their own
degenerate-case statement rather than maxima over an empty class.

**REFUTED (revision 1):** "equivalently, `c < 1/2` iff `D <= n - k`" **under (S)**.
Counterexample: `n = 20`, `alpha = 0.1`, `k = 19`, `n - k = 1`. Nineteen nondefaults,
eighteen at `p = 0.10` and one at `p = 0.70`; one default at `p = 0.20`. Then (S)
holds (`0.70 < 0.80`) and `D = 1 <= 1`, yet `R_(19) = 0.70 >= 1/2`. (S) constrains the
*sum* of the two maxima, not either one against `1/2`.

**Corrected.** Let `A = #{Y_i=0, p_i<1/2}`, `B = #{Y_i=1, p_i>1/2}`. Exactly:

    c < 1/2   <=>   A + B >= k.

The checkable hypothesis that recovers the intended statement is

    (S-half):  max_i p_i^{cal} < 1/2,

which gives `A = n - D`, `B = 0`, hence `c < 1/2 <=> D <= n - k`. **(S-half) is the
standing hypothesis for every claim anchored at 1/2**; (S) is retained only for the
"which block does `c` come from" claim.

**Phase margin.** `m_g = D_g - (n_g - k_g) = D_g - floor(alpha*(n_g+1)) + 1`, with
`m_g <= 0` iff the low regime, under (S-half).

**REFUTED (revision 1):** "exact Binomial tail". Only under conditionally independent
Bernoulli labels given fixed scores and correct calibration does a varying-score
default count have a **Poisson--binomial** law; it reduces to Binomial only when the
within-stratum scores are constant. Neither conditional independence nor calibration
is established here, and the statement must also condition on the random stratum
size `n_g`. Therefore no crossing reference law is active.

**NARROWED (revision 1):** "monitorable early-warning statistic". `m_g` and `c_g` are
computed from the same calibration block at the same instant, so `m_g` gives no timing
advantage over reading `c_g`. What survives: `m_g` is an **integer signed phase
coordinate**. Holding scores and membership fixed under (S-half), a low-branch block
with `m_g<=0` needs `1-m_g` nondefault-to-default label flips to enter the high branch;
a high-branch block with `m_g>=1` needs `m_g` reverse flips to enter the low branch.
Without an independently justified joint label model, this deterministic flip distance
has no active reference law. The eight windows overlap, so any exploratory per-window
crossing statistic is not a sequential monitoring procedure.

---

## 3. L3 — Set geometry, with corrected conditions

`0 in S <=> p <= c`; `1 in S <=> 1-p <= c`. Hence, exactly and unconditionally:

    S = empty   <=>  c < min(p, 1-p)          [conjunction, not a gloss]
    S = {0}     <=>  p <= c < 1-p
    S = {0,1}   <=>  c >= max(p, 1-p)         [revision 1 wrote "c >= 1-p": WRONG]
    S = {1}     <=>  1-p <= c < p             [requires p > 1/2]

Boundaries: at `p = c` we have `0 in S`, and the clipped form agrees exactly
(`l > 0 <=> p > c`, `u < 1 <=> 1-p > c`), so `eq-binary-miss` is precisely the
set-membership rule with no inequality mismatch. At `p = 1/2` exactly, no singleton is
possible. `AvgC = 1 - e + b` and `OneC = 1 - e - b` are trivial consequences of
`e + b + s = 1`; they require neither conformal structure nor any hypothesis and must
not be presented as results.

**Free corollary:** `empty` is equivalent to `c < p < 1-c`, and therefore requires
`c < 1/2`. Empty sets are impossible in every high-threshold cell. In a low-threshold
cell their occurrence additionally requires target support inside the open central
band `(c,1-c)`. Merely observing `p>c` is insufficient: when `p>=1-c`, label one is
included and the set is `{1}` rather than empty.

### The category error, and the corrected `{1}` explanation

**REFUTED (revision 1):** "`{1}` is impossible under (S), which is why Table S6A shows
a nonzero `{1}` share only for numeric logistic, the only learner whose scores exceed
1/2."

The category error is that (S) and (S-half) constrain **calibration** scores,
whereas the set map quantifies over **target** units; neither condition constrains
target support. Checking a calibration maximum cannot establish a target-set claim.

**Corrected:** the exact support boundary depends on the threshold regime. If
`c<1/2`, then `{1}` occurs exactly at `p>=1-c`; if `c>=1/2`, it occurs exactly at
`p>c`. Thus `sup p<=c` precludes `{1}` in a high-regime cell, while a finite
low-regime panel needs `max p<1-c`.

**REFUTED (revision 1):** "in the high regime no nondefault is missed". This needs
`P_t(p>c,Y=0)=0`, not merely `c >= 1/2`; `sup target p<=c` is an
outcome-free sufficient condition.

---

## 4. L4 — The coverage ceiling, and the stratification corollary

**Coverage identity (correct, and it needs no regime and no separation condition):**

    Cov_t = (1 - pi_t) * P_t(p <= c | Y=0)  +  pi_t * P_t(p >= 1-c | Y=1).

Use the left limit `1 - F_t^1((1-c)^-)`; scores are atomic. This is the strongest
statement in the note and follows directly from `eq-binary-miss`.

**Ceiling, corrected.** Revision 1 claimed `c < 1/2 => Cov_t <= 1 - pi_t`. That
silently assumed `p < 1/2` for the **target** unit. Counterexample: calibration all
`Y=0` with `c = 0.42 < 1/2`; a target default at `p = 0.65` gets `u = 1` and is
covered. Corrected:

    c_g < 1/2  =>  Cov_{t,g} <= 1 - pi_{t,g} + pi_{t,g} * P_t(p >= 1-c_g | Y=1),

If `P_t(p >= 1-c_g | Y=1) = 0`, the clean ceiling `Cov <= 1 - pi_t` follows, and
`sup{p : target, g} < 1 - c_g` is a sufficient support condition. The condition is
not necessary for the numerical inequality: missed nondefaults can offset covered
defaults.

### L4 — Conditional stratum diagnostic

For a frozen calibration stratum, the phase margin is an exact diagnostic of which
calibration-class maximum supplies the order statistic, subject to the conditions in
L2.  It does **not** follow that score binning guarantees a low-regime stratum.  A
perfectly calibrated score can, for example, have support only on `[0.15, 0.25]` when
`alpha=0.10`, or be constant at `0.20`; every bin can then lie above the phase
boundary.  Finite-bin prevalences also need not be ordered even when population
conditional means are ordered.

**Conditional corollary.** If a frozen stratum satisfies the below-half separation
condition and its phase margin selects the negative-class branch, then the threshold
is the `k`-th smallest calibration score among negatives. It is their maximum only at
the boundary `m_g=0`. The stratum has zero
positive-class target coverage only with the additional target-support condition
`P_t(p >= 1-c_g | Y=1,g)=0`.  Thus the phase margin is calibration-only, whereas the
zero-positive-coverage conclusion is a calibration-plus-target diagnostic.

Score-Mondrian and label-Mondrian target different conditioning variables.
Label-Mondrian is retained as a retrospective outcome-free sensitivity; it is not a
proved repair for temporal nonexchangeability and does not transfer a classwise
coverage guarantee to this archive.

No archive-wide phase count is active until a clean, registered empirical replay is
promoted. The theory alone does not license the universal phrase “degenerate by
construction.”

---

### L4 — external probes are quarantined

Earlier cross-archive probes and the attempted V1 external run are exploratory
provenance only. They do not support a paper-facing generality claim: the V1 evidence
predates its protocol; the Freddie fit and calibration samples are not ordered
temporal blocks; target sets, target support and target coverage were not evaluated;
and neither input identity nor use rights were registered. No external number or
archive name from those probes may enter the active manuscript. A future illustration
would require a post-inspection protocol, true temporal roles, registered hashes and
rights, freeze before target contact, and complete target-set and coverage evaluation.

## 5. L5 — Exact coverage change between two thresholds

For any fixed target distribution and `0 <= c_L < c_H <= 1`, the exact identity is

    Cov(c_H) - Cov(c_L)
      = P(Y=0, c_L < p <= c_H)
        + P(Y=1, 1-c_H <= p < 1-c_L)
      = (1-pi) P(c_L < p <= c_H | Y=0)
        + pi P(1-c_H <= p < 1-c_L | Y=1).

It is nonnegative and shows that a coverage change is determined by target mass in
the two crossed score bands, not by threshold distance alone. It does **not** imply
continuity: atoms can make coverage jump from zero to one even with varying scores.
It also does not couple the `m=0` and `m=1` thresholds of two different calibration
blocks through a common pair of class maxima.

For unresolved target outcomes, let

    d_i(y) = 1{|y-p_i| <= c_H} - 1{|y-p_i| <= c_L}.

Sharp completion bounds follow by adding `min_{y in {0,1}} d_i(y)` and
`max_{y in {0,1}} d_i(y)` over unresolved units, together with the resolved terms.

Archive-specific magnitudes are active only through the clean-tagged V8
common-panel replay, which retains the complete 175-stratum and 35-learner
adjacent-transition censuses. The highlighted CatBoost S3 (the third score
stratum; internal zero-based group 2) W7--W8 pair was
inspected before that replay and remains descriptive. Sharpness is cellwise under
one shared unresolved-label completion per contrast; no globally shared completion,
selected transition, slope, temporal-transport explanation, or causal claim is
authorized.

---

## 6. T2 — WITHDRAWN. No universal optimizer mechanism

**REFUTED (revision 1), three ways.**

**(a) The verification was a null test.** The objective-matched ruler *minimizes*
`s(gamma)'a` subject to an objective floor; it has **no risk row and no `tau`**.
`frontier_cap` is null for 100% of `objective_matched` rows (2,496 of the 4,992
`gamma > 0` portfolios). Revision 1 substituted the realized weighted score for `tau`,
which reduces the claim to `gamma * 1{u=1} <= q` summed against a nonnegative weight —
true for any vector, feasible or not, using no constraint of the program. "0 violations
in 4,992" therefore could not have failed. The bound is a genuine theorem **only for
the normalized-score ruler**, where the cap is exogenous and binds (max slack
1.48e-12 over 3,120 portfolios).

**(b) The comparative claim is empirically false.** Revision 1 offered T2 as "a
theorem-level explanation" for miscoverage being adverse in 40 of 48 cells. Across
1,248 matched pairs, `gamma=1` versus `gamma=0`: saturated exposure is **higher** for
the guardrail in 517 pairs and lower in 48; covered-default exposure is **higher** in
345 and lower in 19. The adverse direction is driven by the guardrail funding a higher
realized default rate (`+0.0257`, about 89% of the effect) and by missed nondefaults
(`+0.0070`), while covered defaults move `-0.0039` — the **wrong sign**, about one
seventh of the magnitude. The bounded quantity moves in the guardrail's favour.

**(c) The proposed objective theorem was also overgeneralized.** For fixed contractual
rate and loss-given-default, the plug-in coefficient decreases with `p`; across loans,
rates and constraints vary. Moreover `u_i=1` is the condition for covering `Y=1`, but
whether that corresponds to a “high” score depends on the stratum threshold. No global
anti-selection theorem follows for the optimizer used here.

### The valid outcome-free statement

For a fixed allocation and binary sets represented by endpoints `(l_i,u_i)`, sharp
outcome-free exposure-weighted miscoverage bounds are

    MC_L = sum_i a_i 1{l_i>0 and u_i<1} / B_0,
    MC_U = sum_i a_i [1 - 1{l_i=0 and u_i=1}] / B_0,

for the declared normalizer `B_0`. Empty sets always miss and full sets never miss;
the labels of all other binary sets can attain either endpoint independently. In
particular, `l_i>0` alone is **not** a miscoverage floor: if `(l_i,u_i)=(0.6,1)` and
`Y_i=1`, the observation is covered.

The share `sum_i a_i 1{u_i=1}/B_0` is only the total-capital-normalized exposure able
to cover a positive label. It is not an upper bound on conditional positive-class
coverage, whose denominator is positive-label exposure. Neither result identifies a
policy direction or a universal incompatibility between conformal prediction and
optimization.

### Exact continuous-embedding fibre retained after binary intersection

The binary set identifies only endpoint contact with zero and one. If a bounded
continuous interval is additionally required to contain its center `p`, then for
`0<gamma<=1` the downstream coefficient `q=(1-gamma)*p+gamma*u` has the exact
compatible fibre

    {p+gamma*(1-p)}              when 1 belongs to S,
    [p,p+gamma*(1-p))            when 1 does not belong to S.

At `gamma=0`, `q=p`. Under rectangular loan-wise ambiguity and nonnegative
allocations, the supremum coefficient is therefore `p+gamma*(1-p)` for every
loan. At `gamma=1`, naive worst-fibre robustification assigns coefficient one
to every loan: a full-budget cap below one is infeasible, while a formulation
with optional cash reduces the constraint to total invested capital and loses
loan discrimination. For sets without label one the boundary is a supremum,
not generally an attained maximum. This is an information-loss corollary for
the declared fibre. It neither asserts that an optimizer must change nor treats
the product of marginal binary sets as a jointly covered uncertainty set.

---

## 7. T3 — WITHDRAWN

Revision 1 proposed an exact additive decomposition of the coverage shortfall into
prevalence and within-class score components. Withdrawn for four independent reasons.

1. **Published.** Wasserstein-regularized conformal prediction (ICLR 2025,
   arXiv:2501.13430) decomposes the coverage gap into covariate-shift and
   concept-shift terms via pushforward measures, with the explicit design goal that
   the two effects be separable. Podkopaev & Ramdas (UAI 2021, arXiv:2103.03323) cover
   the label-shift half. `barber2023beyond` and `tibshirani2019covshift`, both already
   cited, bound the gap by total-variation and density-ratio arguments.
2. **The identity as written is wrong.** With `Cov = (1-pi)a + pi*b`, the exact
   identity has **four** terms, not three: the omitted one is the Oaxaca--Blinder
   interaction `delta_pi (delta_a - delta_b)`, which can be first-order rather than
   a discretization residual. Revision 1's "rank-discretization residual" therefore
   both misnames it and hides the resulting path dependence.
3. **"Every out-of-time shortfall is transport, not sampling" is false** and
   contradicts the manuscript's own Appendix B.4.1: even under exchangeability the
   target miss count is random under the Beta--Binomial reference law. If shortfall
   were transport by construction, the sampling reference would be conceptually
   pointless.
4. **The component intervals are not sharp.** Under unresolved completion the same
   label enters `pi_t`, `a_t` and `b_t` simultaneously, and each component is bilinear
   in the completion, so interval arithmetic over components gives an outer bound —
   exactly the error D.5 and B.4.2 warn against. A stratum-composition channel is also
   missing, and the aggregate calibration coverage is not `k/n` but a weighted mixture.

Also corrected for the record: revision 1 said calibration coverage is "within `1/n`
of `1-alpha`". The true deterministic bound is
`(1-alpha)/n <= k/n - (1-alpha) < (2-alpha)/n`.

The one piece worth keeping is the exact two-threshold identity in section 5. It is a
separate target-band accounting identity, not a continuity bound or a decomposition
of transport mechanisms.

---

## 8. A defect in the existing manuscript: Proposition 4 requires uniqueness it declines

This is not about the new material. Proposition 4's convexity argument is fine on a
fixed basis, but its conclusion is about sharp payoff, default and miscoverage
contributions, which are functionals of the **allocation** `a(c)`, not of the LP
objective value. The registered support audit establishes objective-side facts: for a
basic upper-only row with zero dual, a looser cap keeps the incumbent optimal, with the
same dual certificate and the same objective. Under dual degeneracy the objective can
be constant while the optimal **set** changes, so `a(c)` is a set-valued map and
"affine in `c`" has no referent. The V3a protocol explicitly declines any uniqueness
claim; Proposition 4 silently requires one.

Additional soundness problems with treating the current breakpoint walk as a
certificate:

- Basis ranging intervals are not optimal-partition invariancy intervals under
  degeneracy, and are solver-path dependent (Jansen, de Jong, Roos, Terlaky, EJOR 1997).
  The audit itself records primal degeneracy and thirteen scale-aware warnings.
- The walk warm-starts from the previous basis with presolve on, so interval widths
  depend on the probe sequence and the HiGHS build. Pinning 1.15.1 is provenance, not
  proof.
- `src/ijds_audit/portfolio.py` clips reported basis endpoints into `[lower, upper]`
  before recording them and then unconditionally overwrites the first and last
  deduplicated entries with `lower` and `upper`. The ends of `[0.05, 0.12]` are covered
  by assignment inside the routine whose job is to certify coverage.
- "No gap above 1e-10" is a merge convention, not an error bound, on a model whose
  coefficients span roughly seven orders of magnitude.

**Required action.** Either bring Proposition 4's wording down to the V3a protocol's
level — conditional on an exhaustive partition *and* on a unique optimum per cell,
neither established — or supply a genuine certificate: optimal-partition parametric
analysis with one-sided duals at each seam, exact rational arithmetic, or rigorous
a-posteriori interval verification.

**Current boundary (2026-07-26).** The manuscript states Proposition 4 only
conditionally on a unique optimum and an exhaustive fixed-basis partition. The
unregistered midpoint residual check is an internal diagnostic, not paper evidence:
a solver can return the same vertex of a non-singleton optimal face and obtain zero
residual, and endpoints plus one midpoint do not certify global affinity. Its numerical
result must therefore be absent from the manuscript and supplement unless a separate
registered certificate is built.

---

## 9. A second defect: the JOMI obstruction as drafted is false

Revision 1 proposed that JOMI does not apply because budget coupling breaks
permutation invariance. **That is wrong.** JOMI (Jin & Ren 2025, JRSS-B) requires
invariance to permutations of the **calibration** units, not of the test batch; the
selection rule may depend jointly on the entire test batch, and the paper's own worked
examples include top-K, threshold, p-value and **knapsack** selection. Budget-coupled
menu selection is the advertised regime, not an obstruction.

**Correct obstructions to state instead:**

1. **Exchangeability.** JOMI still needs calibration/target exchangeability to build
   its reference set. That is exactly the condition this audit refuses to assume.
2. **Estimand mismatch.** JOMI conditions on the binary event {unit selected}. The
   estimand here is dollar-exposure-weighted set coverage over a *fractional*
   allocation `a_i in [0, A_i]`; "selected" is not the primitive.
3. **Outcome incompleteness is an evaluation boundary, not a construction
   obstruction.** Calibration labels are available and target labels are not needed
   to construct a selection-conditional set. The 12,076 unresolved target outcomes
   would instead keep retrospective selected-coverage evaluation partially identified,
   so any comparison would still require the common-completion bounds.
4. **Cost** (practical, not a validity argument): the reference set requires re-running
   the selection with each calibration unit posited as the test unit, and each re-solve
   changes the coupled feasible set.

Obstruction (1) is load-bearing for the entire manuscript, which makes this a stronger
position than the false one it replaces.

---

## 10. What is actually left, and how to use it

Ranked by defensibility:

1. **L1–L3 exact geometry**, with every below-half, non-interleaving and finite-rank
   condition stated explicitly.
2. **The exact two-threshold coverage-band identity**, which explains why target mass,
   rather than threshold distance alone, determines the observed coverage response.
3. **The conditional stratum diagnostic**, separating a calibration-only phase margin
   from the additional target-support condition needed for zero positive coverage.
4. **Sharp empty/full-set outcome-free bounds**, without an optimizer mechanism or
   policy-direction claim.
5. **The Proposition 4 and JOMI corrections**, required regardless of which empirical
   additions are retained.

These results support an identification audit, not a pre-deployment certificate or a
universal design prohibition. In the active archive the frozen low-bin pattern is
descriptive evidence; it must not be generalized to all score-Mondrian constructions.

---

## 11. Claim boundaries

Nothing here licenses a selected learner, window, taxonomy, lag, gamma, ruler,
coordinate, cap, scenario, comparator or policy; selected-set or funded-set conformal
validity; a claim that the split-conformal theorem fails; an identified shift
mechanism; or any causal, prospective, deployment or fair-lending conclusion. The
forbidden-claim list in `docs/research/active_claims_2026-07-14.md` remains in force
without relaxation.
