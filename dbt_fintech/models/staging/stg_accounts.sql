with source as (

    select *
    from {{ source('raw', 'raw_accounts') }}

),

renamed as (

    select
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,

        payload ->> 'account_type' as account_type,
        payload ->> 'account_status' as account_status,
        nullif(payload ->> 'opened_at', '')::timestamptz as opened_at,

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