select
    a.account_id,
    a.customer_id,
    a.account_type,
    at.account_type_label,
    at.account_type_group,
    a.account_sub_type,
    ast.account_sub_type_label,
    ast.account_sub_type_group,
    a.plan_tier,
    pt.plan_tier_label,
    pt.plan_tier_rank,
    pt.is_paid_tier,
    a.currency,
    a.account_status,
    a.opened_at,
    a.closed_at,
    a.initial_balance,
    a.current_balance,
    a.batch_id,
    a.source_file_path,
    a.ingested_at
from {{ ref('stg_accounts') }} a
left join {{ ref('account_types') }} at
    on a.account_type = at.account_type
left join {{ ref('account_sub_types') }} ast
    on a.account_sub_type = ast.account_sub_type
    and a.account_type = ast.account_type
left join {{ ref('plan_tiers') }} pt
    on a.plan_tier = pt.plan_tier
