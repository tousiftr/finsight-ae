with source as (
    select *
    from {{ source('raw', 'raw_transactions') }}
)

select
    payload ->> 'transaction_id' as transaction_id,
    payload ->> 'account_id' as account_id,
    payload ->> 'customer_id' as customer_id,
    coalesce(
        nullif(payload ->> 'transaction_timestamp', ''),
        nullif(payload ->> 'transaction_time', ''),
        nullif(payload ->> 'occurred_at', ''),
        nullif(payload ->> 'posted_at', ''),
        nullif(payload ->> 'created_at', ''),
        nullif(payload ->> 'timestamp', '')
    )::timestamptz as transaction_ts,
    nullif(payload ->> 'amount', '')::numeric as amount,
    payload ->> 'currency' as currency,
    payload ->> 'transaction_type' as transaction_type,
    payload ->> 'transaction_status' as transaction_status,
    payload ->> 'merchant_category' as merchant_category,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    loaded_at as ingested_at
from source
