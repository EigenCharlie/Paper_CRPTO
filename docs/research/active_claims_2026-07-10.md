# CRPTO Active IJDS Claim Registry - 2026-07-10

This file is the source of truth for the single IJDS manuscript. It combines
the immutable maturity-safe v2 experiment with a separate, explicitly post hoc
comparator-stringency falsification audit. The compact-v7 registry is
historical provenance only.

## Evidence Hierarchy

The maturity-safe v2 run establishes the data universe, chronology, model,
conformal construction, selected guardrail, payoff, monthly optimization, and
sharp outcome bounds. The later comparator audit changes none of those
objects. It asks whether the original same-numeric-threshold point-PD baseline
was decision-comparable.

The comparator audit was designed after the v2 results were inspected, then
committed and tagged before the first successful persisted execution. It is a
transparent post hoc falsification analysis, not a preregistered or prospective
confirmation. Its result may narrow or overturn the interpretation of the
original contrast, but it may not promote another guardrail or retune the
model, dates, alpha, gamma, payoff, LGD, or purpose cap.

## Immutable Identifiers

### Maturity-safe parent

- Run tag:
  `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2`.
- Protocol tag:
  `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2`.
- Protocol commit: `78a64fe67a4df46c3d19b9243deb991c56fd1ff6`.
- Evidence: `reports/crpto/ijds_maturity_safe_evidence.json`.

### Comparator-stringency audit

- Run tag:
  `champion-reopen-2026-07-10__maturity-safe-v2-comparator-stringency-audit-v1`.
- Protocol tag:
  `protocol/ijds-maturity-safe-v2-comparator-stringency-audit-2026-07-10-v1`.
- Protocol commit: `ca632ccfbbfaec0e6cdf482a279468665cdb62c0`.
- Evidence: `reports/crpto/ijds_comparator_stringency_evidence.json`.
- Post-run audit:
  `docs/research/ijds_comparator_stringency_results_2026-07-10.md`.
- Status: complete from a clean tagged tree; post hoc by design.
- Runtime: 302.16 seconds, with 21 fixed policy specifications.
- Protected stages run: none.
- Protected artifacts overwritten: none.

## Active Method

- Universe: 540,121 status-independent 36-month Lending Club loans.
- PD: CatBoost on 2007--2010, followed by Platt calibration on 2011.
- Conformal: 90%-target split-Mondrian absolute-residual interval using the
  exact finite-sample rank for the observed binary outcome, fitted on 2012H1
  in five calibrated-PD strata.
- The interval is not a confidence interval for latent individual PD.
- Guardrail score: `q=(1-gamma)p+gamma*u`.
- Development-selected guardrail: `tau_q=0.17`, `gamma=0.25`, hence
  `q=0.75p+0.25u`.
- Policy development: six monthly menus, July--December 2012.
- Primary evaluation: 15 separate monthly decisions, April 2016--June 2017,
  with a fresh $1M budget per month.
- Censored extension: July--September 2017, stress evidence only.
- Coherent standardized payoff: expected `(1-p)r-p*LGD`, realized
  `(1-Y)r-Y*LGD`, with `LGD=0.45`.
- Unresolved outcomes remain in each candidate menu and enter sharp additive
  and common-outcome pairwise bounds after allocations are fixed.

## Comparator Non-Invariance

For `gamma` in `[0,1]`, binary conformal upper endpoints satisfy `u>=p`, so
`q>=p`. At a shared threshold `tau`, the guardrail feasible set is therefore a
subset of the point-PD feasible set. With the same objective and all other
constraints fixed, the point-PD optimum has weakly greater model-expected
payoff. Equal numeric thresholds do not identify equal decision stringency.

The original point-PD comparator used `tau_p=0.17`. Its primary OOT weighted
point PD is only `0.115758`, leaving `0.054242` aggregate slack; its risk cap is
nonbinding in all 15 months. The guardrail cap is binding in every month.

The post hoc primary comparator instead fixes point-PD tolerance to the
selected guardrail's capital-weighted mean funded point PD over the six 2012H2
development months:

`tau_p=0.06831339893217318`.

This aligns one prespecified development risk moment; it does not make the two
feasible sets identical or estimate a causal effect. The only threshold
sensitivity is the closed development minimum/mean/maximum set:

- low: `0.06503179389092847`;
- mean: `0.06831339893217318`;
- high: `0.07170531506384897`.

No OOT result selects among these thresholds.

## Predictive Evidence

| Quantity | Value |
|---|---:|
| Conformal-fit coverage | `0.900448` |
| Primary resolved-row coverage | `0.876313` |
| Primary all-candidate coverage | `[0.854923, 0.879692]` |
| Primary mean interval width | `0.736564` |
| Primary lower-endpoint-zero share | `0.988458` |
| Primary upper-endpoint-one share | `0.180766` |
| Primary resolved-row AUC | `0.641688` |
| Primary resolved-row Brier | `0.131126` |
| Primary resolved-row ECE-10 | `0.049691` |

The conformal fit attains its target, but the OOT population does not. No 90%
OOT or selected-set coverage claim is permitted.

## Baseline-Dependent Primary Result

Every policy allocates $15M over the 15 primary months.

| Guardrail minus point PD | Same numeric `tau=0.17` | Development-matched `tau_p=0.068313` |
|---|---:|---:|
| Expected payoff | `-$240,977.78` | `+$8,479.18` |
| Realized payoff | `[-$322,703.79, -$58,040.34]` | `[-$506,587.03, -$295,967.17]` |
| Weighted default | `[-0.046275, -0.020093]` | `[0.034431, 0.056287]` |
| Weighted miscoverage | `[0.008822, 0.029850]` | `[0.027093, 0.046283]` |

The same-threshold comparison makes the guardrail appear safer. The
development-matched comparison reverses that default conclusion: the
guardrail has lower realized payoff, higher default, and higher miscoverage.
All three matched-comparator signs survive the low/mean/high threshold set and
dropping each of the 15 primary months once. For the matched leave-one-month-out
audit, the least favorable sign margins are:

- largest payoff upper endpoint: `-$231,823.93`;
- smallest default lower endpoint: `0.029599`;
- smallest miscoverage lower endpoint: `0.021984`.

The expected-payoff difference is small and favors the guardrail at the mean
match, while the entire sharp realized-payoff interval favors point PD. This
is model-versus-outcome disagreement, not a dominance claim.

## Closed Nine-Policy Census

Each of the nine frozen guardrails is paired with its own 2012H2 mean-funded-PD
point comparator. No policy is reselected OOT.

- Guardrail realized payoff is sign-robustly worse in 7 of 9 pairs.
- Guardrail default is sign-robustly worse in 7 of 9 pairs.
- Guardrail miscoverage is sign-robustly worse in 9 of 9 pairs.
- All three directions hold jointly in 7 of 9 pairs (`7/9`).
- `linear-003` and `linear-006` have ambiguous payoff and default bounds.
- The locked 9-of-9 family claim fails and must not be stated.

The selected `linear-004` result is directionally stable under its locked diagnostics, but
the family evidence is heterogeneous. No OOT winner exists.

## Selection Stability

The parent-selected guardrail wins the full six-month development grid by only
$1,238.33. In leave-one-development-month-out selection it wins 3 of 6 folds;
`linear-001` wins one and `linear-008` wins two. This is selector fragility,
not a reason to promote an alternative policy after OOT inspection.

## Mechanism After Comparator Repair

The original composition result remains true only relative to the loose
same-threshold point policy:

- guardrail group-0 exposure: `0.611338`;
- same-threshold point-PD group-0 exposure: `0.101627`.

The development-matched point policy also shifts toward low point risk:

- development-matched point-PD group-0 exposure: `0.499786`;
- guardrail weighted point PD: `0.074979`;
- development-matched point weighted point PD: `0.068313`;
- guardrail weighted contractual rate: `0.210113`;
- development-matched point weighted contractual rate: `0.204369`.

Under the lower outcome completion, guardrail versus development-matched point
PD has similar low-risk group composition but larger within-group penalties:

- default group-composition term: `-0.041210` versus `-0.043475`;
- default within-group selection: `+0.175652` versus `+0.132496`;
- miscoverage within-group selection: `+0.171111` versus `+0.131075`.

Thus the old "composition regularizer lowers default" interpretation is
baseline-dependent. Once development risk is aligned, point PD obtains an even
lower default bound and lower funded-set miscoverage. The enduring mechanism
claim is descriptive: within-group terms algebraically account for the funded
coverage departure under the ordered transport decomposition for both
policies.

## Payoff and LGD Diagnostics

Against the development-matched comparator, the guardrail has:

- contractual component: `+$86,171.75`;
- resolved default-and-foregone-interest component: `-$488,201.64`;
- expected interest component: `+$53,474.88`;
- expected default-loss component: `-$44,995.70`.

Expected payoff breaks even at `LGD=0.534800`. At the locked `LGD=0.45`, the
guardrail's expected payoff is $8,479.18 higher. Its sharp realized-payoff
upper endpoint remains negative throughout `LGD in [0,1]`; there is no
realized break-even in the locked domain.

## Exact Theory Boundary

The paper may use four exact statements:

1. Binary miscoverage identity:
   `1{Y not in [l,u]} = 1{Y=0,l>0} + 1{Y=1,u<1}`.
2. Sharp additive bounds for unrestricted unresolved binary outcomes after an
   allocation is fixed, including common-outcome pairwise bounds.
3. Selection-transport identity:
   `M_fund-a = (M_row-a) + (M_exp-M_row) + (M_mix-M_exp) +
   (M_fund-M_mix)`.
4. Same-threshold feasible-set nesting when `q>=p`.

The fourth statement diagnoses a comparator defect; it does not prove that
development matching is uniquely correct. The transport components are
completion-specific. Only the funded endpoints are asserted to be sharp.

## Permitted IJDS Claims

- Maturity-safe construction, chronological separation, coherent payoff, and
  sharp handling of unresolved outcomes materially change the research object.
- Marginal/Mondrian conformal coverage does not control the adaptively funded
  set under the observed temporal shift.
- Copying a numeric risk cap across different score definitions confounds the
  score transformation with decision stringency.
- A development-risk-matched point comparator reverses the selected policy's
  apparent default benefit and dominates it on realized payoff, default, and
  miscoverage in this retrospective archive.
- The reversal is directionally stable for the selected policy under the
  locked diagnostics but not universal over the full nine-policy family.

## Forbidden Claims

- confirmatory, preregistered, prospective, or causal comparator evidence;
- universal economic or statistical dominance;
- a unique or theoretically optimal matching rule;
- selected-set conformal validity;
- 9-of-9 family direction;
- Markov certificate or deterministic tail guarantee;
- cash-flow return, IRR, NPV, welfare, or live-deployment performance;
- fair-lending certification;
- promotion of `linear-003`, `linear-006`, or any other OOT-inspected policy.

## Evidence Contract

- Parent summary SHA-256:
  `a9c3b3738b26096703fdd2d1b1e852f72b1516157317c65a92e1bb0abdfd693b`.
- Comparator summary SHA-256:
  `e47d3c74bb0ca262dd097fb13b27ffcd588af4aa62a1f4f2d24ffc495e04c034`.
- Parent publication outputs: maturity-safe tables 1--4, S1--S7, and figures
  0--3.
- Comparator publication outputs: comparator tables 1--3, S1--S12, and
  figures 1--4.
- Two consecutive comparator evidence builds are byte-identical across all 39
  files including the manifest.
- DVC pointers track both comparator run directories in addition to the
  maturity-safe parent directories.

## Required Limitations

- one historical platform and 36-month contracts;
- snapshot binary outcome with unresolved administrative states;
- standardized payoff without cash-flow timing or prepayment;
- substantial temporal drift;
- no selected-set conformal validity;
- comparator audit designed after the parent results were known;
- development matching aligns one empirical moment, not feasible sets;
- fragile six-month guardrail selection;
- no causal, prospective, live-deployment, or fair-lending interpretation;
- extension bounds too wide for a directional claim.

## Historical Boundary

The compact-v7 run, its A35--A40 tables, Markov-style sensitivities, and the
older A1--A34 diagnostics remain reproducible historical artifacts. They
cannot be quoted as active evidence, used to fill a missing maturity-safe
result, or described as replications of either active run.
