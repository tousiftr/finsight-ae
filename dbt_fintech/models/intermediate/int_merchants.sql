{{ config(materialized='table') }}

select
    merchant_id,
    merchant_name,
    merchant_category,
    merchant_country,
    merchant_city,
    risk_tier as merchant_risk_tier,
    is_high_risk as is_high_risk_merchant,
    onboarded_at,
    updated_at,
    batch_id,
    ingested_at
from {{ ref('stg_merchants') }}
