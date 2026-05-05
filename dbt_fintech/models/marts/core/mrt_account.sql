{{ config(materialized='view') }}

select
    account_id,
    customer_id,
    account_type,
    investment_sub_type,
    currency,
    account_status,
    opened_at,
    closed_at,
    current_balance,
    customer_segment,
    latest_kyc_status,
    risk_segment
from {{ ref('int_account_enriched') }}
