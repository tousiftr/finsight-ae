with source as (
    select *
    from {{ source('raw', 'raw_accounts') }}
),

renamed as (
    select
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,
        replace(replace(lower(trim(payload ->> 'account_type')), ' ', '_'), '-', '_') as account_type,
        nullif(lower(trim(payload ->> 'investment_sub_type')), '') as investment_sub_type,
        payload ->> 'currency' as currency,
        lower(trim(payload ->> 'account_status')) as account_status,
        nullif(payload ->> 'opened_at', '')::timestamptz as opened_at,
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
            partition by account_id
            order by coalesce(updated_at, opened_at, ingested_at) desc, ingested_at desc
        ) as _rn
    from renamed
)

select * except(_rn)
from deduped
where _rn = 1
