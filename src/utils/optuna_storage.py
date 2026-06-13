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


_JOURNAL_URL_PREFIXES = ("journal+file:", "journalfile:", "journal:")


def _is_journal_url(url: str) -> bool:
    return url.lower().startswith(_JOURNAL_URL_PREFIXES)


def _journal_path_from_url(url: str) -> str:
    """Strip the ``journal:`` prefix from a URL, returning the bare filesystem path."""
    for prefix in _JOURNAL_URL_PREFIXES:
        if url.lower().startswith(prefix):
            value = url[len(prefix) :]
            if value.startswith("///"):
                return "/" + value[3:]
            return value
    return url


def make_storage(
    study_name: str,
    *,
    backend: Literal["journal", "sqlite", "auto"] = "auto",
    directory: Path | None = None,
) -> optuna.storages.BaseStorage:
    """Return an Optuna storage backend appropriate for the current environment.

    Resolution order when ``backend="auto"``:

    1. If ``OPTUNA_STORAGE`` is set and starts with ``journal:`` (or
       ``journal+file:``, ``journalfile:``), use :class:`JournalFileStorage`.
    2. Else if ``OPTUNA_STORAGE`` is set with any RDB URL, hand it to
       :class:`optuna.storages.RDBStorage` directly so callers can configure
       SQLite/PostgreSQL/MySQL via env var without code changes.
    3. Otherwise, fall back to JournalStorage with a per-study log under
       ``data/processed/optuna/<study>.log``.
    """
    env_url = os.environ.get("OPTUNA_STORAGE", "").strip()
    if backend == "auto" and env_url:
        if _is_journal_url(env_url):
            journal_path = Path(_journal_path_from_url(env_url))
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Using OPTUNA_STORAGE journal file: {}", journal_path)
            return _make_journal_storage(journal_path, study_name=study_name)
        logger.info("Using OPTUNA_STORAGE RDB URL: {}", env_url)
        return optuna.storages.RDBStorage(env_url)

    if backend == "sqlite":
        url = env_url or f"sqlite:///data/processed/optuna/{study_name}.db"
        Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
        return optuna.storages.RDBStorage(url)

    journal_path = _resolve_journal_path(study_name, directory=directory)
    return _make_journal_storage(journal_path, study_name=study_name)


def _make_journal_storage(journal_path: Path, *, study_name: str) -> optuna.storages.BaseStorage:
    # Optuna 4 deprecated ``JournalFileStorage`` in favour of
    # ``optuna.storages.journal.JournalFileBackend``. On Windows, the default
    # symlink-based lock fails without admin privileges; use
    # ``JournalFileOpenLock`` (open-with-O_EXCL) when available.
    try:
        from optuna.storages import JournalStorage
        from optuna.storages.journal import JournalFileBackend
    except ImportError:
        try:
            # Optuna <4 fallback (legacy import path)
            from optuna.storages import (
                JournalFileStorage as JournalFileBackend,
                JournalStorage,
            )
        except ImportError:  # pragma: no cover — only fires on very old Optuna.
            logger.warning("Optuna JournalStorage unavailable; falling back to SQLite.")
            return make_storage(study_name, backend="sqlite")

    lock_obj: object | None = None
    try:
        from optuna.storages.journal import JournalFileOpenLock

        lock_obj = JournalFileOpenLock(str(journal_path))
    except ImportError:
        lock_obj = None

    if lock_obj is not None:
        backend_file = JournalFileBackend(str(journal_path), lock_obj=lock_obj)
    else:
        backend_file = JournalFileBackend(str(journal_path))
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
        wilcoxon_cls = getattr(optuna.pruners, "WilcoxonPruner", None)
        pruner_obj = wilcoxon_cls() if wilcoxon_cls else optuna.pruners.MedianPruner()
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
