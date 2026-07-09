# Pool93 Tail-Risk Closeout

Date: 2026-07-02

Certificate terminology was synchronized on 2026-07-09 with the policy-aware
A35 audit. A37--A39 values remain valid for the fixed selected allocation;
`0.345084` is now called the exact loss threshold, not a generic cap.

This memo closes the post-promotion caveat that tail-risk, cluster-bound, and
bootstrap diagnostics should not be cited as pool93-specific unless regenerated
from the selected pool93 funded allocation.

## Generated Artifacts

- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.csv`
- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.tex`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.csv`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.tex`
- `reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.csv`
- `reports/crpto/tables/crpto_tableA39_pool93_body_bootstrap_metrics.tex`
- Generator: `scripts/search/build_pool93_tail_risk_audit.py`

The generator reads the selected allocation from:

`data/processed/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_body_allocation_alpha01.parquet`

## A37 Tail-Risk Repricing

At baseline `LGD = 0.45`, the selected body allocation has:

- realized return: `$184,832.48`
- weighted default rate / `V`: `0.035350`
- realized CVaR95 loss rate: `0.276211`
- decision-time CVaR95 loss rate: `0.218140`
- exact loss threshold at `alpha = 0.01`: `0.345084`

Across the LGD grid, repriced return ranges from `$188,367.48` at `LGD = 0.35`
to `$179,529.98` at `LGD = 0.60`.

## A38 Cluster-Bound Repricing

At `alpha = 0.01` and `delta = 0.10`, the distribution-free Markov increment
is `sqrt(alpha) = 0.100000`.
The regenerated cluster-aware Hoeffding thresholds are:

- period: `0.395502`
- grade bucket: `0.728588`
- period-grade: `0.281247`
- score-vintage: `0.348546`

None is tighter than the distribution-free Markov step. This supports the
manuscript's theory boundary: the policy-aware certificate remains the
body-level distribution-free statement, while cluster-aware tightening is
shown as an assumption-priced sensitivity.

## A39 Fixed-Allocation Bootstrap

The final pool93 bootstrap diagnostic resamples funded-loan contributions under
the fixed selected body allocation with `5,000` draws and seed `20260702`.

Key baseline results:

- observed baseline return at `LGD = 0.45`: `$184,832.48`
- bootstrap return mean: `$184,623.11`
- bootstrap return interval, 2.5%--97.5%: `$167,963.20` to `$198,650.47`
- observed weighted default / `V`: `0.035350`
- bootstrap `V` interval, 2.5%--97.5%: `0.018157` to `0.057193`
- observed `Gamma_CP`: `0.162616`
- bootstrap `Gamma_CP` interval, 2.5%--97.5%: `0.137160` to `0.193092`
- observed realized CVaR95: `0.276211`
- observed decision-time CVaR95: `0.218140`

This is a fixed-allocation empirical contribution interval. It does not resample
solver inputs, the PD model, calibration data, conformal intervals, or the policy
search.

## Claim Boundary

A37--A39 are selected-allocation risk-profile audits. They do not change the
pool93 body selector, do not make CVaR/OCE the optimized objective, and do not
turn bootstrap intervals into a conformal guarantee. The paper-facing claim
remains the finite-grid policy-aware decision certificate in A35 plus the exact
funded-set audit; A37--A39 close reviewer questions about the selected point's tail,
concentration, and empirical contribution profile.
