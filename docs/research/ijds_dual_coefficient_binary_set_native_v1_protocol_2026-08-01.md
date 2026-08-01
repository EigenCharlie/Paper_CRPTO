# IJDS dual-coefficient binary-set-native protocol V1 (2026-08-01)

## Status and retrospective question

This is an outcome-free, retrospectively designed logical audit of the active
set-native Phase-A evidence. The predecessor's complete results were already
inspected. V1 asks whether its 208 monthly menus satisfy conditions under which
the exact binary-set decision model has a closed-form structural conclusion,
making another cap grid and another optimizer census scientifically redundant.

Required protocol tag:
`protocol/ijds-dual-coefficient-binary-set-native-2026-08-01-v1`.
Required run:
`ijds-dual-coefficient-binary-set-native-2026-08-01-v1`.

The implementation, protocol, config, runner, and tests must be committed and
annotated-tagged before execution. This implementation step performs no run,
reads no raw archive, imports no endpoint, and changes no active claim.

## Exact two-coefficient decision model

Let `S_i` be the frozen binary prediction set. For a nonempty set, define the
loan's objective coefficient as the minimum standardized credit payoff over
the labels in `S_i`:

```text
u_i(S_i) = min_{y in S_i} [(1-y) r_i - y LGD].
```

Here `r_i` is the nonnegative contractual rate and `LGD>0`. The predecessor's
declared fail-closed decision convention first completes an empty set to
`{0,1}`; this is a convention, not a conformal theorem. Therefore the objective
has exactly two coefficient classes:

```text
u_i = r_i    when S_i = {0};
u_i = -LGD   when S_i is empty, {1}, or {0,1}.
```

The terminology is deliberately exact: V1 calls the first class exclusively
`singleton-zero`. Neither coefficient is an individual calibrated PD, expected
payoff, or global worst-case loss outside the completed set.

The accompanying risk coefficient is the predecessor's exact set score:

```text
q_i = 0  iff S_i = {0};
q_i = 1  otherwise.
```

Both portfolio expressions are additive loanwise functions of these marginal
binary sets. They are not an optimization over a jointly covered Cartesian
product of outcomes, and no joint-law or simultaneous-coverage statement is
used in the theorem below.

## Conditional substitution theorem

Fix one menu. Its inherited allocation polytope has candidate bounds
`0 <= a_i <= loan_amnt_i`, exact budget equality `sum_i a_i=B`, no cash,
one exhaustive disjoint purpose label per candidate, and only upper purpose
caps `sum_{i in g} a_i <= cB`. There are no lower purpose constraints or
overlapping constraint groups.

Assume there exists a feasible full-budget allocation supported only on
singleton-zero candidates. Take any feasible allocation with positive exposure
`D` outside singleton-zero. Remove that exposure. If `A_g` is the remaining
singleton-zero exposure in purpose `g`, and `U_g` its available candidate
amount, the unused admissible singleton-zero capacity is

```text
sum_g [min(U_g,cB)-A_g] >= B-sum_g A_g = D.
```

The inequality follows from existence of a singleton-zero full-budget
allocation. Because groups are disjoint and have upper constraints only, the
removed `D` can be reassigned across singleton-zero candidates without changing
the budget or violating a bound or purpose cap. Each replaced dollar improves
the objective by at least `LGD`, since its old coefficient is `-LGD` and its
new coefficient is a nonnegative contractual rate. Thus every maximin optimizer
has zero exposure outside singleton-zero.

Every singleton-zero optimizer is feasible for every set-risk cap in `[0,1]`
and has constructed set risk zero. Hence the maximin objective value and full
optimal face are identical over the continuous cap domain. This is a
conditional frontier-collapse theorem, not a numerical interpolation result.
V1 does not claim a unique allocation.

The result can fail if the budget is not exact, cash is present, purpose groups
overlap, lower constraints exist, rates can be negative, `LGD=0`, empty sets
are not failed closed, or singleton-zero full-budget feasibility fails.

## Existing existence certificate

No new optimization is needed. The hash-pinned predecessor already solved the
minimum exact set score under the same exact-budget, no-cash, bounded-loan,
disjoint upper-purpose-cap polytope. Because `q_i` is binary and equals zero
only for singleton-zero, `minimum_score=0` is equivalent to existence of a
feasible full-budget singleton-zero allocation.

V1 reads only four Git-tracked predecessor authorities:

1. 1,248 frontier solve records;
2. 208 set-taxonomy rows;
3. the Phase-A summary; and
4. the verified Phase-A manifest.

Their descriptors and the predecessor config, protocol, runner, implementation,
source loader, LP, payoff, and conformal-set code are hash-pinned in the V1
config. V1 verifies all six ruler--coordinate repetitions in each menu. Every
repetition must report `minimum_score=0`, a USD 1 million total allocation,
budget residual within `1e-4`, no cash variable, the exact binary score,
fail-closed empty-set convention, and optimal status. The six repetitions are
not six independent certificates: they reconcile to one certificate per menu.

The taxonomy must contain exactly 208 unique menu identities and partition
every candidate into empty, singleton-zero, singleton-one, and two-label sets,
with risk zero exactly equal to the singleton-zero count. The final census is
exactly eight windows times 26 role--month menus, or 208 certificates.

## Outputs and stop rules

V1 emits only one 208-row Parquet certificate table plus a summary, receipt,
manifest, and protocol freeze. It performs zero LP solves and writes no
allocation table. It stops before output on a dirty or untagged HEAD, source or
tag mismatch, nonzero minimum score, budget/cash failure, invalid taxonomy,
incomplete identity grid, or occupied output path. DVC and protected stages are
not invoked.

After committing and creating the required annotated protocol tag, execute only:

```powershell
uv run --locked python scripts/experiments/run_ijds_dual_coefficient_binary_set_native_v1.py `
  --config configs/experiments/ijds_dual_coefficient_binary_set_native_2026-08-01_v1.yaml
```

## Interpretation boundary

Passing V1 establishes a finite-archive structural certificate for this one
declared binary-set objective and inherited polytope. It does not repair
conformal validity, give joint coverage to the Cartesian product of marginal
sets, provide probabilistic robust-optimization coverage, establish funded- or
selected-set validity, select a cap, window, allocation, or policy, identify a
winner, prove optimizer uniqueness, or support causal, prospective, deployment,
or outcome-performance claims. No Phase B exists in this lineage.
