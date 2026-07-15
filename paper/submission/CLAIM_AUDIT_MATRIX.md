# IJDS Claim Audit Matrix

Use this editor-facing matrix with the active evidence manifest. It is not a
reviewer manuscript and does not authorize claims beyond the registry.

<!-- claim:data.exhaustive_status_independent_population -->
<!-- claim:endpoint.not_verified_snapshot -->
<!-- claim:coverage.five_models_all_windows_below_nominal -->
<!-- claim:geometry.prevalence_sensitive_mechanism -->
<!-- claim:timing.endpoint_six_month_reconciles_v3 -->
<!-- claim:timing.fit_and_endpoint_lags_not_factorial -->
<!-- claim:decision.no_selected_policy -->
<!-- claim:comparator.broad_support_all_cross_zero -->
<!-- claim:sensitivity.structure_no_universal_direction -->
<!-- claim:simulation.portfolio_claim_forbidden -->
<!-- claim:boundary.no_selected_set_validity -->

| Claim object | Active evidence | Permitted wording | Forbidden inference |
|---|---|---|---|
| Population | 2,925,493 raw rows; 640,543 eligible design rows | Exhaustive population under declared horizon, dates, schema, and observability rules | All raw rows share one estimand |
| Endpoint | 364,814 resolved; 12,076 unresolved among 376,890 primary candidates | Terminal status reconstructed as observable by the cutoff | Verified point-in-time archive snapshot |
| Endpoint recovery | V2: 365,339 resolved / 11,551 unresolved; V3: 364,814 / 12,076 | The 525 reclassified candidates change some sharp directions; both versions are disclosed | Promotion of a V2 or V3 direction |
| Coverage | Under the active six-month endpoint, all 40 model-window upper bounds are below 0.90; largest 0.897726 | Coverage does not transport here across five protocol-locked specifications | Universal conformal invalidity, endpoint-lag invariance, or selected-set validity |
| Binary geometry | W7 prevalence 0.101703 and quantile 0.888435; W8 prevalence 0.097147 and quantile 0.111801 | Pattern matches the constant-score phase mechanism | Finite-sample causal explanation |
| Fit-label timing | Crossing persists at 0, 3, and 6 months; 8 and 12 months fail strict >99% retention | Stable across fit-label lags satisfying the rule | Invariance to arbitrary label delay |
| Evaluation-endpoint timing | Coverage upper bounds below 0.90: 40/40 at lags 0, 3, 6, and 8; 39/40 at lag 12, maximum 0.900411 | The active six-month claim is contract-specific; the complete lag grid is reported without endpoint selection | Lag-universal 40/40 coverage failure or selection of the six-month endpoint |
| Endpoint decision sensitivity | Payoff lower/cross is 32/16 at lags 0, 3, 6, and 8 and 31/17 at 12; default higher/cross is 33/15 then 32/16; miscoverage is 40/8 throughout; all 216 broad envelopes cross at every lag | No opposite one-sided direction emerges, and broad-support nonidentification survives the grid | Endpoint-robust adverse direction or a preferred lag |
| Timing design | Fit-label timing refits residual recipes; endpoint timing holds recipes and allocations fixed | Two separate one-factor sensitivities, not a factorial design | Joint lag robustness across 25 untested combinations |
| Objective ruler .25 | Payoff [-9,134.34, 5,603.66]; default/miscoverage [-0.0068, 0.1265] pp | All three metrics are unidentified in all eight windows | A favorable endpoint |
| Objective ruler .50/.75 | .50 adverse in 8/8; .75 payoff/default cross in 7/8 | Direction changes with coordinate | Coordinate-free ordering |
| Normalized ruler | .25/.50 adverse; .75 payoff crosses in 1/8 | Same relative score relaxation, different opportunity cost | Neutral comparison or preferred ruler |
| Portfolio structure | Complete 36-scenario budget--purpose-cap--LGD grid; every scenario has at least 17 adverse default and 21 adverse miscoverage cells; zero scenarios are uniformly favorable or adverse | Direction remains conditional after varying three active structural assumptions | Scenario winner, structural invariance, universal harm, or deployment guidance |
| Exact support | 216/216 broad envelopes cross zero; default 72/72 development envelopes cross | No universal direction over declared supports | Universal comparator quantification |
| Solver stability | 7,297 evaluated rows; 0 tie-sensitive reversed-order reruns | Deterministic stability at evaluated caps | Continuous-frontier uniqueness |
| Credit controls | Five coverage specifications; one portfolio learner | Same below-target finding across the protocol-locked specifications under the active endpoint | Model promotion or WOE/IV novelty |
| Payoff | Plug-in `(1-p)r-p*LGD`; realized `(1-Y)r-Y*LGD` | Coherent standardized endpoint | IRR, cash-flow return, or welfare |

## Nonnegotiable Boundaries

- No selected learner, window, taxonomy, endpoint lag, gamma, ruler,
  coordinate, structural scenario, cap, comparator, or policy.
- No causal, prospective, confirmatory, deployment, Markov, or fair-lending
  claim.
- Overlapping windows and repeated allocations are not independent replications.
- Sharp bounds are finite-archive partial identification, not confidence
  intervals.
- The paper is one ML--conformal--optimization audit; none of the three
  components is presented as a separate successor paper.
