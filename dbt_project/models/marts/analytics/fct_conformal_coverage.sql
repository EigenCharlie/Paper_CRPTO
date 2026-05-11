select
    grade,
    count(*) as n_loans,
    avg(case when y_true between pd_low_90 and pd_high_90 then 1.0 else 0.0 end) as coverage_90,
    avg(width_90) as avg_width_90
from {{ ref('stg_conformal_intervals') }}
group by 1
