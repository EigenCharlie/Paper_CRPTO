"""Render anonymous IJDS HTML previews to local PDF drafts."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
BODY_HTML = ROOT / "paper" / "CRPTO_ijds.html"
BODY_PDF = ROOT / "paper" / "CRPTO_ijds.pdf"
SUPPLEMENT_HTML = ROOT / "paper" / "supplement_ijds.html"
SUPPLEMENT_PDF = ROOT / "paper" / "supplement_ijds.pdf"


def _chrome_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        candidates.append(Path(env_path))
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base = os.environ.get(env_var)
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ]
        )
    return candidates


def find_chrome() -> Path:
    """Return a Chromium-compatible browser executable for PDF printing."""
    for candidate in _chrome_candidates():
        if candidate.exists():
            return candidate
    msg = (
        "No Chrome or Edge executable was found. Set CHROME_PATH to a "
        "Chromium-compatible browser before running this target."
    )
    raise FileNotFoundError(msg)


def render_pdf(chrome: Path, html_path: Path, pdf_path: Path) -> None:
    """Print one local HTML preview to PDF with Chrome headless."""
    if not html_path.exists():
        msg = f"Missing HTML preview: {html_path.relative_to(ROOT)}"
        raise FileNotFoundError(msg)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    logger.info("Rendered {}", pdf_path.relative_to(ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command line flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-only", action="store_true", help="Render only CRPTO_ijds.pdf.")
    parser.add_argument(
        "--supplement-only",
        action="store_true",
        help="Render only supplement_ijds.pdf.",
    )
    return parser.parse_args()


def main() -> int:
    """Render the requested submission PDF preview(s)."""
    args = parse_args()
    if args.body_only and args.supplement_only:
        raise ValueError("Choose at most one of --body-only or --supplement-only.")

    pairs = [(BODY_HTML, BODY_PDF), (SUPPLEMENT_HTML, SUPPLEMENT_PDF)]
    if args.body_only:
        pairs = [(BODY_HTML, BODY_PDF)]
    elif args.supplement_only:
        pairs = [(SUPPLEMENT_HTML, SUPPLEMENT_PDF)]

    chrome = find_chrome()
    logger.info("Using {}", chrome)
    for html_path, pdf_path in pairs:
        render_pdf(chrome, html_path, pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
