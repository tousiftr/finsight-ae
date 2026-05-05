{{ config(materialized='table') }}

select
    activity_date,
    platform,
    count(distinct customer_id) as daily_active_users,
    sum(event_count) as total_events,
    sum(session_count) as total_sessions,
    count(distinct case when used_investment_feature then customer_id end) as investment_feature_users,
    count(distinct case when used_card_feature then customer_id end) as card_feature_users,
    count(distinct case when used_transfer_feature then customer_id end) as transfer_feature_users
from {{ ref('int_daily_user_activity') }}
group by 1,2
