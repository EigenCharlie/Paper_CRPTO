# IJDS marginal mean-score--outcome-gap V3I protocol

**Protocol date:** 2026-07-29

**Run tag:** `ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i`

**Required clean tag:**
`protocol/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i`

**Status:** post-inspection direct-Git recovery, locked before V3I execution.

## Why V3I exists

V3H completed the local scientific calculation and a Git-native artifact seal,
but its separately mandated DVC transport gate failed because the verifier
could not obtain remote credentials. V3H therefore remains non-active evidence.
The failed gate concerned transport, not the estimand or its arithmetic. V3I
replaces that overengineered transport contract with a smaller, inspectable
calculation over exact byte-identified local sources supplied through an
explicit, distinct `--protected-read-root`.

V3I imports no V3H output. It reconstructs the endpoint from the raw archive
and recomputes the five learner rows. Its Git-small CSV and JSON outputs may be
committed directly. No DVC command, DVC remote, protected stage, environment
bootstrap, model fit, recalibration, optimization, or row-level outcome output
is authorized.

This is a recovery after inspection, not preregistration, confirmation, an
untouched holdout, or independent replication. Completion alone does not
promote a paper claim; an explicit downstream evidence and claim-ledger review
is still required.

## V3H results already inspected

Before this protocol was written, V3H had disclosed the complete target census,
the signs, and all five numerical rows:

| Learner | Mean score | Gap lower | Gap upper |
|---|---:|---:|---:|
| CatBoost + Platt | 0.10896781492541122 | -0.07423683364578992 | -0.04219565452190763 |
| Numeric logistic + Platt | 0.12722986345883128 | -0.05597478511236986 | -0.023933605988487566 |
| Monotonic CatBoost + Platt | 0.11483073028912258 | -0.06837391828207856 | -0.036332739158196264 |
| Platform WOE scorecard + Platt | 0.12058983357842160 | -0.06261481499277954 | -0.030573635868897248 |
| Borrower WOE scorecard + Platt | 0.12640229060334635 | -0.056802357967854794 | -0.024761178843972498 |

The inspected outcome-prevalence interval was
`[0.15116346944731884, 0.18320464857120114]`; its width, and every gap
interval's width, was `0.03204117912388230`. All five gap hulls were negative.
Those facts are disclosed to prevent retrospective relabelling. V3I's exact
arithmetic reconciliation to these rows is a lineage-identity gate, not a
scientific selection rule. Sign, magnitude, and learner order may not govern
execution, retention, or model choice. A downstream claim review may promote
the complete five-learner census only as a descriptive post-inspection
finite-archive result; V3I itself selects no learner and supplies no preferred
model.

## Population and frozen scores

The target is the complete status-independent 36-month primary-OOT population
issued from 2016-04 through 2017-06. Membership uses only issue month and term.
The expected census is 376,890 unique loan IDs across all 15 months. The
canonical length-prefixed identifier-set SHA-256 is
`72799b236a7e45d8746099adefba7da5683e8308959643d6ad341d3585e8fa74`.

The five frozen score columns are read from the V1b outcome-free credit-control
freeze. The runner requires its exact eight-column schema (ID, issue date,
design split, and the five scores), the freeze's exact nested score descriptor,
all five learners, no model selection, exhaustive sampling, and an empty list
of primary-OOT outcome columns. It neither selects nor ranks a learner.

## Endpoint reconstruction

The raw archive is scanned in full using only `id`, `issue_d`, `term`,
`loan_status`, and `last_pymnt_d`. Fully Paid becomes available at the
last-payment month-end. Charged Off becomes available six calendar months
after the last-payment month-end. A terminal outcome is resolved only if this
reconstructed availability date is no later than 2020-09-30. `Default` and
all other nonterminal statuses remain unresolved.

The exact expected partition is:

| Endpoint reason | Candidate | Resolved | Unresolved |
|---|---:|---:|---:|
| Charged Off by reconstructed cutoff | 56,972 | 56,972 | 0 |
| Fully Paid by reconstructed cutoff | 307,842 | 307,842 | 0 |
| Nonterminal or unresolved status | 11,551 | 0 | 11,551 |
| Terminal after reconstructed cutoff | 47 | 0 | 47 |
| Terminal availability date missing | 478 | 0 | 478 |

Thus the endpoint contains 364,814 resolved outcomes: 307,842 nondefaults and
56,972 defaults, plus 12,076 unresolved outcomes. The runner also requires the
locked 75-cell month-by-reason census, an exact one-to-one score/outcome join,
zero issue-month mismatches, and endpoint-assignment SHA-256
`04c4d182b1223dc1c92df0898d4cd25e0a44fedded46dc1f52af62ba3d9317b6`.
No row-level reconstructed outcome is persisted.

The distributed archive is not represented as a verified point-in-time
snapshot. These are deterministic reconstructed-availability categories, not
observed operational event dates and not a missingness-mechanism model.

## Estimand and sharp binary completion

For learner (j), with frozen scores (p_{ij}), let

\[
\bar p_j=N^{-1}\sum_i p_{ij}.
\]

Under the unrestricted binary completion class, each unresolved outcome may be
zero or one. If (D_R=56{,}972) and (U=12{,}076), then

\[
\bar Y\in[D_R/N,(D_R+U)/N]
\]

and

\[
\overline{p_j-Y}\in
[\bar p_j-(D_R+U)/N,\;\bar p_j-D_R/N].
\]

Both endpoints are sharp: all unresolved outcomes equal to one jointly attain
the five lower endpoints, and all equal to zero jointly attain the five upper
endpoints. The exact marginal identified set is the finite grid

\[
\{\bar p_j-(D_R+k)/N:k=0,\ldots,U\},
\]

with 12,077 points and step `1/N`; the reported interval is its hull. The exact
joint set is one shared collinear grid, not the Cartesian product of five
marginal intervals.

These are finite-archive deterministic partial-identification bounds. They are
not confidence, prediction, posterior, tolerance, or conformal-validity
intervals. V3I reports no p-value and supports no causal, mechanism, MAR/MNAR,
exchangeability, prospective-validity, funded-set, selected-set, policy,
guardrail, or model-winner claim.

## Source and execution contract

The YAML binds the score table, its outcome-free freeze, raw archive, raw-data
audit evidence, and raw-audit configuration by canonical repository-relative
path, byte count, and SHA-256. `--protected-read-root` must resolve to a
different explicit path from the tagged execution checkout; nesting alone is
not treated as scientific independence because every actual source is
path/byte/hash bound. Every
descriptor is verified before reading and again after computation. The
absolute protected root is never serialized or used as an output location.

The runner must start from a Git-clean HEAD exactly matching the required
protocol tag. It binds the protocol, configuration, calculation module,
endpoint helper, runner, atomic-I/O helpers, and `uv.lock` by Git-small
implementation descriptors. It writes only five aggregate files beneath the
fresh V3I run directories:

1. the five-row marginal-gap CSV;
2. the five-row endpoint-reason CSV;
3. the 75-row month-by-reason CSV;
4. one summary JSON; and
5. one execution-receipt JSON.

Writes are atomic and no existing run directory or target may be overwritten.
Serialized paths are repository-relative. Runtime records omit executable and
protected-root absolute paths. The runner records empty lists for protected
stages run and protected artifacts written.

The required artifact tag is
`artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3i`. After the
runner exits, its five declared outputs are still
`pending_git_artifact_commit`: they must be the complete diff of one artifact
commit whose sole parent is the protocol commit. DVC is neither required nor
authorized. Downstream activation must verify that exact tag, parent relation,
and five-path diff rather than trusting the runner's pre-commit state.

## Fail-closed rules

Stop before output on dirty or incorrectly tagged Git state, unsafe paths,
source descriptor drift, frozen-lineage drift, score schema or census drift,
raw archive census drift, ID or issue-month mismatch, endpoint taxonomy or
month-cell drift, nonfinite/out-of-range scores, reversed or inconsistent
bounds, V3H arithmetic non-reconciliation, implementation drift, pre-existing
outputs, or a source changing during execution. Do not stop, retry, select, or
rewrite because of a sign, learner ordering, or substantive interpretation.
