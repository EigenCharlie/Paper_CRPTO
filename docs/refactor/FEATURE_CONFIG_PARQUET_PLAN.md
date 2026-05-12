# `feature_config.pkl` → Parquet + schema migration plan

**Status**: YAML dual-write and reader migration are partially executed. The
pipeline still preserves `feature_config.pkl`, but
`src/features/feature_config_io.py` can read/write the YAML companion and the
main PD/conformal consumers prefer YAML when present, with pickle fallback.
The full Parquet/dataclass replacement remains deferred because it cascades
through `crpto.data.features` and downstream.

## Context

`data/processed/feature_config.pkl` is a Python pickle produced by
`scripts/materialize_feature_artifacts.py` and consumed by every script
that needs the feature encoding (WoE bins, monotone constraints, dtype
hints, training feature order). Pickles have well-known portability and
security drawbacks:

- The class types and module paths are baked in. Any rename in `src/features`
  breaks deserialisation.
- Reviewers cannot inspect the artefact without running Python.
- Pickles can execute arbitrary code on load, which trips automated
  security scanners (Bandit's `B301`).

## Target representation

Two artefacts replacing the single pickle:

1. **`data/processed/feature_config.parquet`** — the data tables that today
   live inside the pickle (binning rules, woe values, monotone constraint
   vectors). Schema declared via Pandera.
2. **`configs/feature_config.yml`** — the small scalar metadata (feature
   order, target column, calibration choice, training seed).

A loader helper:

```python
# src/features/feature_config_io.py
def load_feature_config(
    repo_root: Path | None = None,
) -> FeatureConfig:
    """Read Parquet + YAML and reconstruct the FeatureConfig dataclass."""
```

`FeatureConfig` becomes a `@dataclass(frozen=True)` instead of an arbitrary
pickled object — easier to type-check, diff in PRs, and serialise.

## Why it was not executed in the bootstrap

`scripts/materialize_feature_artifacts.py` is a stage in `dvc.yaml`:

```yaml
crpto.data.features:
  cmd: python scripts/materialize_feature_artifacts.py --config configs/crpto_pd_model.yaml
  outs:
    - data/processed/train_fe.parquet
    - data/processed/test_fe.parquet
    - data/processed/calibration_fe.parquet
```

Changing the output format triggers a re-run of every downstream stage,
including `crpto.pd.champion` and `crpto.conformal.intervals` — exactly the
stages on the deny-list. Migrating without re-runs requires writing the new
format alongside the legacy `.pkl` for one cycle.

## Acceptance criteria

1. **Dual-write phase.** `materialize_feature_artifacts.py` writes BOTH
   `.pkl` (legacy) and `.parquet` + `.yml` (new) on every run for one
   release cycle. Consumers keep reading the pickle.

2. **Reader migration.** Each consumer adds a fallback:

   ```python
   try:
       cfg = load_feature_config_parquet(...)
   except FileNotFoundError:
       cfg = joblib.load("data/processed/feature_config.pkl")
   ```

   Switch the preferred path to Parquet+YAML.

3. **Round-trip test.** Pickled config and Parquet+YAML config must be
   semantically identical on the existing champion. Compare via
   `dataclass.asdict()` on the deserialised objects.

4. **Drop the pickle.** Once all consumers have moved, remove the
   `.pkl` write and the fallback branch. New champion run-tag captures the
   change.

## Risks

- Schema gaps: some legacy pickles store scikit-learn objects (encoders,
  fitted transformers). Parquet cannot serialise those directly. Two
  options: keep them inside a small companion `.joblib` blob inside
  `data/processed/` (only the fitted estimators), or refit them on demand.
- Determinism: the order of WoE bins iterates over a Python `dict` in the
  legacy code. Confirm that the Parquet variant preserves the iteration
  order or wraps it explicitly.

## Timing

Schedule together with the MAPIE migration and the conformal split — all
three sit in the same "freshen the champion" window.
