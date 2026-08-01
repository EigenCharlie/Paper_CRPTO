from __future__ import annotations

from copy import deepcopy

import yaml

from scripts.check_publication_integrity import (
    EXPECTED_SCIENTIFIC_GIT_LINEAGES,
    SOURCE_REGISTRY_PATH,
    _scientific_git_lineages,
    check_publication_integrity,
)


def test_active_ijds_publication_surfaces_are_claim_synchronized() -> None:
    assert check_publication_integrity() == []


def test_scientific_git_lineage_count_is_derived_from_registry() -> None:
    registry = yaml.safe_load(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert _scientific_git_lineages(registry) == EXPECTED_SCIENTIFIC_GIT_LINEAGES
    assert len(EXPECTED_SCIENTIFIC_GIT_LINEAGES) == 9

    missing = deepcopy(registry)
    del missing["lineages"]["diagnostics"]["common_panel_threshold_response"]["artifact_tag"]
    assert _scientific_git_lineages(missing) != EXPECTED_SCIENTIFIC_GIT_LINEAGES

    unexpected = deepcopy(registry)
    unexpected["sensitivities"]["endpoint_availability"]["artifact_tag"] = "artifacts/unexpected"
    assert _scientific_git_lineages(unexpected) != EXPECTED_SCIENTIFIC_GIT_LINEAGES
