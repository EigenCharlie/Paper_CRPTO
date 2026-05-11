# MAPIE 0.9 → 1.x migration plan

**Status**: Documented, not executed. Requires drift validation against the
frozen champion conformal artefact.

## Context

MAPIE 1.0 rewrote the public API:

- `MapieRegressor` / `MapieClassifier` → `SplitConformalRegressor`,
  `CrossConformalRegressor`, `SplitConformalClassifier` (and
  `CrossConformalClassifier`).
- `MondrianCP` becomes a standalone wrapper instead of an argument.
- The conformity score selection moved from string `method=` arguments to
  explicit `conformity_score=` objects.

`pyproject.toml` already pins `mapie>=1.4` and `uv.lock` records `1.4.0`, so
the runtime is on MAPIE 1.x. However `src/models/conformal.py` and
`scripts/generate_conformal_intervals.py` still use the 0.9 call style. The
1.x library accepts the legacy classes for a deprecation window (which is
why nothing is broken today), but the deprecation warnings are visible and
we cannot rely on them remaining a no-op forever.

## Why it was not executed in the bootstrap

The champion's conformal artefact
`data/processed/conformal_intervals_mondrian.parquet` was generated under
MAPIE 0.9 with very specific quantile/scoring choices. Switching to the 1.x
API can change numerical results by `~1e-6` even with identical seeds because
default conformity score families changed (`absolute_residual` → `absolute`,
`apsbinary` → `aps`, …). Any drift invalidates the run tag
`paper-thesis-final-economic-2026-04-06`.

The deny-list in `.claude/settings.json` blocks `dvc repro
crpto.conformal.intervals` for exactly this reason.

## Acceptance criteria

Execute the migration when ALL of the following can be verified:

1. **Compatibility shim ready.** Wrap the old call sites in a thin adapter
   so the diff focuses on imports rather than logic:

   ```python
   # src/models/_mapie_compat.py
   try:
       from mapie.regression import SplitConformalRegressor  # 1.x
       from mapie.classification import SplitConformalClassifier
   except ImportError:  # pragma: no cover
       from mapie.regression import MapieRegressor as SplitConformalRegressor
       from mapie.classification import MapieClassifier as SplitConformalClassifier
   ```

2. **Drift harness.** Add `tests/test_models/test_conformal_mapie_drift.py`
   that loads `conformal_intervals_mondrian.parquet`, recomputes the
   intervals against MAPIE 1.x with the same seed, and asserts max abs diff
   ≤ `1e-6` per loan and coverage delta ≤ `5e-4` per Mondrian cell.

3. **Run on a branch.** `feat/mapie-1.x-migration`. Re-run
   `crpto.conformal.intervals` and `crpto.conformal.validation` outside
   `main`. Compare `models/conformal_policy_status.json` before/after.

4. **MRM sign-off.** If drift exceeds tolerance, the change is *not* a
   refactor — it is a model change and needs a fresh run-tag.

## Patch shape (preview)

```python
# Before (MAPIE 0.9 style)
from mapie.regression import MapieRegressor
mapie = MapieRegressor(estimator, method="plus", cv=5)
mapie.fit(X_cal, y_cal)
y_pred, y_pis = mapie.predict(X_test, alpha=0.1)

# After (MAPIE 1.x style)
from mapie.regression import SplitConformalRegressor
from mapie.conformity_scores import AbsoluteConformityScore
mapie = SplitConformalRegressor(
    estimator=estimator,
    conformity_score=AbsoluteConformityScore(),
    confidence_level=0.9,
)
mapie.fit_conformalize(X_cal, y_cal)
y_pred, y_pis = mapie.predict_interval(X_test)
```

## Timing

Pair with the conformal module refactor (see `CONFORMAL_REFACTOR_PLAN.md`).
Both touch `src/models/conformal.py` and benefit from a single drift
validation pass.
