# IJDS policy-support RHS-semantics recovery V3a protocol

## Status and purpose

This implementation-recovery protocol is locked before V3a execution under
`protocol/ijds-policy-support-rhs-semantics-recovery-2026-07-21-v3a`. It is a
retrospective, outcome-free numerical recovery of one failed component of the
immutable V2 optimal-face audit. It neither reruns nor edits V2, and it cannot
select a policy, cap, ruler, outcome direction, or tie break.

The tagged predecessor V3 (`8508a339`) completed all 196 gap-seed solves, then
raised `KeyError: lateral_objective_difference_dollars` when its post-solve
lateral-reporting adapter received an incomplete tolerance mapping. It created
no output directory or artifact. V3a changes no hypothesis, support, seed,
solver, numerical threshold, or scientific gate; it adds the two already-V2-
locked lateral reporting tolerances to the V3a config and an integration test
covering the failed adapter. The V3 tag remains immutable.

V2 solved 7,297 central cap-month LPs, 5,874 bilateral midpoint-to-breakpoint
paths, and eight conditional epsilon-near-optimal coordinate ranges. Its
fresh-RHS gate reported zero of 15 months covered. Inspection against the
official HiGHS 1.15.1 semantics showed that this aggregate failure combines:

1. an incorrect interpretation of ranging for a **basic**, slack upper-bound
   row; and
2. genuine gaps between the fresh basis intervals persisted at the V1 census
   endpoints.

V3a separates and tests those two facts. It also corrects a reporting field that
called seven breakpoint rows allocation-difference cooccurrences even though
none exceeded the registered allocation-distance threshold.

## Locked inputs

The sole result input is the SHA-256-locked V2 deterministic summary at commit
`86fddefdcf4d40a971866b2d9acf1d34f5c3bca2`. V3a verifies every V2 artifact it
uses through the descriptors embedded in that summary:

- 7,297 central full-basis diagnostics;
- all central and lateral row/slack details;
- 5,874 lateral probe diagnostics;
- 2,952 breakpoint comparisons; and
- eight conditional epsilon-near-optimal coordinate ranges.

For the 196 registered gap-seed solves only, V3a reconstructs the exact same
outcome-free monthly decision panels used by V2. It inherits V2's verified V4
score freeze, raw-column allowlist (`id`, amount, contractual rate, purpose),
budget, purpose cap, LGD, candidate ordering, and HiGHS identity. No evaluation
label, payoff, default, coverage, or miscoverage column enters a solve.
Before reconstruction, the V2 config is verified against its descriptor inside
the immutable V2 protocol freeze and is also included in V3a implementation
provenance. V3a requires exact equality of the two raw-column allowlists, then
reapplies its stricter forbidden-token scan to the reconstructed dataframe.

## Why the V2 upper-RHS interpretation was wrong

Write the risk row as

`-infinity <= a(x) <= u`, with `u = c B`.

HiGHS ranging depends on the basis status of the row variable. For a row
nonbasic at its upper bound (`kUpper`), `row_bound_dn/up` are the lower and upper
values to which that active upper RHS may move while the reported basis remains
optimal. Dividing by budget therefore gives a cap interval.

For a `kBasic` row, however, the row bound records describe attainable values
of the **basic row activity/slack**, not an interval that must contain the
currently inactive upper RHS. The official HiGHS test applies the returned
records to different row bounds depending on whether the row is basic or
nonbasic; the implementation obtains row records by flipping and negating the
underlying slack-variable ranging records.

The correct upper-RHS ray for a basic slack row is instead

`[a(x*)/B, 1]`

on the normalized model domain. The proof is elementary. V2 reports zero row
dual for every such row. For any `u' >= a(x*)`, the incumbent remains primal
feasible. Because the row multiplier is zero, the same dual certificate retains
the same bound objective. Primal and dual feasibility therefore preserve
optimality. For fresh V3a solves, V3a persists the raw HiGHS pair as an activity
range but never calls it an RHS range in this regime. The central V2 source
contains only its already domain-clipped reported pair, which V3a labels as such.

Any `kLower`, `kZero`, or generic `kNonbasic` status for this upper-only risk row
is an execution stop. V3a also stops if a basic row has a nonzero multiplier, if
activity exceeds its stated cap, or if an active-row range fails to contain its
solved cap.

## Deterministic central correction

V3a joins each central V2 diagnostic to exactly one central `point_risk_cap` row.
The locked input census is 7,228 `upper` rows and 69 `basic` rows. It computes
and persists, without overwriting V2:

- the V2-reported, `[0,1]` domain-clipped down/up records (not the original raw
  HiGHS pair);
- row activity, upper bound, slack, multiplier, and basis status;
- the status-aware effective RHS interval;
- raw and corrected cap-containment indicators; and
- a semantic mode distinguishing active-bound ranging from a basic-row ray.

The expected input fact that 66 V2-reported domain-clipped pairs fail cap
containment is an integrity check, not a desired result. All 7,297 status-aware
intervals must contain their own solved caps.

## Locked gap census and replay

After clipping the corrected intervals to `[0.05, 0.12]`, V3a merges them at
absolute cap tolerance `1e-10`. The positive connected components left uncovered
form the immutable gap census. Pre-execution inspection found 196 such gaps.

For each gap, V3a computes its midpoint and requires a unique V2 probe
`seed_cap` in the same month within `1e-12`. The exact registered seed must lie
strictly inside the target gap. This gives 196 nonselective, outcome-free solves.
V3a performs exactly one registered pass; if any final gap remains, it reports a
scientific failure and does not add a favorable adaptive solve.

Each seed is solved in a new HiGHS session. V3a persists its raw and status-aware
range, solver runtime, objective and funded point score, complete structural-
column and row/slack basis audit, all row details, and every scale-aware warning.
It requires an optimal finite solution, valid supported basis, correct dual
signs, objective reconciliation, and policy feasibility. Every seed interval
must contain its seed and cover the gap it was assigned. The union of central
and gap-seed intervals must be one connected cover of `[0.05, 0.12]` in each of
15 months, with no positive gap above `1e-10`.

This is numerical fresh-basis interval coverage of one locked support. It is not
symbolic exactness, a proof that no unobserved alternative basis exists, seam
conditioning, allocation continuity, or uniqueness of a continuously varying
joint policy problem.

## Full-basis warnings and epsilon mobility

V2's 13 warning rows collapse to eight cap-variable targets in seven
cap-months, four loans, and three months. Their reduced costs are strictly
signed, but fall inside the predeclared scale-aware warning band. V2's secondary
programs allow an objective band of approximately `1e-12` times the primary
objective. The resulting largest individual exposure movement is below USD 1
on a USD 1 million budget.

Consequently, positive movement is **epsilon-near-optimal conditioning**, not
evidence of an exactly distinct optimum. V3a does not rerun or relabel those
programs, does not sum coordinate ranges, and does not infer a global L1
diameter. Any existing or new scale-aware warning keeps a numerical uniqueness
promotion closed but does not, by itself, invalidate RHS interval coverage.

## Corrected lateral reporting

For each V2 breakpoint, define:

`allocation_differs = maximum_pairwise_allocation_distance > 1e-10`.

The corrected cooccurrence field is

`allocation_differs AND same_cap_epsilon_mobility`.

V2 used only the second operand when populating the cooccurrence label. Its
scientific gate for differences *without* mobility remained correct, but the
reported count did not. V3a writes a corrected comparison table while retaining
every original V2 field and value.

## Gates and permissible conclusion

V3a has separate gates for:

1. status-aware solved-cap containment;
2. complete registered seed census and seed-to-gap matching;
3. numerical validity of all 196 gap-seed bases;
4. connected fresh-RHS coverage of `[0.05, 0.12]`; and
5. absence of scale-aware warnings for any possible numerical-uniqueness
   promotion.

Passing gates 1--4 permits only: *the locked fresh HiGHS basis intervals
numerically cover the registered support at tolerance `1e-10` after correcting
basic-row semantics and replaying every registered gap midpoint*. Gate 5 is
reported separately. Regardless of its value, V3a forbids claims of exact
optimal-face uniqueness, global face diameter, continuous joint-frontier
uniqueness, policy selection, empirical outcome direction, causal benefit, or
selected/funded-set conformal validity.

## Immutable outputs

V3a writes six complete parquet tables plus a deterministic summary, protocol
freeze, and execution receipt under a new run tag. Output paths are created only
after input, solver, census, solve, gate, and implementation-drift checks pass.
The V2 directories and summary remain byte-identical.
