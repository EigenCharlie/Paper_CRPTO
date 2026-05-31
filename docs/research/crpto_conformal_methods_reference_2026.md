> **RESEARCH NOTE** — Conformal-prediction methods reference, ported and condensed
> from the parent project's `conformal_prediction_research_2026.md`. Technical
> support for the CRPTO methods chapter; the live policy/results are in
> `data/processed/conformal_intervals_mondrian.parquet` and
> `models/conformal_policy_status.json`.

# CRPTO — Conformal Prediction Methods Reference (2026)

Consolidated best practices for conformal prediction applied to PD (probability
of default) intervals, aligned with the CRPTO Mondrian policy. MAPIE 1.4 in the
local environment.

## Book concept → implementation → backlog

| Concept | CRPTO implementation | Backlog (out of scope for the frozen champion) |
|---|---|---|
| Finite-sample validity & exchangeability | Split conformal + Mondrian by `grade`, temporal calibration holdout, explicit policy artifacts | formal shift-aware/online diagnostics under drift (→ A24) |
| Validity ↔ efficiency tradeoff | coverage + width + group-coverage metrics, Pareto tuning, guardbands | richer objective across multiple proper scoring rules |
| Mondrian conditional coverage | `create_pd_intervals_mondrian`, group-floor multipliers, per-group coverage | partitioning beyond `grade`; hierarchical partitions |
| Venn-Abers calibration | candidate calibrator in PD training, interval-ready probabilities | first-class branch in benchmark/policy comparison |
| Statistical interval diagnostics | Winkler + Kupiec + Christoffersen stored in policy status | adaptive/sample-size-aware interpretation layer |
| Cross-conformal regression | not in canonical pipeline (split conformal only) | controlled benchmark with `CrossConformalRegressor` |
| CQR | researched; not in canonical LGD/EAD path | CQR branch for LGD/EAD with heteroscedastic checks |
| Classification sets (LAC/APS/RAPS) | wrappers available, not primary PD gate | multi-class/ambiguity benchmark workflow |

## Conformity scores (regression PD)

- **Absolute residual** (`|y − ŷ|`): default; symmetric intervals.
- **Normalized/locally-weighted**: scale residuals by an estimate of local
  difficulty → heteroscedastic-aware widths.
- **CQR**: conformalize quantile-regression predictions; naturally adaptive width.

## Method comparison (when to use)

| Method | Coverage guarantee | Cost | Use when |
|---|---|---|---|
| Split conformal | marginal, finite-sample | 1 fit + calibration holdout | production path; large `n` (our 276k OOT) |
| Cross-conformal | marginal, tighter on small data | K fits | small calibration sets |
| CQR | marginal, adaptive width | quantile fit + calibration | heteroscedastic targets (LGD/EAD) |
| Jackknife+ | marginal (approx.) | leave-one-out | small `n`, no holdout to spare |
| Mondrian (any of the above) | **per-group** marginal | partition overhead | group-conditional validity (credit `grade`) — **our policy** |

## Mondrian conditional coverage (the CRPTO core)

Partition the score space by a discrete taxonomy (here `grade`, optionally
score-decile) and calibrate **within** each cell. This delivers group-conditional
coverage `P(Y ∈ C(X) | group = g) ≥ 1 − α` per cell, instead of only the marginal
guarantee. The promoted variant is `score_decile_mondrian`; group floor multipliers
lift any cell that falls under the coverage floor.

Why Mondrian and not Kandinsky/covariate-conditional methods: credit grades are
**naturally disjoint and pre-registered**, so the partition is given by the domain
rather than learned — the simpler Mondrian construction is the correct tool and
avoids the extra assumptions of adaptively selected groups.

## Validation metrics tracked in the policy status

| Metric | Meaning | CRPTO winner value |
|---|---|---|
| `coverage_90` | empirical coverage at nominal 90% | 0.9297 |
| `coverage_95` | empirical coverage at nominal 95% | 0.9664 |
| `avg_width_90` | mean interval width | 0.7842 |
| `min_group_coverage_90` | worst per-group coverage | 0.9190 |
| `winkler_90` | Winkler interval score (sharpness + coverage penalty) | 1.1107 |

Statistical backtests (Kupiec, Christoffersen) are stored as **diagnostics**: at
`N = 276,869` the power detects any persistent deviation, so the operational gate
uses a materiality threshold (deviation < 3pp, conservative over-coverage) plus a
methodological-justification layer rather than the raw p-value.

## Shift / online layer (future / Appendix A24)

- **ACI** (`gibbs2021aci`): update the conformal quantile each step,
  `α_{t+1} = α_t + γ·(α − 1{Y_t ∉ Ĉ_t})`, to track coverage under drift.
- **Gradient equilibrium** (`angelopoulos2025gradient`) and **UP-OCP**
  (`liu2026portfolio`): parameter-free online recalibration with finite
  miscoverage bounds — the modern route beyond a generic ACI mention.
- **Covariate shift** (`tibshirani2019covshift`): weighted conformal under known
  likelihood ratios; relevant to the temporal OOT regime.

## Practical notes

- Keep the calibration holdout **temporally separated** from training to respect
  the out-of-time design; do not reuse the OOT evaluation window for calibration.
- Report **both** marginal and worst-group coverage — a marginal 93% can hide a
  group at 59% (the precise failure Mondrian fixes).
- Treat width as a first-class output: it is the parameter the robust portfolio LP
  consumes as the uncertainty set, so width quality is decision-relevant, not cosmetic.
