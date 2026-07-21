# IJDS Policy-Support Optimal-Face Audit V2 Protocol

## Status and retrospective boundary

This document locks a new outcome-free numerical audit before execution. It
inherits the complete cap-month census from the inspected V1 policy-support and
solver-tie audit, but it does not overwrite V1 or reinterpret V1 as a complete
uniqueness certificate. The archive, V1 column reduced-cost results, primal
degeneracy counts, reverse-ID stress, exact-support outcomes, and manuscript
claims have already been inspected. V2 is retrospective protocol discipline,
not preregistration, prospective confirmation, or a new policy search.

Required tag, to be created only after the implementation is committed and
reviewed:
`protocol/ijds-policy-support-optimal-face-audit-2026-07-21-v2`.

Required run tag:
`ijds-policy-support-optimal-face-audit-2026-07-21-v2`.

No execution, tag creation, DVC registration, evidence promotion, or manuscript
change is authorized by this protocol file alone.

Execution accepts only the tracked canonical config
`configs/experiments/ijds_policy_support_optimal_face_2026-07-21_v2.yaml` at
the tagged clean HEAD. An equivalent copied or ignored config is rejected.
Every configured output is a distinct contained basename with its declared
Parquet or JSON suffix; path traversal and output aliasing are invalid.

## Question

Does the complete finite V1 point-cap census have a numerically unique primary
LP allocation at every evaluated cap once nonbasic row/slack variables are
audited together with structural columns? At each period-specific basis
breakpoint, do independent solver paths seeded at the registered left/right
midpoints and then reoptimized at the exact cap return the same allocation? If
a complete-basis reduced cost is near zero, does the corresponding standard
variable move over the declared primary-objective face?

The audit may support or block the finite-support exactness interpretation. It
cannot select a cap, comparator, allocation, endpoint, or outcome direction.
The equal-quarter follow-up analysis remains non-primary replay provenance for
the manuscript and is not an input to V2; V2 neither reads its outcomes nor
uses its result to choose a numerical trigger.

## Immutable inputs

V2 hash-verifies:

1. the complete V1 deterministic summary and the nested census descriptor it
   consumes;
2. the V1 `point_cap_basis_diagnostics.parquet` census;
3. the V4 V1 outcome-free allocation freeze;
4. the exact V4 config descriptor nested in that freeze, before reading its
   budget, purpose-cap, or LGD values;
5. the frozen CatBoost/Platt scores and design roles referenced by that freeze;
6. the raw archive hash, reading only `id`, `loan_amnt`, `int_rate`, and
   `purpose`;
7. every scientific implementation file recorded in the V2 implementation
   provenance.

The verified V4 freeze must expose both
`outcome_free_funded_allocations.parquet` and
`outcome_free_solve_records.parquet`. V2 reads only outcome-free allocation,
score, contractual-rate, ID, cap, role, and comparator fields from them.

The V1 census must contain exactly 7,297 unique `(period, point_cap)` rows in 15
primary months, including all 2,952 rows marked
`period_basis_breakpoint`. Before any solve, V2 also requires finite
`expected_objective`, `weighted_point_score`, `basis_cap_lower`, and
`basis_cap_upper` values plus complete Boolean breakpoint and development-
support endpoint flags in every period. No cap is added, removed, or selected.

Config loading also fails before computation unless schema version
`2026-07-21.1` and a nonempty locked hypothesis are present.

Column names containing `status`, `outcome`, `default`, `pymnt`, `realized`, or
`miscoverage` are forbidden. Outcomes are never loaded or joined. The runner
must report empty outcome, protected-stage, and protected-artifact lists.

## Full-basis certificate

For every one of the 7,297 cap-months, solve the original one-thread point-PD
LP with its exact budget, purpose constraints, coherent plug-in objective, and
risk-cap right-hand side. Record:

- all column and row basis-status counts, with `kBasic`, `kLower`, `kUpper`,
  `kZero`, and `kNonbasic` persisted separately;
- a period/column registry plus exhaustive structural-column status counts,
  `col_dual` extrema, scale-aware warning entities, and cryptographic hashes of
  every full status/value/dual array;
- row values, bounds, statuses, `row_dual` values, signs, near-zero counts, and
  a hash of the full row status/value/dual arrays;
- every row/slack detail because the row count is small;
- every nonbasic column or movable row/slack satisfying the locked scale-aware
  numerical trigger described below;
- primal degeneracy, raw-HiGHS objective reconciliation, budget reconciliation,
  risk-cap and purpose-cap violations, raw bound violations, and unsupported
  basis statuses.

Let the common structural-column reference scale be
`s_c = max_j(abs(c_j))`. The trigger is

`abs(col_dual_j) / s_c <= 1e-7 + 1e-12`,

equivalently `abs(col_dual_j) <= s_c * (1e-7 + 1e-12)`.

For row `i`, let `s_i = max_j(abs(c_j)) / max_j(abs(A_ij))`. A standard
row/slack variable is warned when
`abs(row_dual_i) / s_i <= 1e-7 + 1e-12`. This has the same
objective-per-row-activity units as `row_dual` and is invariant to rescaling the
entire objective. Zero objective or all-zero rows are invalid contracts. These
thresholds are locked before execution and are applied exhaustively; outcomes
and observed allocation discrepancies cannot open a conditional range. HiGHS
dual and primal feasibility tolerances are both fixed at `1e-9` and persisted
in the solver contract.

Under the HiGHS maximization convention, a nonbasic column at its lower bound
must have reduced cost no greater than zero and one at its upper bound no less
than zero. A nonbasic row at its lower bound must have `row_dual <= 0`; a
nonbasic row at its upper bound must have `row_dual >= 0`. The exact-budget
equality is fully recorded but excluded from the movable-slack warning because
it has no slack direction.

Basis validity, basis dimension, supported nonbasic statuses, raw feasibility,
and correctly signed reduced costs outside their registered near-zero bands are
all required for the strict numerical certificate. Primal degeneracy alone is
not evidence of an alternative allocation.

The sufficiency argument is the standard-form LP argument. Transform a bounded
structural variable at its upper bound to its nonnegative complement and expose
every movable one-sided row as its nonnegative slack/activity variable. Relative
to one valid optimal basis, every different feasible primal point requires a
positive move in at least one nonbasic standard variable. If every such lower-
bound variable has strictly negative reduced cost and every upper-bound variable
has strictly positive reduced cost under the HiGHS maximization convention,
then every different feasible point has strictly smaller primary objective.
Thus exhaustive full-basis strict signs are sufficient for primal uniqueness;
they are not necessary. V2 applies this argument only numerically outside the
registered scale-aware bands. Any near-zero sign blocks the sufficiency route
and opens only its registered conditional diagnostic, never symbolic exactness.

## Frozen-allocation bridge

The reconstructed V2 LP is not silently equated with historical endpoints. V2
maps the hash-verified V4 allocation vectors to every V1 census key using
within-period nearest-cap matching at tolerance `1e-10`. The deterministic
source priority is `point_cap_frontier`, C0, C1, then C2. The V4 artifact
historically named `exact-frontier` provides each month with the global union
of its solver-reported basis-ranging endpoints,
while the named comparators provide additional V1 caps. Frozen files contain
positive exposures only; absent menu IDs are reconstructed as zero exposure.

Coverage must be exactly 7,297/7,297. A frozen source representation is keyed
by period, window, solve candidate ID, comparator rule, policy label,
paired-policy ID, and source cap. Every mapped solve-record source must have one
positive-exposure vector, with no repeated candidate ID. When several source
representations map to the same `(period, cap)`, candidate IDs absent from a
source enter its comparison as zero exposure. The complete-vector exposure
spread must not exceed USD `1e-7` and the available point/objective coefficient
spread must not exceed `1e-12`.
Deterministic priority selects one complete source vector; it must never splice
candidate rows from different sources. For every central V2 solve, persist and
gate:

- L1 exposure difference in dollars and symmetrically normalized by fresh plus
  frozen committed capital (`2e-4` dollars and `1e-10`, respectively);
- expected-objective difference (USD `1e-5`);
- funded point-score difference (`1e-10`);
- coefficient identity (`1e-12`), budget reconciliation, and reconciliation of
  the frozen vector to the V1 census objective and funded point score.

Failure limits the result to an audit of the reconstructed LP. It cannot be
used to characterize the historical allocation extrema that feed the paper.

## Fresh RHS basis-range coverage

Every fresh central solve persists its own HiGHS RHS-ranging interval
`[fresh_basis_cap_lower, fresh_basis_cap_upper]`. For each month, V2 merges the
fresh intervals at numerical gap tolerance `1e-10`. One connected merged
segment must cover the broad `[0.05,0.12]` support and the complete hull obtained
by adding all V1 development-support endpoints. Every solved cap must lie in its
reported fresh interval.

Both the tolerance-merged gate gap and the raw uncollapsed positive gap are
persisted. A raw gap at or below `1e-10` may pass the registered numerical
coverage gate but must remain visible rather than being reported as exact zero.

V1 lower/upper basis ranges are hash-locked through the census descriptor and
their numerical differences from fresh ranges are reported, but basis identity
is not required when allocations reconcile. The result is only **fresh RHS
basis-range coverage at the registered tolerance**. It is not exact coverage,
allocation continuity, seam conditioning, symbolic exactness, or a uniqueness
claim for a continuously varying joint policy problem.

## Bilateral midpoint-to-cap path stresses

Every one of the 2,952 V1 basis breakpoints receives a path stress from each
available side. For sorted V1 breakpoints in one month, the left seed is the
midpoint to the preceding breakpoint and the right seed is the midpoint to the
following breakpoint. Fresh and V1 basis identities are not required; therefore
a midpoint is not claimed to lie in the immediately adjacent fresh basis region.
The 5,874 registered paths are not an exhaustive enumeration of lateral fresh
bases or seams. The central path is isolated by month. Every
individual lateral breakpoint-side pair uses a fresh HiGHS session, independent
of the central path, the opposite side, and every prior breakpoint. Each pair
follows only:

1. solve at the midpoint seed;
2. change only the risk-cap right-hand side to the exact breakpoint;
3. solve again from the side-seeded basis;
4. run the complete column-plus-row basis audit at the breakpoint;
5. compare the raw resulting allocation, objective, and funded point score for
   all available pairs: central-left, central-right, and left-right.

The two outer support endpoints per month have only their available inward
path stress. The locked expected path count is therefore 5,874. Basis hashes may
differ when allocations coincide; that is multiple basis representation, not
an alternative primal allocation.

All solvers use HiGHS 1.15.1 (native version 1.15.1, githash `04024d7`), simplex,
presolve on, one thread, dual and primal feasibility tolerances `1e-9`,
deterministic input order, and scheduler reset where available. Highspy 1.15.1
does not expose `zeroAllClocks()` on every build, so its absence does not block
execution. Fresh lateral and secondary sessions prevent a cumulative time limit
across probes; the central session is scoped to one month. `getRunTime()` is
persisted for every central/probe path and for both secondary min/max solves.
Any version or option drift blocks execution.

## Conditional optimal-face ranges

The optimal-face stage is forbidden unless a central or side-seeded basis has
a nonbasic structural column or movable row/slack that satisfies its
predeclared absolute-plus-relative threshold. Only the union of those warned
standard variables is examined; allocation discrepancies, outcomes, and
empirical results cannot trigger an otherwise unregistered solve.

For one warned cap, let `z*` be the raw objective returned by HiGHS, not the
objective recomputed from clipped allocation fractions. The raw objective and
the portfolio solution must reconcile within the reported `epsilon_z`. Add the
reported numerical face lock

`c'x >= z* - epsilon_z`,

where `epsilon_z` is the maximum of the locked absolute and relative objective
tolerances. The implementation may also impose the redundant numerical upper
band `c'x <= z* + epsilon_z`. For each warned variable:

- a structural column is minimized and maximized directly;
- a warned row/slack is tested by minimizing and maximizing its row activity;
- every secondary solve reports its attained primary objective, the exact
  `epsilon_z` used, its independent `getRunTime()`, and raw column/row bound
  violations;
- secondary values are never clipped or silently repaired.

Every range must satisfy `minimum <= base <= maximum` within `1e-9`. The raw
signed range and each consistency violation are retained. A tiny negative range
is floored to zero only for the mobility magnitude, never hidden; any violation
above the registered tolerance gates the numerical certificate.

Finite objective-reconciliation and raw primal-bound violations are persisted
and claim-gated, not raised after an otherwise optimal finite solve. Model
rejection, nonoptimal status, invalid/nonfinite values, or shape errors remain
technical stops. Final immutable output directories are created only after all
solves, complete-census checks, summary gates, and implementation-drift checks
finish, so a technical stop does not consume the registered run path. Their
nonexistence and containment are also preflighted before scientific computation
and checked again at creation.

If every warned standard variable remains fixed, V2 reports only that no
**individual registered coordinate** moved beyond the declared epsilon and
resolution. Coordinatewise ranges do not bound the global L1 diameter of the
face: many subthreshold changes or an ill-conditioned pivot can still produce
material joint movement. Therefore any registered warning keeps the global
finite-grid numerical-uniqueness gate closed unless a future protocol directly
bounds the global face diameter. If any warned variable moves beyond the locked
normalized mobility tolerance, V2 reports **epsilon-near-optimal mobility**.
Because the lock admits `z* - epsilon_z`, positive mobility is not by itself
proof of a distinct exact optimum. V2 makes no symbolic exact-face or global
diameter claim and cannot choose a tie-break. A deterministic tie-break, direct
global-diameter program, or outcome-robust envelope over an optimal face
requires a new protocol.

## Complete outputs

V2 writes, without filtering:

1. one central diagnostic row for every 7,297 cap-month;
2. one frozen-allocation reconciliation row for every 7,297 cap-month and one
   fresh RHS basis-range coverage row for every 15 periods;
3. one stable period/column registry; full column-array hashes and aggregates
   on all 13,171 audited bases; and every scale-aware column warning entity;
4. complete row/slack details for every central and side-seeded audited basis;
5. one diagnostic row for every 5,874 bilateral midpoint-to-cap path stress;
6. one all-pair comparison row for every 2,952 breakpoint;
7. every warned nonbasic variable from every solve origin;
8. every conditional min/max epsilon-near-optimal range, or an empty table with the
   declared schema if no warning occurs;
9. one deterministic JSON summary, protocol freeze, and execution receipt.

No favorable subset may be promoted. A scientific stop is retained in the
summary rather than deleting completed diagnostics.

## Stop and claim-gate rules

Execution stops immediately on input-hash mismatch, dirty or untagged HEAD,
outcome-like input, duplicate or missing IDs, cap-census drift, an incomplete
central solve, an incomplete breakpoint/probe census, nonoptimal solve,
nonfinite output, implementation drift during execution, or artifact overwrite.
Unsupported statuses are retained and gate the certificate rather than being
filtered from a completed audit.

The strict numerical-certificate gate fails, while complete results remain reportable, if:

- any scaled column or row dual sign violation exceeds `1e-9`;
- any basis is invalid, has the wrong dimension, or has an unsupported nonbasic
  structural-column or movable-row status;
- any objective reconciliation error exceeds USD `1e-5`;
- any normalized budget, risk-cap, or purpose-cap violation exceeds `1e-8`, or
  any raw LP bound violation exceeds the fixed HiGHS primal tolerance;
- frozen-vector coverage is not 7,297/7,297, any frozen duplicate contract
  fails, or any fresh-to-frozen allocation/objective/point reconciliation
  exceeds its registered tolerance;
- fresh monthly RHS basis-range coverage has a gap above `1e-10`, fails to cover
  `[0.05,0.12]` plus the development-support hull, or fails cap containment;
- lateral allocations differ above `1e-10` without conditional epsilon-near-
  optimal mobility at the same `(period, cap)`. When both occur, V2 records only
  `allocation_difference_cooccurs_with_same_cap_epsilon_mobility`; it does not
  claim that any coordinate range reaches, explains, or reconciles the lateral
  allocation distance;
- any pairwise lateral objective difference exceeds USD `1e-5`, or any funded
  point-score difference exceeds `1e-10`;
- a secondary solve leaves the reported primary-objective band;
- a conditional range violates `minimum <= base <= maximum` beyond `1e-9`;
- any warned standard variable has epsilon-near-optimal normalized range above
  `1e-10`.

Even if all individual warned ranges remain below `1e-10`, the finite-grid
numerical-uniqueness gate remains closed because V2 has no global L1 face-
diameter bound. The gate can pass only when every numerical contract passes and
the complete registered central and midpoint-path full-basis audit produces no
warning. It also requires complete frozen-vector reconciliation and fresh RHS
basis-range coverage at the registered tolerance.

Possible final statuses are:

- `strict_full_basis_freeze_and_fresh_rhs_range_coverage_numeric_certificate`;
- `registered_warnings_without_global_face_diameter_claim_inconclusive`;
- `epsilon_near_optimal_mobility_detected_claim_blocked`; or
- `numerical_contract_failed_claim_blocked`.

These statuses concern the reconstructed LP, its verified reproduction of the
frozen V4 allocations, and fresh RHS basis-range coverage at the declared
tolerance. They do not authorize exact coverage, allocation continuity, seam
conditioning, exhaustive fresh lateral-basis enumeration, symbolic exactness,
continuously varying joint-policy uniqueness, comparator universality, policy
selection, historical extrema claims after a failed bridge, or any empirical
outcome claim.

The summary reports the fresh-RHS coverage gate separately from the composite
certificate. An unrelated basis warning or frozen-vector failure can close the
composite certificate while leaving the standalone RHS-coverage gate true; an
RHS coverage failure closes both.
