{{ config(materialized='view') }}

select
    transaction_id,
    transaction_date,
    transaction_ts as transaction_timestamp,
    account_id,
    customer_id,
    transaction_type,
    amount,
    currency,
    transaction_status,
    merchant_id,
    merchant_category,
    account_type,
    account_sub_type,
    plan_tier,
    account_status,
    customer_status,
    country,
    batch_id,
    source_file_path,
    ingested_at,
    case
        when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then true
        else false
    end as is_successful_transaction
from {{ ref('int_transactions_enriched') }}
