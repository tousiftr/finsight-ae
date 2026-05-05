{{ config(materialized='view') }}

select
    payload ->> 'account_id' as raw_account_id,
    payload ->> 'account_id' as account_id,
    payload ->> 'customer_id' as customer_id,
    lower(nullif(payload ->> 'account_type', '')) as account_type,
    lower(nullif(payload ->> 'investment_sub_type', '')) as investment_sub_type,
    upper(nullif(payload ->> 'currency', '')) as currency,
    lower(nullif(payload ->> 'account_status', '')) as account_status,
    nullif(payload ->> 'opened_at', '')::timestamptz as opened_at,
    nullif(payload ->> 'closed_at', '')::timestamptz as closed_at,
    nullif(payload ->> 'initial_balance', '')::numeric as initial_balance,
    nullif(payload ->> 'current_balance', '')::numeric as current_balance,
    dt,
    batch_id,
    loaded_at,
    loaded_at as ingested_at
from {{ source('raw', 'raw_accounts') }}
