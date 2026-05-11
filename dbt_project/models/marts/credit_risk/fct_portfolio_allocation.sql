select
    *,
    realized_total_return / nullif(total_allocated, 0) as return_on_allocated_capital
from {{ ref('stg_portfolio_allocations') }}
qualify row_number() over (order by alpha01_exact_pass desc, realized_total_return desc) = 1
