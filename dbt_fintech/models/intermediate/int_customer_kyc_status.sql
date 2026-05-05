{{ config(materialized='view') }}

with ranked as (
    select
        customer_id,
        kyc_application_id,
        kyc_status,
        kyc_level,
        risk_score,
        submitted_at,
        reviewed_at,
        row_number() over (
            partition by customer_id
            order by coalesce(reviewed_at, submitted_at) desc
        ) as rn
    from {{ ref('stg_kyc_applications') }}
)
select
    customer_id,
    kyc_application_id as latest_kyc_application_id,
    kyc_status as latest_kyc_status,
    kyc_level as latest_kyc_level,
    risk_score as latest_risk_score,
    submitted_at as latest_kyc_submitted_at,
    reviewed_at as latest_kyc_reviewed_at,
    (kyc_status = 'approved') as is_kyc_approved,
    (kyc_status = 'rejected') as is_kyc_rejected,
    (kyc_status = 'pending') as is_kyc_pending,
    (kyc_status = 'manual_review') as is_kyc_manual_review,
    (kyc_status = 'expired') as is_kyc_expired
from ranked
where rn = 1
