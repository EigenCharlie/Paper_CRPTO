select *
from read_parquet('{{ var("crpto_data_dir") }}/test_predictions.parquet')
where y_prob_final < 0
   or y_prob_final > 1
   or coalesce(pd_calibrated, y_prob_final) < 0
   or coalesce(pd_calibrated, y_prob_final) > 1
