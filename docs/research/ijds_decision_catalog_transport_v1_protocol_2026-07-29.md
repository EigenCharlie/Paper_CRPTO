# IJDS decision-catalog transport diagnostic V1 protocol (2026-07-29)

## Status and authority

This is a **retrospective, post-inspection diagnostic protocol**. It is not a
preregistration, a prospective conformal guarantee, a policy-selection rule, or
active manuscript evidence. The exact execution tag is
`protocol/ijds-decision-catalog-transport-2026-07-29-v1`; execution is forbidden
unless that tag resolves to the clean current `HEAD`.

V1 reuses only the already frozen V1c outcome-free allocation catalog and its
already completed V5 endpoint join. It must not call a PD, conformal, portfolio
optimization, or exact-bound stage. Protected inputs are supplied through an
explicit `--protected-read-root`, opened read-only, and verified by byte count
and SHA-256. Outputs are fresh, isolated, and atomically written.

The outcome pattern and exploratory values described below were inspected
before this protocol was written. Therefore no nominal probability reported by
V1 is a calibrated discovery p-value and no result can repair temporal
exchangeability or selected/funded-set conformal validity.

## Question

Does the complete, frozen monthly catalog of 240 portfolio policies exhibit a
decision-relevant deterioration from the 11 policy-development months to the
15 primary OOT months, when unresolved labels are retained through exact shared
binary-completion bounds?

The unit is a month-role block. The policy catalog is not searched for a winner:
every policy contributes to a prespecified worst-catalog score.

## Frozen sources

The executable configuration pins five source objects:

1. the V1c protocol freeze;
2. V1c outcome-free funded allocations;
3. the V5 verified evaluation manifest;
4. V5 evaluated portfolios; and
5. V5 joined funded allocations.

The V1c catalog has 622,455 funded allocation rows. The V5 portfolio census has
6,240 rows. The join has 622,455 rows. V1 must reconcile the nested descriptors
in the V1c freeze and V5 manifest to the independently pinned descriptors before
using the data.

The outcome-free artifact must have no outcome or outcome-derived columns. Its
decision fields must reconcile exactly, by a canonical allocation key, to the
same fields in the endpoint-joined artifact. The endpoint join may add outcomes
and derived endpoint quantities; it may not change a frozen decision.

## Complete catalog and block split

For each month the catalog is exactly

\[
  8\ \text{residual windows}\times 2\ \text{rulers}\times
  3\ \text{coordinates}\times 5\ \gamma\text{ values}=240
\]

policies. The policy key is
`(role, period, window_id, frontier_ruler, frontier_coordinate, gamma)`.
Each policy contains unique funded loan IDs and allocates USD 1,000,000 within
USD 0.0001 absolute tolerance. Frozen expected-payoff rates are reconciled at
`1e-12` absolute tolerance and dollar contributions at `1e-8`.

The calibration blocks are all 11 `policy_development` months from 2013-02
through 2013-12. The target blocks are all 15 `primary_oot` months from 2016-04
through 2017-06. Missing, duplicated, or extra cells stop the run.

## Outcome-free geometry gate

Intersect each stored interval with the binary outcome space. Define set type
from exact membership of 0 and 1 after requiring finite endpoints in `[0,1]`
and `lower <= upper`:

- `empty`: contains neither endpoint;
- `{0}`: contains 0 only;
- `{1}`: contains 1 only;
- `{0,1}`: contains both.

The pinned outcome-free census is 13,463 empty rows, 599,371 `{0}` rows,
zero `{1}` rows, and 9,621 `{0,1}` rows. A `{1}` row, an invalid interval, or a
census change stops V1. The absence of `{1}` is not treated as a universal
property of binary conformal prediction; it is a verified property of this
frozen catalog and is the monotonicity condition used below.

## Three decision-relevant metrics

For policy allocations \(a_i\), contractual rate \(r_i\), point PD \(p_i\),
binary default \(Y_i\), LGD \(L=0.45\), and budget \(B=10^6\), define:

\[
S_{\rm payoff}=\left[ B^{-1}\sum_i a_i(r_i+L)(Y_i-p_i)\right]_+,
\]

the positive expected-versus-realized standardized-payoff shortfall;

\[
S_{\rm default}=\left[B^{-1}\sum_i a_i(Y_i-p_i)\right]_+,
\]

the positive funded default-rate gap; and

\[
S_{\rm miss}=\left[B^{-1}\sum_i a_i
  1\{Y_i\notin C_i\}-0.10\right]_+,
\]

the positive funded miscoverage excess above the nominal 0.10 reference.

These are diagnostic losses, not coverage guarantees. The payoff expression is
an algebraic consequence of the frozen coherent payoff
\((1-p)r-pL\) and realized payoff \((1-Y)r-YL\).

For each month and metric, the catalog score is the maximum over all 240 frozen
policies. No maximizing policy is promoted, named a winner, or carried forward.

## Exact shared-completion bounds

Resolved outcomes remain fixed. Every unresolved loan has one shared binary
completion used simultaneously wherever that loan appears in the catalog. All
three policy losses are coordinatewise nondecreasing in unresolved outcomes
when no funded prediction set is `{1}`:

- payoff coefficients are \(a_i(r_i+L)/B\ge0\);
- default coefficients are \(a_i/B\ge0\); and
- miscoverage changes from `miss(0)` to `miss(1)` by 0 for empty/full sets and
  by +1 for `{0}` sets.

Consequently, assigning every unresolved outcome to zero gives the exact joint
lower endpoint and assigning every unresolved outcome to one gives the exact
joint upper endpoint for every policy and for the maximum-over-catalog monthly
score. V1 must verify all coefficient signs and the no-`{1}` condition rather
than merely assume monotonicity. Separate endpoint completions by policy or
metric are forbidden.

## Calibration rank and target classification

For each metric there are \(n=11\) development block scores. At
\(\alpha=0.10\), the declared split-conformal-style rank is

\[
k=\lceil(n+1)(1-\alpha)\rceil=11.
\]

V1 applies rank 11 separately to the lower and upper development block-score
endpoints, producing a bounded reference \([q_L,q_U]\). This construction is a
descriptive temporal reference only: post-inspection design and unverified block
exchangeability preclude a new finite-sample transport guarantee.

Each target month is classified without selecting a policy:

- `definitely_exceeds` if its lower score is greater than \(q_U\);
- `definitely_within` if its upper score is at most \(q_L\); and
- `indeterminate` otherwise.

Exact equality is retained on the within side. V1 also reports comparisons to
the conservative scalar reference \(q_U\).

## Post-inspection complete-separation disclosure

Exploration before this protocol found the following approximate pattern:

| Metric | development \(q_U\) | target lower range |
|---|---:|---:|
| payoff shortfall | 13.913446 pp | 15.354699--31.576904 pp |
| default gap | 20.990112 pp | 21.944625--43.392524 pp |
| miscoverage excess | 20.3775 pp | 21.06--42.2275 pp |

It also found all 15 target lower endpoints above the maximum development upper
endpoint for all three metrics. These values are disclosure, not execution
acceptance criteria. The runner must neither hard-code them nor fail when clean
recomputation differs.

No combinatorial ordering probability is reported. The familiar
(1/{26\choose11}) calculation applies to one prespecified scalar ranking under
hypothetical exchangeability and an exact tie rule; it is not the probability
of the post-inspection intersection of three dependent metric rankings. V1
therefore reports the complete finite-archive ordering only, with no p-value,
familywise-error interpretation, exchangeability claim, or temporal-validity
transfer.

## Outputs and execution stops

Fresh output directories contain:

- `policy_score_bounds.csv` (18,720 rows: 6,240 policies times three metrics);
- `block_score_bounds.csv` (26 blocks times three metrics);
- `calibration_thresholds.csv` (three metrics);
- `target_classification.csv` (15 target blocks times three metrics);
- `decision_catalog_transport_summary.json`; and
- `execution_receipt.json`.

All tabular and JSON outputs are written atomically. The run stops on source hash
or byte drift, nested-manifest mismatch, dirty or incorrectly tagged `HEAD`,
non-fresh output paths, outcome leakage into Phase A, allocation misalignment,
catalog/census/budget failure, invalid probabilities/rates/outcomes, a `{1}` set,
negative monotonic coefficient, incorrect rank, or any output census mismatch.

The predeclared artifact tag is
`artifacts/ijds-decision-catalog-transport-2026-07-29-v1`. The runner must leave
both the summary and execution receipt in `pending_git_artifact_commit` status
and serialize only repository-relative paths in its artifact-transport
contract. It does not commit or tag its own outputs.

Transport requires one artifact commit that is a single direct child of the
protocol commit. The complete diff of that commit must be exactly the six
declared output paths: the four CSV files, summary, and receipt. It must contain
no code, protocol, configuration, source, DVC pointer, or unrelated change.
The artifact tag must resolve exactly to that direct-child commit. These small
outputs use direct Git transport and explicitly set `dvc_required: false`;
running DVC is outside this protocol. Until the relationship, exact diff, and
tag are independently verified, the result remains a pending candidate.

## Interpretation boundary

V1 is a candidate diagnostic for whether the **complete frozen decision catalog**
shows decision loss transport. It activates no selected gamma, ruler,
coordinate, policy, winner, causal effect, universal guardrail direction,
selected-set conformal claim, or submission-freeze claim. It does not authorize
CPP, MCP, CREME, refitting, reoptimization, or manuscript language. Promotion
requires a separate audit of the clean tagged replay and an explicit update to
the active claim registry.
