# CRPTO Multidataset External Replication - 2026-06-05

This note records the curated multidataset layer promoted into the IJDS paper,
online supplement, and thesis book. It is intentionally self-contained: it uses
local curated summaries under `reports/crpto/multidataset/source/` and does not
reference exploratory laboratory paths, browser sessions, or credentials.

## Editorial Decision

Promote two external economic replications:

- **Prosper final-status loans**: marketplace personal loans with final outcome,
  amount, rate/yield and temporal OOT candidates.
- **Freddie/Mendeley FM48**: single-family mortgage replication based on Freddie
  Mac loan-level performance data and the Mendeley processed train/OOS/OOT
  default-window package.

Archive Home Credit:

- **Home Credit Default Risk** is useful for scoring/conformal robustness, but
  it lacks a clean `exposure + return` investment contract comparable to Lending
  Club, Prosper and Freddie. It is not promoted in the main IJDS external claim.

## Main Results

| Dataset | Rows | Default rate | AUC | Coverage 90% | alpha = 0.01 coverage | OOT candidates | Robust LP objective |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prosper final-status | `54,807` | `30.92%` | `0.7074` | `0.9205` | `0.9943` | `10,531` | `$199,419` |
| Freddie/Mendeley FM48 | `3,173,355` | `1.45%` | `0.7839` | `0.9745` | `0.9907` | `1,396,053` | `$1,291,228` |

These results strengthen the empirical defense against the single-dataset
critique. They do not replace the official Lending Club champion or create a new
universal exact certificate.

## Extended Audit Results

- **Freddie all-candidate LP certificate:** the FM48 robust LP was solved at
  `500,000`, `1,000,000`, and all `1,396,053` OOT candidates. The robust
  objective is unchanged at `$1,291,228`; the all-candidate optimum funds `143`
  loans, the worst funded rank is `551`, and zero funded loans fall outside the
  top-`250,000` screen.
- **Freddie sparse Mondrian audit:** all-group minimum coverage is driven by
  four tiny sparse groups containing `43` OOT rows. Eligible groups
  (`cal+test >= 500`) cover `1,396,010` OOT rows and raise minimum 90% coverage
  to `0.8854`; this supports a global external claim, not perfect conditional
  coverage in every mortgage cell.
- **Intervals and subperiods:** Prosper AUC is `0.7073` with CI
  `[0.6956, 0.7190]`; Freddie AUC is `0.7839` with CI `[0.7799, 0.7878]`.
  Prosper 2012/2013 and Freddie 2015Q1--Q4 keep 90% coverage above target, while
  Freddie 2015Q4 alpha coverage is a documented edge case at `0.9896`.
- **Prosper default definitions:** main, `Defaulted`-only, and `Chargedoff`-only
  definitions all pass the 90% and alpha01 gates with positive all-candidate
  robust LP objectives.
- **Freddie red/green segments:** combined FM48 and green pass alpha01; red
  passes 90% coverage and has positive all-candidate robust value but fails the
  alpha01 gate at `0.9850`, so it remains sensitivity evidence only.
- **Cross-dataset price of robustness (A34):** under frozen application (no
  champion search) the signed price of robustness is a positive premium that
  increases monotonically with the panel default rate: Freddie green `0.58%`
  pays `+1.00%`, Freddie combined `1.45%` pays `+1.09%`, Freddie red `2.97%`
  pays `+2.37%`, and Prosper `30.92%` pays `+9.46%`. The selected Lending Club
  champion is favorable (`-10.56%`). The premium tracks irreducible default risk
  rather than discrimination (green and red have near-identical AUC). This turns
  the external layer into a positive economic finding, not only a defensive gate.

## Artifacts

- Tables:
  - `reports/crpto/tables/crpto_tableA25_external_replication_gate.csv`
  - `reports/crpto/tables/crpto_tableA26_external_candidate_sensitivity.csv`
  - `reports/crpto/tables/crpto_tableA27_freddie_horizon_sensitivity.csv`
  - `reports/crpto/tables/crpto_tableA28_external_lp_exhaustiveness.csv`
  - `reports/crpto/tables/crpto_tableA29_freddie_mondrian_sparse_group_audit.csv`
  - `reports/crpto/tables/crpto_tableA30_external_metric_intervals.csv`
  - `reports/crpto/tables/crpto_tableA31_external_subperiod_metrics.csv`
  - `reports/crpto/tables/crpto_tableA32_prosper_default_definition_sensitivity.csv`
  - `reports/crpto/tables/crpto_tableA33_freddie_segment_sensitivity.csv`
  - `reports/crpto/tables/crpto_tableA34_price_of_robustness_cross_dataset.csv`
    (built by `scripts/build_price_of_robustness_cross_dataset.py` from the
    status JSON; derived secondary table, not part of the main builder outputs)
- Figures:
  - `reports/crpto/figures/crpto_fig22_external_replication.png`
  - `reports/crpto/figures/crpto_fig23_external_candidate_sensitivity.png`
  - `reports/crpto/figures/crpto_fig24_freddie_all_candidate_certificate.png`
- Book copies:
  - `book/assets/figures/publication/crpto_fig22_external_replication.png`
  - `book/assets/figures/publication/crpto_fig23_external_candidate_sensitivity.png`
  - `book/assets/figures/publication/crpto_fig24_freddie_all_candidate_certificate.png`
- Status:
  - `models/crpto_multidataset_external_status.json`
- Builder:
  - `scripts/build_multidataset_external_replication.py`

Regenerate with:

```bash
uv run python scripts/build_multidataset_external_replication.py
```

## Dataset Sources

- Prosper loan-level data access documentation:
  <https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper>
- Freddie Mac Single Family Loan-Level Dataset:
  <https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset>
- Freddie/Mendeley processed mortgage windows:
  <https://data.mendeley.com/datasets/bzr2rxttvz/3>
- Home Credit Default Risk, archived only:
  <https://www.kaggle.com/competitions/home-credit-default-risk/data>

## Claim Boundary

Allowed wording:

- "CRPTO preserves conformal gates and positive robust LP objectives on two
  external economic credit datasets."
- "The external layer reduces the risk that the result is merely a Lending Club
  artifact."
- "Freddie FM48 is solved on the full OOT candidate universe; the top-screen
  result is an exhaustiveness certificate, not an untested cap."

Avoid:

- "The exact Lending Club funded-set certificate automatically transfers to all
  datasets."
- "Home Credit supports the economic LP claim."
- "The result is a live or prospective deployment validation."
- "Every external subgroup satisfies perfect conditional or alpha01 coverage."
