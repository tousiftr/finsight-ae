{{ config(materialized='table', tags=['product_analytics_hourly']) }}

select
    event_timestamp::date as activity_date,
    customer_id,
    platform,
    count(*) as event_count,
    count(distinct session_id) as session_count,
    min(event_timestamp) as first_event_at,
    max(event_timestamp) as last_event_at,
    bool_or(event_name = 'investment_tab_viewed' or feature_name ilike '%investment%') as used_investment_feature,
    bool_or(event_name = 'card_screen_viewed' or feature_name ilike '%card%') as used_card_feature,
    bool_or(event_name in ('transfer_started', 'transfer_completed') or feature_name ilike '%transfer%') as used_transfer_feature
from {{ ref('stg_product_events') }}
group by 1,2,3
