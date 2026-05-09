{{
    config(
        materialized='incremental',
        unique_key='transaction_id',
        on_schema_change='sync_all_columns'
    )
}}

select
    transaction_id,
    account_id,
    customer_id,
    transaction_timestamp as transaction_ts,
    transaction_timestamp::date as transaction_date,
    status_updated_at,
    updated_at,
    amount,
    currency,
    transaction_type,
    status as transaction_status,
    payment_method,
    merchant_id,
    merchant_category,
    fee_amount,
    failure_reason,
    batch_id,
    loaded_at,
    ingested_at
from {{ ref('stg_transactions') }}
{% if is_incremental() %}
where loaded_at >= (
    select coalesce(max(loaded_at), '1900-01-01'::timestamp)
    from {{ this }}
)
{% endif %}
