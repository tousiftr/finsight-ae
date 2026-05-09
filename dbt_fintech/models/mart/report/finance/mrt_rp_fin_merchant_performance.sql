{{ config(materialized='view') }}

select
    merchant_id,
    merchant_name,
    merchant_category,
    merchant_country,
    merchant_city,
    merchant_risk_tier,
    is_high_risk_merchant,
    count(*) as transaction_count,
    count(*) filter (where is_successful_status) as successful_transaction_count,
    count(*) filter (where not coalesce(is_successful_status, false)) as unsuccessful_transaction_count,
    sum(amount) as gross_transaction_volume,
    avg(amount) as average_transaction_value,
    sum(coalesce(fee_amount, 0)) as fee_revenue,
    min(transaction_ts) as first_transaction_ts,
    max(transaction_ts) as latest_transaction_ts,
    max(ingested_at) as latest_ingested_at
from {{ ref('int_transactions_enriched') }}
where merchant_id is not null
group by
    merchant_id,
    merchant_name,
    merchant_category,
    merchant_country,
    merchant_city,
    merchant_risk_tier,
    is_high_risk_merchant
