# IJDS normalized-score and objective-matched frontier V1b protocol

## Status and lineage

This outcome-free erratum is locked after the V1 numerical stop and before any
archive outcome join. V1b preserves the V1 research question, family, rulers,
cells, solver contract, promotion rules, and claim boundaries. It changes only
the score-independent objective-optimum uniqueness diagnostic.

The failed protocol, exact stop, and post-stop outcome-free diagnosis are
recorded in:

- `protocol/ijds-normalized-objective-frontier-2026-07-12-v1`;
- `docs/research/ijds_normalized_objective_frontier_protocol_2026-07-12.md`;
- `docs/research/ijds_normalized_objective_frontier_v1_stop_2026-07-13.md`.

V1b is retrospective and is not a pristine preregistration, a conformal repair,
or a submission freeze. V4 remains active until a completed V1b freeze and a
separately locked V2 outcome evaluation pass the declared promotion rules.

## Unchanged research design

The parent remains the hash-verified V4-v1 outcome-free freeze. V1b imports the
same status-independent score universe, eight CatBoost five-group recipes,
four-column raw allowlist, coherent plug-in objective, USD 1 million monthly
budget, and 25% purpose cap.

The complete score path is `gamma={0,.25,.50,.75,1}` over all eight residual
windows, 11 development menus, and 15 OOT menus. The coordinate grid is
`{.25,.50,.75}` for both:

1. the primary common-objective frontier, which minimizes each score at a
   common absolute plug-in objective floor; and
2. the secondary affine-invariant normalized-score frontier.

The V1b freeze still requires exactly 6,240 solve records, 720 primary endpoint
comparisons, 1,440 reversed-ID endpoint reruns, and 288 independent GLOP cells.
The future primary contrast remains `gamma=1 - gamma=0`; no outcome may select
a window, ruler, coordinate, or interior gamma.

## Corrected objective-optimum uniqueness diagnostic

V1 minimized and maximized each gamma score subject to
`v'a >= z* - USD 1e-7`. A nonzero score span under that inequality can represent
the permitted objective deterioration even when the exact optimum is unique.
Its `1e-8` stop therefore did not test exact objective ties.

For each of the 26 distinct monthly menus, V1b now:

1. solves the score-independent plug-in objective optimum once with one-thread
   HiGHS simplex and point cap 1.0;
2. inspects the returned optimal basis;
3. stops if any nonbasic reduced cost has absolute value at or below `1e-7`;
4. reports primal degeneracy but does not equate it with an alternate optimum;
5. resolves the same LP after reversing stable ID order; and
6. stops if normalized exposure distance exceeds `1e-10` or objective drift
   exceeds USD `1e-5`.

For a linear program, an alternate optimum is reachable through an edge with
zero reduced cost. Nonzero nonbasic reduced costs rule out that mechanism for
the returned basis; the order rerun provides a direct allocation-level stress.
The diagnostic is score independent and is therefore neither repeated by gamma
nor by residual window. This is both more faithful to the mathematical object
and less computationally redundant.

Before the V1b tag, this corrected diagnostic was smoke-tested outcome-free on
all 26 distinct menus, without constructing a frontier or reading outcomes.
The minimum absolute and scaled nonbasic reduced costs were respectively
`0.004653265386878047` and `3.6143215598948346e-06`; no menu had a near-zero
reduced cost or primal-degenerate basis. Maximum reversed-ID exposure distance
was `9.09e-19` and maximum objective drift was `1.16e-10` dollars. These values
validate numerical scale only and do not reveal a policy direction.

## Remaining numerical stops

All V1 stops unrelated to the proxy tie diagnostic remain unchanged:

- every normalized score range must exceed `1e-4`;
- every common objective range must exceed USD `1e-4`;
- normalized caps bind within `1e-8`;
- objective floors reconcile in absolute dollars within `1e-5`;
- budget residual stays within USD `1e-6`;
- all primary gamma endpoints are invariant to reversed IDs;
- three declared months reconcile HiGHS and GLOP within `1e-7`; and
- a ruler with zero nonidentical primary endpoint pairs stops before outcomes.

No tolerance may be changed after the V1b tag. A stopped run remains a stopped
run and must receive another transparent erratum rather than an overwritten
artifact.

## Outcome and promotion boundary

V1b cannot read outcomes. A completed freeze only establishes a fixed set of
allocations. V2 must verify every V1b artifact by hash before a single outcome
join and report sharp common-outcome bounds for standardized payoff, funded
default, and funded binary miscoverage.

Any crossing bound or disagreement across rulers, coordinates, or windows
strengthens the comparator-dependence finding. A positive direction can only
advance to a separately locked rolling-origin challenger if the same nonzero
sign holds for all eight windows, all three coordinates, and both rulers. Even
that result would not restore candidate coverage, selected-set validity, or a
conformal portfolio guarantee.
