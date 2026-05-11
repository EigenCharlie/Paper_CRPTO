select
    cast(id as varchar) as loan_id,
    grade,
    temporal_segment,
    cast(y_true as double) as y_true,
    cast(y_pred as double) as pd_point,
    cast(pd_low_90 as double) as pd_low_90,
    cast(pd_high_90 as double) as pd_high_90,
    cast(width_90 as double) as width_90
from read_parquet('{{ var("crpto_conformal_winner_dir") }}/conformal_intervals_mondrian.parquet')
