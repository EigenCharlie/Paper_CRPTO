# IJDS Claim Audit Matrix

Use this editor-facing matrix with the active evidence manifest. It is not a
reviewer manuscript and does not authorize claims beyond the registry.

<!-- claim:data.exhaustive_status_independent_population -->
<!-- claim:endpoint.not_verified_snapshot -->
<!-- claim:endpoint.reason_census_partitions_candidates -->
<!-- claim:coverage.five_models_all_windows_below_nominal -->
<!-- claim:coverage.closed_taxonomies_primary_below_nominal -->
<!-- claim:coverage.censored_extension_mixed_stress -->
<!-- claim:coverage.joint_block_rank_reference_nominal_flags -->
<!-- claim:coverage.resolved_label_diagnostic_descriptive -->
<!-- claim:coverage.common_panel_adjacent_response -->
<!-- claim:sensitivity.label_mondrian_complete_mixed -->
<!-- claim:sensitivity.label_mondrian_common_completion_gap -->
<!-- claim:geometry.binary_threshold_phase_characterization -->
<!-- claim:theory.coverage_band_identity -->
<!-- claim:theory.outcome_free_binary_set_bounds -->
<!-- claim:theory.binary_set_embedding_nonidentification -->
<!-- claim:timing.endpoint_six_month_reconciles_active -->
<!-- claim:timing.fit_and_endpoint_lags_not_factorial -->
<!-- claim:sensitivity.second_origin_coverage_recurrence -->
<!-- claim:sensitivity.missingness_encoding_recurrence -->
<!-- claim:sensitivity.fit_label_completion_coverage_recurrence -->
<!-- claim:geometry.fit_label_completion_crossing_not_universal -->
<!-- claim:theory.binary_identification_width -->
<!-- claim:decision.no_selected_policy -->
<!-- claim:comparator.registered_cap_values_all_include_zero -->
<!-- claim:sensitivity.structure_no_universal_direction -->
<!-- claim:optimization.allocation_granularity_is_diagnostic -->
<!-- claim:optimization.finite_rhs_coverage_without_uniqueness -->
<!-- claim:theory.basis_endpoint_sufficiency -->
<!-- claim:boundary.no_selected_set_validity -->

| Claim object | Active evidence | Permitted wording | Forbidden inference |
|---|---|---|---|
| Population | 2,925,493 raw rows; 640,543 eligible design rows | Exhaustive population under declared horizon, dates, schema, and observability rules | All raw rows share one estimand |
| Endpoint | 364,814 resolved; 12,076 unresolved among 376,890 primary candidates | Terminal status reconstructed as observable by the cutoff | Verified point-in-time archive snapshot |
| Endpoint reasons | 307,842 fully paid and 56,972 charged off are resolved; 11,551 are nonterminal, 47 terminate after the cutoff, and 478 lack a reconstructible availability date | The five reasons partition every primary candidate | Identified missingness mechanism or observed operational event dates |
| Finite-archive coverage | Under the active six-month endpoint, all 40 model-window sharp upper bounds are below 0.90; largest 0.897726 | A complete deterministic finite-archive shortfall census under the declared endpoint contract | Rejection of exchangeability or failure of the conformal theorem from the 40 endpoints alone; endpoint-lag invariance; selected-set validity |
| Closed taxonomy grid | Under the six-month Charged Off availability rule, for the two V4 learners all 64 primary cells over 1, 2, 5, and 10 frozen score groups have sharp upper endpoints below 0.90; largest 0.897294 | Complete reporting of the four protocol-frozen taxonomies without selecting one | Taxonomy winner; universal taxonomy robustness; extension of the joint-block rank-reference result; theorem failure |
| Censored extension | Under the six-month rule, among 88,227 July--September 2017 candidates, CatBoost has 8/8 upper endpoints below 0.90; numeric logistic contains 0.90 in W1--W6 and lies below it in W7--W8; maximum 0.908928 | A mixed, highly censored declared stress result | Primary OOT evidence; independent or prospective replication; selected origin; model winner; extension of the joint-block rank-reference result; theorem or exchangeability test |
| Joint-block rank-reference diagnostic | In the combined-rank lineage, 31/40 learner-window cell reference tail areas meet the locked nominal reporting thresholds: 8/8 CatBoost, 4/8 logistic, 8/8 monotonic CatBoost, 6/8 platform WOE, and 5/8 pricing-excluded WOE | Complete retrospective threshold reporting under the stronger null that each calibration stratum and its entire target block are jointly exchangeable; Bonferroni over five strata within cell and Holm over 40 cells define the locked nominal thresholds | Rejection of the usual one-future-point marginal guarantee; significance or incompatibility language; post-selection, study-wide, or global 200-stratum FWER; a shift mechanism; exchangeability inferred from any of the nine unflagged cells; inference exported to another sensitivity |
| Resolved-label coverage diagnostic | Across all 40 cells, observed-label coverage is 0.982982--0.992714 for resolved nondefaults and 0.232570--0.363916 for resolved defaults | Coverage stratified by observed label in the administratively resolved panel | All-candidate label-conditional validity; treating this marginal diagnostic as a label-Mondrian procedure; fairness or equalized coverage |
| Common-panel adjacent-threshold response | On the fixed 376,890-candidate panel, the complete 175 stratum-transition census has 122 negative, 5 exactly $[0,0]$, and 48 positive sharp response bounds, with no strict straddles or one-sided zero touches; the 35 pooled learner-transition rows have 31 negative, 0 exactly zero, and 4 positive | Exact crossed class mass, response magnitude, and sharp width from each fitted threshold to the next, with integer numerators summed across mutually exclusive strata and every unresolved label assigned once in both terms; each interval is sharp cellwise; stratum signs are a monotonicity-based consistency check | Treating the mechanical stratum sign census as a discovery; preregistration or confirmation; temporal transport; continuity, slope, or a bound from threshold distance; a complete explanation of threshold movement or score-band mass; joint attainability of all overlapping cell endpoints under one global completion; learner/window selection; causal mechanism; funded-set conformal validity |
| Label-Mondrian sensitivity | Marginal states are 27/40 shortfalls, 12/40 crossings, and 1/40 at-or-above nominal; category states are 109/400 shortfalls, 185/400 crossings, and 106/400 at-or-above nominal; two-label sets are 0.723718--0.785468 | Complete descriptive sensitivity over all 40/200/400 declared cells; it redistributes resolved coverage but does not uniformly restore nominal finite-archive coverage | Conditional-validity repair; 400 hypothesis tests; selected method; fairness or equalized coverage; funded-set validity |
| Label-Mondrian shared-completion gap | All 40 aggregate class-0-minus-class-1 sharp gap bounds cross zero | Each gap endpoint optimizes over completions in which every unresolved loan is assigned once and shared by both class ratios; the lower and upper endpoints may use different completions | Subtracting separately optimized class-ratio endpoints; equal conditional coverage; exchangeability or fairness certification |
| Binary geometry | W7 has $(n,D,k,n-k,m)=(5{,}929,603,5{,}337,592,+11)$, prevalence 0.101703, and quantile 0.888435; W8 has $(6{,}238,606,5{,}616,622,-16)$, prevalence 0.097147, and quantile 0.111801; the finite boundary rates are 0.099848 and 0.099711 | The threshold is exactly the k-th order statistic of the two mirror calibration samples; all S3 calibration scores lie below one half, so the phase margin identifies the branch. W7 uses one minus the 11th largest default score; W8 uses the 5,616th of 5,632 nondefault scores. In W8 the target maximum 0.111893 is below $1-c=0.888199$, certifying zero positive-label coverage for that finite cell | Finite-sample causal explanation; an unconditional or unit-flip phase criterion; a target-side statement without target support; transport; a Binomial crossing law |
| Coverage response to a threshold change | Exact identity on one common fixed target distribution | For any two thresholds, the coverage difference equals target class mass in the two crossed score bands | Universal continuity, threshold distance as a coverage bound, an archive-specific magnitude without registered evidence, a complete geometric explanation of a shortfall, an identified shift mechanism, or restored transport |
| Outcome-free binary-set bounds | Empty sets always miss and full sets never miss under either binary outcome | For a fixed allocation, empty-set exposure and all-but-full-set exposure are the sharp miscoverage lower and upper bounds over unrestricted loan-wise outcomes | A floor from a positive lower endpoint alone, conditional positive-class coverage, funded-set conformal validity, an optimizer direction, or policy dominance |
| Continuous interval embedding | Binary-outcome coverage equals coverage of the induced binary set; when label one is absent, the set identifies only $u<1$, and $u^{(\theta)}=(1-\theta)u+\theta p$ preserves that set exactly | The optimizer uses one declared absolute-residual design embedding; set-equivalent embeddings can change its continuous coefficient | A preferred embedding; set-native optimization; calibrated probability magnitude for the upper endpoint; ordering loans or optimizer effects within a fixed binary set by conformal validity alone |
| Fit-label timing | Crossing persists at 0, 3, and 6 months; 8 and 12 months fail strict >99% retention | Stable across fit-label lags satisfying the rule | Invariance to arbitrary label delay |
| Evaluation-endpoint timing | Coverage upper bounds below 0.90: 40/40 at lags 0, 3, 6, and 8; 39/40 at lag 12, maximum 0.900411 | The active six-month finite-archive statement is contract-specific; the complete lag grid is reported without endpoint selection | Lag-universal 40/40 statement, conformal-theorem failure, or selection of the six-month endpoint |
| Endpoint decision sensitivity | Payoff lower/cross is 32/16 at lags 0, 3, 6, and 8 and 31/17 at 12; default higher/cross is 33/15 then 32/16; miscoverage is 40/8 throughout; all 216 endpoint envelopes over the finite registered cap values spanning `[0.05,0.12]` include zero at every lag, without computing continuous-support extrema | No opposite one-sided direction emerges, and finite registered-cap nonidentification survives the grid | Endpoint-robust adverse direction or a preferred lag |
| Timing design | Fit-label timing refits residual recipes; endpoint timing holds recipes and allocations fixed | Two separate one-factor sensitivities, not a factorial design | Joint lag robustness across 25 untested combinations |
| Objective ruler .25 | Payoff [-9,134.34, 5,603.66]; default/miscoverage [-0.0068, 0.1265] pp | All three metrics are unidentified in all eight windows | A favorable endpoint |
| Objective ruler .50/.75 | .50 adverse in 8/8; .75 payoff/default cross in 7/8 | Direction changes with coordinate | Coordinate-free ordering |
| Normalized ruler | .25/.50 adverse; .75 payoff crosses in 1/8 | Same relative score relaxation, different opportunity cost | Neutral comparison or preferred ruler |
| Portfolio structure | Complete 36-scenario budget--purpose-cap--LGD grid; every scenario has at least 17 adverse default and 21 adverse miscoverage cells; zero scenarios are uniformly favorable or adverse | Direction remains conditional after varying three active structural assumptions | Scenario winner, structural invariance, universal harm, or deployment guidance |
| Registered point-cap support | 216/216 endpoint envelopes over the evaluated registered values spanning `[0.05,0.12]` include zero; default does so in 72/72 development-set cells | Finite witnesses rule out a universal direction over the declared interval without computing continuous-support extrema | Universal comparator quantification or an exhaustive continuous point-cap envelope |
| Solver stability and RHS coverage | 7,228 active-upper RHS ranges, 69 zero-dual basic-row safe rays, and 196 V2 midpoint seeds retrospectively registered in V3a leave no gap above `1e-10` on `[0.05,0.12]` in 15/15 periods; 0 bilateral differences above `1e-10` (maximum `3.08e-14`); scale-aware warnings remain | Finite-support numerical coverage and solver-path stability without a selected cap or uniqueness promotion | Exact or symbolic optimal-face uniqueness or nonuniqueness, global face diameter, allocation continuity, seam conditioning, or continuous-joint-frontier uniqueness |
| Conditional fixed-basis endpoint lemma | On a cap range with a unique optimizer and one fixed valid optimal basis, allocations are affine and the sharp lower/upper endpoints are concave/convex | Endpoint sufficiency is conditional; exact continuous-interval coverage also requires a certified exhaustive partition of all relevant optimal-basis ranges | Claiming that midpoint affinity proves uniqueness, that the active lineage certifies an exhaustive partition, or that the continuous frontier is exact |
| Credit controls | Five coverage specifications; one portfolio learner | Same below-target finding across the protocol-locked specifications under the active endpoint | Model promotion or WOE/IV novelty |
| Missingness encoding | Active sentinels, explicit indicators, and native nullable features each have 8/8 upper bounds below 0.90; maxima 0.882597, 0.884332, and 0.880037 | Coverage finding recurs across three semantics-preserving encodings | Missingness mechanism, encoding winner, or portfolio robustness |
| Individual-age origins | At 39 months after each candidate's issue-month end, both retrospective origins have 8/8 upper bounds below 0.90; maxima 0.879120 and 0.875261 for 2016 and 2017 | Complete 16-cell two-origin retrospective sensitivity at equal whole-month administrative age | Independent replication, temporal invariance, exact day-level loan age, a pooled-origin estimand, or prospective validation; promotion of the parent equal-quarter or earlier unequal-follow-up comparisons beyond replay provenance |
| Fit-label completion | All four scenarios have 8/8 upper bounds below 0.90; the W7--W8 crossing remains in three of four | The finite-archive below-nominal finding survives the declared scenario family, while the geometric path is not scenario-invariant | Sharp bounds over all $2^{215}$ assignments, preregistration, or a universal phase transition |
| Allocation granularity | USD 25 flooring changes any evaluated rate by at most 0.001284 percentage points over 1,440 portfolios | The declared floor-with-cash transformation negligibly perturbs the evaluated rates | Adequacy or optimality of the continuous relaxation; integer optimality, reoptimization, or robustness to another lot rule |
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
