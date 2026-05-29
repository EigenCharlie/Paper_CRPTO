# PyEPO 1.3 Intake Memo - 2026-05-26

> Ported from the parent research factory (`pyepo_1_3_intake_2026-05-26`).
> Evaluates PyEPO 1.3 for the CRPTO project, the Quarto book and the Paper 4
> agenda. It is not a promotion artifact and does not modify the frozen champion.

## Bottom Line

PyEPO 1.3 matured enough to reopen the **SPO/DFL lane as a bounded, isolated
prototype**, especially for the Paper 4 agenda. The 2026-05-28 closeout below
now satisfies the CRPTO stop rule: we import the paired SPO+ rerun as appendix
evidence, but we do not import the full suite, add a dependency, or replace
CRPTO. The strongest contribution is a cleaner comparator boundary:

1. `SPOPlus` as the existing regret-minimizing baseline.
2. `regularizedFrankWolfeFenchelYoung` (RFYL) as the new low-friction
   differentiable loss for the current continuous LP-style credit selection
   problem.
3. `perturbedFenchelYoungMul` only for positive-cost risk/ECL variants, not for
   raw net-return costs that can be negative.
4. `coneAlignedCosine` / CaVE only if we run a **binary** approval or top-k
   selection prototype with a Gurobi-backed model.

The key update relative to the older v32 SPO blocker is that we do **not** need
`cvxpy/cvxpylayers` to make a formal PyEPO prototype. PyEPO 1.3.7 works in an
isolated OR-Tools environment with PyTorch autograd modules.

## Curated Closeout - 2026-05-28

The parent project completed the PyEPO 1.3.7 rerun after this intake memo was
created. CRPTO imports only the conclusion needed for IJDS/thesis appendix:

| Result | Curated value | CRPTO decision |
|---|---:|---|
| SPO+ mean regret | `0.184366` | Appendix comparator only. |
| Two-stage mean regret | `0.358073` | Baseline for the paired comparison. |
| SPO+ improvement | `48.51%` | Curated PyEPO closeout value; separate from the committed A19/Fig. 15 artifact (`49.09%`). |
| Paired Wilcoxon | `p = 3.80e-163` | Statistical support for the comparator. |

Interpretation: SPO+ remains the regret winner, as expected. CRPTO remains the
coverage/auditability method because the PyEPO suite does not provide conformal
coverage, exact funded-set bound guarantees, or a replacement for the frozen
`bound_aware_276k_economic_champion`. RFYL, CaVE and PFYL-Mul stay in the Paper 4
DFL lab as comparator research, not as CRPTO promotion evidence.

Operational decision: do not copy PyEPO run directories, solver logs, Gurobi
artifacts or new dependencies into this repo. Keep this memo and the SPO+ chapter
language as the self-contained record.

## Version Check

| Source | Finding |
|---|---|
| PyPI | Latest package is `pyepo 1.3.7`, released 2026-05-26. Requires Python `>=3.9` and publishes typed wheels. |
| GitHub releases | 1.3 release notes attached to the 2026-05-25 series. |
| Docs | Documentation site reports `PyEPO 1.3.7` with a rebuilt tutorial structure. |
| Repo README | PyEPO is the official MPC-paper implementation and now asks users to cite CaVE separately when using that loss. |

Sources: https://pypi.org/project/pyepo/ ,
https://github.com/khalil-research/PyEPO/releases ,
https://khalil-research.github.io/PyEPO/build/html/index.html ,
https://github.com/khalil-research/PyEPO

## What Changed In 1.3

### CaVE / CaVE+

`pyepo.func.coneAlignedCosine` implements cone-aligned vector estimation for
binary linear programs. Instead of differentiating through the solver or sampling
perturbations, it aligns predicted costs with the normal cone at the true binary
optimum. The default `max_iter=3` is the CaVE+ preset (truncated Clarabel
projection).

- Strong for a binary approval/top-k prototype.
- Weak for the current continuous/fractional CRPTO champion.
- Requires `optDatasetConstrs`, which needs Gurobi-backed constraint extraction.

Decision: Paper 4 only, as a small Gurobi-enabled binary lane. Do not import into
the CRPTO main claim.

### Regularized Frank-Wolfe

`regularizedFrankWolfeOpt` and `regularizedFrankWolfeFenchelYoung` smooth the LP
oracle with L2 regularization. Best new match for our current credit optimizer
because it only needs a linear optimization oracle and works with our
OR-Tools-style `optModel`.

- Good for continuous LP portfolio selection; better than CaVE for the current
  CRPTO shape.
- Avoids the old `cvxpy/cvxpylayers` dependency blocker.
- Gives Paper 4 a more credible "formal DFL" experiment than the earlier
  oracle-regret surrogate.

Decision: **promote to next experiment** as a third DFL comparator beside
two-stage and SPO+.

### Multiplicative Perturbation

`perturbedOptMul` and `perturbedFenchelYoungMul` preserve cost signs via
multiplicative noise (matters when a solver expects nonnegative costs).

- Good for `PD`, `PD_high`, ECL/loss-only or positive shifted cost variants.
- Dangerous for raw `PD * LGD - int_rate`, because those costs naturally cross
  zero; shifting costs changes optimization behavior unless carefully justified.

Decision: use only in a risk-cost/ECL experiment, not as the default CRPTO regret
comparator.

### CVRP Models

PyEPO 1.3 adds CVRP models across Gurobi/COPT/Pyomo backends. Not directly useful
for Lending Club credit selection; only a didactic Quarto sidebar or future
servicing/collections example. Decision: park.

### Performance And API Hardening

Release notes report broad 1.0-3.3x speedups for core methods and 6-14x CaVE+
speedups versus SPO+ on TSP, plus full public type annotations, solution-pool
refactors, expanded tests, CUDA tests and a docs overhaul. Supports tightening
the optional `spo` dependency and makes the DFL lane less fragile in
reviewer-facing reproducibility language.

## Local Probe

The parent probe created a dedicated environment outside the repo with PyTorch +
OR-Tools. The Windows-first equivalent (isolated, optional, never the default
`.venv`):

```powershell
uv venv .venv-pyepo --python 3.12
uv pip install --python .venv-pyepo\Scripts\python.exe "pyepo[ortools]==1.3.7"
```

Installed versions in the probe: `pyepo` 1.3.7, `torch` 2.12.0+cu130, `ortools`
9.15.6755, `numpy` 2.4.6, `pandas` 3.0.3, `clarabel` 0.11.1.

Smoke result on a tiny OR-Tools credit-selection LP:

| Check | Result |
|---|---|
| `optDataset` pre-solve | 48 instances solved |
| `SPOPlus` two-epoch training | loss moved from `1.403071` to `0.618665` |
| `regularizedFrankWolfeFenchelYoung` forward pass | returned finite scalar loss |
| `perturbedFenchelYoungMul` forward pass | returned finite scalar loss on positive shifted costs |

Interpretation: PyEPO 1.3.7 is usable in an isolated env with OR-Tools; we no
longer describe the whole DFL lane as blocked by `cvxpy/cvxpylayers`. The env is
heavy (`pyepo[ortools]` pulls PyTorch and CUDA wheels), so it stays
optional/isolated.

## Repo Fit (child)

| File | Observation | Action |
|---|---|---|
| `pyproject.toml` (`spo` extra, `pyepo>=1.0`) | Too loose for the new claim. | Later tighten to `pyepo[ortools]>=1.3.7,<1.4` in a dedicated dependency PR. |
| `src/optimization/spo_integration.py` | Verify the helper matches PyEPO 1.3 SPO+ signature `SPOPlus(pred, costs, sols, objs)` rather than the old `SPOPlus(pred, costs)`. | Deprecate or rewrite around `optDataset`. |
| `scripts/run_spo_real.py` | Canonical DFL prototype entrypoint candidate; confirm it uses the correct `optDataset` tuple. | Make this the canonical DFL prototype entrypoint. |
| `scripts/run_spo_comparison.py`, `scripts/run_crpto_vs_spo_stability.py` | Existing comparator/stability runners. | Keep as the comparator surface; add RFYL only after a real rerun. |
| `book/chapters/09-spo-regret.qmd` | Frames SPO+ as a regret comparator, not a conformal replacement. | Add a short PyEPO 1.3 footnote only after a real rerun. |

## Recommended Experiments

Historical intake status: Experiment A is now closed by the 2026-05-28 rerun.
Experiments B--D remain Paper 4 research lanes and are not prerequisites for
the CRPTO IJDS manuscript.

- **A - SPO+ repro rerun**: run `scripts/run_spo_real.py` in the isolated PyEPO
  env (`n_items=100`, `budget=30`, `epochs=50`, `seeds=5`). Gate: reproduces the
  current regret-improvement story within tolerance; logs PyEPO/Torch/solver
  versions. Sink: CRPTO appendix and Quarto `09-spo-regret`.
- **B - RFYL comparator**: add `regularizedFrankWolfeFenchelYoung` to the same
  sampled instances; compare two-stage Ridge, SPO+, RFYL and CRPTO robust costs.
  Gate: finite, stable regret across seeds; improves over two-stage or gives a
  useful speed/stability trade-off. Sink: Paper 4 DFL lane; optional CRPTO
  appendix.
- **C - multiplicative PFYL for risk-only costs**: positive costs only (`PD`,
  `PD_high`, ECL). Do not use raw `PD * LGD - int_rate` unless reframed. Sink:
  Paper 4 only.
- **D - CaVE binary prototype**: only if Gurobi is available; convert to binary
  top-k/fixed-budget, use `optDatasetConstrs` + `coneAlignedCosine`. Sink: Paper 4
  method appendix.

## Claim Boundaries

Allowed: "PyEPO 1.3.7 enables a reproducible isolated DFL comparator stack";
"RFYL is the most natural PyEPO 1.3 method for the current continuous credit LP
prototype"; "CaVE is promising for binary approval/top-k variants but requires a
Gurobi-backed binary model."

Not allowed: "PyEPO replaces CRPTO"; "SPO+/RFYL/CaVE provide conformal coverage
guarantees"; "CaVE applies to the current fractional champion without
reformulating the decision problem"; "multiplicative perturbation is valid for
signed net-return costs without a documented transformation."

## Editorial Recommendation

For **CRPTO**, keep PyEPO as a comparator appendix. The core claim remains CRPTO:
calibrated PD plus Mondrian conformal uncertainty plus a robust portfolio policy
that is auditable.

For **Paper 4 (agenda)**, reopen the SPO/DFL lane with a new stop rule: one SPO+
rerun, one RFYL comparator, optional multiplicative PFYL risk-only probe, optional
CaVE binary probe only if Gurobi is available. If those do not change a manuscript
claim or produce a cleaner comparator table, stop.
