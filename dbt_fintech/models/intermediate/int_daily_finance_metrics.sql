select
    transaction_date,
    currency,
    count(*) as transaction_count,
    sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then 1 else 0 end) as approved_transaction_count,
    sum(case when lower(transaction_status) = 'declined' then 1 else 0 end) as declined_transaction_count,
    sum(case when lower(transaction_status) in ('failed', 'error') then 1 else 0 end) as failed_transaction_count,
    sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then amount else 0 end) as approved_transaction_amount,
    avg(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then amount end) as average_approved_transaction_amount,
    (
        sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then 1 else 0 end)::numeric
        / nullif(count(*), 0)::numeric
    ) as transaction_success_rate
from {{ ref('int_transactions_enriched') }}
group by transaction_date, currency
