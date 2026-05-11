select
    case
        when pd_point < 0.05 then '00_low'
        when pd_point < 0.10 then '01_medium'
        else '02_high'
    end as pd_band,
    count(*) as n_loans,
    avg(y_true) as default_rate,
    avg(pd_point) as mean_pd,
    avg(abs(y_true - pd_point)) as mean_abs_error
from {{ ref('stg_test_predictions') }}
group by 1
