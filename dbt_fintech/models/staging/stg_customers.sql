with source as (
    select
        dt,
        batch_id,
        payload,
        source_object_key,
        source_file_path,
        raw_record_hash,
        loaded_at
    from {{ source('raw', 'raw_customers') }}
)

select
    payload ->> 'customer_id' as customer_id,
    payload ->> 'first_name' as first_name,
    payload ->> 'last_name' as last_name,
    payload ->> 'email' as email,
    lower(payload ->> 'email') as email_normalized,
    payload ->> 'phone_number' as phone_number,
    payload ->> 'country' as country,
    payload ->> 'kyc_status' as customer_status,
    payload ->> 'signup_channel' as signup_channel,
    nullif(payload ->> 'created_at', '')::timestamptz as created_at,
    nullif(payload ->> 'updated_at', '')::timestamptz as updated_at,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    loaded_at as ingested_at
from source
