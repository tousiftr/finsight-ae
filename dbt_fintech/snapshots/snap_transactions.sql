{% snapshot snap_transactions %}

{{
    config(
        target_schema='snapshots',
        unique_key='transaction_id',
        strategy='timestamp',
        updated_at='status_updated_at'
    )
}}

select
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
from {{ ref('stg_transactions') }}
where transaction_id is not null

{% endsnapshot %}
