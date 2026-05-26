{{ config(materialized='view', tags=['product_analytics_hourly']) }}

with first_txn as (
    select customer_id, min(transaction_timestamp) as first_transaction_at
    from {{ ref('stg_transactions') }}
    where status = 'completed'
    group by 1
), acct as (
    select customer_id, min(opened_at) as first_account_opened_at
    from {{ ref('stg_accounts') }}
    group by 1
)
select
    c.customer_id,
    c.created_at::date as signup_date,
    c.signup_channel,
    (k.customer_id is not null) as has_kyc,
    coalesce(k.is_kyc_approved, false) as is_kyc_approved,
    (a.customer_id is not null) as has_account,
    (t.customer_id is not null) as has_completed_transaction,
    t.first_transaction_at,
    t.first_transaction_at as activated_at,
    extract(day from (t.first_transaction_at - c.created_at))::int as days_to_activation
from {{ ref('stg_customers') }} c
left join {{ ref('int_customer_kyc_status') }} k using (customer_id)
left join acct a using (customer_id)
left join first_txn t using (customer_id)
