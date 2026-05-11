select
    loan_id,
    cast(y_true as double) as y_true,
    cast(y_prob_final as double) as pd_point,
    cast(coalesce(pd_calibrated, y_prob_final) as double) as pd_calibrated
from read_parquet('{{ var("crpto_data_dir") }}/test_predictions.parquet')
