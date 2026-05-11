"""Optuna 4 storage helpers — JournalStorage with a SQLite fallback.

CRPTO sweeps (portfolio bound-aware search with 276k trials, conformal alpha
sweeps, CatBoost HPO) outgrew the default SQLite storage because writes become
the bottleneck. Optuna 4 ships a journal-based storage that is much faster for
write-heavy workloads.

Usage::

    from src.utils.optuna_storage import make_study

    study = make_study(
        name="pd_catboost_hpo",
        direction="maximize",
        sampler="tpe",
    )

The helper resolves the storage path from the ``OPTUNA_STORAGE`` env variable
when set, otherwise falls back to a journal file under
``data/processed/optuna/<study>.log``. SQLite remains available via the
``backend="sqlite"`` keyword.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import optuna
from loguru import logger

DEFAULT_JOURNAL_DIR = Path("data/processed/optuna")


def _resolve_journal_path(study_name: str, directory: Path | None = None) -> Path:
    base = directory if directory is not None else DEFAULT_JOURNAL_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{study_name}.log"


def make_storage(
    study_name: str,
    *,
    backend: Literal["journal", "sqlite", "auto"] = "auto",
    directory: Path | None = None,
) -> optuna.storages.BaseStorage:
    """Return an Optuna storage backend appropriate for the current environment.

    ``backend="auto"`` honours the ``OPTUNA_STORAGE`` env variable when set
    (any URL accepted by :func:`optuna.create_study`), otherwise uses
    JournalStorage (write-optimised).
    """
    env_url = os.environ.get("OPTUNA_STORAGE", "").strip()
    if backend == "auto" and env_url:
        logger.info("Using OPTUNA_STORAGE from environment: {}", env_url)
        return optuna.storages.RDBStorage(env_url)

    if backend == "sqlite":
        url = env_url or f"sqlite:///data/processed/optuna/{study_name}.db"
        Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
        return optuna.storages.RDBStorage(url)

    journal_path = _resolve_journal_path(study_name, directory=directory)
    try:
        # Optuna >=4.0 exposes JournalFileStorage; earlier versions need the
        # legacy JournalFileOpenLock backend. Import lazily to stay compatible.
        from optuna.storages import JournalFileStorage, JournalStorage  # type: ignore
    except ImportError:  # pragma: no cover — only fires on very old Optuna.
        logger.warning("Optuna JournalStorage unavailable; falling back to SQLite.")
        return make_storage(study_name, backend="sqlite", directory=directory)

    backend_file = JournalFileStorage(str(journal_path))
    return JournalStorage(backend_file)


def make_study(
    *,
    name: str,
    direction: Literal["maximize", "minimize"] = "maximize",
    sampler: Literal["tpe", "nsgaii", "random"] = "tpe",
    pruner: Literal["median", "wilcoxon", "none"] = "median",
    seed: int = 42,
    backend: Literal["journal", "sqlite", "auto"] = "auto",
    load_if_exists: bool = True,
) -> optuna.Study:
    """Create or load an Optuna study with sensible CRPTO defaults."""
    if sampler == "tpe":
        sampler_obj: optuna.samplers.BaseSampler = optuna.samplers.TPESampler(seed=seed)
    elif sampler == "nsgaii":
        sampler_obj = optuna.samplers.NSGAIISampler(seed=seed)
    else:
        sampler_obj = optuna.samplers.RandomSampler(seed=seed)

    if pruner == "median":
        pruner_obj: optuna.pruners.BasePruner = optuna.pruners.MedianPruner()
    elif pruner == "wilcoxon":
        try:
            pruner_obj = optuna.pruners.WilcoxonPruner()  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover — Optuna <4
            pruner_obj = optuna.pruners.MedianPruner()
    else:
        pruner_obj = optuna.pruners.NopPruner()

    storage = make_storage(name, backend=backend)
    return optuna.create_study(
        study_name=name,
        direction=direction,
        sampler=sampler_obj,
        pruner=pruner_obj,
        storage=storage,
        load_if_exists=load_if_exists,
    )
