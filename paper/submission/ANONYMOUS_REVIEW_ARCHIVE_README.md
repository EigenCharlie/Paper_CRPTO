# Anonymous Review Archive Contract

This is the README template for any editor-requested, double-anonymous review
archive. It deliberately contains no author identity, affiliation, repository
owner, public URL, exact Git commit, protocol tag, run tag, DVC fingerprint, or
local path.

## Evidence Layers

- **P1:** code-locked retrospective maturity-safe parent protocol.
- **C1:** separately locked post hoc comparator-stringency audit.

The manuscript reports all scientific quantities needed to interpret P1 and
C1. Exact public-searchable provenance is held by the editor and released after
acceptance, not embedded in this archive.

## Archive Contents

| Path | Purpose |
|---|---|
| `manuscript.pdf` | Official anonymous IJDS manuscript |
| `online_supplement.pdf` | Anonymous proofs, complete diagnostics and limitations |
| `source/` | Sanitized method and evidence-builder source if requested |
| `evidence/P1/` | Opaque parent summaries, tables and figures |
| `evidence/C1/` | Opaque comparator summaries, tables and figures |
| `tests/` | Focused scientific, claim-sync and anonymity tests |
| `environment/` | Dependency lock and platform-neutral setup instructions |
| `ARCHIVE_SHA256.txt` | Checksums generated after sanitization |

## Generic Reproduction

1. Create the locked Python environment from `environment/`.
2. Run the P1 and C1 evidence builders against the supplied immutable inputs.
3. Run the focused scientific, publication-integrity and anonymity tests.
4. Compile the body and supplement without executing analysis code.
5. Compare every archive-local checksum with `ARCHIVE_SHA256.txt`.

The default path rebuilds paper evidence; it does not rerun model selection or
any protected historical pipeline stage. An expensive full replay is supplied
only through an editor-approved verification channel with fresh output paths.

## Sanitization Gate

Before upload, inspect both visible text and PDF metadata. Reject the archive if
it contains any personal name/email, affiliation, repository owner or URL,
local absolute path, credential, remote storage location, exact Git/protocol/run
identifier, or public-searchable DVC/content fingerprint. Remove `.git`, DVC
remote configuration, logs, caches, PDF producer paths, and filesystem
timestamps that reveal identity. Generate archive checksums only after this
sanitization.

The editor-only P1/C1 crosswalk is intentionally absent.
