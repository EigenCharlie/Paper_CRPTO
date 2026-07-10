# Locked comparator-stringency audit protocol (2026-07-10)

## Status and parent evidence

This protocol is a post hoc falsification audit designed after the maturity-safe
v2 results were inspected. It is not preregistered, prospective, or
confirmatory. Its parent is the immutable run
`champion-reopen-2026-07-10__maturity-safe-locked-bounded-h1h2-v2` at protocol
tag `protocol/ijds-maturity-safe-locked-bounded-h1h2-2026-07-10-v2`.

The parent model, calibrator, conformal recipe, decision panels, outcomes,
selected guardrail, dates, payoff, LGD, budget, purpose cap, solver, and sharp
bound definitions do not change. No protected DVC stage or manifest-protected
artifact may be executed or overwritten.

## Why the audit is required

For the active score

`q_i = (1 - gamma) p_i + gamma u_i`,

the binary conformal upper endpoint satisfies `u_i >= p_i`, so `q_i >= p_i`.
At a shared numeric threshold `tau`, every q-feasible allocation is p-feasible,
but the reverse need not hold. The parent point-PD policies at `tau` 0.15,
0.17, and 0.19 are nonbinding and identical. Calling `tau=0.17` "matched"
therefore equates labels, not decision stringency.

## Locked primary comparator

The new primary comparator is point PD with a fixed risk tolerance equal to the
selected guardrail's capital-weighted mean funded point PD over the six 2012H2
development months:

`tau_PD = 0.06831339893217318`.

The value is derived exclusively from parent development allocations. It is
then frozen for every 2016--2017 monthly menu. The original `tau=0.17`
point-PD policy remains a secondary same-threshold diagnostic.

The only threshold sensitivity is the closed minimum/mean/maximum set observed
across the six development months:

- low: `0.06503179389092847`;
- mid: `0.06831339893217318`;
- high: `0.07170531506384897`.

No threshold may be selected from OOT results.

## Closed family census

All nine parent guardrails are evaluated OOT without reselection. Each receives
one point-PD comparator whose threshold is that guardrail's own 2012H2 funded
mean point PD. Every row is reported. No OOT winner exists, and no result can
replace the parent-selected `linear-004`. A family-level direction may be stated
only if it holds for all nine guardrail/comparator pairs.

## Required diagnostics

The immutable audit must report monthly and aggregate allocations, optimality,
budget use, cap slack, funded overlap, common-outcome sharp payoff/default/
miscoverage contrasts, development and primary leave-one-month-out results,
score geometry and saturation, selection transport, payoff decomposition, and
fixed-allocation LGD break-even values over `[0,1]`.

Purpose-concentration sensitivity is outside this protocol because it changes
the feasible-set definition and would open another policy family.

## Decision rule

The comparator non-invariance headline is allowed only if the tagged replay
simultaneously shows:

1. guardrail default remains lower than same-threshold point PD;
2. guardrail payoff is lower than development-matched point PD;
3. guardrail default is higher than development-matched point PD;
4. guardrail miscoverage is higher than development-matched point PD; and
5. all four directions survive dropping each primary month once.

If any condition fails, the headline stops. The project may report the complete
heterogeneous diagnostic, but it may not change alpha, gamma, tau rules, LGD,
payoff, months, matching definition, or promoted guardrail in search of a more
favorable result.
