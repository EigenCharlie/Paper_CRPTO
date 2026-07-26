# IJDS set-preserving embedding sensitivity V1 protocol (2026-07-26)

## Status and question

This document predeclares a clean candidate experiment. It supports no active
claim until the protocol and implementation are committed, the commit is tagged
as declared in the configuration, and each phase completes from its own clean,
committed, tagged authority. Phase B requires a later hash-pinned evaluation
configuration and cannot run under the V1 tag.
It does not replace or amend any active artifact.

The binary conformal set used by the paper is the intersection of an interval
`[l_i,u_i]` with `{0,1}`. The portfolio layer nevertheless consumes the numeric
upper endpoint `u_i`. Binary-set membership does not identify a unique numeric
embedding. This experiment asks whether the reported policy response is robust
over a complete evaluation of one prespecified, outcome-free five-point
contraction path whose alternative upper endpoints leave every loan's binary
prediction set exactly unchanged. It does not exhaust all set-preserving maps.

## Locked source and scope

- The decision universe, primary CatBoost score, five-group score-Mondrian
  recipes, roles, months, budget, purpose cap, LGD, and score construction are
  inherited without refitting from the hash-verified V4/V1 parent named in the
  configuration.
- CatBoost with five taxonomy groups is the only portfolio input. This is not a
  model comparison and no learner is selected using OOT outcomes.
- After the inherited loader removes its numeric-logistic control, Phase A
  requires the exact seven-column decision schema and rejects every residual or
  unexpected learner column; only `pd_point` survives as a model score.
- Both roles are solved completely: 11 policy-development months and 15
  primary-OOT months, for each of eight calibration windows.
- Outcomes are unavailable to Phase A. Phase B evaluates primary OOT only, and
  may start only after verifying the Phase-A freeze and every artifact hash.
- Git authority resolves only explicit `refs/tags/<tag>^{commit}` refs; revision
  expressions, branches, raw commits, and pseudo-options are forbidden. The
  parent commit must be an ancestor of V1 and V1 an ancestor of V2. Parent
  configuration and implementation descriptors are reconciled to their tagged
  Git blobs before Phase A.
- No gamma, theta, ruler, coordinate, window, policy, direction, or result may
  be selected or omitted after inspection.

## Set-preserving family

For point score `p_i`, original interval `[l_i,u_i]`, and
`theta in {0,.25,.5,.75,1}`, define

```text
u_i(theta) = 1                                      if 1 is in S_i,
             (1-theta) u_i + theta p_i              otherwise,
S_i          = [l_i,u_i] intersect {0,1}.
```

The lower endpoint remains `l_i`. Because `1 in S_i` exactly when `u_i=1`, this
construction must verify loan by loan

```text
0 <= l_i <= p_i <= u_i(theta) <= u_i < 1     when 1 is not in S_i,
u_i(theta) = u_i = 1                         when 1 is in S_i,
([l_i,u_i(theta)] intersect {0,1}) = S_i      in every case.
```

No tolerance is used to redefine set membership. Exact endpoint membership is
checked after validating finite probabilities on `[0,1]`. `theta=0` must recover
the original upper endpoint exactly. The construction is outcome-free.

For each `gamma in {0,.25,.5,.75,1}`, the optimization score is

```text
q_i(theta,gamma) = p_i + gamma (u_i(theta)-p_i).
```

Consequently all five theta policies at `gamma=0` have the exact same score
vector. Their theta-minus-zero contrasts are a prespecified negative control
and must be exactly zero up to the declared numerical tolerances.

## Two rulers and common comparison coordinates

The coordinate grid is `{.25,.5,.75}` and both rulers are co-primary diagnostic
surfaces; neither is selected.

For a fixed role, month, window, theta, and gamma, let `m_s` be the minimum
funded score, `z_s` the plug-in objective attained by an efficient minimum-score
portfolio, `o_s` the score of the common unconstrained plug-in-objective optimum,
and `z_star` that common optimum.

### Normalized-score ruler

For coordinate `lambda`, maximize the plug-in objective subject to

```text
funded score <= m_s + lambda (o_s-m_s).
```

This ruler is normalized separately for each score and is affine invariant in
that score.

### Objective-matched ruler

Within each role-month-window menu, define one common lower objective over the
entire 25-cell score family,

```text
z_L = max over all theta,gamma of z_s.
```

For coordinate `rho`, minimize the cell's funded score subject to

```text
plug-in objective >= z_L + rho (z_star-z_L).
```

The same absolute opportunity-cost target therefore applies to all 25
theta-by-gamma cells in that role-month-window. A theta-specific `z_L` is
forbidden because it would change the theta estimand.

## Complete census and numerical audits

Phase A contains

- `8 x 26 x 5 x 5 x 3 x 2 = 31,200` frontier solves;
- `8 x 26 x 25 = 5,200` minimum-score endpoints;
- 26 score-independent objective optima, reused across windows only after their
  declared basis and ID-reversal checks;
- `8 x 15 x 25 x 3 x 2 = 18,000` descending-ID replays on every primary cell;
- `8 x 3 x 25 x 3 x 2 = 3,600` independent GLOP checks for the three locked
  primary months.

All cells must be present. A solver failure, nonbinding declared boundary,
budget failure, inadequate score/objective range, ID-order difference, GLOP
disagreement, set-preservation failure, or census mismatch fails closed. The
runner may not silently retry except for the closed minimum-endpoint ladder
`{1e-10,1e-9,1e-8}` declared in this configuration, used only for exact
`Infeasible` or `Unknown` point-LP statuses, or the declared
`Point LP did not fill its budget:` boundary prefix, and never beyond the
`1e-8` cap tolerance. Every applied slack is retained in the endpoint
diagnostics.

## Frozen contrasts and outcome evaluation

Before any outcome column is read, Phase A writes and hashes all allocations,
solve records, embedding diagnostics, numerical audits, and allocation-only
contrast diagnostics. It then writes a freeze receipt binding the configuration,
protocol, runner, new module, every transitive implementation dependency, source
descriptors, environment, and git state.

Phase A stores every strictly positive solver exposure; it does not apply the
reporting tolerance as a support truncation. Loan-wise identities and
policy-wise exposure, weight, and contribution sums must reconcile to the solve
records. It also freezes an order-invariant SHA-256 fingerprint of every exact
`role x period x loan ID` candidate cell, not merely its row count.

The V1 config cannot authorize Phase B. After Phase A, a separate evaluation
config must pin both the V1 configuration and freeze by `path`, `bytes`, and
`sha256`, plus the V1 run tag, protocol tag, and protocol commit; that descriptor
is committed and tagged before any endpoint is opened. V2 must be canonically
identical to V1 except for `schema_version`, `protocol_status`, `protocol_tag`,
`run_tag`, and `source_frontier`. Every shared implementation/dependency byte,
the complete AST import closure, environment, package version, solver variable,
and lockfile hash must remain identical. Phase B verifies the strict V1 tag and
ancestry, the V1 clean-Git attestation, every declared descriptor against its V1
Git blob, and its own V2 config and provenance against V2 Git blobs. Phase A
applies the same tagged-blob check to its own V1 config and provenance. Phase B
also verifies the exact run-directory containment and hashes of all eight Phase-A
artifacts, their schemas, summary, and execution receipt. It revalidates the
complete outcome-free frontier and requires the Phase-B candidate fingerprint
to equal V1 before evaluation. Only then may it reconstruct the explicitly
pinned V5 endpoint observable by 2020-09-30. It evaluates primary OOT
allocations and retains both complete contrast families:

1. `gamma=1 minus gamma=0` within each theta, ruler, and coordinate;
2. each `theta>0 minus theta=0` at each fixed gamma, ruler, and coordinate.

The second family includes `gamma=0` as the exact-zero negative control. Bounds
use a common loan-wise assignment over the funded union. Monthly bounds are
reported directly. Window bounds are recomputed on the pooled 15-month funded
union, so payoff/default/miscoverage numerators are summed before conversion to
rates; monthly rates are never averaged. Unresolved outcomes receive sharp
binary common-outcome assignments. Original binary-set endpoints are used for
miscoverage because the alternative embeddings have been proven to encode the
same set. Exact-zero controls are checked separately at every month and pooled
window; temporal cancellation cannot make a failing monthly control pass.
Direction output separates literal bound geometry (`positive`, `negative`,
`exact_zero`, `contains_zero`) from tolerance-based decisions (`positive`,
`negative`, `within_tolerance`, or
`not_directionally_separated_at_tolerance`). A small nonzero bound is never
called literally zero; every bound that touches or spans zero is labeled
`contains_zero`.

## Estimands and interpretation boundary

This is a finite-archive, finite-grid sensitivity analysis. It identifies how
the deterministic optimization output and sharp retrospective outcome bounds
change across a prespecified class of numerically different but set-equivalent
upper-endpoint embeddings. It does not establish a causal effect, a conformal
guarantee for a selected portfolio, universal monotonicity, a policy winner,
uniqueness of an optimum, or validity outside the frozen archive and grid.

All directions and null results are retained. Windows and months are overlapping
diagnostic scopes, not independent replications. The experiment neither repairs
exchangeability nor authorizes selection from the grid.

## Stop rules

Stop without evaluation if any Phase-A cell or audit is incomplete, any
embedding changes a binary set, any forbidden outcome-like column reaches the
builder, any negative-control allocation contrast exceeds tolerance, or any
output path is occupied. Stop Phase B on a freeze/hash mismatch, outcome census
mismatch, V1/V2 code or environment drift, candidate-ID fingerprint mismatch,
mutated contrast reference or policy label, incomplete contrast family,
nonbinary observed endpoint, invalid sharp-bound ordering, or negative-control
bound exceeding tolerance. Never overwrite an existing run tag; choose a new
protocol and run tag for any repair.
