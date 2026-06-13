"""Stable Venn-Abers calibration helpers for canonical PD artifacts.

## Audit note (C15, 2026-05-10)

The original review wondered whether this custom wrapper duplicated logic
that the upstream ``venn-abers`` (PyPI) package already covers. After
inspection the answer is **no** — :class:`VennAbersScoreCalibrator` is a thin
~50 LOC interface adapter, not a re-implementation of the Venn-Abers
calibration algorithm. The actual math lives in ``venn_abers.VennAbers``,
which we delegate to inside ``fit`` and ``_predict_bounds``.

What this wrapper adds on top of the upstream class:

1. Accepts a **1-D vector of raw probabilities** ``y_prob_raw`` and
   internally expands it to the ``[p0, p1]`` binary matrix the upstream
   ``VennAbers.fit`` and ``.predict_proba`` expect. CRPTO calibrates from
   CatBoost ``predict_proba(...)[:, 1]`` slices, which are 1-D by design.
2. Returns a **point estimate** (mean of the bounds) via ``predict`` while
   preserving access to the raw bounds via ``_predict_bounds``. Other
   calibrators in the project (Platt sigmoid, isotonic) expose the same
   ``predict``/``predict_proba`` surface, so keeping that contract keeps
   ``models/pd_canonical_calibrator.pkl`` interchangeable with the rest of
   the pipeline.
3. Clips bounds into ``[0, 1]`` defensively (upstream occasionally emits
   ``1.0 + epsilon`` from floating point).
4. Sorts ``p_bounds`` so callers cannot rely on ``[lo, hi]`` ordering when
   the upstream returns ``[hi, lo]`` for very small calibration sets.

Decision: **keep the wrapper.** Removing it would force every call site
(``pd_pipeline.py``, calibration scripts, MRM card generation) to repeat the
1-D → 2-D expansion and the contract adaptation. The wrapper is also part
of the frozen champion's calibrator pickle, so replacing it would invalidate
``models/pd_canonical_calibrator.pkl``.

Future work, if and when the calibrator is re-trained:

- Consider folding this class into ``src/models/calibration.py`` alongside
  the Platt/Isotonic wrappers so all calibrators live in one module.
- Add a ``predict_intervals`` method that returns ``(low, high)`` directly
  for downstream conformal pipelines (today they go through the private
  ``_predict_bounds``).
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np


class VennAbersScoreCalibrator:
    """Score-based Venn-Abers calibrator over 1D raw probabilities.

    Thin adapter around ``venn_abers.VennAbers``. See module docstring for
    the audit notes and rationale for keeping the wrapper.
    """

    def __init__(self) -> None:
        self._wrapped: Any = None
        self._is_fitted = False

    @staticmethod
    def _as_binary_proba(y_prob_raw: np.ndarray) -> np.ndarray:
        p1 = np.clip(np.asarray(y_prob_raw, dtype=float).reshape(-1), 0.0, 1.0)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def fit(self, y_prob_raw: np.ndarray, y_true: np.ndarray) -> VennAbersScoreCalibrator:
        from venn_abers import VennAbers

        X = self._as_binary_proba(y_prob_raw)
        y = np.asarray(y_true, dtype=int)
        wrapped = VennAbers()
        wrapped.fit(X, y)
        self._wrapped = wrapped
        self._is_fitted = True
        return self

    def _predict_bounds(self, y_prob_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if not self._is_fitted or self._wrapped is None:
            raise RuntimeError("VennAbersScoreCalibrator is not fitted.")
        X = self._as_binary_proba(y_prob_raw)
        _, p_bounds = self._wrapped.predict_proba(X)
        p0 = np.clip(np.asarray(p_bounds[:, 0], dtype=float), 0.0, 1.0)
        p1 = np.clip(np.asarray(p_bounds[:, 1], dtype=float), 0.0, 1.0)
        low = np.minimum(p0, p1)
        high = np.maximum(p0, p1)
        return low, high

    def predict(self, y_prob_raw: np.ndarray) -> np.ndarray:
        low, high = self._predict_bounds(y_prob_raw)
        return cast(np.ndarray, np.clip((low + high) / 2.0, 0.0, 1.0))

    def predict_proba(self, y_prob_raw: np.ndarray) -> np.ndarray:
        p1 = self.predict(y_prob_raw)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict_intervals(self, y_prob_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Public accessor for the ``(low, high)`` Venn-Abers bounds.

        Added to remove the need for downstream conformal code to dip into
        the private ``_predict_bounds``.
        """
        return self._predict_bounds(y_prob_raw)
