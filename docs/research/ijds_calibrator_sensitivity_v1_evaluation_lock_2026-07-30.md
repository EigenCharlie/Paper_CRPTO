# IJDS calibrator sensitivity V1 evaluation lock

**Date:** 2026-07-31

**Status:** Phase-B endpoint-evaluation protocol locked after the outcome-free
Phase-A artifacts were committed, and before Phase B loaded or evaluated the
primary-OOT endpoint.

## Immutable Git lineage

- Protocol P tag:
  `protocol/ijds-calibrator-sensitivity-2026-07-30-v1`
- Protocol P commit:
  `808827926eff5030b3cb28d2b89a87a0e6210b2e`
- Phase-A source tag:
  `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1-source`
- Phase-A source commit A:
  `ea3e7326afc38ccc1b99b09de30792986640e3c3`
- Phase-B protocol tag:
  `protocol/ijds-calibrator-sensitivity-evaluation-2026-07-30-v1`
- Final artifact tag to be created only after complete evaluation:
  `artifacts/ijds-calibrator-sensitivity-2026-07-30-v1`

A is the single direct child of P. This evaluation-lock commit B must be the
single direct child of A. Relative to A, B may change exactly this document and
`configs/experiments/ijds_calibrator_sensitivity_evaluation_2026-07-30_v1.yaml`.
Any other changed path fails the Phase-B runtime gate.

## Exact Phase-A transport

The Phase-A freeze descriptor is:

- path:
  `models/experiments/ijds_audit/ijds-calibrator-sensitivity-2026-07-30-v1-source/protocol_freeze.json`
- bytes: `12098`
- SHA-256:
  `bf00dff0084bb6d017a808897a2ef654f4efaca6880da6a91161b6a3a1171f4c`

The Phase-A execution-receipt descriptor is:

- path:
  `models/experiments/ijds_audit/ijds-calibrator-sensitivity-2026-07-30-v1-source/execution_receipt.json`
- bytes: `1530`
- SHA-256:
  `d117de6253001f152d7ed558a27e125dfd43da78818347ebbc2f67431d9754c2`

The scientific environment uses `uv.lock` SHA-256
`83a10656fcad1af30b42659df24924614576e9eaa727f83e8bb10043da236149`,
including exact `betacal==1.1.0` and `venn-abers==1.5.3`.

Phase A reconciled exactly to the active V4 Platt calibration population:
14,077 rows, 12,602 nondefaults, 1,475 defaults, zero difference across all six
recorded Platt fit metrics, zero active-taxonomy assignment changes, and zero
Platt recipe-quantile difference in all eight windows. Its ordered fit-panel
hashes are:

- ID:
  `81045766e24eb4039c922437a92fb7e37c2715bbe67c5fd95cfd0386d07563de`
- binary label:
  `24e74d0ef1f29c60ee9b45c75741eeecb7623f8d7036a6219684df39260237c4`
- frozen Platt probability:
  `3ce39046141dec723ffe080d3eb41857bbcb1f4f0e8d4a915472380a758daf57`

## Locked evaluation and interpretation

Phase B must report the complete family:

- four maps: frozen Platt, isotonic, beta `abm`, and IVAP Venn--Abers;
- all eight residual windows;
- `ALL` plus all five common `q_raw` strata;
- 192 coverage/geometry cells, 32 overall cells, and all 288 unordered
  pairwise shared-completion cells;
- the complete active V5 population of 376,890 loans, including 364,814
  resolved and 12,076 unresolved outcomes;
- all 48 Platt reconciliation rows at tolerance `1e-12`.

No calibrator, window, stratum, efficiency metric, or pairwise result may be
selected. If every one of the 32 overall sharp upper bounds is below 0.90, the
permitted result is persistence of the complete-archive shortfall within this
closed four-map family and common taxonomy. If any upper bound reaches 0.90,
the permitted result is only that a uniform closed-family shortfall is not
established; this does not by itself prove that true coverage depends on the
calibrator.

Neither branch selects a winning calibrator, refutes conformal theory,
establishes prospective temporal transport, supplies a sampling confidence
interval or missing-at-random conclusion, transfers the Venn multiprobability
guarantee to its scalarization, validates selected or funded sets, or
authorizes portfolio optimization.
