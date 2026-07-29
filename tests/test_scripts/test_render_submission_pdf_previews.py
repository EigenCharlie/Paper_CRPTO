from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from scripts import render_submission_pdf_previews as previews


def test_explicit_chrome_path_has_priority(monkeypatch, tmp_path: Path) -> None:
    chrome = tmp_path / "chrome"
    chrome.touch()
    monkeypatch.setenv("CHROME_PATH", str(chrome))

    assert previews.find_chrome() == chrome


def test_candidates_cover_native_linux_and_wsl_windows(monkeypatch) -> None:
    native = Path("/opt/browser/chromium")
    monkeypatch.delenv("CHROME_PATH", raising=False)
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        monkeypatch.delenv(env_var, raising=False)
    monkeypatch.setattr(
        previews.shutil,
        "which",
        lambda executable: str(native) if executable == "chromium" else None,
    )

    candidates = previews._chrome_candidates()

    assert native in candidates
    if previews.os.name != "nt":
        assert Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe") in candidates
        assert (
            Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") in candidates
        )


def test_wsl_browser_paths_translate_input_and_output(monkeypatch, tmp_path: Path) -> None:
    html = tmp_path / "paper preview.html"
    pdf = tmp_path / "paper preview.pdf"
    translations = {
        html: r"C:\repo\paper preview.html",
        pdf: r"C:\repo\paper preview.pdf",
    }
    monkeypatch.setattr(
        previews,
        "_wsl_windows_path",
        lambda path: translations[path],
    )

    html_uri, browser_pdf = previews._browser_paths(
        Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"),
        html,
        pdf,
    )

    assert html_uri == "file:///C:/repo/paper%20preview.html"
    assert browser_pdf == r"C:\repo\paper preview.pdf"


def test_render_pdf_replaces_output_only_after_browser_creates_pdf(
    monkeypatch,
    tmp_path: Path,
) -> None:
    html = tmp_path / "preview.html"
    html.write_text("<html></html>", encoding="utf-8")
    pdf = tmp_path / "preview.pdf"
    pdf.write_bytes(b"old")
    monkeypatch.setattr(previews, "ROOT", tmp_path)

    def fake_run(command, **_kwargs):
        target = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf="))
        Path(target).write_bytes(b"new-pdf")

    monkeypatch.setattr(previews.subprocess, "run", fake_run)
    monkeypatch.setattr(previews, "_trim_trailing_blank_pages", lambda _path: 0)

    previews.render_pdf(tmp_path / "chrome", html, pdf)

    assert pdf.read_bytes() == b"new-pdf"


def test_render_pdf_preserves_previous_output_when_browser_writes_nothing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    html = tmp_path / "preview.html"
    html.write_text("<html></html>", encoding="utf-8")
    pdf = tmp_path / "preview.pdf"
    pdf.write_bytes(b"old")
    monkeypatch.setattr(previews, "ROOT", tmp_path)
    monkeypatch.setattr(previews.subprocess, "run", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="Browser exited without creating"):
        previews.render_pdf(tmp_path / "chrome", html, pdf)

    assert pdf.read_bytes() == b"old"


def test_trailing_blank_pages_are_removed_but_one_page_is_retained(tmp_path: Path) -> None:
    pdf = tmp_path / "blank-tail.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    with pdf.open("wb") as handle:
        writer.write(handle)

    removed = previews._trim_trailing_blank_pages(pdf)

    assert removed == 2
    assert len(PdfReader(pdf).pages) == 1


@pytest.mark.parametrize(
    "content",
    [
        b"q 0 0 10 10 re f Q",
        b"BT (OK) Tj ET",
    ],
)
def test_trailing_graphic_or_short_text_page_is_never_trimmed(
    tmp_path: Path,
    content: bytes,
) -> None:
    pdf = tmp_path / "meaningful-tail.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    meaningful = writer.add_blank_page(width=612, height=792)
    stream = DecodedStreamObject()
    stream.set_data(content)
    meaningful[NameObject("/Contents")] = writer._add_object(stream)
    with pdf.open("wb") as handle:
        writer.write(handle)

    removed = previews._trim_trailing_blank_pages(pdf)

    assert removed == 0
    assert len(PdfReader(pdf).pages) == 2


def test_chrome_white_background_only_tail_is_trimmed(tmp_path: Path) -> None:
    pdf = tmp_path / "chrome-blank-tail.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    tail = writer.add_blank_page(width=612, height=792)
    stream = DecodedStreamObject()
    stream.set_data(
        b"q 1 1 1 RG 1 1 1 rg 0 0 612 792 re f Q "
        b"/NonStruct <</MCID 0>> BDC q 1 1 1 rg 0 0 612 10 re f Q EMC"
    )
    tail[NameObject("/Contents")] = writer._add_object(stream)
    with pdf.open("wb") as handle:
        writer.write(handle)

    removed = previews._trim_trailing_blank_pages(pdf)

    assert removed == 1
    assert len(PdfReader(pdf).pages) == 1
