select
    account_id,
    customer_id,
    account_type,
    account_status,
    opened_at,
    batch_id,
    ingested_at
from {{ ref('stg_accounts') }}
