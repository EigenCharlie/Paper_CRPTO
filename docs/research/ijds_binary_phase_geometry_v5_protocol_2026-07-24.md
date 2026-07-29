# Binary Phase Geometry V5 — Stopped Theory Provenance

Run tag: `ijds-binary-phase-geometry-2026-07-24-v5`

Protocol tag claimed by the stopped draft:
`protocol/ijds-binary-phase-geometry-2026-07-24-v5`

Status: **STOPPED; NOT AN ACTIVE PROTOCOL OR EVIDENCE SOURCE**

Superseded by:
`docs/research/ijds_binary_phase_geometry_v6_protocol_2026-07-26.md`

## Why V5 was stopped

Adversarial review found that two proposed results were false and that a third
was overgeneralized.

1. The proposed “boundary continuity” argument coupled the `m=0` threshold of
   one calibration block to the `m=1` threshold of another through a common pair
   of class maxima. One calibration block cannot have both margins. The correct
   result is an identity between any two fixed thresholds and their common target
   distribution; it does not imply continuity.
2. Exposure with `l_i>0` is not an outcome-free miscoverage floor. For example,
   `[l_i,u_i]=[0.6,1]` covers `Y_i=1`. The sharp outcome-free lower bound is
   exposure in empty binary sets, `l_i>0` and `u_i<1`; the upper bound is all
   exposure except full sets.
3. Score-Mondrian binning does not guarantee that realized finite-bin prevalence
   is ordered or that any bin falls below `alpha`. The phase margin is an exact
   frozen-calibration diagnostic under its stated condition; zero positive target
   coverage additionally requires target support below `1-c_g`.

V5 also proposed outputs `P1`--`P4` that were never created by a standalone V5
run. A later publication builder derived a phase table from registered parent
artifacts, but that does not retroactively execute or validate this protocol.

## Consequence

No V5 decision-floor result, universal low-stratum statement, continuity claim,
or external generality claim may appear in the manuscript, supplement, claim
ledger, or active evidence registry. This file is retained only so the failed
reasoning remains auditable rather than being silently rewritten as if it had
been predeclared correctly.
