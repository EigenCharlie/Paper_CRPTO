<!-- Curated for the standalone CRPTO project on 2026-05-10. Sources: docs/ADSFCR_EXECUTABLE_BACKLOG_2026-03-30.md and docs/ADSFCR_AUDIT_AND_MONOTONIC_CHALLENGER_PLAN_2026-03-29.md -->

# CRPTO Validation Hardening Notes

This note keeps only the CRPTO-relevant lessons from the ADSFCR-inspired audit and executable backlog. It is support material for governance, appendix writing and reviewer responses, not a new dependency of the CRPTO champion.

## What Matters For CRPTO

- Bootstrap diagnostics strengthen interpretation of PD, conformal coverage and MRM decisions when asymptotic tests become over-sensitive at large samples.
- Calibration mapping diagnostics tested a plausible post-hoc repair path for cohort persistence. The executed shadow validation was negative but valuable: lightweight intercept/isotonic sidecars did not improve the champion enough to justify promotion.
- Model-shift and p-value semantics are useful for explaining why a statistically visible diagnostic alert is not automatically a failed economic policy.
- Monotonicity and constrained-threshold challenger ideas remain useful future-work for governance, but they do not replace the official CRPTO champion.
- Encoding/binning stability is relevant as a feature-contract appendix because CRPTO depends on stable PD, calibrated probabilities and conformal residual behavior.

## What Stays Out Of Scope

- LGD survival, IFRS9 macro/ECL modeling and scenario temporal overlays are not CRPTO base-lane artifacts.
- Causal pricing, CATE portfolio surfaces and broad research-lab adoptions remain future work unless a later paper deliberately reopens them.
- External ADSFCR notebooks/PDFs are literature/support context only; CRPTO should cite methods directly rather than depend on that repository.

## Carry-Forward Checklist

- Keep CRPTO's evidence focused on: PD calibration, conformal coverage/width, bound-aware portfolio selection, exact alpha-gamma validation, funded-set composition, fairness and MRM.
- Mention negative calibration-mapping results only if a reviewer asks why the residual cohort persistence was not fixed through a simple remap.
- Use bootstrap and model-shift diagnostics as governance support, not as a new acceptance gate for the already frozen champion.
