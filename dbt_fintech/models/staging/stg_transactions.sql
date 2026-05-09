{{ config(materialized='view') }}

with ranked as (
    select
        payload ->> 'transaction_id' as raw_transaction_id,
        payload ->> 'transaction_id' as transaction_id,
        payload ->> 'account_id' as account_id,
        payload ->> 'customer_id' as customer_id,
        lower(nullif(payload ->> 'transaction_type', '')) as transaction_type,
        nullif(payload ->> 'transaction_timestamp', '')::timestamptz as transaction_timestamp,
        nullif(payload ->> 'status_updated_at', '')::timestamptz as status_updated_at,
        coalesce(nullif(coalesce(payload ->> 'updated_at', payload ->> 'status_updated_at'), '')::timestamptz, loaded_at) as updated_at,
        nullif(payload ->> 'amount', '')::numeric as amount,
        upper(nullif(payload ->> 'currency', '')) as currency,
        nullif(payload ->> 'merchant_id', '') as merchant_id,
        lower(nullif(payload ->> 'merchant_category', '')) as merchant_category,
        lower(nullif(payload ->> 'status', '')) as status,
        nullif(payload ->> 'payment_method', '') as payment_method,
        nullif(payload ->> 'fee_amount', '')::numeric as fee_amount,
        nullif(payload ->> 'failure_reason', '') as failure_reason,
        dt,
        batch_id,
        loaded_at,
        loaded_at as ingested_at,
        row_number() over (
            partition by payload ->> 'transaction_id'
            order by nullif(coalesce(payload ->> 'status_updated_at', payload ->> 'updated_at'), '')::timestamptz desc nulls last, loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_transactions') }}
)
select
    raw_transaction_id,
    transaction_id,
    account_id,
    customer_id,
    transaction_type,
    transaction_timestamp,
    status_updated_at,
    updated_at,
    amount,
    currency,
    merchant_id,
    merchant_category,
    status,
    payment_method,
    fee_amount,
    failure_reason,
    dt,
    batch_id,
    loaded_at,
    ingested_at
from ranked
where rn = 1
