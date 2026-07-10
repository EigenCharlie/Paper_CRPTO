"""Retired writer for volatile book build metadata.

Build commit, branch, and timestamp belong in release receipts and tags.  They
must not be written into a tracked Quarto source because doing so makes every
render dirty and creates an unavoidable self-reference.
"""

from __future__ import annotations


def main() -> int:
    """Fail closed for old invocations of the removed source mutator."""
    raise SystemExit(
        "Dynamic book build metadata is retired. Use the release tag and "
        "reproducibility receipt instead of modifying tracked Quarto input."
    )


if __name__ == "__main__":
    raise SystemExit(main())
