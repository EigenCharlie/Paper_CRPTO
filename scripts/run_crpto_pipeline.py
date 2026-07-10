#!/usr/bin/env python
"""Retired compatibility entry point for the former canonical pipeline runner.

The original runner rewrote frozen data, PD, conformal, and portfolio paths and
also embedded Unix-only commands.  It remains as a fail-closed stop sign so an
old command cannot silently mutate the submission baseline.  Use
``just submission-check`` for the complete safe release gate, or an explicitly
versioned experiment runner for challengers.
"""

from __future__ import annotations


def main() -> int:
    """Stop old invocations before they can touch canonical artifacts."""
    raise SystemExit(
        "scripts/run_crpto_pipeline.py is retired because it rewrote protected artifacts. "
        "Use `just submission-check` or an isolated versioned experiment command."
    )


if __name__ == "__main__":
    raise SystemExit(main())
