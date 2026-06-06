> **RESEARCH NOTE** — Bound-and-literature audit ported and de-identified from the
> CRPTO bound-audit ledger (May 2026). Working material for the
> IJDS paper; the canonical numbers live in `EXTRACTION_MANIFEST.json` and
> `models/final_project_promotion.json`.

# CRPTO — Bound & Literature Audit

Editorial objective: a publishable IJDS paper on Conformal Robust
Predict-Then-Optimize (CRPTO). This note records (1) the canonical decision, (2)
the literature matrix that anchors the bound, (3) the bound audit, and (4) the
claim→artifact map.

## Canonical decision

The official champion is run tag `paper-thesis-final-economic-2026-04-06`, policy
`bound_aware_276k_economic_champion`. The `theorem-tight` comparator stays an
internal point for theoretical tightness, not the official policy.

| Role | Canonical source | Use |
|---|---|---|
| Official policy & robust region | `models/final_project_promotion.json` | champion, return, bound pass, region 45/45 |
| Exported policy | `models/champion_portfolio_policy.json` | operational freeze of the policy |
| Final summary | `data/processed/final_project_summary.parquet` | paper/thesis support |
| Exact 276k bound | `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/portfolio_bound_aware_bound_eval.parquet` | exact checks by alpha/policy |
| Conformal winner | `final_project_promotion.json::conformal_upstream.winner_metrics` | coverage/width/min-group/Winkler |
| Operational PD | `data/processed/pipeline_summary.json`, `reports/dvc/metrics_summary.json` | live AUC/Brier/ECE |

## Canonical metrics

| Metric | Value |
|---|---:|
| Run tag | `paper-thesis-final-economic-2026-04-06` |
| Label | `bound_aware_276k_economic_champion` |
| `risk_tolerance` | 0.175 |
| `policy_mode` | `blended_uncertainty` |
| `gamma` | 0.45 |
| `uncertainty_aversion` | 0.10 |
| `alpha01_exact_pass` | true |
| `alpha01_weighted_miscoverage_V` | 0.03645 |
| `alpha01_gamma_cp` | 0.18591 |
| `alpha01_violation` | 0.00000 |
| Realized return | 170,464.54 |
| Price of robustness | −10.56% |
| Robust region | 45/45 policies pass `alpha01` |

Conformal winner: `coverage_90 = 0.929714`, `coverage_95 = 0.966388`,
`avg_width_90 = 0.784230`, `min_group_coverage_90 = 0.918983`, `winkler_90 = 1.110742`.

PD operational: `paper1-e2e-all-champions-2026-04-07` reports AUC 0.712438,
Brier 0.154631, ECE 0.006380 in `pipeline_summary.json`. A historical PD-only
candidate reached AUC 0.713852 but is **not** promoted (it is not the paper/thesis
champion and must not be mixed with the bound-aware family).

## Literature matrix — base PDFs (thesis library)

| Concept/focus | Relevant formula/figure | Current use | Concrete improvement |
|---|---|---|---|
| Conformal Risk Control: controls expectation of bounded monotone losses | risk control over `E[L(C_λ(X),Y)]` | theoretical base of Theorem 1 | keep as central cite; clarify CRPTO instantiates the loss as weighted miscoverage |
| RCPS / distribution-free risk-controlling sets | λ-selection to control risk with a calibration sample | supports `risk control` language | defend post-hoc calibration; separate theoretical guarantee from post-selection evidence |
| Learn-then-Test | learn-then-test with finite control | supports approval-based closure narrative | justify guardrails/audit, not to inflate the bound |
| Conformal Uncertainty Sets for RO | conformal set → robust feasibility | CP→RO bridge cite | contrast: they do not land a weighted credit funded-set |
| Predict-then-Calibrate | coverage guarantee for cost vector | closest methodological comparator | PtC covers parameter/cost; CRPTO controls a weighted funded-set target |
| SPO+ / decision regret | SPO loss / SPO+ surrogate | main DFL comparator | keep as benchmark: better regret, weaker formal auditability |
| Task-based end-to-end DFL | gradients through the optimization solution | DFL antecedent | use as antecedent, not a direct competitor to the conformal guarantee |
| The Price of Robustness | Bertsimas–Sim `Γ`; price of robustness | base of `Γ_CP` language | reinforce the analogy; clarify `Γ_CP` is inherited from CP |

## Recent-frontier intake (the 17-PDF re-read)

| Line | Key reading | Concrete future-work hook |
|---|---|---|
| CRO/CRS (robust satisficing) | `U_α(z) = {d: s(z,d) ≤ η_α}`; CRO/CRS equivalence; `O(n^-1/2)` concentration | propose a fragility/satisficing metric alongside `Γ_CP` and price of robustness |
| End-to-end conformal calibration | ETO vs E2E; exact differentiation of calibration; PICNN convex sets | future: a conformal score trained by the portfolio loss |
| Online DFL | DF-FTPL / DF-OGD; online regret | future sequential work for continuous origination and CRPTO-vs-DFL under drift |
| CROMS | E/F/J-CROMS; finite-robustness vs compute trade-off | select the conformal family by robust return, `V`, `Γ_CP`, violation — not coverage/width alone |
| Conformal Risk Training | conformal OCE risk control; differentiable conformal risk | control the funded-set loss tail with OCE/CVaR, not only expectation/Markov (→ A22) |
| MDCP | `min_k P(Y∈C(X)|P^(k)) ≥ 1−α`; max-p aggregation | extend Mondrian to robust coverage without knowing the test group (→ A23) |
| Online CP via universal portfolios | UP-OCP parameter-free; pinball loss; finite miscoverage bounds | replace the generic ACI mention with a modern online route under stream (→ A24) |

## Bound audit

- The theorem controls a bounded target `Y_i ∈ [0,1]` and the weighted miscoverage
  `V = Σ_i w_i · 1{Y_i > u_i}`.
- The reading of `Y_i` as a latent PD is an **additional assumption**, not an observable.
- The policy is fixed **before** observing the evaluated labels; the 276k is
  post-selection empirical validation, not a stronger conformal guarantee.
- **Markov** is the principal distribution-free result.
- **Hoeffding/Bernstein** are a conditional tightening under additional
  independence/structure assumptions, not a replacement.

Open journal risk: formalize whether the conformal wrapper should cover observed
default, latent PD, expected loss, or a calibrated risk score. The validation code
(`scripts/validate_alpha_gamma_bound.py` in this repository) uses `y_true`/`default_flag`
against `pd_high`, so the text must not claim more than that without an extra lemma.

## Claim → artifact map

| Paper claim | Supporting artifact | Status |
|---|---|---|
| Official champion = bound-aware economic champion | `models/final_project_promotion.json` | synced |
| Official return `$170,464.54` | `final_champion.realized_total_return` | synced |
| Exact `alpha01` pass | `final_champion.alpha01_exact_pass` | synced |
| Full robust region `45/45` | `robust_region_summary` | synced |
| `V=0.03645`, `Γ_CP=0.18591`, `violation=0` | `final_champion` | synced |
| Conformal winner coverage/width/min-group | `conformal_upstream.winner_metrics` | synced |
| PD operational AUC/Brier/ECE | `pipeline_summary.json`, `reports/dvc/metrics_summary.json` | synced (with family note) |

## Prioritized improvement plan (carried into the local repo)

1. Journal `claim → artifact → test` table in the reproducible appendix. **Done**
   (local `book/chapters/06b-guia-editorial-claims.qmd`).
2. Separate lemma for the latent-PD reading, or drop that reading from the main theorem.
3. Minimal future-work experiment: nested holdout to confirm the bound-aware
   selection does not use the same OOT as sole evidence. **Done** as Appendix A3 family.
4. Decision-aware conformal selector inspired by CROMS — compare families by robust
   return, `V`, `Γ_CP`, violation, on a separate holdout.
5. OCE/CVaR funded-set tail extension inspired by Conformal Risk Training. **Done**
   as Appendix A22.
6. Multi-distribution robustness and online recalibration as future/robustness work.
   **Done** as Appendices A23 (multi-distribution) and A24 (online/ACI).
7. Keep SPO+ as a regret comparator, not a coverage baseline.
