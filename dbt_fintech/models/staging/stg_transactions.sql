with source as (
    select *
    from {{ source('raw', 'raw_transactions') }}
),

renamed as (
    select
        payload ->> 'transaction_id' as transaction_id,
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,
        replace(replace(lower(trim(payload ->> 'transaction_type')), ' ', '_'), '-', '_') as transaction_type,
        nullif(payload ->> 'amount', '')::numeric as amount,
        payload ->> 'currency' as currency,
        lower(trim(payload ->> 'status')) as status,
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
),

deduped as (
    select *,
        row_number() over (
            partition by transaction_id
            order by coalesce(transaction_timestamp, ingested_at) desc, ingested_at desc
        ) as _rn
    from renamed
)

select * except(_rn)
from deduped
where _rn = 1
