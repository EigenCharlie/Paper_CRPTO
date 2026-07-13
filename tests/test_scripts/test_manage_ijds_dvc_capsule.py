from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.manage_ijds_dvc_capsule import active_dvc_pointers


def _targets(tmp_path: Path, count: int) -> Path:
    pointers: list[str] = []
    for index in range(count):
        relative = f"active/run-{index}.dvc"
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("outs: []\n", encoding="utf-8")
        pointers.append(relative)
    targets = tmp_path / "targets.yaml"
    targets.write_text(
        yaml.safe_dump({"active_scientific_contract": {"dvc_pointers": pointers}}),
        encoding="utf-8",
    )
    return targets


def test_active_dvc_pointers_loads_exact_four_pointer_capsule(tmp_path: Path) -> None:
    pointers = active_dvc_pointers(root=tmp_path, targets_path=_targets(tmp_path, 4))

    assert len(pointers) == 4
    assert all(path.is_file() and path.suffix == ".dvc" for path in pointers)


def test_active_dvc_pointers_rejects_incomplete_capsule(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="four unique pointers"):
        active_dvc_pointers(root=tmp_path, targets_path=_targets(tmp_path, 3))
