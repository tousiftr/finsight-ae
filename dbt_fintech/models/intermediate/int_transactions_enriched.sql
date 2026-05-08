{{ config(materialized='table') }}

select
    t.transaction_id,
    t.account_id,
    t.customer_id,
    t.transaction_ts,
    t.transaction_ts::date as transaction_date,
    t.amount,
    t.currency,
    t.transaction_type,
    tt.transaction_type_label,
    tt.transaction_flow,
    t.transaction_status,
    ts.transaction_status_label,
    ts.is_success as is_successful_status,
    ts.is_terminal as is_terminal_status,
    t.merchant_id,
    t.merchant_category,
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
    c.customer_status,
    c.country,
    t.batch_id,
    coalesce(a.source_file_path, c.source_file_path) as source_file_path,
    t.ingested_at
from {{ ref('int_transactions') }} t
left join {{ ref('int_account_enriched') }} a
    on t.account_id = a.account_id
left join {{ ref('int_customers') }} c
    on t.customer_id = c.customer_id
left join {{ ref('stg_seed_transaction_types') }} tt
    on t.transaction_type = tt.transaction_type
left join {{ ref('stg_seed_transaction_statuses') }} ts
    on t.transaction_status = ts.transaction_status
