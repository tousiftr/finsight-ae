with source as (
    select *
    from {{ source('raw', 'raw_transactions') }}
)

select
    payload ->> 'transaction_id' as transaction_id,
    payload ->> 'account_id' as account_id,
    payload ->> 'customer_id' as customer_id,
    payload ->> 'transaction_type' as transaction_type,
    nullif(payload ->> 'amount', '')::numeric as amount,
    payload ->> 'currency' as currency,
    payload ->> 'status' as status,
    payload ->> 'merchant_category' as merchant_category,
    nullif(payload ->> 'transaction_timestamp', '')::timestamptz as transaction_timestamp,
    payload ->> 'batch_id' as payload_batch_id,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    loaded_at as ingested_at
from source
