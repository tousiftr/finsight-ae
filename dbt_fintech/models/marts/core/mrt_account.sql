{{ config(materialized='view') }}

select
    account_id,
    customer_id,
    account_type,
    account_type_label,
    account_type_group,
    account_sub_type,
    account_sub_type_label,
    account_sub_type_group,
    plan_tier,
    plan_tier_label,
    plan_tier_rank,
    is_paid_tier,
    currency,
    account_status,
    opened_at,
    closed_at,
    initial_balance,
    current_balance,
    batch_id,
    source_file_path,
    ingested_at,
    customer_segment,
    latest_kyc_status,
    risk_segment
from {{ ref('int_account_enriched') }}
