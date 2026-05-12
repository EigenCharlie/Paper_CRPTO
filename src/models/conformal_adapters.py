"""sklearn-style adapter classes for the conformal stack.

This module was split out of ``src/models/conformal.py`` to make the
monolithic file shorter and easier to navigate. The three classes here are
exactly the ones the frozen ``models/pd_canonical_calibrator.pkl`` (and any
older calibrator pickles) reference by their fully-qualified
``src.models.conformal.<ClassName>`` path.

To keep those pickles working without re-pickling, every class below sets
its ``__module__`` attribute back to ``"src.models.conformal"`` after
definition. ``conformal.py`` then re-imports each class so the public name
is reachable at both ``src.models.conformal.<ClassName>`` (the legacy path)
and ``src.models.conformal_adapters.<ClassName>`` (the new home).

Pickle behaviour:

* ``pickle.load`` on a pre-refactor pickle resolves
  ``src.models.conformal.ProbabilityRegressor`` to the re-exported name in
  ``conformal.py``, which points to the class here.
* ``pickle.dump`` of a freshly constructed instance writes
  ``src.models.conformal.ProbabilityRegressor`` because of the
  ``__module__`` override, so future loads remain stable.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

# Canonical module path that pickled instances must report.
_PICKLE_MODULE = "src.models.conformal"


class ProbabilityRegressor(BaseEstimator, RegressorMixin):
    """Wrap classifier predict_proba as a regression predictor.

    Optionally applies a probability calibrator after raw predictions.
    """

    def __init__(self, classifier, calibrator: Any | None = None) -> None:
        self.classifier = classifier
        self.calibrator = calibrator
        self.is_fitted_ = True  # required for MAPIE prefit checks

    def fit(self, X, y):
        """Already fitted — no-op for MAPIE interface."""
        return self

    def predict(self, X):
        """Return calibrated P(default) in [0, 1]."""
        # Local import keeps the heavy ``apply_probability_calibrator`` lazy
        # and avoids a circular import between ``conformal`` and this module.
        from src.models.conformal import apply_probability_calibrator

        raw = self.classifier.predict_proba(X)[:, 1]
        return apply_probability_calibrator(self.calibrator, raw)


class PrefitClassifierAdapter(BaseEstimator):
    """Small sklearn-style adapter for prefit classifiers inside MAPIE checks."""

    def __init__(self, classifier, n_features_in: int | None = None) -> None:
        self.classifier = classifier
        classes = getattr(classifier, "classes_", np.array([0, 1]))
        self.classes_ = np.asarray(classes)
        self.n_features_in_ = int(n_features_in or getattr(classifier, "n_features_in_", 0) or 0)
        self.feature_names_in_ = np.asarray(
            [f"f{i}" for i in range(self.n_features_in_)], dtype=object
        )
        self.is_fitted_ = True

    def fit(self, X, y):
        return self

    def _is_minimal_probe(self, X: pd.DataFrame) -> bool:
        if X.shape[0] != 1 or X.shape[1] != self.n_features_in_:
            return False
        numeric = X.apply(pd.to_numeric, errors="coerce")
        return bool(
            np.isfinite(numeric.to_numpy()).all() and np.allclose(numeric.to_numpy(), 0.0)
        )

    def predict(self, X):
        X_df = pd.DataFrame(X) if not isinstance(X, pd.DataFrame) else X
        if self._is_minimal_probe(X_df):
            return np.zeros(len(X_df), dtype=int)
        return self.classifier.predict(X_df)

    def predict_proba(self, X):
        X_df = pd.DataFrame(X) if not isinstance(X, pd.DataFrame) else X
        if self._is_minimal_probe(X_df):
            return np.column_stack([np.ones(len(X_df)), np.zeros(len(X_df))])
        return self.classifier.predict_proba(X_df)


class PrefitCalibratedClassifierAdapter(PrefitClassifierAdapter):
    """Prefit classifier adapter that applies a probability calibrator."""

    def __init__(
        self,
        classifier,
        calibrator: Any | None = None,
        n_features_in: int | None = None,
    ) -> None:
        super().__init__(classifier, n_features_in=n_features_in)
        self.calibrator = calibrator

    def predict_proba(self, X):
        from src.models.conformal import apply_probability_calibrator

        raw = super().predict_proba(X)
        if self.calibrator is None:
            return raw
        p_pos = apply_probability_calibrator(self.calibrator, raw[:, 1])
        p_neg = np.clip(1.0 - p_pos, 0.0, 1.0)
        return np.column_stack([p_neg, p_pos])


# ---------------------------------------------------------------------------
# Pickle compatibility shim: report the legacy fully-qualified path.
# ---------------------------------------------------------------------------
for _cls in (ProbabilityRegressor, PrefitClassifierAdapter, PrefitCalibratedClassifierAdapter):
    _cls.__module__ = _PICKLE_MODULE
