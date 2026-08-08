# IJDS equal-notional fixed-$K$ JOMI synthetic feasibility V1 protocol (2026-08-08)

## Status and authority

This is a locked **synthetic theorem-to-code validation protocol**. It is not
an active empirical evidence source, does not authorize any read of new loan
outcomes, and cannot support a selected-set, temporal, utility, causal, or
portfolio-validity claim for the inspected LendingClub archive.

The protocol tag is
`protocol/ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1`.
The only admissible artifact tag is
`artifacts/ijds-equal-notional-jomi-synthetic-feasibility-2026-08-08-v1`, on a
single direct child containing only the outputs declared in the locked YAML.

The study answers a narrower question that is useful before acquiring fresh
data: does the CRPTO implementation reproduce the exact top-$K$ JOint Mondrian
Conformal Inference (JOMI) construction, its fixed-$K$/equal-notional accounting
bridge, and the finite-threshold reference-size law under an explicitly i.i.d.
synthetic design? The Monte Carlo component is a bug detector and an
illustration under one declared data-generating process. It does not prove the
theorem or validate the historical portfolio.

## Why no real-data run is authorized

The 2007--2020Q3 LendingClub archive and the later cohorts used in historical
experiments have already been inspected. LendingClub ceased its Retail Notes
program in 2020, so no public same-population continuation supplies a fresh
confirmatory cohort. The current 11 development and 15 target issue months also
remain too few and too temporally dependent for a conformal-risk-control (CRC)
or Learn-Then-Test (LTT) retrofit. Reusing those observations would add numbers
without repairing the sampling law.

The first serious external candidate is the Freddie Mac Single-Family
Loan-Level Standard Sample, but its acquisition requires registration and a
separate origination-first, performance-sealed protocol. This synthetic study
therefore precedes rather than substitutes for that external design.

## Scientific questions

1. Does a generic swap-and-rerun reference construction agree exactly with the
   top-$K$ shortcut of Jin and Ren for every audited focal unit and both binary
   candidate labels?
2. Does the implementation preserve exactly $K$ selected units under
   calibration permutations, test permutations, visible-ID reversal, repeat
   execution, and a label-independent continuous tie priority?
3. Does equal exposure make count and invested-dollar false-coverage
   proportions identical in every realization?
4. Under i.i.d. continuous selection scores, does the exact beta-binomial law
   characterize finite-threshold resolution and provide a pre-outcome
   sample-size frontier?
5. Does the locked implementation exhibit the theorem-aligned Monte Carlo
   behavior under one declared nonlinear, misspecified-but-exchangeable binary
   design?
6. Can an exact two-loan construction show why nested prediction sets alone do
   not imply a monotone end-to-end portfolio loss after reoptimization?

No question asks whether the active CRPTO portfolios possess JOMI validity.

## Top-$K$ JOMI construction

Let $n$ labeled calibration units and $m$ unlabeled test units have a selection
score map $S(X)$ trained and frozen without using their calibration or test
labels; the ensuing selector is label-free. It funds exactly the $K$ test
units with the largest lexicographic
pair $(S,U)$, where the continuous tie priority $U$ is assigned independently
before labels and treated as part of the frozen covariate record. The primary
synthetic law has continuous $S$, so $U$ is inactive almost surely; it exists
to make the implementation total and auditable.

For a selected test unit $j$, the generic reference set swaps calibration unit
$i$ into test position $j$, reruns the identical selector, and retains $i$
exactly when the inserted unit remains selected and the selected set has size
$K$. Because selection is label-free, the reference does not depend on the
hypothesized binary label. For top-$K$ selection with distinct scores,
Proposition 6 of Jin and Ren reduces every selected focal reference to

\[
  \mathcal R_{\mathrm{topK}}
  =\{i\in[n]:S_i>T_{\mathrm{topK}}\},
\]

where $T_{\mathrm{topK}}$ is the $(m-K)$-th order statistic of the test scores.
The implementation must reconcile the shortcut and the generic swap oracle
exactly before any Monte Carlo output is eligible.

The binary nonconformity score is

\[
  V(x,y)=|y-\widehat q(x)|,\qquad y\in\{0,1\}.
\]

For reference size $r$, the deterministic threshold is the
$\lceil(1-\alpha)(r+1)\rceil$-th order statistic of the $r$ calibration scores
augmented by $+\infty$. This order-statistic definition is implemented
directly; library quantile conventions based on $r$, rather than $r+1$, are
forbidden. Both candidate labels are always inverted.

The threshold is not forced to $+\infty$ exactly when

\[
  r\ge r_\alpha
  :=\left\lceil \frac{1}{\alpha}-1\right\rceil.
\]

At $\alpha=0.10$, $r_\alpha=9$. This is only a finite-threshold condition: it
does not by itself ensure that the resulting binary prediction set is smaller
than $\{0,1\}$ or otherwise informative. The primary run stops if any primary
replication has $r<9$; it does not silently replace the cutoff by $+\infty$.

## Reference-size corollary

The following exact finite-sample top-$K$ result complements the general
asymptotic reference-size analysis in Proposition 9 of Jin and Ren; it is not
derived from that proposition. Combining their exact top-$K$ reference-set
identity with the classical shared-threshold beta--binomial mechanism
highlighted by Marques yields this role-reversed reference-size corollary. We
do not claim a new beta--binomial law, and the result is not a claim about the
historical archive. Its useful role here is the explicit pre-outcome
sample-size calculation.

**Corollary (top-$K$ finite-threshold resolution).** Suppose the $n$ calibration
selection scores and the $m$ test selection scores are i.i.d. from a continuous
distribution $F$, with $1\le K<m$. Let $T_{\mathrm{topK}}$ be the $(m-K)$-th
test order statistic and let
$R=\sum_{i=1}^n\mathbf 1\{S_i>T_{\mathrm{topK}}\}$. Then

\[
 Q:=1-F(T_{\mathrm{topK}})\sim\operatorname{Beta}(K+1,m-K),
 \qquad R\mid Q\sim\operatorname{Binomial}(n,Q),
\]

and hence

\[
 R\sim\operatorname{BetaBinomial}(n,K+1,m-K).
\]

Its probability mass function, mean, and variance are

\[
 \Pr(R=r)=\binom nr
 \frac{B(r+K+1,n-r+m-K)}{B(K+1,m-K)},
\]

\[
 \mathbb E[R]=\frac{n(K+1)}{m+1},\qquad
 \operatorname{Var}(R)=
 \frac{n(K+1)(m-K)(m+1+n)}{(m+1)^2(m+2)}.
\]

Therefore the exact probability that the deterministic JOMI threshold is not
forced to $+\infty$ is

\[
 \Pr(R\ge r_\alpha)
 =1-F_{\mathrm{BetaBinomial}}
 (r_\alpha-1;n,K+1,m-K).
\]

**Proof.** For continuous $F$, the probability integral transform sends the
$(m-K)$-th order statistic to
$F(T_{\mathrm{topK}})\sim\operatorname{Beta}(m-K,K+1)$, so its upper-tail
mass $Q$ has the displayed beta law. Conditional on the test threshold, the
$n$ independent calibration scores exceed it independently with probability
$Q$. Mixing the conditional binomial law over the beta law gives the stated
beta-binomial mass function and moments. The conformal threshold is finite
exactly when $\lceil(1-\alpha)(R+1)\rceil\le R$, which is equivalent to
$R\ge\lceil1/\alpha-1\rceil$. $\square$

The continuity and i.i.d. conditions are load-bearing. With ties, a
lexicographic score law must be stated; with sampling without replacement from
a fixed finite cohort, the beta-binomial statement is not automatic.

## Equal-notional bridge

For miss indicator $M_j=\mathbf1\{Y_j\notin C_j\}$, exactly $K$ selected
units, total capital $B$, and $a_j=B/K$,

\[
 \operatorname{FCP}^{\$}
 =\frac1B\sum_{j\in\widehat S}\frac BK M_j
 =\frac1K\sum_{j\in\widehat S}M_j
 =\operatorname{FCP}^{N}
\]

pathwise. Under the JOMI exchangeability, permutation, taxonomy, and reference
conditions, focal selection-conditional coverage plus the fixed-size taxonomy
implies expected count FCR at most $\alpha$, and the identity transfers that
same expectation bound to invested-dollar FCP. It does not give simultaneous
joint-label coverage, a high-probability bound for one realized portfolio,
fractional-allocation validity, or temporal transport.

The runner must not certify this identity by assigning the same computed value
to both fields. It constructs the $K$ unit allocations, verifies every
$a_j=B/K$ and $\sum_j a_j=B$, computes count FCP from miss counts, and computes
dollar FCP independently from the allocation-weighted misses and invested-
capital denominator.

## Locked synthetic design

One independent training draw of 50,000 rows fits a linear logistic learner.
One disjoint design draw of 20,000 rows fits Platt scaling on the frozen learner
logit. Those fitted objects are then held fixed for all 2,000 independent
calibration/test replications. Both fits use deterministic `lbfgs` with at most
500 iterations; the learner uses $C=1$ and Platt scaling uses $C=10^6$.
Any `ConvergenceWarning` or arrival at the iteration limit is a hard stop.

One master `SeedSequence` spawns named, nonreused streams for training
features and labels, design features and labels, and---within every
replication---calibration features, calibration labels, test features, test
labels, and pre-label tie priorities. Stream identities and the frozen model
fingerprint are part of the execution receipt.

Each row has eight independent standard-normal covariates. The true binary law
uses the locked nonlinear logit

\[
-1.4+1.2x_0-0.8x_1+0.65x_2x_3+0.9\sin(x_4)
+0.7\mathbf1\{x_5>0\}-0.35x_6^2+0.2x_7.
\]

The linear learner is deliberately misspecified; this tests distribution-free
implementation without selecting a favorable model. The synthetic interest
rate is

\[
 r(x)=0.04+0.08\,\operatorname{logit}^{-1}
 (0.6x_1-0.3x_2+0.2x_7),
\]

and the label-free selection score is

\[
 S(x)=(1-\widehat q(x))r(x)-0.45\widehat q(x).
\]

Each replication contains $n=5{,}000$ calibration rows and $m=2{,}000$ test
rows, selects $K=100$, and allocates $1/K$ to every selected row. The only
primary method is deterministic JOMI. Vanilla split conformal is retained as a
diagnostic comparator; whether it looks favorable is never a stop or promotion
criterion.

Conditional on that single frozen training/design fit, the replication, not a
selected loan, is the independent Monte Carlo unit. The run reports the mean
replication-level FCP and a one-sided 99.9% Hoeffding lower bound. A lower bound
above 0.10 is a hard implementation-warning stop; failure to cross that
boundary is not a proof of coverage or an unconditional average over refits.

## Exact, analytic, and scale controls

Before the primary simulation, the runner must:

1. reconcile generic swaps and the shortcut over the declared exhaustive
   canonical calibration/test rank interleavings---$\binom{n+m}{n}$, namely
   126, 462, and 495 cases---and 250 seeded random fixtures;
2. enumerate both candidate labels for every focal unit;
3. verify the beta-binomial mass sums to one and matches its closed-form
   moments;
4. calculate the full declared finite-threshold resolution frontier and the
   minimum calibration sizes achieving 95% and 99% finite-threshold
   probability; every cell stores both the survival probability and the
   below-resolution lower tail, plus its log probability, so float64 survival
   saturation at one cannot erase a small but nonzero failure probability;
5. verify permutation, test-equivariance, tie-priority, repeat, and visible-ID
   controls; and
6. run ten outcome-free selection fixtures at menu sizes 6,011, 10,000, and
   28,106.

The $R\ge r_\alpha$ hard stop applies only to the 2,000 primary replications.
The larger-menu scale fixtures deliberately audit resolution pressure and may
record $R<r_\alpha$ without classifying it as an implementation failure.

The analytic CRC/LTT table is design evidence only. Finite-grid non-monotone
CRC assumes a bounded loss $0\le L\le B$ with the locked value $B=1$ and uses

\[
D_B(M,n)=B\sqrt{\frac{\log(2M)}{2n}}
+\frac{B}{2\sqrt{2n\log(2M)}}.
\]

This is an expected-risk excess bound and has no confidence-$\delta$ parameter.
The table therefore labels its tail-probability fields not applicable, reports
the minimum $n$ for the declared catalog sizes and excess targets, and requires
a pointwise zero-loss terminal policy rather than a merely mean-safe candidate.
The separate LTT rows use the locked familywise tail budget $\delta=0.10$ and
report optimistic bounded-loss Hoeffding/KL context requirements; they cannot
be read as power guarantees.

## Reoptimization counterexample

Two loans and one unit of capital suffice. At $\lambda_0$, both prediction sets
are $\{0\}$; both worst-label coefficients are zero; and objective values 2 and
1 make the optimizer allocate the unit to loan A. A's realized label is 0, so
its unit miss and portfolio contribution are both zero. Loan B has realized
label 1 and therefore unit miss one at both parameter values, but its allocation
at $\lambda_0$ is zero and so is its portfolio contribution. At $\lambda_1$,
A's set expands to $\{0,1\}$, making its worst-label coefficient one and
violating a zero upper cap. B remains feasible with set $\{0\}$, receives the
unit allocation, and contributes loss one.

Every prediction set is nested, yet end-to-end loss increases because the
allocation changes. Thus classical scalar CRC is clean only when allocation is
fixed across the nesting parameter or a separate universal proof establishes
monotonicity of the complete reoptimized loss.

## Runtime and observability

The computation runs from a clean exact protocol tag, with a single process
and one worker, below-normal priority when supported. Scratch and status live
under a fresh run-specific directory on `D:/CRPTO/runtime`, outside Git,
official artifacts, protected reads, and DVC cache. One complete replication is
the atomic unit; the denominator is 2,000 and never changes.

The observer writes a bounded operational heartbeat every 30 seconds and no
scientific value to status. The wall deadline is 1,800 seconds. Resume is not
authorized: interruption or deadline produces no official output and requires
a new successor protocol or a complete clean replay. Official paths are created
only after every replication and validation passes.

## Hard stop rules

Stop without official materialization or paper promotion if:

1. the protocol tag is absent, not exact, lightweight, or the worktree is dirty
   at launch;
2. a generic reference differs from the shortcut once;
3. a calibration permutation, test permutation, visible-ID reversal, or repeat
   changes anything beyond the corresponding row identities;
4. the selected support differs from $K$, a candidate label is skipped, or a
   primary reference size is below $r_\alpha$;
5. count and dollar FCP differ by any representable amount;
6. a replication is missing, duplicated, nonfinite, partial, or retained after
   a failed unit;
7. the 99.9% one-sided lower warning bound exceeds $\alpha$;
8. any DGP, seed, model, calibrator, comparator, cell, figure, or stop rule is
   edited after the protocol tag;
9. the wall deadline is reached; or
10. an output path already exists.

## Claim boundary

Permitted after a complete run:

- the implementation reconciles with the generic top-$K$ swap construction in
  the complete declared fixture bank;
- equal-notional allocation makes count and dollar FCP identical;
- combining the JOMI top-$K$ reference identity with the classical
  beta--binomial count law yields the stated exact pre-outcome finite-threshold
  frontier; this is neither a new beta--binomial law nor a guarantee that a
  realized set is informative; and
- the locked implementation's Monte Carlo behavior under the one named
  synthetic i.i.d. DGP.

Forbidden:

- LendingClub, funded-set, or selected-set validity for the active paper;
- temporal, covariate-shift, causal, utility, payoff, or prospective claims;
- validity for fractional exposures or the current LP;
- joint Cartesian-product label coverage;
- a policy, learner, calibrator, coordinate, ruler, or winner; and
- any statement that simulation proves JOMI or repairs a missing theorem
  premise.
