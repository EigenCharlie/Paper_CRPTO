# IJDS Reproducibility Package Plan

Editor-facing operational material. Do not include this file in the
double-anonymous reviewer packet. Use
`ANONYMOUS_REVIEW_ARCHIVE_README.md` for the sanitized review-stage contract
and `EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md` for exact immutable identifiers.

Official policy: <https://pubsonline.informs.org/page/ijds/data-and-code-disclosure-policy>

## Release Stages

| Stage | Provide | Withhold |
|---|---|---|
| Initial submission | Neutral availability statement and anonymous PDFs | Identity, repository ownership, personal URLs, secrets |
| Editor-requested verification | Metadata-sanitized archive labeled P1/C1, evidence, tests, and archive-local hashes | Git history, public-repository links, exact public-searchable run identifiers, credentials, and remote metadata |
| Acceptance | Public source, environment lock, data instructions, active artifacts and final outputs | Secrets and raw files prohibited from redistribution |

## Minimal Active Capsule

| Component | Files | Purpose |
|---|---|---|
| Environment | `pyproject.toml`, `uv.lock`, `justfile` | Recreate Python and task tooling |
| Protocol | locked parent and comparator YAML/memos | Fix dates, estimands, policy, matching rule, payoff, bounds, and post hoc boundary |
| Method | maturity-safe modules plus parent/comparator runners | Reproduce both tagged experiments |
| Active runs | four DVC pointers plus remote/archive objects | Recover parent and comparator panels, allocations, summaries, and receipts |
| Evidence | two builders, parent M/S bundle, comparator C/CS bundle, two manifests | Reproduce every manuscript number and graphic |
| Manuscript | QMD body, QMD supplement, official TeX, bibliography | Reproduce reviewer-facing PDFs |
| Guardrails | claim sync, integrity, unit/integration tests | Detect numerical, narrative, and historical drift |

Historical A1--A40, compact-v7, Prosper, and Freddie/Mendeley artifacts remain
available as project provenance but are outside the minimal active capsule.
Excluding them reduces package size and prevents a reviewer from mistaking old
experiments for current evidence.

## Identifier Boundary

The manuscript calls the parent layer P1 and the comparator layer C1. Exact
run tags, protocol tags, commits, summary and receipt hashes, and DVC object
fingerprints live only in `EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`. This
separation preserves a complete audit trail without placing public-searchable
fingerprints in reviewer-facing material.

Both execution receipts record clean initial and final worktrees. The C1
receipt records Python 3.11.14, CatBoost 1.2.10, highspy 1.14.0, and a
302.16-second runtime. Both builders verify artifact hashes before producing
publication outputs.

## Standard Editor/Acceptance Reproduction

```powershell
uv sync --extra dev
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2.dvc
uv run dvc pull data/processed/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1.dvc
uv run dvc pull models/experiments/champion_reopen/champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1.dvc
just ijds-evidence
uv run pytest tests/test_ijds_active_claim_sync.py tests/test_ijds_comparator_evidence.py -q
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

uv run python scripts/experiments/run_ijds_comparator_stringency_audit.py `
  --config configs/experiments/ijds_maturity_safe_locked_comparator_stringency_2026-07-10.yaml
```

Both runners verify protocol tags and clean commits, refuse path escape and
overwrite, and write receipts only after outputs complete. The comparator
verifies and replays parent artifacts before evaluating fixed policies. Neither
replay requires or permits a protected historical `dvc repro`.

## Official PDF Build

Download the current official style package from the INFORMS author portal and
place `informs4.cls`, `informs2014.bst`, `eqndefns-left.sty`, and
`informs_Logo.pdf` in `paper/submission`. These publisher assets are external
build prerequisites and are intentionally ignored by Git.

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

The initial ScholarOne upload does not require a public repository or the full
method replay. IJDS requires the disclosure form at submission and the full
reproducibility workflow at acceptance; an editor-requested review archive is
prepared under the anonymous contract rather than by exposing this repository.
