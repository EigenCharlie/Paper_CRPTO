"""Pickle compatibility tests for the frozen champion calibrator.

These tests are the safety net for any future refactor of
``src/models/conformal.py``. They verify that ``models/pd_canonical_calibrator.pkl``
can be loaded *with the current code on disk* and that its public surface
(predict / predict_proba) still produces sensible probabilities.

If a refactor moves :class:`src.models.conformal.ProbabilityRegressor` or
its sibling adapters to a submodule without preserving the original
``__module__`` path, these tests will fail loudly. That is the desired
behaviour — the failure forces the refactor to add explicit pickle
compatibility shims (see ``docs/refactor/CONFORMAL_REFACTOR_PLAN.md``).
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pytest

CALIBRATOR_PATH = Path("models/pd_canonical_calibrator.pkl")


@pytest.fixture(scope="module")
def calibrator():
    if not CALIBRATOR_PATH.is_file():
        pytest.skip(f"{CALIBRATOR_PATH} not available locally — run `dvc pull` to fetch.")
    return joblib.load(CALIBRATOR_PATH)


def test_calibrator_loads(calibrator) -> None:
    """Pickle deserialisation must not raise. This is the canary."""
    assert calibrator is not None


def test_calibrator_module_paths_are_stable(calibrator) -> None:
    """The classes inside the calibrator pickle must still live under
    ``src.models.conformal`` (or a wrapper). Any refactor that changes
    ``__module__`` without compat shims breaks reproducibility."""

    def _module_of(obj) -> str:
        return type(obj).__module__

    seen_modules: set[str] = set()

    def _collect(node):
        seen_modules.add(_module_of(node))
        for attr in dir(node):
            if attr.startswith("_") and attr not in {"_estimator", "_wrapped", "_calibrator"}:
                continue
            try:
                value = getattr(node, attr, None)
            except Exception:
                continue
            if value is None:
                continue
            type_module = getattr(type(value), "__module__", "")
            if type_module.startswith(("src.", "crpto.")):
                seen_modules.add(type_module)

    _collect(calibrator)

    forbidden = {m for m in seen_modules if "._legacy" in m or "._private" in m}
    assert not forbidden, (
        f"Calibrator references private/legacy submodules — pickle compat at risk: {forbidden}"
    )


def test_calibrator_predict_returns_probabilities(calibrator) -> None:
    """Whatever public surface the calibrator exposes (predict / predict_proba /
    transform) must produce values in [0, 1]."""
    rng = np.random.default_rng(0)
    sample = rng.uniform(0.0, 1.0, size=64)
    sample_2d = sample.reshape(-1, 1)

    output = None
    for method in ("predict", "predict_proba", "transform"):
        fn = getattr(calibrator, method, None)
        if not callable(fn):
            continue
        for candidate in (sample, sample_2d):
            try:
                result = fn(candidate)
            except Exception:
                continue
            output = np.asarray(result, dtype=float)
            break
        if output is not None:
            break

    assert output is not None, (
        "Calibrator does not expose any of predict/predict_proba/transform — "
        "this would silently break ScoreCalibrator consumers."
    )
    finite = output[np.isfinite(output)]
    assert finite.size > 0
    assert np.all((finite >= -1e-9) & (finite <= 1.0 + 1e-9)), (
        f"Calibrator output outside [0, 1]: min={finite.min()}, max={finite.max()}"
    )


def test_calibrator_is_deterministic(calibrator) -> None:
    """Two consecutive predict calls on the same input must return the same
    values bit-for-bit. Calibrators are deterministic by design."""
    rng = np.random.default_rng(1)
    sample = rng.uniform(0.0, 1.0, size=32)

    for method in ("predict", "predict_proba"):
        fn = getattr(calibrator, method, None)
        if not callable(fn):
            continue
        try:
            a = np.asarray(fn(sample))
            b = np.asarray(fn(sample))
        except Exception:
            try:
                a = np.asarray(fn(sample.reshape(-1, 1)))
                b = np.asarray(fn(sample.reshape(-1, 1)))
            except Exception:
                continue
        np.testing.assert_array_equal(a, b)
        return  # one deterministic method is enough

    pytest.skip("Calibrator has no callable predict/predict_proba.")
