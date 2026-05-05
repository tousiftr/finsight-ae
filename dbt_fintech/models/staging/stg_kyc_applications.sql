{{ config(materialized='view') }}

select
    payload ->> 'kyc_application_id' as raw_kyc_application_id,
    payload ->> 'kyc_application_id' as kyc_application_id,
    payload ->> 'customer_id' as customer_id,
    nullif(payload ->> 'submitted_at', '')::timestamptz as submitted_at,
    nullif(payload ->> 'reviewed_at', '')::timestamptz as reviewed_at,
    lower(nullif(payload ->> 'kyc_status', '')) as kyc_status,
    lower(nullif(payload ->> 'kyc_level', '')) as kyc_level,
    nullif(payload ->> 'document_type', '') as document_type,
    nullif(payload ->> 'country', '') as country,
    nullif(payload ->> 'risk_score', '')::numeric as risk_score,
    nullif(payload ->> 'rejection_reason', '') as rejection_reason,
    nullif(payload ->> 'review_channel', '') as review_channel,
    nullif(payload ->> 'reviewer_type', '') as reviewer_type,
    dt,
    batch_id,
    loaded_at,
    loaded_at as ingested_at
from {{ source('raw', 'raw_kyc_applications') }}
