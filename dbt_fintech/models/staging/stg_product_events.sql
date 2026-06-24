{{ config(materialized='view') }}

with ranked as (
    select
        payload ->> 'event_id' as raw_product_event_id,
        payload ->> 'event_id' as event_id,
        payload ->> 'customer_id' as customer_id,
        nullif(payload ->> 'account_id', '') as account_id,
        payload ->> 'session_id' as session_id,
        payload ->> 'event_name' as event_name,
        nullif(payload ->> 'event_timestamp', '')::timestamptz as event_timestamp,
        payload ->> 'platform' as platform,
        payload ->> 'device_type' as device_type,
        payload ->> 'app_version' as app_version,
        payload ->> 'screen_name' as screen_name,
        payload ->> 'feature_name' as feature_name,
        (payload -> 'event_properties')::jsonb as event_properties,
        dt,
        batch_id,
        loaded_at,
        loaded_at as ingested_at,
        row_number() over (
            partition by payload ->> 'event_id'
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_product_events') }}
)
select
    raw_product_event_id,
    event_id,
    customer_id,
    account_id,
    session_id,
    event_name,
    event_timestamp,
    platform,
    device_type,
    app_version,
    screen_name,
    feature_name,
    event_properties,
    dt,
    batch_id,
    loaded_at,
    ingested_at
from ranked
where rn = 1
  and exists (
      select 1
      from {{ ref('stg_customers') }} as customers
      where customers.customer_id = ranked.customer_id
  )
