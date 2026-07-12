# IJDS Reproducibility Package Plan

Editor-facing operations. The current IJDS policy requires the disclosure form
at submission and data/code plus a reproducibility workflow at acceptance.

## Release Stages

| Stage | Provide | Withhold |
|---|---|---|
| Initial submission | Anonymous manuscript, supplement, title page, disclosure form | Public identity inside reviewer files, secrets, remote metadata |
| Editor-requested verification | Sanitized active capsule and archive-local checksums | Git history, public-searchable identifiers, credentials |
| Acceptance | Source, lock, data instructions, active artifacts, final outputs | Secrets and files prohibited from redistribution |

## Minimal Active Capsule

| Component | Contents | Purpose |
|---|---|---|
| Environment | `pyproject.toml`, `uv.lock`, `justfile` | Recreate tooling |
| Protocol | fixed-taxonomy V1/V2 and temporal V3 YAML/memos | Fix timing, policies, comparators, payoffs, bounds |
| Method | active data/model/evaluation/optimization modules and runner | Reproduce the study |
| Active runs | six DVC pointers | Recover both freezes and evaluation bundles |
| Evidence | one builder, 18 table families, 4 figures, manifest | Reproduce every paper-facing result |
| Manuscript | canonical QMD, generated INFORMS TeX, supplement, bibliography | Reproduce PDFs |
| Gates | scientific tests, claim sync, lint, typing, anonymity, visual QA | Detect drift |

Historical selected-policy, compact-v7, pool93, Prosper/Freddie, and A1--A40
materials remain recoverable from Git/DVC but are excluded from the capsule.

## Standard Reproduction

```powershell
uv sync --frozen --extra dev --extra search --extra spo
uv run dvc pull data/processed/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v1.dvc
uv run dvc pull models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v1.dvc
uv run dvc pull data/processed/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v2.dvc
uv run dvc pull models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-2026-07-11-v2.dvc
uv run dvc pull data/processed/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1.dvc
uv run dvc pull models/experiments/ijds_prefreeze/ijds-fixed-taxonomy-c2-temporal-v3-2026-07-12-v1.dvc
just ijds-active-check
just paper-submission
just paper-submission-official
```

The DVC pull requires a machine-local `.dvc/config.local` or equivalent S3
credentials; credentials are never committed. The official PDF additionally
requires the current INFORMS style kit (`informs4.cls`, `informs2014.bst`,
`eqndefns-left.sty`, and `informs_Logo.pdf`) in `paper/submission`; these
publisher files are intentionally ignored by Git.

The maintainer-only `just submission-check` additionally runs
`validate-champion-strict`, which requires every historical artifact in
`EXTRACTION_MANIFEST.json` to be present. An active-capsule reviewer need not
download that separate historical champion to reproduce V1/V2/V3 or the paper;
maintainers must run the strict gate before freeze.

This sequence was verified on July 12, 2026, from the current pre-freeze branch
in a fresh local clone. `uv` installed 325 locked packages; DVC fetched 92
objects and materialized 103 files across all six V1/V2/V3 pointers; the
41-test active contract passed; and the official citation-clean PDF rebuilt at
28 pages. Rebuilding the evidence and TeX left the clean clone without a
tracked diff.

`just ijds-active-replay` validates the active evidence and rebuilds
publication outputs. It intentionally does not hide an expensive methodology
rerun.

The repository also retains tests and DVC pointers for historical P1/C1 and
compact-v7 diagnostics. Those inputs are deliberately outside the active
capsule and are not required by `just ijds-active-check`; maintainers who run
the complete historical test suite must materialize the corresponding DVC
pointers as well.

## Full Replay Boundary

The outcome-free V1 archive is immutable and its evaluator is intentionally
marked incomplete. V2 verifies and resumes its frozen scientific objects. A
new full replay may be run only in a clean clone with a new run tag and fresh
paths; it must not overwrite V1/V2/V3 or invoke protected DVC stages. Its results
cannot silently replace the paper contract.

## Official PDF Build

The INFORMS TeX is generated from `paper/CRPTO_ijds.qmd`:

```powershell
just paper-submission-tex
just paper-submission-official
```

The compiler attempts `latexmk` and uses the robust Windows fallback
`pdflatex -> bibtex -> pdflatex -> pdflatex`. The first LaTeX pass writes
`.aux`, BibTeX writes `.bbl`, and the final two passes resolve and stabilize
citations, references, floats, and pagination.

## Acceptance QA

1. Reproduce from a fresh clone and DVC pull.
2. Confirm the evidence builder and QMD-to-TeX builder are byte-idempotent.
3. Run the full gate and protected champion validation without reproducing its stages.
4. Compile and visually inspect body, supplement, and official PDF.
5. Confirm reviewer-facing identity and path sanitization.
6. Publish acquisition instructions, data dictionary, environment, and hashes.
7. Document any platform-level numerical difference rather than changing evidence.

The exact immutable identifiers live only in
`EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`.
