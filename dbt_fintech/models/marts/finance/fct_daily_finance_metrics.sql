{{ config(materialized='table') }}

select
    transaction_date,
    currency,
    count(*) as transaction_count,
    sum(case when status = 'completed' then 1 else 0 end) as completed_transaction_count,
    sum(case when status in ('failed', 'declined') then 1 else 0 end) as failed_transaction_count,
    sum(amount) as gross_transaction_volume,
    sum(coalesce(fee_amount, 0)) as fee_revenue,
    avg(amount) as average_transaction_value,
    (sum(case when status = 'completed' then 1 else 0 end)::numeric / nullif(count(*), 0)::numeric) as transaction_success_rate
from {{ ref('int_transactions_enriched') }}
group by 1,2
