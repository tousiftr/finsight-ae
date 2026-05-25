{{ config(materialized='view', tags=['product_analytics_hourly']) }}

with product_events as (
    select
        event_id,
        customer_id,
        account_id,
        session_id,
        event_name,
        event_timestamp,
        platform,
        feature_name,
        event_properties
    from {{ ref('stg_product_events') }}
    where customer_id is not null
      and event_timestamp is not null
),
kyc_events as (
    select
        raw_kyc_application_id as source_event_id,
        case
            when submitted_at is not null then 'KYC Submitted'
            when kyc_status = 'approved' and reviewed_at is not null then 'KYC Approved'
            when kyc_status = 'rejected' and reviewed_at is not null then 'KYC Rejected'
        end as event_name,
        customer_id::text as distinct_id,
        coalesce(
            case when submitted_at is not null then submitted_at end,
            case when kyc_status in ('approved', 'rejected') then reviewed_at end
        ) as event_time,
        'stg_kyc_applications' as event_source,
        jsonb_strip_nulls(jsonb_build_object(
            'source', 'kyc_application',
            'customer_id', customer_id,
            'kyc_application_id', kyc_application_id,
            'kyc_status', kyc_status,
            'kyc_level', kyc_level,
            'country', country,
            'review_channel', review_channel,
            'reviewer_type', reviewer_type
        )) as event_properties
    from {{ ref('stg_kyc_applications') }}
    where customer_id is not null
),
product_events_normalized as (
    select
        event_id as source_event_id,
        case
            when event_name = 'signup_completed' then 'User Registered'
            when event_name = 'account_created' then 'Account Activated'
            when event_name = 'transfer_started' then 'Transaction Started'
            when event_name = 'transfer_completed' then 'Transaction Completed'
            when event_name = 'crypto_buy_clicked' then 'Feature Used'
            when event_name = 'deposit_completed' then 'Account Activated'
            when event_name = 'deposit_started' then 'Transaction Started'
            else null
        end as event_name,
        customer_id::text as distinct_id,
        event_timestamp as event_time,
        'stg_product_events' as event_source,
        jsonb_strip_nulls(jsonb_build_object(
            'source', 'product_event',
            'customer_id', customer_id,
            'account_id', account_id,
            'session_id', session_id,
            'platform', platform,
            'feature_name', feature_name,
            'raw_event_name', event_name,
            'event_properties', event_properties
        )) as event_properties
    from product_events
)
select
    source_event_id,
    event_name,
    distinct_id,
    event_time,
    md5(concat_ws('||', source_event_id, event_name, distinct_id, event_time::text)) as insert_id,
    event_source,
    event_properties
from (
    select * from product_events_normalized
    union all
    select * from kyc_events
) events
where event_name is not null
  and event_time is not null
