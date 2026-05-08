select
    account_id,
    account_type,
    account_sub_type
from {{ ref('stg_accounts') }}
where account_sub_type is null
