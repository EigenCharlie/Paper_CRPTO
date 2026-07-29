# Marginal Mean-Score--Outcome-Gap V3H Candidate Status — 2026-07-29

## Decision

**TRANSPORT-BLOCKED CANDIDATE; NOT ACTIVE EVIDENCE.** V3H completed its local
calculation, local artifact verification, and Git-native direct-child seal.
The mandatory verification from a separate clean clone did not pass because
the exact three-target DVC pull exited before materializing any source target.
The remote reported `Unable to locate credentials`.

This is a reproducibility and transport failure, not a refutation of the local
arithmetic. It nevertheless fails the preregistered promotion gate. V3H may
support no manuscript number, active claim, Table S2B, evidence-manifest entry,
claim-ledger entry, or machine-readable-supplement file.

## Frozen identity

- Protocol tag:
  `protocol/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3h`
- Protocol commit: `1e608bcc4006766e5c65f4bd56d2ca1cdb704a48`
- Artifact tag:
  `artifacts/ijds-marginal-mean-score-outcome-gap-2026-07-29-v3h`
- Artifact commit: `359562e79c952b9cb27a0ecd5d8f20c0ad8095fb`
- Artifact parent: `1e608bcc4006766e5c65f4bd56d2ca1cdb704a48`
- The artifact commit is the direct child of the protocol commit and adds
  exactly the six aggregate paths declared in
  `configs/crpto_publication_targets.yaml`.

The six outputs contain aggregate tables and receipts only. They remain under
the annotated artifact tag, not in the current `main` tree; the tag preserves
the candidate's exact provenance without turning failed lineage into current
architecture.

## Checks that passed

- The local computation completed under the tagged protocol.
- The local artifact verifier recomputed the source-bound results and passed.
- The protocol and artifact tag identities, direct-parent relation, and exact
  six-path artifact diff were independently checked.
- The separate clean clone resolved the exact artifact tag and verified its
  parent relation before attempting data transport.
- The clean-clone seven-RECORD Python environment materialization passed with
  4,093 files and 164,741,477 bytes.

These checks establish the identity of the candidate and the consistency of
its local artifact. They do not replace the failed source-transport gate.

## Gate that failed

- Exact DVC targets requested: 3.
- DVC pull exit code: 1.
- Failure class: `missing_dvc_remote_credentials`.
- Targets materialized: 0.
- Sources copied by another route: no.
- Clean-clone artifact recomputation executed: no, because the required DVC
  predecessor failed.
- Clean clone remained Git-clean.
- Sanitized verification-result SHA-256:
  `78fb585068177498663bc80e41b6fd18c337ce878007093a4494d297ccb83a33`.
- Structured transport receipt:
  `ijds_marginal_mean_score_outcome_gap_v3h_transport_receipt_2026-07-29.json`.

The receipt records the independent audit without placing a local path,
credential, or raw transcript in the publication repository. Its evidentiary
limit is explicit: the PowerShell transcript captured the failing DVC exit but
not the child process's credential-error stderr. The observed credential error
therefore classifies the transport blocker but cannot substitute for a passing
transport gate.

## Executable boundary

```yaml
active_promotion_allowed: false
active_paper_evidence_allowed: false
active_claim_support_allowed: false
machine_readable_supplement_allowed: false
clean_clone_verify_artifact_executed: false
```

The active evidence registry, active claim ledger, paper-facing evidence JSON,
main manuscript, supplement, and reviewer ZIP must remain V3H-free while this
status holds.

## Only valid next steps

1. Provision authorized read credentials for the existing DVC remote and start
   from a new clean clone.
2. Resolve the same tags and commits, materialize the same locked environment,
   pull exactly the three declared DVC targets, and run the existing V3H
   artifact verifier in that order.
3. Promote only if every gate passes and a sanitized promotion receipt is
   committed under a new review decision.

The failed clone must not be reused. If the transport mechanism, inputs,
receipt schema, computation, or protocol must change, create and freeze V3I;
do not relax V3H retroactively.
