# Pool93 Tail-Risk Closeout

Date: 2026-07-02

This memo closes the post-promotion caveat that tail-risk and cluster-bound
diagnostics should not be cited as pool93-specific unless regenerated from the
selected pool93 funded allocation.

## Generated Artifacts

- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.csv`
- `reports/crpto/tables/crpto_tableA37_pool93_body_tail_risk.tex`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.csv`
- `reports/crpto/tables/crpto_tableA38_pool93_body_cluster_bound_audit.tex`
- Generator: `scripts/search/build_pool93_tail_risk_audit.py`

The generator reads the selected allocation from:

`data/processed/experiments/champion_reopen/champion-reopen-2026-06-19__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_body_allocation_alpha01.parquet`

## A37 Tail-Risk Repricing

At baseline `LGD = 0.45`, the selected body allocation has:

- realized return: `$184,832.48`
- weighted default rate / `V`: `0.035350`
- realized CVaR95 loss rate: `0.276211`
- decision-time CVaR95 loss rate: `0.218140`
- Markov cap: `0.345084`

Across the LGD grid, repriced return ranges from `$188,367.48` at `LGD = 0.35`
to `$179,529.98` at `LGD = 0.60`.

## A38 Cluster-Bound Repricing

At `alpha = 0.01` and `delta = 0.10`, Markov's body threshold is `0.100000`.
The regenerated cluster-aware Hoeffding thresholds are:

- period: `0.395502`
- grade bucket: `0.728588`
- period-grade: `0.281247`
- score-vintage: `0.348546`

None is tighter than Markov. This supports the manuscript's theory boundary:
Markov remains the body-level distribution-free statement, while cluster-aware
tightening is shown as an assumption-priced sensitivity.

## Claim Boundary

A37 and A38 are selected-allocation risk-profile audits. They do not change the
pool93 body selector and do not make CVaR/OCE the optimized objective. The
paper-facing claim remains the finite-grid return-bound certificate in A35 plus
the exact funded-set audit; A37/A38 close the reviewer question about the
selected point's tail and concentration profile.
