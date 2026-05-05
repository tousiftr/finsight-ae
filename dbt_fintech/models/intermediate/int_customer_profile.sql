{{ config(materialized='view') }}

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.country,
    c.city,
    c.created_at,
    c.signup_channel,
    c.customer_segment,
    c.employment_status,
    c.income_band,
    c.risk_segment,
    k.latest_kyc_application_id,
    k.latest_kyc_status,
    k.latest_kyc_level,
    k.latest_risk_score,
    k.latest_kyc_submitted_at,
    k.latest_kyc_reviewed_at,
    coalesce(k.is_kyc_approved, false) as is_kyc_approved,
    coalesce(k.is_kyc_rejected, false) as is_kyc_rejected,
    coalesce(k.is_kyc_pending, false) as is_kyc_pending,
    coalesce(k.is_kyc_manual_review, false) as is_kyc_manual_review,
    coalesce(k.is_kyc_expired, false) as is_kyc_expired,
    extract(year from age(current_date, c.date_of_birth))::int as customer_age,
    (current_date - c.created_at::date) as days_since_signup
from {{ ref('stg_customers') }} c
left join {{ ref('int_customer_kyc_status') }} k using (customer_id)
