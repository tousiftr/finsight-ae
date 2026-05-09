{{ config(materialized='view') }}

select
    customer_id,
    concat_ws(' ', first_name, last_name) as full_name,
    email,
    country,
    city,
    signup_channel,
    customer_segment,
    employment_status,
    income_band,
    risk_segment,
    kyc_status,
    created_at,
    updated_at,
    (kyc_status = 'approved') as is_kyc_approved,
    extract(day from (current_timestamp - created_at))::int as customer_age_days
from {{ ref('stg_customers') }}
