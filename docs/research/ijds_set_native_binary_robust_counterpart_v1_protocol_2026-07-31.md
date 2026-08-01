# IJDS set-native binary robust counterpart V1 protocol (2026-07-31)

## Status, question, and boundary

This is a retrospectively designed, non-confirmatory, two-phase candidate. It
asks a narrower question than the set-preserving embedding sensitivity: what
allocation is obtained when the optimizer receives the binary prediction set
itself through its exact worst-label loss, rather than any continuous interval
endpoint? No outcome may be read in Phase A. Phase B remains blocked until the
complete Phase-A artifact is committed, annotated-tagged, and hash-pinned in a
new evaluation config.

For the primary CatBoost/Platt score, canonical five-bin recipe, all eight
declared calibration windows, default label one, and a binary prediction set
`S_i`, define

```text
r(S_i) = 0  if S_i = {0}
         1  if S_i is empty, {1}, or {0,1}.
```

For nonempty sets this is `max S_i`. The empty-set value is an explicit
fail-closed decision convention, not a conformal theorem and not an estimate of
PD. It prevents an empty set from being treated as safe. The score is determined
only by membership of labels zero and one; no interval magnitude, theta, gamma,
outcome, funded result, or post-hoc choice enters Phase A.

## Frozen finite census

The source universe, eight calibration windows, monthly candidate menus,
objective, USD 1 million exact-budget equality, loan bounds, and 25% purpose
cap are inherited without change from binary-geometry V4. There is no invented
absolute score cap and no new cash option. Each menu is traced under the two
existing outcome-blind rulers (`normalized_score` and `objective_matched`) at
coordinates 0.25, 0.50, and 0.75. The complete Phase-A grid is therefore

```text
8 windows x (11 development + 15 primary months) x 2 rulers x 3 coordinates
= 1,248 cells.
```

The normalized-score ruler interpolates between the minimum feasible funded
mean of `r(S)` and its value at the unconstrained objective optimum. The
objective-matched ruler interpolates between the objective at the minimum-risk
endpoint and the unconstrained objective. These are relative coordinates on the
same source polytope, not a selected risk tolerance. All cells are retained.

## Atomic Phase A and numerical audit

During computation, each cell is written as one self-contained Parquet
checkpoint shard outside the repository, by default under
`%LOCALAPPDATA%/CRPTO/runtime/<run-tag>` or under an explicit external
`--runtime-root`. The runner rejects a runtime root inside the repository,
protected source tree, or official output roots, and never serializes its
absolute location. The
shard contains the funded allocation and repeated scalar cell/audit metadata. A
checkpoint becomes resumable only after an atomic rename; an existing shard is
verified and never overwritten. Runtime shards are deliberately not Git
artifacts and are not Phase-B authority. After all 1,248 distinct checkpoints
and their schemas, identities, and full-budget reconciliations pass, Phase A
materializes exactly four consolidated official Parquet objects: solve records,
funded allocations, set-taxonomy diagnostics, and solver audits. The terminal
manifest hash-binds those four objects. This preserves cell-level progress
without burdening Git or the desktop UI with 1,248 official files.

Every cell has three solver checks:

1. a fresh same-order HiGHS replay must reproduce exposure, objective, and
   weighted set risk within locked tolerances;
2. an ID-reversal HiGHS replay must reproduce objective and weighted set risk;
   its exposure distance is retained because binary scores can create genuine
   optimal-face degeneracy;
3. an independent OR-Tools GLOP solve must reproduce objective rate and weighted
   set risk; its allocation may differ on an optimal face.

The unrestricted objective optimum is audited once per role--month and reused
across the eight windows. Phase A stops on outcome-like input columns, invalid
binary-set membership, an incomplete taxonomy partition, absent score range,
budget failure, same-order nondeterminism, reversal objective/score mismatch,
independent-solver objective/score mismatch, occupied nonmatching shard, source
hash drift, implementation drift, or an incomplete cell census.

## Git-native two-phase authority

The intended chain is:

```text
P1 --direct child--> A1 --direct child--> P2 --direct child--> B1
```

`P1` is the annotated protocol tag. `A1` adds only the four consolidated
Phase-A Parquets plus their manifest, freeze, summary, and receipt, and receives
an annotated artifact tag. `P2` adds a separate evaluation config whose Phase-A
freeze, summary, receipt, manifest, four consolidated objects, and source
artifact tag are exact hash authorities. `B1` may add only the predeclared
Phase-B outputs and receives its own annotated artifact tag. DVC is not invoked.
Phase-B code must reject the committed blocked template before loading the raw
archive or any endpoint column.

Phase B is predeclared to evaluate all 720 primary robust-counterpart cells and
to compare each with the 25 V1d embedding cells having the same window, month,
ruler, and coordinate. That gives 18,000 robust-minus-embedding contrasts, with
loan-wise shared completions and no selected theta, gamma, ruler, coordinate,
window, direction, or policy. The comparison requires exact descriptors for
both the new Phase-A allocation census and the V1d source allocation; it cannot
borrow the already inspected V1d outcome tables.

## Interpretation and stop rules

Passing Phase A would establish only a complete finite-archive allocation
census for one declared set-native robust counterpart. Marginal conformal sets
do not endow their Cartesian product across funded loans with simultaneous or
joint coverage. Consequently, optimizing the worst label inside every marginal
set does not inherit a probabilistic robust-optimization guarantee. The run
would not establish selected-set conformal validity, calibrated individual
risk, distributional robustness, prospective transport, a policy winner, or a
favorable portfolio direction. Empty-set fail-closure is a policy convention.
Differences from V1d must be measured; they cannot be inferred from set geometry
alone.

The blocked Phase-B template supports no outcome claim. No Phase-B command may
run until P2 is a clean tagged HEAD and all exact source descriptors and tag
relations pass before the first outcome read.
