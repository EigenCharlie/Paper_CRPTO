# Fixed-Taxonomy Protocol Semantic Errata - 2026-07-12

This note corrects terminology in the immutable V1/V2 protocol without
changing its design, code, artifacts, or numerical results.

## Residual Interval

The locked protocol called

`[max(0, p - c_g), min(1, p + c_g)]`

the convex-hull representation of a binary conformal prediction set. That
description is not correct. Intersecting the interval with `{0,1}` produces a
discrete set whose convex hull is generally `{0}`, `{1}`, `[0,1]`, or empty,
not the original continuous interval.

The implemented object has always been a clipped split-conformal residual
interval in the ambient real line. Coverage means that the observed binary
outcome lies between its endpoints. Its upper endpoint is used as a decision
score. It is not a confidence limit for latent individual default probability.

## Default Score And Objective

The CatBoost margin is mapped through a 2011 Platt fit. Active prose calls the
result a Platt-scaled default score because OOT calibration drifts. The
coefficient `(1-p)r-p*LGD` is therefore a model-implied plug-in objective. It
equals a conditional expected payoff only if `p` equals the true conditional
default probability, which the retrospective audit does not establish.

## Scientific Effect

This is a semantic erratum only. The residual scores, finite-sample ranks,
interval endpoints, allocations, outcomes, bounds, tables, and figures are
unchanged. The original protocol file remains untouched so its tagged hash and
historical record stay intact. The 2026-07-12 active claim registry, manuscript,
supplement, and submission documents use the corrected terminology.
