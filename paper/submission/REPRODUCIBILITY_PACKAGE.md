# IJDS Reproducibility Package Plan

IJDS requires the Data and Code Disclosure Form at submission and expects
accepted computational papers to upload data/code and complete the journal's
reproducibility workflow. CRPTO can satisfy this without exposing secrets,
private credentials, local paths, or author-identifying repository URLs during
double-anonymous review.

Official policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Disclosure Timing

| Stage | What to disclose | What to withhold |
|---|---|---|
| Initial double-anonymous submission | Neutral description of the companion package, data sources, DVC-style artifact validation, and code/data availability timing. | Public GitHub/DagsHub URLs, author identity, local paths, secrets, tokens. |
| If editors request verification during review | An anonymized archive or controlled access bundle with source, tables, figures, tests, and non-identifying artifact metadata. | Credentials, raw private data, non-anonymized remotes. |
| Acceptance | Public source repository, reproducibility commands, DVC pointers or downloadable processed artifacts where permitted, raw-data acquisition instructions, manifest hashes, and final rendered outputs. | Secrets and any data redistribution prohibited by source licenses. |

## Package Contents

| Component | Files/directories | Purpose |
|---|---|---|
| Source code | `src/`, `scripts/`, `tests/`, `pyproject.toml`, `uv.lock`, `justfile`. | Rebuild tables, figures, journal package, and validation checks. |
| Manuscript | `paper/CRPTO_ijds.qmd`, `paper/supplement_ijds.qmd`, `paper/submission/`. | Reproduce body, supplement, and submission surfaces. |
| Frozen evidence | `EXTRACTION_MANIFEST.json`, `models/*.json`, `reports/crpto/tables/`, `reports/crpto/figures/`. | Tie claims to immutable metrics and rendered evidence. |
| Data pointers | `.dvc/`, `dvc.yaml`, `dvc.lock`, DVC remote notes. | Retrieve or verify processed artifacts outside Git. |
| Raw-data instructions | Lending Club, Prosper, Freddie/Mendeley source notes. | Let readers reconstruct inputs without committing raw CSVs or credentials. |
| Guardrails | `just smoke`, `just validate-champion`, publication target tests, DVC status. | Confirm reproducibility without rerunning protected search stages. |

## Accepted-Paper Reproduction Commands

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

Artifact-aware DVC verification, when credentials or public artifact access are
available:

```powershell
uv run dvc status --no-updates
uv run dvc status -c -r dagshub
```

## Non-Rerunnable Stages

The following stages are not part of routine reproduction because they would
change the frozen champion or reopen the protected search:

```text
crpto.pd.champion
crpto.conformal.intervals
crpto.conformal.validation
crpto.portfolio.optimization
crpto.portfolio.bound_exact_eval
```

Paper-facing exports are safe because they consume frozen inputs. Any protected
rerun requires a new branch, drift report, and explicit decision to create a new
run tag.

## Data-License Strategy

The current plan is to publish code, derived tables/figures, manifest hashes,
and instructions for obtaining the raw public datasets. Processed artifacts and
models should be provided through DVC or a journal-approved supplement only when
source licenses and file sizes permit. If a dataset cannot be redistributed, the
package should include enough source instructions, schema notes, and commands for
a reader to rebuild comparable artifacts from legally obtained data.
