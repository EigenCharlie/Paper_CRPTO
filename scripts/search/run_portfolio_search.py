"""Retired portfolio search entrypoint.

The former generic ``scripts.run_long_pipeline`` orchestrator was removed when
the IJDS paper lane was narrowed around frozen artifacts. Keep this file as a
readable stop sign for old commands instead of failing with an import error.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    _ = argv
    sys.stderr.write(
        "scripts/search/run_portfolio_search.py is retired. The submitted IJDS "
        "claim uses the closed finite-grid frontier; use "
        "scripts/search/run_pool93_ijds_local_refinement.py only for an explicitly "
        "tagged isolated refinement, not as a default paper path.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
