# Editor-Only Reproducibility Crosswalk

**Confidential handling:** do not upload this file as reviewer-facing material.
Its public-searchable identifiers connect the anonymous P1/C1 labels to the
exact immutable evidence chain.

## P1: Maturity-Safe Parent

| Item | Exact value |
|---|---|
| Run | `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2` |
| Protocol tag | `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2` |
| Protocol commit | `78a64fe67a4df46c3d19b9243deb991c56fd1ff6` |
| Summary SHA-256 | `a9c3b3738b26096703fdd2d1b1e852f72b1516157317c65a92e1bb0abdfd693b` |
| Receipt SHA-256 | `7847ba0dc68598de7960c7e78f8a11de527cc7bbf4ddd9f90421bdfa48b68f33` |
| Processed DVC MD5 | `90ecc510414f698f91767f3e507733f0.dir` |
| Model/result DVC MD5 | `fb6220447bb86971c9f41a44f208e885.dir` |
| Evidence manifest | `reports/crpto/ijds_maturity_safe_evidence.json` |

## C1: Comparator-Stringency Audit

| Item | Exact value |
|---|---|
| Run | `champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1` |
| Protocol tag | `protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1` |
| Protocol commit | `ca632ccfbbfaec0e6cdf482a279468665cdb62c0` |
| Summary SHA-256 | `e47d3c74bb0ca262dd097fb13b27ffcd588af4aa62a1f4f2d24ffc495e04c034` |
| Receipt SHA-256 | `869be623ef5e6cc106450ecb49e60ac0dde9ade69a0a7e3f013dd71fa9b10ea8` |
| Processed DVC MD5 | `ce16e806cdf1e97a496d7be722c77835.dir` |
| Model/result DVC MD5 | `4c1cbec15b8d60b40d5f2a05c33c66ab.dir` |
| Evidence manifest | `reports/crpto/ijds_comparator_stringency_evidence.json` |

## Verification Sequence

```powershell
uv sync --extra dev
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1.dvc
just ijds-evidence
just publication-integrity
just validate-champion
```

P1 contains 30 publication outputs and C1 contains 38. The evidence builders
verify source hashes before writing and are byte-idempotent. C1 exactly replays
the two P1 policy allocations it consumes. Neither sequence invokes or writes a
manifest-protected historical stage.

## Release Rule

- During double-anonymous review, provide only P1/C1 labels and the
  metadata-sanitized archive contract.
- If the editor requires exact verification during review, transmit this
  crosswalk through an editor-only channel and ask that it not be forwarded to
  reviewers.
- At acceptance, publish this crosswalk with the repository, DVC pointers, data
  acquisition instructions, and IJDS reproducibility report.
