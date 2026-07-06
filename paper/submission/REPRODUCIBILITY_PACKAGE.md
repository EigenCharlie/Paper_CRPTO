# IJDS Reproducibility Package Plan

IJDS requires the Data and Code Disclosure Form at submission and expects
accepted computational papers to upload data/code and complete the journal's
reproducibility workflow unless an exemption applies. CRPTO can satisfy this
without exposing secrets, private credentials, local paths, or
author-identifying repository URLs during double-anonymous review.

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
| Raw-data instructions | `RAW_DATA_SOURCE_NOTES.md`. | Let readers reconstruct inputs without committing raw CSVs or credentials. |
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

Official IJDS-template PDF build, after `paper/submission/CRPTO_ijds_submission.tex`
is synchronized:

```powershell
cd paper/submission
latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
```

PowerShell/TinyTeX fallback proven in the local Codex environment:

```powershell
cd paper/submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
bibtex CRPTO_ijds_submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
```

Artifact-aware DVC verification, when credentials or public artifact access are
available:

```powershell
uv run dvc status --no-updates
uv run dvc status -c -r dagshub
```

## Pool93 Body-Claim Artifacts

The paper body point (A35 "Body/default balanced point") and its frontier come
from the pool93 champion-reopen experiments, generated *outside* the DVC DAG by
deterministic re-evaluation of a pre-declared finite policy grid over the
frozen Mondrian conformal intervals. The package therefore includes, verbatim
and frozen:

| Artifact | Path | Role |
|---|---|---|
| A35 frontier | `reports/crpto/tables/crpto_tableA35_pool93_ijds_frontier.csv` (+ `.tex`) | Consolidated return-bound frontier; body point row. |
| A36 grade audit | `reports/crpto/tables/crpto_tableA36_pool93_body_funded_grade_audit.csv` (+ `.tex`) | Funded-set grade composition of the body allocation. |
| A37 tail risk | `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.csv` (+ `.tex`) | LGD-grid repricing and CVaR/OCE diagnostics. |
| A38 cluster bounds | `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.csv` (+ `.tex`) | Cluster-aware Hoeffding sensitivity. |
| A39 bootstrap | `reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.csv` (+ `.tex`) | 5,000-draw fixed-allocation bootstrap intervals. |
| Terminal claim governance | `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal/portfolio/pool93_ijds_claim_governance.json` | Declared return floor, claim hierarchy, do-not-claim list. |
| Consolidated governance | `models/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_ijds_consolidated_governance.json` | Authoritative body-point metrics and frontier counts. |

Run tags: terminal `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal`;
consolidated `champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive`.
Their hashes are pinned in `EXTRACTION_MANIFEST.json` and enforced by
`tests/test_manifest_regression.py`; body-claim consistency with the manuscript
is enforced by `tests/test_pool93_body_claim_sync.py`. These artifacts are not
regenerated by `just tables`/`just figures` (which rebuild only the
rebaseline-chain tables); they ship as frozen evidence.

Anonymity note: the governance JSONs embed absolute local paths in their
`source_paths`/`runtime_status` blocks. Copies shipped inside any
review-stage or accepted-paper archive must be path-sanitized (or the fields
dropped); the in-repo originals stay hash-frozen.

## Hash and DVC Boundary

- `EXTRACTION_MANIFEST.json` is the source of truth for protected artifact
  hashes; `just validate-champion` runs the manifest regression tests.
- DVC metadata (`dvc.yaml`, `dvc.lock`, `.dvc/`) records large data/model
  dependencies and outputs without placing raw CSVs, processed parquet files, or
  model binaries in Git.
- The accepted-paper archive may include processed/model artifacts directly only
  if the journal workflow and source-data terms permit it. Otherwise it should
  include DVC pointers, source acquisition notes, and the commands above.
- Review-stage archives must sanitize author-local paths and repository remotes
  if they are sent before anonymity is lifted.

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
