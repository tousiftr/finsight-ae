{{ config(materialized='view') }}

select
    event_timestamp::date as event_date,
    count(*) as event_count,
    count(distinct customer_id) as active_customers,
    count(distinct session_id) as sessions,
    sum(case when event_name = 'app_opened' then 1 else 0 end) as app_opens,
    sum(case when event_name = 'signup_started' then 1 else 0 end) as signup_started,
    sum(case when event_name = 'signup_completed' then 1 else 0 end) as signup_completed,
    sum(case when event_name = 'kyc_started' then 1 else 0 end) as kyc_started,
    sum(case when event_name = 'kyc_submitted' then 1 else 0 end) as kyc_submitted,
    sum(case when event_name = 'transfer_started' then 1 else 0 end) as transfer_started,
    sum(case when event_name = 'transfer_completed' then 1 else 0 end) as transfer_completed
from {{ ref('stg_product_events') }}
group by 1
