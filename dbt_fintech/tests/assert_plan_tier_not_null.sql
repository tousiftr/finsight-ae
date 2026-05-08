select
    account_id,
    account_type,
    plan_tier
from {{ ref('stg_accounts') }}
where plan_tier is null
