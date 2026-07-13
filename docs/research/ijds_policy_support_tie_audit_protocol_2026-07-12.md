# IJDS Policy-Support and Solver-Tie Audit Protocol

## Status and claim boundary

This protocol is locked before executing the complete audit under tag
`protocol/ijds-policy-support-tie-audit-2026-07-12-v1`. It is a post hoc
structural audit of already inspected V4 decision objects, not confirmation and
not a new empirical policy search. It reads no realized outcome, default,
repayment, status, or miscoverage column.

The audit may justify, narrow, or reject the interpretation of the current
policy family and comparator supports. It cannot select a winning policy,
change a realized direction, establish selected-set coverage, or promote an
endpoint because it looks favorable.

## Questions

1. Are `tau={0.15,0.17,0.19}` and `gamma={0.25,0.50,0.75}` feasible and
   decision-active over all declared development and primary monthly menus?
2. What happens at the omitted semantic endpoints `gamma=0` and `gamma=1`?
3. Which cap-month pairs are actually covered by named C0/C1/C2 rules,
   development-support endpoints, broad stress endpoints, and exact
   period-specific basis breakpoints?
4. Does any evaluated point LP have a nonbasic near-zero reduced cost or a
   degenerate primal basis, and can changing deterministic column order change
   its allocation while preserving the primary objective?

## Outcome-free source contract

The parent is the immutable V4 V1 outcome-free freeze at commit `2f8a760`. Its
freeze descriptor, scores, residual recipes, solve records, comparator support,
and exact frontier artifacts are hash-verified before use.

The raw CSV is read only for `id`, `loan_amnt`, `int_rate`, and `purpose`.
Membership, issue month, design role, and point PD come from the frozen score
artifact. Any column name containing `status`, `outcome`, `default`, `pymnt`,
`realized`, or `miscoverage` is forbidden in the decision panel. The runner
must report an empty outcome-column list.

## Policy-family domain

For each of eight residual windows, 11 policy-development months, 15 primary
months, and `gamma` in `{0,.25,.50,.75,1}`, define

`q_gamma = p + gamma * (U-p)`.

At a fixed budget and purpose cap, let `q_min` be the minimum achievable funded
score and `q_obj` the funded score of the unconstrained coherent-payoff
maximizer. Both are solved exactly without outcomes. Each fixed `tau` is then
classified as:

- `infeasible` if below `q_min`;
- `minimum_boundary` if equal to `q_min` within `1e-8`;
- `decision_active` if strictly between `q_min` and `q_obj`;
- `objective_boundary` if equal to `q_obj` within `1e-8`; or
- `objective_slack` if above `q_obj`.

Every feasible cap is solved and its score, budget, and coherent plug-in
objective are recorded. The inherited 1,872 interior cells are reconciled to
the frozen V4 solve records within USD `1e-4` in objective and `1e-8` in funded
effective score.

`gamma=0` is the point-score endpoint already represented by C0 and is not
renamed a conformal guardrail. `gamma=1` is the full upper-endpoint diagnostic.
Neither endpoint is automatically added to the paper-facing family. The audit
must first expose feasibility, binding, informativeness, and duplication.

## Comparator-support taxonomy

The comparator is part of the estimand. This audit preserves three distinct
support roles:

1. **Named rules:** C0 copies a numeric cap, C1 transports the mean development
   funded point moment, and C2 matches the contemporaneous guardrail point
   moment. They are not interchangeable votes.
2. **Development-transport support:** the minimal interval containing all 11
   development funded point moments for each window-policy pair. It is
   outcome-free but conditional on that design period.
3. **Broad stress support `[.05,.12]`:** a sensitivity domain, not a normative
   or universally admissible comparator set.

The cap census is the tolerance-deduplicated union, by primary month, of all
named caps, all development-support endpoints, both broad-stress endpoints,
and every period-specific HiGHS basis breakpoint. Its cardinality is derived,
not chosen after diagnostics.

## Basis and tie diagnostics

At every cap in the union, the point-PD LP is solved with exact budget and one
thread. The audit records:

- nonbasic lower/upper counts and minimum absolute and scaled reduced cost;
- number of nonbasic reduced costs within `1e-7` of zero;
- basic structural variables at a bound within `1e-9`;
- basic inequality-row slacks at zero within `1e-9`;
- dual-sign violation, objective reconciliation, cap slack, and basis range.

A near-zero nonbasic reduced cost is a necessary warning for alternate optima;
primal degeneracy alone is not proof of one. Every warned or primal-degenerate
cap is rerun after sorting columns by descending loan ID. The exposure distance
is `L1/(2B)`. An objective difference above USD `1e-5` is a solver failure. A
nonzero exposure distance with reconciled objective is reported as tie-sensitive
and would require outcome envelopes or an explicit tie rule before manuscript
use.

## Stop and interpretation rules

1. Stop on source-hash mismatch, missing IDs, duplicate IDs, unexpected design
   months, or any forbidden decision column.
2. Stop if an inherited interior solve cannot be reproduced within tolerance.
3. Report every endpoint, cap class, basis diagnostic, and order rerun.
4. Do not redesign `tau`, `gamma`, support, or tolerances after seeing this run.
   Any normalized-cap challenger requires a new tagged protocol.
5. An outcome-free active range demonstrates computational relevance, not
   empirical benefit.
6. Absence of a tie warning over the finite census supports deterministic
   stability only at that census; it does not prove uniqueness over every real
   cap.
7. If `gamma=1` is infeasible or uninformative, explain the endpoint omission.
   If it is feasible and distinct, retain it as a declared sensitivity or give
   a substantive reason for excluding it.
8. Broad-stress results must remain labeled sensitivity, while development
   support remains conditional identification under a transported design range.

## Required outputs

- one row for every window-role-month-gamma-tau family cell;
- one row for every deduplicated primary cap-month basis diagnostic;
- one row for every triggered column-order sensitivity solve;
- a deterministic summary with source and implementation hashes;
- an execution receipt with empty protected-stage and protected-artifact lists.
