{{ config(materialized='view') }}

select
    transaction_date,
    count(*) as transaction_count,
    sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then 1 else 0 end) as completed_transaction_count,
    sum(case when lower(transaction_status) in ('failed', 'declined', 'error') then 1 else 0 end) as failed_transaction_count,
    sum(case when lower(transaction_status) = 'pending' then 1 else 0 end) as pending_transaction_count,
    coalesce(sum(amount), 0) as gross_transaction_volume,
    coalesce(sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then amount else 0 end), 0) as completed_transaction_volume,
    coalesce(sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then fee_amount else 0 end), 0) as fee_revenue,
    avg(amount) as average_transaction_amount,
    (
        sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then 1 else 0 end)::numeric
        / nullif(count(*), 0)::numeric
    ) as transaction_success_rate
from {{ ref('int_transactions_enriched') }}
group by 1
