# `feature_config.pkl` → Parquet + schema migration plan

**Status**: Executed as of 2026-06-13. The live pipeline now writes
`data/processed/feature_config.yml` plus
`data/processed/feature_config.parquet`, and no longer writes or tracks
`feature_config.pkl`. The downstream champion/conformal stages were re-keyed
without re-running CatBoost; `just drift-gate` stayed bit-exact.

## Context

`data/processed/feature_config.pkl` used to be a Python pickle produced by
`scripts/materialize_feature_artifacts.py` and consumed by scripts that need
the feature contract (feature order, categorical features, challenger pools
and IV scores). Pickles have well-known portability and security drawbacks:

- The class types and module paths are baked in. Any rename in `src/features`
  breaks deserialisation.
- Reviewers cannot inspect the artefact without running Python.
- Pickles can execute arbitrary code on load, which trips automated
  security scanners (Bandit's `B301`).

## Target representation

Two artefacts replaced the single pickle:

1. **`data/processed/feature_config.yml`** — the canonical human-readable
   mapping used by live consumers.
2. **`data/processed/feature_config.parquet`** — a long-form table with
   columns `section`, `kind`, `ordinal`, `key`, `value_json`, validated by a
   Pandera schema for reviewers and MRM inspection.

A loader helper:

```python
# src/features/feature_config_io.py
def load_feature_config(
    repo_root: Path | None = None,
) -> FeatureConfig:
    """Read YAML, Parquet, or an explicit legacy pickle audit path."""
```

The project kept the existing `dict[str, Any]` API because all live consumers
already expect dictionaries and the object contains no fitted transformers.
That is simpler than introducing a dataclass solely for this academic repo.

## Execution notes

`scripts/materialize_feature_artifacts.py` is a stage in `dvc.yaml`:

```yaml
crpto.data.features:
  cmd: python scripts/materialize_feature_artifacts.py --config configs/crpto_pd_model.yaml
  outs:
    - data/processed/train_fe.parquet
    - data/processed/test_fe.parquet
    - data/processed/calibration_fe.parquet
```

Changing the output format required one re-run of `crpto.data.features`. The
feature Parquets remained byte-identical, `feature_config.yml` kept its
existing SHA256, and only `feature_config.parquet` plus the JSON serialization
of `feature_manifest_v2.json` changed. The champion and conformal stages were
not reproduced; their DVC dep hashes were accepted with `dvc commit -f` after
`just drift-gate` showed zero numerical drift.

## Acceptance criteria

1. **Dual-write phase.** Completed before phase 4: YAML was written next to
   the pickle and consumers moved to YAML-first loading.

2. **Reader migration.** Each consumer adds a fallback:

   ```python
   try:
       cfg = load_feature_config_parquet(...)
   except FileNotFoundError:
       cfg = joblib.load("data/processed/feature_config.pkl")
   ```

   Completed. Live consumers now point at `feature_config.yml`; explicit
   `prefer="pickle"` remains only for legacy audits.

3. **Round-trip test.** Completed. Tests cover YAML/Parquet equivalence on the
   current frozen contract and retain a small explicit-pickle escape hatch.

4. **Drop the pickle.** Completed. `feature_config.pkl` is no longer a DVC out,
   no longer in `EXTRACTION_MANIFEST.json`, and is absent from the local
   `data/processed` checkout after `dvc checkout`.

## Risks

- Historical search scripts may still write pickle snapshots inside their
  external experiment bundles. That is separate from the live CRPTO feature
  contract and remains outside the frozen champion DAG.
- The Parquet table stores JSON values with explicit `ordinal` fields so list
  order is stable.

## Timing

Completed in the 2026-06-13 run-tag-approved cleanup window.
