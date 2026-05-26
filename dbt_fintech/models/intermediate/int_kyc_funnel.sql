{{ config(materialized='table', tags=['product_analytics_hourly']) }}

select
    customer_id,
    kyc_application_id,
    submitted_at,
    reviewed_at,
    kyc_status,
    kyc_level,
    risk_score,
    extract(epoch from (reviewed_at - submitted_at)) / 60.0 as time_to_review_minutes,
    (kyc_status = 'approved') as is_approved,
    (kyc_status = 'rejected') as is_rejected,
    (kyc_status = 'pending') as is_pending,
    (kyc_status = 'manual_review') as is_manual_review,
    (kyc_status = 'expired') as is_expired
from {{ ref('stg_kyc_applications') }}
