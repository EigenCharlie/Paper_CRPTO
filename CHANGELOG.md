# Changelog

All notable changes to **CRPTO** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to a single-author, paper-driven release cadence — see
`docs/ACADEMIC_CONTEXT.md`.

## [Unreleased]

### Added
- `tests/test_manifest_regression.py` — hash-regression tests against
  `EXTRACTION_MANIFEST.json` for the three protected champion files
  (`pd_canonical.cbm`, `pd_canonical_calibrator.pkl`,
  `final_project_promotion.json`) plus a sweep over frozen
  model/data/table artefacts.
- `crpto/` package re-exports the public API: `PolicyMode`,
  `load_pipeline_state`, `make_study`, `paper_run`, `VennAbersScoreCalibrator`,
  etc.
- `book/__init__.py` so `from book._helpers import ...` resolves to a real
  package rather than an implicit namespace package.
- `LICENSE-CONTENT` — CC-BY 4.0 for the book/paper text, separated from the
  MIT licensed code in `LICENSE`.
- `CONTRIBUTING.md` for reviewers (MRM, journal) describing how to
  regenerate the deliverables without disturbing the champion.

### Changed
- `LICENSE` now contains only the MIT text covering code; the dual-license
  note moved out to `LICENSE-CONTENT`.
- `CLAUDE.md` cross-references `docs/SCOPE_AND_GOVERNANCE.md` and
  `docs/ACADEMIC_CONTEXT.md` as required reading.

## [0.1.0] — 2026-05-11

First public release of the standalone Paper_CRPTO repository on GitHub
under `EigenCharlie/Paper_CRPTO`. Frozen against the paper champion:

- run tag `paper-thesis-final-economic-2026-04-06`
- policy `bound_aware_276k_economic_champion`
- robust return `$170,464.54`
- `V(α=0.01) = 0.03645`, `Γ_CP(α=0.01) = 0.18591`
- robust region `45/45`

### Highlights
- Quarto book with 24 chapters (manuscript + extended dossier), APA
  bibliography, dark mode, lightbox.
- DVC pipeline with 13 stages, frozen champion outputs hashed in
  `EXTRACTION_MANIFEST.json`.
- Refactors merged additively without touching the champion:
  `PolicyMode` enum, `pipeline_state` aggregator+writer (with protected
  files), MAPIE 1.x helper surface, Optuna 4 JournalStorage, MLflow 3
  tracing helpers, Pandera DataFrameModel companions.
- Dual-write helper for `feature_config.pkl` → YAML (companion file
  generated, round-trip tested).
- DVC `params:` declared on the four protected stages plus
  `crpto.book.render`; baseline absorbed without re-runs.
- 105 author tests green (including Hypothesis property-based tests,
  pickle-compat safety net, MAPIE structural invariants on the frozen
  parquet).
- GitHub Actions sized for a single-author academic project:
  `lint.yml` + `book-publish.yml` only. No branch protection. GitHub
  Pages serves the book at https://eigencharlie.github.io/Paper_CRPTO/.

### Operational decisions documented
- `docs/ACADEMIC_CONTEXT.md`: single-author, static dataset, no
  production deployment. Sizes CI/governance overhead accordingly.
- `docs/SCOPE_AND_GOVERNANCE.md`: explicit scope, frozen champion
  contract, refactor lanes with execution preconditions.
- `docs/security/SECRETS_AND_REMOTES.md`: secret handling and DagsHub
  integration.
- `docs/refactor/`: deferred-refactor plans for MAPIE class extraction,
  conformal monolith split and feature-config Parquet migration.

### Dependabot alert dismissed
- `diskcache <= 5.6.3` (CVE-2025-69872, transitive via `dvc-data`,
  severity medium, no upstream fix available) — dismissed as
  `no_bandwidth`. Re-evaluate when DVC publishes a fix.
