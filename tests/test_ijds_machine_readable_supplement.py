"""Contracts for the anonymous machine-readable IJDS supplement."""

from __future__ import annotations

import csv
import io
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from scripts.build_ijds_machine_readable_supplement import (
    FORBIDDEN_FINGERPRINT_PATTERNS,
    FORBIDDEN_FINGERPRINTS,
    OUTPUT,
    SOURCE_FILENAMES,
    SOURCES,
    TABLE_CONTRACTS,
    _read_validated_reviewer_csv,
    _reviewer_csv_payload,
    _zip_payload,
)
from scripts.check_publication_integrity import (
    REVIEWER_FORBIDDEN_LITERALS,
    REVIEWER_FORBIDDEN_PATTERNS,
)
from src.ijds_audit.publication_schemas import S6B_PUBLICATION_COLUMNS


@pytest.fixture
def valid_sources(tmp_path: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for archive_name, source in SOURCES.items():
        target = tmp_path / SOURCE_FILENAMES[archive_name]
        target.write_bytes(source.read_bytes())
        sources[archive_name] = target
    return sources


def _csv_matrix(path: Path) -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_text(encoding="utf-8")), strict=True))


def _write_csv_matrix(path: Path, matrix: list[list[str]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(matrix)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def test_zip_scanner_inherits_every_central_reviewer_literal() -> None:
    assert {literal.encode("utf-8") for literal in REVIEWER_FORBIDDEN_LITERALS}.issubset(
        FORBIDDEN_FINGERPRINTS
    )
    assert {label for label, _ in REVIEWER_FORBIDDEN_PATTERNS}.issubset(
        label for label, _ in FORBIDDEN_FINGERPRINT_PATTERNS
    )


def test_current_zip_has_fixed_metadata_and_complete_table_censuses() -> None:
    expected_rows = {
        "Table_S6B_exchangeability_cells.csv": 40,
        "Table_S6C_exchangeability_strata.csv": 200,
        "Table_S6D_label_mondrian_cells.csv": 40,
        "Table_S6E_label_mondrian_strata.csv": 200,
        "Table_S6F_label_mondrian_categories.csv": 400,
        "Table_S6J_common_panel_threshold_response_strata.csv": 175,
        "Table_S6K_common_panel_threshold_response_learners.csv": 35,
    }
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.namelist() == sorted(archive.namelist())
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.external_attr >> 16 == 0o100644

        for name, expected in expected_rows.items():
            text = archive.read(name).decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            assert reader.fieldnames is not None
            assert len(reader.fieldnames) == len(set(reader.fieldnames))
            assert sum(1 for _ in reader) == expected


def test_current_zip_has_complete_five_learner_eight_window_cell_structure() -> None:
    expected_multiplicity = {
        "Table_S6B_exchangeability_cells.csv": 1,
        "Table_S6C_exchangeability_strata.csv": 5,
        "Table_S6D_label_mondrian_cells.csv": 1,
        "Table_S6E_label_mondrian_strata.csv": 5,
        "Table_S6F_label_mondrian_categories.csv": 10,
    }
    with zipfile.ZipFile(OUTPUT) as archive:
        for name, multiplicity in expected_multiplicity.items():
            rows = list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8"))))
            learners = {row["learner"] for row in rows}
            windows = {row["window_id"] for row in rows}
            cell_counts = Counter((row["learner"], row["window_id"]) for row in rows)

            assert len(learners) == 5
            assert len(windows) == 8
            assert len(cell_counts) == 40
            assert set(cell_counts.values()) == {multiplicity}

        categories = list(
            csv.DictReader(
                io.StringIO(archive.read("Table_S6F_label_mondrian_categories.csv").decode("utf-8"))
            )
        )
        assert {row["label"] for row in categories} == {"0", "1"}


def test_machine_readable_supplement_is_current_and_anonymous() -> None:
    payload = _zip_payload()
    assert OUTPUT.read_bytes() == payload

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == [
            "README.txt",
            "Table_S6B_exchangeability_cells.csv",
            "Table_S6C_exchangeability_strata.csv",
            "Table_S6D_label_mondrian_cells.csv",
            "Table_S6E_label_mondrian_strata.csv",
            "Table_S6F_label_mondrian_categories.csv",
            "Table_S6J_common_panel_threshold_response_strata.csv",
            "Table_S6K_common_panel_threshold_response_learners.csv",
        ]
        combined = b"\n".join(archive.read(name).lower() for name in archive.namelist())

    for forbidden in FORBIDDEN_FINGERPRINTS:
        assert forbidden not in combined
    for _, pattern in FORBIDDEN_FINGERPRINT_PATTERNS:
        assert pattern.search(combined) is None

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        s6b_payload = archive.read("Table_S6B_exchangeability_cells.csv")
        s6b_header = tuple(s6b_payload.splitlines()[0].decode("utf-8").split(","))
    assert s6b_header == S6B_PUBLICATION_COLUMNS


def test_common_panel_tables_have_complete_fixed_adjacent_grids() -> None:
    with zipfile.ZipFile(OUTPUT) as archive:
        strata = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("Table_S6J_common_panel_threshold_response_strata.csv").decode(
                        "utf-8"
                    )
                )
            )
        )
        learners = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("Table_S6K_common_panel_threshold_response_learners.csv").decode(
                        "utf-8"
                    )
                )
            )
        )

    assert len({row["learner"] for row in strata}) == 5
    assert len({row["pair_index"] for row in strata}) == 7
    assert len({row["conformal_group"] for row in strata}) == 5
    assert (
        len({(row["learner"], row["pair_index"], row["conformal_group"]) for row in strata}) == 175
    )
    assert len({(row["learner"], row["pair_index"]) for row in learners}) == 35
    for row in strata:
        assert float(row["delta_lower"]) <= float(row["delta_upper"])
        assert float(row["delta_width"]) == pytest.approx(
            float(row["delta_upper"]) - float(row["delta_lower"])
        )


def test_all_seven_source_contracts_validate_and_preserve_csv_bytes(
    valid_sources: dict[str, Path],
) -> None:
    assert set(valid_sources) == set(TABLE_CONTRACTS) == set(SOURCE_FILENAMES)
    for name, path in valid_sources.items():
        payload, rows = _read_validated_reviewer_csv(name, path)
        assert payload == path.read_bytes()
        assert len(rows) == TABLE_CONTRACTS[name].rows


@pytest.mark.parametrize("name", tuple(TABLE_CONTRACTS))
def test_every_source_rejects_header_drift(
    name: str,
    valid_sources: dict[str, Path],
) -> None:
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    matrix[0][0] = f"{matrix[0][0]}_drift"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match=rf"Unexpected {name.split('_')[1]} reviewer schema"):
        _reviewer_csv_payload(name, path)


@pytest.mark.parametrize("name", tuple(TABLE_CONTRACTS))
def test_every_source_rejects_row_count_drift(
    name: str,
    valid_sources: dict[str, Path],
) -> None:
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    matrix.pop()
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="data rows"):
        _reviewer_csv_payload(name, path)


@pytest.mark.parametrize("name", tuple(TABLE_CONTRACTS))
def test_every_source_rejects_duplicate_composite_keys(
    name: str,
    valid_sources: dict[str, Path],
) -> None:
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    matrix[-1] = matrix[1].copy()
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="duplicate composite keys"):
        _reviewer_csv_payload(name, path)


@pytest.mark.parametrize(
    ("name", "column", "invalid"),
    [
        ("Table_S6B_exchangeability_cells.csv", "taxonomy_groups", "4"),
        ("Table_S6C_exchangeability_strata.csv", "role", "secondary"),
        ("Table_S6D_label_mondrian_cells.csv", "role", "secondary"),
        ("Table_S6E_label_mondrian_strata.csv", "sharp_endpoint_delta_reported", "True"),
        ("Table_S6F_label_mondrian_categories.csv", "alpha", "0.05"),
        ("Table_S6J_common_panel_threshold_response_strata.csv", "threshold_sign", "2"),
        ("Table_S6K_common_panel_threshold_response_learners.csv", "strata_rows", "4"),
    ],
)
def test_every_source_rejects_a_locked_domain_violation(
    name: str,
    column: str,
    invalid: str,
    valid_sources: dict[str, Path],
) -> None:
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    matrix[1][matrix[0].index(column)] = invalid
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="out-of-domain value"):
        _reviewer_csv_payload(name, path)


def test_nonfinite_scientific_values_are_rejected(valid_sources: dict[str, Path]) -> None:
    name = "Table_S6J_common_panel_threshold_response_strata.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    matrix[1][matrix[0].index("threshold_delta")] = "nan"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="is not finite"):
        _reviewer_csv_payload(name, path)


def test_cross_table_s6j_to_s6k_aggregate_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6K_common_panel_threshold_response_learners.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("potential_y0_crossed_rows")
    matrix[1][column] = str(int(matrix[1][column]) + 1)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S6J-to-S6K aggregate"):
        _zip_payload(valid_sources)


def test_cross_table_s6b_to_s6c_minimum_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6B_exchangeability_cells.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("minimum_stratum_log_p_value")
    matrix[1][column] = str(float(matrix[1][column]) + 0.01)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S6B-to-S6C minimum"):
        _zip_payload(valid_sources)


def test_cross_table_s6d_to_s6e_aggregate_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6D_label_mondrian_cells.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("baseline_resolved_rows")
    matrix[1][column] = str(int(matrix[1][column]) + 1)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S6D-to-S6E aggregate"):
        _zip_payload(valid_sources)


def test_cross_table_s6f_to_s6e_covered_count_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6F_label_mondrian_categories.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("resolved_label_covered_rows")
    matrix[1][column] = str(int(matrix[1][column]) + 1)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="resolved covered rows disagree with S6E"):
        _zip_payload(valid_sources)


def test_source_path_aliases_are_rejected_before_csv_copy(
    valid_sources: dict[str, Path],
) -> None:
    names = tuple(valid_sources)
    valid_sources[names[1]] = valid_sources[names[0]]

    with pytest.raises(ValueError, match="source paths must be distinct"):
        _zip_payload(valid_sources)
