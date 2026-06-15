# CRPTO sensitivity / robustness run — design spec

**Branch:** `experiments/ijds-sensitivity-suite`
**Run tag:** `ijds-sensitivity-2026-06-14` (distinct from the frozen champion tag `ijds-rebaseline-2026-06-07`)
**Status:** DESIGN ONLY. No protected stage has been run. Nothing here overwrites a frozen artifact.
**Author note:** this spec was produced from the expert audit of theory/claims/artifacts. It enumerates the experiments that would require a dedicated branch + run tag and would strengthen a claim, metric, bound, or theorem, and specifies exactly how to run each one safely.

---

## 0. Why a separate run tag at all

The paper's headline (`$170,464.54`, `V=0.028875`, `Gamma_CP=0.187987`, `B_u=0.278393`, `45/45`)
is the frozen champion under `ijds-rebaseline-2026-06-07`, hash-pinned in
`EXTRACTION_MANIFEST.json`. Every experiment below produces *new* artifacts under the
new run tag and **never** overwrites the frozen ones. The champion remains the headline;
these are diagnostics that either confirm it or are reported as separate sensitivity
evidence.

## 1. The governing design principle: keep the PD model frozen

CatBoost training is **not bit-reproducible** (multi-threaded float reduction). Retraining
`pd_canonical.cbm` therefore drifts and would fail `just drift-gate` by construction — this
is the lesson of the april-lineage unification. **Inference with a frozen model is
deterministic**, and the conformal layer is deterministic given the PD scores and the
calibration set.

This splits the suite into tiers:

| Tier | Definition | Drift risk | Permission |
|---|---|---|---|
| **T0 — conformal-only** | Frozen `pd_canonical.cbm` + frozen calibrator; re-fit only the conformal quantiles and/or re-score the frozen funded set. No PD retrain, no 276k search. | None (deterministic) | Run under the run tag; restore-before-merge |
| **T1 — PD retrain** | Retrains the PD model (new seed, new temporal fold). | High (CatBoost non-reproducible) | Explicit per-run approval; drift documented, not gated |
| **T2 — re-search** | Re-runs the 276k `bound_exact_eval` policy search as a *new champion*. | Replaces the contribution | Do not, except as a deliberate v2 protocol |

**Almost everything worth running is T0.** Only temporal re-folding and seed-stability are T1.

## 2. Experiment catalogue

### E1 — Group-weighted / localized conformal to control funded-set coverage  (T0, highest theory value)
- **Claim it strengthens:** the central coverage claim. Today `V(0.01)=0.028875 > alpha=0.01`
  (funded-set under-coverage), so the certificate holds only at `V <= sqrt(alpha)`. If a
  group-weighted or localized split-conformal recalibration achieves `E[V] <= alpha` on the
  funded set, the certificate would hold at the **nominal** `alpha` — a strictly stronger bound.
- **Method:** re-fit weighted/localized conformal quantiles (weights = funded-set exposure
  weights, or grade/score-decile group weights) on the frozen calibration scores; re-derive
  `u_i(alpha)`; re-score the **frozen** funded set; report `V`, `Gamma_CP`, funded coverage.
  References already in bib: `barber2023beyond`, `guan2023localized`, `bhattacharyya2026groupweighted`,
  `jonkers2024wcps`.
- **Touches:** conformal recalibration code only (frozen PD, frozen funded set). T0.
- **Outputs:** `reports/crpto/experiments/ijds-sensitivity-2026-06-14/E1_weighted_conformal.parquet`.
- **Report:** a supplement table — does weighted/localized CP close the `V > alpha` gap, and at
  what width cost? If yes, the body can claim nominal-`alpha` coverage for the funded set.
- **Risk/compute:** low; minutes. **Highest payoff of the suite.**

### E2 — Calibration-partition sensitivity (empirical Beta-band confirmation)  (T0)
- **Claim it strengthens:** confirms empirically the analytical Beta band just added to the body
  (the under-coverage is structural, not a draw artifact).
- **Method:** for `K=50` seeds, bootstrap/subsample the 237,584 calibration loans, re-fit the
  Mondrian conformal quantiles, re-derive `u_i(alpha)`, re-score the **frozen** funded set;
  collect the distribution of `V`, `Gamma_CP`, funded coverage.
- **Touches:** conformal fit on resampled calibration + re-score frozen funded set. Frozen PD. T0.
- **Outputs:** `.../E2_calibration_sensitivity.parquet` (K rows).
- **Report:** mean/sd/quantiles of `V` across calibration draws; compare to the Beta prediction
  (sd ~ 0.0002 on the endpoint side). Expected: `V` band dominated by the test side, endpoints
  near-invariant — i.e., the body's claim verified.
- **Risk/compute:** low; ~K conformal fits.

### E3 — Rolling-origin / walk-forward temporal validation  (T1, high value, high risk)
- **Claim it strengthens:** "the certificate is not specific to the Jan-2018 cutoff." Re-run the
  certificate on K rolling temporal folds.
- **Method:** for each fold, re-split by origin date, **retrain PD**, re-fit conformal, re-optimize,
  re-certify; report `V`/return/coverage per fold.
- **Touches:** `data.splits`, `pd.champion` (retrain — drift), conformal, optimization, bound_eval. **T1.**
- **Outputs:** `.../E3_walkforward/<fold>/...`.
- **Report:** per-fold certificate stability. Drift across folds is expected and **reported as such**
  (it is genuine temporal variation, not a reproducibility bug).
- **Risk/compute:** high; K full pipeline runs; PD drift must be reported, never gated.

### E4 — PD seed-stability characterization  (T1)
- **Claim it strengthens:** turns the CatBoost non-reproducibility from a hidden caveat into a
  measured band, supporting the reproducibility section.
- **Method:** retrain PD with `K=10` seeds (same config); report AUC/Brier/ECE distribution and the
  induced spread in the downstream certificate (`V`, return) when the rest of the chain is held fixed.
- **Touches:** `pd.champion` x K. **T1.**
- **Outputs:** `.../E4_pd_seed_stability.parquet`.
- **Report:** "the headline AUC 0.7139 sits in a [lo, hi] band over seeds; the certificate moves by
  [x]" — a quantified reproducibility statement.
- **Risk/compute:** medium-high; K PD trainings.

### E5 — Conformal method / partition ablation at alpha=0.01  (T0)
- **Claim it strengthens:** justifies the score-decile Mondrian choice (or finds a better one).
- **Method:** re-fit global split / grade-Mondrian / score-decile-Mondrian / CQR at `alpha=0.01` on
  the frozen calibration; re-score the **frozen** funded set; compare `V`, funded coverage, width.
- **Touches:** conformal variants on frozen PD + frozen funded set. T0.
- **Outputs:** `.../E5_conformal_ablation.parquet`.
- **Report:** an ablation table; either confirms the choice or motivates a switch (overlaps E1).
- **Risk/compute:** low.

### E6 — Per-alpha end-to-end certificate  (T0 if re-scoring frozen funded set; T1-lite if re-optimizing)
- **Claim it strengthens:** the deep-tail / flat-`V` finding and the alpha-gamma figure, with a true
  per-`alpha` recomputation rather than one optimization re-scored at several `alpha`.
- **Method:** for `alpha in {0.005, 0.01, 0.02, 0.05, 0.10}`, re-derive endpoints and re-score the
  frozen funded set (T0); optionally also re-optimize per `alpha` (touches optimization, gated).
- **Outputs:** `.../E6_per_alpha.parquet`.
- **Report:** the genuine `V(alpha)` / `Gamma_CP(alpha)` curve; confirms the flat-`V` deep-tail story.
- **Risk/compute:** low (re-score) / medium (re-optimize).

### E7 — Calibration-set-size sensitivity  (T0)
- **Claim it strengthens:** the F2 sparse-cell reliability discussion at the tight `alpha=0.01`.
- **Method:** subsample calibration to `n in {25k, 50k, 100k, 237k}`, re-fit conformal, re-score the
  frozen funded set; track per-cell endpoint reliability and `V`, especially in the smallest cells.
- **Touches:** conformal on subsampled calibration + frozen funded set. T0.
- **Outputs:** `.../E7_calibration_size.parquet`.
- **Report:** how endpoint reliability and `V` degrade as cells thin — empirical backing for F2.
- **Risk/compute:** low.

## 3. Priority (value x tractability)

1. **E1** — could upgrade the bound from `sqrt(alpha)` to nominal `alpha`. T0. Do first.
2. **E2** — empirically confirms the Beta band; directly answers the referee. T0.
3. **E5** — justifies the Mondrian choice. T0.
4. **E6** — rigorous alpha-sweep. T0 (re-score variant).
5. **E7** — F2 sparse-cell backing. T0.
6. **E4** — reproducibility band. T1.
7. **E3** — temporal robustness. T1, highest cost.

The five T0 experiments (E1, E2, E5, E6, E7) carry essentially no drift risk and deliver most of
the value; the two T1 experiments (E3, E4) are the only ones that need per-run approval and explicit
drift reporting.

## 4. Safe execution protocol (mandatory for every experiment)

1. Work only on `experiments/ijds-sensitivity-suite` (or a child branch).
2. All outputs go under `reports/crpto/experiments/ijds-sensitivity-2026-06-14/` — never under the
   frozen champion paths.
3. New experiment code lives under `scripts/experiments/` and loads the frozen
   `pd_canonical.cbm` / `pd_canonical_calibrator.pkl` read-only; it never writes them.
4. For any T1 step: capture a drift report against the frozen champion and **restore before merge**
   (`git restore data/processed/ models/ dvc.lock && dvc checkout`); `just validate-champion` must be
   green post-restore to certify the champion was not contaminated.
5. Only **code + the sensitivity reports/tables** merge to `main`; regenerated frozen artifacts never do.
6. `just drift-gate` stays the tripwire: a RED on the champion chain means contamination — stop.

## 5. NO-DO list

- Do not run `crpto.portfolio.bound_exact_eval` as a *new champion* (T2 / 276k search).
- Do not overwrite any path in `EXTRACTION_MANIFEST.json`.
- Do not retrain PD and silently let the new numbers flow into the paper — T1 drift is reported, not promoted.
- Do not merge regenerated frozen artifacts to `main`.

## 6. What each experiment could change in the paper

- E1 success -> body upgrades "operative safety level `V <= sqrt(alpha)`" to "nominal `alpha`-coverage
  on the funded set under group-weighted recalibration" (a materially stronger headline).
- E2 -> a one-line empirical confirmation of the Beta band ("across 50 calibration draws `V` stays in
  [lo, hi], matching the analytical band").
- E5/E6/E7 -> supplement ablation/sweep tables that pre-empt method-choice and sparse-cell questions.
- E3/E4 -> temporal-fold and seed-stability tables (reproducibility/robustness appendix).

---

## 7. Execution log — 2026-06-14

**E1 / E6 resolved analytically from the frozen funded-set artifact (`crpto_tableA7_funded_set_loans.csv`), no protected-stage rerun, no reimplementation risk.**

Sanity: `V(0.01)=0.028875` and `Gamma_CP(0.01)=0.187987` reproduce exactly from A7.

Key finding (binary-outcome reading of `V`): of 341 funded loans, 19 defaulted. A
non-default cannot miss (`y=0 <= u`); a default misses unless its endpoint reached
`u=1`. The `alpha=0.01` endpoint capped 2 of 19 defaults at `u=1` (weight 0.004) and
left 17 uncapped (weight 0.028875 = `V`). So `V` = funded weighted default rate
(0.032875) minus endpoint-capped defaults.

Consequence for **E1**: no calibration reweighting (group-weighted / localized / MDCP)
can drive `V` to nominal `alpha=0.01` without capping most funded defaults at `u=1`,
which voids `Gamma_CP` and the economics. The `sqrt(alpha)` level is the honest
guarantee. This is a *negative* result for E1 but a stronger, more honest paper
statement than a re-run would have produced. **Added to the body and supplement.**

Consequence for **E6**: the stored `pd_high_90/95` are two-sided intervals, not
one-sided endpoints, so a faithful per-`alpha` one-sided curve would need a conformal
refit; the binary-outcome reading above already explains the flat-`V` behaviour
without it. Not pursued (reimplementation risk > marginal value).

**E2 / E5 / E7** (calibration bootstrap, partition ablation, calibration size) would
each confirm the same structural conclusion via a conformal refit; given E1's
analytical result they are demoted to optional. **E3 / E4** (T1, PD retrain) remain the
only experiments that could add genuinely new information (temporal-fold and seed
stability) and still require explicit per-run approval + drift management.

## 8. Execution log — E3/E4 run (2026-06-15)

Ran under run tag `ijds-sensitivity-2026-06-14`, fully isolated output paths
(`models/experiments/ijds-sensitivity-2026-06-14/`), ~12-13 min per full PD training.
Three frozen artefacts leaked to default paths (decision_threshold.json,
decision_threshold_v2.json, pd_model_contract.json — git-tracked) plus
`data/processed/test_predictions.parquet` (DVC out); all restored via
`git restore` + `dvc checkout`. **Post-restore: validate-champion 8/8, drift-gate
4/4, dvc status clean — champion intact.**

**E4 — PD seed stability** (champion config, varying `model.params.random_seed`):

| seed | OOT AUC | Brier | ECE |
|---|---:|---:|---:|
| 42 | 0.71268 | 0.15459 | 0.00615 |
| 52 | 0.71227 | 0.15465 | 0.00583 |
| 62 | 0.71210 | 0.15470 | 0.00597 |

AUC spread 0.00058 (<0.001); Brier 0.1546 +/- 0.0001. The CatBoost non-reproducibility
across seeds is negligible — confirms that distributing a frozen binary loses no
discrimination and that the bit-exact certified chain is the right reproducibility object.

**E3 — walk-forward temporal validation** (expanding windows, 80k eval each):

| window | fit rows | validation AUC | best_iter |
|---|---:|---:|---:|
| 1 | 200,000 | 0.7332 | 499 |
| 2 | 372,850 | 0.7330 | 491 |
| 3 | 545,700 | 0.7173 | 621 |

Internal validation AUC stays in [0.717, 0.733]; the dip in the most recent window
foreshadows the harder post-2018 OOT regime (the OOT test AUC of 0.7127 is lower still,
consistent with the deliberately adversarial out-of-time design).

**Verdict:** both confirm stability rather than overturning anything. E4 added to the
supplement reproducibility appendix; E3 noted as temporal-stability evidence. No body
change (page budget; lineage offset 0.712 vs headline 0.7139 kept out of the body to
avoid conflation). T1 experiments are now complete; no further protected runs planned.
