# IJDS Reproducibility Package Plan

Official policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

CRPTO can support accepted-paper reproduction without exposing credentials,
local paths, or author identity during double-anonymous review.

## Disclosure Timing

| Stage | Disclose | Withhold |
|---|---|---|
| Initial submission | Neutral package description, source-data availability, and release timing. | Repository ownership, personal URLs, local paths, secrets. |
| Editor-requested verification | Anonymized source, A35--A40, tests, and sanitized artifact metadata. | Credentials, private remotes, non-anonymous provenance. |
| Acceptance | Public source, environment lock, data instructions, artifact pointers/hashes, and final outputs. | Secrets and data prohibited from redistribution. |

## Package Contents

| Component | Files | Purpose |
|---|---|---|
| Environment | `pyproject.toml`, `uv.lock`, `justfile`. | Recreate the Windows-first toolchain. |
| Method source | `src/models/conformal_alpha_grid.py`, `src/optimization/`, active experiment scripts. | Replay exact intervals and solve declared policies. |
| Active config | `configs/experiments/champion_reopen_ijds_calibration_selected_simple90_v6.yaml`. | Fix alpha, 3x3 grid, selector, and solver settings. |
| Active evidence | A35--A40 CSV/TeX files and `ijds_policy_governance.json`. | Tie every paper claim to generated evidence. |
| Manuscript | body QMD, supplement QMD, official TeX. | Reproduce reviewer-facing surfaces. |
| Data pointers | `dvc.yaml`, `dvc.lock`, `.dvc/`, raw-data notes. | Retrieve large artifacts where terms permit. |
| Guardrails | active claim sync, publication integrity, manifest regression. | Detect narrative or historical artifact drift. |

## Active Artifact Contract

| Evidence | Path |
|---|---|
| Exact alpha grid | `data/processed/experiments/champion_reopen/<exact-run>/conformal/exact_alpha_grid.parquet` |
| Calibration selector | `data/processed/experiments/champion_reopen/<active-run>/portfolio/calibration_policy_selection_grid.parquet` |
| OOT evaluation | `data/processed/experiments/champion_reopen/<active-run>/portfolio/calibration_selected_policy_oot_evaluation.csv` |
| Funded rows | `data/processed/experiments/champion_reopen/<active-run>/portfolio/calibration_selected_policy_full_oot_allocations.parquet` |
| Governance | `models/experiments/champion_reopen/<active-run>/portfolio/ijds_policy_governance.json` |
| Paper tables | `reports/crpto/tables/crpto_tableA35...A40_*` |

Active run:
`champion-reopen-2026-06-19__pool93__ijds-calibration-selected-simple90-v6`.

Exact-alpha run:
`champion-reopen-2026-06-19__pool93__ijds-exact-alpha-grid-v1`.

The active policy evidence is intentionally separate from the manifest-protected
historical bundle. `tests/test_ijds_active_claim_sync.py` guards the submitted
claim; `tests/test_manifest_regression.py` guards frozen provenance. The
manifest is not rewritten to make a manuscript update look historical.

## Reproduction Commands

Paper-facing reproduction from frozen experiment outputs:

```powershell
just setup-base
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py -q
just paper-submission
just paper-submission-official
just validate-champion
```

Full isolated methodology replay:

```powershell
just ijds-active-replay
```

The full replay recomputes the exact alpha grid, solves the nine calibration
policies, evaluates the frozen selected policy, and rebuilds A35--A40. It writes
only to versioned experiment paths and does not overwrite the frozen PD model,
calibrator, historical intervals, or manifest.

Official-template compilation is automated by:

```powershell
just paper-submission-official
```

Manual Windows fallback:

```powershell
cd paper/submission
if (-not $env:WINDIR) { $env:WINDIR = $env:SystemRoot }
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
bibtex CRPTO_ijds_submission
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
```

## Data and Artifact Boundary

- Lending Club, Prosper, and Freddie/Mendeley raw data are distributed through
  their original sources, not copied into Git.
- Large processed parquet and model binaries use DVC or journal-approved
  artifact delivery when source terms permit.
- `EXTRACTION_MANIFEST.json` verifies the historical upstream bundle.
- Review-stage copies of DVC/configuration metadata must remove repository
  ownership, remote URLs, credentials, and absolute local paths.
- If a remote is unavailable, provide journal-approved processed artifacts plus
  hashes, schema/source notes, and the commands above.

## Non-Routine Stages

The active reproduction does not run protected upstream stages:

```text
crpto.pd.champion
crpto.conformal.intervals
crpto.conformal.validation
crpto.portfolio.optimization
crpto.portfolio.bound_exact_eval
```

Those stages would retrain, rewrite frozen artifacts, or reopen historical
search. Any such run requires a distinct tag and drift report.

## Acceptance Checklist

1. Build in the locked `uv` environment.
2. Rebuild A35--A40 and run active claim sync.
3. Validate historical manifest hashes.
4. Compile and visually inspect the official PDF and supplement.
5. Sanitize author identity and local paths in the review archive.
6. Publish source-data acquisition instructions and artifact hashes.
7. Record any unavoidable platform-level numerical differences explicitly.
