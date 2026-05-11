# Run Comparison: crpto-e2e-all-champions-2026-04-07

- Generated: 2026-04-07T17:48:44.349138+00:00
- Overall gates pass: `False`
- Conformal promotion pass: `True`
- Conformal statistical warning: `True`
- Artifact coherence pass: `False`
- Semantic coherence pass: `True`
- Fairness absolute (business) pass: `True`
- A/B gate mode: `no_regression`
- A/B no-regression pass: `True`
- A/B significance (diagnostic): `False`

## Gates
- `artifact_coherence`: **FAIL**
- `semantic_coherence`: **PASS**
- `pd_quality`: **PASS**
- `conformal_policy`: **PASS**
- `ab_no_regression`: **PASS**
- `fairness_relative`: **PASS**
- `fairness_absolute_business`: **PASS**
- `survival_quality`: **PASS**
- `export_contracts`: **PASS**

## Artifact Changes
- `data/processed/model_comparison.json`: hash_changed=True, baseline_exists=True, current_exists=True
- `data/processed/pipeline_summary.json`: hash_changed=True, baseline_exists=True, current_exists=True
- `data/processed/portfolio_robustness_frontier.parquet`: hash_changed=True, baseline_exists=True, current_exists=True
- `data/processed/portfolio_robustness_summary.parquet`: hash_changed=True, baseline_exists=True, current_exists=True
- `models/conformal_policy_status.json`: hash_changed=True, baseline_exists=True, current_exists=True
- `models/fairness_audit_status.json`: hash_changed=True, baseline_exists=True, current_exists=True
- `models/governance_status.json`: hash_changed=True, baseline_exists=True, current_exists=True
- `reports/dvc/metrics_summary.json`: hash_changed=True, baseline_exists=True, current_exists=True

## Conformal Diagnostics
- Statistical warnings (non-blocking): `kupiec_pvalue_90`, `kupiec_pvalue_95`, `christoffersen_pvalue_90`, `christoffersen_pvalue_95`
