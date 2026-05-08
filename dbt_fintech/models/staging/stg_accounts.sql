{{ config(materialized='view') }}

with ranked as (
    select
        payload ->> 'account_id' as raw_account_id,
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,
        lower(nullif(payload ->> 'account_type', '')) as account_type,
        case
            when lower(nullif(payload ->> 'account_type', '')) = 'investment'
                then lower(coalesce(
                    nullif(payload ->> 'account_sub_type', ''),
                    nullif(payload ->> 'investment_sub_type', '')
                ))
            else lower(nullif(payload ->> 'account_sub_type', ''))
        end as account_sub_type,
        lower(nullif(payload ->> 'plan_tier', '')) as plan_tier,
        case
            when lower(nullif(payload ->> 'account_type', '')) = 'investment'
                then lower(coalesce(
                    nullif(payload ->> 'investment_sub_type', ''),
                    nullif(payload ->> 'account_sub_type', '')
                ))
            else null
        end as investment_sub_type,
        upper(nullif(payload ->> 'currency', '')) as currency,
        lower(nullif(payload ->> 'account_status', '')) as account_status,
        nullif(payload ->> 'opened_at', '')::timestamptz as opened_at,
        nullif(payload ->> 'closed_at', '')::timestamptz as closed_at,
        nullif(payload ->> 'initial_balance', '')::numeric as initial_balance,
        nullif(payload ->> 'current_balance', '')::numeric as current_balance,
        nullif(source_object_key, '') as source_file_path,
        dt,
        batch_id,
        loaded_at,
        loaded_at as ingested_at,
        row_number() over (
            partition by payload ->> 'account_id'
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_accounts') }}
)
select
    raw_account_id,
    account_id,
    customer_id,
    account_type,
    account_sub_type,
    plan_tier,
    investment_sub_type,
    currency,
    account_status,
    opened_at,
    closed_at,
    initial_balance,
    current_balance,
    source_file_path,
    dt,
    batch_id,
    loaded_at,
    ingested_at
from ranked
where rn = 1
