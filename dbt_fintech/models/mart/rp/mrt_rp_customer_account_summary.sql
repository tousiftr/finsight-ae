-- depends_on: {{ ref('int_customer_accounts') }}
select
    ca.customer_id,
    ca.account_id,
    ca.customer_status,
    ca.country,
    ca.account_type,
    ca.account_sub_type,
    ca.plan_tier,
    ca.account_status,
    ca.opened_at,
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
