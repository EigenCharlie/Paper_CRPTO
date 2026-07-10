# IJDS Reproducibility Package

Official policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Release Stages

| Stage | Provide | Withhold |
|---|---|---|
| Initial submission | Neutral availability statement and anonymous PDFs | Identity, repository ownership, personal URLs, secrets |
| Editor-requested verification | Sanitized source, active config, evidence, tests, hashes, DVC pointers | Credentials and non-anonymous remote metadata |
| Acceptance | Public source, environment lock, data instructions, active artifacts and final outputs | Secrets and raw files prohibited from redistribution |

## Minimal Active Capsule

| Component | Files | Purpose |
|---|---|---|
| Environment | `pyproject.toml`, `uv.lock`, `justfile` | Recreate Python and task tooling |
| Protocol | locked v2 YAML and protocol memo | Fix dates, estimands, model, policy grid, payoff and bounds |
| Method | maturity-safe data/model/evaluation modules and runner | Reproduce the tagged experiment |
| Active run | two DVC pointers plus remote/archive objects | Recover processed panels, model, allocations, summary and receipt |
| Evidence | builder, tables 1--3/S1--S7, figures 1--3, manifest | Reproduce every manuscript number and graphic |
| Manuscript | QMD body, QMD supplement, official TeX, bibliography | Reproduce reviewer-facing PDFs |
| Guardrails | claim sync, integrity, unit/integration tests | Detect numerical, narrative, and historical drift |

Historical A1--A40, compact-v7, Prosper, and Freddie/Mendeley artifacts remain
available as project provenance but are outside the minimal active capsule.
Excluding them reduces package size and prevents a reviewer from mistaking old
experiments for current evidence.

## Immutable Identifiers

| Item | Value |
|---|---|
| Run tag | `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2` |
| Protocol tag | `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2` |
| Commit | `78a64fe67a4df46c3d19b9243deb991c56fd1ff6` |
| Summary SHA-256 | `a9c3b3738b26096703fdd2d1b1e852f72b1516157317c65a92e1bb0abdfd693b` |
| Receipt SHA-256 | `7847ba0dc68598de7960c7e78f8a11de527cc7bbf4ddd9f90421bdfa48b68f33` |
| Processed DVC MD5 | `90ecc510414f698f91767f3e507733f0.dir` |
| Model/results DVC MD5 | `fb6220447bb86971c9f41a44f208e885.dir` |

The receipt records a clean initial and final worktree, Python 3.11.14,
CatBoost 1.2.10, and highspy 1.14.0. The evidence builder verifies every
artifact hash before generating publication outputs.

## Standard Reproduction

```powershell
uv sync --extra dev
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py -q
just publication-integrity
just paper-submission
just paper-submission-official
just validate-champion
```

`just ijds-active-replay` intentionally means evidence validation and rebuild,
not an implicit 1.7 GB methodology rerun.

## Optional Full Method Replay

Only in a clean clone where the immutable run directory does not exist:

```powershell
uv run python scripts/experiments/run_ijds_maturity_safe_challenger.py `
  --config configs/experiments/ijds_maturity_safe_locked_bounded_h1h2_2026-07-10.yaml
```

The runner verifies the protocol tag and clean commit, refuses path escape and
overwrite, separates decisions from outcomes, and writes the deterministic
summary and receipt only after all outputs complete. Replaying the active run
does not require or permit a protected historical `dvc repro`.

## Official PDF Build

```powershell
just paper-submission-official
```

The wrapper invokes the direct Windows `latexmk.pl` payload. Its robust fallback
is `pdflatex -> bibtex -> pdflatex -> pdflatex`: the first LaTeX pass creates
`.aux`, BibTeX creates `.bbl`, and two final LaTeX passes resolve then stabilize
citations, references, floats, and pagination.

## Acceptance QA

1. Reproduce from a fresh clone and DVC pull.
2. Confirm the evidence builder is byte-idempotent.
3. Run the full release gate and historical manifest validation.
4. Compile and visually inspect body, supplement, and official PDF.
5. Confirm no reviewer-facing identity or local path leakage.
6. Publish source-data acquisition instructions and all immutable hashes.
7. Record any unavoidable platform-level numerical difference rather than
   silently changing the evidence.
