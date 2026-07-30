# IJDS set-preserving embedding sensitivity V1a stop record (2026-07-29)

This is a reconstructed local stop note first committed with V1c. It preserves
the earlier recorded operational rationale, but it was not committed or tagged
at the time of the V1a stop and is not cryptographic evidence of contemporaneous
authorship or chronology.

## Disposition

V1a is stopped after outcome-free computation and before an artifact commit or
artifact tag. It is quarantine/provenance only and supports no scientific or
paper-facing claim. Its materialized outputs remain intact in the isolated V1a
clone for forensic review; they must not be copied, renamed, promoted, or used
to initialize a successor run.

No Phase-B outcome evaluation was authorized. No semantic result inspection is
recorded or permitted by this stop record. The only observations used to reach
the stop decision were execution exit status, file census, byte/hash
descriptors, protected-path read/write census, and Git/DVC authority state.

## Mechanical reason for stopping

The Phase-A runner completed with exit code zero and produced the predeclared
8 data plus 3 model files. `dvc add` also returned zero and created the two
expected directory pointers. However, `DVC_SITE_CACHE_DIR` had been placed at
`.dvc/site-cache` inside the experiment clone. Immediately before the required
two-pointer artifact commit, full `git status --porcelain=v1` therefore showed
three untracked paths: the data pointer, the model pointer, and
`.dvc/site-cache/`.

The locked V1a protocol permits a direct-child artifact commit containing
exactly the two DVC pointers and forbids overwriting or repairing a run under
the same tag. Deleting, ignoring, staging around, or otherwise concealing the
third path after observing it would create an undeclared post-execution repair.
Accordingly, V1a stopped without staging, committing, or tagging any artifact.

## Successor boundary

Any retry requires a fresh protocol tag, run tag, output directories, and clean
execution. The successor may change only operational DVC-promotion authority;
the scientific grid, estimands, solvers, tolerances, schemas, and no-selection
boundaries must remain byte-equivalent after excluding those administrative
fields. V1a output bytes are not reusable evidence for that successor.

## Later V1c supersession note

The later V1c protocol preserves this record as the earlier documented V1a
decision but explicitly supersedes its operational no-reuse rule after further
inspection established that the eleven completed scientific files were intact
and that the failure occurred only in post-run DVC promotion. V1c is therefore
classified as retrospective and post-inspection, not as the clean successor
envisioned here; V1a remains non-evidence.
