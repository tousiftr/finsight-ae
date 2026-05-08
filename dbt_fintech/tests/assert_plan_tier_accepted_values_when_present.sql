select
    account_id,
    plan_tier
from {{ ref('stg_accounts') }}
where plan_tier is not null
  and plan_tier not in ('free', 'plus', 'premium')
