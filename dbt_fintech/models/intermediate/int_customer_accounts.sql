select
    a.account_id,
    a.customer_id,
    c.customer_status,
    c.country,
    c.created_at as customer_created_at,
    a.account_type,
    a.account_type_label,
    a.account_type_group,
    a.account_sub_type,
    a.account_sub_type_label,
    a.account_sub_type_group,
    a.plan_tier,
    a.plan_tier_label,
    a.plan_tier_rank,
    a.is_paid_tier,
    a.account_status,
    a.opened_at,
    a.batch_id,
    a.source_file_path,
    a.ingested_at
from {{ ref('int_accounts') }} a
left join {{ ref('int_customers') }} c
    on a.customer_id = c.customer_id
