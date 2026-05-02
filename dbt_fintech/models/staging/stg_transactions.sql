with source as (

    select *
    from {{ source('raw', 'raw_transactions') }}

),

renamed as (

    select
        payload ->> 'transaction_id' as transaction_id,
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,

        nullif(payload ->> 'transaction_timestamp', '')::timestamptz as transaction_timestamp,
        nullif(payload ->> 'amount', '')::numeric as amount,
        payload ->> 'currency' as currency,
        payload ->> 'transaction_type' as transaction_type,
        payload ->> 'transaction_status' as transaction_status,

        dt,
        batch_id,
        source_object_key,
        source_file_path,
        raw_record_hash,
        loaded_at

    from source

)

select *
from renamed