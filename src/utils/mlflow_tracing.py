"""MLflow 3 helpers — Datasets API + Tracing + structured tags.

This module is purely **additive**: existing scripts that call ``mlflow.log_*``
directly keep working. The helpers below give new code a thin, opinionated
wrapper that:

* registers an input parquet as a hashed :class:`mlflow.data.Dataset` so runs
  remain traceable to bytes-exact files (``digest`` is a SHA256 of the file
  contents);
* exposes ``@trace`` as a decorator that no-ops when MLflow tracing is
  unavailable (e.g. running offline on a developer machine);
* applies the same ``paper.*`` tag schema CRPTO uses for the frozen champion
  (``run_tag``, ``section``, ``policy``) so dashboards stay coherent across
  experiments.

Nothing here touches the champion artefacts: every function logs to whatever
MLflow tracking URI is configured (DagsHub by default — see ``.env.example``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T", bound=Callable[..., Any])

try:  # pragma: no cover — exercised only when mlflow is installed.
    import mlflow
    from mlflow.data.pandas_dataset import PandasDataset
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]
    PandasDataset = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Hashing & dataset registration
# ---------------------------------------------------------------------------


def _sha256_of_file(path: Path, chunk_size: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def register_parquet_dataset(
    parquet_path: str | Path,
    *,
    name: str | None = None,
    targets: str | None = None,
    context: str = "training",
) -> Any:
    """Log a parquet input to the active MLflow run with a SHA256 ``digest``.

    Returns the dataset object (or ``None`` if MLflow is not installed) so
    callers can attach it to ``mlflow.evaluate``.
    """
    if mlflow is None or PandasDataset is None:
        return None
    import pandas as pd  # local import keeps base deps light.

    path = Path(parquet_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = _sha256_of_file(path)[:16]
    df = pd.read_parquet(path)
    dataset = mlflow.data.from_pandas(
        df,
        source=str(path),
        name=name or path.stem,
        digest=digest,
        targets=targets,
    )
    mlflow.log_input(dataset, context=context)
    return dataset


# ---------------------------------------------------------------------------
# Tracing (MLflow 3) — no-op fallback when not available
# ---------------------------------------------------------------------------


def trace(name: str | None = None) -> Callable[[T], T]:
    """Decorator that wraps a function in an ``mlflow.trace`` span when possible."""

    def decorator(fn: T) -> T:
        if mlflow is None or not hasattr(mlflow, "trace"):
            return fn
        try:  # pragma: no cover — depends on installed MLflow version.
            return mlflow.trace(name=name or fn.__name__)(fn)  # type: ignore[attr-defined]
        except Exception:
            return fn

    return decorator


# ---------------------------------------------------------------------------
# Tag conventions
# ---------------------------------------------------------------------------

PAPER_RUN_TAG = "paper-thesis-final-economic-2026-04-06"


def set_paper_tags(
    *,
    run_tag: str = PAPER_RUN_TAG,
    section: str | None = None,
    policy: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Apply the CRPTO ``paper.*`` tag schema to the currently active run.

    Falls back to ``mlflow.log_param`` when ``set_tag`` is not available
    (older client versions) and silently no-ops when MLflow is missing.
    """
    if mlflow is None:
        return
    tags: dict[str, Any] = {"paper.run_tag": run_tag}
    if section is not None:
        tags["paper.section"] = section
    if policy is not None:
        tags["paper.policy"] = policy
    if extra:
        for k, v in extra.items():
            tags[f"paper.{k}"] = v
    try:
        mlflow.set_tags(tags)
    except Exception:  # pragma: no cover
        for k, v in tags.items():
            mlflow.log_param(k, v)


# ---------------------------------------------------------------------------
# Context manager for a tagged run
# ---------------------------------------------------------------------------


@contextmanager
def paper_run(
    run_name: str,
    *,
    section: str | None = None,
    policy: str | None = None,
    run_tag: str = PAPER_RUN_TAG,
    nested: bool = False,
) -> Any:
    """Start an MLflow run with the CRPTO paper tag schema applied.

    Yields the active run (or ``None`` when MLflow is unavailable).
    """
    if mlflow is None:
        yield None
        return
    with mlflow.start_run(run_name=run_name, nested=nested) as run:
        set_paper_tags(run_tag=run_tag, section=section, policy=policy)
        yield run
