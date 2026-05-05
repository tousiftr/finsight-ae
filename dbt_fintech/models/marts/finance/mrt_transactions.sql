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
    status,
    payment_method,
    fee_amount,
    merchant_id,
    account_type,
    customer_segment,
    signup_channel,
    latest_kyc_status,
    is_successful_transaction
from {{ ref('int_transactions_enriched') }}
