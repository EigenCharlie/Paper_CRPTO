"""Retired conformal search entrypoint.

The former generic ``scripts.run_long_pipeline`` orchestrator was removed when
the IJDS paper lane was narrowed around frozen artifacts. Keep this file as a
readable stop sign for old commands instead of failing with an import error.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    _ = argv
    sys.stderr.write(
        "scripts/search/run_conformal_search.py is retired. Use the frozen "
        "IJDS artifacts plus paper evidence stages, or start a new isolated "
        "experiment under scripts/search/run_conformal_reopen_search.py with "
        "an explicit run tag and drift plan.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
