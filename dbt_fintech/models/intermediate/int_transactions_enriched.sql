{{
    config(
        materialized='incremental',
        unique_key='transaction_id',
        on_schema_change='sync_all_columns'
    )
}}

select
    t.transaction_id,
    t.account_id,
    t.customer_id,
    t.transaction_ts,
    t.transaction_ts::date as transaction_date,
    t.status_updated_at,
    t.updated_at,
    t.amount,
    t.currency,
    t.fee_amount,
    t.transaction_type,
    tt.transaction_type_label,
    tt.transaction_flow,
    t.transaction_status,
    t.payment_method,
    ts.transaction_status_label,
    ts.is_success as is_successful_status,
    ts.is_terminal as is_terminal_status,
    t.merchant_id,
    t.merchant_category,
    m.merchant_name,
    m.merchant_country,
    m.merchant_city,
    m.merchant_risk_tier,
    m.is_high_risk_merchant,
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
    t.loaded_at,
    t.ingested_at
from {{ ref('int_transactions') }} t
left join {{ ref('int_account_enriched') }} a
    on t.account_id = a.account_id
left join {{ ref('int_customers') }} c
    on t.customer_id = c.customer_id
left join {{ ref('int_merchants') }} m
    on t.merchant_id = m.merchant_id
left join {{ ref('stg_seed_transaction_types') }} tt
    on t.transaction_type = tt.transaction_type
left join {{ ref('stg_seed_transaction_statuses') }} ts
    on t.transaction_status = ts.transaction_status

{% if is_incremental() %}
where t.loaded_at >= (
    select coalesce(max(loaded_at), '1900-01-01'::timestamp)
    from {{ this }}
)
{% endif %}
