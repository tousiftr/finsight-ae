{{ config(materialized='view') }}

select
    payload ->> 'transaction_id' as raw_transaction_id,
    payload ->> 'transaction_id' as transaction_id,
    payload ->> 'account_id' as account_id,
    payload ->> 'customer_id' as customer_id,
    lower(nullif(payload ->> 'transaction_type', '')) as transaction_type,
    nullif(payload ->> 'transaction_timestamp', '')::timestamptz as transaction_timestamp,
    nullif(payload ->> 'amount', '')::numeric as amount,
    upper(nullif(payload ->> 'currency', '')) as currency,
    nullif(payload ->> 'merchant_id', '') as merchant_id,
    lower(nullif(payload ->> 'status', '')) as status,
    nullif(payload ->> 'payment_method', '') as payment_method,
    nullif(payload ->> 'fee_amount', '')::numeric as fee_amount,
    nullif(payload ->> 'failure_reason', '') as failure_reason,
    dt,
    batch_id,
    loaded_at,
    loaded_at as ingested_at
from {{ source('raw', 'raw_transactions') }}
