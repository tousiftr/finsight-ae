{{ config(materialized='view') }}

with ranked as (
    select
        raw_merchant_id,
        coalesce(merchant_id, payload ->> 'merchant_id') as merchant_id,
        nullif(payload ->> 'merchant_name', '') as merchant_name,
        lower(nullif(payload ->> 'merchant_category', '')) as merchant_category,
        upper(nullif(payload ->> 'merchant_country', '')) as merchant_country,
        nullif(payload ->> 'merchant_city', '') as merchant_city,
        lower(nullif(payload ->> 'risk_tier', '')) as risk_tier,
        nullif(payload ->> 'is_high_risk', '')::boolean as is_high_risk,
        nullif(payload ->> 'onboarded_at', '')::timestamptz as onboarded_at,
        nullif(payload ->> 'updated_at', '')::timestamptz as updated_at,
        source_file_path,
        dt,
        batch_id,
        loaded_at,
        loaded_at as ingested_at,
        row_number() over (
            partition by coalesce(merchant_id, payload ->> 'merchant_id')
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_merchants') }}
)
select
    raw_merchant_id,
    merchant_id,
    merchant_name,
    merchant_category,
    merchant_country,
    merchant_city,
    risk_tier,
    is_high_risk,
    onboarded_at,
    updated_at,
    source_file_path,
    dt,
    batch_id,
    loaded_at,
    ingested_at
from ranked
where rn = 1
