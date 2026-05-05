{{ config(materialized='view') }}

select
    t.transaction_id,
    t.account_id,
    t.customer_id,
    t.transaction_type,
    t.transaction_timestamp,
    t.transaction_timestamp::date as transaction_date,
    t.amount,
    t.currency,
    t.merchant_id,
    t.status,
    t.payment_method,
    t.fee_amount,
    t.failure_reason,
    a.account_type,
    a.investment_sub_type,
    p.signup_channel,
    p.customer_segment,
    p.latest_kyc_status,
    p.risk_segment,
    (t.status = 'completed') as is_successful_transaction,
    (t.status in ('failed', 'declined')) as is_failed_transaction
from {{ ref('stg_transactions') }} t
left join {{ ref('stg_accounts') }} a using (account_id)
left join {{ ref('int_customer_profile') }} p using (customer_id)
