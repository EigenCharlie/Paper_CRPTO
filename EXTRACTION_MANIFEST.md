# EXTRACTION_MANIFEST — human summary

`EXTRACTION_MANIFEST.json` is a machine-readable record of how this
standalone repository was extracted from the parent
`lending-club-risk-project`. This Markdown file is the human-readable
companion: it explains what the manifest contains, why each section
exists, and how `tests/test_manifest_regression.py` enforces it.

## TL;DR

- **Schema version**: 4 (top-level key `schema_version`).
- **Champion run tag**: `paper-thesis-final-economic-2026-04-06`.
- **134 critical files** hashed under `critical_hashes` (SHA256 + byte
  count).
- **3 files are flagged as non-overwriteable** without a fresh run tag:
  - `models/pd_canonical.cbm`
  - `models/pd_canonical_calibrator.pkl`
  - `models/final_project_promotion.json`
- **Regenerable from frozen inputs** (allowed to drift):
  - `models/crpto_evidence_status.json`
  - `models/crpto_journal_package_status.json`
- **Source code, the Quarto book, CI files** are intentionally **not**
  bit-frozen — they evolve as documentation and tooling improve.

## Top-level fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer; the format of this manifest. Bump only when the JSON shape changes. |
| `project_name` | Always `CRPTO`. |
| `source_project` | The parent project. The absolute path was intentionally omitted to avoid leaking local paths. |
| `source_project_note` | Confirms the parent was not modified during extraction. |
| `destination` | Absolute path where the standalone repo was materialised. |
| `generated_at_utc` | When the manifest was produced. |
| `summary` | Free-text human description of the extraction scope. |
| `champion_metrics` | The headline numbers that define the paper contribution (robust return, V, Γ_CP, etc.). |
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

1. A new paper run tag — the champion has been re-validated against
   fresh model artefacts.
2. A revalidated refactor under one of the plans in `docs/refactor/`
   that produces bit-different but functionally equivalent outputs.
3. A schema migration of the manifest itself (e.g. switching the hash
   algorithm or adding a new section).

It is **not** regenerated for routine documentation, CI or test changes.

## Pointing to the parent project

The manifest deliberately does not store the absolute path of the parent
`lending-club-risk-project` repository. If you need to reproduce the
extraction:

1. Clone the parent locally.
2. Mount this repository's `destination` as the output directory.
3. Run the extraction script (kept in the parent project, not here).
4. Compare the new manifest to this one; the only fields that should
   differ are `generated_at_utc` and `destination`.

## Where to look next

- The frozen champion contract: [`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md).
- Refactor lanes that touch protected files:
  [`docs/refactor/`](docs/refactor/).
- The release checklist that must pass before any push touches
  protected paths: section "Release checklist" in
  `docs/SCOPE_AND_GOVERNANCE.md`.
