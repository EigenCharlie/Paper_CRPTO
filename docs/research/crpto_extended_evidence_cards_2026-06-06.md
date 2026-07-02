# CRPTO Extended Evidence Cards - 2026-06-06

## Decision

This memo consolidates the remaining high-value material for the CRPTO book,
master's thesis and IJDS appendix surface. The material is imported as
**evidence cards**, not as a second manuscript, not as a dependency on another
workspace, and not as a promotion protocol.

The rule is deliberately conservative:

1. CRPTO keeps the promoted pool93 IJDS body point and the current funded-set
   claim.
2. Evidence cards can strengthen thesis chapters, appendix language, reviewer
   defenses and future-work gates.
3. Evidence cards do not reopen the champion, add heavy solver dependencies, or
   convert exploratory lanes into production claims.
4. Any future promotion requires a pre-declared claim target, evidence gate,
   artifact sink and stop rule inside this repository.

Canonical tables live in `reports/crpto/extended/`.

## Post-Pool93 IJDS Closure

After the pool93 closure, the IJDS manuscript should not import the full
sequential-decision laboratory as a second center of gravity. The paper-facing
surface is now:

- **Body:** pool93 A35 return-bound frontier, exact funded-set certificate and
  Theorem 1 under weighted funded-set validity.
- **Supplement:** A19 regret-auditability comparator, A20--A24 robustness and
  source diagnostics, and A35--A39 selected-allocation pool93 audits.
- **Submission package:** claim matrix and reproduction notes that preserve the
  A19 SPO+ numbering rule and the A35--A39 pool93 closure.
- **Thesis / extended evidence:** the full DFL, FICO-proxy, IFRS9/SICR,
  CRC/CROMS-lite and source-governance material below.

This means the extended cards remain useful, but none of them replaces A35--A39
or adds a hidden promotion criterion.

## Card Register

| card_id | card | thesis use | IJDS use | status |
|---|---|---|---|---|
| EC01 | PyEPO 1.3.7 / DFL formal suite | DFL comparator appendix | SPO+ comparator context only | append for thesis |
| EC02 | FICO proxy versus calibrated champion | model-risk and score-governance appendix | context only if reviewer asks | append for thesis |
| EC03 | IFRS9/SICR prudential absorption | prudential uncertainty appendix | implication/limitation only | append for thesis |
| EC04 | CRC/LTT and CROMS-lite decision-risk governance | decision-risk governance appendix | reviewer-defense only | append or future gate |

The machine-readable register is
`reports/crpto/extended/crpto_extended_evidence_cards_2026-06-06.csv`.

## EC01 - PyEPO 1.3.7 / DFL Formal Suite

**Claim target.** Show that modern decision-focused learning is a serious
regret comparator, while CRPTO remains the auditable conformal-risk method.

**Evidence.** The curated PyEPO suite uses `pyepo==1.3.7`,
`gurobipy==13.0.2`, an exact top-k oracle for standard methods and a
Gurobi-backed binary oracle for CaVE. All smoke and nonnegative-regret checks
passed.

| surface | best result | interpretation |
|---|---|---|
| Full DFL suite | SPO+ mean regret `0.122379`; RFYL `0.125405`; CaVE `0.128109` | SPO+ remains the regret leader; RFYL and CaVE are credible thesis comparators. |
| Temporal DFL suite | SPO+ mean regret `0.061835`; RFYL `0.071448`; CaVE `0.072284` | The DFL story survives a temporal surface. |
| Paired CRPTO comparator | SPO+ improvement `48.51%` versus two-stage | Supports the appendix claim already used by the IJDS supplement. |

**Destination.** Thesis appendix and DFL comparator discussion. IJDS only keeps
the existing SPO+ comparator framing.

**Boundary.** DFL can reduce regret, but it does not provide conformal coverage,
the exact funded-set bound, source-governance guarantees, or a replacement for
the CRPTO champion.

**Stop rule.** Do not import solver logs, Gurobi artifacts, PyTorch/PyEPO
dependencies or heavy run directories. Reopen only if a reviewer asks for a
comparator table or the thesis needs a standalone DFL appendix.

Canonical tables:

- `reports/crpto/extended/crpto_extended_pyepo_dfl_execution_ledger_20260528.csv`
- `reports/crpto/extended/crpto_extended_pyepo_dfl_full_summary_20260528.csv`
- `reports/crpto/extended/crpto_extended_pyepo_dfl_temporal_summary_20260528.csv`

## EC02 - FICO Proxy Versus Calibrated Champion Governance

**Claim target.** Support the governance claim that the calibrated champion is
not merely a repackaged traditional score signal.

**Evidence.** On the latest 40% of the OOT split (`n=103,865`), the calibrated
champion improves over the origin-time FICO proxy on both ranking and
calibration metrics:

| metric | delta champion - FICO proxy | interpretation |
|---|---:|---|
| AUC | `+0.10757` | stronger discrimination |
| Gini / Somers' D | `+0.21514` | stronger rank ordering |
| Brier | `-0.010815` | better probabilistic loss |
| ECE 10-bin | `-0.022137` | better calibration |
| Decile-band MAE | `-0.020532` | lower decile calibration error |
| Rank shift >= 20pp | `0.486526` | nearly half the loans move materially |

**Destination.** Model-risk, score-governance and thesis appendix. In IJDS this
is optional context only if a reviewer asks whether CRPTO depends on FICO-style
ranking.

**Boundary.** This is not a legal fair-lending claim, protected-attribute
inference, or champion replacement claim. It is a score-governance diagnostic.

**Stop rule.** Do not rerun unless a reviewer asks for score-governance
replication or a new external score dataset appears.

Canonical table:

- `reports/crpto/extended/crpto_extended_metric_governance_fico_vs_champion_2026-05-19.csv`

## EC03 - IFRS9/SICR Prudential Absorption

**Claim target.** Keep the prudential value of the IFRS9 lane inside the thesis
without turning IJDS into a second IFRS9 paper.

**Evidence.**

| prudential piece | retained value | boundary |
|---|---|---|
| ECL scenario propagation | baseline ECL `USD 870.3M`; severe ECL `USD 1.479B`; severe uplift `69.9%` | diagnostic scenario stress, not production allowance |
| Conformal ECL range | baseline point `USD 432.1M`; high conformal `USD 1.408B`; high/point ratio `3.26x` | uncertainty diagnostic, not audited regulatory capital |
| SICR conformal trigger | `t*=0.30`; recall of missed defaults `75.8%`; added ECL `USD 56.6M` | complementary signal, not contractual staging policy |
| Competing-risks correction | KM baseline about `USD 1.003B`; CIF-adjusted `USD 870.3M`; over-reserve about `USD 125.8M` | prepayment caveat, not a full IFRS9 engine |
| Stage threshold governance | minimum cost near `pd_threshold=0.15`; robust band `0.13--0.18` | thresholds are governance decisions |

**Destination.** Thesis prudential appendix and CRPTO implications/future-work
section. IJDS can mention it as applied implication only.

**Boundary.** IFRS9-inspired evidence is not contractual IFRS9. The repository
does not claim a production allowance model.

**Stop rule.** Keep contractual IFRS9 claims false without monthly DPD history,
cure logic, EAD paths, recovery/prepayment timing and governed macro scenarios.

Canonical table:

- `reports/crpto/extended/crpto_extended_prudential_ifrs9_absorption_2026-05-18.csv`

## EC04 - CRC/LTT And CROMS-Lite Governance

**Claim target.** Show that the project did not select a conformal method only
by visual preference or single-metric ranking; it also audited decision-risk
gates and selector tradeoffs.

**Evidence.**

- CRC/LTT-style gates over retained policies find `22` operational gate passes.
- One source-hardened candidate passes the stricter source-defense gate.
- The official CRPTO champion remains protected because the source-defense
  screen is a governance diagnostic, not a promotion protocol.
- CROMS-lite exposes return versus source-defense tradeoffs: a source-defended
  policy improves worst-source coverage by `+0.3636` but gives up
  `USD 3,842.90` of realized return versus the official champion.

**Destination.** Thesis decision-risk governance appendix and reviewer defense.
IJDS keeps A5/A10 as the official compact selector evidence.

**Boundary.** These are screens over retained artifacts, not end-to-end CROMS
training, not a new conformal selector, and not a champion promotion protocol.

**Stop rule.** Open a direct CRC/LTT decision-loss gate only with a declared
split and fixed monotone loss before outcomes.

Canonical tables:

- `reports/crpto/extended/crpto_extended_decision_risk_governance_crc_ltt_2026-05-18.csv`
- `reports/crpto/extended/crpto_extended_decision_risk_governance_croms_lite_2026-05-18.csv`
- `reports/crpto/extended/crpto_extended_future_experiment_gate_register_2026-05-19.csv`
- `reports/crpto/extended/crpto_extended_strong_appendix_register_2026-06-06.csv`

## Editorial Status

| surface | action |
|---|---|
| IJDS body | No change. The body remains CRPTO: calibrated PD, conformal uncertainty, robust policy and funded-set certificate. |
| IJDS supplement | Already carries the compact comparator/limitation language through A19--A39. |
| Quarto CRPTO book | Add these cards to the controlled appendix and thesis/future-work map. |
| Master's thesis | Use the full evidence-card register to show breadth, maturity, negative results and stop rules. |
| Future experiments | Reopen only from `reports/crpto/extended/crpto_extended_future_experiment_gate_register_2026-05-19.csv`. |

## Closed Or Parked Material

The following remain outside the CRPTO/IJDS claim:

- legal fair-lending certification;
- contractual IFRS9 allowance modeling;
- CATE policy value;
- online/live conformal deployment;
- exact Bellman optimality;
- DFL or PyEPO as champion replacement;
- GPU and quantum papers.

This keeps the thesis broad without making the IJDS paper look like several
papers competing for the same center.
