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
| Protocol | V4 config, protocol, recovery memo, and claim registry | Fix windows, policies, comparators, outcomes, and stop rules |
| Method | `src/ijds_audit`, V4 runner, and evidence builder | Reproduce the active study |
| Active runs | four V4 DVC pointers | Recover outcome-free and evaluated roots |
| Evidence | one manifest, five tables, and three figures in PNG/PDF | Reproduce paper-facing results |
| Manuscript | canonical QMD, generated INFORMS TeX, supplement, bibliography | Reproduce PDFs |
| Gates | scientific tests, claim sync, lint, typing, anonymity, visual QA | Detect drift |

Historical fixed-taxonomy V1--V3, selected-policy, compact-v7, pool93,
Prosper/Freddie, and A1--A40 materials remain recoverable from Git/DVC but are
excluded from the active capsule.

## Standard Reproduction

```powershell
uv sync --frozen --extra dev --extra search --extra spo
uv run dvc pull data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v1.dvc
uv run dvc pull data/processed/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc
uv run dvc pull models/experiments/ijds_audit/ijds-binary-geometry-frontier-v4-2026-07-12-v2.dvc
just ijds-active-check
just paper-submission
just paper-submission-official
```

The DVC pull requires a machine-local `.dvc/config.local` or equivalent remote
credentials; credentials are never committed. The official PDF additionally
requires the current INFORMS style kit (`informs4.cls`, `informs2014.bst`,
`eqndefns-left.sty`, and `informs_Logo.pdf`) in `paper/submission`; these
publisher files are intentionally ignored by Git.

The maintainer-only `just submission-check` also runs
`validate-champion-strict`. That gate requires every historical artifact in
`EXTRACTION_MANIFEST.json` to be present, but does not execute its protected
stages. An active-capsule reviewer does not need those historical artifacts to
reproduce V4.

`just ijds-active-replay` validates the active evidence and rebuilds
paper-facing outputs. It intentionally does not hide an expensive methodology
rerun.

## Full Replay Boundary

The outcome-free Phase-1 archive is immutable. Phase 2 verifies and imports it
before one outcome join. A new full replay may run only with a new run tag and
fresh paths; it must not overwrite either phase or invoke protected DVC stages.
Its results cannot silently replace the paper contract.

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

1. Reproduce from a fresh clone and the four DVC pointers.
2. Confirm evidence and QMD-to-TeX builders are byte-idempotent.
3. Run the full gate and protected champion validation without reproducing its stages.
4. Compile and visually inspect body, supplement, and official PDF.
5. Confirm reviewer-facing identity and path sanitization.
6. Publish acquisition instructions, data dictionary, environment, and hashes.
7. Document any platform-level numerical difference rather than changing evidence.

The exact immutable identifiers live only in
`EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`.
