from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "compile_ijds_submission_windows.ps1"
JUSTFILE = ROOT / "justfile"
SUBMISSION_README = ROOT / "paper" / "submission" / "README.md"
SUBMISSION_GITIGNORE = ROOT / "paper" / "submission" / ".gitignore"
PUBLICATION_TARGETS = ROOT / "configs" / "crpto_publication_targets.yaml"


def _launcher_text() -> str:
    return LAUNCHER.read_text(encoding="utf-8")


def _write_fake_tinytex(root: Path) -> None:
    for relative in (
        "bin/windows/pdflatex.exe",
        "bin/windows/bibtex.exe",
        "tlpkg/tlperl/bin/perl.exe",
        "texmf-dist/scripts/latexmk/latexmk.pl",
        "texmf-dist/web2c/texmf.cnf",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def test_windows_launcher_uses_bundled_perl_latexmk_convergence_loop() -> None:
    text = _launcher_text()

    assert "$nativeOutput = & $aliasedPerl $aliasedLatexmk @latexmkArguments" in text
    for argument in (
        '"-pdf"',
        '"-gg"',
        '"-interaction=nonstopmode"',
        '"-halt-on-error"',
        '"-file-line-error"',
        '"-bibtexfudge-"',
    ):
        assert argument in text
    assert "Latexmk: All targets .* are up-to-date" in text
    assert "latexmk.exe/runscript wrapper is not reliable" in text


def test_windows_launcher_cleanup_is_fail_closed_and_unconditional() -> None:
    text = _launcher_text()
    outer_try = text.index("$primaryError = $null")
    cleanup = text[outer_try:]

    assert "} finally {" in cleanup
    assert "Pop-Location" in cleanup
    assert "$env:PATH = $originalPath" in cleanup
    assert "$env:BIBINPUTS = $originalBibInputs" in cleanup
    assert "$env:BSTINPUTS = $originalBstInputs" in cleanup
    assert '& $substExecutable "$selectedDrive`:" "/D"' in cleanup
    assert "drive alias remains mounted" in cleanup
    assert "if ($cleanupFailures.Count -gt 0)" in cleanup
    assert 'throw "Windows LaTeX cleanup failed:' in cleanup


def test_windows_launcher_rejects_nonconverged_or_incomplete_outputs() -> None:
    text = _launcher_text()

    for contract in (
        "Required LaTeX output is missing",
        "Required LaTeX output is empty",
        "There were undefined references",
        "Citation `[^`]+`.*undefined",
        "Reference `[^`]+`.*undefined",
        r"Rerun to get cross-references right|Label\(s\) may have changed",
        "Missing character:",
        "LaTeX log does not contain a parseable positive page count",
        "BibTeX emitted one or more warnings",
    ):
        assert contract in text


@pytest.mark.skipif(os.name != "nt", reason="PowerShell launcher is Windows-only")
def test_windows_launcher_plan_builds_expected_command_without_mapping(
    tmp_path: Path,
) -> None:
    tinytex = tmp_path / "TinyTeX"
    _write_fake_tinytex(tinytex)
    tex = tmp_path / "paper" / "submission" / "paper.tex"
    tex.parent.mkdir(parents=True)
    tex.write_text("\\documentclass{article}\n", encoding="utf-8")
    output = tmp_path / "output"

    plan_path = tmp_path / "plan.json"
    with plan_path.open("w", encoding="utf-8", newline="") as stdout:
        subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(LAUNCHER),
                "-TexFile",
                str(tex),
                "-TinyTexRoot",
                str(tinytex),
                "-OutputDirectory",
                str(output),
                "-PlanOnly",
            ],
            cwd=ROOT,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
        )

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["command"][0].endswith(r"\tlpkg\tlperl\bin\perl.exe")
    assert plan["command"][1].endswith(r"\texmf-dist\scripts\latexmk\latexmk.pl")
    assert plan["command"][2:7] == [
        "-pdf",
        "-gg",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
    ]
    assert plan["command"][-1] == tex.name
    assert plan["cleanup"] == [
        "restore location",
        "restore process PATH and TeX search paths",
        f"subst {plan['drive']} /D",
    ]
    assert plan["environment"]["bibinputs_prefix"] == str(tex.parent)
    assert plan["environment"]["bstinputs_prefix"] == str(tex.parent)
    assert not output.exists()


def test_nonfreeze_just_target_and_submission_docs_use_windows_launcher() -> None:
    justfile = JUSTFILE.read_text(encoding="utf-8")
    readme = SUBMISSION_README.read_text(encoding="utf-8")
    gitignore = SUBMISSION_GITIGNORE.read_text(encoding="utf-8")
    targets = PUBLICATION_TARGETS.read_text(encoding="utf-8")

    assert "paper-official-windows: paper-tex" in justfile
    assert "compile_ijds_submission_windows.ps1" in justfile
    assert "-ExecutionPolicy Bypass" in justfile
    assert "just paper-official-windows" in readme
    assert "temporary drive alias" in readme
    assert "*.latexmk.txt" in gitignore
    assert "- scripts/compile_ijds_submission_windows.ps1" in targets
