# Changelog

All notable changes to **CRPTO** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to a single-author, paper-driven release cadence — see
`docs/ACADEMIC_CONTEXT.md`.

## [Unreleased]

### Added
- `src/utils/script_helpers.py` — canonical JSON/YAML/table I/O helpers for
  the publication scripts, with LF-only idempotent writers that keep
  regenerated tables bit-exact against `EXTRACTION_MANIFEST.json` on
  Windows (fixes a latent CRLF reproducibility bug in `just tables`).
- `scripts/archive/` — six zero-reference one-shot scripts moved out of the
  active tree (`build_concentration_bound_table.py`,
  `run_crpto_notebook_suite.py`, and four `search/` helpers); roles recorded
  with `status: archived` in `configs/pipeline_registry/script_role_registry.yaml`.

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

### Changed (april-lineage unification, 2026-06-10)
- `models/pd_canonical.cbm` and `models/pd_canonical_calibrator.pkl` are now
  byte-copies of the April search candidate
  (`models/search_pd/pd-hpo-local-2026-04-03-1325`), the exact binaries that
  produced the frozen conformal intervals and the funded-set certificate
  (drift harness: 0.0 across all columns). The previous canonical files were
  later retrains of the same config that never fed the paper's certificate.
- `data/processed/test_predictions.parquet` rebuilt from that bundle via the
  new `scripts/rebuild_test_predictions_from_frozen.py` (hard assert:
  `pd_calibrated` equals the frozen intervals' `y_pred` exactly).
- Paper-facing PD metrics now come from the certificate lineage:
  AUC `0.7127 -> 0.7139`, Brier `0.1546 -> 0.1544`, ECE `0.0062 -> 0.0070`
  (table0, paper body/tex, book chapters). The exact certificate
  (`$170,464.54`, `V=0.028875`, `Gamma_CP=0.187987`, `45/45`) is unchanged.
- `crpto_tableA5/A9/A10` re-frozen under the current locked stack (their
  committed versions were generated in an unrecoverable environment);
  `crpto_tableA7/A8` deliberately NOT regenerated — they remain the frozen
  per-loan view of the certificate funded set (LP re-solves are degenerate).
- `EXTRACTION_MANIFEST.json` gains an `april_lineage_unification` block and
  14 refreshed hashes; environment-leak paths removed from
  `models/threshold_semantics.json` and `models/mrm_report_status.json`.

### Removed (R0 cleanup, 2026-06-12)
- Second dead-code pass, verified zero references across src/scripts/tests/
  book/docs/notebooks: `src/data/build_datasets.py`, `src/utils/mlflow_utils.py`,
  `src/models/conformal_registry.py`, and `src/models/_mapie_compat.py`
  (created during the drift-gate work but never adopted by any call site).
- `_policy_match`/`_policy_matches` consolidated from three scripts into
  `src/utils/script_helpers.policy_matches` with parametrizable field tuples;
  regenerated tables remained bit-exact.

### Removed
- Dead modules with no imports anywhere in the repo:
  `src/evaluation/encoding_stability.py`, `src/evaluation/monotonicity.py`,
  `src/evaluation/slicing_functions.py`, `src/optimization/sda.py`,
  `src/optimization/spo_integration.py`. The frozen audit artefacts they
  once produced (`models/encoding_stability_status.json`,
  `models/monotonicity_audit_status.json`) remain committed and are still
  consumed by `scripts/generate_mrm_report.py` and the book.

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
