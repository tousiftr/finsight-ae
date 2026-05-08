{{ config(materialized='view') }}

{% set required_raw_merchant_columns = [
    'raw_merchant_id',
    'merchant_id',
    'payload',
    'source_file_path',
    'dt',
    'batch_id',
    'loaded_at'
] %}

{% if execute %}
    {% set raw_merchants_relation = adapter.get_relation(database=target.database, schema='raw', identifier='raw_merchants') %}
    {% set raw_transactions_relation = adapter.get_relation(database=target.database, schema='raw', identifier='raw_transactions') %}
    {% set raw_merchant_columns = [] %}
    {% if raw_merchants_relation is not none %}
        {% set raw_merchant_columns = adapter.get_columns_in_relation(raw_merchants_relation) | map(attribute='name') | map('lower') | list %}
    {% endif %}
    {% set missing_raw_merchant_columns = required_raw_merchant_columns | reject('in', raw_merchant_columns) | list %}
    {% set use_raw_merchants = raw_merchants_relation is not none and (missing_raw_merchant_columns | length == 0) %}
{% else %}
    {% set raw_transactions_relation = none %}
    {% set use_raw_merchants = true %}
{% endif %}

{% if use_raw_merchants %}
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
{% elif raw_transactions_relation is not none %}
with transaction_merchants as (
    select
        'raw_mer_' || md5(nullif(payload ->> 'merchant_id', '')) as raw_merchant_id,
        nullif(payload ->> 'merchant_id', '') as merchant_id,
        'Unknown Merchant ' || nullif(payload ->> 'merchant_id', '') as merchant_name,
        coalesce(lower(nullif(payload ->> 'merchant_category', '')), 'unknown') as merchant_category,
        null::text as merchant_country,
        null::text as merchant_city,
        'low' as risk_tier,
        false as is_high_risk,
        nullif(payload ->> 'transaction_timestamp', '')::timestamptz as onboarded_at,
        nullif(payload ->> 'transaction_timestamp', '')::timestamptz as updated_at,
        nullif(source_object_key, '') as source_file_path,
        dt,
        batch_id,
        loaded_at,
        loaded_at as ingested_at,
        row_number() over (
            partition by nullif(payload ->> 'merchant_id', '')
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_transactions') }}
    where nullif(payload ->> 'merchant_id', '') is not null
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
from transaction_merchants
where rn = 1
{% else %}
select
    null::text as raw_merchant_id,
    null::text as merchant_id,
    null::text as merchant_name,
    null::text as merchant_category,
    null::text as merchant_country,
    null::text as merchant_city,
    null::text as risk_tier,
    null::boolean as is_high_risk,
    null::timestamptz as onboarded_at,
    null::timestamptz as updated_at,
    null::text as source_file_path,
    null::date as dt,
    null::text as batch_id,
    null::timestamptz as loaded_at,
    null::timestamptz as ingested_at
where false
{% endif %}
