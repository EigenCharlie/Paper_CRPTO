"""Compatibility surface for MAPIE imports.

The CRPTO runtime pins ``mapie>=1.4`` and ``src/models/conformal.py`` already
uses the 1.x public class names, so the fallback branch below should never
trigger in a synced environment. The shim exists so that every MAPIE class
used by the project is imported from one place: when MAPIE 2.x renames the
public API again, only this module and its drift gate
(``tests/test_models/test_conformal_mapie_drift.py``) need to change.

Note that the frozen champion conformal artifact
(``data/processed/conformal_intervals_mondrian.parquet``) is produced by the
Mondrian path in ``create_pd_intervals_mondrian``, which computes split
conformal quantiles with plain numpy and does not depend on these classes.
The MAPIE classes back the global-split baseline, regression intervals,
classification sets, cross-conformal, and Venn-Abers helpers.
"""

from __future__ import annotations

try:  # MAPIE >= 1.0
    from mapie.classification import SplitConformalClassifier
    from mapie.regression import CrossConformalRegressor, SplitConformalRegressor
except ImportError:  # pragma: no cover - MAPIE 0.9 fallback, runtime pins >=1.4
    from mapie.classification import MapieClassifier as SplitConformalClassifier
    from mapie.regression import MapieRegressor as SplitConformalRegressor

    CrossConformalRegressor = None  # type: ignore[assignment]

__all__ = [
    "CrossConformalRegressor",
    "SplitConformalClassifier",
    "SplitConformalRegressor",
]
