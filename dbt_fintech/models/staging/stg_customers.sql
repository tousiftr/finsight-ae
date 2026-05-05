{{ config(materialized='view') }}

select
    payload ->> 'customer_id' as raw_customer_id,
    payload ->> 'customer_id' as customer_id,
    payload ->> 'first_name' as first_name,
    payload ->> 'last_name' as last_name,
    lower(nullif(payload ->> 'email', '')) as email,
    nullif(payload ->> 'phone', '') as phone,
    nullif(payload ->> 'date_of_birth', '')::date as date_of_birth,
    payload ->> 'country' as country,
    payload ->> 'city' as city,
    nullif(payload ->> 'created_at', '')::timestamptz as created_at,
    lower(nullif(payload ->> 'signup_channel', '')) as signup_channel,
    nullif(payload ->> 'customer_segment', '') as customer_segment,
    nullif(payload ->> 'employment_status', '') as employment_status,
    nullif(payload ->> 'income_band', '') as income_band,
    nullif(payload ->> 'risk_segment', '') as risk_segment,
    lower(nullif(payload ->> 'kyc_status', '')) as kyc_status,
    dt,
    batch_id,
    loaded_at,
    loaded_at as ingested_at
from {{ source('raw', 'raw_customers') }}
