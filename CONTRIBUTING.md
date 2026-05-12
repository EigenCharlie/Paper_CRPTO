# Contributing to CRPTO

This is a single-author academic project (master's thesis + paper +
journal package). It is **not** a community-driven open-source library.
Pull requests from external contributors are not expected; this document
exists so that reviewers (MRM, journal, defense committee) can
reproduce the deliverables and understand the operational guardrails.

If you are reading this because you are a reviewer or a future agent that
inherited the repo, read in this order:

1. [`README.md`](README.md) — what the repo is and how to run the book.
2. [`docs/ACADEMIC_CONTEXT.md`](docs/ACADEMIC_CONTEXT.md) — why the
   tooling is intentionally minimal and how the champion-versus-search
   distinction works.
3. [`docs/SCOPE_AND_GOVERNANCE.md`](docs/SCOPE_AND_GOVERNANCE.md) —
   what is in scope, what is forbidden in `main`, the release
   checklist.
4. [`CLAUDE.md`](CLAUDE.md) — operating rules for AI agents working in
   this repo.

## Reproducing the paper outputs

```powershell
# One-time setup (Windows PowerShell)
git clone https://github.com/EigenCharlie/Paper_CRPTO.git
cd Paper_CRPTO
uv venv
uv sync --extra dev --extra search
just smoke           # runs artifact-independent guardrail tests
```

To re-render the Quarto book without re-executing any chunks (uses
`_freeze`):

```powershell
just book            # uv run -- quarto render book --to html --no-execute
```

To regenerate the paper tables and figures from frozen inputs:

```powershell
just paper-export    # tables + figures + evidence + journal package + book
```

These commands never touch the champion artefacts on disk and never
re-run any DVC stage that performs *search* (the 276k portfolio sweep
or Optuna HPO are out of scope by policy).

## What you may change freely

- Documentation, comments, docstrings.
- Quarto prose, glossary entries, chapter ordering.
- Test coverage (especially in `tests/test_utils/`, `tests/test_optimization/`,
  `tests/test_features/`).
- Tooling: ruff config, hooks, IDE settings, justfile recipes.
- New scripts that read frozen artefacts without overwriting them.

## What requires a deliberate revalidation plan

Anything that would change the bytes of these files:

- `models/pd_canonical.cbm`
- `models/pd_canonical_calibrator.pkl`
- `models/final_project_promotion.json`
- `models/conformal_policy_status.json`
- `data/processed/conformal_intervals_mondrian.parquet`
- The `portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_*` directory
- `EXTRACTION_MANIFEST.json`

`tests/test_manifest_regression.py` will fail loudly if these drift.

A revalidation plan must include:

1. A branch dedicated to the change (never on `main`).
2. A drift report comparing the new artefact to the frozen one with
   tolerances documented in `docs/ACADEMIC_CONTEXT.md`:
   max abs diff `≤ 1e-6` per loan on conformal intervals, coverage
   delta `≤ 5e-4` per Mondrian cell, robust return delta `≤ $1.00`.
3. If the drift is non-zero, the change is not a refactor — it is a
   model change and needs a fresh run tag.

See the three plans under `docs/refactor/` for the pre-written templates
(MAPIE migration, conformal module split, feature_config Parquet).

## What is forbidden in `main`

The DVC search stages listed in `docs/ACADEMIC_CONTEXT.md` are blocked
by `.claude/settings.json` and `.codex/skills/crpto/SKILL.md`. Do not
run them from the default branch:

- `dvc repro crpto.portfolio.bound_exact_eval`
- Any Optuna HPO that would overwrite the frozen study.

## Code style

- Run `just lint` (ruff check + format check) before any commit.
- Run `just smoke` to verify the tests that the pre-push hook will
  re-run anyway.
- Mypy strict applies to a small allow-list of new modules
  (`src/optimization/policy.py`, `src/utils/pipeline_state.py`,
  `src/utils/mlflow_tracing.py`, `src/utils/optuna_storage.py`).
  Other modules use a laxer config to absorb research-grade code.
- No new top-level scripts; add to `src/` or `scripts/` according to
  whether the code is library or pipeline.
- Spanish for book/paper prose; English for code, docstrings, tests,
  CI and changelog.

## Releasing

Single-author releases happen by tagging a clean `main`:

```bash
git tag -a vX.Y.Z -m "release notes here"
git push origin vX.Y.Z
```

The tag triggers the `book-publish` workflow which deploys the latest
HTML rendering of the book to GitHub Pages.

## Citing

See [`CITATION.cff`](CITATION.cff) for the canonical citation block.
