"""Book helpers — artifact loading and plotting utilities for Quarto chunks.

Re-exports the most commonly used functions so chapters can write simply::

    from book._helpers import load_json, load_parquet, PALETTE, apply_publication_style

without dipping into submodules. For less common helpers, import directly from
``book._helpers.load_artifacts`` or ``book._helpers.plot_helpers``.
"""

from __future__ import annotations

from .load_artifacts import (
    CONFIGS_DIR,
    DATA_DIR,
    MODEL_DIR,
    NOTEBOOK_IMAGE_DIR,
    PUBLICATION_FIGURES_DIR,
    REPO_ROOT,
    REPORTS_DIR,
    load_parquet,
    try_load_parquet,
)
from .plot_helpers import PALETTE

# Optional: bring publication-style helpers if present.
try:
    from .plot_helpers import apply_publication_style  # type: ignore
except ImportError:  # pragma: no cover
    apply_publication_style = None  # type: ignore

# Optional JSON loader (some chapters expect it from the unified namespace).
try:
    from .load_artifacts import load_json  # type: ignore
except ImportError:  # pragma: no cover
    import json
    from pathlib import Path

    def load_json(name: str) -> dict:  # type: ignore[no-redef]
        """Fallback JSON loader. Resolves ``name`` against repo root or DATA_DIR."""
        candidates = [
            REPO_ROOT / name,
            REPO_ROOT / f"{name}.json",
            DATA_DIR / name,
            DATA_DIR / f"{name}.json",
            MODEL_DIR / name,
            MODEL_DIR / f"{name}.json",
        ]
        for c in candidates:
            if c.is_file():
                return json.loads(Path(c).read_text(encoding="utf-8"))
        raise FileNotFoundError(name)


__all__ = [
    "CONFIGS_DIR",
    "DATA_DIR",
    "MODEL_DIR",
    "NOTEBOOK_IMAGE_DIR",
    "PALETTE",
    "PUBLICATION_FIGURES_DIR",
    "REPORTS_DIR",
    "REPO_ROOT",
    "apply_publication_style",
    "load_json",
    "load_parquet",
    "try_load_parquet",
]
