# IJDS set-preserving embedding sensitivity V1c recovery protocol (2026-07-29)

## Status, chronology, and interpretation boundary

V1c is a **retrospective, post-inspection recovery**, not a clean replay and
not a confirmatory experiment. Before this protocol was locked, the V1a Phase-A
run had finished after about 7.56 wall-clock hours; its eleven output files,
complete frontier census, set-preservation result, numerical diagnostics, and
file hashes had been inspected. V1a itself remains non-active and supports no
paper claim.

The reconstructed local V1a stop note rejected reuse under the same V1a
protocol after its DVC transport step failed. The note was not committed or
tagged at the time of the stop and is not cryptographic evidence of its timing;
the earlier recorded operational decision is nevertheless preserved here.
V1c transparently supersedes it with a new decision: reuse the exact completed
V1a bytes under a new protocol and Git-native transport, then execute only the
already specified Phase B. This change is justified by the verified fact that
the DVC failure occurred after scientific materialization and did not alter the
eleven source files. It must never be described as if V1a had passed its own
transport gate.

V1c may report the complete prespecified grid descriptively. It may not select
a theta, gamma, ruler, coordinate, window, policy, direction, or winner; compute
or imply a p-value; use confirmatory language; repair a conformal guarantee;
claim causality; or promote V1a as evidence. Any later paper-facing use must
retain the retrospective/post-inspection qualifier.

At runtime the runner parses the hash-bound original V1a config Git blob. The
hypothesis, outcomes, normalization, embedding, frontier, solver, contrasts,
metrics, and claim-boundary mappings must equal V1a exactly. The shared expected
census must also be exact; V1c may add only the locked 1,783,274 joined-row
census and fifteen-row outcome audit needed by compact Phase B. Phase-A and
transport-only mappings are explicitly outside this reuse comparison. This is
a computed fail-closed reconciliation, not merely a declarative statement.

## Git-native P -> A -> B authority

Let `P` be the commit named by the annotated V1c protocol tag. Let `A` be the
commit named by the annotated V1c source-artifact tag, and let `B` be the commit
named by the annotated V1c evaluation-artifact tag.

The only valid chain is:

```text
P --single parent/direct child--> A --single parent/direct child--> B
```

`A` adds exactly the eleven repository-relative V1a files enumerated in the
V1c configuration. None may exist at `P`. Every Git blob at `A` and every
materialized worktree file must match its locked byte count and SHA-256. The
runner also requires the original annotated V1a tag object and peeled commit,
the original V1a config and protocol blobs, and the internal identities,
schemas, file descriptors, no-selection fields, protected-read record, and
clean-Git record in the V1a freeze, summary, and receipt to reconcile.

Phase B runs only from a clean worktree at `A`. The implementation contains no
Phase-A execution path. `B` may add exactly the nine compact Phase-B paths in
the configuration, all absent at `A`, and no other path. DVC is neither required
nor invoked. Both artifact tags must be annotated; lightweight tags, merge
commits, extra diff paths, renamed paths, missing paths, and hash mismatches
fail closed. Phase-B files retain
`pending_git_artifact_commit_and_annotated_tag` at runner exit because a runner
cannot truthfully attest a future commit. The separate read-only B verifier
checks that final commit and tag.

The runner hashes all eleven source files and the protected raw archive before
opening outcomes, again after scientific calculation, and again before the
final seal. It also requires tracked Git state to remain unchanged. This is the
declared TOCTOU mitigation on a non-hostile local machine; it is not a defense
against an adversary able to mutate and restore bytes between observations.

## Reused Phase-A scientific object

The reused object is exactly the V1a freeze:

- 31,200 optimal frontier solves and 3,120,241 funded-allocation rows;
- 80 set-preservation diagnostics, 5,200 minimum endpoints, and 26 objective
  optima;
- 18,000 outcome-free allocation contrasts and 18,000 order replays;
- 3,600 independent GLOP checks;
- all five theta values, five gamma values, two rulers, three coordinates,
  eight windows, and both roles;
- zero changed binary sets and the complete 2,880-cell gamma-zero negative
  control.

The runner rereads all eight parquet files, matches their frozen schemas, and
reruns the complete scientific validation before any outcome join. No Phase-A
solver is rerun, no inspected V1a diagnostic chooses a retained Phase-B cell,
and no V1a result changes the predeclared complete grid.

## Phase-B estimands and fixed-capital correction

Phase B joins only the terminal default endpoint reconstructed as observable by
2020-09-30 to the frozen primary OOT allocations. It retains all 18,000 primary
portfolio evaluations, 18,000 monthly sharp contrasts, 1,200 pooled-window
sharp contrasts, 3,600 metric-direction rows, and fifteen outcome-audit rows.

Let `B = USD 1,000,000` be the committed monthly policy budget and let a pooled
window contain `T = 15` months. Both policies in every comparison use the same
denominator:

```text
monthly: N_A = N_B = B
pooled:  N_A = N_B = T B = USD 15,000,000
```

Using policy-specific solver-returned capital as a rate denominator is
forbidden. The implementation records both solver capitals and both locked
normalization capitals; it checks budget residuals, exact equality of the
common denominators, and dollar-payoff-to-rate reconciliation. Gamma-zero
theta contrasts remain a complete fixed-capital negative control.

An unresolved loan appearing under both policies receives one shared binary
completion in its exposure-difference contribution. Bounds may not combine two
independently completed policy marginals; doing so would widen a different,
invalid estimand.

Every applicable decision/audit numeric field must be finite. Missing values
are permitted in the exact ruler-specific not-applicable Phase-A fields and,
in Phase B only, in `snapshot_default` when the locked endpoint is genuinely
unresolved. Every nonmissing endpoint must be a finite numeric binary value
(never a string or boolean) and must agree with its resolution reason; unresolved
values must carry one of the locked unresolved reasons. Objective optima require
`basis_valid=true`; point-basis audit fields must be finite.

## Compact outputs and outcome privacy boundary

The full 1,783,274-row joined allocation table is not written. It is used in
memory, checked against its locked census, and represented by a compact join
identity that records its schema, deterministic sorted content hash, source
allocation hash, endpoint-source descriptor, and outcome census. The remaining
outputs are five parquet tables plus the join identity, summary, receipt, and
manifest. Absolute paths, host names, usernames, branches, remotes, and raw
archive locations outside the repository-relative logical binding are never
serialized.

The raw archive is supplied through an explicit hash-bound
`--protected-read-root` distinct from the execution checkout (nesting is not
claimed to imply filesystem independence); its repository-relative logical
path, bytes, and SHA-256 are recorded. Protected
stages run and protected artifacts written remain empty. No DVC or protected
historical experiment stage is invoked.

## Stop rules

Stop before writing results on any failure of annotated-tag authority, direct
parentage, exact diff/path absence, source or Git-blob hash, V1a internal audit,
frozen schema or complete-frontier validation, runtime binding, raw descriptor,
candidate identity, endpoint alignment, complete output census, fixed-capital
normalization, gamma-zero control, finite-number gate, or source/raw/Git TOCTOU
recheck. Stop on occupied V1c output directories. Retain all predeclared cells;
do not adapt the grid after observing Phase B.
