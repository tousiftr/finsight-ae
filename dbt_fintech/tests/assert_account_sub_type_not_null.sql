select *
from {{ ref('stg_accounts') }}
where account_sub_type is null
