{{ config(materialized='view') }}

select
    customer_id,
    first_name,
    last_name,
    email,
    country,
    city,
    created_at,
    signup_channel,
    customer_segment,
    employment_status,
    income_band,
    risk_segment,
    latest_kyc_status,
    latest_kyc_level,
    latest_risk_score,
    is_kyc_approved,
    days_since_signup
from {{ ref('int_customer_profile') }}
