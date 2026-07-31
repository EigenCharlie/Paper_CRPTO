"""Retrospective CatBoost calibrator sensitivity under one common taxonomy.

The module deliberately separates the score used for fixed Mondrian group
membership (the uncalibrated CatBoost probability ``q_raw``) from the
calibrated probability used in the absolute residual.  This prevents a change
of calibrator from silently changing the target population of each stratum.

Venn--Abers contributes its standard IVAP scalar probability ``p_prime`` to the
four-way point-calibrator comparison.  The accompanying ``p0``/``p1`` values
are retained as a multiprobability pair; neither ``p_prime`` nor that pair is treated
as a latent-PD interval or as an optimizer-valid conformal guarantee.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from betacal import BetaCalibration
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from venn_abers import VennAbers

from src.evaluation.coverage_transport import binary_miscoverage_bounds
from src.ijds_audit.geometry import BOTH, EMPTY, ONE_ONLY, ZERO_ONLY, binary_set_codes
from src.ijds_audit.prediction import binary_probability_metrics

CALIBRATOR_METHODS = ("platt", "isotonic", "beta", "venn_abers")
WINDOW_IDS = (
    "w01_2012m01_m06",
    "w02_2012m02_m07",
    "w03_2012m03_m08",
    "w04_2012m04_m09",
    "w05_2012m05_m10",
    "w06_2012m06_m11",
    "w07_2012m07_m12",
    "w08_2012m08_2013m01",
)
CANONICAL_GROUPS = 5
VECTOR_HASH_CONTRACT = "little_endian_float64_c_order_sha256_v1"
STRING_HASH_CONTRACT = "utf8_length_prefixed_sha256_v1"


@dataclass(frozen=True)
class CalibratorResidualRecipe:
    """One window's residual thresholds under common ``q_raw`` membership."""

    method: str
    window_id: str
    alpha: float
    taxonomy_edges_q_raw: tuple[float, ...]
    residual_quantiles: tuple[float, ...]
    group_counts: tuple[int, ...]
    finite_sample_ranks: tuple[int, ...]
    raw_finite_sample_ranks: tuple[int, ...]
    taxonomy_provenance: str
    taxonomy_method: str = "fixed_common_catboost_q_raw_edges"
    residual_method: str = "exact_split_mondrian_absolute_residual"
    estimand: str = "binary_outcome_prediction_set"


@dataclass(frozen=True)
class CalibratorFamily:
    """Fitted point-calibration maps used by both locked phases."""

    platt: LogisticRegression
    isotonic: IsotonicRegression
    beta: BetaCalibration
    venn_abers: VennAbers
    venn_abers_precision: int | None = None
    venn_abers_scalarization: str = "p_prime_positive_class"


def float_array_sha256(values: Sequence[float] | np.ndarray) -> str:
    """Hash a numeric vector under an explicit cross-platform byte contract."""
    array = np.asarray(values, dtype="<f8")
    if array.ndim != 1 or not bool(np.isfinite(array).all()):
        raise ValueError("Vector hashing requires one finite numeric dimension.")
    return hashlib.sha256(np.ascontiguousarray(array).tobytes(order="C")).hexdigest()


def string_array_sha256(values: Sequence[object] | pd.Series) -> str:
    """Hash strings without delimiter ambiguity."""
    digest = hashlib.sha256()
    for value in values:
        encoded = str(value).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def _platt_parameters(platt: LogisticRegression) -> tuple[float, float]:
    coefficient = np.asarray(platt.coef_, dtype=float)
    intercept = np.asarray(platt.intercept_, dtype=float)
    if coefficient.shape != (1, 1) or intercept.shape != (1,):
        raise RuntimeError("The frozen Platt calibrator is not a one-margin binary map.")
    if not np.array_equal(np.asarray(platt.classes_), np.array([0, 1])):
        raise RuntimeError("The frozen Platt class order must be exactly [0, 1].")
    slope = float(coefficient[0, 0])
    offset = float(intercept[0])
    if not np.isfinite(slope) or not np.isfinite(offset) or slope <= 0.0:
        raise RuntimeError("The frozen Platt map must have finite positive slope.")
    return offset, slope


def recover_catboost_base_probability(
    platt_probability: Sequence[float] | np.ndarray,
    platt: LogisticRegression,
) -> tuple[np.ndarray, np.ndarray]:
    """Invert the frozen Platt map into raw margin and ``q_raw``."""
    probability = np.asarray(platt_probability, dtype=float)
    if probability.ndim != 1 or not bool(np.isfinite(probability).all()):
        raise ValueError("Frozen Platt probabilities must be one finite vector.")
    if bool(np.any((probability <= 0.0) | (probability >= 1.0))):
        raise RuntimeError("Exact Platt inversion requires probabilities strictly inside (0, 1).")
    offset, slope = _platt_parameters(platt)
    margin = (logit(probability) - offset) / slope
    q_raw = expit(margin)
    if not bool(np.isfinite(margin).all() and np.isfinite(q_raw).all()):
        raise RuntimeError("Platt inversion returned a non-finite base score.")
    if not np.array_equal(q_raw, expit(margin)):
        raise RuntimeError("Recovered q_raw is not exactly expit(raw_margin).")
    return np.asarray(margin, dtype=float), np.asarray(q_raw, dtype=float)


def apply_frozen_platt(platt: LogisticRegression, margin: np.ndarray) -> np.ndarray:
    """Apply one fitted Platt map with strict output validation."""
    probability = np.asarray(
        platt.predict_proba(np.asarray(margin, dtype=float).reshape(-1, 1))[:, 1],
        dtype=float,
    )
    _validate_probability("platt", probability, expected_rows=len(margin))
    return probability


def transform_platt_edges_to_q_raw(
    platt_edges: Sequence[float],
    platt: LogisticRegression,
) -> tuple[float, ...]:
    """Transform the active fixed Platt edges without recomputing quantiles."""
    _, edges = recover_catboost_base_probability(np.asarray(tuple(platt_edges)), platt)
    if len(edges) != CANONICAL_GROUPS + 1 or bool(np.any(np.diff(edges) <= 0.0)):
        raise RuntimeError("Transformed common taxonomy edges are not five strict groups.")
    return tuple(float(value) for value in edges)


def _two_class_probability(q_raw: np.ndarray) -> np.ndarray:
    q = np.asarray(q_raw, dtype=float)
    return np.column_stack((1.0 - q, q))


def fit_calibrator_family(
    *,
    q_raw: Sequence[float] | np.ndarray,
    labels: Sequence[int] | np.ndarray,
    frozen_platt: LogisticRegression,
    venn_abers_precision: int | None = None,
) -> CalibratorFamily:
    """Fit the three alternatives on the exact 2011 Platt-fit population."""
    q = np.asarray(q_raw, dtype=float)
    y = np.asarray(labels)
    if q.ndim != 1 or len(q) == 0 or len(q) != len(y):
        raise ValueError("Calibrator-fit arrays must be nonempty, one-dimensional, and aligned.")
    if not bool(np.isfinite(q).all()) or bool(np.any((q <= 0.0) | (q >= 1.0))):
        raise ValueError("Base probabilities must be finite and strictly inside (0, 1).")
    if not bool(np.isin(y, (0, 1)).all()) or set(np.unique(y.astype(int))) != {0, 1}:
        raise ValueError("Calibrator-fit labels must contain both binary classes.")
    _platt_parameters(frozen_platt)

    isotonic = IsotonicRegression(
        increasing=True,
        y_min=0.0,
        y_max=1.0,
        out_of_bounds="clip",
    )
    isotonic.fit(q, y.astype(int))

    beta = BetaCalibration(parameters="abm")
    beta.fit(q.reshape(-1, 1), y.astype(int))

    venn_abers = VennAbers(setting="classification")
    venn_abers.fit(
        _two_class_probability(q),
        y.astype(int),
        precision=venn_abers_precision,
    )
    family = CalibratorFamily(
        platt=frozen_platt,
        isotonic=isotonic,
        beta=beta,
        venn_abers=venn_abers,
        venn_abers_precision=venn_abers_precision,
    )
    calibrator_state_audit(family)
    return family


def calibrator_state_audit(family: CalibratorFamily) -> dict[str, Any]:
    """Validate fitted estimator state and return compact convergence metadata."""
    _platt_parameters(family.platt)
    iso_x = np.asarray(family.isotonic.X_thresholds_, dtype=float)
    iso_y = np.asarray(family.isotonic.y_thresholds_, dtype=float)
    if (
        iso_x.ndim != 1
        or iso_y.shape != iso_x.shape
        or len(iso_x) < 2
        or not bool(np.isfinite(iso_x).all() and np.isfinite(iso_y).all())
        or bool(np.any(np.diff(iso_x) <= 0.0))
        or bool(np.any(np.diff(iso_y) < 0.0))
        or bool(np.any((iso_y < 0.0) | (iso_y > 1.0)))
    ):
        raise RuntimeError("Isotonic fitted state is invalid or nonmonotone.")

    beta_internal = getattr(family.beta, "calibrator_", None)
    beta_map = np.asarray(getattr(beta_internal, "map_", ()), dtype=float)
    beta_lr = getattr(beta_internal, "lr_", None)
    beta_iterations = np.asarray(getattr(beta_lr, "n_iter_", ()), dtype=int)
    beta_max_iter = int(getattr(beta_lr, "max_iter", 0))
    if (
        beta_map.shape != (3,)
        or not bool(np.isfinite(beta_map).all())
        or beta_map[0] < 0.0
        or beta_map[1] < 0.0
        or beta_iterations.size == 0
        or beta_max_iter <= 0
        or bool(np.any(beta_iterations >= beta_max_iter))
    ):
        raise RuntimeError("Beta calibration state is invalid or did not converge.")

    p0 = np.asarray(getattr(family.venn_abers, "p0_", ()), dtype=float)
    p1 = np.asarray(getattr(family.venn_abers, "p1_", ()), dtype=float)
    knots = np.asarray(getattr(family.venn_abers, "c_", ()), dtype=float)
    if (
        p0.ndim != 2
        or p0.shape[1:] != (2,)
        or p1.shape != p0.shape
        or len(p0) < 2
        or knots.ndim != 1
        or len(knots) != len(p0) - 1
        or not bool(np.isfinite(p0).all() and np.isfinite(p1).all() and np.isfinite(knots).all())
        or bool(np.any(np.diff(p0[:, 0]) < 0.0))
        or bool(np.any(np.diff(p1[:, 0]) < 0.0))
        or bool(np.any(np.diff(knots) < 0.0))
        or not np.array_equal(p0[:, 0], p1[:, 0])
        or not np.array_equal(p0[1:, 0], knots)
        or bool(np.any((p0[:, 1] < 0.0) | (p0[:, 1] > 1.0)))
        or bool(np.any((p1[:, 1] < 0.0) | (p1[:, 1] > 1.0)))
        or bool(np.any(p0[:, 1] > p1[:, 1]))
    ):
        raise RuntimeError("Venn--Abers fitted state is incomplete or non-finite.")
    return {
        "platt_classes": [int(value) for value in family.platt.classes_],
        "isotonic_thresholds": int(len(iso_x)),
        "beta_parameters": {
            "a": float(beta_map[0]),
            "b": float(beta_map[1]),
            "m": float(beta_map[2]),
        },
        "beta_iterations": [int(value) for value in beta_iterations],
        "beta_max_iter": beta_max_iter,
        "venn_abers_state_rows": int(len(p0)),
        "venn_abers_knots": int(len(knots)),
    }


def _validate_probability(name: str, probability: np.ndarray, *, expected_rows: int) -> None:
    if (
        probability.shape != (expected_rows,)
        or not bool(np.isfinite(probability).all())
        or bool(np.any((probability < 0.0) | (probability > 1.0)))
    ):
        raise RuntimeError(f"{name} returned an invalid probability vector.")


def apply_calibrator_family(
    family: CalibratorFamily,
    *,
    q_raw: Sequence[float] | np.ndarray,
    margin: Sequence[float] | np.ndarray,
    frozen_platt_probability: Sequence[float] | np.ndarray | None = None,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Apply all four maps and return the IVAP multiprobability pair separately."""
    q = np.asarray(q_raw, dtype=float)
    raw_margin = np.asarray(margin, dtype=float)
    if q.ndim != 1 or raw_margin.shape != q.shape:
        raise ValueError("Base probability and raw-margin vectors must align.")
    if not bool(np.isfinite(q).all() and np.isfinite(raw_margin).all()):
        raise ValueError("Base score vectors must be finite.")
    base_replay_difference = float(np.max(np.abs(q - expit(raw_margin))))
    if base_replay_difference > 1.0e-15:
        raise RuntimeError(
            "q_raw does not match expit(raw_margin): "
            f"max_abs_difference={base_replay_difference:.3e}."
        )

    applied_platt = apply_frozen_platt(family.platt, raw_margin)
    if frozen_platt_probability is not None:
        source_platt = np.asarray(frozen_platt_probability, dtype=float)
        _validate_probability("frozen_platt_source", source_platt, expected_rows=len(q))
        maximum = float(np.max(np.abs(applied_platt - source_platt)))
        if maximum > 5.0e-14:
            raise RuntimeError(
                f"Frozen Platt source failed algebraic replay: max_abs_difference={maximum:.3e}."
            )
        applied_platt = source_platt

    isotonic = np.asarray(family.isotonic.predict(q), dtype=float).reshape(-1)
    beta = np.asarray(family.beta.predict(q.reshape(-1, 1)), dtype=float).reshape(-1)
    venn_prime_matrix, venn_multiprobability_pair = family.venn_abers.predict_proba(
        _two_class_probability(q)
    )
    venn_prime = np.asarray(venn_prime_matrix, dtype=float)[:, 1]
    multiprobability_pair = np.asarray(venn_multiprobability_pair, dtype=float)

    outputs = {
        "platt": applied_platt,
        "isotonic": isotonic,
        "beta": beta,
        "venn_abers": venn_prime,
    }
    for name, probability in outputs.items():
        _validate_probability(name, probability, expected_rows=len(q))
    if multiprobability_pair.shape != (len(q), 2) or not bool(
        np.isfinite(multiprobability_pair).all()
    ):
        raise RuntimeError("Venn--Abers returned an invalid multiprobability pair.")
    if bool(
        np.any(multiprobability_pair[:, 0] > multiprobability_pair[:, 1])
        or np.any(multiprobability_pair < 0.0)
        or np.any(multiprobability_pair > 1.0)
        or np.any(venn_prime < multiprobability_pair[:, 0] - 1.0e-15)
        or np.any(venn_prime > multiprobability_pair[:, 1] + 1.0e-15)
    ):
        raise RuntimeError(
            "Venn--Abers multiprobability pair or scalar probability violates its domain."
        )
    denominator = 1.0 - multiprobability_pair[:, 0] + multiprobability_pair[:, 1]
    standard = np.divide(
        multiprobability_pair[:, 1],
        denominator,
        out=np.full(len(multiprobability_pair), np.nan, dtype=float),
        where=denominator > 0.0,
    )
    if (
        not bool(np.isfinite(standard).all())
        or float(np.max(np.abs(standard - venn_prime))) > 1e-15
    ):
        raise RuntimeError("Venn--Abers p_prime does not match the standard IVAP formula.")
    return outputs, multiprobability_pair


def monotonicity_audit(
    q_raw: np.ndarray,
    probabilities: Mapping[str, np.ndarray],
    *,
    tolerance: float = 1.0e-14,
) -> dict[str, float]:
    """Return each map's most negative adjacent change after stable sorting."""
    q = np.asarray(q_raw, dtype=float)
    order = np.argsort(q, kind="mergesort")
    result: dict[str, float] = {}
    for method in CALIBRATOR_METHODS:
        values = np.asarray(probabilities[method], dtype=float)[order]
        minimum = float(np.min(np.diff(values))) if len(values) > 1 else 0.0
        if minimum < -float(tolerance):
            raise RuntimeError(f"{method} calibration map is not nondecreasing: {minimum:.3e}.")
        result[method] = minimum
    return result


def fit_common_taxonomy_recipe(
    *,
    method: str,
    window_id: str,
    q_raw: Sequence[float] | np.ndarray,
    calibrated_probability: Sequence[float] | np.ndarray,
    labels: Sequence[int] | np.ndarray,
    alpha: float,
    taxonomy_edges_q_raw: Sequence[float],
    taxonomy_provenance: str,
) -> CalibratorResidualRecipe:
    """Fit residual thresholds while holding common group membership fixed."""
    if method not in CALIBRATOR_METHODS:
        raise ValueError(f"Unknown calibrator method: {method}.")
    q = np.asarray(q_raw, dtype=float)
    probability = np.asarray(calibrated_probability, dtype=float)
    y = np.asarray(labels)
    edges = np.asarray(tuple(taxonomy_edges_q_raw), dtype=float)
    if not (q.shape == probability.shape == y.shape) or q.ndim != 1 or len(q) == 0:
        raise ValueError("Recipe-fit arrays must be nonempty, one-dimensional, and aligned.")
    if (
        edges.shape != (CANONICAL_GROUPS + 1,)
        or not bool(np.isfinite(edges).all())
        or bool(np.any(np.diff(edges) <= 0.0))
    ):
        raise ValueError("Common taxonomy must contain six strict finite edges.")
    _validate_probability(method, probability, expected_rows=len(q))
    if not bool(np.isfinite(q).all()) or not bool(np.isin(y, (0, 1)).all()):
        raise ValueError("Recipe-fit score or outcome vector is invalid.")
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must lie in (0, 1).")

    groups = assign_common_groups(q, edges)
    residual = np.abs(y.astype(float) - probability)
    quantiles: list[float] = []
    counts: list[int] = []
    ranks: list[int] = []
    raw_ranks: list[int] = []
    for group in range(CANONICAL_GROUPS):
        ordered = np.sort(residual[groups == group])
        count = int(len(ordered))
        if count == 0:
            raise RuntimeError(f"Common taxonomy group {group} is empty in {window_id}.")
        raw_rank = int(np.ceil((count + 1) * (1.0 - float(alpha))))
        rank = min(max(raw_rank, 1), count)
        threshold = 1.0 if raw_rank > count else float(ordered[rank - 1])
        counts.append(count)
        raw_ranks.append(raw_rank)
        ranks.append(rank)
        quantiles.append(float(np.clip(threshold, 0.0, 1.0)))
    return CalibratorResidualRecipe(
        method=method,
        window_id=str(window_id),
        alpha=float(alpha),
        taxonomy_edges_q_raw=tuple(float(value) for value in edges),
        residual_quantiles=tuple(quantiles),
        group_counts=tuple(counts),
        finite_sample_ranks=tuple(ranks),
        raw_finite_sample_ranks=tuple(raw_ranks),
        taxonomy_provenance=str(taxonomy_provenance),
    )


def assign_common_groups(
    q_raw: Sequence[float] | np.ndarray,
    taxonomy_edges_q_raw: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Assign common five-group membership from the uncalibrated score."""
    q = np.asarray(q_raw, dtype=float)
    edges = np.asarray(tuple(taxonomy_edges_q_raw), dtype=float)
    if q.ndim != 1 or not bool(np.isfinite(q).all()):
        raise ValueError("Common taxonomy assignment requires one finite score vector.")
    if (
        edges.shape != (CANONICAL_GROUPS + 1,)
        or not bool(np.isfinite(edges).all())
        or bool(np.any(np.diff(edges) <= 0.0))
    ):
        raise ValueError("Common taxonomy edges are invalid.")
    return np.searchsorted(edges[1:-1], q, side="right").astype(np.int8)


def apply_common_taxonomy_recipe(
    *,
    q_raw: Sequence[float] | np.ndarray,
    calibrated_probability: Sequence[float] | np.ndarray,
    recipe: CalibratorResidualRecipe,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply calibrated residual widths under fixed ``q_raw`` membership."""
    q = np.asarray(q_raw, dtype=float)
    probability = np.asarray(calibrated_probability, dtype=float)
    if q.shape != probability.shape:
        raise ValueError("Common score and calibrated probability must align.")
    _validate_probability(recipe.method, probability, expected_rows=len(q))
    groups = assign_common_groups(q, recipe.taxonomy_edges_q_raw)
    threshold = np.asarray(recipe.residual_quantiles, dtype=float)[groups]
    lower = np.clip(probability - threshold, 0.0, 1.0)
    upper = np.clip(probability + threshold, 0.0, 1.0)
    return groups, lower, upper


def recipe_payload(
    recipes: Mapping[str, Mapping[str, CalibratorResidualRecipe]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Serialize the complete four-by-eight recipe grid."""
    return {
        method: {window_id: asdict(recipe) for window_id, recipe in windows.items()}
        for method, windows in recipes.items()
    }


def load_recipe_payload(
    payload: Mapping[str, Any],
) -> dict[str, dict[str, CalibratorResidualRecipe]]:
    """Deserialize recipes after validating the declared method/window keys."""
    result: dict[str, dict[str, CalibratorResidualRecipe]] = {}
    common_edges: tuple[float, ...] | None = None
    for method, raw_windows in payload.items():
        if not isinstance(raw_windows, Mapping):
            raise TypeError(f"Recipe windows for {method!r} are not a mapping.")
        windows: dict[str, CalibratorResidualRecipe] = {}
        for window_id, raw_recipe in raw_windows.items():
            if not isinstance(raw_recipe, Mapping):
                raise TypeError(f"Recipe {method}/{window_id} is not a mapping.")
            values = dict(raw_recipe)
            for field in (
                "taxonomy_edges_q_raw",
                "residual_quantiles",
                "group_counts",
                "finite_sample_ranks",
                "raw_finite_sample_ranks",
            ):
                values[field] = tuple(values[field])
            recipe = CalibratorResidualRecipe(**values)
            if recipe.method != str(method) or recipe.window_id != str(window_id):
                raise RuntimeError("Recipe identity disagrees with its mapping key.")
            edges = np.asarray(recipe.taxonomy_edges_q_raw, dtype=float)
            residuals = np.asarray(recipe.residual_quantiles, dtype=float)
            counts = np.asarray(recipe.group_counts, dtype=int)
            ranks = np.asarray(recipe.finite_sample_ranks, dtype=int)
            raw_ranks = np.asarray(recipe.raw_finite_sample_ranks, dtype=int)
            if (
                recipe.alpha != 0.10
                or edges.shape != (CANONICAL_GROUPS + 1,)
                or not bool(np.isfinite(edges).all())
                or bool(np.any(np.diff(edges) <= 0.0))
                or residuals.shape != (CANONICAL_GROUPS,)
                or not bool(np.isfinite(residuals).all())
                or bool(np.any((residuals < 0.0) | (residuals > 1.0)))
                or counts.shape != (CANONICAL_GROUPS,)
                or bool(np.any(counts <= 0))
                or ranks.shape != (CANONICAL_GROUPS,)
                or raw_ranks.shape != (CANONICAL_GROUPS,)
            ):
                raise RuntimeError(f"Recipe {method}/{window_id} has an invalid field domain.")
            expected_raw = np.ceil((counts + 1) * (1.0 - recipe.alpha)).astype(int)
            expected_rank = np.minimum(np.maximum(expected_raw, 1), counts)
            if not np.array_equal(raw_ranks, expected_raw) or not np.array_equal(
                ranks, expected_rank
            ):
                raise RuntimeError(f"Recipe {method}/{window_id} violates the rank formula.")
            if bool(np.any((raw_ranks > counts) & (residuals != 1.0))):
                raise RuntimeError(
                    f"Recipe {method}/{window_id} omits the finite-sample infinite threshold."
                )
            edge_tuple = tuple(float(value) for value in edges)
            if common_edges is None:
                common_edges = edge_tuple
            elif edge_tuple != common_edges:
                raise RuntimeError("Recipe artifact changed common taxonomy edges.")
            windows[str(window_id)] = recipe
        result[str(method)] = windows
    if tuple(result) != CALIBRATOR_METHODS:
        raise RuntimeError("Recipe artifact does not preserve the locked calibrator order.")
    for method, windows in result.items():
        if tuple(windows) != WINDOW_IDS:
            raise RuntimeError(f"Recipe artifact changed the locked windows for {method}.")
    return result


def calibration_fit_diagnostics(
    labels: np.ndarray,
    probabilities: Mapping[str, np.ndarray],
    venn_multiprobability_pair: np.ndarray,
) -> pd.DataFrame:
    """Report descriptive same-sample fit metrics without ranking methods."""
    rows: list[dict[str, Any]] = []
    for method in CALIBRATOR_METHODS:
        metrics = binary_probability_metrics(
            np.asarray(labels, dtype=int),
            np.asarray(probabilities[method], dtype=float),
        )
        rows.append(
            {
                "method": method,
                **metrics,
                "venn_multiprobability_gap_mean": (
                    float(
                        np.mean(venn_multiprobability_pair[:, 1] - venn_multiprobability_pair[:, 0])
                    )
                    if method == "venn_abers"
                    else np.nan
                ),
                "same_sample_descriptive_only": True,
                "selection_metric": False,
            }
        )
    return pd.DataFrame(rows)


def geometry_summary(
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[str, float | int]:
    """Return compact interval and binary-set efficiency summaries."""
    codes = binary_set_codes(lower, upper)
    width = np.asarray(upper, dtype=float) - np.asarray(lower, dtype=float)
    cardinality = (codes == ZERO_ONLY).astype(int)
    cardinality += (codes == ONE_ONLY).astype(int)
    cardinality += 2 * (codes == BOTH).astype(int)
    result: dict[str, float | int] = {
        "rows": int(len(codes)),
        "mean_width": float(np.mean(width)),
        "average_set_size": float(np.mean(cardinality)),
        "singleton_share": float(np.mean((codes == ZERO_ONLY) | (codes == ONE_ONLY))),
        "set_empty_count": int(np.sum(codes == EMPTY)),
        "set_empty_share": float(np.mean(codes == EMPTY)),
        "set_zero_only_count": int(np.sum(codes == ZERO_ONLY)),
        "set_zero_only_share": float(np.mean(codes == ZERO_ONLY)),
        "set_one_only_count": int(np.sum(codes == ONE_ONLY)),
        "set_one_only_share": float(np.mean(codes == ONE_ONLY)),
        "set_both_count": int(np.sum(codes == BOTH)),
        "set_both_share": float(np.mean(codes == BOTH)),
        "lower_positive_share": float(np.mean(np.asarray(lower) > 1.0e-12)),
        "upper_saturated_share": float(np.mean(np.asarray(upper) >= 1.0 - 1.0e-12)),
    }
    for quantile in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        result[f"width_q{int(round(100.0 * quantile)):02d}"] = float(np.quantile(width, quantile))
    return result


def coverage_cell(
    *,
    outcomes: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[str, float | int]:
    """Return sharp finite-population coverage bounds and efficiency."""
    y, low, high = _validated_evaluation_arrays(outcomes, lower, upper)
    miss_low, miss_high = binary_miscoverage_bounds(y, low, high)
    resolved = np.isfinite(y)
    if not bool(resolved.any()):
        raise RuntimeError("Every evaluation cell must contain resolved outcomes.")
    resolved_y0 = resolved & (y == 0.0)
    resolved_y1 = resolved & (y == 1.0)
    result: dict[str, float | int] = {
        "candidate_rows": int(len(y)),
        "resolved_rows": int(resolved.sum()),
        "unresolved_rows": int((~resolved).sum()),
        "coverage_resolved": float(1.0 - miss_low[resolved].mean()),
        "coverage_lower": float(1.0 - miss_high.mean()),
        "coverage_upper": float(1.0 - miss_low.mean()),
        "coverage_resolved_y0": (
            float(1.0 - miss_low[resolved_y0].mean()) if bool(resolved_y0.any()) else np.nan
        ),
        "coverage_resolved_y1": (
            float(1.0 - miss_low[resolved_y1].mean()) if bool(resolved_y1.any()) else np.nan
        ),
    }
    return {**result, **geometry_summary(low, high)}


def shared_completion_coverage_difference(
    *,
    outcomes: np.ndarray,
    lower_a: np.ndarray,
    upper_a: np.ndarray,
    lower_b: np.ndarray,
    upper_b: np.ndarray,
) -> dict[str, float | int]:
    """Sharp A-minus-B coverage bounds under one loan-wise completion."""
    y, validated_lower_a, validated_upper_a = _validated_evaluation_arrays(
        outcomes,
        lower_a,
        upper_a,
    )
    _, validated_lower_b, validated_upper_b = _validated_evaluation_arrays(
        outcomes,
        lower_b,
        upper_b,
    )
    arrays = (
        validated_lower_a,
        validated_upper_a,
        validated_lower_b,
        validated_upper_b,
    )
    observed = np.isfinite(y)
    cover_a_observed = (y >= arrays[0]) & (y <= arrays[1])
    cover_b_observed = (y >= arrays[2]) & (y <= arrays[3])
    difference_observed = cover_a_observed.astype(float) - cover_b_observed.astype(float)
    cover_a_zero = (arrays[0] <= 0.0) & (arrays[1] >= 0.0)
    cover_a_one = (arrays[0] <= 1.0) & (arrays[1] >= 1.0)
    cover_b_zero = (arrays[2] <= 0.0) & (arrays[3] >= 0.0)
    cover_b_one = (arrays[2] <= 1.0) & (arrays[3] >= 1.0)
    difference_zero = cover_a_zero.astype(float) - cover_b_zero.astype(float)
    difference_one = cover_a_one.astype(float) - cover_b_one.astype(float)
    lower = np.where(
        observed,
        difference_observed,
        np.minimum(difference_zero, difference_one),
    )
    upper = np.where(
        observed,
        difference_observed,
        np.maximum(difference_zero, difference_one),
    )
    return {
        "candidate_rows": int(len(y)),
        "resolved_rows": int(observed.sum()),
        "unresolved_rows": int((~observed).sum()),
        "coverage_difference_resolved": float(np.mean(difference_observed[observed])),
        "coverage_difference_lower": float(np.mean(lower)),
        "coverage_difference_upper": float(np.mean(upper)),
        "shared_loanwise_completion": True,
    }


def _validated_evaluation_arrays(
    outcomes: Sequence[float] | np.ndarray,
    lower: Sequence[float] | np.ndarray,
    upper: Sequence[float] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Validate binary outcomes and interval endpoints before evaluation."""
    y = np.asarray(outcomes, dtype=float)
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    if y.ndim != 1 or len(y) == 0 or low.shape != y.shape or high.shape != y.shape:
        raise ValueError("Evaluation arrays must be nonempty, one-dimensional, and aligned.")
    resolved = np.isfinite(y)
    if not bool(resolved.any()) or not bool(np.isin(y[resolved], (0.0, 1.0)).all()):
        raise ValueError("Evaluation outcomes must contain resolved binary values or NaN.")
    if bool(np.isinf(y).any()):
        raise ValueError("Evaluation outcomes cannot contain infinite values.")
    if (
        not bool(np.isfinite(low).all() and np.isfinite(high).all())
        or bool(np.any(low < 0.0))
        or bool(np.any(high > 1.0))
        or bool(np.any(low > high))
    ):
        raise ValueError("Evaluation endpoints must be finite ordered values in [0, 1].")
    return y, low, high


def unordered_method_pairs() -> tuple[tuple[str, str], ...]:
    """Return the locked six unordered pairs in deterministic order."""
    return tuple(combinations(CALIBRATOR_METHODS, 2))
