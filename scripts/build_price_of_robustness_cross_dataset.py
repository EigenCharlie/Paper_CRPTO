"""Build the cross-dataset price-of-robustness table (A34).

Surfaces a finding that is already computed but never displayed: the signed
``price_of_robustness_pct`` of the frozen CRPTO recipe is a *positive* premium on
the external economic panels, and it *increases with the panel default rate*
across frozen applications (no champion search). This reframes the multidataset
layer from a defensive "the gates still pass" claim into a positive, economically
interpretable result: buying the conformal coverage guarantee costs a premium
that scales with the panel's irreducible default risk.

All inputs are frozen: the multidataset external status JSON. No champion stage
and no external replication run is re-executed.

Reading of the sign (same convention as the Lending Club champion field):
``price_of_robustness_pct = (nonrobust - robust) / nonrobust``. A positive value
means robustness costs a premium; a negative value means robustness is favorable.
The Lending Club *selected* champion is ``-10.56%`` (favorable) and is reported in
prose as the selected-protocol contrast, not as a frozen-application row.

Output: reports/crpto/tables/crpto_tableA34_price_of_robustness_cross_dataset.{csv,tex}
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "reports" / "crpto" / "tables"
STATUS = REPO_ROOT / "models" / "crpto_multidataset_external_status.json"


def build_table() -> pd.DataFrame:
    status = json.loads(STATUS.read_text(encoding="utf-8"))

    rows: list[dict[str, object]] = []

    # Freddie FM48 segments (green / combined / red) -- same frozen protocol.
    seg_label = {
        "green": "Freddie FM48 (green)",
        "both": "Freddie FM48 (combined)",
        "red": "Freddie FM48 (red)",
    }
    for seg in status["freddie_segment_sensitivity"]:
        name = seg["segment"]
        if name not in seg_label:
            continue
        rows.append(
            {
                "application": seg_label[name],
                "panel_default_rate": float(seg["default_rate"]),
                "auc_roc": float(seg["auc_roc"]),
                "price_of_robustness_pct": float(seg["price_of_robustness_pct"]),
                "protocol": "frozen_application",
            }
        )

    # Prosper final-status -- same frozen protocol.
    for rep in status["external_replications"]:
        if rep["dataset"] != "Prosper":
            continue
        rows.append(
            {
                "application": "Prosper final-status",
                "panel_default_rate": float(rep["default_rate"]),
                "auc_roc": float(rep["auc_roc"]),
                "price_of_robustness_pct": float(rep["price_of_robustness_pct"]),
                "protocol": "frozen_application",
            }
        )

    df = pd.DataFrame(rows).sort_values("panel_default_rate").reset_index(drop=True)

    # Monotonicity check across frozen applications (descriptive, not a fitted law).
    price = df["price_of_robustness_pct"].to_numpy()
    df.attrs["price_monotone_increasing"] = bool((price[1:] >= price[:-1]).all())
    return df


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df = build_table()

    out = df.copy()
    out["panel_default_rate"] = out["panel_default_rate"].round(6)
    out["auc_roc"] = out["auc_roc"].round(4)
    out["price_of_robustness_pct"] = out["price_of_robustness_pct"].round(6)

    csv_path = TABLES / "crpto_tableA34_price_of_robustness_cross_dataset.csv"
    out.to_csv(csv_path, index=False)

    tex = out.to_latex(index=False, escape=True, float_format=lambda x: f"{x:.4f}")
    (TABLES / "crpto_tableA34_price_of_robustness_cross_dataset.tex").write_text(
        tex, encoding="utf-8"
    )

    logger.info(
        "A34 price of robustness: {} frozen applications, monotone-increasing in default rate = {}",
        len(out),
        df.attrs["price_monotone_increasing"],
    )
    for _, r in out.iterrows():
        logger.info(
            "  {:<26} default={:.4f} price_of_robustness={:+.4f}",
            r["application"],
            r["panel_default_rate"],
            r["price_of_robustness_pct"],
        )
    logger.info("Wrote {}", csv_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
