# IJDS normalized/objective frontier V2 outcome-evaluation results

## Status and lineage

V2 completed from clean commit `d3041e5` under the annotated tag
`protocol/ijds-normalized-objective-frontier-2026-07-13-v2`. Before reading the
archive outcomes, the evaluator verified the exact V1c freeze SHA-256
`7877c5e460772a0093e4132eaa542e9049f7ec15d2ddaa35c2df389892a0e185`,
all six source artifact descriptors, the outcome-free declaration, and the
6,240-solve/622,455-funded-row census.

The verified run took 65.63 seconds and has status
`verified_post_freeze_outcome_evaluation_complete`. It did not refit a model,
recalibrate a recipe, resolve an LP, select a result, run a protected stage, or
write a protected artifact.

An initial shell call returned a client timeout while its child process
continued. A second invocation therefore repeated the fixed evaluation in
memory and stopped at the hard no-overwrite check. Only the first invocation
wrote artifacts. The duplicate invocation changed no specification or output
and is not treated as another replication.

The retained tag records this incident exactly. A post-run hardening change
moved a read-only output-path preflight ahead of archive loading for any future
run tag, while preserving the tagged implementation that produced V2.

## Complete census and outcome join

The retained evaluation contains:

- 6,240 evaluated fixed portfolios;
- 622,455 outcome-joined funded rows;
- 720 monthly endpoint contrasts;
- 48 complete-window endpoint contrasts;
- 144 metric-direction cells; and
- five outcome-census rows.

The outcome panel contains 94,885 policy-development candidates, all resolved,
and 376,890 primary-OOT candidates: 57,497 charged off, 307,842 fully paid, and
11,551 right censored. Every funded ID, role, and issue month aligned exactly.
The 48 complete-window funded unions contain 34--58 unresolved loans. Bounds
use one common loan-wise binary assignment on each policy union.

Every source and output byte count and SHA-256 in the evaluation manifest was
recomputed after the run and matched. Maximum endpoint capital disagreement is
USD `1.34e-6`, below the locked USD `1e-4` reconciliation tolerance.

## Complete endpoint result

Every contrast is `gamma=1 - gamma=0` over all fifteen primary-OOT months. The
eight residual windows overlap and are a complete specification path, not
independent replications or inputs to a vote.

| Ruler | Coordinate | Active months/window | Plug-in objective difference (USD) | Realized payoff bound hull (USD) | Default bound hull (pp) | Miscoverage bound hull (pp) | Complete-window direction |
|---|---:|---:|---:|---:|---:|---:|---|
| normalized score | .25 | 15 | 425,196 to 557,294 | -598,986 to -201,873 | 8.6917 to 13.0148 | 8.5998 to 13.3438 | payoff lower; default and miscoverage higher in 8/8 |
| normalized score | .50 | 15 | 152,031 to 226,848 | -243,218 to -94,767 | 3.6160 to 6.3717 | 2.5016 to 5.0222 | payoff lower; default and miscoverage higher in 8/8 |
| normalized score | .75 | 15 | 28,263 to 51,202 | -132,158 to -31,335 | 1.8273 to 2.3697 | .7329 to 1.6624 | payoff lower; default and miscoverage higher in 8/8 |
| objective matched | .25 | 4 | numerical zero | 5,603.66 to 5,603.66 | -.0068 to -.0068 | -.0068 to -.0068 | payoff higher; default and miscoverage lower in 8/8 |
| objective matched | .50 | 15 | numerical zero | -82,616 to -27,958 | .4572 to 1.0973 | 1.0154 to 1.9321 | payoff lower; default and miscoverage higher in 8/8 |
| objective matched | .75 | 15 | numerical zero | -158,470 to 72,565 | -.2264 to 2.2453 | 1.4326 to 3.9352 | payoff/default cross zero in 7/8; gamma=1 worse in W8; miscoverage higher in 8/8 |

The 48 window cells contain 632 nonidentical monthly endpoint pairs: all 360
normalized-score pairs, 32 objective-matched `.25` pairs, and all 240
objective-matched `.50`/`.75` pairs. The 88 structural monthly zeros at
objective-matched `.25` remain in every complete-window aggregate.

## Interpretation

The normalized-score ruler does not compare portfolios at a common plug-in
objective. It assigns both endpoint models the same relative score coordinate,
under which `gamma=1` receives USD 28,263--557,294 more optimized plug-in
objective, yet has lower bounded realized payoff and higher bounded default in
all 24 cells. This is evidence that a normalized risk coordinate is not an
objective-matched estimand, not evidence that the plug-in objective is causal.

The objective-matched ruler removes that objective-level difference. Its result
still changes with frontier coordinate: a small favorable contrast at `.25`, a
uniformly unfavorable contrast at `.50`, and mostly unidentified payoff/default
at `.75`. Thus the endpoint ordering is neither ruler-invariant nor
coordinate-invariant. Selecting `.25`, `.50`, one ruler, or W8 after seeing the
outcomes would manufacture a winner and is forbidden.

The locked universal-direction condition fails for all three metrics:

- standardized payoff: 8 higher, 33 lower, 7 crossing zero;
- funded default: 8 lower, 33 higher, 7 crossing zero; and
- funded binary miscoverage: 8 lower and 40 higher.

V2 therefore does not activate the separately locked rolling-origin
challenger. It provides no policy winner, causal effect, funded-set conformal
validity, restored candidate coverage, or deployment recommendation.

## Editorial consequence

The strongest defensible result is a decision-identification result inside the
original ML--conformal--optimization handoff: the conformal upper score changes
allocations substantially, but the sign assigned to that change depends on the
outcome-free ruler and on where the common efficient frontier is evaluated.
The experiment preserves CRPTO's three components while falsifying a universal
"more uncertainty aversion is better" or "worse" narrative.

V4 remains the active manuscript until a separate, outcome-aware editorial
decision compares explanatory value, code burden, and overlap. V2 may replace
some comparator machinery or enter as a compact two-ruler falsification; it
must not be appended as an additional winner search.

## Retained artifacts

- data pointer:
  `data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc`;
- model pointer:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2.dvc`;
- summary:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2/normalized_objective_frontier_v2_summary.json`;
- manifest:
  `models/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-13-v2/verified_evaluation_manifest.json`.
