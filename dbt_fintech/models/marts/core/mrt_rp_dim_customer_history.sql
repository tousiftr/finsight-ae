{{ config(materialized='view', alias='dim_customer_history') }}

select
    customer_id,
    kyc_status,
    customer_segment,
    risk_segment,
    dbt_valid_from,
    dbt_valid_to,
    (dbt_valid_to is null) as is_current
from {{ ref('snap_customers') }}
