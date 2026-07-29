# IJDS set-preserving embedding sensitivity V1a protocol (2026-07-29)

## Status and precedence

This is a pre-result repair of the stopped V1 candidate. The historical tag
`protocol/ijds-set-preserving-embedding-sensitivity-2026-07-26-v1` produced no
scientific output and remains provenance only. V1 must not be executed or
promoted because its sharp-rate builder implicitly normalized each policy by
the capital returned by that policy's solve. That behavior disagreed with the
fixed-capital estimand and could affect a direction classification at the same
scale as the declared numerical tolerance.

Except for the corrections and stronger transport authority below, the complete
grid, estimands, no-selection boundaries, solvers, rulers, outcomes, and stop
rules in
`ijds_set_preserving_embedding_sensitivity_v1_protocol_2026-07-26.md` remain
locked. V1a supports no active claim until both phases finish from their own
clean tagged authorities and a clean-clone DVC transport replay passes.

## Corrected common-capital estimand

Let `B` be the committed parent-policy budget and let a pooled scope contain
`T` primary months. For every policy pair, rates use identical denominators:

```text
monthly normalization:  N_A = N_B = B
pooled normalization:   N_A = N_B = T B
```

The runner may not substitute either policy's solver-returned invested capital
for these denominators. Dollar payoff contrasts remain loan-wise exposure
contrasts. With the common denominator, every payoff-rate bound must reconcile
exactly to its corresponding dollar-payoff bound divided by `B` or `T B`.
Default and binary-miscoverage contrasts use exposure divided by that same
common capital.

Each output row records the rule, period count, committed per-period budget,
both invested-capital totals, and both normalization capitals. Monthly invested
capital must reconcile to `B` within the declared solver budget residual; pooled
capital must reconcile to `T B` within `T` times that residual. Any mismatch,
unequal policy normalizer, or rate/dollar reconciliation failure stops the run.

V1a locks `B = USD 1,000,000`, inherited from the hash-pinned V4 parent. The
pooled primary window contains 15 months, so its common normalizer is
`USD 15,000,000`. This is a correction of implementation to the already stated
fixed-capital estimand, not a post-result change: V1 produced no outputs.

## Protected-read provenance

The protected archive
`data/raw/Loan_status_2007-2020Q3.csv` is read but never modified. Its exact
repository-relative path, byte count, and SHA-256 descriptor must appear in the
Phase-A summary, receipt, and freeze and in the Phase-B summary, receipt, and
manifest under `protected_artifacts_read`. Protected stages run and protected
artifacts written remain empty.

Scientific runtime provenance serializes `sys.executable` only as a logical
binding plus byte count and SHA-256, never as an installation-specific absolute
path. Phase A and Phase B still require exact equality of that sanitized runtime
record.

As with any ordinary filesystem audit, hashing before and after a long read does
not constitute a cryptographic defense against an adversary able to mutate and
restore the file between those observations. The pre-read hash, post-build
hashes, clean tagged authority, and protected-read descriptor are the declared
operational TOCTOU mitigation; no stronger hostile-host claim is made.

## Two-phase Git and DVC transport authority

Phase A runs only at the clean annotated protocol tag
`protocol/ijds-set-preserving-embedding-sensitivity-2026-07-29-v1a`. After it
finishes, its data and model run directories are added as two DVC directory
pointers in a new single-parent direct descendant commit. Neither pointer may
exist at the protocol commit; the artifact commit may add exactly those two
paths and nothing else. Each pointer has one directory output whose path equals
the V1a run tag, with exactly eight data files or three model files. That commit
is annotated with a fresh artifact tag. Lightweight tags and merge commits are
invalid authority.

Before Phase B is locked, the committed verifier must run at the clean annotated
artifact tag in a separate clone where both materialized Phase-A paths are
initially absent. It invokes one exact two-pointer DVC pull and stops on a
nonzero return code, tracked-worktree drift, occupied pre-pull output, an
unexpected pointer schema, or any materialized-file mismatch. On success it
writes the unique schema `2026-07-29.2` JSON byte representation: UTF-8 without
BOM, lexicographically sorted keys, compact separators, `allow_nan=False`, and
one terminal LF. It contains no timestamp, branch, remote, host, username, or
absolute path. The executable receives the actual `sys.executable` argument
and invokes DVC as `sys.executable -I -m dvc`, so an untracked or ignored local
module cannot shadow the hash-bound installed distribution;
the privacy-safe receipt serializes that first argument as `{sys.executable}`
and binds the interpreter version/cache tag separately.

The receipt records each annotated tag object's Git object ID and peeled commit,
the single-parent chain and exact two-path diff, exact Git-blob descriptors for
the runner and `uv.lock`, the full Python version and executable byte hash, DVC
`3.67.1`, the installed wheel's `RECORD` hash, and byte/size reconciliation of
every hashed file listed by that `RECORD`,
tracked Git state before and after the pull, exact logical argv/cwd/`shell=false`,
return code plus stdout/stderr byte hashes, and a canonical transcript hash. A
separate `dvc status --json` must be clean after the pull. Each DVC `out.size`
and `nfiles` reconciles to real bytes and file counts. The verifier also
recomputes the DVC 3.67.1 directory MD5 from the real file bytes and exact
`Tree.as_bytes` serialization, while an independent canonical SHA-256 tree
descriptor binds every one of the 8+3 files. The same tree is therefore checked
against its pointer and independently content-described without relying on DVC
private APIs.

This is a deterministic, tamper-evident reconciliation record. It is not an
independent cryptographic proof that a historical subprocess ran: its force
comes from the clean-clone procedure, exact Git/tag/pointer authority, observed
subprocess result, content reconciliation, canonical committed bytes, and the
subsequent Phase-B verifier taken together. A success boolean alone is
explicitly insufficient.

The Phase-B V1b config and canonical receipt are then committed and tagged in
the single-parent direct child of the artifact commit. Its `source_frontier`
pins:

- V1a run, protocol tag, and protocol commit;
- Phase-A artifact tag and artifact commit;
- exact path/bytes/SHA-256 descriptors for both DVC pointers;
- the path/bytes/SHA-256 descriptor of the clean-clone transport receipt;
- exact descriptors for the V1a config and freeze.

The V1b runner fails closed unless the tag chain is
parent -> V1a protocol -> Phase-A artifact -> V1b protocol, both DVC pointer
blobs agree byte-for-byte with the artifact commit, both materialized directories
are occupied, the receipt is committed at the V1b protocol commit in its unique
canonical byte representation, its static authority and 8+3 content descriptors
reconcile exactly, every transcript is internally hash-consistent, the source
config and freeze descriptors resolve locally, and all scientific/runtime bytes
equal V1a. A forged success
boolean without the hash-pinned receipt is insufficient. Phase B receives a
fresh run tag; after completion its data and model directories are also promoted
to two DVC pointers in a single-parent direct descendant. The committed
`verify-phase-b-transport` gate must then run from that clean annotated artifact
tag with both output trees initially absent, invoke exactly one two-pointer pull,
reconcile the exact 6+3 evaluation files, require clean post-pull DVC status, and
write the same canonical receipt schema before any Phase-B result can be
promoted.

## Locked tests and interpretation

Tests must include budgets just below the common cap so that normalization by
solver-returned capital produces a demonstrably different answer from the
locked estimand. They must verify manual monthly and pooled numerators, the
common denominators, payoff dollars-to-rate reconciliation, budget residuals,
and rejection of any config that re-enables solver-capital renormalization.
Every applicable numerical value in the frontier and evaluation audit tables
must be finite before any maximum or tolerance comparison; pandas' skip-NA
reductions cannot authorize a pass. The only permitted missing values are the
exact ruler-specific not-applicable fields: `objective_target` for
`normalized_score`, and `frontier_cap` plus `risk_tolerance` (where present) for
`objective_matched`. The converse entries must be finite, and infinity is never
permitted. Every objective-optimum diagnostic must explicitly retain
`basis_valid=true`, and the underlying point-basis audit stops on an invalid
basis or any non-finite primal, dual, cost, row, or objective value.

All five theta values, five gamma values, both rulers, all three coordinates,
eight windows, both contrast families, common-outcome sharp bounds, gamma-zero
controls, HiGHS checks, and GLOP checks are retained without selection. The
experiment does not select an embedding, ruler, coordinate, gamma, window, or
policy; it does not establish funded-set conformal validity, causality,
universal allocation change, optimal-basis uniqueness, or exhaustiveness over
all set-equivalent numeric embeddings.
