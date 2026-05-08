{{ config(materialized='table') }}

select
    a.account_id,
    a.customer_id,
    a.account_type,
    a.account_sub_type,
    a.plan_tier,
    a.investment_sub_type,
    a.currency,
    a.account_status,
    a.opened_at,
    a.closed_at,
    a.current_balance,
    p.signup_channel,
    p.customer_segment,
    p.latest_kyc_status,
    p.risk_segment
from {{ ref('int_accounts') }} a
left join {{ ref('int_customer_profile') }} p using (customer_id)
