# IJDS Policy-Support and Solver-Tie Audit Results

## Status

The outcome-free audit completed under `protocol/ijds-policy-support-tie-audit-2026-07-12-v1` at commit
`115eaf1`. It read only ID, amount, contractual rate, purpose,
frozen design role, point score, and frozen conformal recipes. No outcome column
entered a solve. These results are pre-freeze structural evidence and do not by
themselves promote a policy or empirical direction.

## Policy-family domain

- The audit retained 3,120 cells: eight windows, 26 months, five gamma levels,
  and three fixed risk tolerances.
- All 1,872 inherited interior cells were feasible; 1,846 were decision-active.
  The 26 slack cells all occur at `gamma=.25` in W8.
- `gamma=0` is objective-slack in all 624 cells under
  `tau={.15,.17,.19}`. It is correctly treated as a point-score nesting
  control, not an uncertainty-aware policy.
- `gamma=1` is feasible and decision-active in all 624 cells. Relative to
  `gamma=.75` on the same menu and cap, its plug-in objective is lower in all
  624 cells, by a mean of `-2519.44`
  and a range from `-8337.85` to
  `-579.98` plug-in objective dollars per
  monthly USD 1 million budget.
- Parent V4 scores and objectives reconcile to
  `2.220e-16` and
  `8.731e-11`.

The endpoint result means the current nine-policy family is computationally
active but semantically incomplete. The next specification must either include
`gamma=1` as a complete-family sensitivity or replace fixed caps with a tagged
normalized-stringency design that includes both endpoints. Silent omission is
no longer defensible.

## Comparator support

The tolerance-deduplicated union contains `7297` cap-month pairs in
15 primary months. The earlier exploratory statement of 2,249 solves was not a
complete census; the correct named unique count is
`2204` and the full union also includes support
endpoints and 2,952 period-specific basis breakpoints.

- All 45 C0 cap-months are objective-slack for point PD.
- C1 has 1,079 active and one slack cap-month.
- C2 has 1,075 active and four objective-boundary cap-months.
- Every lower development endpoint is active; six upper endpoints are slack.
- Broad `.05` is active in every month, while broad `.12` is slack in every
  month. `[.05,.12]` is therefore a stress interval spanning active and slack
  regions, not a normative admissible support.

## Solver ties

There are `2941` primal-degenerate bases, mostly
because basis breakpoints are transition points. None has a nonbasic reduced
cost within `1e-7` of zero; the minimum absolute nonbasic reduced cost is
`0.000387573`. All
`2941` triggered caps were rerun after reversing loan-ID
order. Zero were tie-sensitive; maximum exposure distance was
`1.450e-14` and maximum absolute objective
difference `1.717e-09`.

Thus primal degeneracy does not explain the portfolio directions in this finite
census. This supports deterministic stability at the evaluated caps, not a
universal uniqueness theorem over every real cap.

## Required next decision

Do not freeze the current family. The highest-value challenger is an
outcome-free normalized stringency parameter
`lambda=(q_cap-q_min)/(q_obj-q_min)` over both score endpoints. It directly
addresses the all-slack point endpoint and the arbitrary cross-score meaning of
one numeric tau. It must be separately tagged and reported whether it strengthens
or weakens the V4 conclusion. A simpler fallback is to add `gamma=1` to the
fixed-cap sensitivity and retain the exact support caveat.
