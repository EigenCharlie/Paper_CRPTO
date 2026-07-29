from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import scripts.build_ijds_binary_geometry_frontier_v4_evidence as builder


def test_phase_figure_uses_independent_axes_and_exact_window_ordinals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phase = pd.DataFrame(
        {
            "window_id": builder.WINDOW_IDS,
            "fit_prevalence": [0.117, 0.116, 0.114, 0.110, 0.107, 0.105, 0.102, 0.097],
            "phase_boundary_rate": [0.10] * 8,
            "fit_residual_quantile": [0.888] * 7 + [0.112],
            "phase_margin": [20, 18, 16, 14, 13, 12, 11, -16],
        }
    )
    rendered: dict[str, object] = {}

    def capture_figure(
        figure: builder.plt.Figure,
        stem: str,
        *,
        output_dir: Path,
    ) -> dict[str, Path]:
        left, right = figure.axes
        figure.canvas.draw()
        rendered["joined"] = left.get_shared_x_axes().joined(left, right)
        rendered["ticks"] = [axis.get_xticks().tolist() for axis in (left, right)]
        rendered["labels"] = [
            [tick.get_text() for tick in axis.get_xticklabels()] for axis in (left, right)
        ]
        rendered["formatters_are_distinct"] = (
            left.xaxis.get_major_formatter() is not right.xaxis.get_major_formatter()
        )
        builder.plt.close(figure)
        return {}

    monkeypatch.setattr(builder, "_save_figure", capture_figure)

    builder._phase_figure(phase, output_dir=tmp_path)

    expected = [str(index) for index in range(1, 9)]
    assert rendered == {
        "joined": False,
        "ticks": [[float(index) for index in range(1, 9)]] * 2,
        "labels": [expected, expected],
        "formatters_are_distinct": True,
    }


def test_stage_only_generation_stays_inside_repo_and_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    stage = repo / "staging" / "generation"
    calls: list[tuple[Path, bool]] = []

    def fake_build(path: Path, *, promote: bool = True) -> Path:
        calls.append((path, promote))
        return path / "outputs" / "manifest.json"

    monkeypatch.setattr(builder, "ROOT", repo)
    monkeypatch.setattr(builder, "_build_evidence", fake_build)

    output = builder.build_evidence(stage_only_root=stage)

    assert output == stage.resolve() / "outputs" / "manifest.json"
    assert calls == [(stage.resolve(), False)]
    assert stage.is_dir()


def test_stage_only_generation_rejects_paths_outside_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(builder, "ROOT", repo)

    with pytest.raises(ValueError, match="inside the repository"):
        builder.build_evidence(stage_only_root=tmp_path / "outside")


def test_clean_rebuild_verifier_requires_exact_canonical_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    table = repo / "reports/tables/table.csv"
    figure_dir = repo / "reports/figures"
    figure_png = figure_dir / "figure.png"
    figure_pdf = figure_dir / "figure.pdf"
    manifest = repo / "reports/evidence.json"
    stage = repo / "staging/generation"
    staged_outputs = stage / "outputs"
    targets = (table, figure_png, figure_pdf)
    for index, target in enumerate(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"artifact-{index}".encode())
        staged = staged_outputs / target.relative_to(repo)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(target.read_bytes())
    payload = {
        "paper_artifacts": {
            f"artifact-{index}": {"path": target.relative_to(repo).as_posix()}
            for index, target in enumerate(targets)
        }
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    staged_manifest = staged_outputs / manifest.relative_to(repo)
    staged_manifest.parent.mkdir(parents=True, exist_ok=True)
    staged_manifest.write_bytes(manifest.read_bytes())

    monkeypatch.setattr(builder, "ROOT", repo)
    monkeypatch.setattr(builder, "EVIDENCE_PATH", manifest)
    monkeypatch.setattr(builder, "TABLE_TARGETS", {"table": table})
    monkeypatch.setattr(builder, "FIGURE_DIR", figure_dir)
    monkeypatch.setattr(builder, "FIGURE_STEMS", {"figure": "figure"})

    assert builder.verify_staged_evidence_matches_canonical(stage) == staged_manifest

    staged_table = staged_outputs / table.relative_to(repo)
    staged_table.write_text("drift", encoding="utf-8")
    with pytest.raises(RuntimeError, match="differs from canonical artifact"):
        builder.verify_staged_evidence_matches_canonical(stage)
