with source as (
    select *
    from {{ source('raw', 'raw_kyc_applications') }}
)

select
    payload ->> 'kyc_application_id' as kyc_application_id,
    payload ->> 'customer_id' as customer_id,
    nullif(payload ->> 'submitted_at', '')::timestamptz as submitted_at,
    nullif(payload ->> 'reviewed_at', '')::timestamptz as reviewed_at,
    payload ->> 'kyc_status' as kyc_status,
    payload ->> 'kyc_level' as kyc_level,
    payload ->> 'document_type' as document_type,
    payload ->> 'country' as country,
    nullif(payload ->> 'risk_score', '')::numeric as risk_score,
    nullif(payload ->> 'rejection_reason', '') as rejection_reason,
    payload ->> 'review_channel' as review_channel,
    payload ->> 'reviewer_type' as reviewer_type,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    loaded_at as ingested_at
from source
