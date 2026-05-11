from __future__ import annotations

from pathlib import Path

import yaml

LEGACY_BRAND = ["paper " + "estrella", "paper_" + "estrella", "paper-" + "estrella"]
LEGACY_PUBLIC = ["estrella" + "_fig", "paper1" + "_table", "paper1" + "_e2e"]


def public_files() -> list[Path]:
    roots = [Path("book"), Path("docs"), Path("reports"), Path("configs"), Path("tests")]
    files: list[Path] = [Path("README.md")]
    ignored_suffixes = {
        ".png",
        ".jpg",
        ".pdf",
        ".parquet",
        ".pkl",
        ".cbm",
        ".pyc",
    }
    for root in roots:
        if root.exists():
            files.extend(
                p
                for p in root.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix.lower() not in ignored_suffixes
            )
    return files


def test_quarto_book_lists_existing_chapters() -> None:
    cfg = yaml.safe_load(Path("book/_quarto.yml").read_text(encoding="utf-8"))
    chapters = list(_flatten_chapters(cfg["book"]["chapters"]))
    assert cfg["book"]["title"] == "CRPTO"
    for chapter in chapters:
        assert (Path("book") / chapter).exists(), chapter


def _flatten_chapters(entries: list[str | dict]) -> list[str]:
    chapters: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            chapters.append(entry)
        elif isinstance(entry, dict):
            chapters.extend(_flatten_chapters(entry.get("chapters", [])))
    return chapters


def test_public_branding_is_crpto_only() -> None:
    offenders: list[str] = []
    legacy = [token.lower() for token in [*LEGACY_BRAND, *LEGACY_PUBLIC]]
    for path in public_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(token in text for token in legacy):
            offenders.append(str(path))
    assert not offenders
