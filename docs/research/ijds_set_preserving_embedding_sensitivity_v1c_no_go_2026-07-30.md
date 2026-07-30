# IJDS set-preserving embedding sensitivity V1c NO-GO note (2026-07-30)

## Status

V1c is a retrospective, post-inspection non-evidence run. Its Phase-B outputs
remain preserved locally for forensic audit, but they were not committed and no
evaluation artifact tag was created. They must not be copied, renamed, repaired
in place, or used as evidence.

## Windows pre-outcome launch history

The first Phase-B launch encountered a Windows `MAX_PATH` failure before the
protected outcome archive was opened and before any V1c output was written. A
fresh retry used an ephemeral effective long-path Git configuration. This was
an operational retry, not a scientific adaptation. V1d therefore checks the
effective Windows long-path setting before opening outcomes; it does not infer
success from the prior retry.

## Materialized Phase B and finite-gate breach

The retry completed Phase B in approximately 167.8 seconds and materialized all
nine planned local outputs. The evaluated-primary table contained 18,000 rows
and 50 columns. Before commit or tag, the persisted-finiteness audit found one
undeclared nullable field:

- `realized_payoff_exact` was missing in 8,325 rows, exactly when
  `n_unresolved_positive_exposure > 0`;
- the other 9,675 values were defined and equaled both the lower and upper
  realized-payoff endpoints;
- identified-set widths in the unresolved rows were nonzero, ranging from
  approximately USD 298.03 to USD 207,788.13;
- the three already declared ruler-structural fields—`frontier_cap`,
  `objective_target`, and `risk_tolerance`—each had the expected 9,000 missing
  entries and were not the breach.

An exact realized payoff is not identified when funded exposure has unresolved
outcomes. Persisting a nullable “exact” column without declaring that estimand
violated the fail-closed output contract even though its missingness was
scientifically explainable. V1c is therefore NO-GO. The lower and upper payoff
bounds remain the appropriate identified-set representation, but no V1c output
is promoted.

Separately, the pooled-window table carried an all-null `period` field in all
1,200 rows because a pooled fifteen-month window has no single monthly period.
This nonnumeric field was not the unequivocal numeric finite-gate blocker above,
but V1d removes the ambiguity as persistence hardening rather than inventing a
sentinel month.

## V1d successor boundary

V1d is a new retrospective, post-inspection, non-confirmatory protocol. It
replays Phase B from a fresh Git-native `P2 -> A2 -> B2` authority, drops
`realized_payoff_exact` before persistence, retains the lower and upper bounds,
removes `period` only from the pooled-window table, and validates exact output
schemas plus every remaining persisted value. The sole permitted
numeric missingness is the exact three-field ruler pattern declared above;
unresolved `snapshot_default` values remain permitted only in the protected
outcome/join objects held in memory.
