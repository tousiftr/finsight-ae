{{ config(materialized='view') }}

select
    submitted_at::date as submitted_date,
    kyc_status,
    kyc_level,
    count(*) as application_count,
    avg(risk_score) as avg_risk_score,
    sum(case when is_approved then 1 else 0 end) as approved_count,
    sum(case when is_rejected then 1 else 0 end) as rejected_count,
    sum(case when is_manual_review then 1 else 0 end) as manual_review_count,
    sum(case when is_pending then 1 else 0 end) as pending_count,
    (sum(case when is_approved then 1 else 0 end)::numeric / nullif(count(*), 0)::numeric) as approval_rate,
    (sum(case when is_manual_review then 1 else 0 end)::numeric / nullif(count(*), 0)::numeric) as manual_review_rate
from {{ ref('int_kyc_funnel') }}
group by 1,2,3
