select
    t.transaction_id,
    t.account_id,
    t.customer_id,
    t.transaction_ts,
    t.transaction_date,
    t.amount,
    t.currency,
    t.transaction_type,
    t.transaction_status,
    t.merchant_category,
    a.account_type,
    a.account_status,
    a.opened_at as account_opened_at,
    c.customer_status,
    c.country,
    t.batch_id,
    t.source_file_path,
    t.ingested_at
from {{ ref('int_transactions') }} t
left join {{ ref('int_accounts') }} a
    on t.account_id = a.account_id
left join {{ ref('int_customers') }} c
    on t.customer_id = c.customer_id
