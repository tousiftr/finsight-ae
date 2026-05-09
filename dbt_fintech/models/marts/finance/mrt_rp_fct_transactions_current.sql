{{ config(materialized='view', alias='fct_transactions_current') }}

select
    transaction_id,
    account_id,
    customer_id,
    transaction_type,
    transaction_ts as transaction_timestamp,
    amount,
    currency,
    merchant_id,
    merchant_category,
    transaction_status as status,
    payment_method,
    fee_amount,
    failure_reason,
    loaded_at,
    coalesce(status_updated_at, updated_at) as status_updated_at,
    coalesce(is_successful_status, lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded')) as is_successful,
    lower(transaction_status) in ('failed', 'declined', 'error') as is_failed,
    lower(transaction_status) = 'pending' as is_pending
from {{ ref('int_transactions_enriched') }}
