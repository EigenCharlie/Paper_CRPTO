with rates as (
    select avg(y_true) as default_rate
    from read_parquet('{{ var("crpto_data_dir") }}/test_predictions.parquet')
)
select *
from rates
where default_rate <= 0 or default_rate >= 0.5
