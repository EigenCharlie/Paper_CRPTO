# Conformal Claim And Parallelization Memo - 2026-06-22

## Decision

Continue the conformal reopen search as a paper-facing claim search, not as a
classification leaderboard. The live claim target is a decision certificate:
a calibrated PD model plus conformal uncertainty should support a robust
portfolio region with auditable coverage, width, bound, return, and zero
violation evidence.

## Local Paper Synthesis

The local sources in `Papers_tesis/paper` point to four roles for this phase:

- Conformal prediction and risk control: Angelopoulos and Bates, Angelopoulos
  et al., Bates et al., Barber et al., and Learn-Then-Test support finite-sample
  marginal/risk-control language, while warning against overclaiming exact
  individual conditional coverage.
- Conformal robust optimization: Sun et al., Patel et al., Hu et al.,
  Johnstone and Cox, and Zhao et al. motivate calibrated uncertainty sets as
  inputs to robust or satisficing decisions, especially when downstream loss is
  the object of interest.
- Predict-then-optimize and robust optimization: Bertsimas and Kallus,
  Elmachtoub and Grigas, Donti et al., Bertsimas and Sim, Delage and Ye, and
  Goldfarb and Iyengar support the paper framing that a useful predictor is one
  whose uncertainty improves a decision, not only a score.
- Credit/P2P context: Serrano-Cinca and Gutierrez-Nieto, Guo et al., Zhao et
  al., Jagtiani and Lemieux, Albanesi and Vamossy, Chi et al., Torkian et al.,
  and Das et al. support the business meaning of credit risk, profit scoring,
  portfolio allocation, fairness/equity, and tabular/alternative-data credit
  modeling.

## Method Implications

- Prefer clean partitions with paper meaning: `grade`, score bands, grade by
  score band, and later vintage/risk bands if the support is large enough.
- Report Mondrian/group results as approximate group-conditional diagnostics,
  not as impossible exact distribution-free conditional guarantees.
- Select conformal candidates by a multi-criterion gate: global coverage,
  minimum group coverage, temporal stability, width/Winkler, sidecar set
  behavior, and downstream portfolio usefulness.
- Keep calibration alternatives as a tournament, but only promote them when
  they do not trade better ECE for wider or less stable conformal intervals.
- Treat MAPIE and crepes as sidecar validators or alternative implementations
  for coverage/partition sanity checks unless they beat the native artifact
  path without weakening traceability.

## Implementation Change

`scripts/search/run_conformal_reopen_search.py` now supports:

- `--phase1-workers N` for parallel independent phase-1 inner conformal runs.
- Automatic resume of completed phase-1 namespaces when both tuning and result
  artifacts exist.
- `conformal_reopen_phase1_progress.json` with total, completed, running, failed
  and reused-existing inner runs.

`configs/profiles/search_conformal_claim_max.yaml` sets `parallel_workers: 3`.

`scripts/archive/experiments/launch_conformal_parallel_after_current_inner.sh` waited for
the current serial block to publish its first checkpoint, stops the old serial
tmux session, and relaunches the same conformal run tag with parallel phase-1
workers. This preserves the work already spent on the first block while
allowing the remaining inner blocks to run concurrently.

## Evidence Gate

A conformal candidate can move to portfolio only if it provides:

- accepted global coverage and group coverage under the profile gates;
- no large width inflation versus the current canonical conformal artifact;
- stable temporal diagnostics;
- a clear partition story suitable for the paper;
- a final status artifact with reproducible namespaces and inputs.

## Stop Rule

Stop extending conformal variants when the best candidate is either accepted for
portfolio search or all accepted variants are dominated in width, temporal
stability, or downstream bound/return. Extra variants should be parked in
experiment artifacts, not promoted into the manuscript.
