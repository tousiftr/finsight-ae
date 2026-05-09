{{ config(materialized='view') }}

select
    transaction_id,
    account_id,
    customer_id,
    status,
    amount,
    fee_amount,
    failure_reason,
    dbt_valid_from,
    dbt_valid_to,
    (dbt_valid_to is null) as is_current
from {{ ref('snap_transactions') }}
