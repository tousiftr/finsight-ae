select
    a.account_id,
    a.plan_tier
from {{ ref('stg_accounts') }} a
left join {{ ref('plan_tiers') }} p
    on a.plan_tier = p.plan_tier
where a.plan_tier is not null
  and p.plan_tier is null
