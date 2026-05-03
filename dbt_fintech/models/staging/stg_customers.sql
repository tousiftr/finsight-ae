with source as (
    select dt, batch_id, payload, source_object_key, source_file_path, raw_record_hash, loaded_at
    from {{ source('raw', 'raw_customers') }}
),

renamed as (
    select
        payload ->> 'customer_id' as customer_id,
        payload ->> 'first_name' as first_name,
        payload ->> 'last_name' as last_name,
        lower(payload ->> 'email') as email,
        payload ->> 'phone_number' as phone_number,
        payload ->> 'country' as country,
        lower(trim(payload ->> 'signup_channel')) as signup_channel,
        lower(trim(payload ->> 'kyc_status')) as kyc_status,
        nullif(payload ->> 'created_at', '')::timestamptz as created_at,
        nullif(payload ->> 'updated_at', '')::timestamptz as updated_at,
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
            partition by customer_id
            order by coalesce(updated_at, created_at, ingested_at) desc, ingested_at desc
        ) as _rn
    from renamed
)

select
    customer_id,
    first_name,
    last_name,
    email,
    phone_number,
    country,
    signup_channel,
    kyc_status,
    created_at,
    updated_at,
    dt,
    batch_id,
    source_object_key,
    source_file_path,
    raw_record_hash,
    ingested_at
from deduped
where _rn = 1
