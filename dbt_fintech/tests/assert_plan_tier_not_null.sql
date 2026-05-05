select *
from {{ ref('stg_accounts') }}
where plan_tier is null
