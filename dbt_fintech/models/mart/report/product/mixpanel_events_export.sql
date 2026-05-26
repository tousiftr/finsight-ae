{{ config(materialized='view', tags=['product_analytics_hourly']) }}

with product_events as (
    select
        event_id,
        customer_id,
        account_id,
        session_id,
        event_name as raw_event_name,
        event_timestamp,
        platform,
        feature_name,
        event_properties
    from {{ ref('stg_product_events') }}
    where customer_id is not null
      and event_timestamp is not null
),
product_events_normalized as (
    select
        event_id as source_event_id,
        case
            when raw_event_name = 'signup_completed' then 'User Registered'
            when raw_event_name = 'kyc_submitted' then 'KYC Submitted'
            when raw_event_name = 'pin_set' then 'PIN Set'
            when raw_event_name in ('account_created', 'deposit_completed') then 'Account Activated'
            when raw_event_name = 'transfer_started' then 'Transaction Started'
            when raw_event_name = 'transfer_completed' then 'Transaction Completed'
            when raw_event_name in ('crypto_buy_clicked', 'card_tapped', 'billpay_initiated') then 'Feature Used'
            else null
        end as event_name,
        customer_id::text as distinct_id,
        event_timestamp as event_time,
        'stg_product_events' as event_source,
        jsonb_strip_nulls(jsonb_build_object(
            'platform', platform,
            'feature_name', feature_name,
            'channel', event_properties ->> 'channel',
            'account_type', event_properties ->> 'account_type',
            'product_area', event_properties ->> 'product_area',
            'country', event_properties ->> 'country',
            'raw_event_name', raw_event_name,
            'event_source', 'stg_product_events',
            'session_id', session_id,
            'account_id', account_id
        )) as event_properties
    from product_events
),
kyc_events as (
    select
        raw_kyc_application_id as source_event_id,
        event_name,
        customer_id::text as distinct_id,
        event_time,
        'stg_kyc_applications' as event_source,
        jsonb_strip_nulls(jsonb_build_object(
            'kyc_status', kyc_status,
            'kyc_level', kyc_level,
            'country', country,
            'channel', review_channel,
            'product_area', 'kyc',
            'event_source', 'stg_kyc_applications'
        )) as event_properties
    from (
        select
            raw_kyc_application_id,
            customer_id,
            submitted_at as event_time,
            'KYC Submitted' as event_name,
            kyc_status,
            kyc_level,
            country,
            review_channel
        from {{ ref('stg_kyc_applications') }}
        where customer_id is not null
          and submitted_at is not null

        union all

        select
            raw_kyc_application_id,
            customer_id,
            reviewed_at as event_time,
            case
                when kyc_status = 'approved' then 'KYC Approved'
                when kyc_status = 'rejected' then 'KYC Rejected'
            end as event_name,
            kyc_status,
            kyc_level,
            country,
            review_channel
        from {{ ref('stg_kyc_applications') }}
        where customer_id is not null
          and reviewed_at is not null
          and kyc_status in ('approved', 'rejected')
    ) e
)
select
    source_event_id,
    event_name,
    distinct_id,
    event_time,
    md5(concat_ws('||', source_event_id, event_name, distinct_id, event_time::text, event_source)) as insert_id,
    event_source,
    event_properties
from (
    select * from product_events_normalized
    union all
    select * from kyc_events
) events
where event_name is not null
  and event_time is not null
