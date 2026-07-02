# Champion Reopen Execution Manifest - 2026-06-19

## Decision

Continue the champion-reopen thread as exploratory evidence only until a
candidate clears the full CRPTO chain: PD, calibration, conformal validity,
portfolio exact audit, and robust-region checks.

## Active Claim Target

Find a defensible challenger that improves the current decision certificate,
not only the classifier AUC. The current promotion floor remains:

- PD: mean AUC improvement at least `+0.005` without worse Brier/ECE behavior.
- Portfolio: beat `$170,464.54` or keep return similar with clearly better
  `V(alpha=0.01)` / `C_CP`.
- Robustness: exact alpha pass, zero violation, and robust region at least
  `45/45`.

## Retained Infrastructure

- `configs/experiments/champion_reopen.yaml` defines the isolated search grid,
  promotion gates, output roots, calibrators, and seed policy.
- `scripts/experiments/run_champion_reopen.py` writes command manifests and
  executes resumable smoke, feature-search, seed-replay, and calibration waves.
- `scripts/experiments/monitor_champion_reopen.py` prints the live leaderboard
  from experiment-only status JSON files.
- `scripts/experiments/run_tabprep_feature_selection_catboost.py` now ranks
  pool features even when the selector model omits them, preventing silent
  empty `pooltopX_*` cases.

## Guardrails

All outputs must stay under:

- `data/processed/experiments/champion_reopen/`
- `models/experiments/champion_reopen/`
- `reports/crpto/experiments/champion_reopen/`
- `reports/run_logs/champion_reopen/`

No champion artifact, extraction manifest, canonical conformal interval, or
portfolio bound-aware promotion output is overwritten by this thread.

## Runtime Commands

Create or refresh the dedicated environment:

```bash
uv venv .venv-champion-search --python 3.11
uv pip install --python .venv-champion-search/bin/python -r configs/experiments/champion_reopen_requirements.txt
```

Run a smoke wave:

```bash
.venv-champion-search/bin/python scripts/experiments/run_champion_reopen.py \
  --stage smoke \
  --run-tag champion-reopen-2026-06-19 \
  --execute \
  --resume
```

Monitor:

```bash
tail -f reports/run_logs/champion_reopen/champion-reopen-2026-06-19*/*.log
.venv-champion-search/bin/python scripts/experiments/monitor_champion_reopen.py \
  --run-tag champion-reopen-2026-06-19
```

## Stop / Advance Rule

Advance from smoke to full feature search only if:

- `pool_ranking_count > 0` and `generated_ranking_count > 0`;
- every smoke case writes status and predictions;
- no protected path is touched;
- at least one non-core subset completes without calibration failure.

If those pass, launch `--stage feature_search`, then `--stage seed_replay`.
Downstream conformal and portfolio waves remain gated on the top three
seed-stable PD+calibration finalists.
