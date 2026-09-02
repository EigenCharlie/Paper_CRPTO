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
        "Table_S2C_calibrator_fit_diagnostics.csv": 4,
        "Table_S6B_exchangeability_cells.csv": 40,
        "Table_S6C_exchangeability_strata.csv": 200,
        "Table_S6D_label_mondrian_cells.csv": 40,
        "Table_S6E_label_mondrian_strata.csv": 200,
        "Table_S6F_label_mondrian_categories.csv": 400,
        "Table_S6J_common_panel_threshold_response_strata.csv": 175,
        "Table_S6K_common_panel_threshold_response_learners.csv": 35,
        "Table_S6L_residual_transport_summary.csv": 5,
        "Table_S6M_residual_transport_pooled.csv": 200,
        "Table_S6N_marginal_score_outcome_gap.csv": 5,
        "Table_S6O_calibrator_sensitivity_cells.csv": 192,
        "Table_S6P_calibrator_pairwise_shared_completion.csv": 288,
        "Table_S9G_decision_catalog_metric_separation.csv": 3,
        "Table_S9H_decision_catalog_target_blocks.csv": 45,
        "Table_S9I_funded_selection_track_estimands.csv": 96,
        "Table_S9J_funded_selection_gamma_contrasts.csv": 48,
        "Table_S9K_set_preserving_embedding_allocation_summary.csv": 3,
        "Table_S9L_set_preserving_embedding_direction_census.csv": 6,
    }
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert len(archive.namelist()) == 20
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


def test_current_zip_has_complete_closed_calibrator_family() -> None:
    with zipfile.ZipFile(OUTPUT) as archive:
        fit = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("Table_S2C_calibrator_fit_diagnostics.csv").decode("utf-8")
                )
            )
        )
        cells = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("Table_S6O_calibrator_sensitivity_cells.csv").decode("utf-8")
                )
            )
        )
        pairwise = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("Table_S6P_calibrator_pairwise_shared_completion.csv").decode(
                        "utf-8"
                    )
                )
            )
        )

    methods = {"platt", "isotonic", "beta", "venn_abers"}
    assert len(fit) == 4
    assert {row["method"] for row in fit} == methods
    assert {row["same_sample_descriptive_only"] for row in fit} == {"True"}
    assert {row["selection_metric"] for row in fit} == {"False"}

    assert len(cells) == 192
    assert {row["method"] for row in cells} == methods
    assert {row["window_id"] for row in cells} == {
        f"w0{index}_2012m0{index}_m0{index + 5}" for index in range(1, 4)
    } | {
        "w04_2012m04_m09",
        "w05_2012m05_m10",
        "w06_2012m06_m11",
        "w07_2012m07_m12",
        "w08_2012m08_2013m01",
    }
    assert {row["conformal_group"] for row in cells} == {"-1", "0", "1", "2", "3", "4"}
    overall = [row for row in cells if row["conformal_group"] == "-1"]
    assert len(overall) == 32
    assert sum(row["coverage_upper_below_nominal"] == "True" for row in overall) == 18
    assert Counter(
        row["method"] for row in overall if row["coverage_upper_below_nominal"] == "True"
    ) == Counter({"platt": 8, "beta": 8, "isotonic": 1, "venn_abers": 1})

    assert len(pairwise) == 288
    assert {row["shared_loanwise_completion"] for row in pairwise} == {"True"}
    assert (
        len(
            {
                (
                    row["method_a"],
                    row["method_b"],
                    row["window_id"],
                    row["conformal_group"],
                )
                for row in pairwise
            }
        )
        == 288
    )
    forbidden = ("allocation", "portfolio", "objective", "net_return")
    assert not any(
        token in column.lower()
        for rows in (fit, cells, pairwise)
        for column in rows[0]
        for token in forbidden
    )


def test_machine_readable_supplement_is_current_and_anonymous() -> None:
    payload = _zip_payload()
    assert OUTPUT.read_bytes() == payload

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == sorted(["README.txt", *SOURCE_FILENAMES])
        combined = b"\n".join(archive.read(name).lower() for name in archive.namelist())

    for forbidden in FORBIDDEN_FINGERPRINTS:
        assert forbidden not in combined
    for _, pattern in FORBIDDEN_FINGERPRINT_PATTERNS:
        assert pattern.search(combined) is None

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        s6b_payload = archive.read("Table_S6B_exchangeability_cells.csv")
        s6b_header = tuple(s6b_payload.splitlines()[0].decode("utf-8").split(","))
    assert s6b_header == S6B_PUBLICATION_COLUMNS


def test_display_labels_are_crosswalked_to_historical_csv_stems() -> None:
    expected = {
        "S2": ("table6_credit_controls", "tableS2_credit_prediction_metrics"),
        "S6": ("table1_coverage_windows", "tableS6A_conformal_set_diagnostics"),
        "S7 Panels A--B": ("table2_phase_transition",),
        "S7B": ("tableS5_label_lag_sensitivity",),
        "S7C": ("tableS9_missingness_encoding_sensitivity",),
        "S7F": ("tableS11_fit_label_completion",),
        "S9": ("table5_two_ruler_tracks",),
        "S9B--S9C": ("tableS6_endpoint_availability_sensitivity",),
        "S9D--S9E": ("tableS7_portfolio_structure_sensitivity",),
        "S9F": ("tableS12_allocation_granularity",),
        "S10": ("tableS1_named_comparators",),
        "S11": ("table4_direction_summary",),
    }
    with zipfile.ZipFile(OUTPUT) as archive:
        archive_readme = archive.read("README.txt").decode("utf-8")
    submission_readme = Path("paper/submission/README.md").read_text(encoding="utf-8")

    for label, stems in expected.items():
        assert label in archive_readme
        assert label in submission_readme
        for stem in stems:
            assert stem in archive_readme
            assert stem in submission_readme


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


def test_all_nineteen_source_contracts_validate_and_preserve_csv_bytes(
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
        ("Table_S6L_residual_transport_summary.csv", "pooled_cells", "39"),
        (
            "Table_S6M_residual_transport_pooled.csv",
            "v5_q_and_coverage_reconciled",
            "False",
        ),
        ("Table_S6N_marginal_score_outcome_gap.csv", "joint_endpoint_attainment", "False"),
        ("Table_S2C_calibrator_fit_diagnostics.csv", "selection_metric", "True"),
        ("Table_S6O_calibrator_sensitivity_cells.csv", "role", "secondary"),
        (
            "Table_S6P_calibrator_pairwise_shared_completion.csv",
            "shared_loanwise_completion",
            "False",
        ),
        (
            "Table_S9G_decision_catalog_metric_separation.csv",
            "all_target_blocks_exceed_development",
            "False",
        ),
        ("Table_S9H_decision_catalog_target_blocks.csv", "classification", "crossing"),
        ("Table_S9I_funded_selection_track_estimands.csv", "role", "secondary"),
        (
            "Table_S9J_funded_selection_gamma_contrasts.csv",
            "gamma1_minus_gamma0_count_selected_fcp_direction",
            "crossing",
        ),
        (
            "Table_S9K_set_preserving_embedding_allocation_summary.csv",
            "sets_changed",
            "1",
        ),
        (
            "Table_S9L_set_preserving_embedding_direction_census.csv",
            "contrast_family",
            "selected_embedding_contrast",
        ),
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


def test_calibrator_fit_rejects_non_venn_multiprobability_diagnostic(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S2C_calibrator_fit_diagnostics.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    method = matrix[0].index("method")
    gap = matrix[0].index("venn_multiprobability_gap_mean")
    row = next(values for values in matrix[1:] if values[method] == "platt")
    row[gap] = "0.01"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="Venn-only multiprobability diagnostic"):
        _reviewer_csv_payload(name, path)


def test_calibrator_nominal_flag_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6O_calibrator_sensitivity_cells.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    flag = matrix[0].index("coverage_upper_below_nominal")
    matrix[1][flag] = "False" if matrix[1][flag] == "True" else "True"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="nominal-coverage flag"):
        _reviewer_csv_payload(name, path)


def test_calibrator_pairwise_resolved_difference_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6P_calibrator_pairwise_shared_completion.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("coverage_difference_resolved")
    matrix[1][column] = str(float(matrix[1][column]) + 0.0001)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S6O-to-S6P resolved coverage difference"):
        _zip_payload(valid_sources)


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


def test_cross_table_s6l_to_s6m_direction_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S6L_residual_transport_summary.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("larger_target_residual_discrepancy_dominates")
    matrix[1][column] = str(int(matrix[1][column]) + 1)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S6L-to-S6M direction census"):
        _zip_payload(valid_sources)


def test_cross_table_s9g_to_s9h_margin_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S9G_decision_catalog_metric_separation.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("minimum_separation_margin")
    matrix[1][column] = str(float(matrix[1][column]) + 0.01)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="S9G-to-S9H minimum_separation_margin"):
        _zip_payload(valid_sources)


def test_funded_estimand_positive_gap_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S9I_funded_selection_track_estimands.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("count_selected_minus_invested_dollar_selected_coverage_lower")
    matrix[1][column] = "0.0"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="lower endpoint is not positive"):
        _zip_payload(valid_sources)


def test_set_preserving_embedding_allocation_fraction_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S9K_set_preserving_embedding_allocation_summary.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    column = matrix[0].index("allocation_change_fraction")
    matrix[1][column] = "0.5"
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="allocation-change fraction"):
        _zip_payload(valid_sources)


def test_set_preserving_embedding_exact_direction_census_drift_is_rejected(
    valid_sources: dict[str, Path],
) -> None:
    name = "Table_S9L_set_preserving_embedding_direction_census.csv"
    path = valid_sources[name]
    matrix = _csv_matrix(path)
    negative = matrix[0].index("negative")
    positive = matrix[0].index("positive")
    matrix[1][negative] = str(int(matrix[1][negative]) + 1)
    matrix[1][positive] = str(int(matrix[1][positive]) - 1)
    _write_csv_matrix(path, matrix)

    with pytest.raises(RuntimeError, match="exact direction census changed"):
        _zip_payload(valid_sources)


def test_source_path_aliases_are_rejected_before_csv_copy(
    valid_sources: dict[str, Path],
) -> None:
    names = tuple(valid_sources)
    valid_sources[names[1]] = valid_sources[names[0]]

    with pytest.raises(ValueError, match="source paths must be distinct"):
        _zip_payload(valid_sources)
