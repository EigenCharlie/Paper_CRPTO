"""Tests for ``src.utils.optuna_storage``.

Exercise URL resolution and journal fallback without spinning up Optuna trials.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils import optuna_storage


def test_is_journal_url_recognises_prefixes() -> None:
    assert optuna_storage._is_journal_url("journal:/tmp/x.log")
    assert optuna_storage._is_journal_url("journal+file:/tmp/x.log")
    assert optuna_storage._is_journal_url("journalfile:/tmp/x.log")
    assert not optuna_storage._is_journal_url("sqlite:///tmp/x.db")
    assert not optuna_storage._is_journal_url("postgresql://u:p@h/db")


@pytest.mark.parametrize(
    ("url", "expected_suffix"),
    [
        ("journal:/tmp/x.log", "tmp/x.log"),
        ("journal:tmp/x.log", "tmp/x.log"),
        ("journal+file:/foo/y.log", "foo/y.log"),
        ("journalfile:foo/y.log", "foo/y.log"),
    ],
)
def test_journal_path_from_url(url: str, expected_suffix: str) -> None:
    out = optuna_storage._journal_path_from_url(url)
    assert out.endswith(expected_suffix)


def test_make_storage_journal_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No env var ⇒ JournalStorage under <directory>/<study>.log."""
    monkeypatch.delenv("OPTUNA_STORAGE", raising=False)
    storage = optuna_storage.make_storage("smoke_study", directory=tmp_path)
    # We don't import JournalStorage at module level to avoid version coupling.
    assert storage.__class__.__name__ in {"JournalStorage", "RDBStorage"}


def test_make_storage_env_journal_url_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "explicit.log"
    monkeypatch.setenv("OPTUNA_STORAGE", f"journal:{target}")
    storage = optuna_storage.make_storage("ignored_when_env_present")
    assert storage.__class__.__name__ in {"JournalStorage", "RDBStorage"}


def test_make_storage_explicit_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPTUNA_STORAGE", raising=False)
    db_dir = tmp_path / "optuna"
    db_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    storage = optuna_storage.make_storage("sqlite_smoke", backend="sqlite")
    assert storage.__class__.__name__ == "RDBStorage"


def test_make_study_returns_study(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end smoke: a TPE study can be created. Uses in-memory storage to
    avoid Windows symlink-lock issues — the journal path itself is exercised in
    other tests via :func:`make_storage`."""
    monkeypatch.delenv("OPTUNA_STORAGE", raising=False)
    monkeypatch.setattr(optuna_storage, "DEFAULT_JOURNAL_DIR", tmp_path)

    # Patch make_storage to return an in-memory store for this smoke test.
    import optuna

    monkeypatch.setattr(
        optuna_storage,
        "make_storage",
        lambda *_, **__: optuna.storages.InMemoryStorage(),
    )

    study = optuna_storage.make_study(name="smoke", direction="maximize", pruner="none")
    assert study.study_name == "smoke"
    assert study.sampler is not None
