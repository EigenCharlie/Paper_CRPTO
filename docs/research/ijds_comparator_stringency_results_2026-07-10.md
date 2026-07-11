# Comparator-Stringency Audit Results (2026-07-10)

## Status

The locked comparator audit completed successfully and is active evidence for
the IJDS manuscript. It is a **post hoc falsification audit**: it was designed
after inspecting the maturity-safe parent result, but its own protocol was
committed and tagged before the first successful persisted execution. It is not
confirmatory, prospective, causal, or a new policy-selection exercise.

| Item | Immutable identifier |
|---|---|
| Parent run | `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2` |
| Parent protocol tag | `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2` |
| Comparator run | `champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1` |
| Comparator protocol tag | `protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1` |
| Comparator protocol commit | `ca632ccfbbfaec0e6cdf482a279468665cdb62c0` |
| Comparator summary SHA-256 | `e47d3c74bb0ca262dd097fb13b27ffcd588af4aa62a1f4f2d24ffc495e04c034` |
| Execution-receipt SHA-256 | `869be623ef5e6cc106450ecb49e60ac0dde9ade69a0a7e3f013dd71fa9b10ea8` |
| Comparator processed-data DVC MD5 | `ce16e806cdf1e97a496d7be722c77835.dir` |
| Comparator model/results DVC MD5 | `4c1cbec15b8d60b40d5f2a05c33c66ab.dir` |

The comparator replay reproduces the parent's selected-guardrail and
same-threshold point-PD allocations with maximum absolute difference `0.0`.
No protected DVC stage or manifest-protected artifact was executed or changed.

## Why the Original Baseline Was Not Comparable

The selected guardrail is

`q = 0.75 p + 0.25 u`, with `tau_q = 0.17`.

Because `u >= p` for the binary conformal construction, `q >= p` pointwise.
At a shared numeric cap, every guardrail-feasible allocation is point-PD
feasible, but not conversely. This is feasible-set nesting, not evidence that
one matching rule is uniquely correct.

The diagnostic confirms that the mismatch is material:

| Policy | Cap | OOT weighted constraint score | Aggregate slack | Binding months |
|---|---:|---:|---:|---:|
| Guardrail | 0.170000 | 0.170000 | 0.000000 | 15/15 |
| Point PD, same cap | 0.170000 | 0.115758 | 0.054242 | 0/15 |
| Point PD, development matched | 0.068313 | 0.068313 | 0.000000 | 15/15 |

The same-threshold point policy's monthly slack ranges from `0.039844` to
`0.072349`. Its larger feasible set makes the original comparison a joint
change in score and effective decision stringency.

## Primary Inversion

The primary point-PD comparator fixes its cap at the selected guardrail's
capital-weighted mean funded point PD over the six 2012H2 development months:

`tau_p = 0.06831339893217318`.

All differences below are guardrail minus point PD. Realized intervals are
sharp common-outcome bounds over unresolved binary outcomes, not confidence
intervals.

| Metric | Same numeric cap, secondary | Development matched, primary |
|---|---:|---:|
| Expected standardized payoff | `-$240,977.78` | `+$8,479.18` |
| Realized standardized payoff | `[-$322,703.79, -$58,040.34]` | `[-$506,587.03, -$295,967.17]` |
| Exposure-weighted default | `[-0.046275, -0.020093]` | `[0.034431, 0.056287]` |
| Exposure-weighted miscoverage | `[0.008822, 0.029850]` | `[0.027093, 0.046283]` |

Thus the apparent same-threshold default benefit reverses after development
matching. The guardrail is worse on bounded realized payoff, default, and
funded-set miscoverage in the primary archive, while its model-expected payoff
is only `$8,479.18` higher. This expectation/outcome disagreement is part of
the result rather than a reason to select a different comparator.

## Locked Robustness and Boundary

The selected-policy direction survives all predeclared checks:

- low, mean, and high development caps: `0.065032`, `0.068313`, `0.071705`;
- all 15 leave-one-primary-month-out evaluations;
- least favorable leave-one-month-out payoff upper endpoint:
  `-$231,823.93`;
- least favorable default lower endpoint: `0.029599`;
- least favorable miscoverage lower endpoint: `0.021984`.

Monthly comparisons against the primary matched policy show worse guardrail
payoff in 14 months and one ambiguous month, higher default in 14 and one
ambiguous, and higher miscoverage in 13, lower in one, and ambiguous in one.

The closed nine-policy family does **not** justify a universal claim:

| Direction | Sign-robust pairs |
|---|---:|
| Guardrail payoff worse | 7/9 |
| Guardrail default worse | 7/9 |
| Guardrail miscoverage worse | 9/9 |
| All three jointly | 7/9 |

`linear-003` and `linear-006` have ambiguous payoff and default bounds. The
locked 9-of-9 family gate therefore fails. The selected `linear-004` also wins
only three of six development leave-one-month-out folds; `linear-001` wins one
and `linear-008` wins two. No OOT winner is selected after the fact.

## Mechanism

The same-threshold composition account remains numerically true but is not an
intrinsic effect of conformal scoring. Group-0 capital shares are `0.611338`
for the guardrail, `0.101627` for same-threshold point PD, and `0.499786` for
development-matched point PD. The aligned policies share 1,128 funded IDs and
69.79% of capital.

Against the matched policy, both rules achieve favorable low-risk composition.
The guardrail then incurs larger within-group selection terms under the lower
completion:

| Quantity | Guardrail | Development-matched point PD |
|---|---:|---:|
| Weighted point PD | 0.074979 | 0.068313 |
| Weighted contractual rate | 0.210113 | 0.204369 |
| Default composition term | -0.041210 | -0.043475 |
| Default within-group selection | 0.175652 | 0.132496 |
| Miscoverage within-group selection | 0.171111 | 0.131075 |

The durable mechanism is therefore a candidate-to-funded transport failure for
both policies under adaptive within-group optimization. The old claim that the
guardrail uniquely regularizes composition and lowers default was
comparator-specific.

## Payoff Accounting

For guardrail minus matched point PD, the expected difference decomposes into
`+$53,474.88` expected-interest and `-$44,995.70` expected-default-loss
components. The realized contrast contains `+$86,171.75` contractual payoff,
`-$488,201.64` resolved-default penalty, and an unresolved component bounded by
`[-$104,557.15, $106,062.72]`. These terms reconcile exactly to the primary
realized interval.

Expected payoff breaks even at fixed-allocation `LGD = 0.534800`. The realized
contrast remains negative over the complete locked `LGD` domain `[0,1]`. This
is an accounting sensitivity for fixed allocations, not a reoptimized policy
study.

## IJDS Decision

The active contribution is a defensible negative data-science result:

1. marginal/Mondrian coverage does not imply optimizer-selected validity;
2. a copied numeric threshold does not preserve decision stringency across
   different scores;
3. comparator alignment can reverse an empirical policy conclusion; and
4. maturity-safe candidate construction, sharp unresolved-outcome bounds, and
   exact transport accounting make the failure auditable.

The manuscript must not claim causal effects, universal point-PD dominance, a
unique comparator match, selected-set validity, prospective confirmation, or a
new deployable winner. Another run is not warranted merely to improve the
headline. A future survival, nonexchangeable, selection-valid, or
decision-calibrated method would require a separately locked research protocol
and is outside this single-paper claim.
