# CRPTO / IJDS Champion Tournament Protocol - 2026-05-25

> Ported from the parent research factory
> (`paper1_crpto_ijds_champion_tournament_protocol_2026-05-25`). **Documentation
> only.** Defines the governed, anti-cherry-pick tournament that *would* govern
> any future champion reopen. The frozen champion
> (`paper-thesis-final-economic-2026-04-06`) is **not** reopened by porting this
> protocol; it is recorded as the reviewer-facing selection contract.

## Purpose

Reopens the CRPTO champion search as a governed tournament, not another artifact
loop. Target claim:

`calibrated PD -> Mondrian conformal interval -> uncertainty set -> robust LP -> auditable policy`

The search may replace the frozen economic champion only if a predeclared
candidate wins the complete downstream trade-off. Better AUC alone, better return
alone, or better bound alone is not sufficient.

Frozen champion: return `170464.5429284627`, `V` `0.03645`, `Gamma_CP` `0.18591`,
violation `0`, funded coverage `0.9433`, policy `blended_uncertainty` (risk
`0.175`, gamma `0.45`, uncertainty aversion `0.1`), region `45/45`.

## What This Is Testing

Not whether a new scorer beats the old scorer, but whether the full CRPTO chain
can find a policy that is more valuable and at least as defensible under IJDS
standards:

1. PD is calibrated and auditable.
2. Conformal coverage is stable enough to become a decision input.
3. The robust LP converts uncertainty into a funded set with zero violation.
4. Exact alpha-grid validation confirms the apparent frontier is real.
5. Nested or prospective confirmation shows the winner was not selected by
   peeking across waves.
6. The paper can publish a claim-artifact-test map, negative-results registry,
   and final selection rule.

## Anti-Cherry-Pick Contract

Before any serious medium/full run, the run root must contain:

- `predeclared_candidate_registry.json`: every PD/conformal/portfolio lane that
  may compete for champion replacement.
- `phase_gate_status.json`: uniform gates for every lane.
- `selection_rule.json`: the final ranking rule and tie-breakers.
- `negative_results_registry.csv`: every failed, skipped, parked or appendix
  lane, with reason.

A late idea may be added only by opening a new protocol version **before** running
its downstream portfolio stage. Late ideas cannot enter the same tournament as
champion candidates after seeing portfolio results; they go to Paper 4, appendix,
or a future protocol.

## Candidate Lanes

- **Lane A - Frozen Incumbent Replay.** Anchor every comparison to the official
  claim using `models/final_project_promotion.json` artifacts. Comparator and
  sanity gate, not a new challenger.
- **Lane B - External PD Finalists.** `canonical_4`, `bureau_behavior_15`,
  `affordability_rate_5`. Gates: AUC/Brier/ECE/reliability/Gini reported
  separately; calibration deterioration bounded; monotonicity and
  feature-governance auditable; downstream conformal/portfolio proxy improves or
  preserves the IJDS claim.
- **Lane C - Governance-Aware PD HPO.** CatBoost `monotone_constraints`,
  `feature_weights`, `first_feature_use_penalties`/`penalties_coefficient`;
  `posterior_sampling`/Langevin only as diagnostic unless a CPU-reproducible path
  is shown. Optuna with persistent per-lane storage, retained failed trials,
  constrained/multi-objective (calibration + downstream proxies, not AUC alone),
  seed replay for top trials. Any PD that wins only AUC but fails calibration is
  appended or parked.
- **Lane D - Calibration & Conformal Tournament.** Primary partitions
  `score_decile_mondrian`, `grade`, `grade_x_scoreband_mondrian`,
  `vintage_x_scoreband` (only if cell size sufficient). Venn-Abers main; isotonic
  /Platt/beta controlled alternatives; MAPIE risk-control only as sidecar. Phase
  champion is the best row passing coverage/group/width/temporal/feasibility
  gates, not the highest coverage row. The `score_decile_mondrian` lesson stays
  active: a regulatory-looking grouping that fails group coverage cannot feed the
  robust LP.
- **Lane E - Portfolio Frontier Tournament.** Cascade 25k smoke -> 50k/75k medium
  -> 100k/150k frontier -> full universe -> exact alpha-grid rerank + sealed
  confirmation. Solver: cuOpt for the broad frontier (RAPIDS env), exact rerank
  in `.venv` with HiGHS/highspy; HiGHS fallback rows labeled. Grid: risk
  `0.165-0.200`, gamma `0.275-0.600`, uncertainty aversion `0-0.25`; policy
  families `blended_uncertainty`, `capped_blended_uncertainty`,
  `tail_blended_uncertainty`, segment-tail only if they preserve the main claim.
- **Lane F - Theory & Bound Hardening.** Implement now: funded-set Mondrian
  refinement; decision-aware conformal selector audit; nested/prospective
  confirmation; regret and price-of-robustness table; bootstrap funded-set
  diagnostics. Prototype or park: direct CRC/LTT on decision loss;
  dependence-aware concentration by cluster; online/shift-aware conformal; richer
  LGD/ECL targets; OCE/CVaR as a new objective.

## Phase Gates

- **PD gate.** AUC improves or within tolerance; Brier and ECE non-inferior;
  calibration diagrams reveal no new material failure; monotonicity/governance
  defensible; downstream conformal feasibility proxy not degraded.
- **Conformal gate.** Global 90/95 coverage passes; min-group coverage passes the
  declared floor; rare grades visible in diagnostics; width not inflated enough to
  destroy portfolio value; temporal warnings labeled, not hidden.
- **Portfolio gate.** alpha01 exact pass true; violation zero; realized return
  competitive; `V`, `Gamma_CP`, funded coverage and composition defensible;
  survives medium/full confirmation, not only 25k/50k probes.
- **Champion replacement gate.** Full-universe exact alpha01 pass true; violation
  `0`; return at least `170464.5429284627` (preferably with margin); `V <=
  0.03645` or a clearly superior `Gamma_CP`/coverage trade-off without materially
  worsening `V`; `Gamma_CP <= 0.18591` or a clearly superior bound trade-off;
  funded coverage comparable or better; nested/prospective confirmation passes;
  the negative-results registry proves the winner was not cherry-picked.

## IJDS Evidence Packet If A New Champion Wins

Promote only paper-facing artifacts (child convention): a tournament final
summary CSV under `reports/crpto/tables/`, a negative-results registry CSV under
`reports/crpto/tables/`, and a `docs/research/crpto_champion_decision_memo_<date>.md`.
The manuscript body changes only after the decision memo says `promote`. Appendix
receives high-value negative or theorem-tight evidence. Paper 4 receives ideas
that teach a method lesson but fail replacement gates.

## What Not To Re-run

- exact-all CPU grid; AUC-only HPO;
- `score8_raw_sqrt`, `grade_cal_sqrt`, `score8_cal_none` as champion lanes after
  prior downstream failures (diagnostic controls only);
- online conformal without a serious temporal split;
- OCE/CVaR as replacement objective unless a new protocol explicitly targets a
  tail-risk paper, not IJDS CRPTO replacement.

## Immediate Execution Order (if reopened)

1. Freeze this protocol and run root.
2. Emit candidate registry and dirty-state audit.
3. Run tournament smoke across all declared PD/conformal lanes, not canonical
   alone.
4. Promote only conformal finalists with decision-aware evidence.
5. Run cuOpt frontier 25k/50k uniformly for finalists.
6. Run exact rerank only for finalists selected before seeing full-universe
   results.
7. Seal final selection, then run nested/prospective confirmation.
