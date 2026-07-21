# IJDS Reproducibility Package

This editor-facing plan is the single source for capsule contents, raw-data
instructions, and replay commands.

## Release Stages

| Stage | Provide | Exclude |
|---|---|---|
| Initial submission | Anonymous body, supplement, title-page form, disclosure form | Identity and searchable repository metadata in reviewer files |
| Editor verification | Sanitized active capsule and archive-local checksums | Credentials, machine paths, unrelated Git history |
| Acceptance | Code, lock, data instructions, active artifacts, final outputs | Secrets and source files prohibited from redistribution |

## Minimal Active Capsule

| Component | Contents |
|---|---|
| Environment | `pyproject.toml`, `uv.lock`, `justfile` |
| Authority | Active claim registry, executable claim ledger, source registry, publication targets |
| Method | Complete `src` package, active runners, evidence and paper builders |
| Runs | 47 DVC pointers for active roots, sensitivities, and replay dependencies |
| Evidence | One manifest, 27 CSV tables, three figures in PDF/PNG |
| Manuscript | QMD body/supplement, generated INFORMS TeX, bibliography |
| Gates | Scientific tests, lint, typing, drift, claim sync, anonymity, PDF QA |

Historical selected-policy, compact-v7, pool93, external-transfer, and A1--A40
materials are excluded from this capsule.

## Raw Data Contract

The active raw source is `Loan_status_2007-2020Q3.csv`, expected size
1,773,470,505 bytes and SHA-256
`5878af2a088f8ab5214c9337289fb8b5eb6c6338fd3f417b6cdc18513dc6f35f`.
It is ignored by Git and referenced by DVC metadata. Public community or
repository mirrors have existed, but no single issuer-maintained permanent URL
is guaranteed. The package therefore supplies file identity, schema and
cleaning code, full-file audit artifacts, and reconstruction instructions
rather than depending on one URL or rehosting the raw CSV.

The code scans 2,925,493 rows and 142 columns. The active design uses every
eligible 36-month loan under the declared chronology and schema. The archive is
not a verified point-in-time snapshot; endpoint availability is reconstructed
from servicing dates. Prosper, Freddie/Mendeley, and Home Credit files are
historical diagnostics and are not required.

## Standard Reproduction

```powershell
uv sync --group dev --frozen
uv run --locked python scripts/manage_ijds_dvc_capsule.py pull
just submission-build
just ijds-active-check
uv run --locked python scripts/manage_ijds_dvc_capsule.py status
```

The DVC pull requires machine-local credentials. The official PDF additionally
requires the pinned INFORMS style kit in `paper/submission`.

`just ijds-active-check` verifies active evidence without executing protected
historical stages. The maintainer-only submission closeout may validate
historical artifacts already present with `just submission-check`, but it does
not reproduce them.

## Full Replay Boundary

All outcome-free roots are immutable. A new methodology replay requires a new
protocol tag, run tag, and fresh output paths. It must retain all declared cells,
may not overwrite an active or historical root, and cannot silently replace the
paper contract after inspecting outcomes.

For human scientific replay, each 2026-07-21 runner must be invoked from a
clean checkout at its own registered protocol tag. The active commands are:

```powershell
uv run --locked python scripts/experiments/run_ijds_conformal_set_diagnostics.py --config configs/experiments/ijds_conformal_set_diagnostics_2026-07-21_v1.yaml
uv run --locked python scripts/experiments/run_ijds_exchangeability_transport_test.py --config configs/experiments/ijds_exchangeability_transport_test_2026-07-21_v1.yaml
uv run --locked python scripts/experiments/run_ijds_rolling_origin_equal_followup.py --config configs/experiments/ijds_rolling_origin_equal_followup_2026-07-21_v1.yaml
uv run --locked python scripts/experiments/run_ijds_rolling_origin_individual_age_followup.py --config configs/experiments/ijds_rolling_origin_individual_age_followup_2026-07-21_v1.yaml
uv run --locked python scripts/experiments/run_ijds_label_mondrian_freeze.py --config configs/experiments/ijds_label_mondrian_freeze_2026-07-21_v1.yaml
uv run --locked python scripts/experiments/run_ijds_label_mondrian_evaluation.py --config configs/experiments/ijds_label_mondrian_evaluation_2026-07-21_v1.yaml
```

Every runner requires fresh run-tag output paths and refuses a dirty or
non-tagged scientific checkout. Label-Mondrian evaluation is a second stage:
its config must retain the registered descriptors of the completed outcome-free
freeze. The earlier primary-origin recovery and 2017 rolling-origin runs remain
available with the parent equal-quarter run as replay provenance, but they are
not active paper-facing evidence and are not substitutes for the individual-age runner.

## Official PDF Build

```powershell
just paper-tex
just paper-official
```

The compiler attempts `latexmk` and falls back to
`pdflatex -> bibtex -> pdflatex -> pdflatex`. The passes create the auxiliary
graph, bibliography, cross-references, and stable pagination in that order.

## Acceptance QA

1. Reproduce from a fresh clone and the 47 DVC pointers.
2. Confirm evidence and QMD-to-TeX builders are byte-idempotent.
3. Run scientific, lint, type, drift, publication, and protected-artifact checks.
4. Compile and inspect body, supplement, and official PDF page by page.
5. Confirm identity, path, tag, commit, and hash sanitization for reviewers.
6. Publish data acquisition, dictionary, environment, and artifact hashes.
7. Document platform-level numerical differences without retuning evidence.

Exact immutable identifiers live only in
`EDITOR_ONLY_REPRODUCIBILITY_CROSSWALK.md`.
