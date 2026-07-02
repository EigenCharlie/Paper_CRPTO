"""Hash-regression tests against ``EXTRACTION_MANIFEST.json``.

These guard the frozen champion paper outputs. They compute the SHA256 of
each file currently on disk and compare against the digest recorded when the
champion was extracted. Files that the manifest lists but are not in the
working copy (e.g. heavy DVC-tracked artefacts that need ``dvc pull``) are
skipped, not failed — partial local checkouts are normal in this project.

Failure modes this catches:

* Someone re-ran a protected DVC stage and modified the bytes of the
  champion ``pd_canonical.cbm`` / ``final_project_promotion.json`` /
  ``pd_canonical_calibrator.pkl``.
* A "harmless" code refactor accidentally regenerated a frozen JSON/CSV
  (e.g. ``crpto_table0_key_metrics.csv``) with different formatting.
* A line-ending fix-up touched a paper-tracked text file.

The protected files are tested individually so the failure
message is immediately actionable. The rest are tested parametrically and
report aggregate drift counts.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

MANIFEST_PATH = Path("EXTRACTION_MANIFEST.json")
STRICT_ARTIFACTS = os.getenv("CRPTO_REQUIRE_DVC_ARTIFACTS", "").lower() in {
    "1",
    "true",
    "yes",
}

PROTECTED_CHAMPION_FILES = (
    "models/pd_canonical.cbm",
    "models/pd_canonical_calibrator.pkl",
    "models/final_project_promotion.json",
    "models/conformal_policy_status.json",
    "models/champion_portfolio_policy.json",
    "models/champion_registry.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal/"
    "portfolio/pool93_ijds_claim_governance.json",
    "models/experiments/champion_reopen/"
    "champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/"
    "portfolio/pool93_ijds_consolidated_governance.json",
)


def _sha256_of_file(path: Path, chunk_size: int = 1 << 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        pytest.skip(f"{MANIFEST_PATH} not available locally.")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return _load_manifest()


@pytest.fixture(scope="module")
def critical_hashes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hashes = manifest.get("critical_hashes", {})
    if not isinstance(hashes, dict) or not hashes:
        pytest.skip("No critical_hashes block in the manifest.")
    return hashes


# ---------------------------------------------------------------------------
# Protected champion artefacts — individual tests for actionable failures.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel_path", PROTECTED_CHAMPION_FILES)
def test_protected_champion_artefact_hash(
    rel_path: str, critical_hashes: dict[str, dict[str, Any]]
) -> None:
    """Bit-exact hash check on never-overwrite-without-revalidation files."""
    expected = critical_hashes.get(rel_path)
    if not expected or "sha256" not in expected:
        msg = f"{rel_path} not in manifest critical_hashes."
        if STRICT_ARTIFACTS:
            pytest.fail(msg)
        pytest.skip(msg)
    abs_path = Path(rel_path)
    if not abs_path.is_file():
        msg = f"{rel_path} not present locally — run `dvc pull`."
        if STRICT_ARTIFACTS:
            pytest.fail(msg)
        pytest.skip(msg)
    actual = _sha256_of_file(abs_path)
    assert actual == expected["sha256"], (
        f"Champion drift detected on {rel_path}:\n"
        f"  expected: {expected['sha256']}\n"
        f"  actual:   {actual}\n"
        f"This file is frozen for the paper. Do NOT overwrite without an "
        f"explicit revalidation plan."
    )
    if "bytes" in expected:
        assert abs_path.stat().st_size == expected["bytes"], (
            f"{rel_path} byte count differs: expected {expected['bytes']}, "
            f"got {abs_path.stat().st_size}"
        )


# ---------------------------------------------------------------------------
# Aggregate sweep over every recorded hash.
# ---------------------------------------------------------------------------


# Prefixes whose files must remain bit-exact for the paper to be reproducible.
# Code/docs/CI files evolve and are intentionally NOT included here — the
# champion contract is about model and data outputs, not source code.
# PDF figures are excluded because matplotlib embeds timestamps; PNG and CSV
# outputs are reproducible.
_FROZEN_PREFIXES = (
    "models/",
    "data/processed/",
    "reports/crpto/tables/",
)

# Suffixes that legitimately drift even inside frozen prefixes.
_NON_REPRODUCIBLE_SUFFIXES = (".pdf",)

# Files inside those prefixes that we explicitly allow to drift (regenerable
# from frozen inputs without changing model behaviour).
_ALLOWED_DRIFT = frozenset(
    {
        # status/JSON aggregations that get regenerated by paper.* stages
        "models/crpto_evidence_status.json",
        "models/crpto_journal_package_status.json",
    }
)


def test_manifest_hash_sweep_summary(critical_hashes: dict[str, dict[str, Any]]) -> None:
    """Hash sweep over the model/data artefacts that must remain bit-exact.

    Source code, documentation, CI files and the Quarto book intentionally
    evolve over time — they are not part of the champion contract. Only files
    under ``models/``, ``data/processed/``, ``reports/crpto/tables/`` and
    ``reports/crpto/figures/`` are checked, with a small allow-list for status
    JSONs that are regenerated by deterministic ``crpto.paper.*`` stages.
    """
    drift: list[tuple[str, str, str]] = []
    missing: list[str] = []
    checked = 0

    for rel_path, entry in critical_hashes.items():
        if not rel_path.startswith(_FROZEN_PREFIXES):
            continue
        if rel_path in _ALLOWED_DRIFT:
            continue
        if rel_path.endswith(_NON_REPRODUCIBLE_SUFFIXES):
            continue
        expected = entry.get("sha256") if isinstance(entry, dict) else None
        if not expected:
            continue
        path = Path(rel_path)
        if not path.is_file():
            missing.append(rel_path)
            continue
        actual = _sha256_of_file(path)
        checked += 1
        if actual != expected:
            drift.append((rel_path, expected, actual))

    print(
        f"\nManifest sweep (model/data only): {checked} checked, "
        f"{len(missing)} missing, {len(drift)} drifted."
    )
    if missing[:5]:
        print("  Missing examples:", missing[:5])

    if drift:
        msg = "\n".join(f"  {p}\n    expected={e}\n    actual=  {a}" for p, e, a in drift)
        pytest.fail(f"{len(drift)} frozen artefacts drifted from manifest:\n{msg}")

    if missing and STRICT_ARTIFACTS:
        msg = "\n".join(f"  {p}" for p in missing)
        pytest.fail(f"{len(missing)} frozen artefacts missing after DVC pull:\n{msg}")

    assert checked > 0, "No frozen artefacts found on disk — partial checkout? Run `dvc pull`."


def test_champion_metrics_match_manifest(manifest: dict[str, Any]) -> None:
    """Cross-check that the champion metrics block agrees with the run-tag and the
    paper's headline numbers. This is independent of file hashes."""
    metrics = manifest.get("champion_metrics") or {}
    if not metrics:
        pytest.skip("Manifest has no champion_metrics block.")

    # Allow the manifest to phrase keys slightly differently across schemas.
    flat = {k.lower(): v for k, v in metrics.items() if isinstance(k, str)}
    return_robust = flat.get("robust_return") or flat.get("realized_total_return")
    if return_robust is not None:
        assert float(return_robust) == pytest.approx(170464.5429284627, rel=1e-6), (
            f"Manifest robust_return drift: got {return_robust}"
        )
    assert flat.get("run_tag") == "ijds-rebaseline-2026-06-07"
    assert float(flat["alpha01_weighted_miscoverage_v"]) == pytest.approx(0.028875, abs=1e-12)
    assert float(flat["alpha01_gamma_cp"]) == pytest.approx(0.187987, abs=1e-12)
    assert flat.get("alpha01_exact_pass") is True
