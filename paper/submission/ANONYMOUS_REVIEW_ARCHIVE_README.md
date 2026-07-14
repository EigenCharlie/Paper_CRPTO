# Anonymous Review Archive Contract

This template describes an editor-requested double-anonymous archive. It must
contain no author identity, affiliation, repository owner, public URL, exact
commit or tag, run identifier, DVC fingerprint, remote coordinate, or local
path.

## Evidence Layers

- **Outcome-free freezes:** learner scores, residual recipes, two-ruler paths,
  comparator supports, exact point frontiers, and every allocation are
  persisted before outcomes are joined.
- **Endpoint-corrected evaluations:** source descriptors and hashes are verified
  before keyed outcome joins. Terminal status is reconstructed as observable by
  the cutoff; 364,814 primary outcomes are resolved and 12,076 remain in sharp
  bounds. The distributed file is not a verified point-in-time snapshot.
- **Complete specification:** all eight residual windows and five coverage
  learners are reported; only the primary learner enters five gammas, two
  rulers, three coordinates, and supporting fixed-cap policies. No result is
  selected.

The archive is a retrospective audit of previously inspected data. It is not a
preregistration, prospective trial, causal study, or selected-set guarantee.

## Archive Contents

| Path | Purpose |
|---|---|
| `manuscript.pdf` | Official anonymous IJDS manuscript |
| `online_supplement.pdf` | Anonymous proofs, full protocol, sensitivities, and limitations |
| `source/` | Sanitized active method, evidence builder, and manuscript source |
| `evidence/outcome_free/` | Opaque models, recipes, panels, and allocations |
| `evidence/evaluation/` | Opaque evaluation, contrasts, simulation, and receipts |
| `tests/` | Scientific, claim-sync, and anonymity tests |
| `environment/` | Dependency lock and setup instructions |
| `ARCHIVE_SHA256.txt` | Archive-local checksums created after sanitization |

## Generic Reproduction

1. Create the environment from `environment/`.
2. Verify the opaque evidence descriptors and archive-local checksums.
3. Run the evidence builder and focused scientific tests.
4. Generate the official TeX from the canonical QMD source.
5. Compile the manuscript and supplement without executing analysis code.
6. Compare generated outputs with `ARCHIVE_SHA256.txt`.

This path rebuilds paper evidence; it does not invoke protected historical
stages or rerun model fitting. A full replay requires an editor-approved
channel and fresh output paths.

## Sanitization Gate

Reject the archive if visible text, PDF metadata, filenames, logs, or hidden
configuration contain a personal name/email, affiliation, repository owner,
local absolute path, credential, remote storage location, exact run/tag/commit,
or public-searchable content fingerprint. Remove `.git`, remote configuration,
caches, build logs, producer paths, and identifying timestamps. Generate archive
checksums only after sanitization.

The editor-only crosswalk is intentionally absent.
