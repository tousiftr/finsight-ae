with source as (
    select *
    from {{ source('raw', 'raw_accounts') }}
)

select
    payload ->> 'account_id' as account_id,
    payload ->> 'customer_id' as customer_id,
    payload ->> 'account_type' as account_type,
    nullif(payload ->> 'investment_sub_type', '') as investment_sub_type,
    payload ->> 'currency' as currency,
    payload ->> 'account_status' as account_status,
    nullif(payload ->> 'opened_at', '')::timestamptz as opened_at,
    nullif(payload ->> 'updated_at', '')::timestamptz as updated_at,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    loaded_at as ingested_at
from source
