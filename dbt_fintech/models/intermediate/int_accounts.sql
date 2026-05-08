select
    account_id,
    customer_id,
    account_type,
    account_sub_type,
    plan_tier,
    currency,
    account_status,
    opened_at,
    closed_at,
    initial_balance,
    current_balance,
    batch_id,
    source_file_path,
    ingested_at
from {{ ref('stg_accounts') }}
