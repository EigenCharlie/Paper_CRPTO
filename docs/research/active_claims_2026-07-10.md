# CRPTO Active IJDS Claim Registry - 2026-07-10

This file is the source of truth for the maturity-safe IJDS manuscript. The
compact-v7 claim registry dated 2026-07-09 is historical provenance only.

## Active Experiment

- Run tag:
  `champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2`.
- Protocol tag:
  `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2`.
- Protocol commit: `78a64fe67a4df46c3d19b9243deb991c56fd1ff6`.
- Status: complete, executed from a clean tagged tree.
- Universe: 540,121 status-independent 36-month loans.
- Policy development: July--December 2012.
- Primary evaluation: 15 separate monthly decisions, April 2016--June 2017,
  with a fresh $1M budget per month.
- Censored extension: July--September 2017, reported as stress evidence only.
- No protected DVC stage was run and no manifest-protected artifact was
  overwritten.

## Method

- PD: fixed CatBoost classifier on 2007--2010, followed by Platt calibration on
  2011.
- Conformal: exact 90% split-Mondrian absolute-residual interval for the
  observed binary outcome, fitted on 2012H1 in five calibrated-PD strata.
- The interval is not a confidence interval for latent individual PD.
- Guardrail score: `q=(1-gamma)p+gamma*u`.
- Development-selected policy: `tau=0.17`, `gamma=0.25`, hence
  `q=0.75p+0.25u`.
- Point-PD baselines: matched `tau=0.17` and independently selected
  `tau=0.15`; they yield identical allocations because their point-risk
  constraint is nonbinding.
- Monthly LP: full $1M budget, at most 25% per purpose, fractional funding no
  greater than the listed loan amount, and weighted decision score no greater
  than `tau`.
- Coherent standardized payoff: expected `(1-p)r-p*LGD`, realized
  `(1-Y)r-Y*LGD`, and `LGD=0.45`.
- This payoff is not cash-flow return, IRR, NPV, or a causal welfare measure.

## Observability and Bounds

Candidate membership never uses final status. Snapshot `Default` and `Charged
Off` statuses map to one, `Fully Paid` maps to zero, and all other statuses
remain unresolved. There are 11,386 unresolved primary candidates and 28,716
in the extension.

Every unresolved binary outcome is retained. Default, payoff, and miscoverage
receive sharp bounds. Pairwise policy contrasts are computed on the union of
funded IDs with one shared outcome per loan; they are not obtained by naively
subtracting marginal policy intervals. A directional claim requires the entire
primary contrast bound to have one sign.

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

## Primary Decision Evidence

Both policies allocate $15M across 15 monthly decisions.

| Quantity | Conformal guardrail | Point PD |
|---|---:|---:|
| Expected standardized payoff | `$2,383,112.23` | `$2,624,090.01` |
| Realized payoff | `[-$2,389.90, $168,250.04]` | `[$177,108.53, $369,495.74]` |
| Weighted default | `[0.292775, 0.310322]` | `[0.326037, 0.343428]` |
| Weighted miscoverage | `[0.294708, 0.309589]` | `[0.275360, 0.290265]` |
| Unresolved exposure | `0.017547` | `0.017392` |

Sharp guardrail-minus-point contrasts:

| Contrast | Lower | Upper | Interpretation |
|---|---:|---:|---|
| Realized payoff | `-$322,703.79` | `-$58,040.34` | guardrail worse |
| Payoff rate | `-0.021514` | `-0.003869` | guardrail worse |
| Weighted default | `-0.046275` | `-0.020093` | guardrail better |
| Weighted miscoverage | `0.008822` | `0.029850` | guardrail worse |

The contrast is retrospective and noncausal. The active empirical claim is a
default--payoff trade-off plus a selected-set coverage failure, not economic
dominance.

## Development-to-OOT Reversal

On the six 2012H2 policy-development months, guardrail minus the
development-selected point policy is:

- expected payoff: `-$72,701.67`;
- realized payoff: `+$50,260.10`;
- weighted default: `-0.063802`;
- weighted miscoverage: `-0.007358`.

In the locked primary window, realized payoff and miscoverage reverse while the
default benefit remains. This reversal is active evidence that development
success does not transport. It is not a hypothesis test over six independent
months and cannot be used to reopen the policy grid.

## Mechanism

- The guardrail places 61.1338% of primary capital in conformal score group 0;
  point PD places 10.1627% there.
- The guardrail places 0.9657% in group 4; point PD places 10.4268%.
- Guardrail weighted contractual rate: `0.210114`; point PD: `0.257957`.
- Under the lower completion, the guardrail's default composition term is
  `-0.041210`, versus `+0.019627` for point PD.
- Under the lower completion, guardrail within-group miscoverage selection is
  `+0.171111`, versus `+0.144317` for point PD.

Therefore, the conformal constraint acts empirically as a coarse
score-composition regularizer. Its default benefit is between-group; it does
not improve within-group selection and does not transport marginal coverage to
the funded set.

## Theory Boundary

The paper may use three exact statements:

1. Binary miscoverage identity:
   `1{Y not in [l,u]} = 1{Y=0,l>0} + 1{Y=1,u<1}`.
2. Sharp additive bounds for unrestricted unresolved binary outcomes after an
   allocation is fixed.
3. Selection-transport identity:
   `M_fund-a = (M_row-a) + (M_exp-M_row) + (M_mix-M_exp) +
   (M_fund-M_mix)`.

The transport components are completion-specific. Only the funded endpoints
are asserted to be sharp aggregate bounds. CRPTO does not claim a new
selected-set conformal theorem, distributionally robust guarantee, or Markov
certificate.

## Evidence Contract

- Active evidence manifest:
  `reports/crpto/ijds_maturity_safe_evidence.json`.
- Deterministic summary:
  `models/experiments/champion_reopen/<run>/maturity_safe_locked_summary.json`.
- Execution receipt:
  `models/experiments/champion_reopen/<run>/execution_receipt.json`.
- Summary SHA-256:
  `a9c3b3738b26096703fdd2d1b1e852f72b1516157317c65a92e1bb0abdfd693b`.
- Publication outputs: `crpto_ijds_ms_table1`--`table4`, S1--S7, and
  `crpto_ijds_ms_fig0`--`fig3`.
- DVC pointers track both the versioned processed-data directory and the
  versioned model/results directory.

## Required Limitations

- one historical platform and 36-month contracts;
- snapshot binary outcome with unresolved administrative states;
- standardized payoff without cash-flow timing or prepayment;
- substantial temporal drift;
- no selected-set conformal validity;
- no causal, prospective, live-deployment, or fair-lending interpretation;
- code-locked retrospective audit, not a pristine lockbox or preregistration;
- extension bounds too wide for a directional claim.

## Historical Boundary

The compact-v7 run, its A35--A40 tables, Markov-style sensitivities, and the
older A1--A34 journal diagnostics remain reproducible historical artifacts.
They cannot be quoted as active evidence, used to fill a missing v2 result, or
described as replications of the maturity-safe policy.
