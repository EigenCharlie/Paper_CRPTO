> **RESEARCH NOTE** — Verification log of frozen-field definitions against their
> canonical compute. No values were changed by this audit; it records that the
> paper/book/supplement match the frozen artifacts and the upstream formulas.

# CRPTO — Frozen-Field Definition Audit (2026)

This note documents the audit of every headline frozen field against (a) the
formula that computes it and (b) the frozen artifact that stores it. The goal is
to make the paper's numbers defensible field-by-field before submission.

## Field → formula → status

| Field | Canonical formula (upstream compute) | Frozen value (champion) | Paper/book match |
|---|---|---|---|
| `gamma_cp` (`Γ_CP`) | `Σ wᵢ · clip(pd_highᵢ − pd_pointᵢ, 0, 1)`, weights over the funded set | `0.18591` | ✅ exact |
| `weighted_miscoverage_V` (`V`) | `Σ wᵢ · 1{y_trueᵢ > pd_highᵢ}` (observed default, not latent PD) | `0.03645` | ✅ exact |
| `violation` | `max(0, Σ wᵢ·y_trueᵢ − τ)` | `0.0` | ✅ exact |
| `sqrt_alpha` / bound-c | `√α`; pass iff `V ≤ √α` | `0.10000`, pass | ✅ exact |
| `realized_total_return` | default → `−L·aᵢ` (L=0.45); survive → `+cᵢ·aᵢ`, summed over funded | `$170,464.54` | ✅ exact; Method now states the LP objective is the *expected* `cᵢ − p̃ᵢ·L`, separate from this realized accounting |
| `expected_return_net_point` | `Σ alloc·amount·(int_rate − pd_point·L)` (LP objective value) | `$151,480.27` | ✅ exact |
| `price_of_robustness` | `expected(non-robust baseline) − expected(robust)`; `_pct = price/|baseline|` | `−$14,465.69` (`−10.56%`), baseline `$137,014.58` | ✅ corrected in round 9 (signed) |
| `p_tilde` (robust PD) | `p_hat + γ·(u(α) − p_hat)`, clipped to `[0,1]` | γ=0.45 | ✅ exact |
| robust region | 45 unique policies, all pass α=0.01; `n_exact_checks=180` (45×4 α-levels); τ∈[0.155,0.175], γ∈[0.45,0.55] | `45/45` | ✅ exact |
| Coverage (winner policy) | `coverage_90` of the promoted Mondrian winner | `0.9297` | ✅ exact (distinct from marginal) |
| Coverage (marginal, A23) | marginal `coverage_90` on the frozen intervals | `0.9293` | ✅ exact; used only in the A23 distribution-robustness context |
| A23 worst grade | per-grade `coverage_90`, min over grades (grade E) | `0.9004` (> 0.90 target) | ✅ exact |
| A22 tightest CVaR cap | max-return α01-safe policy under decision-time CVaR95 cap | `$160,978` (`−5.57%`), cap `0.4061` | ✅ exact |
| A20 top satisficing challenger | best satisficing-pass policy by CVaR/return | `$167,069.48` (`−1.99%` return, `−22.58%` CVaR95) | ✅ exact |
| Champion CVaR95 | implied from A20 challenger delta | `0.2542` | ✅ exact |
| Funded set | `n_funded`, exposure shares sum to 1.0 | 335 loans, 100% exposure | ✅ exact; body 4-bucket aggregation (23+114+147+51) reconciles |

## Conventions confirmed

- The `realized_total_return` uses a flat `L = 0.45` LGD on defaults; the regret
  benchmark (A19) uses a separate synthetic protocol with `L = 0.4` and 50-item
  instances — the two are different experiments and are not interchanged.
- `Γ_CP` (portfolio conformal premium, post-allocation) and the lowercase policy
  `γ` are kept typographically and semantically distinct throughout.
- `V` is weighted by exposure, not by loan count, so the per-grade `V`
  contributions sum to the headline `0.03645`.

## Outcome

No numeric corrections were required by this extended audit (rounds 9--10 had
already fixed the price-of-robustness sign and the LP-objective wording). Every
headline number in the paper body, the `.tex`, the supplement, and the book traces
to a frozen artifact and its documented formula.
