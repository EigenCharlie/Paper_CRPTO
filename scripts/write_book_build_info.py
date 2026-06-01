from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "book" / "includes" / "_build-info.qmd"


def _git_value(*args: str, default: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or default


def main() -> None:
    commit = _git_value("rev-parse", "--short", "HEAD", default="local")
    branch = _git_value("branch", "--show-current", default="local")
    rendered_at = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d")

    TARGET.write_text(
        "\n".join(
            [
                "::: {.build-info}",
                f"Build: `{commit}` | Rama: `{branch}` | Actualizado: `{rendered_at}`",
                ":::",
                "",
            ]
        ),
        encoding="utf-8",
    )
    logger.info("Wrote {}", TARGET)


if __name__ == "__main__":
    main()
