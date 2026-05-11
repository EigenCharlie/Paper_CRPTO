# Refactor plan — `src/models/conformal.py`

**Status**: Documented, not executed. Requires a champion-aware migration window.

## Context

`src/models/conformal.py` is 845 LOC and exposes 18 public functions plus
3 classes. The original review (plan §6, item 4) flagged it as a "monolithic
module" worth splitting into focused submodules. This document captures the
proposed structure, the constraints that prevented an in-place refactor in
the bootstrap commit, and the green-light criteria for executing it later.

## Why it was not refactored in the bootstrap

`models/pd_canonical_calibrator.pkl` (the frozen champion's calibrator) is a
pickle that stores the **fully-qualified module path** of every class it
serialises. The pickle very likely references
`src.models.conformal.ProbabilityRegressor` and
`src.models.conformal.PrefitClassifierAdapter`. Moving those classes to a
submodule changes their `__module__` attribute, which breaks `pickle.load`
of the existing artefact, which in turn invalidates the run tag
`paper-thesis-final-economic-2026-04-06`.

Verifying that the move is pickle-safe requires either:

1. Loading the calibrator, re-pickling under the new namespace, and
   comparing predictions bit-for-bit on `data/processed/calibration_fe.parquet`,
   or
2. Re-running the `crpto.pd.champion` stage with the new module layout and
   confirming the new SHA256 in `EXTRACTION_MANIFEST.json` matches.

Neither option is in scope for the bootstrap commit because the champion is
frozen and the DVC stage is on the deny-list of `.claude/settings.json`.

## Proposed structure

```
src/models/conformal/
├── __init__.py          # re-export everything for backwards-compat
├── _adapters.py         # ProbabilityRegressor, PrefitClassifierAdapter,
│                        # PrefitCalibratedClassifierAdapter
├── _scores.py           # _conformal_quantile, _resolve_score_scale_family,
│                        # _compute_score_scale
├── pd_intervals.py      # create_pd_intervals, create_pd_intervals_mondrian,
│                        # create_pd_intervals_venn_abers,
│                        # conditional_coverage_by_group,
│                        # apply_probability_calibrator
├── regression.py        # create_regression_intervals, create_residual_intervals
├── classification.py    # create_classification_sets,
│                        # _create_margin_classification_sets,
│                        # summarize_prediction_sets,
│                        # create_classification_sets_mondrian,
│                        # build_mondrian_partition_labels,
│                        # create_cross_conformal_score_intervals
└── diagnostics.py       # validate_coverage
```

`__init__.py` re-exports every public symbol so existing call sites keep
working:

```python
from ._adapters import (
    PrefitCalibratedClassifierAdapter,
    PrefitClassifierAdapter,
    ProbabilityRegressor,
)
from .classification import (
    build_mondrian_partition_labels,
    create_classification_sets,
    create_classification_sets_mondrian,
    create_cross_conformal_score_intervals,
    summarize_prediction_sets,
)
from .diagnostics import validate_coverage
from .pd_intervals import (
    apply_probability_calibrator,
    conditional_coverage_by_group,
    create_pd_intervals,
    create_pd_intervals_mondrian,
    create_pd_intervals_venn_abers,
)
from .regression import create_regression_intervals, create_residual_intervals
```

## Pickle compatibility strategy

When we are ready to execute the split:

1. **Pin pickle module aliases first.** Add to `src/models/conformal/__init__.py`:

   ```python
   import sys
   # Backwards-compat: pickles created before the split reference
   # ``src.models.conformal.ProbabilityRegressor`` directly. Keep that path
   # alive after the split.
   sys.modules.setdefault(
       "src.models.conformal", sys.modules[__name__]
   )
   ```

   This is a no-op for Python's normal import machinery but ensures pickle's
   `find_class` resolves the legacy fully-qualified name to the new package.

2. **Add a calibrator round-trip test** before any restructuring:

   ```python
   def test_calibrator_pickle_round_trip_after_refactor():
       import joblib
       cal = joblib.load("models/pd_canonical_calibrator.pkl")
       cal.predict(np.array([0.1, 0.5, 0.9]))  # must not raise
   ```

3. **Run on a non-champion branch** and compare predictions on
   `data/processed/test_predictions.parquet` for the first 1000 rows.
   Tolerance: bit-exact (numpy `array_equal`).

## Acceptance criteria

The refactor lands on `main` when ALL of the following are true:

- `tests/test_models/test_conformal*` (existing) — all green.
- A new `test_calibrator_pickle_round_trip` — green.
- `dvc status` against the frozen champion — clean (no drift).
- The first 1000 predictions of `test_predictions.parquet` — byte-exact
  match against the pre-refactor commit.

## Timing

Schedule for the next paper-iteration window when the champion can be
re-validated. Until then, the monolithic `conformal.py` remains the source
of truth.
