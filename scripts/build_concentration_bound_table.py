"""Build the concentration-bound comparison table (A21b).

Compares the distribution-free Markov tail bound used in the main theorem against
Hoeffding and Bernstein tightenings under an *additional* independence assumption,
using the real frozen funded-set weights. The point is illustrative and honest:
it quantifies exactly how much Markov leaves on the table, and under what extra
assumption a sharper bound would hold -- without re-optimizing or re-promoting the
champion.

All inputs are frozen: the funded-set loan export (weights) and the frozen
weighted miscoverage V = 0.028875. No champion search stage is re-run.

Output: reports/crpto/tables/crpto_tableA21b_concentration_bounds.{csv,tex}
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "reports" / "crpto" / "tables"
FUNDED = TABLES / "crpto_tableA7_funded_set_loans.csv"

# Frozen weighted miscoverage of the promoted champion (alpha = 0.01 exact eval).
EMPIRICAL_V = 0.028875
ALPHAS = [0.01, 0.05, 0.10]


def _funded_weights() -> np.ndarray:
    funded = pd.read_csv(FUNDED)
    w = pd.to_numeric(funded["portfolio_weight"], errors="coerce").fillna(0.0).to_numpy(float)
    total = float(w.sum())
    if total <= 0:
        raise ValueError("Funded-set weights sum to zero.")
    return w / total


def build_table() -> pd.DataFrame:
    w = _funded_weights()
    n = int(w.size)
    sum_w2 = float((w**2).sum())
    n_eff = 1.0 / sum_w2
    max_w = float(w.max())

    rows: list[dict[str, object]] = []
    for alpha in ALPHAS:
        # Match the Markov tail probability delta = sqrt(alpha) for an apples-to-apples
        # threshold comparison: each bound reports the t such that P(V > t) <= delta.
        delta = float(np.sqrt(alpha))
        log_term = float(np.log(1.0 / delta))

        markov_t = float(np.sqrt(alpha))  # Markov: P(V > sqrt(alpha)) <= sqrt(alpha)

        # Hoeffding (independent miscoverage indicators across loans):
        # P(V - E[V] > eps) <= exp(-2 eps^2 / sum w_i^2)
        eps_h = float(np.sqrt(sum_w2 * log_term / 2.0))
        hoeffding_t = alpha + eps_h

        # Bernstein (uses variance): Var(V) <= alpha * sum w_i^2; bounded difference ~ max weight.
        var_v = alpha * sum_w2
        b = max_w
        eps_b = float(
            b * log_term / 3.0 + np.sqrt((b * log_term / 3.0) ** 2 + 2.0 * var_v * log_term)
        )
        bernstein_t = alpha + eps_b

        rows.append(
            {
                "alpha": alpha,
                "expected_V_leq": alpha,
                "empirical_V": EMPIRICAL_V,
                "markov_threshold": round(markov_t, 4),
                "hoeffding_threshold_indep": round(hoeffding_t, 4),
                "bernstein_threshold_indep": round(bernstein_t, 4),
                "tail_prob_delta": round(delta, 4),
                "empirical_V_below_all": bool(
                    min(markov_t, hoeffding_t, bernstein_t) > EMPIRICAL_V
                ),
            }
        )

    df = pd.DataFrame(rows)
    df.attrs["n_funded"] = n
    df.attrs["sum_w2"] = sum_w2
    df.attrs["n_eff"] = n_eff
    return df


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df = build_table()
    csv_path = TABLES / "crpto_tableA21b_concentration_bounds.csv"
    df.to_csv(csv_path, index=False)

    # Minimal LaTeX booktabs export for the supplement.
    tex = df.to_latex(index=False, escape=True, float_format=lambda x: f"{x:.4f}")
    (TABLES / "crpto_tableA21b_concentration_bounds.tex").write_text(tex, encoding="utf-8")

    logger.info(
        "A21b concentration bounds: n_funded={} n_eff={:.1f} sum_w2={:.6f}",
        df.attrs["n_funded"],
        df.attrs["n_eff"],
        df.attrs["sum_w2"],
    )
    logger.info("Wrote {}", csv_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
