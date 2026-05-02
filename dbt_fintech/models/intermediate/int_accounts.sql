select
    account_id,
    customer_id,
    account_type,
    account_status,
    opened_at,
    batch_id,
    source_file_path,
    ingested_at
from {{ ref('stg_accounts') }}
