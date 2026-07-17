# Rolling-Origin Stability V2 Execution Erratum

## Why V2 is required

The V1 protocol was committed and tagged at
`5aa241014134227b10746cc28507b599468b33b0` before either new outcome join.
Both V1 freeze attempts stopped before producing an outcome-free freeze:

- the 2015 origin stopped while fitting the first canonical residual recipe
  because at least one of its five fixed-taxonomy groups had fewer than the
  locked 1,000 observations; and
- the 2017 origin completed model and residual fitting but stopped before any
  allocation because `build_outcome_free_portfolios` contained an inherited
  literal requirement for 15 primary OOT menus, while the rolling-origin
  protocol declares exactly three.

Neither attempt joined terminal outcomes, evaluated payoffs, inspected OOT
coverage, or wrote a protocol freeze. The V1 run directories are retained as
failed-run provenance and are not reused or overwritten.

## Scientific decision

The 2015 stop is a locked feasibility finding. V2 does not reduce the 1,000-row
minimum, pool score groups, remove a residual window, change the taxonomy, or
substitute another origin. The 2015 freeze is rerun only to persist a structured
failure receipt with the exact group counts.

The 2017 stop is an implementation defect. V4 legitimately has 15 primary
months, but a reusable constructor must derive the expected count from the
declared design. V2 replaces only that literal with the inclusive month count
from `primary_oot_start_month` through `primary_oot_end_month`. It similarly
derives the already unchanged 11 policy-development months from their declared
dates. For the original V4 configuration the resulting expectation remains
exactly `(11, 15)`; for each rolling-origin configuration it is `(11, 3)`.

No model, feature, seed, calibration rule, residual window, policy, payoff,
comparator, frontier, solver tolerance, outcome, reporting rule, hypothesis, or
promotion criterion changes in V2.

## Failure receipts

The phase runner now writes a deterministic JSON receipt when a locked phase
fails. The receipt records protocol/run tags, exception type and message,
structured protocol details when available, Git state, and an explicit empty
list of protected stages and artifacts. It is written inside the fresh model
run directory and cannot overwrite an existing receipt.

For canonical-group infeasibility, the error now carries learner, window,
taxonomy size, all group counts, and the unchanged minimum. This improves audit
evidence but does not alter the condition that triggers the stop.

## V2 execution contract

Required tag:
`protocol/ijds-rolling-origin-stability-2026-07-12-v2`.

Fresh run tags:

- `ijds-rolling-origin-2015-2026-07-12-v2`;
- `ijds-rolling-origin-2017-2026-07-12-v2`.

Both origins must be rerun from the freeze phase. The expected 2015 feasibility
failure must be retained and reported; it is not permission to adapt the
protocol. If 2017 passes its outcome-free freeze, only then may its evaluation
phase join outcomes under the same tagged implementation. The original V4
origin remains the sole source for the mechanically restricted April--June
2016 comparison.
