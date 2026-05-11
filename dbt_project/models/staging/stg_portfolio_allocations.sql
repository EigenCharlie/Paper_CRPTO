select
    policy_mode,
    cast(risk_tolerance as double) as risk_tolerance,
    cast(gamma as double) as gamma,
    cast(uncertainty_aversion as double) as uncertainty_aversion,
    cast(realized_total_return as double) as realized_total_return,
    cast(n_funded as integer) as n_funded,
    cast(total_allocated as double) as total_allocated,
    cast(alpha01_exact_pass as boolean) as alpha01_exact_pass,
    cast(alpha01_weighted_miscoverage_V as double) as alpha01_weighted_miscoverage_V,
    cast(alpha01_gamma_cp as double) as alpha01_gamma_cp
from read_parquet('{{ var("crpto_portfolio_dir") }}/portfolio_bound_aware_shortlist.parquet')
