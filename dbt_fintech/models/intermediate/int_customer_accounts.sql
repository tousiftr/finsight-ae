select
    a.account_id,
    a.customer_id,
    c.customer_status,
    c.country,
    c.created_at as customer_created_at,
    a.account_type,
    a.account_sub_type,
    a.plan_tier,
    a.investment_sub_type,
    a.account_status,
    a.opened_at,
    a.closed_at,
    a.initial_balance,
    a.current_balance,
    a.batch_id,
    a.source_file_path,
    a.ingested_at
from {{ ref('int_accounts') }} a
left join {{ ref('int_customers') }} c
    on a.customer_id = c.customer_id
