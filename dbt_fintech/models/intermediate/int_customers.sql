select
    customer_id,
    kyc_status as customer_status,
    country,
    created_at,
    batch_id,
    ingested_at
from {{ ref('stg_customers') }}
