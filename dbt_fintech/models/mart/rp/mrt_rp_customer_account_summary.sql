select
    ca.customer_id,
    ca.account_id,
    ca.customer_status,
    ca.country,
    ca.account_type,
    ca.account_sub_type,
    ca.plan_tier,
    ca.investment_sub_type,
    ca.account_status,
    ca.opened_at,
    ca.closed_at,
    ca.initial_balance,
    ca.current_balance,
    te.transaction_id,
    te.transaction_ts,
    te.transaction_date,
    te.amount,
    te.currency,
    te.transaction_type,
    te.transaction_status
from {{ ref('int_customer_accounts') }} ca
left join {{ ref('int_transactions_enriched') }} te
    on ca.account_id = te.account_id
