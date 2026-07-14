"""Compile and sanity-check the official IJDS LaTeX submission PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from scripts.build_ijds_submission_tex import render_submission_tex

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_DIR = ROOT / "paper" / "submission"
REPORT_DIR = ROOT / "reports" / "ci"
TEX_NAME = "CRPTO_ijds_submission.tex"
JOB_NAME = "CRPTO_ijds_submission"
OFFICIAL_TEMPLATE_FILES = (
    "informs4.cls",
    "informs2014.bst",
    "eqndefns-left.sty",
    "informs_Logo.pdf",
)
STYLE_MANIFEST = SUBMISSION_DIR / "informs_style_assets.json"
INFORMS_STYLE_URL = "https://pubsonline.informs.org/authorportal/latex-style-files"


@dataclass(frozen=True)
class LatexScan:
    """Summary of a compiled LaTeX submission surface."""

    pages: int | None
    blg_warnings: tuple[str, ...]
    log_failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.blg_warnings and not self.log_failures


def _run(command: list[str], *, cwd: Path, env: dict[str, str], transcript: Path) -> int:
    logger.info("Running: {}", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    transcript.parent.mkdir(parents=True, exist_ok=True)
    with transcript.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n$ {' '.join(command)}\n")
        handle.write(completed.stdout)
    return int(completed.returncode)


def _submission_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("WINDIR") and env.get("SystemRoot"):
        env["WINDIR"] = env["SystemRoot"]
    return env


def _windows_latexmk_script(latexmk_executable: str | Path) -> Path | None:
    """Locate ``latexmk.pl`` beside a TeX Live/TinyTeX Windows wrapper."""
    executable = Path(latexmk_executable).resolve()
    for root in executable.parents:
        script = root / "texmf-dist" / "scripts" / "latexmk" / "latexmk.pl"
        if script.is_file():
            return script
    return None


def _latexmk_command() -> list[str] | None:
    """Return a working latexmk launcher, bypassing fragile TinyTeX wrappers."""
    executable = shutil.which("latexmk")
    if executable is None:
        return None
    if os.name == "nt" and (perl := shutil.which("perl")) is not None:
        script = _windows_latexmk_script(executable)
        if script is not None:
            return [perl, str(script)]
    return [executable]


def _manual_pdflatex_bibtex(cwd: Path, env: dict[str, str], transcript: Path) -> int:
    sequence = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", TEX_NAME],
        ["bibtex", JOB_NAME],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", TEX_NAME],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", TEX_NAME],
    ]
    for command in sequence:
        code = _run(command, cwd=cwd, env=env, transcript=transcript)
        if code != 0:
            return code
    return 0


def _missing_template_files(directory: Path) -> tuple[str, ...]:
    """Return official publisher assets absent from a submission directory."""
    return tuple(name for name in OFFICIAL_TEMPLATE_FILES if not (directory / name).is_file())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _template_asset_drift(directory: Path) -> tuple[str, ...]:
    """Return publisher assets that differ from the reviewed style-kit manifest."""
    payload = json.loads((directory / STYLE_MANIFEST.name).read_text(encoding="utf-8"))
    assets = payload.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(OFFICIAL_TEMPLATE_FILES):
        return ("style manifest inventory",)
    drift: list[str] = []
    for name in OFFICIAL_TEMPLATE_FILES:
        path = directory / name
        expected = assets[name]
        if path.stat().st_size != int(expected["bytes"]) or _file_sha256(path) != str(
            expected["sha256"]
        ):
            drift.append(name)
    return tuple(drift)


def compile_submission(*, prefer_manual: bool = False, render: bool = True) -> int:
    """Compile the official submission with latexmk, falling back to manual passes."""
    if render:
        render_submission_tex()
    if not (SUBMISSION_DIR / TEX_NAME).is_file():
        logger.error("Missing {}", (SUBMISSION_DIR / TEX_NAME).relative_to(ROOT))
        return 2
    missing = _missing_template_files(SUBMISSION_DIR)
    if missing:
        logger.error(
            "Missing official INFORMS LaTeX assets: {}. Download the current style package "
            "from {} and place these files in paper/submission; they are intentionally "
            "ignored by Git.",
            ", ".join(missing),
            INFORMS_STYLE_URL,
        )
        return 2
    if not STYLE_MANIFEST.is_file():
        logger.error("Missing tracked INFORMS style manifest: {}", STYLE_MANIFEST.relative_to(ROOT))
        return 2
    drift = _template_asset_drift(SUBMISSION_DIR)
    if drift:
        logger.error(
            "INFORMS style assets differ from the reviewed manifest: {}. Re-download "
            "from {} or explicitly review and update informs_style_assets.json.",
            ", ".join(drift),
            INFORMS_STYLE_URL,
        )
        return 2

    env = _submission_env()
    transcript = REPORT_DIR / "ijds-latex-build.txt"
    if transcript.exists():
        transcript.unlink()
    latexmk_command = _latexmk_command()
    if prefer_manual or latexmk_command is None:
        if latexmk_command is None:
            logger.warning("latexmk unavailable; using manual pdflatex/BibTeX fallback.")
        return _manual_pdflatex_bibtex(SUBMISSION_DIR, env, transcript)

    latexmk_code = _run(
        [*latexmk_command, "-pdf", "-gg", "-interaction=nonstopmode", TEX_NAME],
        cwd=SUBMISSION_DIR,
        env=env,
        transcript=transcript,
    )
    if latexmk_code == 0:
        logger.info("LaTeX transcript: {}", transcript.relative_to(ROOT))
        return 0

    logger.warning("latexmk failed with code {}; using manual fallback.", latexmk_code)
    code = _manual_pdflatex_bibtex(SUBMISSION_DIR, env, transcript)
    logger.info("LaTeX transcript: {}", transcript.relative_to(ROOT))
    return code


def scan_submission_logs() -> LatexScan:
    """Inspect `.blg` and `.log` outputs for bibliography/reference drift."""
    blg_path = SUBMISSION_DIR / f"{JOB_NAME}.blg"
    log_path = SUBMISSION_DIR / f"{JOB_NAME}.log"
    blg_text = blg_path.read_text(encoding="utf-8", errors="replace") if blg_path.exists() else ""
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""

    blg_warnings = tuple(
        line.strip() for line in blg_text.splitlines() if line.strip().startswith("Warning--")
    )

    checks = {
        "undefined references": r"There were undefined references",
        "undefined citations": r"Citation `[^`]+`.*undefined",
        "undefined labels": r"Reference `[^`]+`.*undefined",
        "rerun requested": r"Rerun to get cross-references right|Label\(s\) may have changed",
    }
    log_failures = tuple(name for name, pattern in checks.items() if re.search(pattern, log_text))

    pages: int | None = None
    matches = re.findall(r"Output written on .+?\((\d+) pages?,", log_text)
    if matches:
        pages = int(matches[-1])

    return LatexScan(pages=pages, blg_warnings=blg_warnings, log_failures=log_failures)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Skip latexmk and use pdflatex + bibtex + pdflatex + pdflatex directly.",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Do not compile; only inspect existing .log and .blg files.",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Compile the existing generated TeX without rendering the QMD again.",
    )
    args = parser.parse_args(argv)

    if args.scan_only and args.skip_render:
        parser.error("--skip-render is redundant with --scan-only")

    if not args.scan_only:
        code = compile_submission(prefer_manual=args.manual, render=not args.skip_render)
        if code != 0:
            logger.error("Official IJDS LaTeX compile failed with code {}.", code)
            return code

    scan = scan_submission_logs()
    if scan.blg_warnings:
        logger.error("BibTeX warnings:\n{}", "\n".join(scan.blg_warnings))
    if scan.log_failures:
        logger.error("LaTeX convergence failures: {}", ", ".join(scan.log_failures))
    if scan.pages is None:
        logger.warning("Could not read page count from the LaTeX log.")
    else:
        logger.success("Official IJDS PDF page count: {}", scan.pages)

    if not scan.ok:
        return 1
    logger.success("Official IJDS LaTeX build is citation/reference clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
