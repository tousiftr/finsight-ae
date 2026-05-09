{{ config(materialized='view') }}

with history as (
    select
        customer_id,
        count(*) as number_of_customer_versions,
        min(dbt_valid_from) as first_seen_at,
        max(coalesce(dbt_valid_to, dbt_valid_from)) as latest_seen_at,
        bool_or(kyc_status = 'manual_review') as had_manual_review,
        bool_or(kyc_status = 'rejected') as had_rejection,
        max(dbt_valid_from) filter (where dbt_valid_to is null) as latest_snapshot_valid_from
    from {{ ref('snap_customers') }}
    group by 1
)

select
    c.customer_id,
    c.kyc_status as current_kyc_status,
    c.risk_segment as current_risk_segment,
    coalesce(h.first_seen_at, c.created_at) as first_seen_at,
    coalesce(h.latest_seen_at, c.updated_at) as latest_seen_at,
    coalesce(h.number_of_customer_versions, 1) as number_of_customer_versions,
    coalesce(h.had_manual_review, c.kyc_status = 'manual_review') as had_manual_review,
    coalesce(h.had_rejection, c.kyc_status = 'rejected') as had_rejection,
    h.latest_snapshot_valid_from
from {{ ref('stg_customers') }} c
left join history h
    on c.customer_id = h.customer_id
