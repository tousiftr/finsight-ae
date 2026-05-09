{% snapshot snap_transactions %}

{{
    config(
        target_schema='snapshots',
        unique_key='transaction_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select
    transaction_id,
    account_id,
    customer_id,
    transaction_type,
    transaction_timestamp,
    amount,
    currency,
    merchant_id,
    merchant_category,
    status,
    payment_method,
    fee_amount,
    failure_reason,
    status_updated_at,
    updated_at,
    loaded_at
from {{ ref('stg_transactions') }}

{% endsnapshot %}
