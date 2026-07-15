# EXTRACTION_MANIFEST — human summary

`EXTRACTION_MANIFEST.json` is a machine-readable record of how this
standalone repository was extracted from an internal research workspace. This
Markdown file is the human-readable
companion: it explains what the manifest contains, why each section
exists, and how `tests/test_manifest_regression.py` enforces it.

## TL;DR

- **Schema version**: 6 (top-level key `schema_version`).
- **Manifest scope**: frozen upstream baseline plus the historical pool93
  promotion recorded at extraction time. The current IJDS manuscript policy is
  newer and is governed separately by
  `docs/research/active_claims_2026-07-14.md`. The retired registry remains
  recoverable from Git history.
- **187 critical files** are hashed under `critical_hashes` (SHA256 + byte
  count).
- **Historical pool93 claim**: return `$184,832.48`, `V(alpha=0.01)=0.035350`,
  `Gamma_CP=0.162616`, `Gamma_res=0.073584`, endpoint `0.245084`, exact
  Markov loss threshold `0.345084`, realized risk-tolerance excess `0.0`, and
  declared alpha-grid pass `8/8`.
- **Matched A40 baseline**: CRPTO pays `5.875%` realized return relative to a
  point-PD LP and reduces weighted default/miscoverage by `8.305` percentage
  points under matched operating constraints.
- **6 files are flagged as non-overwriteable** without a fresh run tag:
  - `models/pd_canonical.cbm`
  - `models/pd_canonical_calibrator.pkl`
  - `models/final_project_promotion.json`
  - `models/conformal_policy_status.json`
  - `models/champion_portfolio_policy.json`
  - `models/champion_registry.json`
- **Regenerable from frozen inputs** (allowed to drift):
  - `models/crpto_evidence_status.json`
  - `models/crpto_journal_package_status.json`
- **Feature contract**: `data/processed/feature_config.yml` plus
  `data/processed/feature_config.parquet`; the legacy
  `feature_config.pkl` was retired in the 2026-06-13 run-tag-approved cleanup.
- **Source code, the Quarto book, CI files** are intentionally **not**
  bit-frozen — they evolve as documentation and tooling improve.

## Top-level fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer; the format of this manifest. Bump only when the JSON shape changes. |
| `project_name` | Always `CRPTO`. |
| `source_project` | Internal provenance label. Absolute paths and external workspace names are intentionally omitted. |
| `source_project_note` | Confirms the parent was not modified during extraction. |
| `destination` | Absolute path where the standalone repo was materialised. |
| `generated_at_utc` | When the manifest was produced. |
| `summary` | Free-text human description of the extraction scope. |
| `champion_metrics` | Frozen upstream baseline numbers retained as provenance and as the declared return floor. |
| `pool93_ijds_promotion` | Historical IJDS metadata frozen at extraction time; retained as provenance, not the current manuscript claim. |
| `critical_hashes` | Map `relative_path → {sha256, bytes, hash_source}` for every file the paper depends on. |
| `validation_results` | Output of the extraction-time guardrail tests. |
| `files` | Inventory of files copied/created during extraction. |
| `skipped_missing` | Files that the manifest expected but did not find at extraction time. |
| `second_pass_additions` / `final_exhaustive_pass_additions` | Files added during later passes of the extraction script. |

## How drift is detected

`tests/test_manifest_regression.py` reads `critical_hashes` and computes
the current SHA256 of every file that lives under these prefixes:

- `models/`
- `data/processed/`
- `reports/crpto/tables/`

Source code, documentation, the book and CI files are intentionally
**excluded** from drift testing — they are expected to evolve. PDF
figures are also excluded because matplotlib embeds creation timestamps
that change between runs.

The test fails when a file's bytes diverge from the manifest. The error
message names the file and prints both hashes so an operator can decide
whether the change is intentional (and therefore the manifest needs to
be regenerated) or accidental (and should be reverted).

## When to regenerate this manifest

Regenerating means re-running the extraction tooling under a new
`schema_version`. The legitimate triggers are:

1. A new paper run tag — the champion/body claim has been re-validated against
   fresh or newly promoted artefacts.
2. A revalidated refactor under one of the plans in `docs/refactor/`
   that produces bit-different but functionally equivalent outputs.
3. A schema migration of the manifest itself (e.g. switching the hash
   algorithm or adding a new section).

It is **not** regenerated for routine documentation, CI or test changes.

## Standalone Provenance

The manifest deliberately keeps only minimal extraction provenance. Active
remotes are standalone:

- GitHub: `EigenCharlie/Paper_CRPTO`
- DVC: `https://dagshub.com/EigenCharlie94/Paper_CRPTO.s3`
- MLflow: `https://dagshub.com/EigenCharlie94/Paper_CRPTO.mlflow`

If you need to reproduce the original extraction:

1. Restore the internal source workspace under local institutional controls.
2. Mount this repository's `destination` as the output directory.
3. Run the extraction script from the controlled source workspace.
4. Compare the new manifest to this one; the only fields that should
   differ are `generated_at_utc` and `destination`.

## Where to look next

- The frozen champion contract: [`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md).
- Refactor lanes that touch protected files:
  [`docs/refactor/`](docs/refactor/).
- The release checklist that must pass before any push touches
  protected paths: section "Release checklist" in
  `docs/SCOPE_AND_GOVERNANCE.md`.
