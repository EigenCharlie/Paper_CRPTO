# IJDS Claim Audit Matrix

Use this editor-facing matrix with the active evidence manifest. It is not a
reviewer manuscript and does not authorize claims beyond the registry.

<!-- claim:data.exhaustive_status_independent_population -->
<!-- claim:endpoint.not_verified_snapshot -->
<!-- claim:endpoint.reason_census_partitions_candidates -->
<!-- claim:coverage.five_models_all_windows_below_nominal -->
<!-- claim:coverage.exact_exchangeability_transport_test -->
<!-- claim:coverage.resolved_label_diagnostic_descriptive -->
<!-- claim:sensitivity.label_mondrian_complete_mixed -->
<!-- claim:sensitivity.label_mondrian_common_completion_gap -->
<!-- claim:geometry.prevalence_sensitive_mechanism -->
<!-- claim:timing.endpoint_six_month_reconciles_active -->
<!-- claim:timing.fit_and_endpoint_lags_not_factorial -->
<!-- claim:sensitivity.second_origin_coverage_recurrence -->
<!-- claim:sensitivity.missingness_encoding_recurrence -->
<!-- claim:sensitivity.fit_label_completion_coverage_recurrence -->
<!-- claim:geometry.fit_label_completion_crossing_not_universal -->
<!-- claim:theory.binary_identification_width -->
<!-- claim:decision.no_selected_policy -->
<!-- claim:comparator.broad_support_all_cross_zero -->
<!-- claim:sensitivity.structure_no_universal_direction -->
<!-- claim:optimization.allocation_granularity_is_diagnostic -->
<!-- claim:boundary.no_selected_set_validity -->

| Claim object | Active evidence | Permitted wording | Forbidden inference |
|---|---|---|---|
| Population | 2,925,493 raw rows; 640,543 eligible design rows | Exhaustive population under declared horizon, dates, schema, and observability rules | All raw rows share one estimand |
| Endpoint | 364,814 resolved; 12,076 unresolved among 376,890 primary candidates | Terminal status reconstructed as observable by the cutoff | Verified point-in-time archive snapshot |
| Endpoint reasons | 307,842 fully paid and 56,972 charged off are resolved; 11,551 are nonterminal, 47 terminate after the cutoff, and 478 lack a reconstructible availability date | The five reasons partition every primary candidate | Identified missingness mechanism or observed operational event dates |
| Finite-archive coverage | Under the active six-month endpoint, all 40 model-window sharp upper bounds are below 0.90; largest 0.897726 | A complete deterministic finite-archive shortfall census under the declared endpoint contract | Rejection of exchangeability or failure of the conformal theorem from the 40 endpoints alone; endpoint-lag invariance; selected-set validity |
| Joint-block rank-reference diagnostic | In the combined-rank lineage, 31/40 learner-window cells meet the locked nominal thresholds: 8/8 CatBoost, 4/8 logistic, 8/8 monotonic CatBoost, 6/8 platform WOE, and 5/8 pricing-excluded WOE | Complete retrospective threshold reporting under the stronger null that each calibration stratum and its entire target block are jointly exchangeable; Bonferroni over five strata within cell and Holm over 40 cells define the locked nominal thresholds | Rejection of the usual one-future-point marginal guarantee; significance or incompatibility language; post-selection, study-wide, or global 200-stratum FWER; a shift mechanism; exchangeability inferred from any of the nine unflagged cells; inference exported to another sensitivity |
| Resolved-label coverage diagnostic | Across all 40 cells, observed-label coverage is 0.982982--0.992714 for resolved nondefaults and 0.232570--0.363916 for resolved defaults | Coverage stratified by observed label in the administratively resolved panel | All-candidate label-conditional validity; treating this marginal diagnostic as a label-Mondrian procedure; fairness or equalized coverage |
| Label-Mondrian sensitivity | Marginal states are 27/40 shortfalls, 12/40 crossings, and 1/40 at-or-above nominal; category states are 109/400 shortfalls, 185/400 crossings, and 106/400 at-or-above nominal; two-label sets are 0.723718--0.785468 | Complete descriptive sensitivity over all 40/200/400 declared cells; it redistributes resolved coverage but does not uniformly restore nominal finite-archive coverage | Conditional-validity repair; 400 hypothesis tests; selected method; fairness or equalized coverage; funded-set validity |
| Label-Mondrian shared-completion gap | All 40 aggregate class-0-minus-class-1 sharp gap bounds cross zero | Each gap endpoint optimizes over completions in which every unresolved loan is assigned once and shared by both class ratios; the lower and upper endpoints may use different completions | Subtracting separately optimized class-ratio endpoints; equal conditional coverage; exchangeability or fairness certification |
| Binary geometry | W7 prevalence 0.101703 and quantile 0.888435; W8 prevalence 0.097147 and quantile 0.111801 | Pattern matches the constant-score phase mechanism | Finite-sample causal explanation |
| Fit-label timing | Crossing persists at 0, 3, and 6 months; 8 and 12 months fail strict >99% retention | Stable across fit-label lags satisfying the rule | Invariance to arbitrary label delay |
| Evaluation-endpoint timing | Coverage upper bounds below 0.90: 40/40 at lags 0, 3, 6, and 8; 39/40 at lag 12, maximum 0.900411 | The active six-month finite-archive statement is contract-specific; the complete lag grid is reported without endpoint selection | Lag-universal 40/40 statement, conformal-theorem failure, or selection of the six-month endpoint |
| Endpoint decision sensitivity | Payoff lower/cross is 32/16 at lags 0, 3, 6, and 8 and 31/17 at 12; default higher/cross is 33/15 then 32/16; miscoverage is 40/8 throughout; all 216 broad envelopes cross at every lag | No opposite one-sided direction emerges, and broad-support nonidentification survives the grid | Endpoint-robust adverse direction or a preferred lag |
| Timing design | Fit-label timing refits residual recipes; endpoint timing holds recipes and allocations fixed | Two separate one-factor sensitivities, not a factorial design | Joint lag robustness across 25 untested combinations |
| Objective ruler .25 | Payoff [-9,134.34, 5,603.66]; default/miscoverage [-0.0068, 0.1265] pp | All three metrics are unidentified in all eight windows | A favorable endpoint |
| Objective ruler .50/.75 | .50 adverse in 8/8; .75 payoff/default cross in 7/8 | Direction changes with coordinate | Coordinate-free ordering |
| Normalized ruler | .25/.50 adverse; .75 payoff crosses in 1/8 | Same relative score relaxation, different opportunity cost | Neutral comparison or preferred ruler |
| Portfolio structure | Complete 36-scenario budget--purpose-cap--LGD grid; every scenario has at least 17 adverse default and 21 adverse miscoverage cells; zero scenarios are uniformly favorable or adverse | Direction remains conditional after varying three active structural assumptions | Scenario winner, structural invariance, universal harm, or deployment guidance |
| Exact support | 216/216 broad envelopes cross zero; default 72/72 development envelopes cross | No universal direction over declared supports | Universal comparator quantification |
| Solver stability | 7,297 evaluated rows; 0 tie-sensitive reversed-order reruns | Deterministic stability at evaluated caps | Continuous-frontier uniqueness |
| Credit controls | Five coverage specifications; one portfolio learner | Same below-target finding across the protocol-locked specifications under the active endpoint | Model promotion or WOE/IV novelty |
| Missingness encoding | Active sentinels, explicit indicators, and native nullable features each have 8/8 upper bounds below 0.90; maxima 0.882597, 0.884332, and 0.880037 | Coverage finding recurs across three semantics-preserving encodings | Missingness mechanism, encoding winner, or portfolio robustness |
| Equal-follow-up origins | At 39 months after each April--June quarter end, both retrospective origins have 8/8 upper bounds below 0.90; maxima 0.877685 and 0.874768 for 2016 and 2017 | Complete 16-cell two-origin retrospective sensitivity at a common relative endpoint | Independent replication, temporal invariance, identical loan-level age, a pooled-origin estimand, or prospective validation; promotion of the earlier unequal-follow-up comparison beyond replay provenance |
| Fit-label completion | All four scenarios have 8/8 upper bounds below 0.90; the W7--W8 crossing remains in three of four | The finite-archive below-nominal finding survives the declared scenario family, while the geometric path is not scenario-invariant | Sharp bounds over all $2^{215}$ assignments, preregistration, or a universal phase transition |
| Allocation granularity | USD 25 flooring changes any evaluated rate by at most 0.001284 percentage points over 1,440 portfolios | The continuous relaxation is numerically adequate for this archive and lot rule | Integer optimality, reoptimization, or robustness to another lot rule |
| Payoff proxy | Plug-in `(1-p)r-p*LGD`; status-indexed `(1-Y)r-Y*LGD` | Coherent standardized proxy under the declared binary endpoint | IRR, cash-flow return, NPV, or welfare |
| Identification width | For a fixed contrast, width is exactly $\sum_{i\in U}|d_i(1)-d_i(0)|$; reported payoff widths span \$14,738 to \$373,705.31 across the six tracks | Finite-archive sensitivity to unresolved exposure disagreement is algebraically transparent; rate metrics retain their declared capital normalizer | Sampling uncertainty, confidence interval, or an unresolved-count-only ordering across metrics |

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
