"""Report cyclomatic complexity for the declared active code surface."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence

from scripts.run_ty_advisory import iter_python_files

RADON_REQUIREMENT = "radon==6.0.1"
_PYTHON_ENV_KEYS = ("PYTHONHOME", "VIRTUAL_ENV")


def build_radon_command(*, uvx: str, files: Sequence[str]) -> list[str]:
    """Build the pinned Radon command for active Python files."""
    return [
        uvx,
        "--from",
        RADON_REQUIREMENT,
        "radon",
        "cc",
        *files,
        "--show-complexity",
        "--min",
        "C",
    ]


def isolated_uvx_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Remove interpreter bindings that can corrupt a nested uvx runtime."""
    cleaned = dict(environ)
    for key in _PYTHON_ENV_KEYS:
        cleaned.pop(key, None)
    return cleaned


def main() -> int:
    uvx = shutil.which("uvx")
    if uvx is None:
        raise RuntimeError("uvx is required to run the complexity report.")
    files = iter_python_files(scope="active")
    result = subprocess.run(
        build_radon_command(uvx=uvx, files=files),
        check=False,
        env=isolated_uvx_environment(os.environ),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
