from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.manage_ijds_dvc_capsule import active_dvc_pointers, verify_remote

RUN_TAGS = (
    "v4-v1",
    "v4-v2",
    "two-ruler-v1c",
    "two-ruler-v2",
    "credit-controls-v1b",
    "credit-controls-v2b",
)


def _targets(tmp_path: Path, *, omit_last: bool = False) -> Path:
    pointers: list[str] = []
    for run_tag in RUN_TAGS:
        for prefix in ("data/processed", "models"):
            relative = f"{prefix}/experiments/ijds_audit/{run_tag}.dvc"
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.safe_dump(
                    {
                        "outs": [
                            {
                                "md5": f"{'a' * 32}.dir",
                                "size": 1,
                                "nfiles": 1,
                                "hash": "md5",
                                "path": run_tag,
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            pointers.append(relative)
    if omit_last:
        pointers.pop()
    lineage_names = (
        ("binary_geometry", "outcome_free", RUN_TAGS[0]),
        ("binary_geometry", "evaluation", RUN_TAGS[1]),
        ("two_ruler", "outcome_free", RUN_TAGS[2]),
        ("two_ruler", "evaluation", RUN_TAGS[3]),
        ("credit_controls", "outcome_free", RUN_TAGS[4]),
        ("credit_controls", "evaluation", RUN_TAGS[5]),
    )
    lineages: dict[str, dict[str, dict[str, str]]] = {}
    for family, phase, run_tag in lineage_names:
        lineages.setdefault(family, {})[phase] = {
            "run_tag": run_tag,
            "protocol_tag": f"protocol/{run_tag}",
            "protocol_commit": "a" * 40,
        }
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": "test",
                "status": "active_ijds_paper_evidence_source_registry",
                "lineages": lineages,
                "dvc_pointers": pointers,
                "sources": {"placeholder": {"path": "unused", "bytes": 0, "sha256": "0" * 64}},
            }
        ),
        encoding="utf-8",
    )
    targets = tmp_path / "targets.yaml"
    targets.write_text(
        yaml.safe_dump(
            {
                "active_scientific_contract": {
                    "source_registry": registry.name,
                }
            }
        ),
        encoding="utf-8",
    )
    return targets


def test_active_dvc_pointers_loads_two_pointers_per_active_run(tmp_path: Path) -> None:
    pointers = active_dvc_pointers(root=tmp_path, targets_path=_targets(tmp_path))

    assert len(pointers) == 12
    assert all(path.is_file() and path.suffix == ".dvc" for path in pointers)


def test_active_dvc_pointers_rejects_incomplete_capsule(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="do not match"):
        active_dvc_pointers(root=tmp_path, targets_path=_targets(tmp_path, omit_last=True))


def test_verify_remote_accepts_empty_cloud_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pointer = tmp_path / "active.dvc"
    pointer.write_text("outs: []\n", encoding="utf-8")
    observed: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="{}\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    verify_remote(root=tmp_path, pointers=[pointer])

    assert observed == [
        [
            "dvc",
            "status",
            "--cloud",
            "--remote",
            "dagshub",
            "--json",
            "active.dvc",
        ]
    ]


def test_verify_remote_rejects_missing_remote_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pointer = tmp_path / "active.dvc"
    pointer.write_text("outs: []\n", encoding="utf-8")

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"data/run": "new"}\n',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="absent in the configured remote"):
        verify_remote(root=tmp_path, pointers=[pointer])
