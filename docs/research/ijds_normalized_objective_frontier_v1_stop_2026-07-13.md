# IJDS normalized/objective frontier V1 outcome-free stop

## Status

The tagged V1 run under
`protocol/ijds-normalized-objective-frontier-2026-07-12-v1` stopped before
creating an output directory and before joining any outcome. This is a
protocol-compliant numerical stop, not a completed freeze and not an empirical
portfolio result.

## Exact stop

The run started from clean tagged commit `64d1131` and completed windows W1--W7.
In W8 it stopped at the following outcome-free cell:

- residual window: `w08_2012m08_2013m01`;
- role and month: `primary_oot`, April 2017;
- score path: `gamma=.25`;
- objective floor used only for the tie diagnostic: `z* - USD 1e-7`;
- minimum-to-maximum funded-score span: `3.49719776749e-08`;
- locked stop threshold: `1e-8`.

Elapsed wall time was 3,514.5 seconds. The runner wrote neither
`data/processed/experiments/ijds_audit/ijds-normalized-objective-frontier-2026-07-12-v1`
nor its model directory.

## Outcome-free diagnosis after the stop

The failed cell was inspected without loading a status or outcome column. The
score-independent plug-in objective optimum had:

- objective value `USD 193,151.90088630395`;
- minimum absolute nonbasic reduced cost `0.004653265386878047`;
- minimum scaled nonbasic reduced cost `3.6143215598948346e-06`;
- zero nonbasic reduced costs within `1e-7`;
- zero primal-degenerate basic columns or rows;
- zero exposure distance and zero objective drift after reversing ID order.

Imposing the computed objective value as an exact lower bound caused a budget
reconciliation difference of only `USD 1.389028e-4`, just beyond the solver
wrapper's `USD 1e-4` budget tolerance. The V1 score span therefore measured
the deliberately allowed `USD 1e-7` objective deterioration, not evidence of
an alternate exact optimum. The check was answering the wrong numerical
question.

## Consequence

The V1 tag remains immutable and failed. Its tolerance will not be relaxed.
V1b replaces the slack-floor score-span proxy with the standard LP diagnostic:
nonbasic reduced costs at the score-independent objective optimum, plus an
independent rerun after reversing IDs. This test is performed once per monthly
menu because the objective and base polytope do not depend on residual window
or gamma. V1b must receive its own commit, protocol tag, run tag, and fresh
output directories before execution.
