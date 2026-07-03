"""Report DVC drift during local pre-push without blocking the push.

Protected CRPTO stages are intentionally not re-run as part of ordinary
governance, documentation, or paper-surface edits. This hook keeps the useful
``dvc status`` signal visible while leaving artifact promotion to explicit
run-tagged revalidation.
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "dvc", "status"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "").strip()
    error = (result.stderr or "").strip()

    if result.returncode == 0:
        if output:
            print(output)
        return 0

    print("DVC status reports changed deps/outs; treating as non-blocking drift report.")
    print("Protected-stage reproduction still requires an explicit run tag and approval.")
    if output:
        print(output)
    if error:
        print(error, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
