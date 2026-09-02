from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import scripts.build_ijds_binary_geometry_frontier_v4_evidence as builder


def test_publication_figures_pin_headless_backend() -> None:
    assert builder.plt.get_backend().casefold() == "agg"


def test_phase_census_figure_uses_independent_axes_and_exact_window_ordinals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    census = pd.read_csv(
        builder.TABLE_TARGETS["binary_phase_target_support"],
    )
    rendered: dict[str, object] = {}

    def capture_figure(
        figure: builder.plt.Figure,
        stem: str,
        *,
        output_dir: Path,
    ) -> dict[str, Path]:
        panels = figure.axes[:5]
        figure.canvas.draw()
        rendered["joined"] = any(
            panels[0].get_shared_x_axes().joined(panels[0], axis) for axis in panels[1:]
        )
        rendered["ticks"] = [axis.get_xticks().tolist() for axis in panels]
        rendered["labels"] = [
            [tick.get_text() for tick in axis.get_xticklabels()] for axis in panels
        ]
        rendered["formatters_are_distinct"] = len(
            {id(axis.xaxis.get_major_formatter()) for axis in panels}
        ) == len(panels)
        rendered["outline_counts"] = [len(axis.patches) for axis in panels]
        builder.plt.close(figure)
        return {}

    monkeypatch.setattr(builder, "_save_figure", capture_figure)

    builder._phase_census_figure(census, output_dir=tmp_path)

    expected = [f"W{index}" for index in range(1, 9)]
    assert rendered == {
        "joined": False,
        "ticks": [[float(index) for index in range(8)]] * 5,
        "labels": [expected] * 5,
        "formatters_are_distinct": True,
        "outline_counts": [40, 40, 8, 0, 0],
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
