select
    transaction_id,
    account_id,
    customer_id,
    transaction_timestamp as transaction_ts,
    transaction_timestamp::date as transaction_date,
    amount,
    currency,
    transaction_type,
    status as transaction_status,
    merchant_category,
    batch_id,
    source_file_path,
    ingested_at
from {{ ref('stg_transactions') }}
