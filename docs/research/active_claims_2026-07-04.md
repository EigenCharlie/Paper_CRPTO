# CRPTO Historical v7 Claim Registry - 2026-07-09

> **Scientific status override (2026-07-10): NO-GO.** This file records the
> compact v7 claim exactly as frozen; it is no longer the source of an active
> submission claim. The exhaustive audit found outcome-conditioned candidate
> membership, label contamination in the conformal recipe, an incoherent
> economic objective, and a pooled future menu. Read
> `ijds_state_of_art_audit_2026-07-10.md` and
> `ijds_three_front_reconstruction_2026-07-10.md` before any paper or evidence
> work. Keep the values below for replay provenance only.

This file is the source of truth for the historical v7 IJDS-facing claims. The recorded result is a
simple, calibration-selected 90% conformal guardrail. Older pool93 frontier
files remain immutable provenance under `EXTRACTION_MANIFEST.json`; they are no
longer evidence for the manuscript's main claim.

## Active Decision

- Run tag:
  `champion-reopen-2026-06-19__pool93__ijds-calibration-selected-endpoint28-v7`
- Conformal target: `alpha = 0.10`; frozen conservative alpha used by the
  recipe: `0.095`.
- Partition: five score-quantile Mondrian cells on calibrated PD (the frozen
  artifact retains the historical label `score_decile_mondrian`).
- Decision score: `q_i = p_i + 0.50 (u_i - p_i) = (p_i + u_i) / 2`.
- Portfolio risk tolerance: `tau = 0.17`.
- Economic objective: expected point-PD net return, `c_i - p_i L`, with
  `L = 0.45`. Conformal `q_i` enters the risk constraint, not the objective.
- Budget: `$1,000,000`; maximum concentration: `0.25`.

The policy is selected from nine round-number candidates:
`tau in {0.15, 0.17, 0.19}` crossed with
`gamma in {0.25, 0.50, 0.75}`. The final tagged selector uses November 2017,
requires full budget use, enforces the effective-PD cap and deterministic
`B_u <= 0.28`, and maximizes expected point-PD objective. Five of nine
candidates are eligible; the selected policy is `tau = 0.17, gamma = 0.50`.
The selected row remains optimal for endpoint caps in
`[0.259036, 0.290491)`.

The conformal recipe uses `142,550` calibration-fit rows. Policy selection is
performed on `14,943` November rows. Outcomes are stored separately from the
12-column selector frame, which contains no defaults, realized returns,
miscoverage, or assumption-conditional fields. An outcome-free replay on
`20,695` December rows independently selects the same policy. Outcomes joined
afterward give weighted default `0.145650`, weighted
miscoverage `0.124925`, endpoint budget `0.262082`, and accounting bound
`0.387007`. This audit is diagnostic evidence that stable policy selection is
not selected-set coverage validity. Conformal endpoints themselves use
calibration labels, as required.

## Full OOT Result

The fixed policy is evaluated on `276,869` loans from January 2018 through
September 2020:

| Quantity | Value |
|---|---:|
| Funded loans | `308` |
| Allocated budget | `$1,000,000` |
| Expected point-PD objective | `$168,271.56` |
| Realized return | `$179,327.59` |
| Weighted default rate | `0.039375` |
| Weighted miscoverage `V` | `0.036875` |
| Weighted point PD | `0.081949` |
| Weighted decision score | `0.170000` |
| `Gamma_CP` | `0.176102` |
| `Gamma_internalized` | `0.088051` |
| `Gamma_residual` | `0.088051` |
| Endpoint budget `B_u` | `0.258051` |
| Observed accounting bound `B_u + V` | `0.294926` |
| Markov event threshold `B_u + sqrt(alpha)` | `0.574279` |

The primary fixed-allocation bootstrap return interval is
`$163,421.14`--`$193,551.65` (`5,000` draws over `31` origination-month
clusters). A funded-loan sensitivity gives
`$162,706.17`--`$193,924.74`. Neither resamples the model, conformal recipe,
selector, or optimizer.

## Matched Baseline

The point-PD comparator uses the same `276,869` candidates, budget,
concentration cap, `tau = 0.17`, LGD, solver, and point-PD economic objective.
It earns `$196,369.14`, funds `225` loans, and has weighted default `0.118400`,
miscoverage `0.041900`, endpoint budget `0.921317`, and Markov threshold
`1.237545`.

Relative to that comparator, selected CRPTO gives up `$17,041.55` (`8.678%`)
of realized return, reduces weighted default by `7.9025` percentage points,
reduces weighted miscoverage by `0.5025` percentage points, and lowers the
endpoint-plus-Markov threshold by `66.3266` percentage points. These are
retrospective OOT contrasts, not causal effects or universal dominance.

A more conservative `gamma = 0.75` comparator earns `$172,939.50`, with
weighted default `0.035875` and threshold `0.516624`. It shows the remaining
within-CRPTO trade-off: the selected 50/50 policy earns `$6,388.08` more at
`0.35` percentage points more weighted default and a `0.057655` higher
threshold.

## Exact Alpha Evidence

The exact replay reproduces the stored 90% reference intervals to numerical
precision (`max abs error <= 6.67e-16`). Other alpha levels are sensitivity
rows under the same frozen widening recipe, not separately selected policies.
The declared sensitivity grid is
`A = {0.01, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20}`.

Do not reinstate the former `alpha = 0.01` headline. Its exact intervals have
average width `0.9882`, and `93.54%` of OOT upper endpoints equal one. That
setting is nearly vacuous for portfolio discrimination. The active method uses
the conventional 90% level because it is the recipe's selected and exactly
replayed reference level.

## Theory Boundary

For a fixed funded set, the deterministic accounting identity

`weighted outcome <= B_u + V`

holds without a statistical assumption. In the active OOT allocation its
right-hand side is `0.294926`, while the observed weighted outcome is
`0.039375`.

The Markov statement is secondary. If one additionally assumes weighted
funded-set validity, `E[V] <= alpha`, then

`P(weighted outcome >= B_u + sqrt(alpha)) <= sqrt(alpha)`.

At `alpha = 0.10`, this gives threshold `0.574279` and probability bound
`0.316228`. It is deliberately reported as a weak, assumption-conditional
sensitivity, not as a deterministic risk cap, nominal selected-set coverage,
or the paper's primary novelty.

## Evidence Contract

The active evidence bundle is:

- `models/experiments/champion_reopen/<run_tag>/portfolio/ijds_policy_governance.json`
- A35: exact alpha replay and saturation audit.
- A36: November selector, endpoint-cap stability interval, December replay,
  and independent decision audit.
- A37: full-OOT and temporal fixed-policy evaluation.
- A38: selected funded-set grade composition.
- A39: fixed-allocation month-cluster bootstrap plus funded-loan sensitivity.
- A40: selected, more-conservative, and matched point-PD comparison.

The manuscript must say explicitly that earlier project development inspected
this static OOT corpus. The final tagged rule is outcome-free with respect to
its policy-ranking code path, but the evaluation is a transparent retrospective
lockbox replay, not a pristine prospective trial.

## Retired Headline Claims

The following remain provenance only and must not appear as active results:

- alpha-0.01 endpoints obtained by cross-family average-width scaling;
- the `8/8` approximate alpha-grid pass;
- the 50,010-policy frontier as the active selector;
- the `0.345084` Markov threshold;
- capped/tail-focused policy families as the selected method;
- the exploratory 25-policy `gamma = 0.35`, threshold-cap `0.65` challenger;
- policy hyperparameters chosen from OOT realized outcomes.

The frozen upstream model, calibrator, interval artifacts, historical pool93
tables, and `EXTRACTION_MANIFEST.json` remain untouched.

## Reopen Gate

Reopen the active method only for one of four reasons:

1. a calibration-only rule materially improves return at the same `B_u<=0.28`
   screen;
2. a simpler rule matches the selected policy within prespecified tolerances;
3. a valid selected-set or prospective protocol materially strengthens the
   statistical claim;
4. an IJDS reviewer requests a specific additional test.

Otherwise, keep one method, one policy, and one manuscript narrative.
