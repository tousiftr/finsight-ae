{{ config(materialized='table') }}

with activation as (
    select * from {{ ref('fct_activation') }}
)
select
    signup_date,
    signup_channel,
    count(*) as customers_signed_up,
    sum(case when has_kyc then 1 else 0 end) as kyc_submitted,
    sum(case when is_kyc_approved then 1 else 0 end) as kyc_approved,
    sum(case when has_account then 1 else 0 end) as accounts_opened,
    sum(case when has_completed_transaction then 1 else 0 end) as activated_customers,
    (sum(case when has_completed_transaction then 1 else 0 end)::numeric / nullif(count(*), 0)::numeric) as activation_rate
from activation
group by 1,2
