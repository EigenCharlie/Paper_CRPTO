# IJDS Data and Code Disclosure Form Draft

This is a working draft for completing the official IJDS Data and Code
Disclosure Form in ScholarOne. It is not the official form and should not be
uploaded as a substitute unless the submission system asks for free-form
supporting text.

Official policy:
<https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Short Disclosure Statement

The paper is computational and relies on public-source credit-risk datasets,
derived processed artifacts, frozen model outputs, and reproducible code. During
double-anonymous review, the manuscript describes a reproducible companion
package without exposing author-identifying URLs. If accepted, the author will
release a public reproducibility package containing source code, manuscript
sources, paper table/figure generation commands, frozen artifact metadata,
manifest hashes, and instructions for obtaining or reconstructing the raw data.

## Data Sources

| Data source | Role in paper | Disclosure plan |
|---|---|---|
| Lending Club retail-loan data | Main static credit-risk panel and promoted funded-set certificate. | Provide source/acquisition instructions, schema notes, cleaning pipeline, DVC pointers or processed artifacts when redistribution is allowed. |
| Prosper loan data | Frozen external marketplace-loan economic replication. | Provide source notes and generated summary artifacts; do not claim a new exact certificate. |
| Freddie/Mendeley mortgage panel | Frozen external mortgage-credit economic replication. | Provide source notes and generated summary artifacts; do not claim a new exact certificate. |
| Home Credit | Audited but not promoted because it lacks the required economic exposure/return contract. | Mention only as archived/non-promoted source context if needed. |

## Code Availability

The accepted-paper package should include:

- Python package code under `src/`.
- Pipeline and export scripts under `scripts/`.
- Quarto manuscript, supplement, and book sources.
- Tests and guardrails under `tests/`.
- `pyproject.toml`, `uv.lock`, `justfile`, `dvc.yaml`, and `dvc.lock`.
- Commands for regenerating tables, figures, evidence summaries, journal
  package files, and local PDF previews.

## Artifact Availability

The accepted-paper package should include or point to:

- `EXTRACTION_MANIFEST.json`.
- Frozen JSON status files under `models/`.
- Paper tables under `reports/crpto/tables/`.
- Paper figures under `reports/crpto/figures/`.
- DVC metadata and remote-access instructions for large processed/model
  artifacts when allowed.

## Reproducibility Commands

```powershell
just setup-base
just smoke
just validate-champion
just tables
just figures
just evidence
just journal-package
just paper-submission
just paper-submission-pdf
```

Optional artifact-aware check when DVC access is configured:

```powershell
uv run dvc status --no-updates
uv run dvc status -c -r dagshub
```

## Non-Routine Rerun Boundary

The following stages are not routine reproduction steps because they would
change the frozen champion or reopen protected search:

```text
crpto.pd.champion
crpto.conformal.intervals
crpto.conformal.validation
crpto.portfolio.optimization
crpto.portfolio.bound_exact_eval
```

Any protected rerun requires a new run tag and drift report.

## Double-Anonymous Review Note

For initial review, reviewer-facing files should omit public repository URLs,
author-identifying remote names, local paths, credentials, and acknowledgements.
If editors request reproducibility verification during review, provide an
anonymized archive or controlled-access bundle consistent with the journal's
instructions.
